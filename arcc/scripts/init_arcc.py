#!/usr/bin/env python3
"""
RCC init_rcc.py — Bootstrap state directory with default structures.
Always exits 0. Always returns JSON.
"""
import json
import os
import sys
from datetime import datetime, timezone

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(SKILL_DIR, "state")

DEFAULT_RELATIONSHIP_GRAPH = {
    "version": "1.0",
    "last_updated": None,
    "relationships": {}
}

DEFAULT_POLICIES = {
    "version": "1.0",
    "last_updated": None,
    "frequency_expectations": {
        "partner":  "daily",
        "family":   "weekly",
        "friend":   "monthly",
        "work":     "weekly",
        "other":    "monthly"
    },
    "conflict_policy": {
        "unresolved_conflict_limit_hours": 72,
        "repair_reminder_after_hours": 24
    },
    "reciprocity_policy": {
        "imbalance_alert_threshold": 0.65,
        "sustained_imbalance_weeks": 2
    },
    "boundary_policy": {
        "weekly_social_energy_limit_hours": 20,
        "emotional_load_alert_threshold": 0.75,
        "manipulation_auto_protect_threshold": 0.80
    },
    "commitment_policy": {
        "overdue_reminder_hours": 24,
        "critical_breach_threshold": 0.60
    },
    "no_contact_windows": {
        "work": {"after": "21:00", "before": "08:00"}
    }
}

DEFAULT_COMMITMENTS = {
    "version": "1.0",
    "last_updated": None,
    "commitments": []
}

DEFAULT_ENERGY_BUDGET = {
    "version": "1.0",
    "last_updated": None,
    "weekly_limit_hours": 20,
    "current_week_spent_hours": 0,
    "week_start": None,
    "per_relationship_hours": {}
}

DEFAULT_BEHAVIOR_HISTORY = {
    "version": "1.0",
    "protect_episodes": [],
    "override_attempts": [],
    "boundary_violations": []
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


def main():
    reset = "--reset" in sys.argv
    ensure_state_dir()
    statuses = {}
    now = datetime.now(timezone.utc).isoformat()

    # Relationship graph
    if reset or not os.path.exists(file_path("relationship_graph.json")):
        rg = {**DEFAULT_RELATIONSHIP_GRAPH, "last_updated": now}
        with open(file_path("relationship_graph.json"), "w") as f:
            json.dump(rg, f, indent=2)
        statuses["relationship_graph"] = "fresh"
        relationship_count = 0
    else:
        with open(file_path("relationship_graph.json")) as f:
            rg = json.load(f)
        relationship_count = len(rg.get("relationships", {}))
        was_repaired = repair_keys(rg, DEFAULT_RELATIONSHIP_GRAPH)
        if was_repaired:
            with open(file_path("relationship_graph.json"), "w") as f:
                json.dump(rg, f, indent=2)
            statuses["relationship_graph"] = "repaired"
        else:
            statuses["relationship_graph"] = "loaded"

    # Policies
    if reset or not os.path.exists(file_path("policies.json")):
        policies = {**DEFAULT_POLICIES, "last_updated": now}
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

    # Commitments
    if reset or not os.path.exists(file_path("commitments.json")):
        with open(file_path("commitments.json"), "w") as f:
            json.dump({**DEFAULT_COMMITMENTS, "last_updated": now}, f, indent=2)
        statuses["commitments"] = "fresh"
    else:
        statuses["commitments"] = "loaded"

    # Energy budget
    if reset or not os.path.exists(file_path("energy_budget.json")):
        with open(file_path("energy_budget.json"), "w") as f:
            json.dump({**DEFAULT_ENERGY_BUDGET, "last_updated": now}, f, indent=2)
        statuses["energy_budget"] = "fresh"
    else:
        statuses["energy_budget"] = "loaded"

    # Behavior history
    if reset or not os.path.exists(file_path("behavior_history.json")):
        with open(file_path("behavior_history.json"), "w") as f:
            json.dump(DEFAULT_BEHAVIOR_HISTORY, f, indent=2)
        statuses["behavior_history"] = "fresh"
    else:
        statuses["behavior_history"] = "loaded"

    # Interaction log (JSONL)
    log_path = file_path("interaction_log.jsonl")
    if reset or not os.path.exists(log_path):
        open(log_path, "w").close()
        statuses["interaction_log"] = "fresh"
    else:
        statuses["interaction_log"] = "loaded"

    # Overall status
    if all(v == "fresh" for v in statuses.values()):
        overall = "fresh"
    elif any(v == "repaired" for v in statuses.values()):
        overall = "repaired"
    else:
        overall = "loaded"

    policy_count = sum(
        1 for k, v in policies.items()
        if isinstance(v, dict) and k not in ("version",)
    )

    print(json.dumps({
        "status": overall,
        "component_statuses": statuses,
        "relationship_count": relationship_count,
        "policy_count": policy_count,
        "state_dir": STATE_DIR
    }))


if __name__ == "__main__":
    main()
