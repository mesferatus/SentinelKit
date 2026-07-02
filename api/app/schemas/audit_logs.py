from datetime import datetime
from pydantic import BaseModel, ConfigDict

class AuditLogItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    endpoint: str
    method: str
    source_ip: str
    status_code: int
    timestamp: datetime

class AuditLogPage(BaseModel):
    total: int
    items: list[AuditLogItem]
    page: int
    page_size: int
