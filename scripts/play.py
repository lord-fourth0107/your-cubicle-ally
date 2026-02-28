#!/usr/bin/env python3
"""
scripts/play.py
---------------
CLI test harness for the Your Cubicle Ally backend.
Runs a full game session in the terminal — setup, arena loop, debrief.

Usage:
  cd scripts
  pip install -r requirements.txt
  python play.py [--url http://localhost:8000]

Requires the backend to be running:
  cd backend && uvicorn api.main:app --port 8000
"""

import argparse
import sys
import time
import textwrap
import requests
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import BarColumn, Progress, TextColumn
from rich import box
from rich.prompt import Prompt
from rich.text import Text
from rich.rule import Rule

console = Console()


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_URL = "http://localhost:8000"


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def api_get(base_url: str, path: str) -> dict:
    res = requests.get(f"{base_url}{path}", timeout=30)
    res.raise_for_status()
    return res.json()


def api_post(base_url: str, path: str, body: dict) -> dict:
    res = requests.post(f"{base_url}{path}", json=body, timeout=30)
    res.raise_for_status()
    return res.json()


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

HP_FULL = 100

def render_hp_bar(current: int, maximum: int = HP_FULL) -> Text:
    pct = max(0, current / maximum)
    filled = int(pct * 20)
    bar = "█" * filled + "░" * (20 - filled)
    color = "green" if pct > 0.6 else "yellow" if pct > 0.3 else "red"
    t = Text()
    t.append(f"HP  [{bar}]  {current}/{maximum}", style=color)
    return t


def render_situation(situation: str, step: int, max_steps: int) -> Panel:
    wrapped = textwrap.fill(situation, width=70)
    return Panel(
        wrapped,
        title=f"[bold]Turn {step} of {max_steps}[/bold]",
        border_style="blue",
        padding=(1, 2),
    )


def render_actor_reactions(reactions: list[dict], actors: list[dict]) -> None:
    if not reactions:
        return
    actor_map = {a["actor_id"]: a for a in actors}
    for r in reactions:
        actor = actor_map.get(r["actor_id"], {})
        name = r["actor_id"].capitalize()
        role = actor.get("role", "").split(".")[0].strip()
        console.print(f"\n  [bold cyan]{name}[/bold cyan] [dim]({role})[/dim]")
        console.print(f"  [italic]\"{r['dialogue']}\"[/italic]")


def render_choices(choices: list[dict]) -> None:
    table = Table(box=box.ROUNDED, show_header=False, padding=(0, 2), expand=False)
    table.add_column("key", style="bold yellow", width=4)
    table.add_column("label")
    labels = ["A", "B", "C"]
    for i, choice in enumerate(choices):
        table.add_row(f"[{labels[i]}]", choice["label"])
    table.add_row("[F]", "[dim]Free-write your own response[/dim]")
    console.print(table)


def pick_choice(choices: list[dict]) -> str:
    valid = {"a": 0, "b": 1, "c": 2}
    while True:
        raw = Prompt.ask("\n[bold yellow]Your move[/bold yellow]").strip().lower()
        if raw in valid:
            return choices[valid[raw]]["label"]
        if raw == "f":
            return Prompt.ask("  [dim]Type your response[/dim]").strip()
        console.print("  [red]Enter A, B, C, or F[/red]")


def render_debrief(debrief: dict) -> None:
    outcome = debrief.get("outcome", "unknown")
    score = debrief.get("overall_score", 0)
    summary = debrief.get("summary", "")

    outcome_style = "bold green" if outcome == "won" else "bold red"
    outcome_label = "YOU WON" if outcome == "won" else "YOU LOST"

    console.print()
    console.print(Rule(f"[{outcome_style}]  {outcome_label}  [/{outcome_style}]"))
    console.print()
    console.print(Panel(
        textwrap.fill(summary, width=70),
        title=f"[bold]Overall score: {score}/100[/bold]",
        border_style="green" if outcome == "won" else "red",
        padding=(1, 2),
    ))

    # Turn breakdown
    breakdowns = debrief.get("turn_breakdowns", [])
    if breakdowns:
        console.print("\n[bold]Turn breakdown[/bold]")
        for t in breakdowns:
            delta = t.get("hp_delta", 0)
            delta_str = f"[red]{delta}[/red]" if delta < 0 else f"[green]+{delta}[/green]"
            console.print(f"\n  [bold]Step {t['step']}[/bold]  HP {delta_str}")
            console.print(f"  [dim]You said:[/dim] {t['player_choice']}")
            console.print(f"  [dim]Insight:[/dim] {textwrap.fill(t['compliance_insight'], 66, subsequent_indent='             ')}")

    # Key concepts
    concepts = debrief.get("key_concepts", [])
    if concepts:
        console.print("\n[bold]Key concepts covered[/bold]")
        for c in concepts:
            console.print(f"  • {c}")

    # Follow-up
    followup = debrief.get("recommended_followup", [])
    if followup:
        console.print("\n[bold]Recommended follow-up modules[/bold]")
        for m in followup:
            console.print(f"  → {m}")

    console.print()


