# Interactive Agentic Training System — Core Idea

## One-Line Vision
> A Pokemon PvP-style interactive compliance training system where employees battle through real workplace scenarios, making choices that matter — and learning from every hit they take.

---

## Problem Statement

- Corporate compliance training (POSH, Security, etc.) is passive, forgettable, and checkbox-driven
- Employees have no safe environment to practice real decision-making under pressure
- There is no personalization — the same video plays for a senior engineer and a new intern
- No feedback loop — you either pass a quiz or you don't, with no understanding of *why*

---

## The Experience (End to End)

### 1. Player Setup
- User uploads their **resume or job description**
- The system extracts their **role, seniority, domain** — this personalizes the scenario difficulty and framing
- User selects a **compliance module** (e.g. POSH, Security Awareness, Data Privacy)

### 2. The Arena (Pokemon PvP Style)
- A scenario is loaded — an AI agent plays the "opponent" (a coworker, a situation, a threat actor, etc.)
- The player sees a **situation description** and a set of **3 action choices + free-write option**
- The player picks or writes their response
- An evaluator agent judges the quality/accuracy of the response against compliance standards
- **Health Points (HP) are deducted** for bad or inaccurate answers — good answers may recover HP or deal "damage" to the scenario
- The scenario branches based on the player's choices — consequences feel real

### 3. Scenario Steps
- Each scenario runs for a fixed number of steps (e.g. 5–8 turns)
- The narrative evolves based on the player's choices — no two runs are identical
- A scenario can end early if HP drops to zero (player "loses") or all steps are completed

### 4. Debrief & Learnings
- After the scenario ends, the system delivers a **full debrief**:
  - What the player did well
  - Where they went wrong and why
  - The compliance concept behind each turning point
  - A score/grade and areas to revisit

---

## Core Design Principles

- **Modular** — compliance modules are plug-and-play; adding a new topic doesn't touch core logic
- **Extendable** — new agent behaviors, new scenario types, new HP mechanics can be layered in
- **Personalized** — role/seniority context from resume shapes scenario framing and difficulty
- **Consequential** — choices matter; the narrative actually changes

---

## Compliance Modules (Planned)

| Module | Description |
|---|---|
| POSH | Prevention of Sexual Harassment — workplace scenarios, reporting, bystander behavior |
| Security Awareness | Phishing, social engineering, data handling, password hygiene |
| Data Privacy | GDPR/DPDP scenarios, handling PII, data sharing decisions |
| Code of Conduct | Conflict of interest, gifts, insider information |

---

## Notes / Scratchpad

_Add raw thoughts here_
