from __future__ import annotations

import os
import socket
import ssl
import tempfile
from datetime import datetime, timezone
from http.cookies import SimpleCookie
from ipaddress import ip_address
from typing import Any, Callable
from urllib.parse import urljoin, urlsplit

import httpx

from app.core.config import settings
from app.core.targets import resolve_validated_addresses, target_hostname

REDIRECT_STATUS_CODES = {301, 302, 303, 307, 308}

Resolver = Callable[[str], list[str]]
TLSInspector = Callable[[str, str, int, float], dict[str, Any]]
DERDecoder = Callable[[bytes], dict[str, Any]]


class URLValidationError(ValueError):
    pass


class WebAuditFetchError(RuntimeError):
    pass


def validate_webaudit_url(target: str, url: str) -> str:
    candidate = url.strip()
    parsed = urlsplit(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise URLValidationError("A URL deve usar http ou https e possuir hostname")
    if parsed.username or parsed.password:
        raise URLValidationError("Credenciais na URL nao sao aceitas")

    expected_host, expected_port = _split_target(target)
    actual_host = _normalize_host(parsed.hostname)
    if actual_host != expected_host:
        raise URLValidationError("A URL deve permanecer no alvo autorizado")

    if expected_port is not None:
        actual_port = parsed.port or _default_port(parsed.scheme)
        if actual_port != expected_port:
            raise URLValidationError("A porta da URL deve corresponder ao alvo autorizado")

    return candidate


async def audit_web_endpoint(
    target: str,
    url: str,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
    resolve_addresses: Resolver = resolve_validated_addresses,
    tls_inspector: TLSInspector | None = None,
    timeout: float | None = None,
    max_redirects: int | None = None,
    max_response_bytes: int | None = None,
) -> dict[str, Any]:
    request_timeout = settings.web_audit_timeout_seconds if timeout is None else timeout
    redirect_limit = (
        settings.web_audit_max_redirects if max_redirects is None else max_redirects
    )
    response_limit = (
        settings.web_audit_max_response_bytes
        if max_response_bytes is None
        else max_response_bytes
    )
    tls_lookup = inspect_tls_certificate if tls_inspector is None else tls_inspector
    current_url = validate_webaudit_url(target, url)
    redirects: list[dict[str, Any]] = []
    final_response: httpx.Response | None = None
    final_ip: str | None = None

    async with httpx.AsyncClient(
        follow_redirects=False,
        timeout=request_timeout,
        transport=transport,
        trust_env=False,
    ) as client:
        for redirect_count in range(redirect_limit + 1):
            current_url = validate_webaudit_url(target, current_url)
            parsed = urlsplit(current_url)
            approved_ip = _pick_approved_ip(
                resolve_addresses(_target_from_url(parsed.hostname or "", parsed.port))
            )
            final_response = await _send_pinned_request(
                client, current_url, approved_ip, response_limit
            )
            final_ip = approved_ip

            if (
                final_response.status_code not in REDIRECT_STATUS_CODES
                or "location" not in final_response.headers
            ):
                break

            if redirect_count >= redirect_limit:
                raise URLValidationError("Limite de redirects excedido")

            next_url = validate_webaudit_url(
                target,
                urljoin(current_url, final_response.headers["location"]),
            )
            redirects.append(
                {
                    "from": current_url,
                    "to": next_url,
                    "status_code": final_response.status_code,
                }
            )
            current_url = next_url

    if final_response is None or final_ip is None:
        raise RuntimeError("Falha ao obter resposta do alvo")

    final_parsed = urlsplit(current_url)
    tls = None
    if final_parsed.scheme == "https":
        tls = tls_lookup(
            _normalize_host(final_parsed.hostname or ""),
            final_ip,
            final_parsed.port or 443,
            request_timeout,
        )

    cookie_reports = _parse_cookie_headers(final_response.headers.get_list("set-cookie"))
    header_report = _analyze_headers(final_response.headers, final_parsed.scheme)
    score, recommendations = _score_audit(
        header_report,
        cookie_reports,
        tls,
        final_parsed.scheme,
    )

    return {
        "requested_url": url,
        "final_url": current_url,
        "status_code": final_response.status_code,
        "redirects": redirects,
        "headers": header_report,
        "cookies": cookie_reports,
        "tls": tls,
        "score": score,
        "recommendations": recommendations,
    }


def inspect_tls_certificate(
    hostname: str,
    ip_address_text: str,
    port: int,
    timeout: float,
    *,
    connection_factory=socket.create_connection,
    verified_context_factory=ssl.create_default_context,
    unverified_context_factory=None,
    der_decoder: DERDecoder | None = None,
) -> dict[str, Any]:
    context = verified_context_factory()
    issued_at = None
    expires_at = None
    protocol = None
    issuer = None
    valid = False

    reason = None

    try:
        with connection_factory((ip_address_text, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as tls_socket:
                certificate = tls_socket.getpeercert()
                protocol = tls_socket.version()
                issuer = _format_certificate_issuer(certificate)
                issued_at = _parse_cert_time(certificate.get("notBefore"))
                expires_at = _parse_cert_time(certificate.get("notAfter"))
                valid = expires_at is not None and expires_at > datetime.now(timezone.utc)
    except ssl.SSLCertVerificationError:
        reason = "Falha na validação do certificado TLS"
        if unverified_context_factory is None:
            unverified_context = ssl.create_default_context()
            unverified_context.check_hostname = False
            unverified_context.verify_mode = ssl.CERT_NONE
        else:
            unverified_context = unverified_context_factory()
        try:
            with connection_factory((ip_address_text, port), timeout=timeout) as sock:
                with unverified_context.wrap_socket(
                    sock, server_hostname=hostname
                ) as tls_socket:
                    certificate_der = tls_socket.getpeercert(binary_form=True)
                    certificate = (
                        (der_decoder or _decode_der_certificate)(certificate_der)
                        if certificate_der
                        else {}
                    )
                    protocol = tls_socket.version()
                    issuer = _format_certificate_issuer(certificate)
                    issued_at = _parse_cert_time(certificate.get("notBefore"))
                    expires_at = _parse_cert_time(certificate.get("notAfter"))
        except (OSError, ValueError, ssl.SSLError):
            pass
    except OSError:
        valid = False

    return {
        "valid": valid,
        "issuer": issuer,
        "issued_at": issued_at.isoformat() if issued_at else None,
        "expires_at": expires_at.isoformat() if expires_at else None,
        "protocol": protocol,
        "reason": reason,
    }


async def _send_pinned_request(
    client: httpx.AsyncClient,
    url: str,
    approved_ip: str,
    max_response_bytes: int,
) -> httpx.Response:
    parsed = urlsplit(url)
    request = client.build_request(
        "GET",
        _build_pinned_url(parsed, approved_ip),
        headers={"Host": _host_header(parsed)},
    )
    request.extensions["sni_hostname"] = _normalize_host(parsed.hostname or "")
    response = await client.send(request, stream=True)
    content = bytearray()
    try:
        async for chunk in response.aiter_bytes():
            content.extend(chunk)
            if len(content) > max_response_bytes:
                raise WebAuditFetchError(
                    "Resposta HTTP excede o limite permitido"
                )
    finally:
        await response.aclose()
    return httpx.Response(
        response.status_code,
        headers=response.headers,
        content=bytes(content),
        request=request,
    )


def _build_pinned_url(parsed, approved_ip: str) -> str:
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"

    rendered_ip = approved_ip
    try:
        if ip_address(approved_ip).version == 6:
            rendered_ip = f"[{approved_ip}]"
    except ValueError:
        pass

    port_suffix = f":{parsed.port}" if parsed.port is not None else ""
    return f"{parsed.scheme}://{rendered_ip}{port_suffix}{path}"


def _host_header(parsed) -> str:
    host = _normalize_host(parsed.hostname or "")
    if parsed.port is None or parsed.port == _default_port(parsed.scheme):
        return host
    return f"{host}:{parsed.port}"


def _parse_cookie_headers(raw_headers: list[str]) -> list[dict[str, Any]]:
    cookies: list[dict[str, Any]] = []
    for raw_header in raw_headers:
        parsed = SimpleCookie()
        parsed.load(raw_header)
        for morsel in parsed.values():
            cookies.append(
                {
                    "name": morsel.key,
                    "http_only": bool(morsel["httponly"]),
                    "secure": bool(morsel["secure"]),
                    "same_site": morsel["samesite"].title() if morsel["samesite"] else None,
                }
            )
    return cookies


def _analyze_headers(
    headers: httpx.Headers,
    scheme: str,
) -> dict[str, dict[str, Any]]:
    csp = headers.get("Content-Security-Policy")
    xfo = headers.get("X-Frame-Options")
    hsts = headers.get("Strict-Transport-Security")
    xcto = headers.get("X-Content-Type-Options")
    referrer = headers.get("Referrer-Policy")
    return {
        "content_security_policy": {"present": bool(csp), "value": csp},
        "x_frame_options": {"present": bool(xfo), "value": xfo},
        "strict_transport_security": {
            "present": bool(hsts) if scheme == "https" else False,
            "value": hsts if scheme == "https" else None,
        },
        "x_content_type_options": {
            "present": (xcto or "").lower() == "nosniff",
            "value": xcto,
        },
        "referrer_policy": {"present": bool(referrer), "value": referrer},
    }


def _score_audit(
    headers: dict[str, dict[str, Any]],
    cookies: list[dict[str, Any]],
    tls: dict[str, Any] | None,
    scheme: str,
) -> tuple[int, list[str]]:
    score = 100
    recommendations: list[str] = []

    if not headers["content_security_policy"]["present"]:
        score -= 15
        recommendations.append(
            "Configure uma Content-Security-Policy para reduzir execucao de scripts nao confiaveis."
        )
    if not headers["x_frame_options"]["present"]:
        score -= 10
        recommendations.append(
            "Defina X-Frame-Options como DENY ou SAMEORIGIN para reduzir clickjacking."
        )
    if scheme == "https" and not headers["strict_transport_security"]["present"]:
        score -= 10
        recommendations.append(
            "Ative Strict-Transport-Security (HSTS) para reforcar conexoes HTTPS."
        )
    if not headers["x_content_type_options"]["present"]:
        score -= 10
        recommendations.append("Defina X-Content-Type-Options como nosniff.")
    if not headers["referrer_policy"]["present"]:
        score -= 5
        recommendations.append("Adicione uma Referrer-Policy explicita.")

    for cookie in cookies:
        if not cookie["http_only"]:
            score -= 10
            recommendations.append(f"Marque o cookie {cookie['name']} como HttpOnly.")
        if not cookie["secure"]:
            score -= 10
            recommendations.append(f"Marque o cookie {cookie['name']} como Secure.")
        if not cookie["same_site"]:
            score -= 5
            recommendations.append(f"Defina SameSite no cookie {cookie['name']}.")

    if scheme != "https":
        score -= 20
        recommendations.append("Use HTTPS para proteger o trafego.")
    elif tls is None or not tls.get("valid"):
        score -= 5
        recommendations.append("Corrija a configuracao TLS: certificado invalido ou expirado.")

    return max(0, min(100, score)), recommendations


def _split_target(target: str) -> tuple[str, int | None]:
    normalized_host = target_hostname(target)
    stripped = target.strip()
    if stripped.startswith("["):
        parsed = urlsplit(f"//{stripped}")
        return normalized_host, parsed.port
    if stripped.count(":") == 1:
        host_part, port_part = stripped.rsplit(":", 1)
        if port_part.isdigit():
            return _normalize_host(host_part), int(port_part)
    return normalized_host, None


def _target_from_url(hostname: str, port: int | None) -> str:
    normalized_host = _normalize_host(hostname)
    if port is None:
        return normalized_host
    try:
        if ip_address(normalized_host).version == 6:
            return f"[{normalized_host}]:{port}"
    except ValueError:
        pass
    return f"{normalized_host}:{port}"


def _pick_approved_ip(addresses: list[str]) -> str:
    if not addresses:
        raise URLValidationError("O alvo nao retornou nenhum endereco aprovado")
    return addresses[0]


def _normalize_host(hostname: str) -> str:
    return hostname.rstrip(".").encode("idna").decode("ascii").lower()


def _default_port(scheme: str) -> int:
    return 443 if scheme == "https" else 80


def _parse_cert_time(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromtimestamp(ssl.cert_time_to_seconds(value), tz=timezone.utc)


def _format_certificate_issuer(certificate: dict[str, Any]) -> str | None:
    issuer_parts = []
    for group in certificate.get("issuer", ()):
        for key, value in group:
            issuer_parts.append(f"{key}={value}")
    if not issuer_parts:
        return None
    return ", ".join(issuer_parts)


def _decode_der_certificate(certificate_der: bytes) -> dict[str, Any]:
    pem = ssl.DER_cert_to_PEM_cert(certificate_der)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="ascii",
            suffix=".pem",
            delete=False,
        ) as certificate_file:
            certificate_file.write(pem)
            temporary_path = certificate_file.name
        return ssl._ssl._test_decode_cert(temporary_path)
    finally:
        if temporary_path:
            try:
                os.unlink(temporary_path)
            except OSError:
                pass
