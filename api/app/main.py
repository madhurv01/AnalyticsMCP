import contextlib

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.db import init_db
from app.mcp_server import build_mcp_app
from app.routers import auth, datasets, reports

mcp_app = build_mcp_app()


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    async with mcp_app.router.lifespan_context(mcp_app):
        yield


app = FastAPI(title="InsightForge API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.web_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    same_site="lax",
    https_only=settings.is_prod,
)

app.include_router(auth.router)
app.include_router(datasets.router)
app.include_router(reports.router)

app.mount("/mcp", mcp_app)


@app.get("/api/health")
def health():
    return {"status": "ok", "env": settings.env}
