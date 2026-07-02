import ssl

import httpx
import pytest


def tls_details(valid=True):
    return {
        "valid": valid,
        "issuer": "Sentinel CA",
        "issued_at": None,
        "expires_at": "2030-01-01T00:00:00+00:00",
        "protocol": "TLSv1.3",
        "reason": None,
    }


@pytest.mark.asyncio
async def test_redirect_to_other_public_hostname_is_rejected():
    from app.services.web_auditor import URLValidationError, audit_web_endpoint

    async def handler(request):
        return httpx.Response(
            302,
            headers={"Location": "https://other.example/login"},
            request=request,
        )

    with pytest.raises(URLValidationError, match="alvo autorizado"):
        await audit_web_endpoint(
            "safe.example",
            "https://safe.example/",
            transport=httpx.MockTransport(handler),
            resolve_addresses=lambda target: ["93.184.216.34"],
            tls_inspector=lambda *args: tls_details(),
        )


@pytest.mark.asyncio
async def test_redirect_with_same_normalized_hostname_is_allowed():
    from app.services.web_auditor import audit_web_endpoint

    responses = iter(
        [
            httpx.Response(302, headers={"Location": "https://SAFE.EXAMPLE/login"}),
            httpx.Response(200),
        ]
    )

    async def handler(request):
        response = next(responses)
        response.request = request
        return response

    result = await audit_web_endpoint(
        "safe.example",
        "https://safe.example/",
        transport=httpx.MockTransport(handler),
        resolve_addresses=lambda target: ["93.184.216.34"],
        tls_inspector=lambda *args: tls_details(),
    )

    assert result["final_url"] == "https://SAFE.EXAMPLE/login"


@pytest.mark.asyncio
async def test_oversized_response_is_rejected_with_sanitized_error():
    from app.services.web_auditor import WebAuditFetchError, audit_web_endpoint

    async def handler(request):
        return httpx.Response(200, content=b"x" * 65, request=request)

    with pytest.raises(WebAuditFetchError) as error:
        await audit_web_endpoint(
            "safe.example",
            "http://safe.example/",
            transport=httpx.MockTransport(handler),
            resolve_addresses=lambda target: ["93.184.216.34"],
            max_response_bytes=64,
        )

    assert str(error.value) == "Resposta HTTP excede o limite permitido"
    assert "93.184.216.34" not in str(error.value)


def test_invalid_tls_decodes_binary_certificate_metadata_and_preserves_sni():
    from app.services.web_auditor import inspect_tls_certificate

    calls = []

    class FakeSocket:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    class FakeTLSSocket(FakeSocket):
        def getpeercert(self, binary_form=False):
            assert binary_form is True
            return b"fake-der-certificate"

        def version(self):
            return "TLSv1.2"

    class FakeContext:
        def __init__(self, verified):
            self.verified = verified

        def wrap_socket(self, sock, *, server_hostname):
            calls.append((self.verified, server_hostname))
            if self.verified:
                raise ssl.SSLCertVerificationError("secret certificate detail")
            return FakeTLSSocket()

    result = inspect_tls_certificate(
        "safe.example",
        "93.184.216.34",
        443,
        1,
        connection_factory=lambda *args, **kwargs: FakeSocket(),
        verified_context_factory=lambda: FakeContext(True),
        unverified_context_factory=lambda: FakeContext(False),
        der_decoder=lambda der: {
            "subject": ((("commonName", "safe.example"),),),
            "issuer": ((("commonName", "Fallback CA"),),),
            "notBefore": "Jan  1 00:00:00 2025 GMT",
            "notAfter": "Jan  1 00:00:00 2030 GMT",
        },
    )

    assert calls == [(True, "safe.example"), (False, "safe.example")]
    assert result["valid"] is False
    assert result["reason"] == "Falha na validação do certificado TLS"
    assert result["issuer"] == "commonName=Fallback CA"
    assert result["issued_at"] == "2025-01-01T00:00:00+00:00"
    assert result["expires_at"] == "2030-01-01T00:00:00+00:00"
    assert result["protocol"] == "TLSv1.2"
    assert "secret" not in str(result)


def test_tasks_package_exports_run_web_audit_literally():
    import app.tasks as tasks

    assert "run_web_audit" in tasks.__all__
    assert tasks.run_web_audit is not None
