from datetime import datetime

from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: int
    user_id: int | None
    action: str
    target: str | None
    source: str
    endpoint: str | None
    status_code: int | None
    detail: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
