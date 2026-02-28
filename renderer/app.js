/**
 * Your Cubicle Ally — Compliance Training Frontend
 * Flow: Welcome → Setup (resume + module) → World Gen (Gemini sprites) → Arena (battle) → Debrief
 *
 * Uses mock data when backend is not available. World generation uses Gemini/Imagen for sprites.
 */

// ============ Mock Data (synced with backend: Marcus, Claire, Jordan) ============
const MOCK_GAME_STATE = {
  session_id: "mock-001",
  player_hp: 100,
  max_hp: 100,
  current_step: 0,
  max_steps: 6,
  status: "active",
  current_situation:
    "It's a Friday team lunch at a restaurant. Marcus, your senior colleague, cracks a sexually charged joke loosely directed at Claire. " +
    "The table laughs awkwardly. Claire goes quiet and stares at her plate. " +
    "Everyone is waiting to see what happens next.",
  current_choices: [
    { label: "Ask Claire privately if she's okay after lunch", valence: "positive" },
    { label: "Change the subject loudly to break the tension", valence: "neutral" },
    { label: "Laugh it off and look away", valence: "negative" },
  ],
  current_actor_reactions: [],
};

const MOCK_ACTORS = [
  { actor_id: "marcus", name: "Marcus", role: "Senior colleague" },
  { actor_id: "claire", name: "Claire", role: "Team member" },
  { actor_id: "jordan", name: "Jordan", role: "Bystander" },
];

// Mock turn progression (synced with backend: Marcus, Claire, Jordan)
const MOCK_TURN_PROGRESSION = [
  {
    situation:
      "The group laughs awkwardly. Claire forces a smile but her eyes are down. " +
      "Jordan catches your eye briefly, then looks away. Marcus is still grinning, waiting to see if anyone pushes back.",
    choices: [
      { label: "Tell Marcus directly that the comment wasn't appropriate", valence: "positive" },
      { label: "Ask Jordan quietly what he thought of that", valence: "neutral" },
      { label: "Agree with Marcus and change the subject", valence: "negative" },
    ],
    actor_reactions: [
      { actor_id: "marcus", dialogue: "See? Everyone gets it. You all just need to lighten up." },
      { actor_id: "jordan", dialogue: "I mean... haha... yeah. Anyway, should we order?" },
    ],
    hp_delta: -10,
  },
  {
    situation:
      "Claire quietly excuses herself to the bathroom. Marcus watches her go. " +
      "'She'll get over it,' he says to no one in particular. Jordan shifts in his seat. This is your moment.",
    choices: [
      { label: "Follow Claire to check in with her privately", valence: "positive" },
      { label: "Challenge Marcus's 'she'll get over it' comment", valence: "neutral" },
      { label: "Nod and move on — it's not your place", valence: "negative" },
    ],
    actor_reactions: [
      { actor_id: "marcus", dialogue: "She's always been a bit sensitive. You know how it is." },
      { actor_id: "jordan", dialogue: "I don't know... that felt like a bit much to me, honestly." },
    ],
    hp_delta: -10,
  },
  {
    situation:
      "Claire returns to the table. She looks composed but quieter than before. " +
      "Marcus makes another off-colour remark — smaller this time. Jordan gives you a pointed look.",
    choices: [
      { label: "Suggest reporting to HR when back at the office", valence: "positive" },
      { label: "Leave it at that — the moment passed", valence: "neutral" },
      { label: "Confront Marcus before everyone leaves", valence: "neutral" },
    ],
    actor_reactions: [{ actor_id: "claire", dialogue: "Thank you. I wasn't sure what to do." }],
    hp_delta: 0,
  },
];

