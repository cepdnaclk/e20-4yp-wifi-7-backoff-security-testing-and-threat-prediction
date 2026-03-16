from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
import os
import pathlib
import logging

from .db.connection import init_pool, close_pool
from .api import experiments, models, analysis, pipeline
from .api import run as run_router
from .ws.pipeline import router as ws_router

DB_CONFIG = {
    "host": os.getenv("PG_HOST", "localhost"),
    "port": int(os.getenv("PG_PORT", "5432")),
    "database": os.getenv("PG_DB", "udr"),
    "user": os.getenv("PG_USER", "udr"),
    "password": os.getenv("PG_PASS", "udr_pass"),
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        app.state.pool = await init_pool(DB_CONFIG)
        logging.info("DB pool connected: %s:%s/%s", DB_CONFIG["host"], DB_CONFIG["port"], DB_CONFIG["database"])
    except Exception as e:
        logging.warning("DB pool unavailable at startup (will retry on request): %s", e)
        app.state.pool = None
    yield
    if app.state.pool:
        await close_pool(app.state.pool)


class LazyPoolMiddleware(BaseHTTPMiddleware):
    """If the DB pool failed to init at startup, retry on each API request."""
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/api") and getattr(request.app.state, "pool", None) is None:
            try:
                request.app.state.pool = await init_pool(DB_CONFIG)
                logging.info("DB pool reconnected on request")
            except Exception as e:
                logging.warning("DB pool retry failed: %s", e)
        return await call_next(request)


app = FastAPI(title="NDT Dashboard API", version="1.0.0", lifespan=lifespan)

app.add_middleware(LazyPoolMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(experiments.router, prefix="/api")
app.include_router(models.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")
app.include_router(pipeline.router, prefix="/api")
app.include_router(run_router.router, prefix="/api")
app.include_router(ws_router)


@app.get("/api/health")
async def health(request: Request):
    pool = getattr(request.app.state, "pool", None)
    if pool is None:
        return {"status": "ok", "db": "unavailable"}
    try:
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        return {"status": "ok", "db": f"error: {str(e)}"}


# Serve static files (React SPA) - must be last
static_dir = pathlib.Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
