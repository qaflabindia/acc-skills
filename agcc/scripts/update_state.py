#!/usr/bin/env python3
"""
AGCC update_state.py — Update specific fields in AGCC state files.

Usage:
  python update_state.py --field governance_mode --value strict
  python update_state.py --field environment --value production
  python update_state.py --field policies.execution_policy.production_confidence_threshold --value 0.85
  python update_state.py --register-agent '{"id":"doer-agent","scope":"local","registered_at":"2026-05-10"}'
  python update_state.py --set-policy execution_policy.production_confidence_threshold 0.85
  python update_state.py --record-halt '{"agent_id":"deploy-agent","decision_id":"AGC-XXXX","reason":"CR-AG01"}'
  python update_state.py --record-escalation '{"agent_id":"deploy-agent","decision_id":"AGC-XXXX"}'
  python update_state.py --record-override '{"agent_id":"api-agent","decision_id":"AGC-XXXX","outcome":"user_approved"}'
  python update_state.py --increment-session-actions
  python update_state.py --increment-session-halts

Field path format: <file_key>.<nested.key.path>
File keys:
  operational_state (top-level or nested)
  policies.<nested>
  agents.<agent_id>

Always exits 0. Always returns JSON.
"""
import argparse
import json
import os
from datetime import datetime, timezone

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(SKILL_DIR, "state")

