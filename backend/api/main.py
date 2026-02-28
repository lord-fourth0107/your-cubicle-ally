"""
api/main.py
-----------
FastAPI application entry point.
Spawned as a child process by the Electron main process.
Listens on localhost:8000.

Owner: API team
Depends on: core/orchestrator, core/session_manager, utilities/*
Depended on by: Electron main process (server-manager.ts)
"""

from fastapi import FastAPI
from .routes import session, turn

app = FastAPI(title="Your Cubicle Ally", version="0.1.0")

app.include_router(session.router, prefix="/session", tags=["session"])
app.include_router(turn.router, prefix="/turn", tags=["turn"])


@app.get("/health")
async def health():
    return {"status": "ok"}
