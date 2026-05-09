#!/usr/bin/env python3
"""
AFCC evaluate.py — Core 5-layer payment evaluation engine.

Applies Control Layer logic (Layer 3) using cognitive scores from Claude's
Layers 1-2 reasoning. Produces a structured control_decision JSON.

Usage:
  python evaluate.py \\
    --amount 50000 \\
    --type transfer \\
    --urgency high \\
    --new-beneficiary true \\
    --fraud-prob 0.85 \\
    --liquidity-risk 0.40 \\
    --execution-confidence 0.10 \\
    --obligation-priority 0.05 \\
    --beneficiary-trust 0.08 \\
    --urgency-score 0.80 \\
    --panic-prob 0.60 \\
    --authority-claimed true \\
    --authority-verified false

Always exits 0. Always returns JSON.
"""
import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(SKILL_DIR, "state")

# ── Verdict constants ────────────────────────────────────────────────────────

APPROVE = "APPROVE"
ADVISORY = "APPROVE_WITH_ADVISORY"
DELAY = "DELAY"
RESTRICT = "RESTRICT"
ESCALATE = "ESCALATE"
BLOCK = "BLOCK"

# ── Policy loader ─────────────────────────────────────────────────────────────

def load_policies():
    path = os.path.join(STATE_DIR, "policies.json")
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


def load_state():
    path = os.path.join(STATE_DIR, "financial_state.json")
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


# ── Argument parsing ──────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="AFCC Control Layer evaluator")
    p.add_argument("--amount", type=float, default=0.0)
    p.add_argument("--type", dest="payment_type", default="unknown")
    p.add_argument("--urgency", default="none",
                   choices=["none", "low", "medium", "high", "extreme"])
    p.add_argument("--new-beneficiary", default="false")
    p.add_argument("--fraud-prob", type=float, default=0.0)
    p.add_argument("--liquidity-risk", type=float, default=0.0)
    p.add_argument("--execution-confidence", type=float, default=1.0)
    p.add_argument("--obligation-priority", type=float, default=0.0)
    p.add_argument("--beneficiary-trust", type=float, default=1.0)
    p.add_argument("--urgency-score", type=float, default=0.0)
    p.add_argument("--panic-prob", type=float, default=0.0)
    p.add_argument("--authority-claimed", default="false")
    p.add_argument("--authority-verified", default="false")
    p.add_argument("--budget-breach", type=float, default=0.0)
    p.add_argument("--format", dest="output_format", default="compact",
                   choices=["compact", "full"],
                   help="compact=one-liner (default), full=complete JSON")
    return p.parse_args()


def bool_arg(val):
    return str(val).lower() in ("true", "1", "yes")


# ── Risk computation ──────────────────────────────────────────────────────────

NON_NEGOTIABLE_TYPES = {
    "rent", "emi", "electricity", "utility", "insurance", "tax",
    "school_fee", "loan", "debt"
}

URGENCY_SCORES = {
    "none": 0.0, "low": 0.20, "medium": 0.40,
    "high": 0.70, "extreme": 0.95
}


def compute_composite_risk(args, policies):
    """Compute a single composite risk score 0-1 from all inputs."""
    fraud_weight = 1.4
    urgency_weight = 1.2

    scores = [
        args.fraud_prob * fraud_weight,
        args.urgency_score * urgency_weight,
        1.0 - max(args.execution_confidence, 0.0),
        args.liquidity_risk,
        (1.0 - min(args.beneficiary_trust, 1.0)) * 0.7,
        args.panic_prob * 0.8,
        args.budget_breach * 0.6,
    ]
    return min(max(scores), 1.0)


# ── Control rules ─────────────────────────────────────────────────────────────

