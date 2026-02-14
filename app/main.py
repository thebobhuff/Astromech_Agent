from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.api import (
    memory_routes,
    agent_routes,
    task_routes,
    skill_routes,
    system_routes,
    model_routes,
    protocol_routes,
    node_routes,
)
from app.skills.telegram.bot import TelegramSkill
from app.skills.discord.bot import DiscordSkill
from app.core.heartbeat import AgentHeartbeat
from app.core.cron import cron_manager
from app.core.cron_jobs import setup_cron_jobs
from app.core.logging_utils import configure_logging
import asyncio
import logging

configure_logging()
logger = logging.getLogger(__name__)

telegram_skill = TelegramSkill()
discord_skill = DiscordSkill()
heartbeat = AgentHeartbeat(interval=1800)  # Tick every 30 minutes

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup begin", extra={"event": "startup"})
    try:
        # Startup: Initialize and run Telegram Bot
        if settings.TELEGRAM_POLLING_ENABLED:
            logger.info("Initializing Telegram skill", extra={"event": "startup"})
            telegram_skill.initialize()
            if telegram_skill.application:
                asyncio.create_task(telegram_skill.run_polling())
        else:
            logger.info(
                "Telegram polling disabled by config (TELEGRAM_POLLING_ENABLED=false)",
                extra={"event": "startup"},
            )
            
        # Startup: Run Discord Bot
        logger.info("Initializing Discord skill", extra={"event": "startup"})
        asyncio.create_task(discord_skill.start())
        
        # Startup: Run Heartbeat
        logger.info("Initializing heartbeat", extra={"event": "startup"})
        asyncio.create_task(heartbeat.start())
        
        # Startup: Run Scheduler
        logger.info("Initializing cron manager", extra={"event": "startup"})
        cron_manager.start()
        
        logger.info("Application startup complete", extra={"event": "startup"})
        yield
    except Exception as e:
        logger.exception("Application startup error: %s", e, extra={"event": "startup"})
        raise e
    finally:
        # Shutdown
        logger.info("Application shutdown begin", extra={"event": "shutdown"})
        if settings.TELEGRAM_POLLING_ENABLED and telegram_skill.application:
            await telegram_skill.stop()
        await discord_skill.stop()
        await heartbeat.stop()
        cron_manager.stop()
        logger.info("Application shutdown complete", extra={"event": "shutdown"})

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, verify strictly. For localhost/dev, * is fine.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(memory_routes.router, prefix="/api/v1/memory", tags=["Memory"])
app.include_router(agent_routes.router, prefix="/api/v1/agent", tags=["Agent"])
app.include_router(task_routes.router, prefix="/api/v1/tasks", tags=["Tasks"])
app.include_router(skill_routes.router, prefix="/api/v1/skills", tags=["Skills"])
app.include_router(system_routes.router, prefix="/api/v1/system", tags=["System"])
app.include_router(model_routes.router, prefix="/api/v1/models", tags=["Models"])
app.include_router(protocol_routes.router, prefix="/api/v1/protocols", tags=["Protocols"])
app.include_router(node_routes.router, prefix="/api/v1/nodes", tags=["Nodes"])

@app.get("/")
async def root():
    return {"message": "Welcome to Astromech AI Gateway"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "provider": settings.DEFAULT_LLM_PROVIDER}

if __name__ == "__main__":
    import uvicorn
    # Reload is currently enabled for development iteration
    uvicorn.run("app.main:app", host="0.0.0.0", port=13579, reload=True)
