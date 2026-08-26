from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.agents import router as agents_router
from app.api.credentials import router as credentials_router
from app.api.channels.telegram import router as telegram_router
from app.api.runtime import router as runtime_router
from app.api.runtime_demo import router as runtime_demo_router
from app.api.tools import router as tools_router
from app.deps import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="E.V.A.", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(agents_router)
app.include_router(credentials_router)
app.include_router(tools_router)
app.include_router(runtime_router)
app.include_router(runtime_demo_router)
app.include_router(telegram_router)


@app.get("/health")
async def health():
    return {"ok": True}


@app.get("/api/hello")
async def hello():
    return {"message": "Hello from E.V.A."}
