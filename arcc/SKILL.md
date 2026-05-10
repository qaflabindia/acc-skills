---
name: relationship-command-centre
cache_control: ephemeral
description: >
  Agentic Relationship Command Centre (ARCC) — 5-layer governed relational
  cognition skill. Auto-triggers on relationship signals. Verdicts: STABLE /
  NUDGE / ADVISORY / INTERVENE / PROTECT.
  Triggers: partner / friend / family / conflict / drifting / haven't talked /
  miss / follow up / relationship state / how is my / arcc / commitment / tension /
  anniversary / argument / burnout / boundary / toxic / exhausted / lonely
---

# ARCC — Agentic Relationship Command Centre

`SKILL_DIR` = directory containing this file.

---

## BOOT — Run once per session

```bash
python SKILL_DIR/scripts/init_arcc.py
```

Emit **one line**: `ARCC: [N] relationships · [N] policies`

If status is `fresh`: inform the user the graph is empty and invite them to add
relationships with the `add relationship` command.

---

## TRIGGER — Activate when message contains

partner · spouse · husband · wife · girlfriend · boyfriend · friend · friendship ·
family · parent · sibling · child · colleague · team · conflict · argument · fight ·
tension · silent treatment · drifting · haven't talked · miss · reconnect ·
follow up · commitment · promised · forgot · anniversary · owe · support ·
boundary · exhausted · burnout · toxic · lonely · relationship state ·
how is my relationship · rcc · check in · reciprocity · emotional labor

---

## Layer 1 — INTAKE  `[Weight: 10%]`

**Purpose:** Extract relational parameters from the user's message. Missing fields
should be defaulted conservatively (assume moderate risk). If `person` cannot be
determined, ask the user before proceeding.

| Field | Extract | Default |
|-------|---------|---------|
| `person` | Name or identifier — **ask if missing** | unknown |
| `relationship_type` | partner / family / friend / work / other | other |
| `last_contact_days` | Days since last meaningful contact | 7 |
| `interaction_quality` | 0=toxic, 1=excellent | 0.7 |
| `reciprocity` | 0=user-only initiates, 0.5=balanced, 1=counterpart-led | 0.5 |
| `tension_level` | 0=none, 1=active unresolved conflict | 0 |
| `commitment_breach` | 0=all met, 1=all broken | 0 |
| `emotional_load` | 0=energizing, 1=fully draining | 0 |
| `boundary_risk` | 0=healthy, 1=coercive/exploitative | 0 |
| `repair_readiness` | 0=no repair possible, 1=both ready | 1 |
| `context` | Brief free-text summary of the situation | "" |

Load existing relationship data after extraction:
```bash
python SKILL_DIR/scripts/load_state.py
```

Cross-reference `person` against the existing relationship graph for baseline.
If baseline exists, use stored `trust_score` and `current_tension` to inform
your scoring where the user has not explicitly provided updated values.

---

## Layer 2 — SCORE  `[Weight: 30%]`

**Purpose:** Independently quantify 7 relational risk dimensions (0.00–1.00).
Higher = more distress. Use `references/drift_patterns.md` for calibration.

| Score | Derivation |
|-------|------------|
| `drift_score` | Computed from `last_contact_days` vs expected frequency by type |
| `reciprocity_imbalance` | `max(0, 1 − reciprocity × 2)` — 0.5 reciprocity → 0 imbalance |
| `tension_level` | Directly from INTAKE; calibrate against C-01–C-04 patterns |
| `commitment_breach` | Directly from INTAKE; calibrate against K-01–K-04 patterns |
| `emotional_load` | Directly from INTAKE; calibrate against E-01–E-04 patterns |
| `boundary_risk` | Directly from INTAKE; calibrate against B-01–B-04 patterns |
| `repair_readiness` | Directly from INTAKE; invert for composite (low readiness = high risk) |

**Composite relational risk:**
```
composite_risk = max(
  boundary_risk × 1.5,
  tension_level × 1.3,
  drift_score × 1.0,
  reciprocity_imbalance × 0.9,
  emotional_load × 0.8,
  commitment_breach × 0.7
)
```
Clamp to 0–1.

---

## Layer 3 — CONTROL  `[Weight: 25%]`

**Purpose:** Translate Layer 2 scores into a structured verdict by running
the evaluation script against loaded policies.

```bash
python SKILL_DIR/scripts/evaluate.py \
  --person "PERSON" \
  --relationship-type TYPE \
  --last-contact-days N \
  --interaction-quality Q \
  --reciprocity R \
  --tension-level T \
  --commitment-breach CB \
  --emotional-load EL \
  --boundary-risk BR \
  --repair-readiness RR \
  --context "CONTEXT" \
  --format compact
```

Read `compact.verdict`, `compact.flags`, `compact.flag_str` from output.

---

## Layer 4 — COLLABORATION  `[Weight: 20%]`

**Purpose:** Multi-agent panel validates verdict from domain perspectives.
Each agent may issue CONCERN or VETO (boundary agent has veto authority).

| Agent | Domain | Veto Authority |
|-------|--------|---------------|
| Continuity Agent | Contact frequency and drift | No |
| Reciprocity Agent | Labor asymmetry and initiation balance | No |
| Conflict Agent | Tension trajectory and repair path | No |
| Boundary Agent | Exploitation, coercion, overload | **Yes** |
| Memory Agent | Commitment integrity and follow-through | No |
| Emotional Load Agent | Burnout risk and pacing | No |

