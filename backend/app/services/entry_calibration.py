"""Deterministic age-aware entry calibration for SkillScope.

These configurable rules select an onboarding strategy from self-reported
inputs. They are transparent MVP heuristics, not validated psychometrics and
not estimates of aptitude, future success, or career suitability.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas.calibration import (
    AgeBand,
    AgeMode,
    CalibrationRequest,
    CalibrationResponse,
    DesiredTimeline,
    EvidenceQuality,
    ExplorationDomain,
    EvidenceStrength,
    ExperienceLevel,
    JourneyPreference,
    Rating,
    StartingPath,
)

CALIBRATION_VERSION = "1.0.0"

AGE_MODE_LABELS: dict[AgeMode, str] = {
    AgeMode.DISCOVER_AND_SHAPE: "Discover & Shape",
    AgeMode.EXPLORE_AND_VALIDATE: "Explore & Validate",
    AgeMode.DEVELOP_AND_OPTIMIZE: "Develop & Optimize",
}

STARTING_PATH_LABELS: dict[StartingPath, str] = {
    StartingPath.GUIDED_EXPLORATION: "Guided Exploration",
    StartingPath.BASELINE_DISCOVERY: "Baseline Discovery",
    StartingPath.BROADEN_EXPLORATION: "Broaden Exploration",
    StartingPath.VALIDATE_DECLARED_INTEREST: "Validate a Stated Interest",
    StartingPath.CAREER_DISCOVERY: "Career Discovery",
    StartingPath.CAREER_GOAL_VALIDATION: "Career Goal Validation",
    StartingPath.CAREER_GAP_ANALYSIS: "Career Gap Analysis",
    StartingPath.REENTER_DISCOVERY: "Re-enter Discovery",
}

EXPLORATION_DOMAIN_LABELS: dict[ExplorationDomain, str] = {
    ExplorationDomain.CREATIVE_DESIGN: "creative design",
    ExplorationDomain.ANALYTICAL_LOGIC: "analytical and logical problem-solving",
    ExplorationDomain.HANDS_ON_MAKING: "hands-on building and making",
    ExplorationDomain.SOCIAL_COLLABORATION: "social collaboration",
    ExplorationDomain.COMMUNICATION_STORYTELLING: "communication and storytelling",
    ExplorationDomain.SCIENCE_EXPERIMENTATION: "science and experimentation",
    ExplorationDomain.TECHNOLOGY_COMPUTING: "technology and computing",
    ExplorationDomain.ENVIRONMENT_SUSTAINABILITY: "environment and sustainability",
    ExplorationDomain.BUSINESS_ENTREPRENEURSHIP: "business and entrepreneurship",
    ExplorationDomain.HEALTH_WELLBEING: "health and wellbeing",
}

TIMELINE_LABELS: dict[DesiredTimeline, str] = {
    DesiredTimeline.UNSPECIFIED: "not specified",
    DesiredTimeline.UNDER_3_MONTHS: "under 3 months",
    DesiredTimeline.MONTHS_3_TO_6: "3–6 months",
    DesiredTimeline.MONTHS_6_TO_12: "6–12 months",
    DesiredTimeline.OVER_12_MONTHS: "over 12 months",
}

EVIDENCE_STRENGTH_LABELS: dict[EvidenceStrength, str] = {
    EvidenceStrength.NONE: "No prior evidence reported",
    EvidenceStrength.LIMITED: "Limited evidence coverage",
    EvidenceStrength.EMERGING: "Some evidence to explore",
    EvidenceStrength.SUBSTANTIAL: "Broader evidence reported",
}

NEXT_STEPS: dict[StartingPath, str] = {
    StartingPath.GUIDED_EXPLORATION: (
        "Try one short activity in a familiar domain and one in a different domain. "
        "After each, reflect on enjoyment, effort, and whether you would try a related task again."
    ),
    StartingPath.BASELINE_DISCOVERY: (
        "Complete a short baseline across at least two different domains before narrowing the path. "
        "Treat the result as a first snapshot, not a judgement of ability."
    ),
    StartingPath.BROADEN_EXPLORATION: (
        "Try one challenge related to your current direction and one from an unfamiliar domain. "
        "Compare your experience and reflection before choosing what to test next."
    ),
    StartingPath.VALIDATE_DECLARED_INTEREST: (
        "Complete a practical project in the stated area and a small adjacent-domain challenge. "
        "Use the work and reflection to decide what to investigate next."
    ),
    StartingPath.CAREER_DISCOVERY: (
        "Explore two contrasting career families through small work samples before committing to a roadmap. "
        "Record what is known, what is self-reported, and what remains unknown."
    ),
    StartingPath.CAREER_GOAL_VALIDATION: (
        "Compare your current evidence with the requirements of the stated direction, then complete "
        "a small work sample that tests the largest important unknown."
    ),
    StartingPath.CAREER_GAP_ANALYSIS: (
        "Compare your current evidence with verified requirements for the target role. Prioritize "
        "two or three specific gaps and draft a time-bounded learning or project plan."
    ),
    StartingPath.REENTER_DISCOVERY: (
        "Start a fresh exploration cycle with one familiar domain and one unfamiliar domain. "
        "Let new evidence inform the next step instead of treating earlier choices as permanent labels."
    ),
}

LIMITATIONS = [
    "This is a deterministic, versioned MVP heuristic, not a scientifically validated assessment, talent score, or estimate of ability.",
    "Evidence count, evidence quality, experience, career clarity, and exploration need are self-reported for this request.",
    "This endpoint does not persist a student profile or infer historical activity; its result applies only to the submitted inputs.",
    "A starting path is a reversible suggestion. It does not determine the user's ideal career or limit future opportunities.",
]


@dataclass(frozen=True)
class AgeProfile:
    band: AgeBand
    mode: AgeMode


def _age_profile(age: int) -> AgeProfile:
    if 10 <= age <= 14:
        return AgeProfile(AgeBand.AGES_10_14, AgeMode.DISCOVER_AND_SHAPE)
    if 15 <= age <= 17:
        return AgeProfile(AgeBand.AGES_15_17, AgeMode.EXPLORE_AND_VALIDATE)
    # Request schema enforces age >= 10; all remaining supported ages are 18+.
    return AgeProfile(AgeBand.AGES_18_PLUS, AgeMode.DEVELOP_AND_OPTIMIZE)


def _evidence_strength(request: CalibrationRequest) -> EvidenceStrength:
    """Estimate evidence coverage, never talent or ability.

    Thresholds are explicit MVP heuristics and may be revisited after testing.
    """
    count = request.prior_evidence_count
    quality = request.prior_evidence_quality
    # A written activity summary is one unquantified, self-reported context
    # item when the user cannot provide a numeric count.
    if count == 0 and request.prior_activity_summary:
        count = 1

    if count == 0:
        return EvidenceStrength.NONE
    if count <= 2 or quality in {EvidenceQuality.UNKNOWN, EvidenceQuality.LOW}:
        return EvidenceStrength.LIMITED
    if count >= 6 and quality is EvidenceQuality.HIGH:
        return EvidenceStrength.SUBSTANTIAL
    return EvidenceStrength.EMERGING


def _select_next_step(request: CalibrationRequest, starting_path: StartingPath) -> str:
    """Build a concrete next step, honoring user-named unfamiliar domains."""
    base = NEXT_STEPS[starting_path]
    if not request.unexplored_domains:
        return base

    domain_names = [EXPLORATION_DOMAIN_LABELS[domain] for domain in request.unexplored_domains]
    selected = ", ".join(domain_names[:3])
    if len(domain_names) > 3:
        selected += f", and {len(domain_names) - 3} more area(s)"
    unfamiliar_step = (
        f"You marked these areas as less familiar: {selected}. Include one low-stakes activity from "
        "one of these areas so lack of exposure is not mistaken for lack of ability. "
    )
    return unfamiliar_step + base


def _is_strong_enough_for_gap_analysis(
    request: CalibrationRequest,
    evidence_strength: EvidenceStrength,
) -> bool:
    return (
        request.career_clarity is Rating.HIGH
        and bool(request.current_goal)
        and evidence_strength is EvidenceStrength.SUBSTANTIAL
        and request.prior_projects_experience is ExperienceLevel.SUBSTANTIAL
        and bool(request.skills_summary or request.experience_summary)
        and not request.contradictory_evidence
        and not request.career_goal_changed
    )


def _choose_starting_path(
    request: CalibrationRequest,
    age_profile: AgeProfile,
    evidence_strength: EvidenceStrength,
) -> StartingPath:
    """Choose the journey branch while retaining an age-appropriate experience."""
    age_mode = age_profile.mode

    # Younger students always receive broad, developmentally appropriate
    # activities. An optimisation/validation preference is translated into
    # exploration rather than an adult-style career plan.
    if age_mode is AgeMode.DISCOVER_AND_SHAPE:
        return StartingPath.GUIDED_EXPLORATION

    if age_mode is AgeMode.EXPLORE_AND_VALIDATE:
        if request.reenter_discovery or request.journey_preference is JourneyPreference.EXPLORE:
            return StartingPath.REENTER_DISCOVERY
        if request.career_goal_changed and request.contradictory_evidence:
            return StartingPath.BROADEN_EXPLORATION
        if request.career_goal_changed:
            return StartingPath.BASELINE_DISCOVERY
        if request.contradictory_evidence:
            return StartingPath.BROADEN_EXPLORATION
        if request.journey_preference is JourneyPreference.OPTIMIZE:
            if request.current_goal and request.career_clarity is not Rating.LOW:
                return StartingPath.VALIDATE_DECLARED_INTEREST
            return StartingPath.BASELINE_DISCOVERY

        if request.journey_preference is JourneyPreference.VALIDATE:
            if request.current_goal and request.career_clarity is not Rating.LOW:
                return StartingPath.VALIDATE_DECLARED_INTEREST
            return StartingPath.BASELINE_DISCOVERY

        if request.career_clarity is Rating.LOW or not request.current_goal:
            return StartingPath.BASELINE_DISCOVERY
        if (
            request.journey_preference is JourneyPreference.AUTOMATIC
            and request.current_goal
            and request.unexplored_domains
        ):
            return StartingPath.BROADEN_EXPLORATION
        if (
            request.journey_preference is JourneyPreference.AUTOMATIC
            and request.exploration_need is Rating.HIGH
        ):
            return StartingPath.BROADEN_EXPLORATION
        if request.career_clarity is Rating.HIGH:
            return StartingPath.VALIDATE_DECLARED_INTEREST
        return StartingPath.BASELINE_DISCOVERY

    # Adults can start with career discovery, goal validation, or practical gap
    # analysis. Explicitly requested exploration always remains available.
    if request.reenter_discovery:
        return StartingPath.REENTER_DISCOVERY
    if request.journey_preference is JourneyPreference.EXPLORE:
        return StartingPath.CAREER_DISCOVERY
    if request.career_goal_changed and request.contradictory_evidence:
        return StartingPath.CAREER_DISCOVERY
    if request.career_goal_changed:
        if request.current_goal and request.career_clarity is not Rating.LOW:
            return StartingPath.CAREER_GOAL_VALIDATION
        return StartingPath.CAREER_DISCOVERY
    if request.contradictory_evidence:
        return StartingPath.CAREER_DISCOVERY

    if request.journey_preference is JourneyPreference.VALIDATE:
        if request.current_goal and request.career_clarity is not Rating.LOW:
            return StartingPath.CAREER_GOAL_VALIDATION
        return StartingPath.CAREER_DISCOVERY

    if request.journey_preference is JourneyPreference.OPTIMIZE:
        if _is_strong_enough_for_gap_analysis(request, evidence_strength):
            return StartingPath.CAREER_GAP_ANALYSIS
        if request.current_goal and request.career_clarity is not Rating.LOW:
            return StartingPath.CAREER_GOAL_VALIDATION
        return StartingPath.CAREER_DISCOVERY

    # Automatic route: clear goal + sufficiently broad evidence can support
    # gap analysis. Otherwise validate or explore rather than pretending gaps
    # are known.
    if request.exploration_need is Rating.HIGH:
        return StartingPath.CAREER_DISCOVERY
    if request.career_clarity is Rating.LOW or not request.current_goal:
        return StartingPath.CAREER_DISCOVERY
    if _is_strong_enough_for_gap_analysis(request, evidence_strength):
        return StartingPath.CAREER_GAP_ANALYSIS
    return StartingPath.CAREER_GOAL_VALIDATION


def _starting_path_reason(
    request: CalibrationRequest,
    age_profile: AgeProfile,
    starting_path: StartingPath,
) -> str:
    """Explain why the selected path follows from the specific inputs."""
    if starting_path is StartingPath.GUIDED_EXPLORATION:
        return (
            "This age group begins with broad, age-appropriate activities instead of a fixed career label. "
            "A deeper career gap analysis is not the starting task for this mode."
        )
    if starting_path is StartingPath.BASELINE_DISCOVERY:
        if request.career_goal_changed:
            return (
                "Because the direction changed, this baseline uses fresh discovery to avoid assuming that "
                "earlier interests or experiences automatically fit the current goal."
            )
        if request.career_clarity is Rating.LOW or not request.current_goal:
            return (
                "The current direction is unclear or not supplied, so a baseline across multiple domains "
                "is more useful than pretending a target-role gap is already known."
            )
        return (
            "The available context does not support narrowing to a roadmap yet. A baseline will gather "
            "comparable signals across multiple domains before making a more focused choice."
        )
    if starting_path is StartingPath.BROADEN_EXPLORATION:
        if request.career_goal_changed and request.contradictory_evidence:
            return (
                "The direction changed and you also reported conflicting signals, so the next step compares "
                "the current idea with another domain before narrowing the options."
            )
        if request.contradictory_evidence:
            return (
                "Conflicting signals make it premature to narrow to one pathway; compare the current direction "
                "with an unfamiliar domain through practical activities."
            )
        if (
            age_profile.mode is AgeMode.EXPLORE_AND_VALIDATE
            and request.unexplored_domains
            and request.journey_preference is JourneyPreference.AUTOMATIC
        ):
            return (
                "You have a stated direction and identified areas you have not yet tried. Compare the current "
                "direction with one of those unfamiliar domains before narrowing further."
            )
        return (
            "You indicated a high need for exploration while a current goal and some clarity are present, "
            "so a deliberate comparison can test whether the current direction is still the best one to explore."
        )
    if starting_path is StartingPath.VALIDATE_DECLARED_INTEREST:
        return (
            "You supplied a current direction with at least some clarity. Practical work samples can test "
            "that hypothesis before the system recommends a more committed development plan."
        )
    if starting_path is StartingPath.CAREER_DISCOVERY:
        if request.contradictory_evidence and request.career_goal_changed:
            return (
                "Because the goal changed and signals conflict, compare contrasting career families before "
                "assuming the previous direction or its evidence still applies."
            )
        if request.contradictory_evidence:
            return (
                "Conflicting signals or experiences argue against automatically turning the current goal into "
                "a gap plan. Broader work samples should clarify what to investigate next."
            )
        if request.exploration_need is Rating.HIGH:
            return "You indicated a high need for exploration, so this entry path compares different career families before optimization."
        if request.career_goal_changed:
            return "The goal changed and no clear new direction was supplied, so explore before choosing a new target."
        if request.career_clarity is Rating.LOW:
            return "A goal may be present, but you reported low clarity; explore contrasting career families before choosing a target."
        return "A clear current direction is not yet available, so explore contrasting career families before choosing a target."
    if starting_path is StartingPath.CAREER_GOAL_VALIDATION:
        if request.career_goal_changed:
            return (
                "Your goal changed recently. Even if earlier evidence is substantial, the current direction needs "
                "its own practical validation before a gap plan is produced."
            )
        return (
            "A current direction is available, but the submitted inputs do not justify skipping directly to gap analysis. "
            "Validate the goal against work samples and relevant role requirements first."
        )
    if starting_path is StartingPath.CAREER_GAP_ANALYSIS:
        return (
            "The current goal is clear, reported evidence coverage is substantial, practical experience is substantial, "
            "and no changed goal or conflicting signal was marked. This supports beginning with a requirements gap review; "
            "it does not prove that the career is the user's ideal path."
        )
    if starting_path is StartingPath.REENTER_DISCOVERY:
        return (
            "An explicit request to explore again takes priority over automatic narrowing, while the activity style "
            "remains appropriate for the user's age group."
        )
    # Defensive fallback; all enum values above are handled explicitly.
    return f"The selected path is {STARTING_PATH_LABELS[starting_path]} based on the submitted context."


def _build_rationale(
    request: CalibrationRequest,
    age_profile: AgeProfile,
    evidence_strength: EvidenceStrength,
    starting_path: StartingPath,
) -> list[str]:
    reasons = [
        (
            f"Age {request.age} selects the {age_profile.band.value} experience: "
            f"{AGE_MODE_LABELS[age_profile.mode]}. Age determines the activity style, not presumed ability."
        )
    ]

    if request.prior_evidence_count == 0 and not request.prior_activity_summary:
        reasons.append(
            "No prior evidence was reported. That means the profile is unknown at this point, "
            "not that the user has low ability."
        )
    elif request.prior_evidence_count == 0 and request.prior_activity_summary:
        reasons.append(
            "A prior-activity summary was supplied without a numeric count. It is treated as one "
            "unquantified self-reported context item for evidence coverage and is not independently verified."
        )
    else:
        reasons.append(
            f"The request reports {request.prior_evidence_count} prior evidence item(s) with "
            f"self-described quality '{request.prior_evidence_quality.value}'. This indicates "
            f"{EVIDENCE_STRENGTH_LABELS[evidence_strength].lower()}, not talent or future success."
        )

    reasons.append(
        f"Career clarity is self-described as '{request.career_clarity.value}', and exploration need "
        f"as '{request.exploration_need.value}'. These inputs help select the next activity style."
    )

    if request.prior_activity_summary:
        reasons.append(
            "A summary of activities already tried was supplied. It can guide the next challenge, "
            "but is not treated as independently verified performance evidence."
        )

    if request.current_goal:
        reasons.append(
            f"The stated direction '{request.current_goal}' is treated as a hypothesis to test, not a verdict."
        )
    else:
        reasons.append("No current career direction was supplied, so the system does not invent one.")

    if request.prior_projects_experience is not ExperienceLevel.NONE:
        reasons.append(
            f"Prior practical experience is self-described as '{request.prior_projects_experience.value}'."
        )

    if request.unexplored_domains:
        domain_names = [EXPLORATION_DOMAIN_LABELS[domain] for domain in request.unexplored_domains]
        reasons.append(
            "You marked areas with limited prior exposure: "
            + ", ".join(domain_names)
            + ". These are exploration opportunities, not areas of weakness."
        )

    if age_profile.mode is AgeMode.DEVELOP_AND_OPTIMIZE:
        if request.education_summary or request.skills_summary or request.experience_summary:
            provided_context = []
            if request.education_summary:
                provided_context.append("education/training")
            if request.skills_summary:
                provided_context.append("self-described skills")
            if request.experience_summary:
                provided_context.append("project/work experience")
            reasons.append(
                "Adult planning context was provided for: " + ", ".join(provided_context) + "."
            )
        if request.planning_constraints:
            reasons.append(
                "Optional planning constraints were supplied. Later planning should account for them, "
                "without treating them as career suitability signals."
            )
        if request.desired_timeline is not DesiredTimeline.UNSPECIFIED:
            reasons.append(
                f"Desired planning timeline was specified as {TIMELINE_LABELS[request.desired_timeline]}. "
                "This informs planning horizon, not career worth or ability."
            )

    if request.contradictory_evidence:
        reasons.append(
            "You reported conflicting signals. The calibration favors exploring more broadly "
            "rather than prematurely narrowing to one direction."
        )
    if request.career_goal_changed and request.contradictory_evidence:
        reasons.append(
            "Both a recent goal change and conflicting signals were reported. The selected path will compare "
            "the current direction with alternatives instead of assuming older evidence transfers directly."
        )
    if request.career_goal_changed:
        reasons.append(
            "You marked that your career goal changed. Earlier evidence may not answer the new goal, "
            "so the next step should validate the current direction rather than assume continuity."
        )
    if request.reenter_discovery:
        reasons.append(
            "You requested a fresh discovery cycle; this preference is honored within the age-appropriate experience."
        )
    elif request.journey_preference is not JourneyPreference.AUTOMATIC:
        reasons.append(
            f"Your requested journey preference '{request.journey_preference.value}' was considered, "
            "while age-appropriate guardrails remain in place."
        )

    if age_profile.mode is AgeMode.DISCOVER_AND_SHAPE and request.journey_preference in {
        JourneyPreference.VALIDATE,
        JourneyPreference.OPTIMIZE,
    }:
        reasons.append(
            "For ages 10–14, a validation or optimisation request is translated into safe, broad exploration activities."
        )
    reasons.append(_starting_path_reason(request, age_profile, starting_path))

    return reasons


def calibrate_entry(request: CalibrationRequest) -> CalibrationResponse:
    """Return an explainable initial journey for the submitted user profile."""
    age_profile = _age_profile(request.age)
    evidence_strength = _evidence_strength(request)
    starting_path = _choose_starting_path(request, age_profile, evidence_strength)

    considered_inputs = [
        "age_band",
        "career_clarity",
        "prior_evidence_count",
        "prior_activity_summary",
        "prior_evidence_quality",
        "prior_projects_experience",
        "exploration_need",
        "current_goal_present_or_absent",
        "unexplored_domains",
        "adult_education_skills_experience_context",
        "optional_planning_constraints",
        "desired_timeline",
        "contradictory_evidence",
        "career_goal_changed",
        "reenter_discovery",
        "journey_preference",
    ]

    return CalibrationResponse(
        age_band=age_profile.band,
        age_mode=age_profile.mode,
        age_mode_label=AGE_MODE_LABELS[age_profile.mode],
        starting_path=starting_path,
        starting_path_label=STARTING_PATH_LABELS[starting_path],
        evidence_strength=evidence_strength,
        evidence_strength_label=EVIDENCE_STRENGTH_LABELS[evidence_strength],
        rationale=_build_rationale(request, age_profile, evidence_strength, starting_path),
        next_step=_select_next_step(request, starting_path),
        considered_inputs=considered_inputs,
        limitations=LIMITATIONS.copy(),
        calibration_version=CALIBRATION_VERSION,
    )
