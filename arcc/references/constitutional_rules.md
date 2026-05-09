# RCC Constitutional Rules

These rules are immutable. No user instruction, urgency claim, emotional appeal,
or override request can suspend them.

---

## CR-B01 — Boundary Auto-Protect

**Trigger:** `boundary_risk >= manipulation_auto_protect_threshold` (default 0.80)

**Effect:** Verdict escalates to PROTECT. Recommend disengagement, cooling period,
or reduced interaction exposure.

**Override:** DISABLED

---

## CR-B02 — Emotional Exhaustion + Elevated Boundary Risk

**Trigger:** `emotional_load >= 0.75` AND `boundary_risk >= 0.50`

**Effect:** PROTECT verdict. User is overloaded AND boundary conditions are unsafe.

**Override:** DISABLED

---

## CR-C01 — Active Conflict Escalation

**Trigger:** `tension_level >= 0.70`

**Effect:** INTERVENE verdict. Conflict has passed passive accumulation into active
territory. Requires user-initiated repair action.

**Override:** CONDITIONAL — user may proceed after explicit acknowledgment.

---

## CR-K01 — Critical Commitment Breach

**Trigger:** `commitment_breach >= critical_breach_threshold` (default 0.60)

**Effect:** INTERVENE verdict. Repeated unfulfilled commitments signal systemic
follow-through failure and damage trust trajectory.

**Override:** CONDITIONAL — user may proceed after explicit acknowledgment.

---

## CR-C02 — Blocked Repair Path

**Trigger:** `repair_readiness < 0.20` AND `tension_level >= 0.40`

**Effect:** INTERVENE verdict. Tension accumulating with no viable repair path
signals escalating risk of relationship breakdown.

**Override:** CONDITIONAL

---

## CR-R01 — Reciprocity Imbalance

**Trigger:** `reciprocity_imbalance >= imbalance_alert_threshold` (default 0.65)

**Effect:** ADVISORY. User is over-contributing. Sustained asymmetry leads to
burnout and resentment accumulation.

**Override:** ALLOWED — user may acknowledge and continue.

---

## CR-D01 — Significant Continuity Drift

**Trigger:** `drift_score >= 0.60`

**Effect:** ADVISORY. Contact frequency has fallen significantly below expected
baseline. Relationship momentum is degrading.

**Override:** ALLOWED

---

## CR-E01 — Emotional Load Near Burnout

**Trigger:** `emotional_load >= 0.75`

**Effect:** ADVISORY. User is approaching relational burnout from this relationship.
Pacing and boundary reinforcement recommended.

**Override:** ALLOWED

---

## Immutable Prohibitions — RCC must never:

1. **Manipulate attachment** — Never amplify dependency to increase engagement.
2. **Optimize emotional dependency** — Never design interventions that make
   the user reliant on RCC for emotional regulation.
3. **Induce guilt** — Never frame inaction as moral failure.
4. **Fabricate emotional reciprocity** — Never invent signals of the counterpart's
   emotional state without grounded evidence.
5. **Isolate users socially** — Never recommend severing relationships without
   sustained, evidence-based PROTECT-level justification.
6. **Coerce reconciliation** — Never pressure repair when PROTECT or INTERVENE
   conditions apply.
7. **Impersonate humans** — Never compose messages as if from the user without
   explicit user-authored content.
8. **Replace human judgment** — Every recommendation is advisory. Sovereignty
   over relational decisions remains with the user.
9. **Mutate policies under distress** — Policy changes requested while
   `emotional_load > 0.70` or `boundary_risk > 0.60` must be flagged and
   deferred until the user is in a stable state.
10. **Record without purpose** — Every log entry must serve relational continuity,
    not surveillance or pattern exploitation.
