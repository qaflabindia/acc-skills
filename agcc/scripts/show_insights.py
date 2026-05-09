#!/usr/bin/env python3
"""
AGCC show_insights.py — Governance maturity dashboard.

Reads all state files and the audit trail to produce a structured
governance health report with risk telemetry, agent behaviour summary,
constitutional violation history, and policy effectiveness metrics.

Usage:
  python show_insights.py
  python show_insights.py --format json

Always exits 0. Always returns structured output.
"""
import json
import os
import argparse
from datetime import datetime, timezone
from collections import defaultdict

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


def load_audit_records():
    records = []
    if not os.path.exists(AUDIT_PATH):
        return records
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
    return records


def compute_governance_maturity(stats, behavior, policies):
    """
    Score governance maturity on five dimensions (0-100 each).
    Returns maturity_score and dimension breakdown.
    """
    total = stats.get("total_decisions", 0)
    if total == 0:
        return 0, {}, "nascent"

    halt_rate = stats.get("halt_rate", 0)
    escalation_rate = stats.get("escalation_rate", 0)
    exec_rate = stats.get("execution_rate", 1.0)
    cr_violations = stats.get("constitutional_violations", {})
    cr_total = sum(cr_violations.values())

    override_attempts = len(behavior.get("override_attempts", []))
    loop_detections = len(behavior.get("loop_detections", []))
    halt_episodes = len(behavior.get("halt_episodes", []))

    # Dimension 1: Constitutional discipline (CR violations per 100 decisions)
    cr_rate = (cr_total / total) * 100
    constitutional = max(0, 100 - cr_rate * 15)

    # Dimension 2: Override hygiene (lower override rate = better)
    override_rate = (override_attempts / total) * 100
    override_hygiene = max(0, 100 - override_rate * 10)

    # Dimension 3: Escalation calibration (escalation should be moderate — neither 0 nor extreme)
    # Ideal escalation rate ~5-15%. Too low = under-vigilant; too high = over-blocking
    ideal_range = 0.05 <= escalation_rate <= 0.15
    escalation_calibration = 90 if ideal_range else max(0, 100 - abs(escalation_rate - 0.10) * 300)

    # Dimension 4: Behavioral stability (fewer loops and anomaly halts = better)
    stability = max(0, 100 - (loop_detections * 5) - (halt_episodes * 2))

    # Dimension 5: Audit completeness (all decisions audited = 100%)
    # We can only measure what we have — if total > 0, audit is 100% by definition
    audit_completeness = 100 if total > 0 else 0

    # Executive summary score (weighted)
    maturity_score = round(
        constitutional * 0.30 +
        override_hygiene * 0.20 +
        escalation_calibration * 0.20 +
        stability * 0.20 +
        audit_completeness * 0.10
    )

    label = (
        "exemplary" if maturity_score >= 85 else
        "mature" if maturity_score >= 70 else
        "developing" if maturity_score >= 50 else
        "nascent" if maturity_score >= 25 else
        "critical"
    )

    dimensions = {
        "constitutional_discipline": round(constitutional),
        "override_hygiene": round(override_hygiene),
        "escalation_calibration": round(escalation_calibration),
        "behavioral_stability": round(stability),
        "audit_completeness": round(audit_completeness),
    }

    return maturity_score, dimensions, label


def compute_agent_health(records, agent_registry):
    agents_data = {}
    agent_verdicts = defaultdict(lambda: defaultdict(int))
    agent_avg_conf = defaultdict(list)

    for r in records:
        aid = r.get("agent_id", "unknown")
        verdict = r.get("verdict", "UNKNOWN")
        conf = r.get("exec_confidence")
        agent_verdicts[aid][verdict] += 1
        if conf is not None:
            try:
                agent_avg_conf[aid].append(float(conf))
            except (TypeError, ValueError):
                pass

    registered_agents = agent_registry.get("agents", {})

    all_agents = set(list(agent_verdicts.keys()) + list(registered_agents.keys()))
    for aid in all_agents:
        verdicts = dict(agent_verdicts.get(aid, {}))
        total = sum(verdicts.values())
        confs = agent_avg_conf.get(aid, [])
        avg_conf = round(sum(confs) / len(confs), 3) if confs else None
        halt_count = verdicts.get("HALT", 0)
        escalate_count = verdicts.get("ESCALATE", 0)
        reg_info = registered_agents.get(aid, {})

        health = "healthy"
        if total > 0:
            halt_rate = halt_count / total
            esc_rate = escalate_count / total
            if halt_rate > 0.30:
                health = "critical"
            elif halt_rate > 0.10 or esc_rate > 0.40:
                health = "degraded"
            elif halt_rate > 0.05 or esc_rate > 0.20:
                health = "watchlist"

        agents_data[aid] = {
            "registered": aid in registered_agents,
            "operational_scope": reg_info.get("operational_scope", reg_info.get("scope", "unknown")),
            "total_decisions": total,
            "verdict_breakdown": verdicts,
            "avg_exec_confidence": avg_conf,
            "halt_count": halt_count,
            "escalation_count": escalate_count,
            "health_status": health,
        }

    return agents_data


