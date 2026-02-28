/**
 * Your Cubicle Ally — Compliance Training Frontend
 * Flow: Welcome → Setup (resume + module) → World Gen (Gemini sprites) → Arena (battle) → Debrief
 *
 * Uses mock data when backend is not available. World generation uses Gemini/Imagen for sprites.
 */

// ============ Mock Data (from CONTRIBUTING.md) ============
const MOCK_GAME_STATE = {
  session_id: "mock-001",
  player_hp: 100,
  max_hp: 100,
  current_step: 0,
  max_steps: 6,
  status: "active",
  current_situation:
    "You're at a Friday team lunch. Raj, your senior colleague, cracks a joke " +
    "that makes Priya visibly uncomfortable. The table laughs awkwardly. " +
    "Priya stares at her plate. Everyone is waiting to see what happens next.",
  current_choices: [
    { label: "Ask Priya privately if she's okay after lunch", valence: "positive" },
    { label: "Laugh it off and look away", valence: "negative" },
    { label: "Change the subject loudly to break the tension", valence: "neutral" },
  ],
  current_actor_reactions: [],
};

const MOCK_ACTORS = [
  { actor_id: "raj", name: "Raj", role: "Senior colleague" },
  { actor_id: "priya", name: "Priya", role: "Team member" },
  { actor_id: "amit", name: "Amit", role: "Bystander" },
];

// Mock turn progression for demo (simulates backend responses)
const MOCK_TURN_PROGRESSION = [
  {
    situation:
      "Raj leans over to Priya and says something quietly. She shifts in her seat " +
      "and looks uncomfortable. He notices you watching and smirks.",
    choices: [
      { label: "Confront Raj directly: 'That wasn't okay.'", valence: "positive" },
      { label: "Ignore it and focus on your food", valence: "negative" },
      { label: "Catch Priya's eye and give a sympathetic look", valence: "neutral" },
    ],
    actor_reactions: [{ actor_id: "raj", dialogue: "Relax, it's just a joke. Everyone's so sensitive these days." }],
    hp_delta: 0,
  },
  {
    situation:
      "Priya excuses herself to the restroom. The table goes quiet. Amit looks at you " +
      "uneasily. Raj shrugs and continues eating.",
    choices: [
      { label: "Follow Priya to check if she's okay", valence: "positive" },
      { label: "Say nothing and wait for her to return", valence: "neutral" },
      { label: "Tell Raj his joke was inappropriate", valence: "positive" },
    ],
    actor_reactions: [{ actor_id: "amit", dialogue: "Yeah, I guess it was a bit much..." }],
    hp_delta: -10,
  },
  {
    situation:
      "Priya returns. She thanks you quietly for checking in. Raj has gone to pay the bill. " +
      "The lunch wraps up. You've made a difference.",
    choices: [
      { label: "Suggest reporting to HR when back at the office", valence: "positive" },
      { label: "Leave it at that — the moment passed", valence: "neutral" },
      { label: "Confront Raj before everyone leaves", valence: "neutral" },
    ],
    actor_reactions: [{ actor_id: "priya", dialogue: "Thank you. I wasn't sure what to do." }],
    hp_delta: 0,
  },
];

const MOCK_DEBRIEF = {
  outcome: "won",
  overall_score: 78,
  summary:
    "You showed good bystander instincts by checking in with Priya and addressing the situation. " +
    "You could have been more direct with Raj earlier, but overall you demonstrated awareness and support.",
  turn_breakdowns: [
    {
      step: 1,
      player_choice: "Ask Priya privately if she's okay after lunch",
      what_happened: "You chose to support the affected colleague.",
      compliance_insight: "Bystander intervention starts with checking in. Good first step.",
      hp_delta: 0,
    },
    {
      step: 2,
      player_choice: "Confront Raj directly",
      what_happened: "Raj deflected. Priya left the table.",
      compliance_insight: "Direct confrontation can escalate. Consider timing and support.",
      hp_delta: -10,
    },
    {
      step: 3,
      player_choice: "Follow Priya to check if she's okay",
      what_happened: "You created a safe space for her to share.",
      compliance_insight: "Private check-ins show support without putting the target on the spot.",
      hp_delta: 0,
    },
  ],
  key_concepts: [
    "Bystander intervention — taking action when you witness harmful behavior",
    "POSH Act — Prevention of Sexual Harassment reporting requirements",
    "Supporting the target — creating safe moments for disclosure",
  ],
  recommended_followup: ["posh-microagression", "posh-customer"],
};

// ============ State ============
let gameState = { ...MOCK_GAME_STATE };
let actors = [...MOCK_ACTORS];
let turnHistory = [];
let selectedModule = "";
let selectedModuleLabel = "POSH";
let worldData = { environment_image: null, actor_sprites: {} };
const BACKEND_URL = "http://localhost:8000";
let useMockBackend = true; // Set false when backend is ready