def evaluate_control(args, policies, composite_risk):
    """
    Apply all control rules in priority order.
    Returns (verdict, delay_h, approved_amount, override_allowed, flags, rules).
    """
    flags = []
    rules_triggered = []
    delay_hours = None
    approved_amount = None
    override_allowed = True

    new_beneficiary = bool_arg(args.new_beneficiary)
    authority_claimed = bool_arg(args.authority_claimed)
    authority_verified = bool_arg(args.authority_verified)

    transfer_policy = policies.get("transfer_policy", {})
    fraud_policy = policies.get("fraud_response_policy", {})
    override_policy = policies.get("override_policy", {})
    reserve_policy = policies.get("reserve_policy", {})

    new_ben_threshold = transfer_policy.get("new_beneficiary_threshold", 10000)
    new_ben_delay = transfer_policy.get("new_beneficiary_delay_hours", 12)
    high_val_threshold = transfer_policy.get("high_value_threshold", 50000)
    high_val_delay = transfer_policy.get("high_value_delay_hours", 24)
    auto_block_thresh = fraud_policy.get("auto_block_fraud_probability", 0.80)
    escalate_thresh = fraud_policy.get("escalate_fraud_probability", 0.60)
    urgency_delay_thresh = fraud_policy.get("urgency_delay_threshold", 0.50)

    # ── HARD BLOCKS (constitutional — cannot be overridden) ────────────────

    # CR-01: Authority claimed and not verified
    if authority_claimed and not authority_verified:
        flags.append("unverified_authority_claim")
        rules_triggered.append("CR-01: No execution under unverified authority")
        return (BLOCK, None, None, False, flags, rules_triggered)

    # Hard scam block
    if args.fraud_prob >= auto_block_thresh:
        flags.append(f"fraud_probability_{args.fraud_prob:.2f}_exceeds_threshold_{auto_block_thresh}")
        rules_triggered.append("CR-FRAUD: Fraud probability exceeds auto-block threshold")
        return (BLOCK, None, None, False, flags, rules_triggered)

    # Emergency reserve breach (only if we can compute it)
    fs = load_state()
    balances = fs.get("balances", {})
    bank = balances.get("bank_balance", 0)
    reserve_floor = reserve_policy.get("emergency_reserve_minimum", 0)
    payment_type_lower = args.payment_type.lower()
    is_non_negotiable = payment_type_lower in NON_NEGOTIABLE_TYPES

    if reserve_floor > 0 and args.amount > 0 and not is_non_negotiable:
        post_payment = bank - args.amount
        if post_payment < reserve_floor:
            flags.append(
                f"reserve_floor_breach: post_payment_{post_payment:.0f} < floor_{reserve_floor:.0f}"
            )
            rules_triggered.append("CR-02: Emergency reserve floor cannot be breached by discretionary payment")
            return (BLOCK, None, None, False, flags, rules_triggered)

    # ── ESCALATION ─────────────────────────────────────────────────────────

    if args.fraud_prob >= escalate_thresh:
        flags.append(f"fraud_probability_{args.fraud_prob:.2f}_requires_escalation")
        rules_triggered.append("CR-FRAUD: Fraud probability requires escalation")
        approved_amount = None
        override_allowed = False
        return (ESCALATE, None, approved_amount, override_allowed, flags, rules_triggered)

    # Panic + high amount → escalate
    if args.panic_prob >= 0.70 and args.amount >= high_val_threshold:
        flags.append("panic_state_with_high_value_transfer")
        rules_triggered.append("BEHAVIORAL: Panic state detected with high-value transfer")
        override_allowed = composite_risk < 0.75
        return (ESCALATE, None, None, override_allowed, flags, rules_triggered)

    # ── DELAY ──────────────────────────────────────────────────────────────

    # New beneficiary above threshold
    if new_beneficiary and args.amount >= new_ben_threshold and not is_non_negotiable:
        flags.append(f"new_beneficiary_above_{new_ben_threshold}")
        rules_triggered.append(f"TRANSFER: New beneficiary + amount ≥ ₹{new_ben_threshold} → {new_ben_delay}h delay")
        delay_hours = new_ben_delay
        if args.amount >= high_val_threshold:
            delay_hours = max(delay_hours, high_val_delay)
            flags.append(f"high_value_transfer_above_{high_val_threshold}")
            rules_triggered.append(f"TRANSFER: High-value transfer → {high_val_delay}h delay")
        override_allowed = composite_risk < override_policy.get("medium_risk_max", 0.50)
        return (DELAY, delay_hours, None, override_allowed, flags, rules_triggered)

    # Urgency manipulation
    if args.urgency_score >= urgency_delay_thresh:
        flags.append(f"urgency_manipulation_score_{args.urgency_score:.2f}")
        rules_triggered.append("CR-03: Urgency detected — mandatory verification delay")
        delay_hours = max(new_ben_delay, 6)
        override_allowed = composite_risk < override_policy.get("medium_risk_max", 0.50)
        return (DELAY, delay_hours, None, override_allowed, flags, rules_triggered)

    # High value with low trust
    if args.amount >= high_val_threshold and args.beneficiary_trust < 0.50:
        flags.append("high_value_low_trust_beneficiary")
        rules_triggered.append(f"TRANSFER: High-value transfer to low-trust beneficiary → {high_val_delay}h delay")
        delay_hours = high_val_delay
        override_allowed = composite_risk < override_policy.get("high_risk_max", 0.75)
        return (DELAY, delay_hours, None, override_allowed, flags, rules_triggered)

    # ── RESTRICT ───────────────────────────────────────────────────────────

    # Budget breach + discretionary + sufficient balance for partial
    if (args.budget_breach >= 0.70
            and not is_non_negotiable
            and bank > 0
            and args.amount > 0):
        budget_limits = policies.get("budget_limits", {})
        category_limit = budget_limits.get(payment_type_lower, 0)
        if category_limit > 0:
            # Allow up to category limit - already spent (approximate)
            approved_amount = category_limit * 0.20  # 20% of limit as remaining
            if approved_amount < args.amount:
                flags.append(f"budget_breach_{args.budget_breach:.2f}_category_{payment_type_lower}")
                rules_triggered.append(f"BUDGET: Category limit breach → restrict to ₹{approved_amount:.0f}")
                override_allowed = True
                return (RESTRICT, None, approved_amount, override_allowed, flags, rules_triggered)

    # Liquidity pressure on discretionary
    if (args.liquidity_risk >= 0.65 and not is_non_negotiable
            and args.obligation_priority < 0.50):
        flags.append(f"liquidity_risk_{args.liquidity_risk:.2f}_on_discretionary_payment")
        rules_triggered.append("LIQUIDITY: High liquidity risk on discretionary payment")
        # Suggest a reduced amount (50% of requested)
        approved_amount = args.amount * 0.50
        override_allowed = composite_risk < override_policy.get("medium_risk_max", 0.50)
        return (RESTRICT, None, approved_amount, override_allowed, flags, rules_triggered)

    # ── ADVISORY APPROVE ───────────────────────────────────────────────────

    # Obligation with moderate liquidity pressure
    if (is_non_negotiable and args.liquidity_risk >= 0.50):
        flags.append("obligation_under_liquidity_pressure")
        rules_triggered.append("OBLIGATION: Mandatory payment approved with liquidity advisory")
        return (ADVISORY, None, None, True, flags, rules_triggered)

    # General advisory threshold
    if composite_risk >= 0.25:
        flags.append(f"composite_risk_{composite_risk:.2f}_above_advisory_threshold")
        rules_triggered.append("RISK: Composite risk above advisory threshold")
        override_allowed = True
        return (ADVISORY, None, None, override_allowed, flags, rules_triggered)

    # ── CLEAN APPROVE ──────────────────────────────────────────────────────

    return (APPROVE, None, None, True, [], ["All checks passed"])