FILE_MAP = {
    "governance_mode": ("operational_state.json", ["governance_mode"]),
    "environment": ("operational_state.json", ["environment"]),
    "risk_tolerance": ("operational_state.json", ["risk_tolerance"]),
    "active_agents": ("operational_state.json", ["active_agents"]),
    "policies": ("policies.json", []),
    "agents": ("agent_registry.json", ["agents"]),
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
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def set_nested(obj, keys, value):
    for key in keys[:-1]:
        if key not in obj or not isinstance(obj[key], dict):
            obj[key] = {}
        obj = obj[key]
    obj[keys[-1]] = value


def get_nested(obj, keys, default=None):
    for key in keys:
        if not isinstance(obj, dict) or key not in obj:
            return default
        obj = obj[key]
    return obj


def parse_value(raw):
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


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def register_agent(agent_json):
    try:
        agent = json.loads(agent_json)
    except json.JSONDecodeError as e:
        return {"status": "error", "message": f"Invalid JSON: {e}"}

    agent_id = agent.get("id") or agent.get("agent_id")
    if not agent_id:
        return {"status": "error", "message": "Agent must have 'id' or 'agent_id' field"}

    registry = load_json("agent_registry.json")
    agents = registry.setdefault("agents", {})

    agent.setdefault("registered_at", now_iso())
    agent.setdefault("operational_scope", agent.get("scope", "local"))
    agent.setdefault("baseline_established", False)
    agent.setdefault("action_count", 0)
    agent.setdefault("halt_count", 0)

    agents[agent_id] = agent
    registry["last_updated"] = now_iso()
    save_json("agent_registry.json", registry)
    return {"status": "ok", "registered_agent": agent_id}


def set_policy(path_str, value_str):
    parts = path_str.split(".")
    policies = load_json("policies.json")
    value = parse_value(value_str)
    set_nested(policies, parts, value)
    policies["last_updated"] = now_iso()
    save_json("policies.json", policies)
    return {"status": "ok", "updated_policy": path_str, "new_value": value}


def record_halt(halt_json):
    try:
        entry = json.loads(halt_json)
    except json.JSONDecodeError as e:
        return {"status": "error", "message": f"Invalid JSON: {e}"}

    entry.setdefault("recorded_at", now_iso())

    behavior = load_json("behavior_history.json")
    behavior.setdefault("halt_episodes", []).append(entry)
    behavior["last_updated"] = now_iso()
    save_json("behavior_history.json", behavior)

    op = load_json("operational_state.json")
    op["last_halt_at"] = now_iso()
    op["session_halt_count"] = op.get("session_halt_count", 0) + 1
    op["last_updated"] = now_iso()
    save_json("operational_state.json", op)

    # Also increment agent halt count
    agent_id = entry.get("agent_id")
    if agent_id:
        registry = load_json("agent_registry.json")
        agent = registry.get("agents", {}).get(agent_id)
        if agent:
            agent["halt_count"] = agent.get("halt_count", 0) + 1
            registry["last_updated"] = now_iso()
            save_json("agent_registry.json", registry)

    return {"status": "ok", "halt_recorded": entry.get("decision_id", "?")}


def record_escalation(esc_json):
    try:
        entry = json.loads(esc_json)
    except json.JSONDecodeError as e:
        return {"status": "error", "message": f"Invalid JSON: {e}"}

    entry.setdefault("recorded_at", now_iso())
    behavior = load_json("behavior_history.json")
    behavior.setdefault("escalation_episodes", []).append(entry)
    behavior["last_updated"] = now_iso()
    save_json("behavior_history.json", behavior)

    op = load_json("operational_state.json")
    op["last_escalation_at"] = now_iso()
    op["last_updated"] = now_iso()
    save_json("operational_state.json", op)

    return {"status": "ok", "escalation_recorded": entry.get("decision_id", "?")}


def record_override(override_json):
    try:
        entry = json.loads(override_json)
    except json.JSONDecodeError as e:
        return {"status": "error", "message": f"Invalid JSON: {e}"}

    entry.setdefault("recorded_at", now_iso())
    behavior = load_json("behavior_history.json")
    behavior.setdefault("override_attempts", []).append(entry)
    behavior["last_updated"] = now_iso()
    save_json("behavior_history.json", behavior)
    return {"status": "ok", "override_recorded": entry.get("decision_id", "?")}


def increment_session_actions():
    op = load_json("operational_state.json")
    op["session_action_count"] = op.get("session_action_count", 0) + 1
    op["last_updated"] = now_iso()
    save_json("operational_state.json", op)
    return {"status": "ok", "session_action_count": op["session_action_count"]}


def increment_session_halts():
    op = load_json("operational_state.json")
    op["session_halt_count"] = op.get("session_halt_count", 0) + 1
    op["last_updated"] = now_iso()
    save_json("operational_state.json", op)
    return {"status": "ok", "session_halt_count": op["session_halt_count"]}


def update_field(field_path, value_str):
    parts = field_path.split(".")
    top_key = parts[0]

    if top_key not in FILE_MAP:
        # Try operational_state as fallback for single-key fields
        op = load_json("operational_state.json")
        value = parse_value(value_str)
        set_nested(op, parts, value)
        op["last_updated"] = now_iso()
        save_json("operational_state.json", op)
        return {"status": "ok", "updated_field": field_path, "new_value": value, "file": "operational_state.json"}

    filename, base_path = FILE_MAP[top_key]
    data = load_json(filename)
    remaining = parts[1:]
    full_path = base_path + remaining
    value = parse_value(value_str)
    set_nested(data, full_path, value)
    if filename in ("operational_state.json", "policies.json", "agent_registry.json"):
        data["last_updated"] = now_iso()
    save_json(filename, data)
    return {"status": "ok", "updated_field": field_path, "new_value": value, "file": filename}


def main():
    p = argparse.ArgumentParser()
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--field", help="Dot-separated field path to update")
    group.add_argument("--register-agent", dest="register_agent",
                       metavar="JSON", help="Register a new agent (JSON)")
    group.add_argument("--set-policy", dest="set_policy", nargs=2,
                       metavar=("PATH", "VALUE"), help="Set a policy value")
    group.add_argument("--record-halt", dest="record_halt",
                       metavar="JSON", help="Record a halt episode")
    group.add_argument("--record-escalation", dest="record_escalation",
                       metavar="JSON", help="Record an escalation episode")
    group.add_argument("--record-override", dest="record_override",
                       metavar="JSON", help="Record an override attempt")
    group.add_argument("--increment-session-actions", dest="inc_actions",
                       action="store_true")
    group.add_argument("--increment-session-halts", dest="inc_halts",
                       action="store_true")

    p.add_argument("--value", help="New value (used with --field)")
    args = p.parse_args()

    if args.field:
        if not args.value:
            print(json.dumps({"status": "error", "message": "--value required with --field"}))
            return
        print(json.dumps(update_field(args.field, args.value)))
    elif args.register_agent:
        print(json.dumps(register_agent(args.register_agent)))
    elif args.set_policy:
        print(json.dumps(set_policy(args.set_policy[0], args.set_policy[1])))
    elif args.record_halt:
        print(json.dumps(record_halt(args.record_halt)))
    elif args.record_escalation:
        print(json.dumps(record_escalation(args.record_escalation)))
    elif args.record_override:
        print(json.dumps(record_override(args.record_override)))
    elif args.inc_actions:
        print(json.dumps(increment_session_actions()))
    elif args.inc_halts:
        print(json.dumps(increment_session_halts()))


if __name__ == "__main__":
    main()
