from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.db import models  # noqa: F401 - ensures model metadata is registered
from app.db.base import Base
from app.db.schema import check_schema
from app.schemas.common import HealthResponse


def build_engine(settings: Settings):
    kwargs: dict = {"pool_pre_ping": True}
    if settings.database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if ":memory:" in settings.database_url:
            kwargs["poolclass"] = StaticPool
    return create_engine(settings.database_url, **kwargs)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    engine = build_engine(settings)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        settings.storage_dir.mkdir(parents=True, exist_ok=True)
        Base.metadata.create_all(bind=engine)
        try:
            check_schema(engine)
            yield
        finally:
            engine.dispose()

    application = FastAPI(
        title=settings.app_name,
        version="0.4.0",
        description=(
            "MedGuard AI para o Tech Challenge FIAP Fase 4, com analise multimodal educacional. "
            "Aceita somente dados sinteticos/ficticios e nao realiza diagnosticos."
        ),
        lifespan=lifespan,
    )
    application.state.settings = settings
    application.state.engine = engine
    application.state.session_factory = session_factory
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(api_router, prefix=settings.api_prefix)

    @application.get("/health", response_model=HealthResponse, tags=["system"])
    async def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            service=settings.app_name,
            environment=settings.app_env,
            timestamp=datetime.now(UTC),
        )

    return application


app = create_app()