def format_dashboard(maturity_score, maturity_label, dimensions, stats,
                     agent_health, policies, behavior, op_state):
    exec_policy = policies.get("execution_policy", {})
    rate_limits = policies.get("rate_limits", {})

    # Constitutional violations breakdown
    cr_violations = stats.get("constitutional_violations", {})
    top_violations = sorted(cr_violations.items(), key=lambda x: -x[1])[:5]

    # Verdict distribution
    verdict_breakdown = stats.get("verdict_breakdown", {})

    # Recent incidents
    recent_halts = behavior.get("halt_episodes", [])[-3:]
    recent_escalations = behavior.get("escalation_episodes", [])[-3:]

    dashboard = {
        "governance_maturity": {
            "score": maturity_score,
            "label": maturity_label,
            "dimensions": dimensions,
        },
        "operational_summary": {
            "governance_mode": op_state.get("governance_mode", "standard"),
            "environment": op_state.get("environment", "unknown"),
            "total_decisions": stats.get("total_decisions", 0),
            "halt_rate": stats.get("halt_rate", 0),
            "escalation_rate": stats.get("escalation_rate", 0),
            "execution_rate": stats.get("execution_rate", 0),
            "unique_agents": stats.get("unique_agents", 0),
            "session_actions": op_state.get("session_action_count", 0),
            "session_halts": op_state.get("session_halt_count", 0),
        },
        "constitutional_health": {
            "total_violations": sum(cr_violations.values()),
            "violation_breakdown": dict(top_violations),
            "violation_rate_pct": round(
                sum(cr_violations.values()) / max(stats.get("total_decisions", 1), 1) * 100, 2
            ),
        },
        "verdict_distribution": verdict_breakdown,
        "agent_health": agent_health,
        "policy_thresholds": {
            "production_confidence_min": exec_policy.get("production_confidence_threshold", 0.75),
            "max_cascade_risk": exec_policy.get("max_cascade_risk", 0.85),
            "max_uncertainty": exec_policy.get("max_uncertainty", 0.80),
            "behavioral_anomaly_threshold": exec_policy.get("behavioral_anomaly_threshold", 0.85),
            "require_auth_for_irreversible": exec_policy.get("require_auth_for_irreversible", True),
            "max_actions_per_minute": rate_limits.get("max_actions_per_minute", 10),
        },
        "recent_incidents": {
            "last_3_halts": [
                {"agent_id": h.get("agent_id"), "reason": h.get("reason"), "at": h.get("recorded_at", "")[:19]}
                for h in recent_halts
            ],
            "last_3_escalations": [
                {"agent_id": e.get("agent_id"), "decision_id": e.get("decision_id"), "at": e.get("recorded_at", "")[:19]}
                for e in recent_escalations
            ],
            "override_attempts_total": len(behavior.get("override_attempts", [])),
            "loop_detections_total": len(behavior.get("loop_detections", [])),
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    return dashboard


def compute_verdict_stats(records):
    if not records:
        return {"total_decisions": 0}
    verdicts = defaultdict(int)
    halt_count = 0
    escalate_count = 0
    execute_count = 0
    agents_seen = set()
    cr_violations = defaultdict(int)

    for r in records:
        v = r.get("verdict", "UNKNOWN")
        verdicts[v] += 1
        if v == "HALT":
            halt_count += 1
        elif v == "ESCALATE":
            escalate_count += 1
        elif v in ("EXECUTE", "EXECUTE_WITH_ADVISORY"):
            execute_count += 1
        agents_seen.add(r.get("agent_id", "unknown"))
        for flag in r.get("flags", []):
            if flag.startswith("CR-"):
                cr_violations[flag.split(":")[0]] += 1

    total = len(records)
    return {
        "total_decisions": total,
        "verdict_breakdown": dict(verdicts),
        "halt_rate": round(halt_count / total, 3),
        "escalation_rate": round(escalate_count / total, 3),
        "execution_rate": round(execute_count / total, 3),
        "unique_agents": len(agents_seen),
        "constitutional_violations": dict(cr_violations),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--format", default="text", choices=["text", "json"])
    args = p.parse_args()

    op_state = load_json("operational_state.json")
    agent_registry = load_json("agent_registry.json", {"agents": {}})
    policies = load_json("policies.json")
    behavior = load_json("behavior_history.json")
    records = load_audit_records()

    stats = compute_verdict_stats(records)
    maturity_score, dimensions, maturity_label = compute_governance_maturity(stats, behavior, policies)
    agent_health = compute_agent_health(records, agent_registry)
    dashboard = format_dashboard(
        maturity_score, maturity_label, dimensions, stats,
        agent_health, policies, behavior, op_state
    )

    if args.format == "json":
        print(json.dumps({"status": "ok", "dashboard": dashboard}, indent=2))
        return

    # Human-readable text dashboard
    gm = dashboard["governance_maturity"]
    ops = dashboard["operational_summary"]
    ch = dashboard["constitutional_health"]
    ri = dashboard["recent_incidents"]

    lines = [
        "═" * 60,
        f"  AGCC GOVERNANCE DASHBOARD",
        f"  Generated: {dashboard['generated_at'][:19]} UTC",
        "═" * 60,
        "",
        f"  MATURITY: {gm['label'].upper()} ({gm['score']}/100)",
        "",
        "  Dimensions:",
    ]
    for dim, score in gm["dimensions"].items():
        bar = "█" * (score // 10) + "░" * (10 - score // 10)
        lines.append(f"    {dim:<35} {bar} {score:3d}")

    lines += [
        "",
        f"  OPERATIONAL STATE",
        f"    Mode: {ops['governance_mode']}  |  Environment: {ops['environment']}",
        f"    Total decisions audited: {ops['total_decisions']}",
        f"    Halt rate:       {ops['halt_rate']*100:.1f}%",
        f"    Escalation rate: {ops['escalation_rate']*100:.1f}%",
        f"    Execution rate:  {ops['execution_rate']*100:.1f}%",
        f"    Active agents:   {ops['unique_agents']}",
        "",
        f"  CONSTITUTIONAL HEALTH",
        f"    Total violations: {ch['total_violations']}",
        f"    Violation rate:   {ch['violation_rate_pct']}%",
    ]
    if ch["violation_breakdown"]:
        lines.append("    Top violations:")
        for rule, count in list(ch["violation_breakdown"].items())[:3]:
            lines.append(f"      {rule}: {count}")

    lines += [
        "",
        f"  AGENT HEALTH",
    ]
    for aid, ah in list(agent_health.items())[:8]:
        status_icon = {"healthy": "✓", "watchlist": "⚠", "degraded": "!", "critical": "✗"}.get(ah["health_status"], "?")
        lines.append(
            f"    [{status_icon}] {aid:<30} {ah['total_decisions']} decisions  "
            f"halts:{ah['halt_count']}"
        )

    lines += [
        "",
        f"  RECENT INCIDENTS",
        f"    Override attempts: {ri['override_attempts_total']}",
        f"    Loop detections:   {ri['loop_detections_total']}",
    ]
    if ri["last_3_halts"]:
        lines.append("    Last halts:")
        for h in ri["last_3_halts"]:
            lines.append(f"      [{h['at']}] {h['agent_id']} — {h['reason']}")
    if ri["last_3_escalations"]:
        lines.append("    Last escalations:")
        for e in ri["last_3_escalations"]:
            lines.append(f"      [{e['at']}] {e['agent_id']} — {e['decision_id']}")

    lines.append("")
    lines.append("═" * 60)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
