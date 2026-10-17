"""Small, explicit student preference contract; no sensitive trait inference."""
from __future__ import annotations
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.schemas.challenges import ChallengeDomain
from app.schemas.discovery_loop import LoopPreference


class StudentPreferencesUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    journey_preference: LoopPreference = LoopPreference.BALANCED
    preferred_domains: list[ChallengeDomain] = Field(default_factory=list, max_length=9)
    accessibility_formats: list[str] = Field(default_factory=list, max_length=4)

    @field_validator("accessibility_formats")
    @classmethod
    def validate_accessibility_formats(cls, values: list[str]) -> list[str]:
        allowed = {"text", "spoken", "visual", "low_materials"}
        if any(value not in allowed for value in values):
            raise ValueError("Accessibility formats must be selected from text, spoken, visual, or low_materials.")
        return values


class StudentPreferences(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile_id: UUID
    journey_preference: LoopPreference = LoopPreference.BALANCED
    preferred_domains: list[ChallengeDomain] = Field(default_factory=list)
    accessibility_formats: list[str] = Field(default_factory=list)
    updated_at: datetime | None = None
    persisted: bool = False
