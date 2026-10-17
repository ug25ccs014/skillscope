"""Versioned transparent matching for career-path hypotheses.

All ranking values are internal provisional heuristics. Public responses expose reasons and
provenance, not numerical fit probabilities. Student evidence is never treated as a career
verdict, and occupational records remain source-specific.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Callable, Iterable
from uuid import UUID

from app.schemas.challenges import AgeBand as ChallengeAgeBand, ChallengeDomain
from app.schemas.recommendations import (
    CareerHypothesisRecommendation,
    ConfidenceBreakdown,
    EvidenceConfidenceLevel,
    QualitativeStatus,
    RecommendationCategory,
    RecommendationEvidenceReference,
    RecommendationGap,
    RecommendationMatch,
    RecommendationPolicy,
    RecommendationSet,
    RecommendationSource,
    SourcedPathwayFact,
    ValidatingAction,
)
from app.schemas.student_evidence import (
    AgeBand,
    EvidenceItem,
    EvidenceType,
    SignalDimension,
    StudentProfile,
    UserInterpretation,
)
from app.services.challenges import CHALLENGES, ChallengeRepository, LIBRARY
from app.services.evidence_ledger import EvidenceLedgerRepository
from app.services.knowledge_graph import graph_status, list_career_cards
from app.services.provenance import DEFAULT_DB_PATH, ProvenanceRepository
from app.services.database import connect_sqlite

ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = ROOT / "data" / "recommendation_weights.json"
DOMAIN_POLICY_PATH = ROOT / "data" / "career_domain_hypotheses.json"
EVIDENCE_DETAIL_LIMIT = 200
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "become", "by", "for", "from", "how", "i", "in", "into", "is", "it", "like", "me", "my", "of", "on", "or", "the", "this", "to", "want", "what", "with", "would", "you", "your", "career", "job", "path", "work", "working", "learn", "learning", "try", "interested", "interest", "becoming", "could", "can", "about"
}
DOMAIN_LABELS = {
    ChallengeDomain.LOGIC_DATA: "Logic & data",
    ChallengeDomain.SCIENCE_RESEARCH: "Science & research",
    ChallengeDomain.TECHNOLOGY: "Technology",
    ChallengeDomain.DESIGN_CREATIVE: "Design & creative",
    ChallengeDomain.COMMUNICATION: "Communication",
    ChallengeDomain.HELPING_SOCIAL: "Helping & social problem-solving",
    ChallengeDomain.BUSINESS: "Business & entrepreneurship",
    ChallengeDomain.HANDS_ON_SPATIAL: "Hands-on & spatial",
    ChallengeDomain.ENVIRONMENT: "Environment",
}


class RecommendationCatalogError(RuntimeError):
    def __init__(self, message: str, status_code: int = 503):
        super().__init__(message)
        self.status_code = status_code


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Policy contract at {path.name} must be a JSON object.")
    return value


def load_recommendation_policy(path: Path = POLICY_PATH) -> dict[str, Any]:
    data = _read_json(path)
    RecommendationPolicy.model_validate(data)
    weights = data["weights"]
    if not abs(sum(float(v) for v in weights.values()) - 1.0) < 1e-8:
        raise ValueError("Recommendation weights must sum to 1.0 in the versioned policy file.")
    return data


def load_domain_policy(path: Path = DOMAIN_POLICY_PATH) -> dict[str, Any]:
    data = _read_json(path)
    if not isinstance(data.get("mappings"), list) or not data.get("policy_version"):
        raise ValueError("Career domain hypothesis policy is missing mappings or version.")
    for mapping in data["mappings"]:
        if not mapping.get("taxonomy") or not mapping.get("external_id") or not mapping.get("domains"):
            raise ValueError("Every domain hypothesis must be bound to a taxonomy identity and at least one domain.")
        unknown = set(mapping["domains"]) - {item.value for item in ChallengeDomain}
        if unknown:
            raise ValueError(f"Unknown challenge domain(s) in career domain hypothesis: {sorted(unknown)}")
    return data


def _normalize_token(token: str) -> str:
    value = token.casefold()
    if len(value) > 5 and value.endswith("ies"):
        value = value[:-3] + "y"
    elif len(value) > 5 and value.endswith("s") and not value.endswith(("ss", "us", "is")):
        value = value[:-1]
    return value


def _tokens(value: str | None) -> set[str]:
    if not value:
        return set()
    return {
        normalized for token in re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]*", value.casefold())
        if (normalized := _normalize_token(token)) not in STOPWORDS and len(normalized) > 1
    }


def _unique_strings(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        cleaned = value.strip()
        key = cleaned.casefold()
        if cleaned and key not in seen:
            seen.add(key)
            out.append(cleaned)
    return out


def _source_model(source: dict[str, Any]) -> RecommendationSource:
    return RecommendationSource(
        source_id=str(source.get("source_id") or "unknown"),
        source_record_id=str(source.get("source_record_id") or "unknown"),
        title=str(source.get("title") or "Untitled source record"),
        publisher=str(source.get("publisher") or "Publisher not recorded"),
        record_uri=source.get("record_uri"),
        source_version=source.get("source_version"),
        source_type=str(source.get("source_type") or "unknown"),
        geography=source.get("geography"),
        quality_status=str(source.get("quality_status") or "unverified"),
        fact_id=source.get("fact_id"),
        fact_type=source.get("fact_type"),
        fact_statement=source.get("fact_statement"),
        evidence_role=str(source.get("evidence_role") or "source_record"),
        notes=list(source.get("notes") or []),
    )


def _source_quality(career: dict[str, Any]) -> tuple[QualitativeStatus, str, list[RecommendationSource]]:
    sources = [_source_model(source) for source in career.get("source_references", [])]
    statuses = [item.quality_status.casefold() for item in sources]
    if statuses and all(status in {"reviewed", "verified"} for status in statuses):
        return QualitativeStatus.REVIEWED, "Source references in the active graph are marked reviewed or verified. This describes source review status, not the strength of a student's match.", sources
    if any(status in {"reviewed", "verified"} for status in statuses):
        return QualitativeStatus.PARTIAL, "Some source references have reviewed/verified status; others need review.", sources
    return QualitativeStatus.NOT_AVAILABLE, "No reviewed/verified source-reference quality status is available for this occupation.", sources


def _career_mapping(career: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any] | None:
    for item in policy["mappings"]:
        if item["taxonomy"] == career.get("taxonomy") and item["external_id"] == career.get("external_id"):
            return item
    return None


def _evidence_observation_text(item: EvidenceItem) -> str:
    snippets = [item.title, item.observation]
    snippets.extend(obs.criterion for obs in item.rubric_observations)
    snippets.extend(obs.observation for obs in item.rubric_observations)
    return " ".join(snippets)


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _observation_summary(items: Iterable[EvidenceItem]) -> tuple[int, str | None]:
    """Summarize distinct evidence records before the display trace is bounded."""
    unique: dict[UUID, EvidenceItem] = {}
    for item in items:
        unique.setdefault(item.evidence_id, item)
    dated = [parsed for item in unique.values() if (parsed := _parse_datetime(item.observed_at)) is not None]
    latest = max(dated, default=None)
    return len(unique), latest.isoformat() if latest else None


def _challenge_id(item: EvidenceItem) -> str | None:
    context = item.context or {}
    raw = context.get("challenge_id")
    return raw if isinstance(raw, str) and raw in LIBRARY else None


def _evidence_trace(item: EvidenceItem, why: str) -> RecommendationEvidenceReference:
    return RecommendationEvidenceReference(
        evidence_id=item.evidence_id,
        title=item.title,
        evidence_type=item.evidence_type.value,
        signal_dimension=item.signal_dimension.value,
        source_kind=item.source_kind.value,
        observed_at=item.observed_at.isoformat(),
        domain=item.domain,
        uncertainty=item.uncertainty.value,
        user_interpretation=item.user_interpretation.value,
        why_used=why,
    )


def _pathway_facts(career: dict[str, Any], max_facts: int = 4) -> list[SourcedPathwayFact]:
    facts: list[SourcedPathwayFact] = []
    for task in career.get("tasks", []):
        refs = task.get("source_references") or []
        if not refs:
            continue
        source = next((ref for ref in refs if ref.get("fact_statement") or ref.get("fact_type")), refs[0])
        label = str(task.get("label") or "").strip()
        if not label:
            continue
        facts.append(SourcedPathwayFact(
            fact_kind="source_listed_work_activity",
            statement=label,
            source=_source_model(source),
        ))
        if len(facts) >= max_facts:
            break
    if not facts:
        for source in career.get("source_references", []):
            statement = source.get("fact_statement")
            if isinstance(statement, str) and statement.strip():
                facts.append(SourcedPathwayFact(
                    fact_kind=str(source.get("fact_type") or "source_record_fact"),
                    statement=statement.strip(), source=_source_model(source),
                ))
                if len(facts) >= max_facts:
                    break
    return facts


def _portfolio_items(evidence: list[EvidenceItem]) -> list[EvidenceItem]:
    return [item for item in evidence if item.evidence_type == EvidenceType.PROJECT_PORTFOLIO]


def _career_text(career: dict[str, Any]) -> str:
    items = [career.get("label", "")]
    items.extend(task.get("label", "") for task in career.get("tasks", []))
    items.extend(skill.get("label", "") for skill in career.get("skills", []))
    return " ".join(str(item) for item in items if item)


def _normalize_phrase(value: str) -> str:
    """Normalize punctuation/spacing while preserving word order for exact phrase checks."""
    return re.sub(r"[^a-z0-9+#]+", " ", value.casefold()).strip()


def _contains_exact_phrase(text: str, phrase: str) -> bool:
    normalized_text = _normalize_phrase(text)
    normalized_phrase = _normalize_phrase(phrase)
    if not normalized_text or not normalized_phrase:
        return False
    # Whitespace padding enforces whole-phrase boundaries and preserves word order.
    return f" {normalized_phrase} " in f" {normalized_text} "


def _get_skill_matches(career: dict[str, Any], evidence: list[EvidenceItem]) -> list[tuple[str, list[EvidenceItem]]]:
    matches: list[tuple[str, list[EvidenceItem]]] = []
    for skill in career.get("skills", []):
        label = str(skill.get("label") or "").strip()
        if not label:
            continue
        matched = [item for item in evidence if _contains_exact_phrase(_evidence_observation_text(item), label)]
        if matched:
            matches.append((label, matched))
    return matches


def _goal_overlap(goal: str | None, career: dict[str, Any]) -> tuple[float | None, list[str]]:
    if not goal or not goal.strip():
        return None, []
    goal_tokens = _tokens(goal)
    title_tokens = _tokens(str(career.get("label") or ""))
    if not goal_tokens or not title_tokens:
        return 0.0, []
    common = sorted(goal_tokens & title_tokens)
    return min(1.0, len(common) / max(1, len(goal_tokens))), common


def _portfolio_overlap(career: dict[str, Any], portfolio: list[EvidenceItem]) -> tuple[float | None, list[str], list[EvidenceItem]]:
    if not portfolio:
        return None, [], []
    target = _tokens(_career_text(career))
    common_by_item: list[tuple[EvidenceItem, set[str]]] = []
    for item in portfolio:
        shared = target & _tokens(_evidence_observation_text(item))
        if shared:
            common_by_item.append((item, shared))
    if not common_by_item:
        return 0.0, [], []
    shared_tokens = sorted(set().union(*(shared for _, shared in common_by_item)))
    # This is just transparent lexical overlap in a voluntary description, not a project quality score.
    score = min(1.0, len(shared_tokens) / 4.0)
    return score, shared_tokens, [item for item, _ in common_by_item]


def _activity_evidence(evidence: list[EvidenceItem]) -> list[EvidenceItem]:
    return [item for item in evidence if item.evidence_type == EvidenceType.CHALLENGE_PERFORMANCE]


def _confidence(
    related: list[EvidenceItem], career_sources: list[RecommendationSource], today: date,
) -> tuple[EvidenceConfidenceLevel, ConfidenceBreakdown]:
    dated = [(item, _parse_datetime(item.observed_at)) for item in related]
    dated = [(item, dt) for item, dt in dated if dt]
    newest_days = min(((today - dt.date()).days for _, dt in dated), default=None)
    count = len(related)
    families = {_challenge_id(item) for item in related if _challenge_id(item)}
    source_kinds = {item.source_kind.value for item in related}
    dimensions = {item.signal_dimension.value for item in related}
    interpretations = {item.user_interpretation.value for item in related if item.user_interpretation != UserInterpretation.NOT_INTERPRETED}
    contradiction = (
        UserInterpretation.SUPPORTS_CURRENT_HYPOTHESIS.value in interpretations
        and UserInterpretation.CHALLENGES_CURRENT_HYPOTHESIS.value in interpretations
    ) or UserInterpretation.CHALLENGES_CURRENT_HYPOTHESIS.value in interpretations
    quality_values = {item.quality_status.casefold() for item in career_sources}
    reviewed = bool(quality_values & {"reviewed", "verified"})

    if count < 3:
        volume_status = QualitativeStatus.LIMITED
    elif count < 6:
        volume_status = QualitativeStatus.PARTIAL
    else:
        volume_status = QualitativeStatus.BROAD
    if newest_days is None:
        recency_status = QualitativeStatus.NOT_AVAILABLE
    elif newest_days <= 30:
        recency_status = QualitativeStatus.RECENT
    elif newest_days <= 90:
        recency_status = QualitativeStatus.PARTIAL
    else:
        recency_status = QualitativeStatus.OLDER
    if count == 0:
        consistency_status = QualitativeStatus.NOT_AVAILABLE
    elif contradiction:
        consistency_status = QualitativeStatus.MIXED
    elif interpretations:
        consistency_status = QualitativeStatus.CONSISTENT_SO_FAR
    else:
        consistency_status = QualitativeStatus.LIMITED
    source_status = QualitativeStatus.REVIEWED if reviewed else QualitativeStatus.NOT_AVAILABLE
    coverage_status = QualitativeStatus.BROAD if len(source_kinds) >= 2 and (len(families) >= 2 or len(dimensions) >= 2) else QualitativeStatus.NARROW if count else QualitativeStatus.NOT_AVAILABLE

    high = (
        count >= 6 and len(families) >= 3 and len(source_kinds) >= 2 and len(dimensions) >= 2
        and newest_days is not None and newest_days <= 90 and not contradiction and reviewed
    )
    moderate = (
        count >= 3 and len(families) >= 2 and newest_days is not None and newest_days <= 90
        and not contradiction and reviewed
    )
    level = EvidenceConfidenceLevel.HIGH if high else EvidenceConfidenceLevel.MODERATE if moderate else EvidenceConfidenceLevel.LOW
    reasons: list[str] = []
    if count < 3:
        reasons.append("Fewer than three relevant student observations are available.")
    if not families:
        reasons.append("No repeated challenge-family evidence supports this hypothesis yet.")
    elif len(families) < 3:
        reasons.append("Evidence spans only a small number of distinct challenge families.")
    if newest_days is None:
        reasons.append("No dated, career-relevant evidence is available for a recency check.")
    elif newest_days > 90:
        reasons.append("The most recent relevant observation is older than 90 days; refresh it before relying on this hypothesis.")
    if contradiction:
        reasons.append("Student-labelled evidence contains a challenge/conflict; keep this as an open question and validate rather than switching the goal automatically.")
    if len(source_kinds) < 2:
        reasons.append("Relevant evidence comes from fewer than two source kinds.")
    if not reviewed:
        reasons.append("The occupation lacks a reviewed/verified source-reference status, or no references are available.")
    if not reasons:
        reasons.append("Evidence spans multiple activity families and source kinds and is recent enough for this provisional hypothesis; this is still not a prediction of career success.")
    detail = ConfidenceBreakdown(
        evidence_volume=volume_status,
        recency=recency_status,
        consistency=consistency_status,
        source_quality=source_status,
        coverage=coverage_status,
        explanation=" ".join(reasons),
    )
    return level, detail


def _choose_challenge(age_band: AgeBand, domains: list[str], evidence: list[EvidenceItem]) -> ValidatingAction:
    age = ChallengeAgeBand(age_band.value)
    tried = {_challenge_id(item) for item in evidence if _challenge_id(item)}
    domain_counts = Counter(item.domain for item in _activity_evidence(evidence) if item.domain)
    # Keep the authored mapping's order as the stable tie-break after exposure count. The first
    # mapped domain is the intended primary exploration context (e.g. design for Graphic Designers),
    # not a claim of higher fit. A zero-exposure tie should not make a design hypothesis prescribe
    # a generic technology task merely because that family appears earlier in the challenge catalog.
    mapped_order = {domain: index for index, domain in enumerate(dict.fromkeys(domains))}
    valid_domains = {item.value for item in ChallengeDomain}
    ordered_domains = sorted(
        {domain for domain in domains if domain in valid_domains},
        key=lambda domain: (domain_counts.get(domain, 0), mapped_order.get(domain, 999), domain),
    )
    if ordered_domains:
        # Preserve domain priority when building the candidate list. Filtering the global catalog
        # alone would retain its fixed order and could send a design hypothesis to a generic coding
        # task merely because technology challenges appear first in the catalog.
        candidates = [
            challenge
            for domain in ordered_domains
            for challenge in CHALLENGES
            if challenge.domain.value == domain
        ]
    else:
        candidates = list(CHALLENGES)
    if not candidates:
        candidates = list(CHALLENGES)
    unused = [challenge for challenge in candidates if challenge.challenge_id not in tried]
    chosen = (unused or candidates)[0]
    variant = next(item for item in chosen.age_variants if item.age_band == age)
    chosen_domain = chosen.domain.value
    return ValidatingAction(
        challenge_id=chosen.challenge_id,
        title=variant.title,
        domain=chosen_domain,
        expected_minutes=variant.expected_minutes,
        action=f"Complete “{variant.title}” and record observable notes for the rubric criteria. Leave any unobserved criterion unscored, then reflect on enjoyment, difficulty and whether you want to continue.",
        why_this_tests_the_hypothesis=(
            f"This short SkillScope-authored activity samples {DOMAIN_LABELS[chosen.domain]} with an explicit rubric. It tests a small aspect of the hypothesis; it cannot validate a career by itself."
        ),
    )


def _recommend_domain_hypotheses(
    profile: StudentProfile, evidence: list[EvidenceItem], evidence_total: int, limit: int,
    policy: dict[str, Any], domain_policy: dict[str, Any], graph_info: dict[str, Any],
) -> RecommendationSet:
    counts = Counter(item.domain for item in _activity_evidence(evidence) if item.domain)
    domains_ordered = sorted(
        list(ChallengeDomain),
        key=lambda domain: (counts.get(domain.value, 0), next((idx for idx, challenge in enumerate(CHALLENGES) if challenge.domain == domain), 999), domain.value),
    )[:limit]
    recs: list[CareerHypothesisRecommendation] = []
    for domain in domains_ordered:
        related = [item for item in evidence if item.domain == domain.value]
        observation_count, most_recent = _observation_summary(related)
        used = [_evidence_trace(item, "This record identifies the domain in which a student-chosen activity took place; it records exposure, not ability.") for item in related[:5]]
        level, breakdown = _confidence(related, [], date.today())
        recs.append(CareerHypothesisRecommendation(
            hypothesis_id=f"domain:{domain.value}",
            hypothesis_label=f"Explore {DOMAIN_LABELS[domain]}",
            recommendation_type="broad_domain_hypothesis",
            occupation_node_id=None,
            occupation=None,
            taxonomy=None,
            geography=None,
            category=RecommendationCategory.EXPLORE,
            support_level="early_exploration" if not related else "domain_exposure_recorded",
            evidence_confidence=level,
            confidence_breakdown=breakdown,
            rationale=[
                "For ages 10–14, SkillScope suggests broad activity domains rather than ranking specific careers.",
                "This domain is suggested to broaden exposure; an untried domain is unknown, not a weakness or low potential.",
                f"The current record contains {len(related)} activity-evidence item(s) in this domain; no aptitude or career-fit score is produced.",
            ],
            distinct_observation_count=observation_count,
            most_recent_observation_at=most_recent,
            evidence_detail_limit=5,
            matches=[RecommendationMatch(
                match_type="broad_domain_exposure", label=DOMAIN_LABELS[domain],
                explanation=f"{len(related)} recorded activity-evidence item(s) are associated with this domain. Exposure is not evidence of ability.",
                evidence_ids=[item.evidence_id for item in related[:5]], source_references=[],
            )] if related else [],
            evidence_used=used,
            evidence_gaps=[RecommendationGap(
                gap_type="unexplored_domain", label="Try a small activity first",
                explanation="No activity evidence is recorded for this domain. It is unknown/unexplored, not a negative signal.",
            )] if not related else [],
            source_backed_pathway_facts=[],
            next_validating_action=_choose_challenge(profile.age_band, [domain.value], evidence),
            source_record_count=0,
            source_quality_note="This is an original SkillScope exploration domain, not an official occupation classification.",
            important_limitations=[
                "Career names are intentionally withheld in this age band to avoid fixed labels or pressure to choose a career.",
                "Domain order reflects recorded exposure only; it does not rank talent, aptitude, interest, or future potential.",
            ],
        ))
    return RecommendationSet(
        profile_id=profile.profile_id, age_band=profile.age_band, current_goal=profile.current_goal,
        algorithm_version=policy["algorithm_version"], weights_status=policy["status"],
        weights=policy["weights"], domain_hypothesis_policy_version=domain_policy["policy_version"], recommendations=recs,
        evidence_count=evidence_total, evidence_count_is_truncated_for_detail=evidence_total > EVIDENCE_DETAIL_LIMIT,
        career_catalog_count=0, catalog_status="not_required_for_10_14_exploration",
        catalog_limitations=["This age band receives broad exploration prompts, not occupation rankings."],
        ordering_explanation="Broad domains are ordered by recorded activity exposure from least to most exposed; equal counts use stable challenge-library order. This is not a strength ranking.",
        global_notices=[domain_policy["notice"], "No probabilities or fit percentages are returned. Evidence missing from this profile remains unknown."],
    )


def build_recommendation_set(
    profile: StudentProfile,
    evidence: list[EvidenceItem],
    evidence_total: int,
    career_cards: list[dict[str, Any]],
    graph_info: dict[str, Any],
    *,
    limit: int = 5,
    policy: dict[str, Any] | None = None,
    domain_policy: dict[str, Any] | None = None,
    today: date | None = None,
) -> RecommendationSet:
    """Pure recommendation projection; same inputs, policy and evaluation date => same output."""
    policy = policy or load_recommendation_policy()
    domain_policy = domain_policy or load_domain_policy()
    today = today or datetime.now(UTC).date()
    if profile.age_band == AgeBand.AGE_10_14:
        return _recommend_domain_hypotheses(profile, evidence, evidence_total, limit, policy, domain_policy, graph_info)

    weights = policy["weights"]
    activity_items = _activity_evidence(evidence)
    portfolio = _portfolio_items(evidence)
    total_domain_evidence = bool(activity_items)
    have_rubric_evidence = any(item.evidence_type == EvidenceType.CHALLENGE_PERFORMANCE and item.rubric_observations for item in evidence)
    have_portfolio = bool(portfolio)
    goal_supplied = bool(profile.current_goal and profile.current_goal.strip())
    candidate_rows: list[tuple[float, int, CareerHypothesisRecommendation]] = []
    for source_order, career in enumerate(career_cards):
        mapping = _career_mapping(career, domain_policy)
        domains = list(mapping["domains"]) if mapping else []
        related = [item for item in evidence if item.domain in domains]
        related_challenges = [item for item in activity_items if item.domain in domains]
        related_families = {_challenge_id(item) for item in related_challenges if _challenge_id(item)}
        skill_matches = _get_skill_matches(career, evidence)
        goal_score, goal_tokens = _goal_overlap(profile.current_goal, career)
        portfolio_score, portfolio_tokens, portfolio_items = _portfolio_overlap(career, portfolio)
        goal_evidence = [
            item for item in evidence
            if goal_supplied and (item.evidence_type == EvidenceType.STATED_INTEREST_GOAL or item.signal_dimension == SignalDimension.GOAL_PREFERENCE)
            and str(profile.current_goal).casefold() in item.observation.casefold()
        ]

        features: dict[str, float | None] = {
            "goal_language_overlap": goal_score if goal_supplied else None,
            "exact_skill_label_overlap": (len(skill_matches) / max(1, len(career.get("skills", [])))) if have_rubric_evidence and career.get("skills") else None,
            "challenge_domain_alignment": (
                len({item.domain for item in related_challenges if item.domain}) / max(1, len(domains))
                if total_domain_evidence and domains else None
            ),
            "repeated_activity_families": min(1.0, len(related_families) / 3.0) if total_domain_evidence and domains else None,
            "portfolio_context_overlap": portfolio_score if have_portfolio else None,
        }
        active_weight_sum = sum(float(weights[name]) for name, value in features.items() if value is not None)
        internal_ordering_score = (
            sum(float(weights[name]) * float(value) for name, value in features.items() if value is not None) / active_weight_sum
            if active_weight_sum else 0.0
        )

        source_quality, source_quality_note, career_sources = _source_quality(career)
        citations = career_sources
        facts = _pathway_facts(career)
        label = str(career.get("label") or "Unlabelled occupation hypothesis")
        title_match = bool(goal_tokens)
        positive_related = any(item.user_interpretation == UserInterpretation.SUPPORTS_CURRENT_HYPOTHESIS for item in related)
        challenge_related = any(item.user_interpretation == UserInterpretation.CHALLENGES_CURRENT_HYPOTHESIS for item in related)
        related_latest = max((_parse_datetime(item.observed_at) for item in related if _parse_datetime(item.observed_at)), default=None)
        old_related = bool(related_latest and (today - related_latest.date()).days > 90)
        distinct_relevant_signals = {item.signal_dimension.value for item in related}

        if title_match and (challenge_related or old_related):
            category = RecommendationCategory.RECONSIDER_REFRESH
            category_reason = "Your stated goal overlaps with this source-listed occupation, but related evidence is conflicting or old enough to refresh. This flags a question; it does not automatically change your goal."
        elif title_match and (len(related) >= 2 and (len(related_families) >= 2 or portfolio_items) and len(distinct_relevant_signals) >= 1):
            category = RecommendationCategory.DEVELOP
            category_reason = "Your stated goal overlaps with this occupation and some relevant activity/experience evidence is available. Develop a practical next step while keeping the hypothesis revisable."
        elif title_match:
            category = RecommendationCategory.CHALLENGE
            category_reason = "Your stated goal wording overlaps with the occupation label. A small validation activity is more appropriate than treating that wording as proof of fit."
        elif positive_related or (related_challenges and any(
            (item.context or {}).get("willingness_to_continue") is not None and float((item.context or {}).get("willingness_to_continue") or 0) >= 4
            for item in related_challenges
        )):
            category = RecommendationCategory.ALTERNATIVE_TO_CONSIDER
            category_reason = "Some student-labelled or engagement evidence exists in a domain this source-linked profile may touch. Consider it as an alternative to test, not as a hidden goal change."
        elif old_related:
            category = RecommendationCategory.RECONSIDER_REFRESH
            category_reason = "Related evidence is older than 90 days; refresh it with a small activity before relying on the earlier observation."
        else:
            category = RecommendationCategory.EXPLORE
            category_reason = "There is not yet a direct current-goal overlap or a clear domain signal for this candidate. It remains an exploratory option, not a low-potential result."

        confidence_related = list(related)
        for item in skill_matches:
            for evidence_item in item[1]:
                if evidence_item not in confidence_related:
                    confidence_related.append(evidence_item)
        for item in portfolio_items:
            if item not in confidence_related:
                confidence_related.append(item)
        for item in goal_evidence:
            if item not in confidence_related:
                confidence_related.append(item)
        confidence_level, confidence_breakdown = _confidence(confidence_related, citations, today)
        observation_count, most_recent = _observation_summary(confidence_related)

        matches: list[RecommendationMatch] = []
        if goal_supplied:
            if title_match:
                matches.append(RecommendationMatch(
                    match_type="goal_language_overlap", label=f"Shared occupation-label terms: {', '.join(goal_tokens)}",
                    explanation="These words overlap between your current goal and the source-linked occupation label. This is a wording clue only, not evidence of fit or skill.",
                    evidence_ids=[item.evidence_id for item in goal_evidence[:3]], source_references=citations[:2],
                ))
            else:
                # No exact title wording match is not itself a mismatch in potential.
                pass
        for skill_label, skill_items in skill_matches[:5]:
            skill_node = next((item for item in career.get("skills", []) if item.get("label") == skill_label), None)
            skill_sources = [_source_model(source) for source in (skill_node or {}).get("source_references", [])]
            matches.append(RecommendationMatch(
                match_type="exact_skill_label_overlap", label=skill_label,
                explanation="The exact source skill label appears in a recorded rubric observation or user-provided evidence text. Text overlap is not proof of proficiency.",
                evidence_ids=[item.evidence_id for item in skill_items[:5]], source_references=skill_sources[:3],
            ))
        if related:
            match_domain_labels = _unique_strings([DOMAIN_LABELS[ChallengeDomain(item.domain)] for item in related if item.domain in {d.value for d in ChallengeDomain}])
            matches.append(RecommendationMatch(
                match_type="authored_domain_hypothesis", label=", ".join(match_domain_labels),
                explanation=(mapping or {}).get("basis", "No SkillScope-authored domain hypothesis is available for this record."),
                evidence_ids=[item.evidence_id for item in related[:8]], source_references=citations[:2],
            ))
        if portfolio_tokens:
            matches.append(RecommendationMatch(
                match_type="portfolio_text_overlap", label=f"Shared terms: {', '.join(portfolio_tokens[:8])}",
                explanation="Terms co-occur in a voluntary project/portfolio description and the source-linked occupation profile. This is lexical context, not a quality judgment.",
                evidence_ids=[item.evidence_id for item in portfolio_items[:5]], source_references=citations[:2],
            ))

        gaps: list[RecommendationGap] = []
        if not related_challenges:
            gaps.append(RecommendationGap(
                gap_type="unexplored_or_unrecorded_domain", label="No related challenge evidence recorded yet",
                explanation=(f"No challenge evidence has been recorded in the authored domain hints for this profile ({', '.join(DOMAIN_LABELS[ChallengeDomain(d)] for d in domains if d in {x.value for x in ChallengeDomain}) or 'no mapped domains'}). Unknown is not low ability or low potential."),
            ))
        if career.get("skills") and not skill_matches:
            gaps.append(RecommendationGap(
                gap_type="unobserved_exact_skill_label", label="No exact sourced skill label found in evidence text",
                explanation="The recorded observations do not currently contain an exact match for this occupation's source skill labels. This may reflect limited evidence or different wording; it is not a skill-deficiency judgment.",
            ))
        if not portfolio:
            gaps.append(RecommendationGap(
                gap_type="portfolio_not_shared", label="No project/portfolio evidence shared yet",
                explanation="No voluntary project/portfolio record is present in this profile. This does not imply that the student lacks experience.",
            ))
        if not facts:
            gaps.append(RecommendationGap(
                gap_type="pathway_source_gap", label="No source-backed task facts available for this occupation",
                explanation="The active graph did not expose attributable work-activity facts for this record; the engine will not invent role requirements.",
            ))
        gaps.append(RecommendationGap(
            gap_type="qualification_pathway_not_integrated", label="Formal qualification pathway not available in the current graph",
            explanation="The current curated graph does not establish a sourced prerequisite, credential or education pathway for this occupation. Check applicable local requirements separately.",
        ))
        if old_related:
            gaps.append(RecommendationGap(
                gap_type="refresh_older_evidence", label="Refresh old evidence",
                explanation="The most recent relevant evidence is older than 90 days; one new activity can test whether the earlier observation still reflects the student's current view.",
            ))

        used_ids: set[UUID] = set()
        evidence_used: list[RecommendationEvidenceReference] = []
        for item in sorted(confidence_related, key=lambda x: x.observed_at, reverse=True):
            if item.evidence_id in used_ids:
                continue
            used_ids.add(item.evidence_id)
            why = "Recorded in a challenge domain included in a SkillScope-authored exploration hypothesis for this occupation. It indicates exposure, not ability."
            if item.evidence_type == EvidenceType.PROJECT_PORTFOLIO:
                why = "Voluntary project/portfolio description used only for contextual term overlap and evidence coverage."
            if any(item in hit[1] for hit in skill_matches):
                why = "Exact source skill label occurs in this recorded text; the system does not infer proficiency from term presence."
            if item.user_interpretation == UserInterpretation.CHALLENGES_CURRENT_HYPOTHESIS:
                why = "Student explicitly labelled this activity as challenging the current hypothesis; retain the conflict as an open question."
            evidence_used.append(_evidence_trace(item, why))
            if len(evidence_used) >= 8:
                break

        reason_lines = [category_reason]
        if mapping:
            reason_lines.append(f"Domain hints are a SkillScope-authored hypothesis: {mapping['basis']}")
        if title_match:
            reason_lines.append("The current goal shares wording with the occupation title; wording overlap is not a career-fit score.")
        if not title_match and goal_supplied:
            reason_lines.append("No distinctive word overlap was found with the occupation title. This does not rule the occupation out; the catalog is small and vocabulary-sensitive.")
        reason_lines.append(confidence_breakdown.explanation)
        if source_quality == QualitativeStatus.REVIEWED:
            reason_lines.append("Occupational task facts below retain their source reference and geography.")

        validating_domains = domains or [item.value for item in ChallengeDomain]
        rec = CareerHypothesisRecommendation(
            hypothesis_id=f"occupation:{career.get('node_id')}",
            hypothesis_label=label,
            recommendation_type="occupation_hypothesis",
            occupation_node_id=str(career.get("node_id") or ""),
            occupation=label,
            taxonomy=career.get("taxonomy"),
            geography=career.get("geography"),
            category=category,
            support_level=("multiple_signals" if len(confidence_related) >= 3 and len({item.source_kind.value for item in confidence_related}) >= 2 else "emerging" if confidence_related else "tentative"),
            evidence_confidence=confidence_level,
            confidence_breakdown=confidence_breakdown,
            rationale=reason_lines,
            matches=matches,
            distinct_observation_count=observation_count,
            most_recent_observation_at=most_recent,
            evidence_detail_limit=8,
            evidence_used=evidence_used,
            evidence_gaps=gaps,
            source_backed_pathway_facts=facts,
            next_validating_action=_choose_challenge(profile.age_band, validating_domains, evidence),
            source_record_count=len(citations),
            source_quality_note=(source_quality_note + " Geographic context is reported from the source profile and may not represent the user's local labour market."),
            important_limitations=[
                "Recommendations are hypotheses and are not probabilities, psychometric results, or predictions of success.",
                "Internal ordering uses versioned initial heuristic weights; the weights are not scientifically optimized.",
                "Skill-label overlap requires exact wording and cannot prove proficiency; missing or differently worded evidence remains unknown.",
                "The graph contains small curated static occupational extracts, not full O*NET/ESCO catalogues or India-specific demand/salary/qualification data.",
                "Cross-taxonomy occupation records remain separate; the engine does not collapse related records into one occupation identity.",
                domain_policy["notice"],
            ],
        )
        candidate_rows.append((internal_ordering_score, source_order, rec))

    # Stable deterministic tie break: internal heuristic value descending, then graph order and ID.
    candidate_rows.sort(key=lambda row: (-row[0], row[1], row[2].hypothesis_id))
    recommendations = [row[2] for row in candidate_rows[:limit]]
    status = str(graph_info.get("status", "unknown"))
    limitations = list(graph_info.get("limitations") or [])
    return RecommendationSet(
        profile_id=profile.profile_id,
        age_band=profile.age_band,
        current_goal=profile.current_goal,
        algorithm_version=policy["algorithm_version"],
        weights_status=policy["status"],
        weights=policy["weights"], domain_hypothesis_policy_version=domain_policy["policy_version"],
        recommendations=recommendations,
        evidence_count=evidence_total,
        evidence_count_is_truncated_for_detail=evidence_total > EVIDENCE_DETAIL_LIMIT,
        career_catalog_count=len(career_cards),
        catalog_status=status,
        catalog_limitations=limitations + ["The active career catalog is not guaranteed to be comprehensive or local to the student."],
        ordering_explanation=(
            "Ordering uses configurable, initial heuristic weights over currently usable inputs; components absent from the profile are omitted and active weights are renormalized. It is not a probability or career-fit percentage. An unobserved domain or skill is unknown—not a negative ability signal."
        ),
        global_notices=[
            "The recommendations are evolving hypotheses, not career verdicts. Students can correct their evidence and goals.",
            "No aggregate labour-market statistic is used to score an individual student.",
            "This snapshot does not provide a validated India-specific qualification pathway, salary, demand forecast or employment guarantee.",
            domain_policy["notice"],
        ],
    )


class RecommendationRepository:
    """Read the persistent profile/evidence ledger and the active, fresh career graph."""

    def __init__(self, db_path=None, *, career_provider: Callable[..., list[dict[str, Any]]] | None = None,
                 graph_status_provider: Callable[..., dict[str, Any]] | None = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.evidence = EvidenceLedgerRepository(self.db_path)
        self.provenance = ProvenanceRepository(self.db_path)
        self.career_provider = career_provider or list_career_cards
        self.graph_status_provider = graph_status_provider or graph_status
        with connect_sqlite(self.db_path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS recommendation_snapshots (
                snapshot_id TEXT PRIMARY KEY,
                profile_id TEXT NOT NULL,
                algorithm_version TEXT NOT NULL,
                generated_at TEXT NOT NULL,
                evidence_count INTEGER NOT NULL CHECK(evidence_count >= 0),
                catalog_status TEXT NOT NULL,
                source_keys_json TEXT NOT NULL DEFAULT '[]',
                snapshot_json TEXT NOT NULL,
                FOREIGN KEY(profile_id) REFERENCES student_profiles(profile_id) ON DELETE CASCADE
            )""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_recommendation_snapshots_profile_generated ON recommendation_snapshots(profile_id, generated_at DESC, snapshot_id)")

    def _validate_recommendation_lineage(self, result: RecommendationSet) -> list[str]:
        """Fail closed if a response cites evidence or sources that do not resolve internally."""
        source_keys: set[str] = set()
        evidence_ids: set[str] = set()
        for recommendation in result.recommendations:
            evidence_ids.update(str(item.evidence_id) for item in recommendation.evidence_used)
            for match in recommendation.matches:
                evidence_ids.update(str(item) for item in match.evidence_ids)
            sources = [item.source for item in recommendation.source_backed_pathway_facts]
            for match in recommendation.matches:
                sources.extend(match.source_references)
            for source in sources:
                if source.source_id == "unknown" or source.source_record_id == "unknown":
                    raise RecommendationCatalogError("A recommendation contains a source without an internal source-record identity.", 503)
                source_keys.add(f"{source.source_id}:{source.source_record_id}")
                with connect_sqlite(self.db_path) as db:
                    internal_source = db.execute(
                        "SELECT source_uri,record_uri FROM source_records WHERE source_id=? AND source_record_id=?",
                        (source.source_id, source.source_record_id),
                    ).fetchone()
                    if internal_source is None:
                        raise RecommendationCatalogError(
                            "A recommendation source reference is missing from the internal provenance registry. Rebuild the curated graph before retrying.", 503
                        )
                    # A registry row without an original source URI is not auditable enough to
                    # back a career fact. Link-only source records may use source_uri when a
                    # record-specific URI is unavailable.
                    if not (internal_source["record_uri"] or internal_source["source_uri"]):
                        raise RecommendationCatalogError(
                            "An internal source record has no original source URI. Review its provenance before retrying.", 503
                        )
        if evidence_ids:
            placeholders = ",".join("?" for _ in evidence_ids)
            with connect_sqlite(self.db_path) as db:
                rows = db.execute(
                    f"SELECT evidence_id FROM student_evidence_items WHERE profile_id=? AND evidence_id IN ({placeholders})",
                    (str(result.profile_id), *sorted(evidence_ids)),
                ).fetchall()
            resolved = {str(row["evidence_id"]) for row in rows}
            if resolved != evidence_ids:
                raise RecommendationCatalogError("A recommendation references evidence that does not belong to this profile.", 503)
        return sorted(source_keys)

    def _persist_snapshot(self, result: RecommendationSet, source_keys: list[str]) -> None:
        from uuid import uuid4
        generated_at = datetime.now(UTC).replace(microsecond=0).isoformat()
        payload = result.model_dump(mode="json")
        with connect_sqlite(self.db_path) as db:
            db.execute(
                """INSERT INTO recommendation_snapshots(
                    snapshot_id,profile_id,algorithm_version,generated_at,evidence_count,catalog_status,source_keys_json,snapshot_json
                ) VALUES(?,?,?,?,?,?,?,?)""",
                (str(uuid4()), str(result.profile_id), result.algorithm_version, generated_at,
                 result.evidence_count, result.catalog_status, json.dumps(source_keys, sort_keys=True),
                 json.dumps(payload, ensure_ascii=False, sort_keys=True)),
            )

    def get_history(self, profile_id: str | UUID, *, limit: int = 20) -> list[dict[str, Any]] | None:
        if self.evidence.get_profile(profile_id) is None:
            return None
        with connect_sqlite(self.db_path) as db:
            rows = db.execute(
                """SELECT snapshot_id,algorithm_version,generated_at,evidence_count,catalog_status,source_keys_json
                   FROM recommendation_snapshots WHERE profile_id=? ORDER BY generated_at DESC,snapshot_id DESC LIMIT ?""",
                (str(profile_id), limit),
            ).fetchall()
        return [{"snapshot_id": row["snapshot_id"], "profile_id": str(profile_id),
                 "algorithm_version": row["algorithm_version"], "generated_at": row["generated_at"],
                 "evidence_count": int(row["evidence_count"]), "catalog_status": row["catalog_status"],
                 "source_keys": json.loads(row["source_keys_json"])} for row in rows]

    def get_recommendations(self, profile_id: str | UUID, *, limit: int = 5) -> RecommendationSet | None:
        profile = self.evidence.get_profile(profile_id)
        if profile is None:
            return None
        evidence, total = self.evidence.list_evidence(profile.profile_id, limit=EVIDENCE_DETAIL_LIMIT)
        graph_info = self.graph_status_provider(db_path=self.db_path)
        policy = load_recommendation_policy()
        domain_policy = load_domain_policy()
        if profile.age_band != AgeBand.AGE_10_14:
            if graph_info.get("status") != "ready":
                raise RecommendationCatalogError(
                    "The career knowledge graph is not built. Run the documented curated import and graph rebuild commands before requesting occupation hypotheses.", 503
                )
            if graph_info.get("is_stale"):
                raise RecommendationCatalogError(
                    "The career knowledge graph is stale relative to active source snapshots. Rebuild it before requesting occupation hypotheses.", 409
                )
            careers = self.career_provider(db_path=self.db_path, limit=200, offset=0)
        else:
            # Broad exploration for 10-14 intentionally works without loading career labels.
            careers = []
        result = build_recommendation_set(
            profile, evidence, total, careers, graph_info, limit=limit, policy=policy, domain_policy=domain_policy,
        )
        source_keys = self._validate_recommendation_lineage(result)
        self._persist_snapshot(result, source_keys)
        return result