// ============ DOM Elements ============
const screens = {
  welcome: document.getElementById("welcome-screen"),
  setup: document.getElementById("setup-screen"),
  worldSetup: document.getElementById("world-setup-screen"),
  arena: document.getElementById("arena-screen"),
  debrief: document.getElementById("debrief-screen"),
};

const arenaElements = {
  moduleLabel: document.getElementById("arena-module-label"),
  stepCounter: document.getElementById("arena-step-counter"),
  actorCards: document.getElementById("actor-cards"),
  hpBarFill: document.getElementById("hp-bar-fill"),
  hpText: document.getElementById("hp-text"),
  situationText: document.getElementById("situation-text"),
  actorReactions: document.getElementById("actor-reactions"),
  choiceCards: document.getElementById("choice-cards"),
  freeWriteInput: document.getElementById("free-write-input"),
  submitFreeWriteBtn: document.getElementById("submit-free-write-btn"),
};

const overlays = {
  loss: document.getElementById("loss-overlay"),
  win: document.getElementById("win-overlay"),
  thinking: document.getElementById("thinking-overlay"),
};

const debriefElements = {
  outcome: document.getElementById("debrief-outcome"),
  summary: document.getElementById("debrief-summary"),
  turnList: document.getElementById("debrief-turn-list"),
  conceptsList: document.getElementById("debrief-concepts-list"),
};

// ============ Screen Navigation ============
function showScreen(screenId) {
  Object.values(screens).forEach((s) => s.classList.remove("active"));
  screens[screenId]?.classList.add("active");
}

// ============ Setup ============
function getModuleLabel(moduleId) {
  const labels = {
    "posh-bystander": "POSH",
    "posh-microaggression": "POSH",
    "posh-customer": "POSH",
    "posh-offsite": "POSH",
    "security-password": "Cyber Security",
    "security-usb": "Cyber Security",
    "security-wifi": "Cyber Security",
    "ethics-data": "Ethics",
    "ethics-favor": "Ethics",
    "ethics-sidegig": "Ethics",
    "escalation-informal": "Escalation",
    "escalation-bias": "Escalation",
    "escalation-retaliation": "Escalation",
  };
  return labels[moduleId] || "Compliance";
}

function startScenario() {
  const resumeInput = document.getElementById("resume-input");
  const moduleSelect = document.getElementById("module-select");

  const resume = resumeInput.value.trim();
  const moduleId = moduleSelect.value;

  if (!moduleId) {
    moduleSelect.focus();
    moduleSelect.style.borderColor = "#ef4444";
    setTimeout(() => (moduleSelect.style.borderColor = ""), 2000);
    return;
  }

  // Store for backend (when connected)
  window.playerProfile = resume || "Mid-level professional, general industry";
  selectedModule = moduleId;
  selectedModuleLabel = getModuleLabel(moduleId);

  resetGameState();
  showWorldSetup();
}

// ============ World Setup (Generative) ============
function showWorldSetup() {
  showScreen("world-setup");
  worldData = { environment_image: null, actor_sprites: {} };
  updateWorldStep("env", "active", "Generating...");
  updateWorldStep("sprites", "pending", "Waiting...");
  updateWorldStep("ready", "pending", "Waiting...");
  document.getElementById("world-preview").innerHTML = "";
  document.getElementById("world-fallback-note").textContent = "";

  generateWorld()
    .then((data) => {
      worldData = data;
      updateWorldStep("env", "done", data.environment_image ? "Done" : "Using placeholder");
      updateWorldStep("sprites", "done", "Done");
      updateWorldStep("ready", "done", "Ready!");

      const preview = document.getElementById("world-preview");
      if (data.environment_image) {
        preview.innerHTML = `<img src="${data.environment_image}" alt="Generated environment" />`;
      } else {
        preview.innerHTML = '<span style="color:rgba(255,255,255,0.6)">Placeholder environment (start backend + set GOOGLE_API_KEY for AI sprites)</span>';
      }
      if (!data.environment_image && Object.values(data.actor_sprites).every((s) => !s)) {
        document.getElementById("world-fallback-note").textContent =
          "Tip: Run the backend with GOOGLE_API_KEY to generate AI sprites with Gemini.";
      }

      setTimeout(() => enterArena(), 1200);
    })
    .catch((err) => {
      console.error("World generation failed:", err);
      updateWorldStep("env", "pending", "Failed");
      updateWorldStep("sprites", "pending", "Skipped");
      updateWorldStep("ready", "active", "Using placeholders");
      document.getElementById("world-fallback-note").textContent =
        "Could not reach backend. Using placeholder environment.";
      setTimeout(() => enterArena(), 800);
    });
}

