"""用户管理平台入口（FastAPI）。

启动：uvicorn admin.main:app --host 127.0.0.1 --port 8001
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_admin_settings
from .core.exceptions import register_exception_handlers
from .database import Base, SessionLocal, engine
from .routers import auth, business, groups, model_config, roles, users

logging.basicConfig(level=logging.INFO)

settings = get_admin_settings()


def ensure_tables_and_seed() -> None:
    """幂等：建表 + 种子数据（角色/权限/管理员/配额）。"""
    Base.metadata.create_all(bind=engine)
    from .init_db import ensure_seeded

    db = SessionLocal()
    try:
        ensure_seeded(db)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_tables_and_seed()
    yield
    engine.dispose()


app = FastAPI(
    title="Dialogue 用户管理平台",
    lifespan=lifespan,
    docs_url="/docs" if settings.admin_env == "dev" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(roles.router)
app.include_router(roles.perm_router)
app.include_router(groups.router)
app.include_router(model_config.router)
app.include_router(business.conv_router)
app.include_router(business.stats_router)
app.include_router(business.quota_router)
app.include_router(business.log_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "Dialogue Admin Platform", "port": settings.admin_port}
