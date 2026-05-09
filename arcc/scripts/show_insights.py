#!/usr/bin/env python3
"""
RCC show_insights.py — Full relationship health dashboard.
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


def load_log():
    path = os.path.join(STATE_DIR, "interaction_log.jsonl")
    if not os.path.exists(path):
        return []
    records = []
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except FileNotFoundError:
        pass
    return records


def days_since(iso_str):
    if not iso_str:
        return None
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        return round((now - dt).total_seconds() / 86400, 1)
    except Exception:
        return None


def health_label(score):
    if score is None:
        return "unknown"
    if score <= 0.15:
        return "excellent"
    if score <= 0.30:
        return "healthy"
    if score <= 0.50:
        return "watch"
    if score <= 0.70:
        return "advisory"
    if score <= 0.85:
        return "intervene"
    return "protect"


def main():
    rg = load_file("relationship_graph.json") or {}
    policies = load_file("policies.json") or {}
    commitments_data = load_file("commitments.json") or {}
    energy = load_file("energy_budget.json") or {}
    behavior = load_file("behavior_history.json") or {}
    log_records = load_log()

    relationships = rg.get("relationships", {})
    all_commitments = commitments_data.get("commitments", [])
    pending_commitments = [c for c in all_commitments if c.get("status") == "pending"]
    overdue_commitments = [c for c in all_commitments if c.get("status") == "overdue"]

    # Per-relationship health snapshot
    rel_health = {}
    top_concerns = []
    for name, rel in relationships.items():
        last_contact = rel.get("last_contact")
        days_ago = days_since(last_contact)
        tension = rel.get("current_tension", 0.0)
        trust = rel.get("trust_score", 0.8)
        rel_type = rel.get("relationship_type", "other")

        freq_map = {"daily": 1, "weekly": 7, "monthly": 30}
        expected_freq = policies.get("frequency_expectations", {}).get(rel_type, "monthly")
        expected_days = freq_map.get(expected_freq, 30)
        drift = round(min((days_ago or 0) / max(expected_days, 1) * 0.30, 0.95), 2) if days_ago else 0

        # Simple composite for display
        composite = round(min(max(drift, tension * 0.8, (1 - trust) * 0.5), 1.0), 2)
        label = health_label(composite)

        rel_health[name] = {
            "type": rel_type,
            "last_contact_days_ago": days_ago,
            "current_tension": tension,
            "trust_score": trust,
            "drift_score": drift,
            "composite_health_risk": composite,
            "health_label": label,
            "pending_commitments": [
                c["description"] for c in pending_commitments if c.get("person") == name
            ],
        }
        if label in ("advisory", "intervene", "protect"):
            top_concerns.append({"person": name, "label": label, "composite": composite})

    top_concerns.sort(key=lambda x: x["composite"], reverse=True)

    # Verdict distribution from log
    verdict_dist = {}
    for r in log_records:
        v = r.get("verdict", "UNKNOWN")
        verdict_dist[v] = verdict_dist.get(v, 0) + 1

    # Energy summary
    weekly_limit = energy.get("weekly_limit_hours", 20)
    week_spent = energy.get("current_week_spent_hours", 0)
    energy_remaining = max(0, weekly_limit - week_spent)
    energy_pct = round(week_spent / weekly_limit * 100, 1) if weekly_limit > 0 else 0
    energy_status = "over_limit" if week_spent > weekly_limit else ("high" if week_spent > weekly_limit * 0.80 else "healthy")

    # Protect / intervene history
    protect_count = verdict_dist.get("PROTECT", 0)
    intervene_count = verdict_dist.get("INTERVENE", 0)

    # Overall system health
    if protect_count > 0:
        system_health = "protect_active"
    elif intervene_count > 0 or len(overdue_commitments) > 2:
        system_health = "needs_attention"
    elif len(top_concerns) > 0:
        system_health = "advisory"
    else:
        system_health = "stable"

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "system_health": system_health,

        "relationship_overview": rel_health,
        "top_concerns": top_concerns[:5],

        "commitments": {
            "total": len(all_commitments),
            "pending": len(pending_commitments),
            "overdue": len(overdue_commitments),
            "overdue_details": [
                {"person": c.get("person"), "description": c.get("description"), "due": c.get("due")}
                for c in overdue_commitments
            ],
        },

        "energy": {
            "weekly_limit_hours": weekly_limit,
            "week_spent_hours": round(week_spent, 1),
            "remaining_hours": round(energy_remaining, 1),
            "utilization_pct": energy_pct,
            "status": energy_status,
            "per_relationship": energy.get("per_relationship_hours", {}),
        },

        "evaluation_history": {
            "total": len(log_records),
            "verdict_distribution": verdict_dist,
            "protect_episodes": protect_count,
            "intervene_episodes": intervene_count,
        },

        "governance": {
            "protect_episodes_total": len(behavior.get("protect_episodes", [])),
            "override_attempts": len(behavior.get("override_attempts", [])),
            "boundary_violations": len(behavior.get("boundary_violations", [])),
        },

        "active_policies_summary": {
            "frequency_expectations": policies.get("frequency_expectations", {}),
            "conflict_limit_hours": policies.get("conflict_policy", {}).get("unresolved_conflict_limit_hours", 72),
            "reciprocity_alert_threshold": policies.get("reciprocity_policy", {}).get("imbalance_alert_threshold", 0.65),
            "emotional_load_alert": policies.get("boundary_policy", {}).get("emotional_load_alert_threshold", 0.75),
            "manipulation_auto_protect": policies.get("boundary_policy", {}).get("manipulation_auto_protect_threshold", 0.80),
        }
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
