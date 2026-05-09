#!/usr/bin/env python3
"""
AGCC load_state.py — Load and display the complete governance operational state.

Usage:
  python load_state.py
  python load_state.py --format full
  python load_state.py --format summary

Always exits 0. Always returns JSON.
"""
import json
import os
import argparse
from datetime import datetime, timezone

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(SKILL_DIR, "state")

AUDIT_PATH = os.path.join(STATE_DIR, "audit_trail.jsonl")


def load_json(filename, default=None):
    path = os.path.join(STATE_DIR, filename)
    if not os.path.exists(path):
        return default or {}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default or {}


def count_audit_records():
    if not os.path.exists(AUDIT_PATH):
        return 0
    try:
        with open(AUDIT_PATH) as f:
            return sum(1 for line in f if line.strip())
    except OSError:
        return 0


def last_audit_records(n=5):
    if not os.path.exists(AUDIT_PATH):
        return []
    records = []
    try:
        with open(AUDIT_PATH) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except OSError:
        pass
    return records[-n:]


def build_summary(op_state, agent_registry, policies, behavior, audit_count):
    exec_policy = policies.get("execution_policy", {})
    agents = agent_registry.get("agents", {})
    agent_count = len(agents)
    active_agents = op_state.get("active_agents", [])

    halt_episodes = len(behavior.get("halt_episodes", []))
    escalation_episodes = len(behavior.get("escalation_episodes", []))
    override_attempts = len(behavior.get("override_attempts", []))
    loop_detections = len(behavior.get("loop_detections", []))

    governance_mode = op_state.get("governance_mode", "standard")
    environment = op_state.get("environment", "unknown")
    prod_threshold = exec_policy.get("production_confidence_threshold", 0.75)
    max_cascade = exec_policy.get("max_cascade_risk", 0.85)
    max_uncertainty = exec_policy.get("max_uncertainty", 0.80)

    return {
        "governance_mode": governance_mode,
        "environment": environment,
        "registered_agents": agent_count,
        "active_agents": active_agents,
        "total_decisions_audited": audit_count,
        "session_actions": op_state.get("session_action_count", 0),
        "session_halts": op_state.get("session_halt_count", 0),
        "last_halt_at": op_state.get("last_halt_at"),
        "last_escalation_at": op_state.get("last_escalation_at"),
        "policy_thresholds": {
            "production_confidence_min": prod_threshold,
            "max_cascade_risk": max_cascade,
            "max_uncertainty": max_uncertainty,
        },
        "behavioral_incidents": {
            "halts": halt_episodes,
            "escalations": escalation_episodes,
            "override_attempts": override_attempts,
            "loop_detections": loop_detections,
        },
        "last_updated": op_state.get("last_updated"),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--format", default="summary", choices=["summary", "full"])
    args = p.parse_args()

    op_state = load_json("operational_state.json")
    agent_registry = load_json("agent_registry.json", {"agents": {}})
    policies = load_json("policies.json")
    behavior = load_json("behavior_history.json")
    audit_count = count_audit_records()

    summary = build_summary(op_state, agent_registry, policies, behavior, audit_count)

    if args.format == "summary":
        print(json.dumps({"status": "ok", "summary": summary}, indent=2))
        return

    # Full format includes agent registry and recent audit entries
    recent_decisions = [
        {
            "decision_id": r.get("decision_id"),
            "agent_id": r.get("agent_id"),
            "action_type": r.get("action_type"),
            "verdict": r.get("verdict"),
            "recorded_at": r.get("recorded_at", "")[:19],
        }
        for r in last_audit_records(10)
    ]

    print(json.dumps({
        "status": "ok",
        "summary": summary,
        "registered_agents": agent_registry.get("agents", {}),
        "policies": {
            "execution_policy": policies.get("execution_policy", {}),
            "escalation_policy": policies.get("escalation_policy", {}),
            "rate_limits": policies.get("rate_limits", {}),
        },
        "recent_decisions": recent_decisions,
    }, indent=2))


if __name__ == "__main__":
    main()
