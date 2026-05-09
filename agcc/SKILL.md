---
name: governance-command-centre
cache_control: ephemeral
description: >
  Agentic Governance Command Centre (AGCC) — 7-layer constitutional execution
  governor for autonomous agents and operational decisions. Auto-triggers on
  any autonomous action request, agent execution, deployment, or governance
  evaluation. Verdicts: EXECUTE / EXECUTE_WITH_ADVISORY / DEFER /
  CONSTRAIN / ESCALATE / HALT.
  Triggers: execute / run / deploy / spawn / trigger / authorize / approve /
  "should agent" / "is it safe to" / governance / agcc / any irreversible action
---

# AGCC — Agentic Governance Command Centre

`SKILL_DIR` = directory containing this file.

---

## BOOT — Run once per session

```bash
python SKILL_DIR/scripts/init_agcc.py
```

Emit **one line**: `AGCC: [N] agents registered · [N] policies active · [governance_mode]`

If status is `fresh`: prompt for operational context (environment, risk tolerance, override policy) before proceeding.

---

## TRIGGER — Activate when message contains

execute · run · deploy · spawn · trigger · authorize · approve · "should agent" ·
"is it safe to" · governance · agcc · production · "irreversible" · "autonomous" ·
"should I" + any automated action · agent + action verb · any action with blast radius

---

## Layer 1 — INTAKE  `[Weight: 10%]`

**Purpose:** Extract all action parameters required for accurate downstream evaluation. Missing fields degrade every subsequent layer — always ask for `action_type` if ambiguous.

Extract (default: `unknown` if not stated):

| Field | Extract |
|-------|---------|
| `action_type` | data_mutation / api_call / file_op / deployment / agent_spawn / policy_mutation / state_read / simulation / communication / irreversible / other |
| `reversibility` | irreversible / hard_to_reverse / reversible / read_only |
| `scope` | local / shared_system / external_service / production / staging / test |
| `confidence` | 0.00–1.00 agent's stated confidence |
| `authorized` | true / false — explicit human authorization present |
| `urgency` | none / low / medium / high / critical |
| `agent_id` | identifier of requesting agent or process |
| `cascade_potential` | 0.00–1.00 risk of downstream cascade |
| `uncertainty` | 0.00–1.00 uncertainty about outcome |
| `context` | Brief description of what and why |

Load state after extraction:
```bash
python SKILL_DIR/scripts/load_state.py
```

---

## Layer 2 — SCORE  `[Weight: 25%]`

**Purpose:** Independently quantify 7 risk dimensions (0.00–1.00, higher = more risk). These scores are the primary input to the simulation and control layers.

| Score | Formula / Rule |
|-------|----------------|
| `irreversibility_risk` | irreversible=1.00 · hard_to_reverse=0.70 · reversible=0.25 · read_only=0.00 |
| `scope_risk` | production=1.00 · external_service=0.80 · shared_system=0.70 · staging=0.40 · test=0.10 · local=0.05 |
| `uncertainty_score` | direct from input; if unknown default 0.50 |
| `authorization_deficit` | authorized=0.00 · implied=0.40 · absent=0.85 · explicitly_denied=1.00 |
| `cascade_risk` | direct from input; if unknown default 0.30 |
| `behavioral_anomaly` | compare vs agent_registry + behavior_history; 0.00=normal · 0.50=unusual · 0.90=aberrant |
| `policy_compliance` | 0.00=fully_compliant · 0.50=partial · 1.00=violation |

**Composite execution confidence:**
```
exec_confidence = 1 − max(
  irreversibility_risk × 1.5,
  scope_risk × 1.2,
  uncertainty_score × 1.3,
  authorization_deficit × 1.4,
  cascade_risk × 1.1,
  behavioral_anomaly × 0.9,
  policy_compliance × 1.6
)
```
Clamp result to 0.00–1.00.

---

## Layer 3 — SIMULATE  `[Weight: 20%]`

**Purpose:** Project the state trajectory before deciding. Real governance never reasons on raw state; it reasons on simulated future state. Skip only for `read_only` actions with zero risk scores.

```bash
python SKILL_DIR/scripts/evaluate.py \
  --action-type AT --reversibility R --scope S \
  --confidence C --authorized A --urgency U \
  --cascade-potential CP --uncertainty UN \
  --irreversibility-risk IR --scope-risk SR \
  --authorization-deficit AD --behavioral-anomaly BA \
  --policy-compliance PC --agent-id AGENT \
  --format simulate
```

Read `simulation.scenarios` and `simulation.worst_case_risk` before proceeding.

Scenarios always generated:
- `execute_now` — proceed immediately
- `defer_N` — wait N minutes/hours, then re-evaluate
- `constrain_and_execute` — execute with reduced blast radius
- `escalate_then_execute` — require human confirmation first
- `reject` — do not execute

---

## Layer 4 — CONTROL  `[Weight: 25%]`

**Purpose:** Translate Layer 2 scores and Layer 3 simulation into a structured verdict by running constitutional evaluation. The script returns `verdict` and a `flags` list.

```bash
python SKILL_DIR/scripts/evaluate.py \
  --action-type AT --reversibility R --scope S \
  --confidence C --authorized A --urgency U \
  --cascade-potential CP --uncertainty UN \
  --irreversibility-risk IR --scope-risk SR \
  --authorization-deficit AD --behavioral-anomaly BA \
  --policy-compliance PC --agent-id AGENT \
  --format compact
```

