from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlsplit

from fastapi import HTTPException

from app.core.config import settings


def _split_target(value: str) -> tuple[str, int | None]:
    raw = value.strip()
    if not raw or "://" in raw or any(char in raw for char in "/?#@"):
        raise ValueError("Informe apenas host ou host:porta, sem esquema ou caminho")
    if not raw.startswith("["):
        try:
            address = ipaddress.ip_address(raw)
            return address.compressed, None
        except ValueError:
            pass
    parsed = urlsplit(f"//{raw}")
    if not parsed.hostname:
        raise ValueError("Alvo inválido")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Porta inválida") from exc
    return parsed.hostname, port


def normalize_target(value: str) -> str:
    host, port = _split_target(value)
    try:
        address = ipaddress.ip_address(host)
        normalized_host = address.compressed
        rendered = f"[{normalized_host}]" if address.version == 6 and port else normalized_host
    except ValueError:
        normalized_host = host.rstrip(".").encode("idna").decode("ascii").lower()
        if not normalized_host:
            raise ValueError("Domínio inválido")
        rendered = normalized_host
    return f"{rendered}:{port}" if port else rendered


def target_hostname(target: str) -> str:
    return _split_target(target)[0].lower()


def _is_internal(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return not address.is_global


def enforce_network_policy(target: str) -> None:
    resolve_validated_addresses(target)


def resolve_validated_addresses(target: str) -> list[str]:
    host = target_hostname(target)
    allowlist = {target_hostname(item) for item in settings.allowed_scan_targets}
    try:
        addresses = {ipaddress.ip_address(host)}
    except ValueError:
        try:
            addresses = {
                ipaddress.ip_address(item[4][0])
                for item in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
            }
        except (socket.gaierror, OSError, ValueError) as exc:
            raise HTTPException(status_code=403, detail="Não foi possível resolver o alvo") from exc
    if any(_is_internal(address) for address in addresses) and host not in allowlist:
        detail = (
            "Domínio resolve para endereço interno; inclua o host em ALLOWED_SCAN_TARGETS"
            if not _looks_like_ip(host)
            else "Alvo privado, loopback, link-local ou reservado exige ALLOWED_SCAN_TARGETS"
        )
        raise HTTPException(status_code=403, detail=detail)
    return sorted(str(address) for address in addresses)


def _looks_like_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False