# ── Override level ────────────────────────────────────────────────────────────

def override_level(verdict, composite_risk, override_allowed, policies):
    if not override_allowed:
        return "DISABLED"
    override_policy = policies.get("override_policy", {})
    low_max = override_policy.get("low_risk_max", 0.25)
    medium_max = override_policy.get("medium_risk_max", 0.50)
    high_max = override_policy.get("high_risk_max", 0.75)

    if verdict == BLOCK:
        return "DISABLED"
    if verdict == ESCALATE:
        return "CONDITIONAL"
    if composite_risk <= low_max:
        return "ALLOWED"
    if composite_risk <= medium_max:
        return "ALLOWED_WITH_REASON"
    if composite_risk <= high_max:
        return "CONDITIONAL"
    return "DISABLED"


# ── Escalation targets ────────────────────────────────────────────────────────

def compute_escalation_targets(args, verdict):
    targets = []
    if verdict in (ESCALATE, BLOCK):
        targets.append("user_manual_review")
    if args.fraud_prob >= 0.70:
        targets.append("fraud_response_channel")
    if bool_arg(args.authority_claimed):
        targets.append("institutional_callback_verification")
    if args.panic_prob >= 0.70:
        targets.append("trusted_family_contact")
    if args.amount >= 100000:
        targets.append("bank_fraud_helpline")
    return targets


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    args = parse_args()
    policies = load_policies()

    new_ben = bool_arg(args.new_beneficiary)
    urgency_numeric = URGENCY_SCORES.get(args.urgency, 0.0)

    # If urgency_score not explicitly provided, derive from urgency label
    if args.urgency_score == 0.0 and args.urgency != "none":
        args.urgency_score = urgency_numeric

    composite_risk = compute_composite_risk(args, policies)

    verdict, delay_h, approved_amt, override_ok, flags, rules = \
        evaluate_control(args, policies, composite_risk)

    ol = override_level(verdict, composite_risk, override_ok, policies)
    escalation_targets = compute_escalation_targets(args, verdict)

    txn_id = f"TXN-{uuid.uuid4().hex[:8].upper()}"

    if args.output_format == "compact":
        # ── Compact output: one machine-readable line for Claude to echo ──────
        # verdict_str includes delay/restrict detail where relevant
        verdict_str = verdict
        if verdict == DELAY and delay_h:
            verdict_str = f"DELAY {delay_h}h"
        elif verdict == RESTRICT and approved_amt:
            verdict_str = f"RESTRICT ₹{approved_amt:,.0f}"

        flag_str = " · ".join(flags) if flags else "clean"

        compact = {
            "txn": txn_id,
            "verdict": verdict_str,
            "override": ol,
            "flags": flags,
            "flag_str": flag_str,
            "composite_risk": round(composite_risk, 2),
            "fraud": round(args.fraud_prob, 2),
            "liquidity": round(args.liquidity_risk, 2),
            "rules": rules,
        }
        print(json.dumps(compact))
        return

    # ── Full output: complete JSON (used for detailed breakdown) ──────────────
    result = {
        "transaction_id": txn_id,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "input": {
            "amount": args.amount,
            "payment_type": args.payment_type,
            "urgency": args.urgency,
            "new_beneficiary": new_ben,
            "authority_claimed": bool_arg(args.authority_claimed),
            "authority_verified": bool_arg(args.authority_verified),
        },
        "cognitive_scores": {
            "fraud_probability": round(args.fraud_prob, 3),
            "liquidity_risk": round(args.liquidity_risk, 3),
            "execution_confidence": round(args.execution_confidence, 3),
            "obligation_priority": round(args.obligation_priority, 3),
            "beneficiary_trust": round(args.beneficiary_trust, 3),
            "urgency_manipulation_score": round(args.urgency_score, 3),
            "panic_probability": round(args.panic_prob, 3),
            "budget_breach_risk": round(args.budget_breach, 3),
        },
        "composite_risk": round(composite_risk, 3),
        "control_decision": {
            "verdict": verdict,
            "delay_hours": delay_h,
            "approved_amount": approved_amt,
            "override_status": ol,
            "risk_flags": flags,
            "policy_rules_triggered": rules,
        },
        "agent_panel": compute_agent_verdicts(args, verdict, new_ben),
        "escalation_targets": escalation_targets,
    }
    print(json.dumps(result, indent=2))