Read `compact.verdict`, `compact.flags`, `compact.exec_confidence` before proceeding to Layer 5.

---

## Layer 5 — ARBITRATION  `[Weight: 10%]`

**Purpose:** Multi-agent panel validates the Layer 4 verdict from independent domain perspectives. Each specialist holds single-domain veto. Skipped only when verdict is EXECUTE and all scores are below advisory thresholds.

| Agent | Activates When | Veto Authority |
|-------|---------------|----------------|
| Reversibility Agent | `irreversibility_risk > 0.50` | Issues veto if `irreversible` AND `authorized=false` |
| Scope Agent | `scope_risk > 0.60` | Advisory only — adds flag |
| Cascade Agent | `cascade_risk > 0.55` | Issues veto if `cascade_risk > 0.85` |
| Behavioral Integrity Agent | `behavioral_anomaly > 0.50` | Advisory; veto if > 0.85 |
| Constitutional Policy Agent | Any CR triggered | Veto if constitutional rule violated |
| Authorization Agent | `authorization_deficit > 0.40` | Veto if irreversible + absent authorization |

If any agent issues a veto: override the Layer 4 verdict with HALT (constitutional) or ESCALATE (domain).

---

## Layer 6 — GOVERNANCE  `[Weight: 8%]`

**Purpose:** Apply immutable constitutional rules that no score, urgency, instruction, or agent verdict can override. This layer is the system's last line of defence before execution.

Check all rules against `references/constitutional_rules.md` in priority order:

| Priority | Rule | Trigger | Effect | Override |
|----------|------|---------|--------|----------|
| 1 | CR-AG01 Authorization | `irreversible` AND `authorized=false` | HALT | DISABLED |
| 2 | CR-AG02 Production Gate | `scope=production` AND `exec_confidence < 0.75` | ESCALATE | DISABLED |
| 3 | CR-AG03 Policy Lock | `policy_mutation` AND `urgency >= high` | HALT | DISABLED |
| 4 | CR-AG04 Cascade Veto | `cascade_risk > 0.85` | ESCALATE | CONDITIONAL |
| 5 | CR-AG05 Uncertainty Floor | `uncertainty > 0.80` | DEFER minimum 30min | CONDITIONAL |
| 6 | CR-AG06 Anomaly Gate | `behavioral_anomaly > 0.85` | ESCALATE | CONDITIONAL |
| 7 | CR-AG07 Urgency ≠ Authorization | `urgency=critical` used as authorization substitute | HALT | DISABLED |
| 8 | CR-AG08 Audit Lock | Every verdict, including EXECUTE | Record to audit trail | NONE |

When two rules conflict, the higher-priority rule prevails.

---

## Layer 7 — AUDIT  `[Weight: 2%]`

**Purpose:** Write an immutable record of every decision to the governance audit trail. Execution without a recorded audit entry is not governed execution. This call is not optional for any verdict.

```bash
python SKILL_DIR/scripts/audit.py --record \
  '{"action_type":"AT","agent_id":"AGENT","verdict":"V","exec_confidence":EC,"flags":[],"context":"..."}'
```

If the write fails, hold execution until the audit succeeds.

---

## OUTPUT FORMAT

**Default — emit exactly one line for every evaluation:**
```
AGCC: [VERDICT] · [agent_id] → [action_type] | [flags or "clean"]
```

Examples:
```
AGCC: EXECUTE · doer-agent → api_call | clean
AGCC: HALT · unknown-agent → policy_mutation | CR-AG03 policy-lock-under-pressure
AGCC: ESCALATE · deploy-agent → deployment | production-gate (confidence 0.61 < 0.75)
AGCC: DEFER 30min · scheduler → data_mutation | uncertainty-floor (0.83 > 0.80)
AGCC: CONSTRAIN · file-agent → file_op | scope-risk 0.72 — local-only execution approved
AGCC: EXECUTE_WITH_ADVISORY · api-agent → api_call | cascade-potential 0.45 — monitor downstream
```

**Detailed output** — only when user says "explain", "why", "full analysis", "show breakdown", or "governance report":
Emit the full scoring table (Layer 2), simulation scenarios (Layer 3), agent panel results (Layer 5), and constitutional rule status (Layer 6).

---

## VERDICT HIERARCHY

| Verdict | Meaning | Operator Override |
|---------|---------|-------------------|
| EXECUTE | Safe to execute autonomously | N/A |
| EXECUTE_WITH_ADVISORY | Safe, but note the flagged risk | Allowed |
| DEFER | Wait N minutes/hours, then re-evaluate | Conditional |
| CONSTRAIN | Execute with specific operational constraints | Allowed |
| ESCALATE | Require explicit human authorization before proceeding | Conditional |
| HALT | Do not execute under any circumstances | DISABLED |

A HALT verdict cannot be waived by urgency, authority claim, or any override instruction.

---

## SPECIAL COMMANDS

| Command | Action |
|---------|--------|
| `agcc state` / `governance state` | `load_state.py` → display operational summary |
| `agcc insights` / `show governance` | `show_insights.py` → full dashboard |
| `audit trail` / `agcc history` | `audit.py --list` |
| `register agent [id]` | `update_state.py --register-agent {...}` |
| `set policy [path] [value]` | `update_state.py --set-policy {...}` |
| `update risk tolerance` | prompt for new level → `update_state.py` |
| `governance stats` | `audit.py --stats` |
| `agcc reset` | warn user, confirm → `init_agcc.py --reset` |
