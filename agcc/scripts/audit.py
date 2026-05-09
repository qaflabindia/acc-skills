#!/usr/bin/env python3
"""
AGCC audit.py — Immutable governance audit trail.

Usage:
  python audit.py --record '{"action_type":"deployment","agent_id":"deploy-agent","verdict":"ESCALATE",...}'
  python audit.py --list [--last N]
  python audit.py --query AGC-XXXXXXXX
  python audit.py --stats
  python audit.py --agent-history AGENT_ID

Always exits 0. Always returns JSON.
"""
import argparse
import json
import os
import uuid
from datetime import datetime, timezone
from collections import defaultdict

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(SKILL_DIR, "state")
AUDIT_PATH = os.path.join(STATE_DIR, "audit_trail.jsonl")


def ensure_state_dir():
    os.makedirs(STATE_DIR, exist_ok=True)
    if not os.path.exists(AUDIT_PATH):
        open(AUDIT_PATH, "w").close()


def append_record(record: dict) -> str:
    ensure_state_dir()
    if "decision_id" not in record:
        record["decision_id"] = f"AGC-{uuid.uuid4().hex[:8].upper()}"
    if "recorded_at" not in record:
        record["recorded_at"] = datetime.now(timezone.utc).isoformat()
    with open(AUDIT_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")
    return record["decision_id"]


def load_records(last_n=None):
    ensure_state_dir()
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
    except FileNotFoundError:
        pass
    if last_n is not None:
        records = records[-last_n:]
    return records


def query_record(decision_id):
    for rec in load_records():
        if rec.get("decision_id") == decision_id:
            return rec
    return None


def agent_history(agent_id, last_n=50):
    all_records = load_records()
    return [r for r in all_records if r.get("agent_id") == agent_id][-last_n:]


def compute_stats(records):
    if not records:
        return {"total": 0}

    verdicts = defaultdict(int)
    halt_count = 0
    escalate_count = 0
    execute_count = 0
    agents_seen = set()
    action_types = defaultdict(int)
    scope_dist = defaultdict(int)
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
        action_types[r.get("action_type", "unknown")] += 1
        scope_dist[r.get("scope", "unknown")] += 1

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
        "top_action_types": dict(sorted(action_types.items(), key=lambda x: -x[1])[:5]),
        "scope_distribution": dict(scope_dist),
        "constitutional_violations": dict(cr_violations),
        "first_decision": records[0].get("recorded_at") if records else None,
        "last_decision": records[-1].get("recorded_at") if records else None,
    }


def format_record_summary(rec):
    decision_id = rec.get("decision_id", "?")
    agent = rec.get("agent_id", "unknown")
    action = rec.get("action_type", "unknown")
    verdict = rec.get("verdict", "?")
    ts = rec.get("recorded_at", "")[:19].replace("T", " ")
    flags = rec.get("flags", [])
    flag_preview = " · ".join(flags[:2]) if flags else "clean"
    conf = rec.get("exec_confidence", "?")
    return {
        "decision_id": decision_id,
        "timestamp": ts,
        "agent_id": agent,
        "action_type": action,
        "verdict": verdict,
        "exec_confidence": conf,
        "flags_preview": flag_preview,
    }


def main():
    p = argparse.ArgumentParser()
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--record", help="JSON string of the decision to record")
    group.add_argument("--list", action="store_true", help="List audit trail")
    group.add_argument("--query", metavar="DECISION_ID", help="Query by decision ID")
    group.add_argument("--stats", action="store_true", help="Governance audit statistics")
    group.add_argument("--agent-history", dest="agent_history_id",
                       metavar="AGENT_ID", help="Show history for a specific agent")

    p.add_argument("--last", type=int, default=20,
                   help="Number of recent records to show (with --list)")

    args = p.parse_args()

    if args.record:
        try:
            record = json.loads(args.record)
        except json.JSONDecodeError as e:
            print(json.dumps({"status": "error", "message": f"Invalid JSON: {e}"}))
            return
        decision_id = append_record(record)
        print(json.dumps({"status": "recorded", "decision_id": decision_id}))

    elif args.list:
        records = load_records(last_n=args.last)
        summaries = [format_record_summary(r) for r in records]
        print(json.dumps({
            "status": "ok",
            "count": len(summaries),
            "records": summaries
        }, indent=2))

    elif args.query:
        rec = query_record(args.query)
        if rec:
            print(json.dumps({"status": "found", "record": rec}, indent=2))
        else:
            print(json.dumps({"status": "not_found", "decision_id": args.query}))

    elif args.stats:
        records = load_records()
        stats = compute_stats(records)
        print(json.dumps({"status": "ok", "stats": stats}, indent=2))

    elif args.agent_history_id:
        records = agent_history(args.agent_history_id)
        summaries = [format_record_summary(r) for r in records]
        print(json.dumps({
            "status": "ok",
            "agent_id": args.agent_history_id,
            "count": len(summaries),
            "records": summaries
        }, indent=2))


if __name__ == "__main__":
    main()
