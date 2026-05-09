#!/usr/bin/env python3
"""
AFCC init_afcc.py — Bootstrap state directory with default structures.
Always exits 0. Always returns JSON.
"""
import json
import os
import sys
from datetime import datetime, timezone

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(SKILL_DIR, "state")

DEFAULT_FINANCIAL_STATE = {
    "last_updated": None,
    "balances": {
        "bank_balance": 0,
        "wallet_balance": 0,
        "savings_balance": 0,
        "emergency_reserve_balance": 0,
        "credit_card_available_limit": 0
    },
    "obligations": {
        "rent": 0,
        "emi": 0,
        "insurance": 0,
        "utilities": 0,
        "school_fees": 0,
        "subscriptions": 0,
        "credit_card_due": 0,
        "other": 0
    },
    "inflows": {
        "salary_expected_date": None,
        "salary_amount": 0,
        "freelance_income": 0,
        "reimbursements": 0
    },
    "upcoming_30d": []
}

DEFAULT_POLICIES = {
    "version": "1.0",
    "last_updated": None,
    "reserve_policy": {
        "emergency_reserve_minimum": 0,
        "description": "Minimum balance that must always remain untouched"
    },
    "transfer_policy": {
        "new_beneficiary_delay_hours": 12,
        "new_beneficiary_threshold": 10000,
        "high_value_threshold": 50000,
        "high_value_delay_hours": 24
    },
    "fraud_response_policy": {
        "auto_block_fraud_probability": 0.80,
        "escalate_fraud_probability": 0.60,
        "urgency_delay_threshold": 0.50
    },
    "budget_limits": {
        "food": 0,
        "travel": 0,
        "entertainment": 0,
        "shopping": 0,
        "subscriptions": 0,
        "other_discretionary": 0
    },
    "override_policy": {
        "low_risk_max": 0.25,
        "medium_risk_max": 0.50,
        "high_risk_max": 0.75,
        "critical_risk_threshold": 0.75
    }
}

DEFAULT_BENEFICIARY_REGISTRY = {
    "version": "1.0",
    "last_updated": None,
    "beneficiaries": {}
}

DEFAULT_BEHAVIOR_HISTORY = {
    "version": "1.0",
    "override_attempts": [],
    "panic_episodes": [],
    "scam_attempts": []
}


def ensure_state_dir():
    os.makedirs(STATE_DIR, exist_ok=True)


def file_path(name):
    return os.path.join(STATE_DIR, name)


def load_or_default(filename, default):
    path = file_path(filename)
    if os.path.exists(path):
        try:
            with open(path) as f:
                data = json.load(f)
            return data, "loaded"
        except json.JSONDecodeError:
            pass
    with open(path, "w") as f:
        json.dump(default, f, indent=2)
    return default, "fresh"


def repair_keys(data, default, path_prefix=""):
    """Fill missing keys from default. Returns (repaired_data, was_repaired)."""
    repaired = False
    for key, val in default.items():
        if key not in data:
            data[key] = val
            repaired = True
        elif isinstance(val, dict) and isinstance(data.get(key), dict):
            sub_repaired = repair_keys(data[key], val, f"{path_prefix}.{key}")
            if sub_repaired:
                repaired = True
    return repaired


def main():
    reset = "--reset" in sys.argv
    ensure_state_dir()

    statuses = {}

    # Financial state
    if reset or not os.path.exists(file_path("financial_state.json")):
        fs = DEFAULT_FINANCIAL_STATE.copy()
        fs["last_updated"] = datetime.now(timezone.utc).isoformat()
        with open(file_path("financial_state.json"), "w") as f:
            json.dump(fs, f, indent=2)
        statuses["financial_state"] = "fresh"
    else:
        with open(file_path("financial_state.json")) as f:
            fs = json.load(f)
        was_repaired = repair_keys(fs, DEFAULT_FINANCIAL_STATE)
        if was_repaired:
            with open(file_path("financial_state.json"), "w") as f:
                json.dump(fs, f, indent=2)
            statuses["financial_state"] = "repaired"
        else:
            statuses["financial_state"] = "loaded"

    # Policies
    if reset or not os.path.exists(file_path("policies.json")):
        policies = DEFAULT_POLICIES.copy()
        policies["last_updated"] = datetime.now(timezone.utc).isoformat()
        with open(file_path("policies.json"), "w") as f:
            json.dump(policies, f, indent=2)
        statuses["policies"] = "fresh"
    else:
        with open(file_path("policies.json")) as f:
            policies = json.load(f)
        was_repaired = repair_keys(policies, DEFAULT_POLICIES)
        if was_repaired:
            with open(file_path("policies.json"), "w") as f:
                json.dump(policies, f, indent=2)
            statuses["policies"] = "repaired"
        else:
            statuses["policies"] = "loaded"

    # Beneficiary registry
    if reset or not os.path.exists(file_path("beneficiary_registry.json")):
        with open(file_path("beneficiary_registry.json"), "w") as f:
            json.dump(DEFAULT_BENEFICIARY_REGISTRY, f, indent=2)
        statuses["beneficiary_registry"] = "fresh"
        beneficiary_count = 0
    else:
        with open(file_path("beneficiary_registry.json")) as f:
            breg = json.load(f)
        beneficiary_count = len(breg.get("beneficiaries", {}))
        statuses["beneficiary_registry"] = "loaded"

    # Behavior history
    if reset or not os.path.exists(file_path("behavior_history.json")):
        with open(file_path("behavior_history.json"), "w") as f:
            json.dump(DEFAULT_BEHAVIOR_HISTORY, f, indent=2)
        statuses["behavior_history"] = "fresh"
    else:
        statuses["behavior_history"] = "loaded"

    # Audit trail (JSONL — only create if missing)
    audit_path = file_path("audit_trail.jsonl")
    if reset or not os.path.exists(audit_path):
        open(audit_path, "w").close()
        statuses["audit_trail"] = "fresh"
    else:
        statuses["audit_trail"] = "loaded"

    # Determine overall status
    if all(v == "fresh" for v in statuses.values()):
        overall = "fresh"
    elif any(v == "repaired" for v in statuses.values()):
        overall = "repaired"
    else:
        overall = "loaded"

    # Build balance summary for display
    balances = fs.get("balances", {})
    bank = balances.get("bank_balance", 0)
    reserve = balances.get("emergency_reserve_balance", 0)
    if bank == 0 and reserve == 0:
        balance_summary = "no balances set"
    else:
        balance_summary = f"bank ₹{bank:,} · reserve ₹{reserve:,}"

    policy_count = len([k for k, v in policies.items()
                        if isinstance(v, dict) and k not in ("version",)])

    print(json.dumps({
        "status": overall,
        "component_statuses": statuses,
        "financial_state_summary": balance_summary,
        "policy_count": policy_count,
        "beneficiary_count": beneficiary_count,
        "state_dir": STATE_DIR
    }))


if __name__ == "__main__":
    main()
