from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TargetCreate(BaseModel):
    target: str = Field(min_length=1, max_length=255)
    confirmed: bool
    evidence: str = Field(min_length=1, max_length=1000)
    expires_at: datetime

    @field_validator("confirmed")
    @classmethod
    def confirmation_required(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("A autorização deve ser confirmada explicitamente")
        return value

    @field_validator("expires_at")
    @classmethod
    def expiry_must_be_future(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value <= datetime.now(timezone.utc):
            raise ValueError("A validade deve ser uma data futura com fuso horário")
        return value


class TargetRenew(BaseModel):
    confirmed: bool
    expires_at: datetime

    _confirmation_required = field_validator("confirmed")(TargetCreate.confirmation_required.__func__)
    _expiry_must_be_future = field_validator("expires_at")(TargetCreate.expiry_must_be_future.__func__)


class TargetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    target: str
    evidence: str
    confirmed: bool
    expires_at: datetime
    active: bool
    created_at: datetime
    updated_at: datetime
