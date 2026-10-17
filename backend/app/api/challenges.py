from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, HTTPException, Query
from app.schemas.challenges import AgeBand, ChallengeDomain, ChallengeSubmission, ChallengeScoreResult
from app.services.challenges import ChallengeRepository

router=APIRouter(prefix="/api/challenges",tags=["Challenge library"])

def repo(): return ChallengeRepository()

@router.get("")
def list_challenges(age_band: AgeBand|None=None, domain: ChallengeDomain|None=None):
    items=repo().list(age_band=age_band,domain=domain)
    return {"version":"challenge-library-v1.0","count":len(items),"items":[x.model_dump(mode="json") for x in items],"notice":"Challenges are SkillScope-authored exploratory activities. They are not validated psychometric instruments."}

@router.get("/{challenge_id}")
def get_challenge(challenge_id:str):
    ch=repo().get(challenge_id)
    if not ch: raise HTTPException(404,"Challenge not found.")
    return ch.model_dump(mode="json")

@router.post("/{challenge_id}/submissions",response_model=ChallengeScoreResult)
def submit(challenge_id:str,request:ChallengeSubmission):
    try: return repo().submit(challenge_id,request)
    except KeyError as exc: raise HTTPException(404,"Challenge or student profile not found.") from exc
    except ValueError as exc: raise HTTPException(422,str(exc)) from exc
