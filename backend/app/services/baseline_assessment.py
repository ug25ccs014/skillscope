from __future__ import annotations
from datetime import UTC, datetime
from uuid import UUID, uuid4
from app.schemas.baseline_assessment import *
from app.schemas.student_evidence import EvidenceCreate, EvidenceSourceKind, EvidenceType, SignalDimension, UncertaintyLevel, UserInterpretation
from app.services.evidence_ledger import EvidenceLedgerRepository

VERSION = "baseline-exploratory-v1.0"
NOTICE = "This is an initial snapshot. It will improve as you try activities and share feedback. It is exploratory, not a validated psychometric assessment or a final career verdict."
DOMAINS = list(BaselineDomain)

PROMPTS = {
 BaselineDomain.LOGIC_DATA: ("You get a small pattern, table, or number puzzle. What would you try first, and what would you look for?", "Give a short answer; there is no single correct approach."),
 BaselineDomain.SCIENCE_RESEARCH: ("Choose one everyday question you would genuinely like to investigate. What would you observe or test first?", "State a question and one observation or test."),
 BaselineDomain.TECHNOLOGY: ("A simple tool or app behaves unexpectedly. What is the first safe thing you would try to understand or change?", "Describe your first troubleshooting step."),
 BaselineDomain.DESIGN_CREATIVE: ("You need to make an idea easier to understand or more appealing. What could you change or experiment with?", "Describe one possible change."),
 BaselineDomain.COMMUNICATION: ("Someone misunderstands an idea you explained. How would you adapt your explanation?", "Give one concrete adaptation."),
 BaselineDomain.HELPING_SOCIAL: ("Someone is struggling with a problem. What would you want to understand before suggesting a solution?", "Give one question you would ask."),
 BaselineDomain.BUSINESS: ("You have an idea for something people might use. What would you want to learn before building it?", "Name one user, need, or constraint you would investigate."),
 BaselineDomain.HANDS_ON_SPATIAL: ("You need to assemble or arrange something unfamiliar. How would you plan the first few steps?", "Describe how you would inspect parts, sequence, or fit."),
 BaselineDomain.ENVIRONMENT: ("You notice an environmental problem nearby. What would you observe or measure before deciding what to do?", "Name one useful observation or measurement."),
}

AGE_FRAMING = {
 AgeBand.AGE_10_14: "Keep this playful and exploratory. You are not being matched to a career.",
 AgeBand.AGE_15_17: "Use this to check current interests and identify areas you have not yet had a chance to try.",
 AgeBand.AGE_18_PLUS: "Use this as a starting snapshot alongside your goals, education, projects, and experience.",
}

ACTIVITY_DOMAINS = {BaselineDomain.LOGIC_DATA, BaselineDomain.DESIGN_CREATIVE, BaselineDomain.HANDS_ON_SPATIAL}


OPTIONS = ["Not for me right now", "A little", "Somewhat", "Quite a lot", "Very much"]


def mode_for_age(age: AgeBand) -> BaselineMode:
    return {AgeBand.AGE_10_14: BaselineMode.DISCOVER_AND_SHAPE, AgeBand.AGE_15_17: BaselineMode.EXPLORE_AND_VALIDATE, AgeBand.AGE_18_PLUS: BaselineMode.DEVELOP_AND_OPTIMIZE}[age]

