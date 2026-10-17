"""Deterministic, authored challenge library and reproducible scoring."""
from __future__ import annotations
import json, sqlite3
from datetime import UTC, datetime
from uuid import UUID, uuid4
from app.schemas.challenges import *
from app.schemas.student_evidence import EvidenceCreate, EvidenceSourceKind, EvidenceType, SignalDimension, UncertaintyLevel, UserInterpretation
from app.services.evidence_ledger import EvidenceLedgerRepository


def v(age, title, instructions, output, minutes, materials, access, prompts):
    return AgeVariant(age_band=age, title=title, instructions=instructions, expected_output=output, expected_minutes=minutes, materials=materials, accessibility_notes=access, reflection_prompts=prompts)

def c(cid, domain, skills, diff, safety, rubric, variants):
    return Challenge(challenge_id=cid, domain=domain, skill_tags=skills, difficulty=diff, safety_rating=safety, rubric=rubric, age_variants=variants)

A10, A15, A18 = AgeBand.AGE_10_14, AgeBand.AGE_15_17, AgeBand.AGE_18_PLUS
def R(criterion_id, label, observable_description, score_scale="0-2", max_score=2):
    return RubricCriterion(criterion_id=criterion_id, label=label, observable_description=observable_description, score_scale=score_scale, max_score=max_score)
