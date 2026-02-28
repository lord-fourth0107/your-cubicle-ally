"""
api/main.py
-----------
FastAPI application entry point.
Spawned as a child process by the Electron main process.
Listens on localhost:8000.

Startup (lifespan):
  Initialises all shared singletons — SessionManager, SkillRegistry,
  ModuleLoader, PromptBuilder, Orchestrator, CoachAgent, SessionInitializer —
  and stores them on app.state for dependency injection in route handlers.

Owner: API team
Depends on: core/orchestrator, core/session_manager, utilities/*
Depended on by: Electron main process (server-manager.ts)
"""

import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import session, turn, world, modules, tts
from core.session_manager import SessionManager
from core.orchestrator import Orchestrator
from agents.coach_agent import CoachAgent
from agents.guardrail_agent import GuardrailAgent
from skills.skill_registry import SkillRegistry
from utilities.module_loader import ModuleLoader
from utilities.session_initializer import SessionInitializer
from utilities.prompt_builder import PromptBuilder


load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- startup ---
    skill_registry = SkillRegistry()
    skill_registry.load_all()

    module_loader = ModuleLoader()

    prompt_builder = PromptBuilder(
        skill_registry=skill_registry,
        module_loader=module_loader,
    )

    session_manager = SessionManager()
    session_initializer = SessionInitializer(module_loader=module_loader)
    guardrail = GuardrailAgent()

    orchestrator = Orchestrator(
        session_manager=session_manager,
        prompt_builder=prompt_builder,
        guardrail=guardrail,
    )

    coach_agent = CoachAgent()

    app.state.session_manager = session_manager
    app.state.session_initializer = session_initializer
    app.state.orchestrator = orchestrator
    app.state.coach_agent = coach_agent
    app.state.module_loader = module_loader

    yield
    # --- shutdown (nothing to clean up) ---


app = FastAPI(title="Your Cubicle Ally", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(session.router, prefix="/session", tags=["session"])
app.include_router(turn.router, prefix="/turn", tags=["turn"])
app.include_router(world.router, prefix="/world", tags=["world"])
app.include_router(modules.router, prefix="/modules", tags=["modules"])
app.include_router(tts.router, prefix="/tts", tags=["tts"])


@app.get("/health")
async def health():
    return {"status": "ok"}
