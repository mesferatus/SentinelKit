from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.security import validate_bcrypt_password_length


class CredentialsRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
            raise ValueError("E-mail inválido")
        return normalized

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < 8 or not any(character.isdigit() for character in value):
            raise ValueError("A senha deve ter ao menos 8 caracteres e 1 número")
        validate_bcrypt_password_length(value)
        return value


class RegisterRequest(CredentialsRequest):
    name: str
    accepted_terms: bool

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if len(value.strip()) < 2:
            raise ValueError("Informe seu nome completo")
        return value.strip()

    @field_validator("accepted_terms")
    @classmethod
    def validate_terms(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("É necessário aceitar os termos de uso ético")
        return value


class LoginRequest(CredentialsRequest):
    pass


class ProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str
    email: str
    password: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if len(value.strip()) < 2:
            raise ValueError("Informe seu nome")
        return value.strip()

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
            raise ValueError("E-mail inválido")
        return normalized

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str | None) -> str | None:
        if value in (None, ""):
            return None
        if len(value) < 8 or not any(character.isdigit() for character in value):
            raise ValueError("A senha deve ter ao menos 8 caracteres e 1 número")
        validate_bcrypt_password_length(value)
        return value


class UserProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str


class AuthResponse(BaseModel):
    message: str
    user: UserProfile
