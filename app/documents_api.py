import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models import DocumentGroup, GroupStatus
from app.schemas import AckResponse, GroupOut

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/ready", response_model=list[GroupOut])
async def list_ready_documents(session: AsyncSession = Depends(get_session)):
    """Отдаёт все группы в статусе ready. Внешний модуль пуллит этот эндпоинт"""
    stmt = (
        select(DocumentGroup)
        .where(DocumentGroup.status == GroupStatus.ready)
        .options(selectinload(DocumentGroup.files))
        .order_by(DocumentGroup.created_at)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


@router.post("/{group_id}/ack", response_model=AckResponse)
async def ack_document(group_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    """
    Подтверждение, что внешний модуль забрал группу.
    Переводит статус в delivered, чтобы группа не отдавалась повторно при следующем пуллинге
    """
    group = await session.get(DocumentGroup, group_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    if group.status != GroupStatus.ready:
        raise HTTPException(status_code=409, detail=f"Group is in '{group.status.value}' status, not 'ready'")

    group.status = GroupStatus.delivered
    await session.commit()

    return AckResponse(group_id=group.id, status=group.status.value)
