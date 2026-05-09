#!/usr/bin/env python3
"""
RCC load_state.py — Load and display current relational state.
Always exits 0. Always returns JSON.
"""
import json
import os
from datetime import datetime, timezone

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


def load_log_count():
    path = os.path.join(STATE_DIR, "interaction_log.jsonl")
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


def days_since(iso_str):
    if not iso_str:
        return None
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        return round((now - dt).total_seconds() / 86400, 1)
    except Exception:
        return None


def main():
    rg = load_file("relationship_graph.json") or {}
    policies = load_file("policies.json") or {}
    commitments = load_file("commitments.json") or {}
    energy = load_file("energy_budget.json") or {}
    behavior = load_file("behavior_history.json") or {}
    log_count = load_log_count()

    relationships = rg.get("relationships", {})
    rel_count = len(relationships)

    # Build per-relationship summaries
    rel_summaries = {}
    at_risk = []
    for name, rel in relationships.items():
        last_contact = rel.get("last_contact")
        days_ago = days_since(last_contact)
        trust = rel.get("trust_score", None)
        tension = rel.get("current_tension", 0.0)
        rel_type = rel.get("relationship_type", "other")

        rel_summaries[name] = {
            "type": rel_type,
            "last_contact_days_ago": days_ago,
            "trust_score": trust,
            "current_tension": tension,
            "notes": rel.get("notes", ""),
        }
        if (days_ago is not None and days_ago > 14) or tension > 0.50:
            at_risk.append(name)

    # Pending commitments
    all_commitments = commitments.get("commitments", [])
    pending = [c for c in all_commitments if c.get("status") == "pending"]
    overdue = [c for c in all_commitments if c.get("status") == "overdue"]

    # Energy budget
    weekly_limit = energy.get("weekly_limit_hours", 20)
    week_spent = energy.get("current_week_spent_hours", 0)
    energy_remaining = max(0, weekly_limit - week_spent)
    energy_pct = round(week_spent / weekly_limit, 2) if weekly_limit > 0 else 0

    # Behavior
    protect_eps = len(behavior.get("protect_episodes", []))
    override_attempts = len(behavior.get("override_attempts", []))
    boundary_violations = len(behavior.get("boundary_violations", []))

    output = {
        "state_loaded": bool(rg),
        "last_updated": rg.get("last_updated"),
        "relationship_summary": {
            "total_relationships": rel_count,
            "at_risk_count": len(at_risk),
            "at_risk": at_risk,
        },
        "relationships": rel_summaries,
        "commitments": {
            "total": len(all_commitments),
            "pending": len(pending),
            "overdue": len(overdue),
            "overdue_items": [c.get("description", "") for c in overdue],
        },
        "energy_budget": {
            "weekly_limit_hours": weekly_limit,
            "current_week_spent_hours": week_spent,
            "remaining_hours": energy_remaining,
            "utilization_pct": energy_pct,
        },
        "active_policies": {
            "frequency_expectations": policies.get("frequency_expectations", {}),
            "unresolved_conflict_limit_hours": policies.get("conflict_policy", {}).get("unresolved_conflict_limit_hours", 72),
            "reciprocity_alert_threshold": policies.get("reciprocity_policy", {}).get("imbalance_alert_threshold", 0.65),
            "emotional_load_alert_threshold": policies.get("boundary_policy", {}).get("emotional_load_alert_threshold", 0.75),
            "weekly_social_energy_limit_hours": policies.get("boundary_policy", {}).get("weekly_social_energy_limit_hours", 20),
        },
        "behavioral_summary": {
            "protect_episodes": protect_eps,
            "override_attempts": override_attempts,
            "boundary_violations": boundary_violations,
        },
        "interaction_log": {
            "total_evaluations": log_count,
        },
        "display_summary": (
            f"{rel_count} relationships · {len(at_risk)} at risk · "
            f"{len(pending)} pending commitments · "
            f"energy {week_spent:.1f}/{weekly_limit}h · {log_count} evaluations logged"
        )
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
