from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.bot.manager import BotManager
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.seed import seed_initial_data
from app.db.session import SessionLocal
from app.workers.retention import RetentionWorker

settings = get_settings()
configure_logging(settings.log_level)
logger = structlog.get_logger(__name__)


class DisabledBotManager:
    started_at = None
    last_event_at = None
    connected = False

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("app_startup", version=settings.app_version)

    if settings.testing:
        app.state.bot_manager = DisabledBotManager()
        yield
        logger.info("app_shutdown")
        return

    db = SessionLocal()
    try:
        seed_initial_data(db, settings)
    finally:
        db.close()

    bot_manager = BotManager(settings)
    retention_worker = RetentionWorker(settings)
    app.state.bot_manager = bot_manager
    app.state.retention_worker = retention_worker
    await bot_manager.start()
    await retention_worker.start()

    yield

    await retention_worker.stop()
    await bot_manager.stop()
    logger.info("app_shutdown")


app = FastAPI(title="Discord Game Tracker", version=settings.app_version, lifespan=lifespan)
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins_list or [],
    allow_credentials="*" not in settings.cors_allow_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)