const MOCK_DEBRIEF = {
  outcome: "won",
  overall_score: 78,
  summary:
    "You showed good bystander instincts by checking in with Claire and addressing the situation. " +
    "You could have been more direct with Marcus earlier, but overall you demonstrated awareness and support.",
  turn_breakdowns: [
    {
      step: 1,
      player_choice: "Ask Claire privately if she's okay after lunch",
      what_happened: "You chose to support the affected colleague.",
      compliance_insight: "Bystander intervention starts with checking in. Good first step.",
      hp_delta: 0,
    },
    {
      step: 2,
      player_choice: "Tell Marcus directly that the comment wasn't appropriate",
      what_happened: "Marcus deflected. Claire left the table.",
      compliance_insight: "Direct confrontation can escalate. Consider timing and support.",
      hp_delta: -10,
    },
    {
      step: 3,
      player_choice: "Follow Claire to check in with her privately",
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
let selectedModuleId = "";
let selectedScenarioId = "";
let selectedModuleLabel = "";
let worldData = { environment_image: null, actor_sprites: {} };
const BACKEND_URL = "http://localhost:8000";
let useMockBackend = false; // Use real backend; falls back to mock if backend unavailable
let modulesData = []; // Fetched from GET /modules
let isSubmittingTurn = false;
let ttsEnabled = localStorage.getItem("cubicle-ally-tts") !== "false";
let dialogueHistory = [];
let dialogueCounter = 0;
let pendingPlayerMessageId = null;
let lastPlayedAudioSignature = "";

// ============ DOM Elements ============
const screens = {
  welcome: document.getElementById("welcome-screen"),
  setup: document.getElementById("setup-screen"),
  "world-setup": document.getElementById("world-setup-screen"),
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
/** Map backend GameState (with history[]) to our flat UI format. */
function mapBackendGameState(g) {
  const lastTurn = g.history?.length ? g.history[g.history.length - 1] : null;
  return {
    session_id: g.session_id,
    player_hp: g.player_hp,
    max_hp: g.max_hp ?? 100,
    current_step: g.current_step ?? 0,
    max_steps: g.max_steps ?? 6,
    status: g.status,
    current_situation: lastTurn?.situation ?? "",
    current_choices: lastTurn?.choices_offered ?? [],
    current_actor_reactions: lastTurn?.actor_reactions ?? [],
  };
}

/** Map backend role text to short, scenario-agnostic role for sprite prompts. */
function spriteRoleFromActor(actor) {
  const r = (actor.role || "").toLowerCase();
  if (r.includes("offender") || r.includes("senior")) return "Senior colleague";
  if (r.includes("target") || r.includes("newer")) return "Team member";
  if (r.includes("bystander")) return "Colleague";
  const first = (actor.role || "").split(".")[0].trim();
  return first || "Colleague";
}

/** Convert backend ActorInstance to display format { actor_id, name, role, persona } for world gen + arena + TTS. */
function actorsFromGameState(gameState) {
  if (!gameState?.actors?.length) return [...MOCK_ACTORS];
  return gameState.actors.map((a) => ({
    actor_id: a.actor_id,
    name: (a.actor_id || "").charAt(0).toUpperCase() + (a.actor_id || "").slice(1),
    role: spriteRoleFromActor(a),
    persona: a.persona || "",
  }));
}

function getModuleDisplayName(moduleId) {
  const names = {
    posh: "Prevention of Sexual Harassment (POSH)",
    cybersecurity: "Cyber Security",
    ethics: "Ethics",
    escalation: "Escalation",
  };
  return names[moduleId] || moduleId;
}

async function loadModules() {
  const select = document.getElementById("module-select");
  select.innerHTML = '<option value="">Loading...</option>';
  try {
    const res = await fetch(`${BACKEND_URL}/modules`);
    if (!res.ok) throw new Error(res.statusText);
    modulesData = await res.json();
  } catch (err) {
    console.error("Failed to load modules:", err);
    select.innerHTML = '<option value="">Backend unavailable. Start the server.</option>';
    return;
  }
  select.innerHTML = '<option value="">Choose a scenario...</option>';
  for (const mod of modulesData) {
    const optgroup = document.createElement("optgroup");
    optgroup.label = getModuleDisplayName(mod.module_id);
    for (const s of mod.scenarios || []) {
      const opt = document.createElement("option");
      opt.value = s.id;
      opt.textContent = s.title;
      opt.dataset.moduleId = mod.module_id;
      optgroup.appendChild(opt);
    }
    select.appendChild(optgroup);
  }
}

async function startScenario() {
  const nameInput = document.getElementById("player-name-input");
  const resumeInput = document.getElementById("resume-input");
  const moduleSelect = document.getElementById("module-select");

  const playerName = (nameInput?.value || "").trim() || "there";
  const resume = resumeInput.value.trim();
  const scenarioId = moduleSelect.value;
  const selectedOpt = moduleSelect.options[moduleSelect.selectedIndex];
  const moduleId = selectedOpt?.dataset?.moduleId;

  if (!scenarioId || !moduleId) {
    moduleSelect.focus();
    moduleSelect.style.borderColor = "#ef4444";
    setTimeout(() => (moduleSelect.style.borderColor = ""), 2000);
    return;
  }

  selectedModuleId = moduleId;
  selectedScenarioId = scenarioId;
  selectedModuleLabel = getModuleDisplayName(moduleId);

  const playerProfile = {
    name: playerName,
    role: "Professional",
    seniority: "Mid-level",
    domain: "General",
    raw_context: resume || "Mid-level professional, general industry",
  };

  try {
    const res = await fetch(`${BACKEND_URL}/session/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        player_profile: playerProfile,
        module_id: moduleId,
        scenario_id: scenarioId,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert("Failed to start session: " + (err.detail || res.statusText));
      return;
    }
    const data = await res.json();
    gameState = mapBackendGameState(data.game_state);
    actors = actorsFromGameState(data.game_state);
    turnHistory = [];
    dialogueHistory = [];
    dialogueCounter = 0;
    pendingPlayerMessageId = null;
    lastPlayedAudioSignature = "";
    showWorldSetup();
  } catch (err) {
    console.error("Backend error:", err);
    alert("Could not reach backend. Is the server running on http://localhost:8000?");
  }
}

// ============ World Setup (Generative) ============
function showWorldSetup() {
  showScreen("world-setup");
  worldData = {
    environment_image: null,
    environment_frames: [],
    actor_sprites: {},
    actor_animations: {},
  };
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
      const hasAny = data.environment_image || Object.values(data.actor_sprites || {}).some((s) => !!s);
      if (!hasAny) {
        document.getElementById("world-fallback-note").textContent =
          "Tip: Set GOOGLE_API_KEY in backend/.env with Imagen access to generate character portraits and office simulation.";
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
  const cached = await getCachedWorldData(selectedScenarioId);
  if (cached) return cached;

  const res = await fetch(`${BACKEND_URL}/world/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      module_id: selectedModuleId,
      scenario_id: selectedScenarioId,
      actors: actors.map((a) => ({
        actor_id: a.actor_id,
        name: a.name,
        role: a.role,
      })),
    }),
  });
  if (!res.ok) throw new Error(res.statusText);
  const data = await res.json();
  if (hasWorldAssets(data)) {
    await setCachedWorldData(selectedScenarioId, data);
  }
  return data;
}

function hasWorldAssets(data) {
  if (!data) return false;
  if (data.environment_image) return true;
  if (Array.isArray(data.environment_frames) && data.environment_frames.some(Boolean)) return true;
  if (data.actor_sprites && Object.values(data.actor_sprites).some(Boolean)) return true;
  if (
    data.actor_animations &&
    Object.values(data.actor_animations).some((frames) => Array.isArray(frames) && frames.some(Boolean))
  ) {
    return true;
  }
  return false;
}

async function getCachedWorldData(scenarioId) {
  if (!scenarioId) return null;
  const api = window.electronAPI;
  if (!api?.getWorldCache) return null;
  try {
    const cached = await api.getWorldCache(scenarioId);
    return hasWorldAssets(cached) ? cached : null;
  } catch (err) {
    console.warn("Failed to read world cache:", err);
    return null;
  }
}

async function setCachedWorldData(scenarioId, worldData) {
  if (!scenarioId || !hasWorldAssets(worldData)) return;
  const api = window.electronAPI;
  if (!api?.setWorldCache) return;
  try {
    await api.setWorldCache(scenarioId, worldData);
  } catch (err) {
    console.warn("Failed to write world cache:", err);
  }
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
  dialogueHistory = [];
  dialogueCounter = 0;
  pendingPlayerMessageId = null;
  lastPlayedAudioSignature = "";
}

// ============ Arena ============
function enterArena() {
  seedInitialDialogueThread();
  showScreen("arena");
  updateTTSButtonState();
  renderWorldScene();
  renderArena();
  hideAllOverlays();
}

/** Fallback: illustrated avatar when AI sprite unavailable. Uses DiceBear. */
function getActorAvatarUrl(actorId, spriteFromBackend) {
  if (spriteFromBackend) return spriteFromBackend;
  return `https://api.dicebear.com/7.x/lorelei/svg?seed=${encodeURIComponent(actorId)}`;
}

function renderWorldScene() {
  const envEl = document.getElementById("world-environment");
  const spritesEl = document.getElementById("world-sprites");
  if (!envEl || !spritesEl) return;

  // Animated environment: crossfade between frames or single image with Ken Burns
  const envFrames = worldData.environment_frames || [];
  if (envFrames.length >= 2) {
    envEl.innerHTML = envFrames
      .map(
        (src, i) =>
          `<div class="env-frame env-frame-${i}" style="background-image:url(${src})"></div>`
      )
      .join("");
    envEl.classList.add("env-animated");
  } else if (worldData.environment_image) {
    envEl.innerHTML = "";
    envEl.style.backgroundImage = `url(${worldData.environment_image})`;
    envEl.classList.add("env-kenburns");
    envEl.classList.remove("env-animated");
  } else {
    envEl.innerHTML = "";
    envEl.style.backgroundImage = "";
    envEl.classList.remove("env-animated", "env-kenburns");
  }

  const speakingIds = new Set(gameState.current_actor_reactions.map((r) => r.actor_id));
  const animFrames = worldData.actor_animations || {};

  spritesEl.innerHTML = actors
    .map((a) => {
      const frames = animFrames[a.actor_id];
      const speaking = speakingIds.has(a.actor_id) ? " speaking" : "";
      const speechIndicator = speaking ? '<span class="sprite-speaking-badge"></span>' : "";

      if (frames && frames.length > 1) {
        const imgs = frames
          .map(
            (src, i) =>
              `<img class="sprite-frame" data-frame="${i}" src="${src}" alt="" />`
          )
          .join("");
        return `<div class="world-sprite-wrapper sprite-animated${speaking}" data-actor-id="${a.actor_id}" data-frames="${frames.length}">
          <div class="sprite-frames">${imgs}</div>
          ${speechIndicator}
        </div>`;
      }

      const src = getActorAvatarUrl(a.actor_id, worldData.actor_sprites?.[a.actor_id]);
      return `<div class="world-sprite-wrapper${speaking}" data-actor-id="${a.actor_id}">
        <img class="world-sprite" src="${src}" alt="${escapeHtml(a.name || a.actor_id)}" title="${escapeHtml(a.name || a.actor_id)}" />
        ${speechIndicator}
      </div>`;
    })
    .join("");
}

function renderArena() {
  // Header
  arenaElements.moduleLabel.textContent = selectedModuleLabel;
  arenaElements.stepCounter.textContent = `Step ${gameState.current_step + 1} of ${gameState.max_steps}`;

  const speakingIds = new Set(gameState.current_actor_reactions.map((r) => r.actor_id));

  arenaElements.actorCards.innerHTML = actors
    .map((a) => {
      const avatarSrc = getActorAvatarUrl(a.actor_id, worldData.actor_sprites?.[a.actor_id]);
      const speaking = speakingIds.has(a.actor_id);
      const speakingBadge = speaking ? '<span class="actor-speaking-badge"></span>' : "";
      return `
    <div class="actor-card${speaking ? " speaking" : ""}" data-actor-id="${a.actor_id}">
      <div class="actor-avatar-wrap">${speakingBadge}<img class="actor-avatar-img" src="${avatarSrc}" alt="${escapeHtml(a.name || a.actor_id)}" /></div>
      <span class="actor-name">${escapeHtml(a.name || a.actor_id)}</span>
      <span class="actor-role">${escapeHtml(a.role || "")}</span>
    </div>
  `;
    })
    .join("");

  // HP Bar
  const hpPercent = Math.max(0, (gameState.player_hp / gameState.max_hp) * 100);
  arenaElements.hpBarFill.style.width = `${hpPercent}%`;
  arenaElements.hpText.textContent = `${gameState.player_hp} / ${gameState.max_hp}`;

  // Situation — replace element to retrigger entrance animation
  const situationWrap = document.querySelector(".narrative-flow");
  if (situationWrap) {
    const p = document.createElement("p");
    p.className = "situation-text";
    p.id = "situation-text";
    p.textContent = gameState.current_situation;
    const old = situationWrap.querySelector("#situation-text");
    if (old) situationWrap.replaceChild(p, old);
    arenaElements.situationText = p;
  }

  // Actor reactions from last turn (interactive dialogue bubbles)
  const reactionsToPlay = [...gameState.current_actor_reactions];
  renderDialogueThread();

  // Play dialogue audio (live voice) if TTS enabled
  const audioSignature = `${gameState.current_step}:${reactionsToPlay
    .map((r) => `${r.actor_id}:${r.dialogue}`)
    .join("|")}`;
  if (ttsEnabled && reactionsToPlay.length > 0 && audioSignature !== lastPlayedAudioSignature) {
    lastPlayedAudioSignature = audioSignature;
    playDialogueAudio(reactionsToPlay);
  }

  // Highlight speaking actors in sidebar
  arenaElements.actorCards.querySelectorAll(".actor-card").forEach((card) => {
    card.classList.toggle("speaking", speakingIds.has(card.dataset.actorId));
  });

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

function pushDialogueEntry({ speakerType, text, actorId = "", pending = false }) {
  const entry = {
    id: `d-${dialogueCounter++}`,
    speakerType,
    actorId,
    text,
    pending,
  };
  dialogueHistory.push(entry);
  return entry.id;
}

function markDialogueEntryResolved(entryId) {
  if (!entryId) return;
  const entry = dialogueHistory.find((d) => d.id === entryId);
  if (entry) entry.pending = false;
}

function removeDialogueEntry(entryId) {
  if (!entryId) return;
  dialogueHistory = dialogueHistory.filter((d) => d.id !== entryId);
}

function appendActorDialogues(reactions) {
  for (const r of reactions || []) {
    if (!r?.dialogue?.trim()) continue;
    pushDialogueEntry({
      speakerType: "actor",
      actorId: r.actor_id,
      text: r.dialogue.trim(),
      pending: false,
    });
  }
}

function renderDialogueThread() {
  const html = dialogueHistory
    .map((d) => {
      if (d.speakerType === "narrator") {
        return `
          <div class="dialogue-row narrator">
            <div class="dialogue-bubble">${escapeHtml(d.text)}</div>
          </div>
        `;
      }

      if (d.speakerType === "player") {
        return `
          <div class="dialogue-row player${d.pending ? " pending" : ""}">
            <div class="dialogue-meta">You</div>
            <div class="dialogue-bubble">${escapeHtml(d.text)}</div>
          </div>
        `;
      }

      const actorName = getActorName(d.actorId);
      const avatarUrl = getActorAvatarUrl(d.actorId, worldData.actor_sprites?.[d.actorId]);
      return `
        <div class="dialogue-row actor" data-actor-id="${escapeHtml(d.actorId || "")}">
          <img class="dialogue-avatar" src="${avatarUrl}" alt="${escapeHtml(actorName)}" />
          <div class="dialogue-content">
            <div class="dialogue-meta">${escapeHtml(actorName)}</div>
            <div class="dialogue-bubble">${escapeHtml(d.text)}</div>
          </div>
        </div>
      `;
    })
    .join("");

  arenaElements.actorReactions.innerHTML =
    html || '<div class="dialogue-placeholder">Dialogue will appear here as the scene unfolds.</div>';
  arenaElements.actorReactions.scrollTop = arenaElements.actorReactions.scrollHeight;
}

function seedInitialDialogueThread() {
  if (dialogueHistory.length > 0) return;
  const openingReactions = gameState.current_actor_reactions || [];
  if (openingReactions.length > 0) {
    appendActorDialogues(openingReactions);
    return;
  }
  if (gameState.current_situation?.trim()) {
    pushDialogueEntry({
      speakerType: "narrator",
      text: gameState.current_situation.trim(),
    });
  }
}

// ============ TTS / Live Voice Dialogue ============
async function playDialogueAudio(reactions) {
  for (const r of reactions) {
    if (!ttsEnabled || !r.dialogue?.trim()) continue;
    const actor = actors.find((x) => x.actor_id === r.actor_id);
    try {
      const res = await fetch(`${BACKEND_URL}/tts/speech/base64`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: r.dialogue,
          actor_id: r.actor_id,
          persona: actor?.persona || undefined,
        }),
      });
      if (!res.ok) {
        await speakWithSystemVoice(r.dialogue, r.actor_id);
        continue;
      }
      const { audio } = await res.json();
      if (!audio) {
        await speakWithSystemVoice(r.dialogue, r.actor_id);
        continue;
      }
      await new Promise((resolve, reject) => {
        const el = new Audio(audio);
        el.onended = resolve;
        el.onerror = reject;
        el.play().catch(reject);
      });
    } catch (err) {
      console.warn("TTS playback failed:", err);
      await speakWithSystemVoice(r.dialogue, r.actor_id);
    }
  }
}

