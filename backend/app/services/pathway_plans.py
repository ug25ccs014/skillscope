"""Age-aware career pathway and action-plan engine with persistent revision history.

The engine turns the Stage 12 hypotheses into practical, editable steps. It does not invent
qualification requirements, salaries, employment outlook, or career-success probabilities.
"""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable
from uuid import UUID, uuid4

from app.schemas.pathway_plans import (
    DesiredTimeline,
    PathwayOption,
    PathwayPlan,
    PathwayPlanHistoryItem,
    PlanAction,
    PlanInput,
    PlanRequirement,
    SkillEvidenceGap,
    TimeboxAssessment,
)
from app.schemas.recommendations import RecommendationSet, RecommendationSource
from app.schemas.student_evidence import AgeBand, EvidenceItem, StudentProfileUpdate
from app.services.evidence_ledger import DEFAULT_DB_PATH, EvidenceLedgerRepository
from app.services.knowledge_graph import list_career_cards
from app.services.recommendations import RecommendationCatalogError, RecommendationRepository

ALGORITHM_VERSION = "career-pathway-action-plan-v1.0"
MODE_BY_AGE = {
    AgeBand.AGE_10_14: "discover_and_shape",
    AgeBand.AGE_15_17: "explore_and_validate",
    AgeBand.AGE_18_PLUS: "develop_and_optimize",
}
ADULT_ONLY_FIELDS = {
    "current_skills_summary", "education_summary", "experience_summary",
    "planning_constraints", "available_hours_per_week", "desired_timeline",
}


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


def _phrase_present(phrase: str, text: str) -> bool:
    """Case-insensitive phrase containment; avoid loose bag-of-words skill matching."""
    if not phrase.strip() or not text.strip():
        return False
    escaped = re.escape(" ".join(phrase.casefold().split()))
    flexible = escaped.replace(r"\ ", r"\s+")
    return re.search(rf"(?<![\w]){flexible}(?![\w])", text.casefold()) is not None


def _source_refs(fact: Any) -> list[RecommendationSource]:
    source = getattr(fact, "source", None)
    return [source] if isinstance(source, RecommendationSource) else []


def _action(
    *, index: int, phase: str, kind: str, title: str, why: str, instructions: list[str],
    outcome: str, horizon_days: int | None = None, horizon_label: str | None = None,
    hours: tuple[float, float] | None = None, skills: list[str] | None = None,
    evidence_ids: list[UUID] | None = None, sources: list[RecommendationSource] | None = None,
    prerequisite_status: str = "not_assessed", prerequisite_note: str = "No formal prerequisite is inferred by this action.",
    origin: str = "skillscope_authored",
) -> PlanAction:
    return PlanAction(
        step_id=f"step-{index:02d}", order=index, phase=phase, time_horizon_days=horizon_days,
        time_horizon_label=horizon_label, action_type=kind, title=title, why_this_step=why,
        instructions=instructions, expected_outcome=outcome,
        estimated_hours_min=hours[0] if hours else None, estimated_hours_max=hours[1] if hours else None,
        skill_labels=skills or [], evidence_ids=evidence_ids or [], source_references=sources or [],
        prerequisite_status=prerequisite_status, prerequisite_note=prerequisite_note, action_origin=origin,
    )


def _recommendation_labels(rec: Any) -> list[str]:
    labels: list[str] = []
    for match in rec.matches:
        label = getattr(match, "label", None)
        if label and label.casefold() not in {x.casefold() for x in labels}:
            labels.append(label)
    return labels[:8]


def _unknowns(rec: Any) -> list[str]:
    result = [f"{gap.label}: {gap.explanation}" for gap in rec.evidence_gaps]
    if not result:
        result = ["There is not yet enough evidence to treat this hypothesis as settled; use a small validating activity."]
    return result[:8]