def compute_agent_verdicts(args, control_verdict, new_ben):
    """Simulate each agent's domain verdict for the collaboration layer."""
    agents = {}

    # Obligation Agent
    if args.obligation_priority >= 0.70:
        agents["obligation_agent"] = {"verdict": "CLEAR", "evidence": "Mandatory obligation — high priority"}
    elif args.obligation_priority >= 0.40:
        agents["obligation_agent"] = {"verdict": "CONCERN", "evidence": "Moderate obligation — deferrable"}
    else:
        agents["obligation_agent"] = {"verdict": "CONCERN", "evidence": "Not a mandatory obligation"}

    # Liquidity Agent (veto authority)
    if args.liquidity_risk >= 0.80:
        agents["liquidity_agent"] = {
            "verdict": "VETO",
            "evidence": f"Liquidity risk {args.liquidity_risk:.2f} — survivability threatened",
            "veto_authority": True
        }
    elif args.liquidity_risk >= 0.50:
        agents["liquidity_agent"] = {
            "verdict": "CONCERN",
            "evidence": f"Liquidity risk {args.liquidity_risk:.2f} — buffer squeezed",
            "veto_authority": True
        }
    else:
        agents["liquidity_agent"] = {"verdict": "CLEAR", "evidence": "Sufficient liquidity", "veto_authority": True}

    # Budget Agent
    if args.budget_breach >= 0.80:
        agents["budget_agent"] = {"verdict": "CONCERN", "evidence": f"Budget breach risk {args.budget_breach:.2f}"}
    else:
        agents["budget_agent"] = {"verdict": "CLEAR", "evidence": "Within category limits"}

    # Trust Graph Agent
    if args.beneficiary_trust <= 0.20:
        agents["trust_graph_agent"] = {
            "verdict": "CONCERN",
            "evidence": f"Beneficiary trust {args.beneficiary_trust:.2f} — new or unverified"
        }
    elif args.beneficiary_trust >= 0.70:
        agents["trust_graph_agent"] = {
            "verdict": "CLEAR",
            "evidence": f"Beneficiary trust {args.beneficiary_trust:.2f} — verified"
        }
    else:
        agents["trust_graph_agent"] = {
            "verdict": "CONCERN",
            "evidence": f"Beneficiary trust {args.beneficiary_trust:.2f} — partial history"
        }

    # Scam Detection Agent (veto authority)
    fraud_prob = args.fraud_prob
    if fraud_prob >= 0.80:
        agents["scam_detection_agent"] = {
            "verdict": "VETO",
            "evidence": f"Fraud probability {fraud_prob:.2f} — strong pattern match",
            "veto_authority": True
        }
    elif fraud_prob >= 0.50:
        agents["scam_detection_agent"] = {
            "verdict": "CONCERN",
            "evidence": f"Fraud probability {fraud_prob:.2f} — pattern indicators present",
            "veto_authority": True
        }
    else:
        agents["scam_detection_agent"] = {
            "verdict": "CLEAR",
            "evidence": f"Fraud probability {fraud_prob:.2f} — no strong pattern",
            "veto_authority": True
        }

    # Behavioral Integrity Agent
    if args.panic_prob >= 0.70:
        agents["behavioral_integrity_agent"] = {
            "verdict": "CONCERN",
            "evidence": f"Panic probability {args.panic_prob:.2f} — cognitive instability detected"
        }
    else:
        agents["behavioral_integrity_agent"] = {
            "verdict": "CLEAR",
            "evidence": f"Panic probability {args.panic_prob:.2f} — decision appears stable"
        }

    # Authority Validation Agent
    authority_claimed = bool_arg(args.authority_claimed)
    authority_verified = bool_arg(args.authority_verified)
    if authority_claimed and not authority_verified:
        agents["authority_validation_agent"] = {
            "verdict": "CONCERN",
            "evidence": "Authority claimed but not independently verified"
        }
    elif authority_claimed and authority_verified:
        agents["authority_validation_agent"] = {
            "verdict": "CLEAR",
            "evidence": "Authority claim verified through independent channel"
        }
    else:
        agents["authority_validation_agent"] = {
            "verdict": "CLEAR",
            "evidence": "No authority claim"
        }

    # Constitutional Policy Agent (veto authority)
    if control_verdict == BLOCK:
        agents["constitutional_policy_agent"] = {
            "verdict": "VETO",
            "evidence": "Constitutional rule violated — execution prohibited",
            "veto_authority": True
        }
    elif control_verdict in (DELAY, ESCALATE):
        agents["constitutional_policy_agent"] = {
            "verdict": "CONCERN",
            "evidence": "Policy constraints require delay/escalation before execution",
            "veto_authority": True
        }
    else:
        agents["constitutional_policy_agent"] = {
            "verdict": "CLEAR",
            "evidence": "No policy violations detected",
            "veto_authority": True
        }

    return agents


if __name__ == "__main__":
    main()