# ---------------------------------------------------------------------------
# Game loop
# ---------------------------------------------------------------------------

def wait_for_backend(base_url: str) -> None:
    console.print(f"\n[dim]Connecting to {base_url}...[/dim]")
    for attempt in range(1, 11):
        try:
            api_get(base_url, "/health")
            console.print("[green]Backend is up.[/green]\n")
            return
        except Exception:
            if attempt == 10:
                console.print("[red]Could not reach backend after 10 attempts. Is it running?[/red]")
                console.print(f"[dim]  cd backend && uvicorn api.main:app --port 8000[/dim]")
                sys.exit(1)
            console.print(f"[yellow]Waiting for backend (attempt {attempt}/10)...[/yellow]")
            time.sleep(2)


def setup_profile(base_url: str) -> tuple[str, dict]:
    """Prompt for player details and start a session."""
    console.print(Panel(
        "[bold]Your Cubicle Ally[/bold]\nA compliance training scenario. Your choices have consequences.",
        border_style="bright_blue",
        padding=(1, 4),
    ))

    console.print("\n[bold]Player setup[/bold]\n")
    name     = Prompt.ask("  First name")
    role     = Prompt.ask("  Job role", default="Software Engineer")
    seniority = Prompt.ask("  Seniority", default="Mid-level")
    domain   = Prompt.ask("  Domain / industry", default="Technology")
    module   = Prompt.ask("  Module", default="posh")

    console.print()
    with console.status("[dim]Starting session...[/dim]"):
        data = api_post(base_url, "/session/start", {
            "player_profile": {
                "name": name,
                "role": role,
                "seniority": seniority,
                "domain": domain,
                "raw_context": "",
            },
            "module_id": module,
        })

    session_id = data["session_id"]
    game_state = data["game_state"]
    console.print(f"[dim]Session: {session_id}[/dim]\n")
    return session_id, game_state


def play_turn(base_url: str, session_id: str, game_state: dict) -> dict:
    """Render the current turn and submit the player's choice. Returns updated game_state."""
    actors = game_state.get("actors", [])
    current_turn = game_state["history"][-1]

    console.print()
    console.print(render_hp_bar(game_state["player_hp"]))
    console.print()
    console.print(render_situation(
        current_turn["situation"],
        game_state["current_step"],
        game_state["max_steps"],
    ))
    render_actor_reactions(current_turn.get("actor_reactions", []), actors)
    console.print()
    render_choices(current_turn["choices_offered"])

    player_choice = pick_choice(current_turn["choices_offered"])

    with console.status("[dim]Processing turn...[/dim]"):
        result = api_post(base_url, "/turn/submit", {
            "session_id": session_id,
            "player_choice": player_choice,
        })

    return result["game_state"]


def run_game(base_url: str) -> None:
    session_id, game_state = setup_profile(base_url)

    while game_state["status"] == "active":
        game_state = play_turn(base_url, session_id, game_state)

    # Show final HP and outcome
    console.print()
    console.print(render_hp_bar(game_state["player_hp"]))

    status = game_state["status"]

    if status == "lost":
        console.print("\n[bold red]You ran out of HP.[/bold red]")
        action = Prompt.ask(
            "\nWhat would you like to do?",
            choices=["retry", "debrief"],
            default="debrief",
        )
        if action == "retry":
            with console.status("[dim]Resetting session...[/dim]"):
                game_state = api_post(base_url, f"/session/{session_id}/retry", {})
            console.print("\n[green]Session reset. Starting again.[/green]")
            run_game.__wrapped__(base_url, session_id, game_state)
            return

    with console.status("[dim]Generating debrief...[/dim]"):
        debrief = api_get(base_url, f"/session/{session_id}/debrief")

    render_debrief(debrief)


def _resume_game(base_url: str, session_id: str, game_state: dict) -> None:
    """Internal: continue from an existing game_state (used after retry)."""
    while game_state["status"] == "active":
        game_state = play_turn(base_url, session_id, game_state)

    console.print()
    console.print(render_hp_bar(game_state["player_hp"]))

    with console.status("[dim]Generating debrief...[/dim]"):
        debrief = api_get(base_url, f"/session/{session_id}/debrief")

    render_debrief(debrief)


# Attach for retry path
run_game.__wrapped__ = _resume_game  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Your Cubicle Ally — CLI test harness")
    parser.add_argument("--url", default=DEFAULT_URL, help="Backend base URL")
    args = parser.parse_args()

    wait_for_backend(args.url)

    try:
        run_game(args.url)
    except KeyboardInterrupt:
        console.print("\n\n[dim]Session interrupted.[/dim]")
        sys.exit(0)
    except requests.HTTPError as e:
        console.print(f"\n[red]API error {e.response.status_code}:[/red] {e.response.text}")
        sys.exit(1)


if __name__ == "__main__":
    main()