def _unique_sources(values: list[RecommendationSource]) -> list[RecommendationSource]:
    seen: set[tuple[str, str]] = set()
    result: list[RecommendationSource] = []
    for item in values:
        key = (item.source_id, item.source_record_id)
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _pathway_options(recommendations: RecommendationSet, limit: int = 3) -> list[PathwayOption]:
    recs = list(recommendations.recommendations)
    if not recs:
        return []
    selected = recs[:limit]
    # Include a source-supported adjacent/alternative option when the catalog has one, instead
    # of showing only goal-aligned possibilities by default. Keep source/category labels intact.
    if len(selected) >= 2 and not any(r.category.value == "alternative_to_consider" for r in selected):
        alternative = next((r for r in recs[limit:] if r.category.value == "alternative_to_consider"), None)
        if alternative is not None:
            selected[-1] = alternative
    options: list[PathwayOption] = []
    for rec in selected:
        validation: list[PlanAction] = []
        task = rec.next_validating_action
        if task:
            validation.append(_action(
                index=1, phase="Validate", kind="validate", title=task.title,
                why=task.why_this_tests_the_hypothesis,
                instructions=[task.action, "Record what was actually observed, what was enjoyable or difficult, and what remains unknown."],
                outcome="One challenge result and a student-led interpretation that can be compared with later activities.",
                hours=(max(0.25, (task.expected_minutes or 15) / 60), max(0.5, (task.expected_minutes or 15) / 30)),
                skills=_recommendation_labels(rec), evidence_ids=[item.evidence_id for item in rec.evidence_used[:8]],
                sources=_unique_sources([src for fact in rec.source_backed_pathway_facts for src in _source_refs(fact)]),
                prerequisite_status="none_identified", prerequisite_note="This exploratory task has no formal credential prerequisite recorded.",
                origin="source_informed" if rec.source_backed_pathway_facts else "skillscope_authored",
            ))
        if rec.source_backed_pathway_facts:
            fact = rec.source_backed_pathway_facts[0]
            validation.append(_action(
                index=2, phase="Build a small example", kind="build",
                title="Make a small project inspired by a source-listed work activity",
                why="A small, low-risk project can show whether the activity is interesting and help identify what support or skills you still need.",
                instructions=[
                    f"Use this occupational work context as inspiration: {fact.statement}",
                    "Choose a small fictional, classroom, or personal example; do not handle confidential data or deploy anything affecting real people.",
                    "Keep a short note of the method, decisions, output, feedback, and what you would change next time.",
                ],
                outcome="A small inspectable artifact or explanation, plus a note about what was and was not tested.",
                hours=(1.0, 3.0), skills=_recommendation_labels(rec),
                sources=_source_refs(fact), prerequisite_status="not_assessed",
                prerequisite_note="The source fact describes work activity, not an entry requirement or credential.", origin="source_informed",
            ))
        options.append(PathwayOption(
            pathway_id=rec.hypothesis_id,
            label=rec.occupation or rec.hypothesis_label,
            occupation_node_id=rec.occupation_node_id,
            taxonomy=rec.taxonomy,
            geography=rec.geography,
            recommendation_category=rec.category.value,
            evidence_confidence=rec.evidence_confidence.value,
            why_plausible=list(rec.rationale[:5]),
            skill_or_interest_matches=_recommendation_labels(rec),
            what_remains_unknown=_unknowns(rec),
            pathway_facts=list(rec.source_backed_pathway_facts[:4]),
            validation_actions=validation,
            comparison_note="This is one option to test, not a permanent choice or a ranking by prestige. Compare the evidence, unknowns, practical context, and your own response across alternatives.",
        ))
    return options