class BaselineAssessmentRepository:
    def __init__(self, db_path=None):
        self.evidence = EvidenceLedgerRepository(db_path) if db_path else EvidenceLedgerRepository()
        self.db_path = self.evidence.db_path
        self._init()
    def _connect(self): return self.evidence._connect()
    def _init(self):
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS baseline_assessments (
                assessment_id TEXT PRIMARY KEY, profile_id TEXT NOT NULL, age_band TEXT NOT NULL,
                mode TEXT NOT NULL, version TEXT NOT NULL, created_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'issued', submitted_at TEXT,
                FOREIGN KEY(profile_id) REFERENCES student_profiles(profile_id) ON DELETE CASCADE)""")
            db.execute("""CREATE TABLE IF NOT EXISTS baseline_responses (
                assessment_id TEXT NOT NULL, item_id TEXT NOT NULL, skipped INTEGER NOT NULL,
                answer TEXT, confidence INTEGER, recorded_at TEXT NOT NULL,
                PRIMARY KEY(assessment_id,item_id), FOREIGN KEY(assessment_id) REFERENCES baseline_assessments(assessment_id) ON DELETE CASCADE)""")
    def create(self, profile_id: UUID) -> BaselineAssessment:
        profile = self.evidence.get_profile(profile_id)
        if not profile: raise KeyError("profile")
        assessment_id = uuid4()
        items = []
        for i, domain in enumerate(DOMAINS, 1):
            prompt, instructions = PROMPTS[domain]
            is_activity = domain in ACTIVITY_DOMAINS
            item_type = BaselineItemType.MINI_ACTIVITY if is_activity else (BaselineItemType.REFLECTION if i % 2 == 0 else BaselineItemType.SELF_REPORT)
            prompt = f"{AGE_FRAMING[profile.age_band]} {prompt}"
            if is_activity:
                instructions = f"Mini activity: {instructions} Record what you actually did or produced; do not judge yourself."
            items.append(BaselineItem(item_id=f"{VERSION}-q{i:02d}", item_type=item_type, domain=domain, prompt=prompt, instructions=instructions, options=OPTIONS if item_type == BaselineItemType.SELF_REPORT else [], expected_minutes=2 if is_activity else 1, age_bands=[profile.age_band], rubric=["observable approach/output is described", "student may mark uncertainty"] if is_activity else []))
        with self._connect() as db:
            db.execute("INSERT INTO baseline_assessments VALUES (?,?,?,?,?,?,?,?)", (str(assessment_id), str(profile_id), profile.age_band.value, mode_for_age(profile.age_band).value, VERSION, datetime.now(UTC).replace(microsecond=0).isoformat(), "issued", None))
        return BaselineAssessment(assessment_id=assessment_id, profile_id=profile_id, age_band=profile.age_band, mode=mode_for_age(profile.age_band), version=VERSION, notice=NOTICE, items=items, expected_minutes=len(items))
    def get(self, assessment_id: UUID):
        with self._connect() as db:
            row = db.execute("SELECT * FROM baseline_assessments WHERE assessment_id=?", (str(assessment_id),)).fetchone()
        if not row: return None
        return row
    def submit(self, request: BaselineSubmission) -> BaselineResult:
        row = self.get(request.assessment_id)
        if not row: raise KeyError("assessment")
        if row["status"] == "submitted": raise ValueError("This baseline assessment has already been submitted; create a new baseline only if the student intentionally restarts the snapshot.")
        profile = self.evidence.get_profile(row["profile_id"])
        if not profile: raise KeyError("profile")
        valid_ids = {f"{VERSION}-q{i:02d}": d for i,d in enumerate(DOMAINS,1)}
        if any(r.item_id not in valid_ids for r in request.responses): raise ValueError("Response contains an unknown assessment item.")
        if len({r.item_id for r in request.responses}) != len(request.responses): raise ValueError("Each baseline item may be answered once.")
        evidence_count = 0
        results=[]
        with self._connect() as db:
            for response in request.responses:
                domain = valid_ids[response.item_id]
                db.execute("INSERT INTO baseline_responses VALUES (?,?,?,?,?,?)", (str(request.assessment_id), response.item_id, int(response.skipped), response.answer, response.confidence, datetime.now(UTC).replace(microsecond=0).isoformat()))
                if not response.skipped and response.answer:
                    item_is_activity = domain in ACTIVITY_DOMAINS
                    if item_is_activity:
                        evidence = EvidenceCreate(evidence_type=EvidenceType.CHALLENGE_PERFORMANCE, signal_dimension=SignalDimension.DEMONSTRATED_PERFORMANCE, title=f"Baseline activity: {domain.value}", observation=response.answer, domain=domain.value, source_kind=EvidenceSourceKind.CHALLENGE_RESULT, uncertainty=UncertaintyLevel.MEDIUM, user_interpretation=UserInterpretation.NOT_INTERPRETED, challenge_label=f"Baseline mini-activity: {domain.value}", rubric_name=f"{VERSION} observation rubric", rubric_version=VERSION, rubric_observations=[{"criterion":"observable approach/output","observation":response.answer}], reported_curiosity=response.confidence, context={"baseline_assessment_id": str(request.assessment_id), "baseline_version": VERSION, "domain": domain.value, "assessment_item_type":"mini_activity"})
                    else:
                        evidence = EvidenceCreate(evidence_type=EvidenceType.ACTIVITY_REFLECTION if response.item_id.endswith(("02","04","06","08")) else EvidenceType.STATED_INTEREST_GOAL, signal_dimension=SignalDimension.INTEREST, title=f"Baseline snapshot: {domain.value}", observation=response.answer, domain=domain.value, source_kind=EvidenceSourceKind.SELF_REPORT, uncertainty=UncertaintyLevel.MEDIUM if response.confidence in (None,3) else (UncertaintyLevel.LOW if response.confidence >=4 else UncertaintyLevel.HIGH), user_interpretation=UserInterpretation.NOT_INTERPRETED, reported_curiosity=response.confidence, context={"baseline_assessment_id": str(request.assessment_id), "baseline_version": VERSION, "domain": domain.value, "assessment_item_type":"self_report"})
                    self.evidence._insert_evidence(db, profile, evidence); evidence_count += 1
            db.execute("UPDATE baseline_assessments SET status='submitted', submitted_at=? WHERE assessment_id=?", (datetime.now(UTC).replace(microsecond=0).isoformat(), str(request.assessment_id)))
        for domain in DOMAINS:
            rs=[r for r in request.responses if valid_ids[r.item_id]==domain]
            answered=[r for r in rs if not r.skipped and r.answer]
            conf=any(r.confidence is not None for r in answered)
            results.append(BaselineDomainResult(domain=domain, evidence_status="unknown" if not answered else "exploratory_signal", response_count=len(answered), skipped_count=sum(r.skipped for r in rs), confidence_observed=conf, interpretation="An initial signal to explore, not evidence of ability or career fit." if answered else "No evidence collected; this domain remains unknown."))
        next_step = "Try a small challenge in one answered domain and one unfamiliar domain; use the observable result and your reflection to validate or revise this initial snapshot."
        return BaselineResult(assessment_id=request.assessment_id, profile_id=profile.profile_id, age_band=profile.age_band, mode=mode_for_age(profile.age_band), version=VERSION, statement=NOTICE, domain_results=results, evidence_created_count=evidence_count, next_step=next_step)
