from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.core.config import settings
from app.core.database import init_db
from app.api.documents_api import router as documents_router
from app.servises.grouping import group_closer_loop
from app.api.telegram_webhook import router as telegram_router
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(filename)s - %(levelname)s - %(message)s"
)
lg = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    # регистрируем webhook в Telegram при старте
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(
                f"https://api.telegram.org/bot{settings.bot_token}/setWebhook",
                params={"url": settings.webhook_url.rstrip("/") + settings.webhook_path},
            )
            lg.info(f"setWebhook response: {resp.status_code} {resp.text}")
        except httpx.HTTPError as e:
            lg.info(f"[startup] failed to set webhook: {e}")

    lg.info(f"webhook в телеграм установлен")
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