def _requirement_catalog(recommendations: RecommendationSet, career_cards: list[dict[str, Any]]) -> list[PlanRequirement]:
    requirements: list[PlanRequirement] = []
    seen: set[tuple[str, str]] = set()
    selected_nodes = {r.occupation_node_id for r in recommendations.recommendations if r.occupation_node_id}
    for card in career_cards:
        if card.get("node_id") not in selected_nodes:
            continue
        for relationship in card.get("relationships", []) or []:
            if relationship.get("relation_type") != "requires_qualification":
                continue
            label = str(relationship.get("to_label") or relationship.get("label") or "Qualification requirement").strip()
            sources = relationship.get("source_references") or []
            key = (label.casefold(), json.dumps(sources, sort_keys=True, default=str))
            if key in seen:
                continue
            seen.add(key)
            source_models = []
            for source in sources:
                try:
                    source_models.append(RecommendationSource.model_validate(source))
                except Exception:
                    continue
            # A stale, conflicted, unverified, or source-less qualification relationship must not
            # become a formal prerequisite just because a label exists in a graph edge.
            acceptable = bool(source_models) and all(
                item.quality_status.casefold() in {"reviewed", "verified"}
                and bool(item.record_uri)
                for item in source_models
            )
            if acceptable:
                requirements.append(PlanRequirement(
                    label=label, status="source_backed_requirement",
                    statement=f"The active graph contains a source-linked qualification relationship to: {label}.",
                    is_prerequisite=True, source_references=source_models,
                    limitations=["Confirm current applicability, geography, and entry context directly with the source or an appropriate adviser."],
                ))
            else:
                requirements.append(PlanRequirement(
                    label=label, status="not_available_in_catalog",
                    statement=(
                        f"A graph relationship mentions {label}, but its qualification status is not supported by a current, reviewed source. "
                        "It is retained for verification and is not asserted as a current prerequisite."
                    ),
                    is_prerequisite=None, source_references=source_models,
                    limitations=[
                        "Verify the exact qualification name, issuer, geography, version/status and current official record before using it.",
                        "An absent source reference or stale/conflicted/unverified source is not evidence of a current requirement.",
                    ],
                ))
    for rec in recommendations.recommendations[:3]:
        for fact in rec.source_backed_pathway_facts[:3]:
            key = (fact.statement.casefold(), fact.source.source_record_id)
            if key in seen:
                continue
            seen.add(key)
            requirements.append(PlanRequirement(
                label="Source-listed work context", status="source_backed_work_context",
                statement=fact.statement, is_prerequisite=False, source_references=[fact.source],
                limitations=["This is listed occupational work context, not a formal qualification or entry prerequisite."],
            ))
    if not any(item.status == "source_backed_requirement" for item in requirements):
        requirements.append(PlanRequirement(
            label="Formal prerequisites and credentials", status="not_available_in_catalog",
            statement="The active curated catalog does not provide a verified, complete qualification pathway for these hypotheses. Confirm entry requirements with the relevant official education or professional authority before committing to a course or credential.",
            is_prerequisite=None, source_references=[],
            limitations=["No credential or prerequisite has been invented from a work-activity description.", "This checkpoint does not include verified India-specific admission, licensing, or qualification pathways."],
        ))
    return requirements[:30]


def _skill_gap_analysis(
    recommendations: RecommendationSet, career_cards: list[dict[str, Any]], request: PlanInput,
    evidence: list[EvidenceItem],
) -> list[SkillEvidenceGap]:
    if not recommendations.recommendations:
        return []
    selected_ids = {r.occupation_node_id for r in recommendations.recommendations[:3] if r.occupation_node_id}
    user_context = " ".join(filter(None, [request.current_skills_summary, request.education_summary, request.experience_summary]))
    evidence_context = " ".join(
        [f"{item.title} {item.observation} " + " ".join(obs.criterion + " " + obs.observation for obs in item.rubric_observations) for item in evidence]
    )
    results: list[SkillEvidenceGap] = []
    seen: set[str] = set()
    for card in career_cards:
        if card.get("node_id") not in selected_ids:
            continue
        for skill in card.get("skills", []) or []:
            label = str(skill.get("label") or "").strip()
            if not label or label.casefold() in seen:
                continue
            seen.add(label.casefold())
            refs: list[RecommendationSource] = []
            for source in skill.get("source_references", []) or []:
                try:
                    refs.append(RecommendationSource.model_validate(source))
                except Exception:
                    continue
            if _phrase_present(label, user_context):
                status = "self_reported_in_current_state"
                explanation = "This skill label appears in your self-described skills, education, or experience context. That is useful context, not verified proficiency."
            elif _phrase_present(label, evidence_context):
                status = "mentioned_in_evidence"
                explanation = "This label appears in saved evidence. The observation may be task-specific and should not be treated as a general proficiency rating."
            else:
                status = "not_yet_documented"
                explanation = "This source-listed skill is not mentioned in the current context or saved evidence. It may be unfamiliar or simply unrecorded; do not treat it as a demonstrated deficit."
            results.append(SkillEvidenceGap(skill_label=label, status=status, explanation=explanation, source_references=_unique_sources(refs)))
            if len(results) >= 18:
                return results
    return results


