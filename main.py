"""Grabpic API entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import init_db
from app.routes.auth import router as auth_router
from app.routes.crawl import router as crawl_router
from app.routes.images import router as images_router
from app.routes.upload import router as upload_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Grabpic",
    description="Intelligent Identity & Retrieval Engine — facial grouping and selfie auth",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(crawl_router)
app.include_router(auth_router)
app.include_router(images_router)
app.include_router(upload_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return {
        "service": "grabpic",
        "docs": "/docs",
        "redoc": "/redoc",
    }
