from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from app.core.config import settings
from app.models import ScanStatus


DEFAULT_RECON_PORTS = [
    21, 22, 23, 25, 53, 80, 110, 143, 443, 445,
    993, 995, 1433, 1521, 3306, 3389, 5432, 5900, 6379, 8080,
]


class ReconScanRequest(BaseModel):
    target_id: int = Field(gt=0)
    ports: list[int] | None = None

    @model_validator(mode="after")
    def validate_ports(self):
        ports = self.ports if self.ports is not None else DEFAULT_RECON_PORTS
        if any(isinstance(port, bool) or port < 1 or port > 65535 for port in ports):
            raise ValueError("Portas devem estar entre 1 e 65535")
        unique = list(dict.fromkeys(ports))
        if not unique:
            raise ValueError("Informe pelo menos uma porta")
        if len(unique) > settings.scan_max_ports:
            raise ValueError(
                f"Máximo de {settings.scan_max_ports} portas por scan"
            )
        self.ports = unique
        return self


class ReconScanResponse(BaseModel):
    task_id: str
    status: ScanStatus

