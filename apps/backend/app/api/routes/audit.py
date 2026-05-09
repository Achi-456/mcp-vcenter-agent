from typing import Any

from fastapi import APIRouter, Depends, Query

from app.api.deps import audit_dep
from app.core.responses import success_response
from app.services.audit_service import AuditService

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get("/events")
async def recent_events(
    limit: int = Query(default=50, ge=1, le=200),
    audit: AuditService = Depends(audit_dep),
) -> dict[str, Any]:
    rows = await audit.recent(limit=limit)
    data = [
        {
            "id": row.id,
            "event_type": row.event_type,
            "actor": row.actor,
            "target": row.target,
            "action": row.action,
            "status": row.status,
            "error_code": row.error_code,
            "risk_level": row.risk_level,
            "metadata": row.metadata_json,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]
    return success_response(data, source="postgres")