function pickSystemVoice(actorId = "") {
  const synth = window.speechSynthesis;
  if (!synth) return null;
  const voices = synth.getVoices ? synth.getVoices() : [];
  if (!voices.length) return null;

  const english = voices.filter((v) => (v.lang || "").toLowerCase().startsWith("en"));
  const pool = english.length ? english : voices;
  const seed = (actorId || "default").split("").reduce((acc, ch) => acc + ch.charCodeAt(0), 0);
  return pool[seed % pool.length] || pool[0];
}

async function speakWithSystemVoice(text, actorId = "") {
  if (!text?.trim() || !window.speechSynthesis || typeof SpeechSynthesisUtterance === "undefined") {
    return;
  }

  await new Promise((resolve) => {
    const u = new SpeechSynthesisUtterance(text);
    const voice = pickSystemVoice(actorId);
    if (voice) u.voice = voice;
    u.rate = 1;
    u.pitch = 1;
    u.onend = resolve;
    u.onerror = resolve;
    window.speechSynthesis.speak(u);
  });
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function submitChoice(choiceText) {
  if (!choiceText || isSubmittingTurn) return;
  isSubmittingTurn = true;
  pendingPlayerMessageId = pushDialogueEntry({
    speakerType: "player",
    text: choiceText,
    pending: true,
  });
  renderDialogueThread();

  arenaElements.choiceCards.querySelectorAll("button").forEach((b) => (b.disabled = true));
  arenaElements.freeWriteInput.disabled = true;
  arenaElements.submitFreeWriteBtn.disabled = true;

  showOverlay("thinking");

  submitTurnToBackend(choiceText)
    .then((state) => applyGameState(state))
    .catch((err) => {
      console.error("Backend error:", err);
      removeDialogueEntry(pendingPlayerMessageId);
      pendingPlayerMessageId = null;
      hideOverlay("thinking");
      alert("Turn submission failed: " + (err.message || "Server error"));
      renderArena();
    });
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
  gameState = mapBackendGameState(g);
  markDialogueEntryResolved(pendingPlayerMessageId);
  pendingPlayerMessageId = null;
  appendActorDialogues(gameState.current_actor_reactions);
  isSubmittingTurn = false;
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
  markDialogueEntryResolved(pendingPlayerMessageId);
  pendingPlayerMessageId = null;
  appendActorDialogues(gameState.current_actor_reactions);

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

  isSubmittingTurn = false;
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
async function showDebrief() {
  showScreen("debrief");
  hideAllOverlays();

  let d = { outcome: "won", overall_score: 0, summary: "No debrief available.", turn_breakdowns: [], key_concepts: [] };
  const sid = gameState.session_id;
  if (sid) {
    debriefElements.outcome.textContent = "Loading debrief...";
    debriefElements.summary.textContent = "";
    debriefElements.turnList.innerHTML = "";
    debriefElements.conceptsList.innerHTML = "";
    try {
      const res = await fetch(`${BACKEND_URL}/session/${sid}/debrief`);
      if (res.ok) {
        d = await res.json();
      }
    } catch (err) {
      console.warn("Debrief API failed:", err);
      d.summary = "Could not load debrief. " + (err.message || "");
    }
  }
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
document.getElementById("start-btn").addEventListener("click", () => {
  showScreen("setup");
  loadModules();
});
document.getElementById("back-to-welcome-btn").addEventListener("click", () => showScreen("welcome"));
document.getElementById("start-scenario-btn").addEventListener("click", startScenario);

document.getElementById("retry-btn").addEventListener("click", async () => {
  const sid = gameState.session_id;
  if (sid) {
    try {
      const res = await fetch(`${BACKEND_URL}/session/${sid}/retry`, { method: "POST" });
      if (res.ok) {
        const g = await res.json();
        gameState = mapBackendGameState(g);
        dialogueHistory = [];
        dialogueCounter = 0;
        pendingPlayerMessageId = null;
        lastPlayedAudioSignature = "";
        hideAllOverlays();
        enterArena();
        return;
      }
    } catch (err) {
      console.warn("Retry API failed:", err);
    }
  }
  alert("Could not retry. Please go back and start a new scenario.");
});
document.getElementById("debrief-loss-btn").addEventListener("click", () => showDebrief());
document.getElementById("debrief-win-btn").addEventListener("click", () => showDebrief());

document.getElementById("back-to-setup-btn").addEventListener("click", () => {
  showScreen("setup");
  loadModules();
});

document.getElementById("tts-toggle-btn")?.addEventListener("click", () => {
  ttsEnabled = !ttsEnabled;
  localStorage.setItem("cubicle-ally-tts", ttsEnabled.toString());
  updateTTSButtonState();
});

function updateTTSButtonState() {
  const btn = document.getElementById("tts-toggle-btn");
  if (!btn) return;
  const icon = btn.querySelector(".tts-icon");
  if (icon) icon.textContent = ttsEnabled ? "🔊" : "🔇";
  btn.classList.toggle("muted", !ttsEnabled);
}