def _timebox(profile_age: AgeBand, request: PlanInput, goal: str | None) -> tuple[TimeboxAssessment, list[int]]:
    if profile_age == AgeBand.AGE_10_14:
        return TimeboxAssessment(
            status="not_applicable_age_mode", requested_timeline=request.desired_timeline,
            explanation="The younger-student mode gives one manageable next activity and avoids deadline pressure or high-stakes career commitments.",
            missing_inputs=[], available_hours_per_week=None,
        ), []
    if profile_age == AgeBand.AGE_15_17:
        return TimeboxAssessment(
            status="not_applicable_age_mode", requested_timeline=request.desired_timeline,
            explanation="This mode focuses on comparing and validating a small number of possibilities, not setting a pressured career timeline.",
            missing_inputs=[], available_hours_per_week=None,
        ), []
    missing: list[str] = []
    if not goal:
        missing.append("a clearly stated target goal")
    if not any(_clean(x) for x in (request.current_skills_summary, request.education_summary, request.experience_summary)):
        missing.append("at least one current-state input (skills, education, or experience)")
    if request.available_hours_per_week is None:
        missing.append("available hours per week")
    if request.desired_timeline == DesiredTimeline.UNSPECIFIED:
        missing.append("a desired timeline")
    if missing:
        return TimeboxAssessment(
            status="missing_inputs", requested_timeline=request.desired_timeline,
            explanation="A time-bounded plan is withheld until the target, current state, capacity, and timeline are explicit. The plan still provides untimed, ordered next steps.",
            missing_inputs=missing, available_hours_per_week=request.available_hours_per_week,
        ), []
    days_by_timeline = {
        DesiredTimeline.DAYS_30: [7, 15, 30],
        DesiredTimeline.DAYS_60: [14, 30, 60],
        DesiredTimeline.DAYS_90: [30, 60, 90],
        DesiredTimeline.MONTHS_6: [30, 90, 180],
        DesiredTimeline.MONTHS_12: [30, 90, 365],
    }
    days = days_by_timeline[request.desired_timeline]
    return TimeboxAssessment(
        status="time_bounded", requested_timeline=request.desired_timeline,
        explanation=f"Milestones are suggested for a {request.desired_timeline.value.replace('_', ' ')} horizon, using the stated weekly capacity of {request.available_hours_per_week} hour(s). Dates are planning prompts, not outcome predictions or guarantees.",
        missing_inputs=[], available_hours_per_week=request.available_hours_per_week,
    ), days


def _time_hours(request: PlanInput, default: tuple[float, float]) -> tuple[float, float]:
    weekly = request.available_hours_per_week
    if weekly is None:
        return default
    if weekly <= 3:
        return (min(default[0], 1.0), min(default[1], 2.0))
    if weekly <= 8:
        return (min(default[0], 2.0), min(default[1], 4.0))
    return default


