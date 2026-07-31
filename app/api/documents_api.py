import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_session
from app.models import DocumentGroup, GroupStatus, DocumentFile
from app.schemas import AckResponse, GroupOut, FileOut

router = APIRouter(prefix="/documents", tags=["documents"])

from app.core.config import settings

from fastapi.responses import FileResponse

@router.get("/files/{file_id}")
async def download_file(file_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    file = await session.get(DocumentFile, file_id)
    if file is None or file.download_status != "ok" or not file.local_path:
        raise HTTPException(status_code=404, detail="File not found or not downloaded yet")
    return FileResponse(file.local_path)  # Принимает путь к файлу и передает его бинарник по REST

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
    groups = result.scalars().all()
    return [
        GroupOut(
            id=g.id,
            sender_id=g.sender_id,
            status=g.status.value,
            created_at=g.created_at,
            last_photo_at=g.last_photo_at,
            files=[
                FileOut(
                    id=f.id,
                    download_url=f"{settings.webhook_url.rstrip('/')}/documents/files/{f.id}",
                    download_status=f.download_status,
                    received_at=f.received_at,
                )
                for f in g.files
            ],
        )
        for g in groups
    ]


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