CHALLENGES = [
 c("pattern-detective", ChallengeDomain.LOGIC_DATA,["pattern recognition","structured reasoning","data comparison"],Difficulty.GENTLE,SafetyRating.LOW,[R(criterion_id="identify",label="Identifies useful structure",observable_description="Points to a repeated pattern, category, comparison, or rule visible in the supplied data."),R(criterion_id="explain",label="Explains the reasoning",observable_description="Gives a checkable explanation for the proposed pattern or conclusion."),R(criterion_id="check",label="Checks the conclusion",observable_description="Tests the idea against at least one additional example or counterexample.")],[
  v(A10,"Pattern Detective","Sort a small set of everyday objects, numbers, or symbols into groups and explain one pattern you notice. Try a second example to see if your rule still works.","A grouped list plus a one-sentence rule and one check.",7,["paper and pencil"],[],["Which part felt easiest?","What would you test next?"]),
  v(A15,"Pattern Detective: Evidence Check","Given a small table supplied in the challenge screen, identify one pattern, explain why it may exist, then test your explanation against another row or a possible exception.","A short claim, evidence reference, and check.",10,["table shown in app"],[],["What evidence changed your confidence?","What would you need to know next?"]),
  v(A18,"Pattern Detective: Decision Signal","Use a small supplied dataset to identify a useful decision-relevant pattern. State the evidence, one limitation, and one follow-up check before acting on it.","A concise decision note with evidence, limitation, and follow-up.",12,["table shown in app"],[],["What makes the signal useful?","What could make it misleading?"]) ]),
 c("mini-investigation", ChallengeDomain.SCIENCE_RESEARCH,["question formation","observation","evidence recording"],Difficulty.STANDARD,SafetyRating.LOW,[R("question","Forms a testable question","The question can be investigated through observable evidence."),R("method","Plans an observable method","Names what will be changed/observed and how it will be recorded."),R("evidence","Records and interprets evidence","Separates an observation from an interpretation or conclusion.")],[
  v(A10,"Mini Investigation","Choose a safe everyday question such as which paper shape holds more coins. Make a simple plan, observe what happens, and record two observations.","A question, simple plan, and two observations.",12,["paper","coins or safe household objects"],["Can be done with spoken observations instead of writing."],["What surprised you?","What would you change next time?"]),
  v(A15,"Mini Investigation: Fair Test","Choose a low-risk everyday question. Define what you will observe, keep one factor consistent, and record a few observations. Do not use heat, chemicals, or unsafe equipment.","A testable question, method, and evidence table or notes.",15,["safe household materials"],["Use a template or voice notes."],["Was your test fair enough?","What evidence is still missing?"]),
  v(A18,"Mini Investigation: Evidence Memo","Design a small low-risk observational test relevant to daily life, collect a few observations, and write a brief memo separating findings, assumptions, and limitations.","A one-page evidence memo.",20,["safe everyday materials"],["Digital or spoken recording is acceptable."],["Which assumption matters most?","What follow-up would strengthen the conclusion?"]) ]),
 c("debug-the-process", ChallengeDomain.TECHNOLOGY,["debugging","sequencing","technical communication"],Difficulty.STANDARD,SafetyRating.LOW,[R("reproduce","Reproduces the issue", "Clearly describes or demonstrates the steps that lead to the unexpected result."),R("hypothesis","Tests a plausible cause","Chooses a small, relevant change or check instead of changing everything at once."),R("fix","Communicates the result","States what changed and whether the issue was resolved or remains uncertain.")],[
  v(A10,"Fix the Mixed-Up Instructions","A pretend robot follows a 6-step instruction list but does the wrong thing. Rearrange or edit the steps so the intended result is clear.","A corrected ordered instruction list.",8,["paper"],[],["Which step was confusing?","How would you explain the fix to a friend?"]),
  v(A15,"Debug the Process","Use a short flawed algorithm or spreadsheet-like sequence supplied in the challenge. Reproduce the error, propose one cause, test one change, and record the result.","Before/after steps and a short debugging note.",12,["challenge screen"],[],["What did you test first and why?","What remains uncertain?"]),
  v(A18,"Debugging Incident Note","Analyze a small reproducible workflow failure supplied in the challenge. Isolate one plausible cause, test a minimal change, and write a concise incident note with result and next action.","A reproducible bug report and test result.",15,["challenge screen"],[],["How did you avoid changing too much at once?","What evidence would confirm the root cause?"]) ]),
 c("redesign-it", ChallengeDomain.DESIGN_CREATIVE,["visual communication","iteration","constraint handling"],Difficulty.GENTLE,SafetyRating.LOW,[R("clarity","Makes the message clearer","The redesign makes the intended message or hierarchy easier to identify."),R("constraint","Follows the stated constraint","The output respects the required size, audience, or content constraint."),R("iteration","Shows a purposeful change","At least one change is connected to a stated problem or feedback.")],[
  v(A10,"Redesign It","Take a messy notice or simple drawing supplied in the challenge and redesign it so a younger student can understand it quickly. Keep the same core information.","One redesigned page or sketch.",10,["paper or drawing app"],["High-contrast or verbal layout description is acceptable."],["What did you make easier to notice?","What would you change after feedback?"]),
  v(A15,"Redesign It for a Real Audience","Redesign a small information card for a specified audience. Keep the required facts but change hierarchy, wording, or layout and explain one iteration.","A revised information card plus one design rationale.",15,["paper or design tool"],["Text-only wireframe accepted."],["Which audience need drove your choice?","What feedback would you seek?"]),
  v(A18,"Constraint-Based Redesign","Improve a supplied communication artifact for a specified audience and constraint. Make a first pass, identify one usability problem, then revise deliberately.","Before/after artifact or wireframe with rationale.",20,["paper or design tool"],["Text wireframe accepted."],["Which constraint shaped the design?","How would you validate it with users?"]) ]),
 c("three-minute-story", ChallengeDomain.COMMUNICATION,["story structure","audience awareness","concise explanation"],Difficulty.GENTLE,SafetyRating.LOW,[R("structure","Has a clear beginning, middle, and end","The message has an understandable sequence."),R("audience","Uses audience-appropriate language","The explanation avoids unnecessary jargon and matches the stated audience."),R("clarity","Communicates the main point","A listener/reader can identify the intended takeaway.")],[
  v(A10,"Three-Minute Story","Explain how to do a simple everyday task to someone who has never done it. Use a beginning, steps, and a final check.","A spoken or written explanation.",6,["none"],["Can be spoken, written, or recorded."],["What did you simplify?","Where might someone get confused?"]),
  v(A15,"Explain It to a Different Audience","Explain the same idea twice: once to a younger student and once to a technically curious peer. Keep the facts consistent but adapt the language.","Two short versions of the same explanation.",10,["none"],["Speech-to-text or bullet points accepted."],["What changed between versions?","Which version was harder and why?"]),
  v(A18,"Executive Brief","Turn a supplied complex idea into a short brief for a non-specialist decision-maker. Include the point, evidence, caveat, and next action.","A concise written or spoken brief.",12,["challenge prompt"],["Bullets or audio accepted."],["What did you leave out?","What could the audience misunderstand?"]) ]),
 c("helpful-solution", ChallengeDomain.HELPING_SOCIAL,["problem framing","active listening","solution constraints"],Difficulty.STANDARD,SafetyRating.LOW,[R("understand","Identifies the person's stated need","The response distinguishes the person's need from assumptions about them."),R("question","Asks a useful clarifying question","The question could materially improve understanding of the problem."),R("option","Proposes a feasible option","The proposed next step fits the stated constraints and does not claim to solve everything.")],[
  v(A10,"Help Without Guessing","Read a fictional scenario about a classmate struggling with a group task. Write one question you would ask before helping and one small, safe next step.","One clarifying question and one next step.",7,["scenario shown"],[],["Why did you ask that question?","What would you avoid assuming?"]),
  v(A15,"Support Plan","For a fictional scenario, identify the person's stated problem, ask two clarifying questions, and suggest one practical next step that respects their choice.","A short support plan.",10,["scenario shown"],[],["Which assumption did you avoid?","What would you ask before doing more?"]),
  v(A18,"Service Problem Framing","Analyze a fictional service-user problem. Separate stated need, assumptions, constraints, and one feasible next step; do not diagnose or make high-stakes claims.","A structured problem-framing note.",15,["scenario shown"],[],["Which uncertainty matters most?","How would you validate the need?"]) ]),
 c("tiny-business-test", ChallengeDomain.BUSINESS,["customer thinking","hypothesis testing","trade-off reasoning"],Difficulty.STANDARD,SafetyRating.LOW,[R("user","Defines a plausible user and need","Names who might use the idea and what need/problem is being addressed."),R("test","Chooses a useful small test","The proposed test could produce information before substantial effort is spent."),R("tradeoff","Recognizes a constraint or trade-off","Names at least one cost, risk, limitation, or competing priority.")],[
  v(A10,"Tiny Business Test","Imagine selling a simple useful item at a school fair. Pick a user, their need, and one question you would ask before making many copies.","User, need, and one test question.",8,["paper"],[],["What would you want to learn first?","What might make the idea less useful?"]),
  v(A15,"Tiny Business Experiment","Choose a simple product/service idea. Define a target user, key need, low-cost test, and one trade-off. Do not spend real money.","A one-page experiment plan.",12,["paper or notes app"],["No real purchasing required."],["What result would change your mind?","What trade-off matters most?"]),
  v(A18,"Pre-MVP Test Plan","For a hypothetical product/service, define a user problem, smallest informative test, success signal, and one commercial/operational trade-off. No real financial transaction is required.","A pre-MVP test plan.",15,["notes app"],["No real transaction required."],["What evidence would justify iteration?","What assumption is riskiest?"]) ]),
 c("build-a-bridge", ChallengeDomain.HANDS_ON_SPATIAL,["spatial planning","iteration","constraint management"],Difficulty.STANDARD,SafetyRating.LOW,[R("plan","Plans a sequence or structure","Shows a plausible order of assembly or arrangement before or during building."),R("constraint","Works within the constraint","The structure or arrangement respects the stated material/size rule."),R("iterate","Improves after observing the result","Makes a purposeful adjustment based on what happened.")],[
  v(A10,"Build a Paper Bridge","Using paper only, make a small bridge between two books that holds a few lightweight objects. Stop if materials become unsafe and use only ordinary paper.","A paper bridge plus a short build note.",12,["paper","two books"],["Can be planned with a sketch instead of built."],["What changed after your first attempt?","What made the structure stronger or weaker?"]),
  v(A15,"Bridge Challenge","Build a paper bridge between two supports using a stated paper limit. Record the plan, test with lightweight objects, and make one controlled improvement.","Sketch, bridge, test note, and revision.",18,["paper","two supports","lightweight objects"],["Virtual sketch-and-predict version accepted."],["Which change had the clearest effect?","What would you test next?"]),
  v(A18,"Constraint Build","Design and test a small paper structure under explicit material and span constraints. Document the initial design, observed failure/success, and one targeted revision.","Design sketch, test observation, and revision note.",20,["paper","two supports","lightweight objects"],["CAD/sketch-only alternative accepted."],["Which constraint dominated the design?","What evidence supports the revision?"]) ]),
 c("local-eco-audit", ChallengeDomain.ENVIRONMENT,["observation","systems thinking","evidence-based proposal"],Difficulty.GENTLE,SafetyRating.LOW,[R("observe","Records concrete observations","Uses observable features rather than unsupported claims."),R("connect","Identifies a plausible connection","Connects an observation to a possible environmental effect without presenting it as proven causation."),R("propose","Suggests a measurable next step","Proposes a practical observation, measurement, or small action that could generate more evidence.")],[
  v(A10,"Local Eco Audit","Choose a safe place you know, such as a classroom or park. Record three things you notice about waste, shade, water, plants, or energy use. Do not enter restricted areas.","Three observations and one question.",8,["paper or phone notes"],["Can be completed from memory or a photo supplied by an adult; no location sharing required."],["Which observation was easiest to verify?","What would you measure next?"]),
  v(A15,"Local Eco Audit","Make a small observation checklist for a familiar safe place. Record several observations and propose one measurable next step. Do not collect personal data or enter restricted areas.","Checklist, observations, and one measurable next step.",12,["paper or notes app"],["No precise location needs to be recorded."],["Which observation is strongest?","What could bias your observation?"]),
  v(A18,"Environmental Evidence Note","Conduct a small, safe observational audit of a familiar setting. Distinguish observations from assumptions and propose one low-risk measurement or intervention to test.","A concise evidence note with observations and next test.",15,["paper or notes app"],["No precise location or personal data required."],["What evidence is missing?","How would you test the proposed change?"]) ]),
 c("data-story", ChallengeDomain.LOGIC_DATA,["data visualization","comparison","communication"],Difficulty.STANDARD,SafetyRating.LOW,[R("select","Selects relevant data","Chooses values that directly support the stated question."),R("represent","Represents data understandably","Uses a simple table, chart, or ordered list that matches the data."),R("interpret","States a bounded conclusion","Conclusion stays within what the supplied data can support.")],[
  v(A10,"Tell a Data Story","Turn a tiny list of counts supplied in the challenge into a simple picture, table, or bar sketch and say one thing it shows.","One simple representation and one bounded conclusion.",8,["paper or drawing app"],["Can describe the representation verbally."],["What did your picture make easier to see?","What can the data not tell you?"]),
  v(A15,"Data Story","Create a simple visual from a small supplied dataset and write two observations plus one thing the data cannot establish.","Chart/table plus observations and limitation.",12,["paper or spreadsheet if available"],["Hand-drawn chart accepted."],["Why did you choose that representation?","What would more data change?"]),
  v(A18,"Decision Data Brief","Build a compact visual from supplied data for a defined decision. State two evidence-backed observations, one limitation, and avoid causal claims the data cannot support.","Decision visual and evidence note.",15,["paper or spreadsheet"],["Hand-drawn chart accepted."],["Which limitation is most important?","What additional data would reduce uncertainty?"]) ]),
 c("idea-to-prototype", ChallengeDomain.DESIGN_CREATIVE,["ideation","prototyping","feedback use"],Difficulty.STRETCH,SafetyRating.LOW,[R("ideas","Generates distinct options","Produces more than one meaningfully different approach."),R("prototype","Makes a testable representation","Creates a sketch, flow, mock-up, or simple prototype that communicates how the idea works."),R("feedback","Uses feedback purposefully","Makes a revision connected to a specific observation or feedback point.")],[
  v(A10,"Idea to Prototype","Think of a small improvement to a classroom or home routine. Sketch two different ideas, pick one, and make a simple paper prototype.","Two ideas, one prototype, one revision note.",12,["paper","pencil"],["Verbal walkthrough accepted."],["Which idea changed most?","What feedback would help?"]),
  v(A15,"Idea to Prototype","Identify a small user problem, generate two different concepts, build a low-fidelity prototype of one, and revise it after a self-check or peer feedback.","Problem statement, two concepts, prototype, revision.",18,["paper","simple craft materials"],["Wireframe or verbal prototype accepted."],["Which feedback mattered?","What remains untested?"]),
  v(A18,"Prototype Sprint","Frame a small user problem, generate alternatives, build a low-fidelity prototype, and revise once based on a defined feedback question. No real-world deployment is required.","Problem frame, alternatives, prototype, revision rationale.",22,["paper or digital design tool"],["Wireframe accepted."],["Which assumption remains risky?","What test would you run next?"]) ]),
 c("process-map", ChallengeDomain.TECHNOLOGY,["process mapping","systems thinking","clarity"],Difficulty.STANDARD,SafetyRating.LOW,[R("sequence","Captures the key sequence","The process map preserves the important order or decision points."),R("decision","Shows a decision or exception","At least one branch, exception, or alternative path is represented where relevant."),R("clarity","Makes the process inspectable","Another person could follow the map without guessing the intended flow.")],[
  v(A10,"Map a Routine","Draw the steps for a familiar routine such as packing a school bag. Include one 'if something is missing' branch.","A simple process map.",8,["paper"],[],["Which step was easy to forget?","What would make the map clearer?"]),
  v(A15,"Map a Real Workflow","Choose a familiar non-sensitive workflow and map its steps, one decision point, and one exception. Avoid recording personal or confidential information.","A process map with one branch.",12,["paper or diagram tool"],["List format accepted."],["Where could the process fail?","What would you simplify?"]),
  v(A18,"Workflow Model","Model a small non-sensitive workflow with sequence, decision points, and an exception path. Add one improvement hypothesis without claiming measured impact.","An inspectable workflow model and improvement hypothesis.",15,["paper or diagram tool"],["Text outline accepted."],["Which dependency is easy to miss?","How would you test the improvement?"]) ]),
]