def build_pathway_plan(
    profile: Any, request: PlanInput, recommendations: RecommendationSet, evidence: list[EvidenceItem],
    career_cards: list[dict[str, Any]], *, previous_goal: str | None, goal_change_detected: bool,
    plan_id: UUID | None = None, created_at: datetime | None = None,
) -> PathwayPlan:
    """Pure plan builder separated from storage for deterministic unit tests."""
    age_band = profile.age_band
    goal = profile.current_goal
    now = created_at or datetime.now(UTC)
    options: list[PathwayOption] = []
    requirements: list[PlanRequirement] = []
    skills: list[SkillEvidenceGap] = []
    actions: list[PlanAction] = []
    timebox, target_days = _timebox(age_band, request, goal)
    career_cards = career_cards or []

    if age_band == AgeBand.AGE_10_14:
        # The Stage 12 engine intentionally returns domain hypotheses only for this age band.
        # Show just the next small activity; never surface occupations, rankings, or deadline pressure.
        used_domains: set[str] = set()
        selected = None
        for rec in recommendations.recommendations:
            domain = rec.next_validating_action.domain
            if domain not in used_domains:
                selected = rec
                break
        if selected is None and recommendations.recommendations:
            selected = recommendations.recommendations[0]
        if selected:
            task = selected.next_validating_action
            actions.append(_action(
                index=1, phase="Your next small exploration", kind="explore", title=task.title,
                why="Trying one short activity creates a useful starting point without asking you to choose a career.",
                instructions=[task.action, "Afterward, note what felt interesting, tricky, or worth trying again. You can skip or change your mind."],
                outcome="One small activity, an observable result, and a personal reflection.",
                hours=(max(0.25, (task.expected_minutes or 12) / 60), max(0.5, (task.expected_minutes or 12) / 30)),
                prerequisite_status="none_identified", prerequisite_note="No career, purchase, credential, or special equipment is required beyond the challenge's stated materials.",
                origin="skillscope_authored",
            ))
        limitations = [
            "Career occupation labels and high-stakes rankings are intentionally omitted for ages 10–14.",
            "The activity library is SkillScope-authored exploratory content and has not been validated as a psychometric assessment.",
        ]
    else:
        options = _pathway_options(recommendations, limit=3)
        if age_band == AgeBand.AGE_15_17:
            if options:
                actions.append(_action(
                    index=1, phase="Compare, do not commit", kind="review",
                    title="Compare two or three possibilities",
                    why="A small comparison makes assumptions and unknowns visible before investing heavily in one direction.",
                    instructions=[
                        "Read the rationale and unknowns for each option.",
                        "Choose one question you would like to test next; this is not a permanent career decision.",
                        "Compare interest, activity experience, access to materials/support, and what you would like to learn.",
                    ],
                    outcome="A short note naming the next question to test and why you chose it.", hours=(0.5, 1.0),
                    prerequisite_status="none_identified", prerequisite_note="No qualification or academic prerequisite is needed to compare exploratory options.", origin="skillscope_authored",
                ))
                actions.extend(options[0].validation_actions[:2])
            limitations = [
                "Pathways are hypotheses based on a small source catalog; investigate multiple options and discuss major education decisions with trusted adults or qualified advisers.",
                "No salary, job-demand forecast, admission probability, or employment guarantee is provided.",
            ]
        else:
            requirements = _requirement_catalog(recommendations, career_cards)
            skills = _skill_gap_analysis(recommendations, career_cards, request, evidence)
            if not goal:
                actions.append(_action(
                    index=1, phase="Clarify the target", kind="revise", title="Write or revise the outcome you want to work toward",
                    why="The plan cannot make a useful gap analysis without a target; a goal can be exploratory and may change later.",
                    instructions=["Describe a role, project type, course outcome, or capability you want to explore.", "Add a reason and what would count as a useful first milestone.", "Use the goal field above and recalculate whenever your direction changes."],
                    outcome="A target statement that can be revised against new evidence.", hours=(0.25, 0.5), origin="student_goal",
                ))
            primary = options[0] if options else None
            if primary and primary.validation_actions:
                challenge = primary.validation_actions[0]
                actions.append(_action(
                    index=len(actions) + 1, phase="Validate current assumptions", kind="validate",
                    title=challenge.title, why=challenge.why_this_step,
                    instructions=challenge.instructions, outcome=challenge.expected_outcome,
                    hours=_time_hours(request, (1.0, 3.0)), skills=challenge.skill_labels,
                    evidence_ids=challenge.evidence_ids, sources=challenge.source_references,
                    prerequisite_status=challenge.prerequisite_status, prerequisite_note=challenge.prerequisite_note,
                    origin=challenge.action_origin,
                ))
            task_fact = next((fact for option in options for fact in option.pathway_facts), None)
            if task_fact:
                actions.append(_action(
                    index=len(actions) + 1, phase="Build evidence", kind="build",
                    title="Create one small project artifact",
                    why="A small project creates a concrete example to inspect and reflect on; it does not need to prove that a career is right for you.",
                    instructions=[
                        f"Use this source-listed activity as context: {task_fact.statement}",
                        "Define a small scope that fits your time and resources, then make a prototype, analysis, explanation, or other visible output.",
                        "Write down which parts you completed independently, what help you used, and what you would test next.",
                    ],
                    outcome="One inspectable project artifact and a short record of decisions, help used, and remaining unknowns.",
                    hours=_time_hours(request, (2.0, 6.0)), skills=primary.skill_or_interest_matches if primary else [],
                    sources=[task_fact.source], prerequisite_status="not_assessed",
                    prerequisite_note="The source describes occupational work context; it does not establish an entry prerequisite.", origin="source_informed",
                ))
            actions.append(_action(
                index=len(actions) + 1, phase="Document and review", kind="document",
                title="Document the project and request specific feedback",
                why="A short portfolio record and explicit feedback make the next planning cycle more evidence-based.",
                instructions=["Save a brief problem statement, artifact, method, and result.", "Ask a teacher, peer, mentor, or reviewer one concrete question, when available.", "Record the feedback and your own view; separate what was observed from what you infer."],
                outcome="A portfolio note, feedback point if available, and a specific next question.",
                hours=_time_hours(request, (0.5, 2.0)), origin="skillscope_authored",
            ))
            limitations = [
                "This curated graph does not supply a complete, verified qualification/admission pathway for the listed hypotheses.",
                "No salary, hiring probability, market-demand forecast, or employment guarantee is provided.",
                "Skill labels not documented in the supplied context are marked unrecorded, not assumed absent or deficient.",
            ]

    # Time horizons are attached only after explicit planning inputs make a bounded plan reasonable.
    if target_days and age_band == AgeBand.AGE_18_PLUS and actions:
        labels = {30: "By day 30", 60: "By day 60", 90: "By day 90", 7: "By day 7", 14: "By day 14", 15: "By day 15", 180: "By day 180", 365: "By day 365"}
        n_actions = len(actions)
        for index, action in enumerate(actions):
            milestone_index = min(len(target_days) - 1, (index * len(target_days)) // max(1, n_actions))
            # First action is the first milestone, last action reaches the target horizon.
            if n_actions == 1:
                milestone_index = len(target_days) - 1
            elif index == n_actions - 1:
                milestone_index = len(target_days) - 1
            days = target_days[milestone_index]
            actions[index] = action.model_copy(update={"time_horizon_days": days, "time_horizon_label": labels.get(days, f"By day {days}")})
    # Re-sequence actions after construction, especially when the goal-clarification action is present.
    actions = [a.model_copy(update={"order": i, "step_id": f"step-{i:02d}"}) for i, a in enumerate(actions, start=1)]

    inputs = {
        "current_skills_summary": request.current_skills_summary,
        "education_summary": request.education_summary,
        "experience_summary": request.experience_summary,
        "planning_constraints": request.planning_constraints,
        "available_hours_per_week": request.available_hours_per_week,
        "desired_timeline": request.desired_timeline.value,
    }
    if age_band == AgeBand.AGE_18_PLUS and not skills:
        # Still surface the main uncertainty if the graph has no usable skill extract.
        skills = [SkillEvidenceGap(
            skill_label="Current skills and target requirements",
            status="not_yet_documented",
            explanation="The current catalog or supplied profile does not support a reliable skill-by-skill comparison. Add context or use the next project to gather evidence.",
            source_references=[],
        )]
    return PathwayPlan(
        plan_id=plan_id or uuid4(), profile_id=profile.profile_id, age_band=age_band,
        mode=MODE_BY_AGE[age_band], algorithm_version=ALGORITHM_VERSION,
        recommendation_algorithm_version=recommendations.algorithm_version,
        current_goal=goal, previous_goal=previous_goal if goal_change_detected else None, goal_change_detected=goal_change_detected,
        goal_change_handling=(
            "The goal was changed or cleared. Historical evidence was retained and the plan was recalculated against the updated goal; continue the discovery/validation loop to gather new evidence."
            if goal_change_detected else
            "No goal change was detected. You can edit the goal and generate a revised plan; historical evidence will remain in the ledger."
        ),
        created_at=now, inputs_used=inputs, pathway_options=options,
        skills_to_check_or_develop=skills, requirements_and_sources=requirements,
        actions=actions, timebox=timebox,
        revision_instructions=[
            "Edit the stated goal or planning context and generate a new plan when priorities, constraints, or interests change.",
            "Complete an action and record the observable output and reflection in the evidence ledger; a new plan will use the updated evidence.",
            "Treat all actions as editable suggestions. Verify qualifications, entry requirements, and local relevance with the responsible official source before committing time or money.",
        ],
        limitations=limitations,
    )


class PathwayPlanRepository:
    """Persistent plan snapshots. Updating a goal uses the evidence ledger's dated goal history."""

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH, *, recommendation_provider=None, career_provider=None) -> None:
        self.db_path = Path(db_path)
        self.evidence = EvidenceLedgerRepository(self.db_path)
        self.recommendations = recommendation_provider or RecommendationRepository(self.db_path)
        self.career_provider = career_provider or list_career_cards
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        from app.services.database import connect_sqlite
        return connect_sqlite(self.db_path)

    def _initialize(self) -> None:
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS pathway_plans (
                    plan_id TEXT PRIMARY KEY,
                    profile_id TEXT NOT NULL,
                    algorithm_version TEXT NOT NULL,
                    current_goal TEXT,
                    age_band TEXT NOT NULL,
                    goal_change_detected INTEGER NOT NULL CHECK(goal_change_detected IN (0,1)),
                    created_at TEXT NOT NULL,
                    inputs_json TEXT NOT NULL,
                    plan_json TEXT NOT NULL,
                    FOREIGN KEY(profile_id) REFERENCES student_profiles(profile_id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_pathway_plans_profile_created
                    ON pathway_plans(profile_id, created_at DESC, plan_id);
            """)

    def generate(self, profile_id: str | UUID, request: PlanInput) -> PathwayPlan | None:
        profile = self.evidence.get_profile(profile_id)
        if profile is None:
            return None
        if profile.age_band != AgeBand.AGE_18_PLUS:
            supplied_adult_fields = set(request.model_fields_set) & ADULT_ONLY_FIELDS
            # desired_timeline's default is intentionally ignored unless explicitly supplied.
            if supplied_adult_fields:
                raise ValueError("Skills, education, work-experience, time-capacity, constraints, and deadline planning inputs are only collected in the 18+ planning mode.")

        previous_goal = profile.current_goal
        goal_change_detected = False
        if "current_goal" in request.model_fields_set:
            normalized_goal = _clean(request.current_goal)
            goal_change_detected = normalized_goal != previous_goal
            if goal_change_detected:
                profile = self.evidence.update_profile(
                    profile.profile_id,
                    StudentProfileUpdate(current_goal=normalized_goal),
                ) or profile
        # Request has been accepted and a change is recorded as historical evidence before the
        # recommendation engine sees the new goal. Existing evidence is deliberately not erased.
        try:
            recs = self.recommendations.get_recommendations(profile.profile_id, limit=5)
        except RecommendationCatalogError:
            raise
        if recs is None:
            return None
        evidence_items, _ = self.evidence.list_evidence(profile.profile_id, limit=200)
        cards: list[dict[str, Any]] = []
        if profile.age_band == AgeBand.AGE_18_PLUS:
            cards = self.career_provider(db_path=self.db_path, limit=200, offset=0)
        plan = build_pathway_plan(
            profile, request, recs, evidence_items, cards,
            previous_goal=previous_goal, goal_change_detected=goal_change_detected,
        )
        snapshot = plan.model_dump(mode="json")
        with self._connect() as db:
            db.execute(
                """INSERT INTO pathway_plans (
                    plan_id, profile_id, algorithm_version, current_goal, age_band,
                    goal_change_detected, created_at, inputs_json, plan_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (str(plan.plan_id), str(plan.profile_id), plan.algorithm_version, plan.current_goal,
                 plan.age_band.value, int(plan.goal_change_detected), plan.created_at.isoformat(),
                 json.dumps(request.model_dump(mode="json"), sort_keys=True),
                 json.dumps(snapshot, sort_keys=True)),
            )
        return plan

    def get_latest(self, profile_id: str | UUID) -> PathwayPlan | None:
        if self.evidence.get_profile(profile_id) is None:
            return None
        with self._connect() as db:
            row = db.execute("SELECT plan_json FROM pathway_plans WHERE profile_id = ? ORDER BY created_at DESC, plan_id DESC LIMIT 1", (str(profile_id),)).fetchone()
        return PathwayPlan.model_validate_json(row["plan_json"]) if row else None

    def history(self, profile_id: str | UUID, *, limit: int = 20) -> list[PathwayPlanHistoryItem] | None:
        if self.evidence.get_profile(profile_id) is None:
            return None
        with self._connect() as db:
            rows = db.execute(
                "SELECT plan_id, profile_id, current_goal, age_band, goal_change_detected, created_at, plan_json, algorithm_version FROM pathway_plans WHERE profile_id = ? ORDER BY created_at DESC, plan_id DESC LIMIT ?",
                (str(profile_id), limit),
            ).fetchall()
        result = []
        for row in rows:
            snapshot = json.loads(row["plan_json"])
            result.append(PathwayPlanHistoryItem(
                plan_id=UUID(row["plan_id"]), profile_id=UUID(row["profile_id"]),
                created_at=datetime.fromisoformat(row["created_at"]), current_goal=row["current_goal"],
                age_band=AgeBand(row["age_band"]), goal_change_detected=bool(row["goal_change_detected"]),
                action_count=len(snapshot.get("actions", [])), pathway_count=len(snapshot.get("pathway_options", [])),
                algorithm_version=row["algorithm_version"],
            ))
        return result