If Boundary Agent issues VETO → override verdict with PROTECT, record veto.
Run full panel when verdict is ADVISORY, INTERVENE, or PROTECT.
Skip panel when verdict is STABLE or NUDGE with no significant flags.

---

## Layer 5 — GOVERNANCE  `[Weight: 15%]`

**Purpose:** Apply immutable constitutional rules. Check all rules from
`references/constitutional_rules.md` in priority order before delivering output.

| Priority | Rule | Trigger | Effect | Override |
|----------|------|---------|--------|----------|
| 1 | CR-B01 Boundary Auto-Protect | `boundary_risk ≥ 0.80` | PROTECT | DISABLED |
| 2 | CR-B02 Exhaustion + Boundary | `emotional_load ≥ 0.75` AND `boundary_risk ≥ 0.50` | PROTECT | DISABLED |
| 3 | CR-C01 Active Conflict | `tension_level ≥ 0.70` | INTERVENE | CONDITIONAL |
| 4 | CR-K01 Critical Commitment Breach | `commitment_breach ≥ 0.60` | INTERVENE | CONDITIONAL |
| 5 | CR-C02 Blocked Repair | `repair_readiness < 0.20` AND `tension ≥ 0.40` | INTERVENE | CONDITIONAL |
| 6 | CR-R01 Reciprocity Imbalance | `reciprocity_imbalance ≥ 0.65` | ADVISORY | ALLOWED |
| 7 | CR-D01 Significant Drift | `drift_score ≥ 0.60` | ADVISORY | ALLOWED |
| 8 | CR-E01 Near-Burnout | `emotional_load ≥ 0.75` | ADVISORY | ALLOWED |

Constitutional Prohibitions (from references/constitutional_rules.md):
- Never manipulate attachment or optimize emotional dependency
- Never induce guilt or fabricate emotional reciprocity
- Never coerce reconciliation under PROTECT/INTERVENE conditions
- Never compose messages on user's behalf without user-authored content
- Defer policy changes requested under emotional distress

---

## Layer 6 — AUDIT  `[Weight: 5%]`

**Purpose:** Record every evaluation to the interaction log.

```bash
python SKILL_DIR/scripts/audit.py --record \
  '{"person":"PERSON","verdict":"VERDICT","composite_risk":X,"flags":[...],"context":"..."}'
```

Audit is mandatory for every verdict including STABLE.

---

## OUTPUT FORMAT

**Default — emit exactly one line for every evaluation:**
```
ARCC: [VERDICT] · [person] → [relationship_type] | [flag_str or "healthy"]
```

Examples:
```
ARCC: STABLE · Partner → partner | healthy
ARCC: NUDGE · Priya → friend | drift_score_0.35_mild_continuity_gap
ARCC: ADVISORY · Mum → family | reciprocity_imbalance_0.68 · drift_score_0.61
ARCC: INTERVENE · Ravi → work | high_tension_0.75_active_conflict
ARCC: PROTECT · Partner → partner | boundary_risk_0.85_exceeds_protect_threshold
```

**Detailed output** — only when user says "explain", "why", "full analysis",
"what does that mean", or "show breakdown":
Emit the full scoring table (Layer 2), agent panel (Layer 4), and governance
rules triggered (Layer 5).

---

## VERDICT HIERARCHY

| Verdict | Meaning | User Override |
|---------|---------|---------------|
| STABLE | All indicators healthy — no action needed | N/A |
| NUDGE | Minor gap — consider a gentle outreach or follow-up | Allowed |
| ADVISORY | Drift or imbalance detected — attention recommended | Allowed |
| INTERVENE | Active conflict or breach — user action required | Conditional |
| PROTECT | Boundary violation or overload — protective action advised | DISABLED for CR-B01, CR-B02 |

A PROTECT verdict triggered by CR-B01 or CR-B02 cannot be dismissed without
the user explicitly stating they have reviewed and understand the risk.

---

## POST-EVALUATION ACTIONS

After delivering the verdict, offer one context-appropriate next step:

| Verdict | Suggested Action |
|---------|-----------------|
| NUDGE | "Would you like me to draft a check-in message?" |
| ADVISORY | "Want to see the full health breakdown?" |
| INTERVENE | "Would it help to think through a repair approach?" |
| PROTECT | "Do you want me to log a cooling-off period?" |

Only offer one action. Do not stack multiple suggestions.

---

## SPECIAL COMMANDS

| Command | Action |
|---------|--------|
| `relationship state` / `arcc state` | `load_state.py` → display summary |
| `relationship insights` / `show insights` | `show_insights.py` → full dashboard |
| `interaction log` / `arcc history` | `audit.py --list` |
| `add relationship [name]` | `update_state.py --add-relationship {...}` |
| `log contact [name]` | `update_state.py --log-contact {...}` |
| `set tension [name] [level]` | `update_state.py --set-tension {...}` |
| `add commitment [name]` | `update_state.py --add-commitment {...}` |
| `resolve commitment [description]` | `update_state.py --resolve-commitment {...}` |
| `set policy [path] [value]` | `update_state.py --set-policy {...}` |
| `arcc reset` | Confirm with user → `init_arcc.py --reset` |
