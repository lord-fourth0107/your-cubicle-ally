#!/usr/bin/env python3
"""
scripts/play.py
---------------
Textual TUI for Your Cubicle Ally.

Two tabs:
  [⚔ Game]  — arena (ASCII sprite + HP), dialogue chat log, choices + input
  [📋 Logs] — raw API event log

Usage:
  cd scripts && pip install -r requirements.txt
  python play.py [--url http://localhost:8000]

Requires the backend:
  cd backend && uvicorn api.main:app --port 8000
"""

import argparse
import sys
import time
from typing import Optional

import requests
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.widgets import (
    ContentSwitcher,
    Footer,
    Header,
    Input,
    Label,
    RichLog,
    Static,
    TabbedContent,
    TabPane,
)
from textual import on, work


# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_URL = "http://localhost:8000"


# ─────────────────────────────────────────────────────────────────────────────
# ASCII Sprites
# ─────────────────────────────────────────────────────────────────────────────

_SPRITES: dict[str, str] = {
    "player": (
        "   ☺   \n"
        "  /|\\  \n"
        "   |   \n"
        "  / \\  "
    ),
    "manager": (
        "  .─.  \n"
        " (ò_ó) \n"
        "  ╔═╗  \n"
        "  ╚═╝  \n"
        "  ╱ ╲  "
    ),
    "colleague": (
        "  .─.  \n"
        " (^_^) \n"
        "  |||  \n"
        "   |   \n"
        "  ╱ ╲  "
    ),
    "hr": (
        "  .─.  \n"
        " (•_•) \n"
        "  ┌─┐  \n"
        "  └─┘  \n"
        "  ╱ ╲  "
    ),
    "default": (
        "  .─.  \n"
        " (·_·) \n"
        "  |||  \n"
        "   |   \n"
        "  ╱ ╲  "
    ),
}


def _sprite_for(actor_id: str, role: str) -> str:
    r = role.lower()
    if any(k in r for k in ("manager", "director", "vp", "lead", "senior")):
        return _SPRITES["manager"]
    if any(k in r for k in ("hr", "human resource", "people ops")):
        return _SPRITES["hr"]
    if any(k in r for k in ("colleague", "peer", "engineer", "analyst", "associate")):
        return _SPRITES["colleague"]
    return _SPRITES["default"]


# ─────────────────────────────────────────────────────────────────────────────
# API helpers  (sync — always called from background thread workers)
# ─────────────────────────────────────────────────────────────────────────────

def _get(base_url: str, path: str, timeout: int = 90) -> dict:
    r = requests.get(f"{base_url}{path}", timeout=timeout)
    r.raise_for_status()
    return r.json()


def _post(base_url: str, path: str, body: dict, timeout: int = 90) -> dict:
    r = requests.post(f"{base_url}{path}", json=body, timeout=timeout)
    r.raise_for_status()
    return r.json()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _hp_markup(hp: int, max_hp: int = 100) -> str:
    pct = max(0.0, hp / max_hp)
    filled = int(pct * 16)
    bar = "█" * filled + "░" * (16 - filled)
    color = "green" if pct > 0.6 else "yellow" if pct > 0.3 else "red"
    return f"[{color}]HP [{bar}] {hp}/{max_hp}[/{color}]"


# ─────────────────────────────────────────────────────────────────────────────
# Profile setup steps  (name → role → seniority → domain → resume)
# After these complete, a dynamic scenario picker fetches /modules.
# ─────────────────────────────────────────────────────────────────────────────

_SETUP_STEPS: list[tuple[str, str, str]] = [
    ("name",      "Your first name",                                         "Player"),
    ("role",      "Job role",                                                "Software Engineer"),
    ("seniority", "Seniority level",                                         "Mid-level"),
    ("domain",    "Domain / industry",                                       "Technology"),
    ("resume",    "Paste resume or context  [dim](Enter to skip)[/dim]",     ""),
]


# ─────────────────────────────────────────────────────────────────────────────
# App
# ─────────────────────────────────────────────────────────────────────────────

