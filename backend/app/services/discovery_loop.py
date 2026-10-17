"""Deterministic, evidence-aware next-challenge selection for the longitudinal loop.

The selected challenge is a projection of persisted profile/evidence/submission state. It is
not a psychological inference, aptitude score, or career-fit verdict. Every decision is tied to
an explicit user preference, an explicit self-labelled interpretation, or observable exposure.
"""
from __future__ import annotations

import json
from collections import Counter
from uuid import UUID

from app.schemas.challenges import AgeBand, ChallengeDomain, EvidenceStatus
from app.schemas.discovery_loop import (
    DiscoveryLoopState,
    DomainExposure,
    LastCompletion,
    LoopPreference,
    NextChallenge,
)
from app.schemas.student_evidence import UserInterpretation
from app.services.challenges import CHALLENGES, LIBRARY, ChallengeRepository

MODE_BY_AGE = {
    AgeBand.AGE_10_14: "discover_and_shape",
    AgeBand.AGE_15_17: "explore_and_validate",
    AgeBand.AGE_18_PLUS: "develop_and_optimize",
}


class DiscoveryLoopRepository:
    """Build a stable next-step recommendation from the stored evidence ledger."""

    def __init__(self, db_path=None):
        self.challenges = ChallengeRepository(db_path)
        self.evidence = self.challenges.evidence
        self.db_path = self.challenges.db_path

    def get_state(self, profile_id: str | UUID, preference: LoopPreference = LoopPreference.BALANCED) -> DiscoveryLoopState | None:
        profile = self.evidence.get_profile(profile_id)
        if profile is None:
            return None

        with self.evidence._connect() as db:
            total_submissions = int(db.execute(
                "SELECT COUNT(*) AS n FROM challenge_submissions WHERE profile_id = ?",
                (str(profile.profile_id),),
            ).fetchone()["n"])
            # Read only a bounded recent window for narrative/engagement; keep lifetime coverage
            # in SQL aggregates so the loop stays lightweight as histories grow.
            rows = db.execute(
                "SELECT * FROM challenge_submissions WHERE profile_id = ? ORDER BY created_at DESC, submission_id DESC LIMIT 20",
                (str(profile.profile_id),),
            ).fetchall()
            exposure_rows = db.execute(
                "SELECT challenge_id, COUNT(*) AS n, MAX(created_at) AS latest_at FROM challenge_submissions WHERE profile_id = ? GROUP BY challenge_id",
                (str(profile.profile_id),),
            ).fetchall()
            evidence_count = int(db.execute(
                "SELECT COUNT(*) AS n FROM student_evidence_items WHERE profile_id = ?",
                (str(profile.profile_id),),
            ).fetchone()["n"])

        history = [dict(row) for row in rows]
        exposure_counts: Counter[str] = Counter()
        exposure_challenges: dict[str, set[str]] = {}
        latest_at: dict[str, str] = {}
        used_ids: set[str] = set()
        for row in exposure_rows:
            challenge = LIBRARY.get(row["challenge_id"])
            if challenge is None:
                continue
            used_ids.add(challenge.challenge_id)
            domain = challenge.domain.value
            exposure_counts[domain] += int(row["n"])
            exposure_challenges.setdefault(domain, set()).add(challenge.challenge_id)
            candidate_latest = row["latest_at"]
            if domain not in latest_at or candidate_latest > latest_at[domain]:
                latest_at[domain] = candidate_latest

        domain_exposure = []
        for domain in ChallengeDomain:
            count = exposure_counts[domain.value]
            domain_exposure.append(DomainExposure(
                domain=domain,
                submission_count=count,
                distinct_challenges=len(exposure_challenges.get(domain.value, set())),
                latest_at=latest_at.get(domain.value),
                status=("unknown" if count == 0 else "exposed_once" if count == 1
                        else "multiple_challenge_families" if len(exposure_challenges.get(domain.value, set())) > 1
                        else "repeated_same_challenge"),
            ))

        last_completion = self._last_completion(history[0], profile.age_band) if history else None
        recommendation = self._select_next(profile.age_band, history, exposure_counts, used_ids, preference)
        changed = self._change_explanation(last_completion, recommendation)
        if last_completion is None:
            next_step = f"Start with {recommendation.title}; make the expected output, then record only what you actually observed."
        else:
            next_step = f"Try {recommendation.title} ({recommendation.expected_minutes} minutes). Compare this activity with the last one, and update your interpretation if your view has changed."

        return DiscoveryLoopState(
            profile_id=profile.profile_id,
            age_band=profile.age_band,
            mode=MODE_BY_AGE[profile.age_band],
            preference=preference,
            current_goal=profile.current_goal,
            total_submissions=total_submissions,
            evidence_count=evidence_count,
            domain_exposure=domain_exposure,
            last_completion=last_completion,
            next_challenge=recommendation,
            what_changed=changed,
            next_step=next_step,
            limitations=[
                "Challenge selection is a deterministic, versioned heuristic, not a validated recommendation model.",
                "Objective rubric scores remain specific to their challenge and rubric; scores across different tasks are not compared.",
                "A domain with no recorded activity is unknown/unexplored, not evidence of low interest or ability.",
                "Alternative-path testing is triggered by the student's explicit interpretation, not inferred from performance alone.",
                "The loop is request-driven; scheduled reminders and push notifications are not implemented.",
                "The prototype API has no authentication/authorization and is not suitable for real student/minor deployment.",
            ],
        )

    def _last_completion(self, row: dict, age_band: AgeBand) -> LastCompletion:
        challenge = LIBRARY[row["challenge_id"]]
        variant = next(item for item in challenge.age_variants if item.age_band == age_band)
        results = json.loads(row["rubric_results_json"])
        observed = sum(1 for item in results if item.get("score") is not None)
        reflections = json.loads(row["reflections_json"] or "{}")
        return LastCompletion(
            submission_id=UUID(row["submission_id"]),
            challenge_id=row["challenge_id"],
            title=variant.title,
            domain=challenge.domain,
            evidence_status=row["evidence_status"],
            observed_criteria=observed,
            objective_score=row["objective_score"],
            objective_max_score=row["objective_max_score"],
            interpretation=UserInterpretation(row.get("user_interpretation") or UserInterpretation.NOT_INTERPRETED.value),
            enjoyment=reflections.get("enjoyment"),
            reported_difficulty=reflections.get("difficulty"),
            confidence=reflections.get("confidence"),
            willingness_to_continue=reflections.get("willingness_to_continue"),
            reflection=reflections.get("reflection"),
            created_at=row["created_at"],
        )

    def _select_next(self, age_band, history, exposure_counts, used_ids, preference) -> NextChallenge:
        latest = history[0] if history else None
        latest_challenge = LIBRARY.get(latest["challenge_id"]) if latest else None
        latest_domain = latest_challenge.domain if latest_challenge else None
        latest_interpretation = UserInterpretation(
            latest.get("user_interpretation") or UserInterpretation.NOT_INTERPRETED.value
        ) if latest else UserInterpretation.NOT_INTERPRETED
        reflections = json.loads(latest["reflections_json"] or "{}") if latest else {}
        recent_ids = {row["challenge_id"] for row in history[:3]}

        all_candidates = [ch for ch in CHALLENGES if any(v.age_band == age_band for v in ch.age_variants)]
        never_tried = [ch for ch in all_candidates if ch.challenge_id not in used_ids]
        not_recent = [ch for ch in all_candidates if ch.challenge_id not in recent_ids]
        # Prefer a never-tried family first; after the finite library has been used, avoid the
        # three most recent activities. Only then may the loop reintroduce an older activity.
        candidates = never_tried or not_recent or all_candidates

        reason_code = "explore_underexposed_domain"
        rationale = "This domain has had little or no exposure in the saved history. A new activity helps broaden the evidence instead of treating missing data as a weakness."
        why_this_now = "The profile has limited evidence across domains, so the loop is widening exploration before narrowing focus."
        chosen_pool = candidates
        desired_domain: ChallengeDomain | None = None
        forbidden_domain: ChallengeDomain | None = None

        # An explicit student report of conflict outranks the default preference: test a different
        # domain next, without interpreting that report as proof that the current goal is wrong.
        if latest and latest_interpretation == UserInterpretation.CHALLENGES_CURRENT_HYPOTHESIS:
            forbidden_domain = latest_domain
            reason_code = "test_alternative_pathway"
            rationale = "You said the last activity challenged your current hypothesis. The next activity deliberately tests a different domain; this is a comparison, not a verdict or an automatic goal change."
            why_this_now = "Your own interpretation raised an open question, so the loop is sampling an alternative before making any stronger claim."
        elif preference == LoopPreference.ALTERNATIVE:
            forbidden_domain = latest_domain
            reason_code = "test_alternative_pathway"
            rationale = "You chose to explore an alternative. The next task comes from a less-exposed domain and avoids the last task when another option exists."
            why_this_now = "You explicitly requested a broader comparison rather than more evidence for the current direction."
        elif preference == LoopPreference.EXPLORE:
            reason_code = "explore_underexposed_domain"
            rationale = "You selected broad exploration. The loop prefers an age-appropriate domain with the least recorded exposure and avoids recent repetitions where possible."
            why_this_now = "You asked to widen exposure before deciding which areas deserve deeper testing."
        elif preference == LoopPreference.VALIDATE:
            if latest and latest_interpretation == UserInterpretation.CONTEXTUAL_OR_MIXED:
                desired_domain = latest_domain
                reason_code = "validate_uncertain_hypothesis"
                rationale = "Your last reflection was mixed or context-dependent. A different challenge in the same domain can test whether that result generalizes beyond one task."
                why_this_now = "One activity can be unusually easy, hard, familiar, or unfamiliar; a different task is a useful check."
            elif latest:
                desired_domain = latest_domain
                reason_code = "validate_uncertain_hypothesis"
                rationale = "You selected validation. The loop will try a different activity in the most recently tested domain when one is available, rather than repeat the same task."
                why_this_now = "A second kind of task can help test whether the first observation holds in a different context."
            else:
                reason_code = "explore_underexposed_domain"
                rationale = "There is no recorded activity to validate yet, so the first step is a short broad-exploration task. Validation becomes more useful after evidence exists."
                why_this_now = "No hypothesis has been tested in the loop yet; the system will not invent one."
        elif preference == LoopPreference.DEVELOP:
            engaged_domain = self._engaged_domain(history)
            if engaged_domain is not None:
                desired_domain = engaged_domain
                reason_code = "develop_demonstrated_engagement"
                rationale = "A prior activity in this domain has explicit positive self-reported engagement. The next task develops the thread with a different activity; engagement is not treated as ability."
                why_this_now = "You requested development, and this is the clearest domain with recorded engagement to build on."
            else:
                reason_code = "explore_before_developing"
                rationale = "There is not yet clear, explicit engagement evidence to justify choosing a development focus. The loop starts with the least-exposed domain instead of guessing."
                why_this_now = "Development is more useful after the student has tried a task and reported how it felt."
        else:  # balanced default
            if latest and latest_interpretation == UserInterpretation.CONTEXTUAL_OR_MIXED:
                desired_domain = latest_domain
                reason_code = "validate_uncertain_hypothesis"
                rationale = "Your reflection was mixed or depended on context. The loop will test the same domain with a different task where possible, rather than overreact to one result."
                why_this_now = "A second, different activity helps distinguish a one-off experience from a pattern."
            elif latest and latest_interpretation == UserInterpretation.SUPPORTS_CURRENT_HYPOTHESIS:
                desired_domain = latest_domain
                reason_code = "develop_demonstrated_engagement"
                rationale = "You said this activity supports your current hypothesis. The loop will deepen the exploration with a different task where possible, without treating one response as confirmation."
                why_this_now = "The next task checks for repeatability while avoiding the exact activity just completed."
            elif latest and (reflections.get("enjoyment") or 0) >= 4 and (reflections.get("willingness_to_continue") or 0) >= 4:
                desired_domain = latest_domain
                reason_code = "develop_demonstrated_engagement"
                rationale = "You reported high enjoyment and willingness to continue. The loop offers a different task in that domain if available, while keeping performance and self-report separate."
                why_this_now = "Your voluntary feedback is a reason to offer more exploration there, not proof of a fixed trait."

        if desired_domain is not None:
            same_domain = [ch for ch in candidates if ch.domain == desired_domain]
            if same_domain:
                chosen_pool = same_domain
            else:
                # A family-level challenge is not duplicated for validation; switch to exploration.
                reason_code = "explore_underexposed_domain"
                rationale = "There is no different recent challenge available in that domain. The loop broadens exposure rather than immediately repeating the same task."
                why_this_now = "The library has finite challenge families; this next step avoids pretending that a repeated task is new evidence."
                chosen_pool = candidates
        if forbidden_domain is not None:
            alternatives = [ch for ch in chosen_pool if ch.domain != forbidden_domain]
            if not alternatives:
                # The unseen pool might contain only tasks in the domain the student wants to
                # reconsider. Preserve the conflict/alternative intent by reusing an older,
                # non-recent alternative before falling back to the same domain.
                alternatives = [ch for ch in not_recent if ch.domain != forbidden_domain]
            if alternatives:
                chosen_pool = alternatives
            else:
                chosen_pool = candidates
                # This should only occur after all usable alternative-domain families are recent.
                rationale += " The alternative-domain library is exhausted under recent-task avoidance, so the best eligible non-recent task is used."

        if not chosen_pool:
            chosen_pool = all_candidates

        # Tie-break using stable library order after choosing the least-exposed domain. This is a
        # transparent rule; no random values or unlabelled fit weights are involved.
        least_exposed = min(exposure_counts[ch.domain.value] for ch in chosen_pool)
        least_exposed_candidates = [ch for ch in chosen_pool if exposure_counts[ch.domain.value] == least_exposed]
        chosen = least_exposed_candidates[0]
        if reason_code in {"develop_demonstrated_engagement", "validate_uncertain_hypothesis"} and chosen.domain != desired_domain:
            reason_code = "explore_underexposed_domain"
            rationale = "The library has no eligible different task in the selected domain after recent-repeat avoidance, so the loop broadens exposure instead."
            why_this_now = "Keeping the activity genuinely different is more useful than repeating a recent task and implying it added new evidence."
        variant = next(v for v in chosen.age_variants if v.age_band == age_band)
        return NextChallenge(
            challenge_id=chosen.challenge_id,
            challenge_version=chosen.version,
            domain=chosen.domain,
            skill_tags=chosen.skill_tags,
            difficulty=chosen.difficulty,
            safety_rating=chosen.safety_rating,
            title=variant.title,
            instructions=variant.instructions,
            expected_output=variant.expected_output,
            expected_minutes=variant.expected_minutes,
            materials=variant.materials,
            accessibility_notes=variant.accessibility_notes,
            rubric=chosen.rubric,
            reflection_prompts=variant.reflection_prompts,
            reason_code=reason_code,
            rationale=rationale,
            why_this_now=why_this_now,
            avoids_recent_repeat=chosen.challenge_id not in recent_ids,
        )

    @staticmethod
    def _engaged_domain(history: list[dict]) -> ChallengeDomain | None:
        # Use user-declared ordinal signals as separate tie-breakers, never combine them into
        # an invented composite score and never use rubric totals from unrelated tasks.
        for row in history[:10]:
            challenge = LIBRARY.get(row["challenge_id"])
            if not challenge:
                continue
            reflection = json.loads(row["reflections_json"] or "{}")
            interpretation = row.get("user_interpretation") or UserInterpretation.NOT_INTERPRETED.value
            enjoyment = reflection.get("enjoyment")
            willingness = reflection.get("willingness_to_continue")
            if interpretation == UserInterpretation.SUPPORTS_CURRENT_HYPOTHESIS.value or (enjoyment is not None and enjoyment >= 4) or (willingness is not None and willingness >= 4):
                # Most recent qualifying engagement report wins. This avoids letting a high
                # rating from one old activity overpower later changes in a student's interests.
                return challenge.domain
        return None

    @staticmethod
    def _change_explanation(last: LastCompletion | None, next_challenge: NextChallenge) -> str:
        if last is None:
            return "No challenge has been completed in this profile yet. SkillScope starts with a short, low-risk activity and records the first observation; it does not infer a starting strength from missing history."
        if last.evidence_status == EvidenceStatus.NOT_ENOUGH_EVIDENCE.value:
            prefix = "The last activity did not produce enough observed rubric evidence for an objective result. That is not a negative score; unobserved criteria remain unknown. "
        elif last.evidence_status == EvidenceStatus.PARTIAL.value:
            prefix = "The last activity produced partial rubric evidence, so its result is limited to the criteria observed. "
        else:
            prefix = "The last activity and its rubric observations are saved to the evidence ledger. "
        if next_challenge.reason_code == "test_alternative_pathway":
            return prefix + "Because an alternative was requested or your own reflection challenged the current hypothesis, the next task samples a different domain."
        if next_challenge.reason_code == "validate_uncertain_hypothesis":
            return prefix + "Your context-dependent or validation preference makes a different task in the same domain the next check."
        if next_challenge.reason_code == "develop_demonstrated_engagement":
            return prefix + "Your explicit reflection supports exploring this area further, so the next activity is a different task in this domain rather than a repeat of the same challenge."
        if next_challenge.reason_code == "explore_before_developing":
            return prefix + "There is not enough engagement evidence to select a development focus, so the loop broadens exploration first."
        return prefix + "The next task broadens domain exposure and avoids repeating a recent challenge where possible."
