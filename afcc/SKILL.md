---
name: finance-command-centre
cache_control: ephemeral
description: >
  Agentic Finance Command Centre (AFCC) — 5-layer constitutional payment
  governor. Auto-triggers on any payment intent. Verdicts: APPROVE /
  APPROVE_WITH_ADVISORY / DELAY / RESTRICT / ESCALATE / BLOCK.
  Triggers: pay / transfer / send money / should I pay / is this a scam /
  parcel clearance / KYC block / book / invest / semester fee / rent / EMI
---

# AFCC — Runtime Spec (compact)

`SKILL_DIR` = directory containing this file.

---

## BOOT — run once per session

```bash
python SKILL_DIR/scripts/init_afcc.py
```
Emit **one line**: `AFCC: [bank balance] · [N] policies`
If status `fresh`: ask user for bank balance, reserve floor, monthly obligations before proceeding.

---

## TRIGGER — activate when message contains

pay · transfer · send · invest · deposit · book · clear · "shall I pay" ·
"should I transfer" · parcel · customs · KYC · police + payment · any ₹ amount

---

## PHASE 1 — INTAKE (Capability)

Extract (default unknown if not stated):

| Field | Extract |
|-------|---------|
| `amount` | numeric — **ask if missing** |
| `type` | rent/emi/electricity/utility/insurance/tax/school_fee/food/shopping/transfer/investment/other |
| `urgency` | none/low/medium/high/extreme |
| `new_beneficiary` | true/false |
| `authority_claimed` | true/false |
| `authority_verified` | false (always false unless user confirms independent callback) |
| `reason` | brief text |

Load state:
```bash
python SKILL_DIR/scripts/load_state.py
```

---

## PHASE 2 — SCORE (Cognition)

Score 0.00–1.00, higher = more risk:

| Score | Formula / rule |
|-------|----------------|
| `fraud_prob` | Pattern match vs `references/scam_patterns.md` |
| `liquidity_risk` | `(bank - amount - monthly_obligations - reserve_floor) / bank`; clamp 0-1; invert |
| `urgency_score` | none=0 · low=0.2 · medium=0.4 · high=0.7 · extreme=0.95; +0.35 if authority_claimed |
| `beneficiary_trust` | 0.95 institutional · 0.50 known-individual · 0.10 new/unknown |
| `obligation_priority` | 0.95 school_fee/rent/emi/tax · 0.70 utility · 0.05 discretionary |
| `panic_prob` | 0 calm · 0.5 confused · 0.9 distressed |
| `legitimacy` | 0.99 routine · 0.50 unusual · 0.05 implausible |

`execution_confidence = 1 − max(fraud×1.4, urgency×1.2, 1−legitimacy, liquidity, (1−trust)×0.7)` clamp 0-1

---

## PHASE 3 — CONTROL (run script)

```bash
python SKILL_DIR/scripts/evaluate.py \
  --amount A --type T --urgency U \
  --new-beneficiary B --fraud-prob F --liquidity-risk L \
  --execution-confidence E --obligation-priority O \
  --beneficiary-trust TR --urgency-score US \
  --panic-prob P --authority-claimed AC --authority-verified AV \
  --format compact
```

Script returns `compact_verdict` string + `flags` list.

---

## PHASE 4-5 — COLLABORATION + GOVERNANCE (inline, terse)

Only compute explicitly when verdict ≠ APPROVE. Check:
- Any agent VETO? (scam agent if fraud>0.8 · policy agent if CR violated)
- Any CR violated? (see `references/constitutional_rules.md`)

---

## PHASE 6 — AUDIT

```bash
python SKILL_DIR/scripts/audit.py --record '{"amount":A,"type":"T","verdict":"V","fraud_prob":F,"liquidity_risk":L,"explanation":"..."}'
```

---

## OUTPUT FORMAT

**Default (all cases) — emit exactly this, nothing more:**
```
AFCC: [VERDICT] · ₹[amount] → [type] | [flags or "clean"]
```
Examples:
```
AFCC: APPROVE · ₹4,000 → electricity | clean
AFCC: BLOCK · ₹? → police-transfer | CR-01 unverified-authority · scam-veto P-01 (0.95)
AFCC: DELAY 12h · ₹30,000 → new-beneficiary | new-account cooling-period
AFCC: APPROVE_WITH_ADVISORY · ₹25,000 → school_fee | month-end reserve squeeze — pay after salary
```

**Detailed output — only when user says "explain", "why", "full analysis", "show breakdown":**
Emit full cognitive scores table + agent panel + constitutional status.

---

## SPECIAL COMMANDS (no full evaluation needed)

| Command | Action |
|---------|--------|
| `show state` / `financial state` | `load_state.py` → format summary |
| `audit trail` | `audit.py --list` |
| `update balance` | prompt → `update_state.py` |
| `add beneficiary` | prompt → `update_state.py` |
| `set policy` | prompt → `update_state.py` |
| `afcc reset` | confirm → `init_afcc.py --reset` |

---

## CONSTITUTIONAL HARD RULES (never override)

1. Authority claimed + unverified → **BLOCK**, override DISABLED
2. fraud_prob ≥ 0.80 → **BLOCK**, override DISABLED
3. Discretionary payment breaches reserve floor → **BLOCK**
4. Urgency ↑ scrutiny ↑ — never urgency ↓ scrutiny
5. Every decision → audit trail (no silent governance)