LIBRARY = {x.challenge_id: x for x in CHALLENGES}

class ChallengeRepository:
    def __init__(self, db_path=None):
        self.evidence = EvidenceLedgerRepository(db_path) if db_path else EvidenceLedgerRepository()
        self.db_path = self.evidence.db_path
        with self.evidence._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS challenge_submissions (
                submission_id TEXT PRIMARY KEY, challenge_id TEXT NOT NULL, challenge_version TEXT NOT NULL,
                profile_id TEXT NOT NULL, age_band TEXT NOT NULL, output TEXT NOT NULL,
                rubric_results_json TEXT NOT NULL, objective_score INTEGER, objective_max_score INTEGER,
                evidence_status TEXT NOT NULL, reflections_json TEXT NOT NULL, evidence_id TEXT,
                created_at TEXT NOT NULL, user_interpretation TEXT NOT NULL DEFAULT 'not_interpreted',
                FOREIGN KEY(profile_id) REFERENCES student_profiles(profile_id) ON DELETE CASCADE)""")
            # Safe, additive migration for databases created by the Stage 10 checkpoint.
            columns = {row["name"] for row in db.execute("PRAGMA table_info(challenge_submissions)").fetchall()}
            if "user_interpretation" not in columns:
                db.execute("ALTER TABLE challenge_submissions ADD COLUMN user_interpretation TEXT NOT NULL DEFAULT 'not_interpreted'")

    def list(self, age_band: AgeBand | None = None, domain: ChallengeDomain | None = None):
        out=[]
        for ch in CHALLENGES:
            if domain and ch.domain != domain: continue
            for av in ch.age_variants:
                if age_band and av.age_band != age_band: continue
                out.append(ChallengeListItem(challenge_id=ch.challenge_id,version=ch.version,domain=ch.domain,skill_tags=ch.skill_tags,difficulty=ch.difficulty,safety_rating=ch.safety_rating,content_origin=ch.content_origin,title=av.title,expected_minutes=av.expected_minutes,age_band=av.age_band))
        return out

    def get(self, cid): return LIBRARY.get(cid)

    def submit(self, challenge_id: str, request: ChallengeSubmission) -> ChallengeScoreResult:
        ch=self.get(challenge_id)
        if not ch: raise KeyError("challenge")
        profile=self.evidence.get_profile(request.profile_id)
        if not profile: raise KeyError("profile")
        variant=next(v for v in ch.age_variants if v.age_band==profile.age_band)
        ids={r.criterion_id:r for r in ch.rubric}
        if len({x.criterion_id for x in request.rubric_observations}) != len(request.rubric_observations): raise ValueError("Each rubric criterion may be observed at most once.")
        unknown=set(x.criterion_id for x in request.rubric_observations)-set(ids)
        if unknown: raise ValueError(f"Unknown rubric criterion: {sorted(unknown)[0]}")
        rows=[]; observed=0; total=0; max_total=0
        for criterion in ch.rubric:
            item=next((x for x in request.rubric_observations if x.criterion_id==criterion.criterion_id),None)
            score=item.score if item else None
            if score is not None and score>criterion.max_score: raise ValueError(f"Score for {criterion.criterion_id} exceeds its rubric scale.")
            if score is not None: observed+=1; total+=score; max_total+=criterion.max_score
            rows.append(CriterionResult(criterion_id=criterion.criterion_id,label=criterion.label,score=score,observation=item.observation if item else "Not observed in this submission.",max_score=criterion.max_score))
        status=EvidenceStatus.EVIDENCE_AVAILABLE if observed>=variant.minimum_observed_criteria else (EvidenceStatus.PARTIAL if observed else EvidenceStatus.NOT_ENOUGH_EVIDENCE)
        score=total if status!=EvidenceStatus.NOT_ENOUGH_EVIDENCE else None
        scoremax=max_total if status!=EvidenceStatus.NOT_ENOUGH_EVIDENCE else None
        sid=uuid4(); evidence_id=None
        reflections={"enjoyment":request.enjoyment,"difficulty":request.difficulty_reported,"confidence":request.confidence,"willingness_to_continue":request.willingness_to_continue,"reflection":request.reflection}
        explanation=(f"Observed {observed} of {len(ch.rubric)} rubric criteria. " + ("The objective result is reproducible from the criterion observations shown." if score is not None else "There is not enough observed rubric evidence to report an objective score."))
        now=datetime.now(UTC).replace(microsecond=0).isoformat()
        with self.evidence._connect() as db:
            # Evidence is created in the same transaction as the submission.
            evidence=EvidenceCreate(evidence_type=EvidenceType.CHALLENGE_PERFORMANCE,signal_dimension=SignalDimension.DEMONSTRATED_PERFORMANCE,title=f"Challenge: {variant.title}",observation=f"Submitted output: {request.output[:1800]}",source_kind=EvidenceSourceKind.CHALLENGE_RESULT,uncertainty=UncertaintyLevel.LOW if status==EvidenceStatus.EVIDENCE_AVAILABLE else UncertaintyLevel.HIGH,user_interpretation=request.hypothesis_interpretation,domain=ch.domain.value,challenge_label=variant.title,rubric_name=f"{challenge_id}-rubric",rubric_version=ch.version,rubric_observations=[{"criterion":r.label,"observation":r.observation,"score":r.score,"score_scale":(f"0-{r.max_score}" if r.score is not None else None)} for r in rows],reported_enjoyment=request.enjoyment,reported_difficulty=request.difficulty_reported,reported_curiosity=None,context={"challenge_id":challenge_id,"challenge_version":ch.version,"age_band":profile.age_band.value,"objective_evidence_status":status.value,"objective_score":score,"objective_max_score":scoremax,"self_reported_confidence":request.confidence,"willingness_to_continue":request.willingness_to_continue,"hypothesis_interpretation":request.hypothesis_interpretation.value})
            evidence_id=UUID(self.evidence._insert_evidence(db,profile,evidence))
            db.execute(
                """INSERT INTO challenge_submissions (
                    submission_id, challenge_id, challenge_version, profile_id, age_band, output,
                    rubric_results_json, objective_score, objective_max_score, evidence_status,
                    reflections_json, evidence_id, created_at, user_interpretation
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (str(sid),challenge_id,ch.version,str(profile.profile_id),profile.age_band.value,request.output,
                 json.dumps([r.model_dump(mode="json") for r in rows],sort_keys=True),score,scoremax,status.value,
                 json.dumps(reflections,sort_keys=True),str(evidence_id),now,request.hypothesis_interpretation.value)
            )
        return ChallengeScoreResult(submission_id=sid,challenge_id=challenge_id,challenge_version=ch.version,profile_id=profile.profile_id,age_band=profile.age_band,evidence_status=status,observed_criteria=observed,required_observed_criteria=variant.minimum_observed_criteria,objective_score=score,objective_max_score=scoremax,criteria=rows,reflections_recorded=any(x is not None for x in reflections.values()),evidence_created_id=evidence_id,explanation=explanation,hypothesis_interpretation=request.hypothesis_interpretation)
