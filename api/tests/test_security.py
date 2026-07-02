from datetime import timedelta

import jwt
import pytest
from pydantic import ValidationError

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.schemas.auth import LoginRequest, RegisterRequest


def test_password_requires_eight_characters_and_a_number() -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(name="Ana Silva", email="ana@example.com", password="curta1", accepted_terms=True)

    with pytest.raises(ValidationError):
        RegisterRequest(name="Ana Silva", email="ana@example.com", password="semsenha", accepted_terms=True)

    valid = RegisterRequest(name="Ana Silva", email="ana@example.com", password="segura123", accepted_terms=True)
    assert valid.password == "segura123"


def test_password_is_hashed_with_bcrypt_and_can_be_verified() -> None:
    password_hash = hash_password("segura123")

    assert password_hash != "segura123"
    assert password_hash.startswith("$2")
    assert verify_password("segura123", password_hash)
    assert not verify_password("errada123", password_hash)


def test_password_rejects_more_than_72_utf8_bytes_with_clear_message() -> None:
    password = ("á" * 36) + "1"

    with pytest.raises(ValidationError) as error:
        RegisterRequest(name="Ana Silva", email="ana@example.com", password=password, accepted_terms=True)

    assert "72 bytes em UTF-8" in str(error.value)


def test_bcrypt_never_accepts_distinct_passwords_with_same_72_byte_prefix() -> None:
    first = ("a" * 71) + "1x"
    second = ("a" * 71) + "1y"

    with pytest.raises(ValueError, match="72 bytes"):
        hash_password(first)
    with pytest.raises(ValueError, match="72 bytes"):
        hash_password(second)


def test_access_and_refresh_tokens_use_distinct_secrets_and_expected_ttls() -> None:
    access = create_access_token(user_id=7)
    refresh, claims = create_refresh_token(user_id=7)

    access_claims = decode_access_token(access)
    refresh_claims = jwt.decode(
        refresh, settings.jwt_refresh_secret, algorithms=[settings.jwt_algorithm]
    )

    assert access_claims["sub"] == "7"
    assert access_claims["type"] == "access"
    assert refresh_claims["type"] == "refresh"
    assert claims["jti"] == refresh_claims["jti"]
    assert access_claims["exp"] - access_claims["iat"] == int(
        timedelta(minutes=15).total_seconds()
    )
    assert refresh_claims["exp"] - refresh_claims["iat"] == int(
        timedelta(days=7).total_seconds()
    )

    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(access, settings.jwt_refresh_secret, algorithms=[settings.jwt_algorithm])
    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(refresh, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def test_refresh_token_hash_is_stable_and_does_not_store_plaintext() -> None:
    token, _ = create_refresh_token(user_id=3)

    digest = hash_refresh_token(token)

    assert digest == hash_refresh_token(token)
    assert digest != token
    assert len(digest) == 64


def test_jwt_decode_requires_standard_and_token_specific_claims() -> None:
    incomplete_access = jwt.encode(
        {"sub": "7", "type": "access"},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    incomplete_refresh = jwt.encode(
        {"sub": "7", "type": "refresh", "iat": 1, "exp": 4_102_444_800, "jti": "x"},
        settings.jwt_refresh_secret,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(jwt.MissingRequiredClaimError):
        decode_access_token(incomplete_access)
    with pytest.raises(jwt.MissingRequiredClaimError):
        from app.core.security import decode_refresh_token

        decode_refresh_token(incomplete_refresh)
