from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import engine
from app.models import *  # noqa: F401, F403 — register all models with SQLAlchemy
from app.routers import auth, campaigns, content, approvals, voice, executions, analytics, audit, integrations, experiments

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(
    title="Enterprise AI Marketing Execution Platform",
    version="0.1.0",
    description="Governed AI marketing execution — campaigns, content, approvals, analytics.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(campaigns.router)
app.include_router(content.router)
app.include_router(approvals.router)
app.include_router(voice.router)
app.include_router(executions.router)
app.include_router(analytics.router)
app.include_router(audit.router)
app.include_router(integrations.router)
app.include_router(experiments.router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
