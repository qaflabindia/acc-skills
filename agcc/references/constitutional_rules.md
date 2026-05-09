# AGCC Constitutional Rules

These rules are immutable. No urgency, authority, user override, or agent instruction
can bypass them. They are evaluated in priority order. The first triggered rule governs.

---

## CR-AG01 — Authorization Gate
**Priority: 1 (highest)**

**Rule:** Never execute an irreversible action without explicit human authorization.

**Trigger:** `reversibility = irreversible` AND `authorized = false`

**Effect:** HALT — execution is prohibited.

**Override:** DISABLED. Urgency cannot substitute for authorization. Authority claimed
by the requesting agent is not the same as explicit human authorization.

**Rationale:** Irreversible actions create permanent consequences. Autonomous execution
without authorization is a constitutional violation regardless of confidence score.

---

## CR-AG02 — Production Gate
**Priority: 2**

**Rule:** Never execute actions in production scope when execution confidence is below
the production safety threshold.

**Trigger:** `scope = production` AND `exec_confidence < 0.75`

**Effect:** ESCALATE — require explicit human authorization before proceeding.

**Override:** DISABLED. Confidence cannot be raised retroactively to bypass this gate.

**Rationale:** Production environments affect real users and real data. Uncertainty
below the threshold mandates human review regardless of urgency.

---

## CR-AG03 — Policy Lock Under Pressure
**Priority: 3**

**Rule:** Never mutate governance policy when urgency is high or critical.

**Trigger:** `action_type = policy_mutation` AND `urgency ∈ {high, critical}`

**Effect:** HALT — policy mutation under operational pressure is prohibited.

**Override:** DISABLED. Urgency is a risk multiplier, not a legitimacy signal.

**Rationale:** Policy mutations performed under pressure create constitutional
instability. Emergency-driven policy changes routinely produce governance drift
that persists long after the emergency passes.

---

## CR-AG04 — Cascade Veto
**Priority: 4**

**Rule:** Escalate before executing any action with extreme cascade potential.

**Trigger:** `cascade_risk > 0.85`

**Effect:** ESCALATE — require human review of cascade blast radius.

**Override:** CONDITIONAL. User may override with explicit acknowledgment of cascade risk.

**Rationale:** High cascade potential means one action can destabilize multiple
downstream systems. Human review of the cascade map is mandatory.

---

## CR-AG05 — Uncertainty Floor
**Priority: 5**

**Rule:** Actions with extreme outcome uncertainty require a mandatory deferral.

**Trigger:** `uncertainty > 0.80`

**Effect:** DEFER minimum 30 minutes — gather more information before proceeding.

**Override:** CONDITIONAL. User may override with explicit acknowledgment.

**Rationale:** Execution confidence below the uncertainty floor indicates the system
does not have sufficient information to predict outcomes. Acting anyway is
probabilistically reckless.

---

## CR-AG06 — Behavioral Anomaly Gate
**Priority: 6**

**Rule:** Aberrant behavioral patterns from a registered agent require escalation.

**Trigger:** `behavioral_anomaly > 0.85`

**Effect:** ESCALATE — agent behavior deviates significantly from registered baseline.

**Override:** CONDITIONAL. User may investigate and re-authorize.

**Rationale:** Extreme deviation from baseline may indicate agent compromise,
prompt injection, runaway loop, or state corruption. Human review before
continued execution is mandatory.

---

## CR-AG07 — Urgency ≠ Authorization
**Priority: 7**

**Rule:** Urgency cannot be used as a substitute for authorization on any action.

**Trigger:** `urgency = critical` used to justify bypassing authorization check

**Effect:** HALT — urgency-as-authorization is a categorical violation.

**Override:** DISABLED. This rule exists precisely to prevent urgency manipulation.

**Rationale:** Real emergencies sometimes require fast action, but they never
retroactively create authorization that did not exist. An agent claiming
critical urgency to bypass authorization is a governance violation.

---

## CR-AG08 — Audit Lock
**Priority: 8 (universal)**

**Rule:** Every governance decision must be recorded to the audit trail before
execution proceeds.

**Trigger:** Every evaluation, including EXECUTE verdicts.

**Effect:** Audit write is mandatory. Execution must wait for confirmed audit record.

**Override:** NONE. Execution without audit is not governed execution.

**Rationale:** Governance without traceability is governance theater. If an action
cannot be recorded, it should not be executed.

---

## Conflict Resolution

When two rules appear to conflict, the higher-priority rule (lower number) prevails.
In practice, rules operate on orthogonal dimensions and rarely conflict.

The most common apparent conflict:
- CR-AG02 (production gate) vs CR-AG04 (cascade veto)
- Resolution: CR-AG02 fires first if `scope=production`; cascade veto escalates regardless

---

## Rule Version History

| Version | Date | Change |
|---------|------|--------|
| 1.0.0 | 2026-05-09 | Initial constitutional rule set |
