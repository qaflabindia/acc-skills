#!/usr/bin/env python3
"""
AFCC update_state.py — Update specific fields in AFCC state files.

Usage:
  python update_state.py --field balances.bank_balance --value 85000
  python update_state.py --field policies.reserve_policy.emergency_reserve_minimum --value 50000
  python update_state.py --field beneficiaries.hdfc_savings --value '{"name":"HDFC Savings","trust_score":0.95,"verified":true}'

Field path format: <file_key>.<nested.key.path>
File keys:
  balances.*          → financial_state.json / balances
  obligations.*       → financial_state.json / obligations
  inflows.*           → financial_state.json / inflows
  policies.*          → policies.json
  beneficiaries.*     → beneficiary_registry.json / beneficiaries
  behavior.*          → behavior_history.json

Always exits 0. Always returns JSON.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(SKILL_DIR, "state")

FILE_MAP = {
    "balances": ("financial_state.json", ["balances"]),
    "obligations": ("financial_state.json", ["obligations"]),
    "inflows": ("financial_state.json", ["inflows"]),
    "upcoming_30d": ("financial_state.json", ["upcoming_30d"]),
    "policies": ("policies.json", []),
    "beneficiaries": ("beneficiary_registry.json", ["beneficiaries"]),
    "behavior": ("behavior_history.json", []),
}


def load_json(filename):
    path = os.path.join(STATE_DIR, filename)
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


def save_json(filename, data):
    path = os.path.join(STATE_DIR, filename)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def set_nested(obj, keys, value):
    """Set obj[keys[0]][keys[1]]...[keys[-1]] = value. Creates dicts as needed."""
    for key in keys[:-1]:
        if key not in obj or not isinstance(obj[key], dict):
            obj[key] = {}
        obj = obj[key]
    obj[keys[-1]] = value


def parse_value(raw):
    """Try to parse as JSON; fall back to numeric then string."""
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        pass
    try:
        v = float(raw)
        return int(v) if v == int(v) else v
    except (ValueError, TypeError):
        pass
    return raw


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--field", required=True,
                   help="Dot-separated field path (e.g. balances.bank_balance)")
    p.add_argument("--value", required=True, help="New value (JSON or scalar)")
    args = p.parse_args()

    parts = args.field.split(".")
    top_key = parts[0]

    if top_key not in FILE_MAP:
        print(json.dumps({
            "status": "error",
            "message": f"Unknown top-level key '{top_key}'. Valid keys: {list(FILE_MAP.keys())}"
        }))
        return

    filename, base_path = FILE_MAP[top_key]
    data = load_json(filename)

    # Build the full key path inside the file
    remaining_keys = parts[1:]  # everything after the top key
    full_path = base_path + remaining_keys

    value = parse_value(args.value)
    set_nested(data, full_path, value)

    # Touch last_updated if financial_state or policies
    if filename in ("financial_state.json", "policies.json"):
        data["last_updated"] = datetime.now(timezone.utc).isoformat()

    save_json(filename, data)

    print(json.dumps({
        "status": "ok",
        "updated_field": args.field,
        "new_value": value,
        "file": filename
    }))


if __name__ == "__main__":
    main()
