import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session
from app.models import DocumentGroup, GroupStatus


async def get_or_create_open_group(session: AsyncSession, sender_id: int) -> DocumentGroup:
    """
    Возвращает открытую группу отправителя, если она не устарела, иначе создаёт новую
    Группировка только в рамках одного отправителя (см. README, раздел "Ограничения")
    """
    timeout = timedelta(minutes=settings.group_timeout_minutes)
    cutoff = datetime.now(timezone.utc) - timeout

    stmt = (
        select(DocumentGroup)
        .where(DocumentGroup.sender_id == sender_id)
        .where(DocumentGroup.status == GroupStatus.open)
        .where(DocumentGroup.last_photo_at >= cutoff)
        .order_by(DocumentGroup.last_photo_at.desc())
    )
    result = await session.execute(stmt)
    group = result.scalars().first()

    if group is None:
        group = DocumentGroup(sender_id=sender_id)
        session.add(group)
        await session.flush()  # чтобы получить group.id до коммита
    else:
        group.last_photo_at = datetime.now(timezone.utc)

    return group


async def close_stale_groups(session: AsyncSession) -> int:
    """Переводит группы без новых фото дольше таймаута в статус ready. Возвращает кол-во закрытых групп"""
    timeout = timedelta(minutes=settings.group_timeout_minutes)
    cutoff = datetime.now(timezone.utc) - timeout

    stmt = (
        update(DocumentGroup)
        .where(DocumentGroup.status == GroupStatus.open)
        .where(DocumentGroup.last_photo_at < cutoff)
        .values(status=GroupStatus.ready)
    )
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount


async def group_closer_loop() -> None:
    """
    Фоновый цикл внутри самого процесса FastAPI — без Celery/Redis,
    объём задачи этого не требует
    """
    while True:
        await asyncio.sleep(settings.group_check_interval_seconds)
        try:
            async with async_session() as session:
                closed = await close_stale_groups(session)
                if closed:
                    print(f"[group_closer] closed {closed} stale group(s)")
        except Exception as e:
            # не даём фоновому циклу упасть насовсем из-за единичной ошибки БД
            print(f"[group_closer] error: {e}")