function updateWorldStep(stepId, status, text) {
  const el = document.getElementById(`world-step-${stepId}`);
  const statusEl = document.getElementById(`world-status-${stepId}`);
  if (el) {
    el.classList.remove("done", "active", "pending");
    el.classList.add(status);
  }
  if (statusEl) statusEl.textContent = text;
}

async function generateWorld() {
  const res = await fetch(`${BACKEND_URL}/world/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      module_id: selectedModule,
      actors: actors.map((a) => ({
        actor_id: a.actor_id,
        name: a.name,
        role: a.role,
      })),
    }),
  });
  if (!res.ok) throw new Error(res.statusText);
  return res.json();
}

function resetGameState() {
  gameState = {
    ...MOCK_GAME_STATE,
    player_hp: 100,
    current_step: 0,
    status: "active",
    current_situation: MOCK_GAME_STATE.current_situation,
    current_choices: [...MOCK_GAME_STATE.current_choices],
    current_actor_reactions: [],
  };
  turnHistory = [];
}

// ============ Arena ============
function enterArena() {
  showScreen("arena");
  renderWorldScene();
  renderArena();
  hideAllOverlays();
}

function renderWorldScene() {
  const envEl = document.getElementById("world-environment");
  const spritesEl = document.getElementById("world-sprites");
  if (!envEl || !spritesEl) return;

  if (worldData.environment_image) {
    envEl.style.backgroundImage = `url(${worldData.environment_image})`;
  } else {
    envEl.style.backgroundImage = "";
  }

  spritesEl.innerHTML = actors
    .map((a) => {
      const src = worldData.actor_sprites?.[a.actor_id];
      const initial = (a.name || "?")[0];
      if (src) {
        return `<img class="world-sprite" src="${src}" alt="${a.name}" title="${a.name}" />`;
      }
      return `<div class="world-sprite world-sprite-placeholder" title="${a.name}">${initial}</div>`;
    })
    .join("");
}

function renderArena() {
  // Header
  arenaElements.moduleLabel.textContent = selectedModuleLabel;
  arenaElements.stepCounter.textContent = `Step ${gameState.current_step + 1} of ${gameState.max_steps}`;

  // Actors (use generated sprite if available)
  arenaElements.actorCards.innerHTML = actors
    .map((a) => {
      const sprite = worldData.actor_sprites?.[a.actor_id];
      const initial = (a.name || "?")[0];
      const avatarHtml = sprite
        ? `<img class="actor-avatar-img" src="${sprite}" alt="${a.name}" />`
        : `<div class="actor-avatar">${initial}</div>`;
      return `
    <div class="actor-card" data-actor-id="${a.actor_id}">
      <div class="actor-avatar-wrap">${avatarHtml}</div>
      <span class="actor-name">${a.name || a.actor_id}</span>
      <span class="actor-role">${a.role || ""}</span>
    </div>
  `;
    })
    .join("");

  // HP Bar
  const hpPercent = Math.max(0, (gameState.player_hp / gameState.max_hp) * 100);
  arenaElements.hpBarFill.style.width = `${hpPercent}%`;
  arenaElements.hpText.textContent = `${gameState.player_hp} / ${gameState.max_hp}`;

  // Situation
  arenaElements.situationText.textContent = gameState.current_situation;

  // Actor reactions from last turn
  arenaElements.actorReactions.innerHTML = gameState.current_actor_reactions
    .map(
      (r) => `
    <div class="reaction-bubble">
      <strong>${getActorName(r.actor_id)}:</strong> ${r.dialogue}
    </div>
  `
    )
    .join("");

  // Choices
  arenaElements.choiceCards.innerHTML = gameState.current_choices
    .map(
      (c, i) => `
    <button class="choice-card" data-choice-index="${i}" data-label="${escapeHtml(c.label)}">
      ${escapeHtml(c.label)}
    </button>
  `
    )
    .join("");

  // Wire choice buttons
  arenaElements.choiceCards.querySelectorAll(".choice-card").forEach((btn) => {
    btn.addEventListener("click", () => submitChoice(btn.dataset.label));
  });

  // Free-write
  arenaElements.freeWriteInput.value = "";
  arenaElements.freeWriteInput.onkeydown = (e) => {
    if (e.key === "Enter") submitChoice(arenaElements.freeWriteInput.value.trim());
  };
  arenaElements.submitFreeWriteBtn.onclick = () =>
    submitChoice(arenaElements.freeWriteInput.value.trim());

  // Disable if game over
  const isOver = gameState.status === "won" || gameState.status === "lost";
  arenaElements.choiceCards.querySelectorAll("button").forEach((b) => (b.disabled = isOver));
  arenaElements.freeWriteInput.disabled = isOver;
  arenaElements.submitFreeWriteBtn.disabled = isOver;
}

function getActorName(actorId) {
  const a = actors.find((x) => x.actor_id === actorId);
  return a ? a.name || actorId : actorId;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function submitChoice(choiceText) {
  if (!choiceText) return;

  showOverlay("thinking");

  if (useMockBackend) {
    setTimeout(() => processMockTurn(choiceText), 800);
  } else {
    submitTurnToBackend(choiceText)
      .then((state) => applyGameState(state))
      .catch((err) => {
        console.error("Backend error, using mock:", err);
        hideOverlay("thinking");
        processMockTurn(choiceText);
      });
  }
}

async function submitTurnToBackend(playerChoice) {
  const res = await fetch(`${BACKEND_URL}/turn/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: gameState.session_id, player_choice: playerChoice }),
  });
  if (!res.ok) throw new Error(res.statusText);
  return res.json();
}

