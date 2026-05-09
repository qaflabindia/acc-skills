---
name: finance-command-centre
cache_control: ephemeral
description: >
  Agentic Finance Command Centre (AFCC) — 6-layer constitutional payment
  governor. Auto-triggers on any payment intent. Verdicts: APPROVE /
  APPROVE_WITH_ADVISORY / DELAY / RESTRICT / ESCALATE / BLOCK.
  Triggers: pay / transfer / send money / should I pay / is this a scam /
  parcel clearance / KYC block / book / invest / semester fee / rent / EMI
---

# AFCC — Agentic Finance Command Centre

`SKILL_DIR` = directory containing this file.

---

## BOOT — Run once per session

```bash
python SKILL_DIR/scripts/init_afcc.py
```

Emit **one line**: `AFCC: [bank balance] · [N] policies`

If status is `fresh`: ask the user for bank balance, reserve floor, and monthly obligations before proceeding.

---

## TRIGGER — Activate when message contains

pay · transfer · send · invest · deposit · book · clear · "shall I pay" ·
"should I transfer" · parcel · customs · KYC · police + payment · any ₹ amount

---

## Layer 1 — INTAKE  `[Weight: 10%]`

**Purpose:** Extract all payment parameters required for accurate downstream evaluation. Missing or defaulted fields degrade every subsequent layer — always ask for `amount` if not stated.

Extract (default: `unknown` if not stated):

| Field | Extract |
|-------|---------|
| `amount` | Numeric — **ask if missing** |
| `type` | rent / emi / electricity / utility / insurance / tax / school_fee / food / shopping / transfer / investment / other |
| `urgency` | none / low / medium / high / extreme |
| `new_beneficiary` | true / false |
| `authority_claimed` | true / false |
| `authority_verified` | Always `false` unless user confirms an independent callback was completed |
| `reason` | Brief text |

Load state after extraction:
```bash
python SKILL_DIR/scripts/load_state.py
```

---

## Layer 2 — SCORE  `[Weight: 30%]`

**Purpose:** Independently quantify 7 risk dimensions (0.00–1.00, higher = more risk). These scores are the primary input to the verdict engine. No dimension is collapsed into another.

| Score | Formula / Rule |
|-------|----------------|
| `fraud_prob` | Pattern match vs `references/scam_patterns.md` |
| `liquidity_risk` | `(bank − amount − monthly_obligations − reserve_floor) / bank`; clamp 0–1; invert |
| `urgency_score` | none=0.00 · low=0.20 · medium=0.40 · high=0.70 · extreme=0.95; add 0.35 if `authority_claimed=true` |
| `beneficiary_trust` | 0.95 institutional · 0.50 known individual · 0.10 new or unknown |
| `obligation_priority` | 0.95 school_fee / rent / emi / tax · 0.70 utility · 0.05 discretionary |
| `panic_prob` | 0.00 calm · 0.50 confused · 0.90 distressed |
| `legitimacy` | 0.99 routine · 0.50 unusual · 0.05 implausible |

**Composite execution confidence:**
```
execution_confidence = 1 − max(fraud×1.4, urgency×1.2, 1−legitimacy, liquidity, (1−trust)×0.7)
```
Clamp result to 0–1.

---

## Layer 3 — CONTROL  `[Weight: 25%]`

**Purpose:** Translate Layer 2 scores into a structured verdict by running the evaluation script against loaded policies and thresholds. The script returns `compact_verdict` and a `flags` list.

```bash
python SKILL_DIR/scripts/evaluate.py \
  --amount A --type T --urgency U \
  --new-beneficiary B --fraud-prob F --liquidity-risk L \
  --execution-confidence E --obligation-priority O \
  --beneficiary-trust TR --urgency-score US \
  --panic-prob P --authority-claimed AC --authority-verified AV \
  --format compact
```

Read `compact.verdict` and `compact.flags` from script output before proceeding to Layer 4.

---

## Layer 4 — COLLABORATION  `[Weight: 15%]`

**Purpose:** Run a multi-agent panel to validate the Layer 3 verdict from independent domain perspectives. Each agent holds a single-domain veto. Skipped only when verdict is APPROVE and no score exceeds the advisory threshold.

