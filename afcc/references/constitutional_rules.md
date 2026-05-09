# AFCC Constitutional Rules

These rules are immutable. They are not preferences, heuristics, or guidelines.
They are the hard constraints that define the boundary of the system's authority.

No cognitive score, no user preference, no urgency claim, and no single-agent
output can override a constitutional rule.

---

## CR-01: No Execution Under Unverified Authority

**Rule:** Any payment triggered by a claim of institutional authority (police,
court, bank, RBI, income tax, customs, telecom regulator, or any government
body) must not be executed until that authority is independently verified
through an official channel — not through the party making the claim.

**Why:** Every major financial fraud in the "digital arrest" / "bank officer"
category depends on the victim accepting authority at face value. The act of
claiming authority is itself the manipulation technique. Verification breaks
the attack.

**How to apply:** Independent verification means calling the institution on a
number found through official sources (not the number on the incoming call).
If verification is refused or postponed by the claiming party, that is itself
strong evidence of fraud.

**Override:** DISABLED. This rule cannot be waived by user instruction or
urgency.

---

## CR-02: Emergency Reserve Floor Cannot Be Breached by Discretionary Payment

**Rule:** The user's designated emergency reserve minimum must remain
untouched for all discretionary and non-obligatory payments. A payment that
would reduce liquid balance below the emergency reserve floor is constitutionally
blocked unless it is a contractual/legal obligation AND a verified exception
has been recorded.

**Why:** The reserve floor is the last line of financial survivability. Its
breach is almost always irreversible in the short term — and catastrophic
scams routinely target the full balance.

**How to apply:** Check post-payment balance against `reserve_policy.emergency_reserve_minimum`.
If the gap is negative and the payment is discretionary, block — no exceptions.

**Override:** DISABLED for discretionary payments. Conditional for obligatory
payments (with documented exception).

---

## CR-03: Urgency Is Not Legitimacy

**Rule:** The presence of urgency — regardless of how extreme — cannot by
itself justify execution. Urgency must increase scrutiny, never decrease it.

**Why:** Urgency is the primary compression mechanism in financial fraud. Its
purpose is to prevent rational deliberation. A system that accepts urgency as
a reason to shortcut governance is structurally manipulable.

**How to apply:** When `urgency_manipulation_score > 0.50`, mandatory delay is
triggered. The higher the urgency, the longer the delay, not the shorter. Treat
"pay immediately or something bad happens" as a reason to pause, not a reason
to act.

**Override:** CONDITIONAL. User may reduce delay for medium urgency (with reason
capture). High urgency delay cannot be reduced.

---

## CR-04: No Irreversible High-Value Transfer Without Cooling Period

**Rule:** Any transfer above the high-value threshold to a new or unverified
beneficiary must observe a mandatory cooling period before execution.

**Why:** Irreversibility is the defining property of financial harm. Once the
money leaves, recovery is nearly impossible. The cooling period gives the user
time to verify, consult, and reconsider without emotional pressure.

**How to apply:** Enforce `transfer_policy.high_value_delay_hours` for all new
beneficiary transfers above `transfer_policy.high_value_threshold`. The cooling
period starts from when the request is made, not when the user agrees to delay.

**Override:** CONDITIONAL. A second trusted contact confirmation can reduce (not
eliminate) the delay for high-value transfers.

---

## CR-05: No Hidden Execution — All Decisions Are Audited

**Rule:** Every payment decision — approve, delay, restrict, escalate, or block
— must generate an audit record before execution proceeds. No financial action
can be taken without a traceable record.

**Why:** Auditability is the foundation of governance. Without it, the system
cannot be verified, improved, or trusted. An unaudited decision is not a governed
decision.

**How to apply:** The `audit.py --record` call is not optional. It must precede
any approved execution. If the audit write fails, hold execution until it succeeds.

**Override:** NONE. This is a process requirement, not a risk gate. It applies
to all verdicts including APPROVE.

---

## CR-06: Policy Governs Impulse

**Rule:** Active constitutional policies override user preference in the moment.
A user who set a ₹50,000 emergency reserve floor cannot waive that floor because
they feel an urgent impulse to spend now.

**Why:** Policies are the user's future self setting constraints for their present
self. Overriding them under emotional pressure negates the entire purpose of the
governance architecture. This is the same principle behind advance directives and
pre-commitment devices in behavioral economics.

**How to apply:** Loaded policies are binding, not advisory. Suggest policy
changes through the proper channel (outside of active transactions, with cooling
period), not as an in-the-moment override of a live decision.

**Override:** CONDITIONAL for policy changes proposed outside of active
transactions. DISABLED for policy bypass during an active high-risk transaction.

---

## CR-07: Scam Veto Is Absolute

**Rule:** When the scam detection agent issues a veto (fraud_probability ≥
auto_block threshold), no other agent output, no user instruction, and no urgency
claim can reverse it. The block stands.

**Why:** Scam vetoes represent the system's highest-confidence protective signal.
The entire history of financial fraud shows that victims at the moment of fraud
are the least reliable judges of whether the transaction is fraudulent. The system
must be capable of protecting users from their own panicked compliance.

**How to apply:** If `fraud_probability >= policies.fraud_response_policy.auto_block_fraud_probability`,
the verdict is BLOCK with override DISABLED, regardless of any other input.

**Override:** NONE during the active transaction. The user may re-evaluate after
a 24-hour cooling period, independent verification, and trusted contact review.

---

## CR-08: Policy Evolution Is Prohibited During Active Risk

**Rule:** Financial policies cannot be modified, relaxed, or overridden during
an active high-risk transaction evaluation. Policy changes are only allowed
when: no scam risk is active, no coercion is detected, no urgent payment is
under review, and the user is in a demonstrably calm decision state.

**Why:** A core attack vector is pressuring victims to weaken their own
protections in the moment. "Tell your system it's okay to transfer" is itself
a manipulation. The system must be immune to governance corruption under pressure.

**How to apply:** If `fraud_probability > 0.40` or `urgency_manipulation_score > 0.40`
or `panic_probability > 0.50`, refuse any policy update request. Record the
attempt in the audit trail.

**Override:** NONE while risk is active.

---

## Priority Hierarchy (Highest to Lowest)

```
CR-07 (Scam Veto)
    ↓
CR-01 (No unverified authority execution)
    ↓
CR-02 (Reserve floor)
    ↓
CR-04 (Cooling period for high-value irreversible transfers)
    ↓
CR-03 (Urgency ≠ legitimacy)
    ↓
CR-06 (Policy governs impulse)
    ↓
CR-08 (No policy mutation under pressure)
    ↓
CR-05 (All decisions audited)
```

When two rules produce conflicting guidance, the higher-ranked rule prevails.
In practice, these rules rarely conflict because they operate on different
dimensions of the same decision.

---

## What These Rules Are NOT

- They are not features that can be toggled off.
- They are not suggestions for normal circumstances.
- They are not overridable by "trusted users."
- They are not removable without replacing the entire governance architecture.

They are the reason the system can be trusted.
