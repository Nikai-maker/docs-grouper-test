from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.config import settings
from app.database import init_db
from app.documents_api import router as documents_router
from app.grouping import group_closer_loop
from app.telegram_webhook import router as telegram_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    # регистрируем webhook в Telegram при старте
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            await client.get(
                f"https://api.telegram.org/bot{settings.bot_token}/setWebhook",
                params={"url": settings.webhook_url.rstrip("/") + settings.webhook_path},
            )
        except httpx.HTTPError as e:
            print(f"[startup] failed to set webhook: {e}")

    import asyncio
    task = asyncio.create_task(group_closer_loop())

    yield

    task.cancel()


app = FastAPI(title="Telegram Document Ingestion Service", lifespan=lifespan)

app.include_router(telegram_router)
app.include_router(documents_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
