import asyncio
import os
import uuid

import httpx

from app.config import settings

TELEGRAM_API = f"https://api.telegram.org/bot{settings.bot_token}"
TELEGRAM_FILE_API = f"https://api.telegram.org/file/bot{settings.bot_token}"

MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2


async def download_telegram_photo(telegram_file_id: str, group_id: uuid.UUID) -> str | None:
    """
    Скачивает фото максимального качества по file_id
    Возвращает локальный путь к файлу или None, если скачать не удалось после ретраев
    """
    async with httpx.AsyncClient(timeout=30) as client:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                # Получить путь к файлу на серверах Telegram
                resp = await client.get(f"{TELEGRAM_API}/getFile", params={"file_id": telegram_file_id})
                resp.raise_for_status()
                file_path = resp.json()["result"]["file_path"]

                # Скачать сам файл
                file_resp = await client.get(f"{TELEGRAM_FILE_API}/{file_path}")
                file_resp.raise_for_status()

                group_dir = os.path.join(settings.storage_path, str(group_id))
                os.makedirs(group_dir, exist_ok=True)

                file_name = f"{uuid.uuid4()}_{os.path.basename(file_path)}"
                local_path = os.path.join(group_dir, file_name)

                with open(local_path, "wb") as f:
                    f.write(file_resp.content)

                return local_path

            except (httpx.HTTPError, KeyError):
                if attempt == MAX_RETRIES:
                    return None
                await asyncio.sleep(RETRY_BACKOFF_SECONDS * attempt)

    return None