class CubicleAllyApp(App[None]):
    """Your Cubicle Ally — Compliance Training TUI."""

    TITLE = "Your Cubicle Ally"
    SUB_TITLE = "Compliance Training"

    CSS = """
    TabbedContent, TabPane {
        height: 1fr;
    }

    /* ── Setup view ──────────────────────────────────────── */
    #setup-view {
        align: center middle;
        height: 1fr;
    }
    #setup-box {
        width: 64;
        height: auto;
        border: double #3b82f6;
        padding: 2 4;
    }
    #setup-title {
        text-style: bold;
        color: #06b6d4;
        text-align: center;
        margin-bottom: 0;
    }
    #setup-subtitle {
        color: #6b7280;
        text-align: center;
        margin-bottom: 2;
    }
    #setup-field-label {
        color: #9ca3af;
    }
    #setup-progress {
        color: #4b5563;
        text-align: right;
        margin-top: 1;
    }

    /* ── Game view ───────────────────────────────────────── */
    #game-view {
        layout: vertical;
        height: 1fr;
    }
    #arena-row {
        height: 10;
        layout: horizontal;
        margin-bottom: 1;
    }
    #sprite-panel {
        width: 20;
        border: round #22c55e;
        padding: 0 1;
        align: center top;
    }
    #sprite-art {
        color: #06b6d4;
        text-align: center;
        width: 1fr;
    }
    #info-panel {
        width: 1fr;
        border: round #3b82f6;
        padding: 0 2;
        margin-left: 1;
    }
    #hp-bar {
        margin-bottom: 0;
    }
    #step-info {
        color: #6b7280;
    }
    #session-info {
        color: #374151;
    }
    #chat-log {
        height: 1fr;
        border: round #1e3a5f;
        margin-bottom: 1;
        padding: 0 1;
    }
    #action-panel {
        height: auto;
        border: round #92400e;
        padding: 0 2;
        margin-bottom: 0;
    }
    #situation-text {
        color: #e5e7eb;
        margin-bottom: 1;
    }
    #choices-display {
        color: #d1d5db;
        margin-bottom: 1;
    }
    #choice-input {
        margin-top: 0;
    }
    #status-bar {
        height: 1;
        background: #111827;
        color: #6b7280;
        padding: 0 2;
        dock: bottom;
    }

    /* ── Debrief view ────────────────────────────────────── */
    #debrief-view {
        height: 1fr;
        padding: 0 1;
    }
    #debrief-log {
        height: 1fr;
    }

    /* ── Logs tab ────────────────────────────────────────── */
    #event-log {
        height: 1fr;
        padding: 1;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("n", "new_session", "New Session"),
    ]

    def __init__(self, base_url: str = DEFAULT_URL) -> None:
        super().__init__()
        self.base_url = base_url

        # Setup state
        self._setup_idx: int = 0
        self._setup_vals: dict[str, str] = {}

        # Scenario picker state (populated after profile steps complete)
        self._scenario_list: list[tuple[str, str]] = []  # [(module_id, scenario_id), ...]
        self._chosen_module_id: str = ""
        self._chosen_scenario_id: str = ""
        self._picking_scenario: bool = False  # True while waiting for scenario number input

        # Game state
        self._session_id: Optional[str] = None
        self._game_state: Optional[dict] = None
        self._choices: list[dict] = []

        # Input mode flags — mutually exclusive per turn
        self._awaiting: bool = False   # player can type
        self._freewrite: bool = False  # in free-write sub-mode
        self._lost_mode: bool = False  # game-over via loss, waiting for R/D
        self._won_mode: bool = False   # game-over via win, waiting for D

    # ── Compose ──────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with TabbedContent(initial="game-pane"):
            with TabPane("⚔  Game", id="game-pane"):
                with ContentSwitcher(initial="setup-view", id="switcher"):

                    # ── Setup screen ─────────────────────────────────────
                    with Container(id="setup-view"):
                        with Vertical(id="setup-box"):
                            yield Label("YOUR  CUBICLE  ALLY", id="setup-title")
                            yield Label(
                                "A compliance training scenario. Your choices have consequences.",
                                id="setup-subtitle",
                            )
                            yield Label("", id="setup-field-label")
                            yield Input(id="setup-input")
                            yield Label("", id="setup-progress")

                    # ── Game screen ──────────────────────────────────────
                    with Vertical(id="game-view"):
                        with Horizontal(id="arena-row"):
                            with Vertical(id="sprite-panel"):
                                yield Static("", id="sprite-art", markup=True)
                            with Vertical(id="info-panel"):
                                yield Static("", id="hp-bar", markup=True)
                                yield Static("", id="step-info")
                                yield Static("", id="session-info")
                        yield RichLog(
                            id="chat-log", highlight=True, markup=True, wrap=True
                        )
                        with Vertical(id="action-panel"):
                            yield Static("", id="situation-text", markup=True)
                            yield Static("", id="choices-display", markup=True)
                            yield Input(
                                placeholder="A / B / C / F  ›  Enter",
                                id="choice-input",
                            )

                    # ── Debrief screen ───────────────────────────────────
                    with ScrollableContainer(id="debrief-view"):
                        yield RichLog(
                            id="debrief-log", highlight=True, markup=True, wrap=True
                        )

                yield Static("…", id="status-bar", markup=True)

            with TabPane("📋  Logs", id="logs-pane"):
                yield RichLog(
                    id="event-log", highlight=True, markup=True, wrap=True
                )

        yield Footer()

    def on_mount(self) -> None:
        self._advance_setup()

    # ── Setup flow ────────────────────────────────────────────────────────────

    def _advance_setup(self) -> None:
        """Step through profile fields; when done, trigger scenario picker."""
        if self._setup_idx < len(_SETUP_STEPS):
            key, label, default = _SETUP_STEPS[self._setup_idx]
            hint = f"  [dim](default: {default})[/dim]" if default else ""
            self.query_one("#setup-field-label", Label).update(
                f"[bold]{label}[/bold]{hint}"
            )
            inp = self.query_one("#setup-input", Input)
            inp.placeholder = default
            inp.value = ""
            self.query_one("#setup-progress", Label).update(
                f"[dim]{self._setup_idx + 1} / {len(_SETUP_STEPS) + 1}[/dim]"
            )
            inp.focus()
        else:
            # Profile complete — fetch modules and show scenario picker
            self._load_scenarios_for_picker()

    @on(Input.Submitted, "#setup-input")
    def _on_setup_submitted(self, event: Input.Submitted) -> None:
        if self._picking_scenario:
            self._on_scenario_number_entered(event.value.strip())
            return

        if self._setup_idx >= len(_SETUP_STEPS):
            return

        key, _, default = _SETUP_STEPS[self._setup_idx]
        self._setup_vals[key] = event.value.strip() or default
        self._setup_idx += 1
        self._advance_setup()

    # ── Scenario picker ───────────────────────────────────────────────────────

    def _load_scenarios_for_picker(self) -> None:
        self._picking_scenario = False
        self.query_one("#setup-field-label", Label).update(
            "[dim]Loading scenarios from backend…[/dim]"
        )
        inp = self.query_one("#setup-input", Input)
        inp.disabled = True
        inp.placeholder = "Loading…"
        self.query_one("#setup-progress", Label).update(
            f"[dim]{len(_SETUP_STEPS) + 1} / {len(_SETUP_STEPS) + 1}[/dim]"
        )
        self._fetch_scenarios_worker()

    @work(thread=True)
    def _fetch_scenarios_worker(self) -> None:
        for attempt in range(1, 16):
            try:
                _get(self.base_url, "/health", timeout=5)
                break
            except Exception:
                if attempt == 15:
                    self.call_from_thread(
                        self._fatal, "Backend unreachable after 15 attempts."
                    )
                    return
                self.call_from_thread(
                    self._set_status,
                    f"Waiting for backend… (attempt {attempt}/15)",
                )
                time.sleep(2)

        try:
            modules = _get(self.base_url, "/modules")
        except Exception as exc:
            self.call_from_thread(self._fatal, f"Failed to load modules: {exc}")
            return
        self.call_from_thread(self._show_scenario_picker, modules)

    def _show_scenario_picker(self, modules: list) -> None:
        """Build numbered scenario list and prompt the user to pick one."""
        self._scenario_list = []
        lines: list[str] = ["[bold]Choose a scenario — type the number and press Enter[/bold]\n"]
        n = 1
        for mod in modules:
            module_id = mod.get("module_id", "")
            module_name = mod.get("title") or module_id
            lines.append(f"[cyan bold]{module_name}[/cyan bold]")
            for scenario in mod.get("scenarios", []):
                scenario_id = scenario.get("id", "")
                title = scenario.get("title", scenario_id)
                lines.append(f"  [yellow][{n}][/yellow]  {title}")
                self._scenario_list.append((module_id, scenario_id))
                n += 1

        self.query_one("#setup-field-label", Label).update("\n".join(lines))
        inp = self.query_one("#setup-input", Input)
        inp.disabled = False
        inp.placeholder = f"Enter 1–{n - 1}"
        inp.value = ""
        inp.focus()
        self._picking_scenario = True
        self._set_status("Choose a scenario number then press Enter")

    def _on_scenario_number_entered(self, raw: str) -> None:
        try:
            choice = int(raw)
        except ValueError:
            self._set_status("[red]Enter a valid number[/red]")
            return

        if choice < 1 or choice > len(self._scenario_list):
            self._set_status(f"[red]Enter a number between 1 and {len(self._scenario_list)}[/red]")
            return

        self._chosen_module_id, self._chosen_scenario_id = self._scenario_list[choice - 1]
        self._picking_scenario = False
        self._begin_session()

    # ── Session start ─────────────────────────────────────────────────────────

    def _begin_session(self) -> None:
        self._set_status("Starting session…")
        self._log("[yellow]Starting session…[/yellow]")
        self._session_start_worker()

    @work(thread=True)
    def _session_start_worker(self) -> None:
        sv = self._setup_vals
        try:
            data = _post(self.base_url, "/session/start", {
                "player_profile": {
                    "name":        sv.get("name", "Player"),
                    "role":        sv.get("role", "Software Engineer"),
                    "seniority":   sv.get("seniority", "Mid-level"),
                    "domain":      sv.get("domain", "Technology"),
                    "raw_context": sv.get("resume", ""),
                },
                "module_id":   self._chosen_module_id,
                "scenario_id": self._chosen_scenario_id,
            })
        except requests.HTTPError as exc:
            self.call_from_thread(
                self._fatal,
                f"Session start {exc.response.status_code}: {exc.response.text[:200]}",
            )
            return
        except Exception as exc:
            self.call_from_thread(self._fatal, f"Session start error: {exc}")
            return

        sid = data["session_id"]
        gs = data["game_state"]
        self.call_from_thread(self._log, f"[dim]Session: {sid}[/dim]")
        self.call_from_thread(self._on_session_ready, sid, gs)

    def _on_session_ready(self, session_id: str, game_state: dict) -> None:
        self._session_id = session_id
        self._game_state = game_state
        self.query_one("#switcher", ContentSwitcher).current = "game-view"
        self._render_current_turn()

    # ── Turn rendering ────────────────────────────────────────────────────────

    def _render_current_turn(self) -> None:
        gs = self._game_state
        if not gs:
            return
        history = gs.get("history", [])
        if not history:
            return

        turn = history[-1]
        actors = gs.get("actors", [])
        actor_map = {a["actor_id"]: a for a in actors}

        # HP + step
        hp = gs.get("player_hp", 100)
        max_hp = gs.get("max_hp", 100)
        self.query_one("#hp-bar", Static).update(_hp_markup(hp, max_hp))
        step = gs.get("current_step", 0)
        max_steps = gs.get("max_steps", 6)
        self.query_one("#step-info", Static).update(
            f"Step [bold]{step}[/bold] / {max_steps}"
        )
        sid_short = (self._session_id or "")[:16]
        self.query_one("#session-info", Static).update(f"[dim]{sid_short}…[/dim]")

        # Actor reactions → chat log
        chat = self.query_one("#chat-log", RichLog)
        reactions = turn.get("actor_reactions", [])
        last_actor_id: Optional[str] = None
        last_actor_role: str = ""

        for r in reactions:
            aid = r["actor_id"]
            actor = actor_map.get(aid, {})
            role = actor.get("role", "")
            role_short = role.split(".")[0].strip()
            chat.write(
                f"[bold cyan]{aid.upper()}[/bold cyan]  [dim]{role_short}[/dim]"
            )
            chat.write(f'  [italic]{r["dialogue"]}[/italic]')
            chat.write("")
            last_actor_id = aid
            last_actor_role = role

        # Sprite — last speaking actor, or player if no reactions
        if last_actor_id:
            sprite = _sprite_for(last_actor_id, last_actor_role)
            self.query_one("#sprite-art", Static).update(
                f"[cyan]{sprite}[/cyan]\n[bold]{last_actor_id.capitalize()}[/bold]"
            )
        else:
            self.query_one("#sprite-art", Static).update(
                f"[green]{_SPRITES['player']}[/green]\n[bold green]You[/bold green]"
            )

        # Situation
        situation = turn.get("situation", "")
        self.query_one("#situation-text", Static).update(
            f"[bold]Scene[/bold]\n{situation}"
        )

        # Choices
        choices = turn.get("choices_offered", [])
        self._choices = choices
        status = gs.get("status", "active")

        if choices and status == "active":
            labels = ["A", "B", "C"]
            lines = [
                f"  [yellow bold]\\[{labels[i]}][/yellow bold]  {c['label']}"
                for i, c in enumerate(choices[:3])
            ]
            lines.append(
                "  [yellow bold]\\[F][/yellow bold]  [dim]Free-write your own response[/dim]"
            )
            self.query_one("#choices-display", Static).update("\n".join(lines))
            self._enable_input("A / B / C  or  F to free-write  ›  Enter to confirm")
            self._awaiting = True
            self._freewrite = False
            self._lost_mode = False
            self._won_mode = False
            self._set_status("Your move — press \\[A], \\[B], \\[C] or \\[F]")
        else:
            self.query_one("#choices-display", Static).update("")

        self._log(f"[dim]Turn {step}: {situation[:80]}…[/dim]")

    # ── Input helpers ─────────────────────────────────────────────────────────

    def _enable_input(self, placeholder: str = "") -> None:
        inp = self.query_one("#choice-input", Input)
        inp.disabled = False
        inp.placeholder = placeholder
        inp.value = ""
        inp.focus()

    def _disable_input(self, placeholder: str = "Processing…") -> None:
        inp = self.query_one("#choice-input", Input)
        inp.disabled = True
        inp.placeholder = placeholder
        inp.value = ""

    # ── Choice handling ───────────────────────────────────────────────────────

    @on(Input.Submitted, "#choice-input")
    def _on_choice_input(self, event: Input.Submitted) -> None:
        raw = event.value.strip()
        event.input.value = ""

        if not self._awaiting:
            return

        # Win state: only D is valid → go to debrief
        if self._won_mode:
            key = raw.lower()
            if key in ("d", "debrief"):
                self._awaiting = False
                self._won_mode = False
                self._disable_input()
                self._do_debrief()
            else:
                self._set_status("[red]Type  D  then Enter[/red]")
            return

        # Loss state: R = retry, D = debrief
        if self._lost_mode:
            key = raw.lower()
            if key in ("r", "retry"):
                self._awaiting = False
                self._lost_mode = False
                self._disable_input()
                self._do_retry()
            elif key in ("d", "debrief"):
                self._awaiting = False
                self._lost_mode = False
                self._disable_input()
                self._do_debrief()
            else:
                self._set_status("[red]Type  R  (retry) or  D  (debrief) then Enter[/red]")
            return

        # Free-write sub-mode
        if self._freewrite:
            if raw:
                self._freewrite = False
                self._submit_choice(raw)
            return

        # Normal A/B/C/F
        key = raw.lower()
        if key in ("a", "b", "c"):
            idx = {"a": 0, "b": 1, "c": 2}[key]
            if idx < len(self._choices):
                self._submit_choice(self._choices[idx]["label"])
        elif key == "f":
            self._freewrite = True
            self._enable_input("Type your response and press Enter…")
            self._set_status("Free-write mode — type your response then Enter")
        else:
            self._set_status("[red]Invalid — press  A,  B,  C  or  F[/red]")

    def _submit_choice(self, player_choice: str) -> None:
        self._awaiting = False
        self._disable_input()
        chat = self.query_one("#chat-log", RichLog)
        chat.write(f"\n[bold green]YOU[/bold green]  {player_choice}\n")
        self.query_one("#sprite-art", Static).update(
            f"[green]{_SPRITES['player']}[/green]\n[bold green]You[/bold green]"
        )
        self._set_status("Processing turn…")
        self._log(f"[green]Player:[/green] {player_choice}")
        self._turn_submit_worker(player_choice)

    # ── Turn submit worker ────────────────────────────────────────────────────

    @work(thread=True)
    def _turn_submit_worker(self, player_choice: str) -> None:
        try:
            data = _post(self.base_url, "/turn/submit", {
                "session_id": self._session_id,
                "player_choice": player_choice,
            })
        except requests.HTTPError as exc:
            status_code = exc.response.status_code
            try:
                detail = exc.response.json().get("detail", exc.response.text[:200])
            except Exception:
                detail = exc.response.text[:200]

            if status_code == 422:
                # Guardrail rejection — recoverable; re-enable the arena so the
                # player can try a different response.
                self.call_from_thread(self._on_turn_rejected, str(detail))
            else:
                self.call_from_thread(
                    self._fatal, f"Turn submit {status_code}: {detail}"
                )
            return
        except Exception as exc:
            self.call_from_thread(self._fatal, f"Turn error: {exc}")
            return

        gs = data["game_state"]
        self.call_from_thread(
            self._log,
            f"[dim]HP={gs.get('player_hp')} status={gs.get('status')}[/dim]",
        )
        self.call_from_thread(self._on_turn_done, gs)

    def _on_turn_rejected(self, reason: str) -> None:
        """Recover the arena after a guardrail rejection (HTTP 422)."""
        self._log(f"[red]Guardrail:[/red] {reason}")
        self._set_status(f"[red]Blocked:[/red] {reason} — try a different response")

        # Restore choices display and re-enable input so the player can retry
        choices = self._choices
        if choices:
            labels = ["A", "B", "C"]
            lines = [
                f"  [yellow bold]\\[{labels[i]}][/yellow bold]  {c['label']}"
                for i, c in enumerate(choices[:3])
            ]
            lines.append(
                "  [yellow bold]\\[F][/yellow bold]  [dim]Free-write your own response[/dim]"
            )
            self.query_one("#choices-display", Static).update("\n".join(lines))
            self._enable_input("A / B / C  or  F to free-write  ›  Enter to confirm")

        self._awaiting = True
        self._freewrite = False

    def _on_turn_done(self, game_state: dict) -> None:
        self._game_state = game_state
        status = game_state.get("status", "active")
        self._render_current_turn()

        if status == "won":
            self.query_one("#chat-log", RichLog).write(
                "\n[bold green]━━  YOU WON  ━━[/bold green]\n"
            )
            self.query_one("#choices-display", Static).update(
                "  [yellow bold]\\[D][/yellow bold]  View debrief"
            )
            self._enable_input("D (debrief)  ›  Enter")
            self._awaiting = True
            self._won_mode = True
            self._set_status("[green]Scenario complete![/green]  \\[D] view debrief  |  \\[N] new session")
            self._log("[green]Scenario won.[/green]")

        elif status == "lost":
            self.query_one("#chat-log", RichLog).write(
                "\n[bold red]━━  YOU RAN OUT OF HP  ━━[/bold red]\n"
            )
            self.query_one("#choices-display", Static).update(
                "  [yellow bold]\\[R][/yellow bold]  Retry the same scenario\n"
                "  [yellow bold]\\[D][/yellow bold]  View debrief"
            )
            self._enable_input("R (retry)  or  D (debrief)  ›  Enter")
            self._awaiting = True
            self._lost_mode = True
            self._set_status("[red]Game over![/red]  \\[R] retry  |  \\[D] debrief  |  \\[N] new session")
            self._log("[red]Game lost.[/red]")

    # ── Debrief ───────────────────────────────────────────────────────────────

    def _do_debrief(self) -> None:
        self._set_status("Generating debrief…")
        self._log("[yellow]Fetching debrief…[/yellow]")
        self._debrief_worker()

    @work(thread=True)
    def _debrief_worker(self) -> None:
        try:
            debrief = _get(self.base_url, f"/session/{self._session_id}/debrief")
        except Exception as exc:
            self.call_from_thread(self._fatal, f"Debrief error: {exc}")
            return
        self.call_from_thread(self._render_debrief, debrief)

    def _render_debrief(self, debrief: dict) -> None:
        self.query_one("#switcher", ContentSwitcher).current = "debrief-view"
        log = self.query_one("#debrief-log", RichLog)
        log.clear()

        outcome = debrief.get("outcome", "unknown")
        score = debrief.get("overall_score", 0)

        if outcome == "won":
            log.write("[bold green]═══  YOU WON  ═══[/bold green]\n")
        else:
            log.write("[bold red]═══  YOU LOST  ═══[/bold red]\n")

        log.write(f"[bold]Overall score: {score}/100[/bold]")
        log.write(f"\n{debrief.get('summary', '')}\n")

        for t in debrief.get("turn_breakdowns", []):
            delta = t.get("hp_delta", 0)
            delta_str = (
                f"[red]{delta}[/red]" if delta < 0 else f"[green]+{delta}[/green]"
            )
            log.write(f"\n[bold]Step {t.get('step', '?')}[/bold]  HP {delta_str}")
            log.write(f"  You said:      {t.get('player_choice', '')}")
            if t.get("what_happened"):
                log.write(f"  What happened: {t['what_happened']}")
            log.write(f"  Insight:       {t.get('compliance_insight', '')}")

        concepts = debrief.get("key_concepts", [])
        if concepts:
            log.write("\n[bold]Key Concepts[/bold]")
            for c in concepts:
                log.write(f"  • {c}")

        followup = debrief.get("recommended_followup", [])
        if followup:
            log.write("\n[bold]Recommended Follow-up[/bold]")
            for m in followup:
                log.write(f"  → {m}")

        log.write("\n[dim]Press \\[N] to train another module  |  \\[Q] to quit[/dim]")
        self._set_status("Debrief complete — \\[N] new session  |  \\[Q] quit")
        self._log("[green]Debrief rendered.[/green]")

    # ── Retry ─────────────────────────────────────────────────────────────────

    def _do_retry(self) -> None:
        self._set_status("Resetting session…")
        self._log("[yellow]Retrying…[/yellow]")
        self._retry_worker()

    @work(thread=True)
    def _retry_worker(self) -> None:
        try:
            # /session/{id}/retry returns game_state directly (not wrapped in a dict)
            game_state = _post(
                self.base_url,
                f"/session/{self._session_id}/retry",
                {},
            )
        except Exception as exc:
            self.call_from_thread(self._fatal, f"Retry error: {exc}")
            return
        self.call_from_thread(self._on_retry_done, game_state)

    def _on_retry_done(self, game_state: dict) -> None:
        self._game_state = game_state
        chat = self.query_one("#chat-log", RichLog)
        chat.clear()
        chat.write("[bold yellow]── Session Reset ──[/bold yellow]\n")
        self.query_one("#choices-display", Static).update("")
        self._render_current_turn()
        self._log("[yellow]Session reset.[/yellow]")

    # ── New session (Train Another Module) ────────────────────────────────────

    def action_new_session(self) -> None:
        """Reset all state and return to the setup screen."""
        # Clear game state
        self._session_id = None
        self._game_state = None
        self._choices = []

        # Clear scenario selection
        self._scenario_list = []
        self._chosen_module_id = ""
        self._chosen_scenario_id = ""
        self._picking_scenario = False

        # Clear input mode flags
        self._awaiting = False
        self._freewrite = False
        self._lost_mode = False
        self._won_mode = False

        # Clear setup
        self._setup_idx = 0
        self._setup_vals = {}

        # Clear UI
        self.query_one("#chat-log", RichLog).clear()
        self.query_one("#debrief-log", RichLog).clear()
        self.query_one("#choices-display", Static).update("")
        self.query_one("#situation-text", Static).update("")
        self.query_one("#sprite-art", Static).update("")
        self.query_one("#hp-bar", Static).update("")
        self.query_one("#step-info", Static).update("")
        self.query_one("#session-info", Static).update("")

        inp = self.query_one("#choice-input", Input)
        inp.disabled = True
        inp.value = ""

        # Navigate back to setup
        self.query_one("#switcher", ContentSwitcher).current = "setup-view"
        self._set_status("…")
        self._log("[cyan]New session started.[/cyan]")
        self._advance_setup()

    # ── Utilities ─────────────────────────────────────────────────────────────

    def _set_status(self, msg: str) -> None:
        self.query_one("#status-bar", Static).update(msg)

    def _log(self, msg: str) -> None:
        self.query_one("#event-log", RichLog).write(msg)

    def _fatal(self, msg: str) -> None:
        self._set_status(f"[bold red]ERROR[/bold red]  {msg}")
        self._log(f"[bold red]FATAL:[/bold red] {msg}")


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Your Cubicle Ally — TUI")
    parser.add_argument("--url", default=DEFAULT_URL, help="Backend base URL")
    args = parser.parse_args()

    try:
        CubicleAllyApp(base_url=args.url).run()
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
