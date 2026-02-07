"""
FastAPI application entry point.
"""
from __future__ import annotations
import logging
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_db
from backend.routes import deals, transcripts, extraction, exports, auth_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Onboarding Form Filler API",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router, prefix="/api", tags=["auth"])
app.include_router(deals.router, prefix="/api/deals", tags=["deals"])
app.include_router(transcripts.router, prefix="/api/transcripts", tags=["transcripts"])
app.include_router(extraction.router, prefix="/api/runs", tags=["runs"])
app.include_router(exports.router, prefix="/api/runs", tags=["exports"])


@app.get("/api/health")
async def health():
    return {"status": "ok"}
