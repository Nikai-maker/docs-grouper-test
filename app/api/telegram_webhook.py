from fastapi import APIRouter, BackgroundTasks, Request
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session
from app.grouping import get_or_create_open_group
from app.models import DocumentFile
from app.storage import download_telegram_photo

router = APIRouter()


@router.post(settings.webhook_path)
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    update = await request.json()

    message = update.get("message")
    update_id = update.get("update_id")

    # Игнорируем сообщения, если нет фото
    if not message or "photo" not in message or update_id is None:
        return {"ok": True}

    sender_id = message["from"]["id"]
    # Телеграм выдает последний файл в списке с макс качеством
    telegram_file_id = message["photo"][-1]["file_id"]

    async with async_session() as session:
        group = await get_or_create_open_group(session, sender_id)
        group_id = group.id

        # Идемпотентность через upsert по telegram.update.id
        stmt = (
            pg_insert(DocumentFile)
            .values(
                group_id=group_id,
                telegram_update_id=update_id,
                telegram_file_id=telegram_file_id,
                download_status="pending",
            )
            .on_conflict_do_nothing(index_elements=["telegram_update_id"])
            .returning(DocumentFile.id)
        )
        result = await session.execute(stmt)
        await session.commit()

        file_row_id = result.scalar_one_or_none()

    # если это дубль (конфликт) — file_row_id будет None, скачивать нечего
    if file_row_id is not None:
        background_tasks.add_task(_download_and_update, file_row_id, telegram_file_id, group_id)

    # Отвечает телеге, не дожидаяь скачивания
    return {"ok": True}

async def _send_reply(sender_id):
    pass

async def _download_and_update(file_row_id, telegram_file_id: str, group_id) -> None:
    """Фоновая задача: скачивает файл и обновляет статус записи"""
    from sqlalchemy import update as sa_update

    local_path = await download_telegram_photo(telegram_file_id, group_id)

    async with async_session() as session:
        stmt = (
            sa_update(DocumentFile)
            .where(DocumentFile.id == file_row_id)
            .values(
                local_path=local_path,
                download_status="ok" if local_path else "failed",
            )
        )
        await session.execute(stmt)
        await session.commit()
