#!/usr/bin/env python3
"""
AFCC load_state.py — Load and display current financial state.
Always exits 0. Always returns JSON.
"""
import json
import os
import sys

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(SKILL_DIR, "state")


def load_file(name):
    path = os.path.join(STATE_DIR, name)
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def load_audit_count():
    path = os.path.join(STATE_DIR, "audit_trail.jsonl")
    if not os.path.exists(path):
        return 0
    count = 0
    try:
        with open(path) as f:
            for line in f:
                if line.strip():
                    count += 1
    except Exception:
        pass
    return count


def fmt_inr(val):
    try:
        v = float(val)
        return f"₹{v:,.0f}"
    except Exception:
        return str(val)


def main():
    # Load all state components
    fs = load_file("financial_state.json") or {}
    policies = load_file("policies.json") or {}
    breg = load_file("beneficiary_registry.json") or {}
    behavior = load_file("behavior_history.json") or {}
    audit_count = load_audit_count()

    # Build computed summary fields
    balances = fs.get("balances", {})
    bank = balances.get("bank_balance", 0)
    savings = balances.get("savings_balance", 0)
    wallet = balances.get("wallet_balance", 0)
    reserve = balances.get("emergency_reserve_balance", 0)
    cc_limit = balances.get("credit_card_available_limit", 0)

    obligations = fs.get("obligations", {})
    total_monthly_obligations = sum(
        v for v in obligations.values() if isinstance(v, (int, float))
    )

    inflows = fs.get("inflows", {})
    monthly_inflow = (
        inflows.get("salary_amount", 0) +
        inflows.get("freelance_income", 0) +
        inflows.get("reimbursements", 0)
    )

    liquid_total = bank + wallet
    reserve_headroom = liquid_total - reserve if reserve > 0 else None
    obligation_coverage = (
        round(liquid_total / total_monthly_obligations, 2)
        if total_monthly_obligations > 0 else None
    )

    reserve_policy = policies.get("reserve_policy", {})
    policy_reserve_floor = reserve_policy.get("emergency_reserve_minimum", 0)

    transfer_policy = policies.get("transfer_policy", {})
    fraud_policy = policies.get("fraud_response_policy", {})
    budget_limits = policies.get("budget_limits", {})

    beneficiary_count = len(breg.get("beneficiaries", {}))
    verified_count = sum(
        1 for b in breg.get("beneficiaries", {}).values()
        if b.get("verified", False)
    )

    recent_overrides = len(behavior.get("override_attempts", []))
    recent_scam_attempts = len(behavior.get("scam_attempts", []))

    output = {
        "state_loaded": bool(fs),
        "last_updated": fs.get("last_updated"),

        "balances": {
            "bank_balance": bank,
            "savings_balance": savings,
            "wallet_balance": wallet,
            "emergency_reserve_balance": reserve,
            "credit_card_available_limit": cc_limit,
            "liquid_total": liquid_total,
        },

        "obligations": {
            **obligations,
            "total_monthly": total_monthly_obligations,
        },

        "inflows": {
            **inflows,
            "total_monthly_expected": monthly_inflow,
        },

        "financial_health": {
            "reserve_headroom": reserve_headroom,
            "obligation_coverage_ratio": obligation_coverage,
            "policy_reserve_floor": policy_reserve_floor,
            "below_policy_floor": (
                liquid_total < policy_reserve_floor
                if policy_reserve_floor > 0 else False
            ),
        },

        "active_policies": {
            "emergency_reserve_minimum": policy_reserve_floor,
            "new_beneficiary_delay_hours": transfer_policy.get("new_beneficiary_delay_hours", 12),
            "new_beneficiary_threshold": transfer_policy.get("new_beneficiary_threshold", 10000),
            "high_value_threshold": transfer_policy.get("high_value_threshold", 50000),
            "auto_block_fraud_probability": fraud_policy.get("auto_block_fraud_probability", 0.80),
            "budget_limits": budget_limits,
        },

        "beneficiary_registry": {
            "total_known": beneficiary_count,
            "verified": verified_count,
            "unverified": beneficiary_count - verified_count,
        },

        "behavioral_summary": {
            "recent_override_attempts": recent_overrides,
            "scam_attempts_recorded": recent_scam_attempts,
        },

        "audit_trail": {
            "total_decisions": audit_count,
        },

        "display_summary": (
            f"Bank {fmt_inr(bank)} · Reserve {fmt_inr(reserve)} · "
            f"Monthly obligations {fmt_inr(total_monthly_obligations)} · "
            f"{beneficiary_count} beneficiaries · {audit_count} decisions logged"
        )
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
