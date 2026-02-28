"""
api/deps.py
-----------
FastAPI dependency injection helpers.
All route handlers that need access to shared singletons (SessionManager,
Orchestrator, etc.) declare them as Depends(get_*) parameters.

The singletons are stored on app.state by the lifespan handler in main.py.

Owner: API team
"""

from fastapi import Request
from ..core.session_manager import SessionManager
from ..core.orchestrator import Orchestrator
from ..agents.coach_agent import CoachAgent
from ..utilities.session_initializer import SessionInitializer


def get_session_manager(request: Request) -> SessionManager:
    return request.app.state.session_manager


def get_orchestrator(request: Request) -> Orchestrator:
    return request.app.state.orchestrator


def get_coach_agent(request: Request) -> CoachAgent:
    return request.app.state.coach_agent


def get_session_initializer(request: Request) -> SessionInitializer:
    return request.app.state.session_initializer
