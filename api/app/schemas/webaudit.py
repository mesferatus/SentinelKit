from pydantic import AnyHttpUrl, BaseModel, Field

from app.models import ScanStatus


class WebAuditCheckRequest(BaseModel):
    target_id: int = Field(gt=0)
    url: AnyHttpUrl


class WebAuditCheckResponse(BaseModel):
    task_id: str
    status: ScanStatus


WebAuditRequest = WebAuditCheckRequest
WebAuditResponse = WebAuditCheckResponse
