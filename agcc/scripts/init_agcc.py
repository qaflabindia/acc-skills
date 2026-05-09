#!/usr/bin/env python3
"""
AGCC init_agcc.py — Bootstrap state directory with default structures.
Always exits 0. Always returns JSON.

Usage:
  python init_agcc.py
  python init_agcc.py --reset
"""
import json
import os
import sys
from datetime import datetime, timezone

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(SKILL_DIR, "state")

DEFAULT_OPERATIONAL_STATE = {
    "last_updated": None,
    "governance_mode": "standard",
    "environment": "unknown",
    "risk_tolerance": {
        "production": "low",
        "staging": "medium",
        "test": "high",
        "local": "high"
    },
    "active_agents": [],
    "execution_queue_size": 0,
    "last_halt_at": None,
    "last_escalation_at": None,
    "session_action_count": 0,
    "session_halt_count": 0
}

DEFAULT_AGENT_REGISTRY = {
    "version": "1.0",
    "last_updated": None,
    "agents": {}
}

DEFAULT_POLICIES = {
    "version": "1.0",
    "last_updated": None,
    "execution_policy": {
        "production_confidence_threshold": 0.75,
        "max_cascade_risk": 0.85,
        "max_uncertainty": 0.80,
        "behavioral_anomaly_threshold": 0.85,
        "require_auth_for_irreversible": True,
        "audit_all_decisions": True
    },
    "override_policy": {
        "low_risk_max": 0.25,
        "medium_risk_max": 0.50,
        "high_risk_max": 0.75,
        "critical_risk_threshold": 0.75
    },
    "escalation_policy": {
        "escalation_targets": ["human_operator"],
        "escalation_timeout_minutes": 30,
        "auto_defer_on_no_response": True
    },
    "rate_limits": {
        "max_actions_per_minute": 10,
        "max_production_actions_per_hour": 20,
        "loop_detection_window_seconds": 60,
        "loop_detection_threshold": 5
    },
    "scope_permissions": {}
}

DEFAULT_EXECUTION_QUEUE = {
    "version": "1.0",
    "last_updated": None,
    "pending": [],
    "deferred": [],
    "completed_last_100": []
}

DEFAULT_BEHAVIOR_HISTORY = {
    "version": "1.0",
    "last_updated": None,
    "agent_baselines": {},
    "halt_episodes": [],
    "escalation_episodes": [],
    "override_attempts": [],
    "loop_detections": []
}


def ensure_state_dir():
    os.makedirs(STATE_DIR, exist_ok=True)


def file_path(name):
    return os.path.join(STATE_DIR, name)


def repair_keys(data, default):
    repaired = False
    for key, val in default.items():
        if key not in data:
            data[key] = val
            repaired = True
        elif isinstance(val, dict) and isinstance(data.get(key), dict):
            if repair_keys(data[key], val):
                repaired = True
    return repaired


def load_or_create(filename, default, reset=False):
    path = file_path(filename)
    if reset or not os.path.exists(path):
        d = json.loads(json.dumps(default))
        d["last_updated"] = datetime.now(timezone.utc).isoformat()
        with open(path, "w") as f:
            json.dump(d, f, indent=2)
        return d, "fresh"
    try:
        with open(path) as f:
            data = json.load(f)
        if repair_keys(data, default):
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
            return data, "repaired"
        return data, "loaded"
    except (json.JSONDecodeError, OSError):
        d = json.loads(json.dumps(default))
        d["last_updated"] = datetime.now(timezone.utc).isoformat()
        with open(path, "w") as f:
            json.dump(d, f, indent=2)
        return d, "recovered"


def main():
    reset = "--reset" in sys.argv
    ensure_state_dir()

    statuses = {}

    op_state, s = load_or_create("operational_state.json", DEFAULT_OPERATIONAL_STATE, reset)
    statuses["operational_state"] = s

    agent_registry, s = load_or_create("agent_registry.json", DEFAULT_AGENT_REGISTRY, reset)
    statuses["agent_registry"] = s

    policies, s = load_or_create("policies.json", DEFAULT_POLICIES, reset)
    statuses["policies"] = s

    exec_queue, s = load_or_create("execution_queue.json", DEFAULT_EXECUTION_QUEUE, reset)
    statuses["execution_queue"] = s

    behavior, s = load_or_create("behavior_history.json", DEFAULT_BEHAVIOR_HISTORY, reset)
    statuses["behavior_history"] = s

    # Audit trail (JSONL — only create if missing)
    audit_path = file_path("audit_trail.jsonl")
    if reset or not os.path.exists(audit_path):
        open(audit_path, "w").close()
        statuses["audit_trail"] = "fresh"
    else:
        statuses["audit_trail"] = "loaded"

    if all(v == "fresh" for v in statuses.values()):
        overall = "fresh"
    elif any(v in ("recovered", "repaired") for v in statuses.values()):
        overall = "repaired"
    else:
        overall = "loaded"

    agent_count = len(agent_registry.get("agents", {}))
    policy_count = len([k for k, v in policies.items() if isinstance(v, dict)])
    governance_mode = op_state.get("governance_mode", "standard")

    print(json.dumps({
        "status": overall,
        "component_statuses": statuses,
        "agent_count": agent_count,
        "policy_count": policy_count,
        "governance_mode": governance_mode,
        "environment": op_state.get("environment", "unknown"),
        "state_dir": STATE_DIR
    }))


if __name__ == "__main__":
    main()
