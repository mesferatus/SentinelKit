from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models import ScanResult, User
from app.schemas.tasks import TaskStatusResponse

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/{task_id}", response_model=TaskStatusResponse)
def get_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ScanResult:
    scan = db.scalar(
        select(ScanResult).where(
            ScanResult.task_id == task_id,
            ScanResult.user_id == current_user.id,
        )
    )
    if scan is None:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    return scan