| Agent | Activates When | Action |
|-------|---------------|--------|
| Scam Agent | `fraud_prob > 0.50` | Issues veto if `fraud_prob ≥ 0.80` → escalate to BLOCK |
| Policy Agent | Any CR flagged by Layer 3 | Issues veto if constitutional rule is violated |
| Liquidity Agent | `liquidity_risk > 0.60` | Advisory only — no veto, adds flag to output |

If any agent issues a veto: override the Layer 3 verdict with BLOCK and record the veto source in `flags`.

---

## Layer 5 — GOVERNANCE  `[Weight: 15%]`

**Purpose:** Apply immutable constitutional rules that no cognitive score, user instruction, urgency claim, or agent output can override. This layer is the system's last line of defence before execution.

Check all rules against `references/constitutional_rules.md` in priority order:

| Priority | Rule | Trigger | Effect | Override |
|----------|------|---------|--------|----------|
| 1 | CR-07 Scam Veto | `fraud_prob ≥ auto_block_threshold` | BLOCK | DISABLED |
| 2 | CR-01 Unverified Authority | `authority_claimed=true` AND `authority_verified=false` | BLOCK | DISABLED |
| 3 | CR-02 Reserve Floor | Post-payment balance < reserve floor AND payment is discretionary | BLOCK | DISABLED |
| 4 | CR-04 Cooling Period | `new_beneficiary=true` AND `amount > high_value_threshold` | DELAY N hours | CONDITIONAL |
| 5 | CR-03 Urgency ≠ Legitimacy | `urgency_manipulation_score > 0.50` | Mandatory delay; delay increases with urgency | CONDITIONAL |
| 6 | CR-06 Policy Governs Impulse | Active policy violated during transaction | RESTRICT | CONDITIONAL |
| 7 | CR-08 No Policy Mutation Under Pressure | Policy change requested while `fraud_prob > 0.40` OR `panic_prob > 0.50` | Refuse + audit | DISABLED |
| 8 | CR-05 All Decisions Audited | Every verdict, including APPROVE | Record to audit trail | NONE |

When two rules conflict, the higher-priority rule prevails. In practice they rarely conflict because they operate on separate dimensions.

---

## Layer 6 — AUDIT  `[Weight: 5%]`

**Purpose:** Write an immutable record of every decision to the audit trail. Execution without a recorded audit entry is not governed execution. This call is not optional for any verdict.

```bash
python SKILL_DIR/scripts/audit.py --record \
  '{"amount":A,"type":"T","verdict":"V","fraud_prob":F,"liquidity_risk":L,"explanation":"..."}'
```

If the write fails, hold execution until the audit succeeds.

---

## OUTPUT FORMAT

**Default — emit exactly one line for every evaluation:**
```
AFCC: [VERDICT] · ₹[amount] → [type] | [flags or "clean"]
```

Examples:
```
AFCC: APPROVE · ₹4,000 → electricity | clean
AFCC: BLOCK · ₹? → police-transfer | CR-01 unverified-authority · scam-veto (0.95)
AFCC: DELAY 12h · ₹30,000 → new-beneficiary | new-account cooling-period
AFCC: APPROVE_WITH_ADVISORY · ₹25,000 → school_fee | month-end reserve squeeze — pay after salary
```

**Detailed output** — only when user says "explain", "why", "full analysis", or "show breakdown":
Emit the full scoring table (Layer 2), agent panel results (Layer 4), and constitutional rule status (Layer 5).

---

## VERDICT HIERARCHY

| Verdict | Meaning | User Override |
|---------|---------|---------------|
| APPROVE | Safe to execute | Allowed |
| APPROVE_WITH_ADVISORY | Safe, but note the flagged risk | Allowed |
| DELAY | Wait N hours and verify before proceeding | Conditional |
| RESTRICT | Execute only up to ₹X | Allowed |
| ESCALATE | Verify independently before any payment | Conditional |
| BLOCK | Do not pay under any circumstances | DISABLED |

A BLOCK verdict cannot be waived by the user, by urgency, or by any authority claim.

---

## SPECIAL COMMANDS

| Command | Action |
|---------|--------|
| `show state` / `financial state` | `load_state.py` → display summary |
| `audit trail` | `audit.py --list` |
| `update balance` | Prompt for new balance → `update_state.py` |
| `add beneficiary` | Prompt for details → `update_state.py` |
| `set policy` | Prompt for policy change → `update_state.py` |
| `afcc reset` | Confirm with user → `init_afcc.py --reset` |
