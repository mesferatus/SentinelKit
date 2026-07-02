import hashlib
import secrets

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.rate_limit import limiter
from app.middleware.audit_logger import AuditLoggerMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.routers.auth import router as auth_router
from app.routers.audit_logs import router as audit_logs_router
from app.routers.dashboard import router as dashboard_router
from app.routers.recon import router as recon_router
from app.routers.siem import router as siem_router
from app.routers.tasks import router as tasks_router
from app.routers.targets import router as targets_router
from app.routers.webaudit import router as webaudit_router

app = FastAPI(title="SentinelKit")
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-CSRF-Token"],
)
app.add_middleware(AuditLoggerMiddleware)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.include_router(auth_router)
app.include_router(audit_logs_router)
app.include_router(dashboard_router)
app.include_router(targets_router)
app.include_router(tasks_router)
app.include_router(recon_router)
app.include_router(webaudit_router)
app.include_router(siem_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/runtime")
def runtime_health(
    x_sentinel_runtime: str | None = Header(default=None),
) -> dict[str, str]:
    nonce = settings.desktop_runtime_nonce
    if not nonce or not x_sentinel_runtime or not secrets.compare_digest(
        nonce, x_sentinel_runtime
    ):
        raise HTTPException(status_code=404, detail="Not found")
    return {
        "marker": "sentinelkit-desktop",
        "nonce_hash": hashlib.sha256(nonce.encode()).hexdigest(),
    }