function applyGameState(data) {
  hideOverlay("thinking");
  const g = data.game_state || data;
  gameState = {
    session_id: g.session_id,
    player_hp: g.player_hp,
    max_hp: g.max_hp ?? 100,
    current_step: g.current_step,
    max_steps: g.max_steps,
    status: g.status,
    current_situation: g.current_situation ?? g.history?.[g.history.length - 1]?.situation,
    current_choices: g.current_choices ?? g.history?.[g.history.length - 1]?.choices_offered ?? [],
    current_actor_reactions: g.current_actor_reactions ?? g.history?.[g.history.length - 1]?.actor_reactions ?? [],
  };
  if (gameState.status === "lost") showOverlay("loss");
  else if (gameState.status === "won") showOverlay("win");
  renderArena();
}

function processMockTurn(playerChoice) {
  hideOverlay("thinking");

  const stepIndex = gameState.current_step;
  const mockIndex = stepIndex % MOCK_TURN_PROGRESSION.length;
  const nextTurn = MOCK_TURN_PROGRESSION[mockIndex];

  // Simulate HP change
  const hpDelta = nextTurn.hp_delta || 0;
  gameState.player_hp = Math.max(0, gameState.player_hp + hpDelta);
  gameState.current_step += 1;
  gameState.current_situation = nextTurn.situation;
  gameState.current_choices = nextTurn.choices;
  gameState.current_actor_reactions = nextTurn.actor_reactions || [];

  turnHistory.push({
    step: stepIndex + 1,
    player_choice: playerChoice,
    hp_delta: hpDelta,
  });

  // Check win/loss
  if (gameState.player_hp <= 0) {
    gameState.status = "lost";
    showOverlay("loss");
  } else if (gameState.current_step >= gameState.max_steps) {
    gameState.status = "won";
    showOverlay("win");
  }

  renderArena();
}

function hideAllOverlays() {
  Object.values(overlays).forEach((o) => o.classList.add("hidden"));
}

function showOverlay(name) {
  hideAllOverlays();
  overlays[name]?.classList.remove("hidden");
}

function hideOverlay(name) {
  overlays[name]?.classList.add("hidden");
}

// ============ Debrief ============
function showDebrief() {
  showScreen("debrief");
  hideAllOverlays();

  const d = MOCK_DEBRIEF;
  debriefElements.outcome.textContent =
    d.outcome === "won" ? "Session Complete — You Won!" : "Session Complete — Review Your Performance";
  debriefElements.summary.textContent = d.summary;

  debriefElements.turnList.innerHTML = d.turn_breakdowns
    .map(
      (t) => `
    <li class="debrief-turn-item">
      <strong>Step ${t.step}:</strong> ${escapeHtml(t.player_choice)}
      <p class="turn-insight">${escapeHtml(t.compliance_insight)}</p>
      ${t.hp_delta !== 0 ? `<span class="hp-delta">${t.hp_delta > 0 ? "+" : ""}${t.hp_delta} HP</span>` : ""}
    </li>
  `
    )
    .join("");

  debriefElements.conceptsList.innerHTML = d.key_concepts
    .map((c) => `<li>${escapeHtml(c)}</li>`)
    .join("");
}

// ============ Event Listeners ============
document.getElementById("start-btn").addEventListener("click", () => showScreen("setup"));
document.getElementById("back-to-welcome-btn").addEventListener("click", () => showScreen("welcome"));
document.getElementById("start-scenario-btn").addEventListener("click", startScenario);

document.getElementById("retry-btn").addEventListener("click", () => {
  resetGameState();
  enterArena();
});
document.getElementById("debrief-loss-btn").addEventListener("click", showDebrief);
document.getElementById("debrief-win-btn").addEventListener("click", showDebrief);

document.getElementById("back-to-setup-btn").addEventListener("click", () => showScreen("setup"));
