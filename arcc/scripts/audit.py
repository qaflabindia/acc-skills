#!/usr/bin/env python3
"""
RCC audit.py — Immutable interaction log management.

Usage:
  python audit.py --record '{"person":"Partner","verdict":"ADVISORY",...}'
  python audit.py --list [--last N]
  python audit.py --query REL-XXXXXXXX
  python audit.py --stats

Always exits 0. Always returns JSON.
"""
import argparse
import json
import os
import uuid
from datetime import datetime, timezone

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(SKILL_DIR, "state")
LOG_PATH = os.path.join(STATE_DIR, "interaction_log.jsonl")


def ensure_state_dir():
    os.makedirs(STATE_DIR, exist_ok=True)
    if not os.path.exists(LOG_PATH):
        open(LOG_PATH, "w").close()


def append_record(record: dict):
    ensure_state_dir()
    if "eval_id" not in record:
        record["eval_id"] = f"REL-{uuid.uuid4().hex[:8].upper()}"
    if "recorded_at" not in record:
        record["recorded_at"] = datetime.now(timezone.utc).isoformat()
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")
    return record["eval_id"]


def load_records(last_n=None):
    ensure_state_dir()
    records = []
    try:
        with open(LOG_PATH) as f:
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


def query_record(eval_id):
    for rec in load_records():
        if rec.get("eval_id") == eval_id:
            return rec
    return None


def compute_stats(records):
    if not records:
        return {"total": 0}

    verdicts = {}
    protect_count = 0
    intervene_count = 0
    per_person = {}

    for r in records:
        v = r.get("verdict", "UNKNOWN")
        verdicts[v] = verdicts.get(v, 0) + 1
        if v == "PROTECT":
            protect_count += 1
        if v == "INTERVENE":
            intervene_count += 1
        person = r.get("person", "unknown")
        per_person[person] = per_person.get(person, 0) + 1

    return {
        "total_evaluations": len(records),
        "verdict_breakdown": verdicts,
        "protect_episodes": protect_count,
        "intervene_episodes": intervene_count,
        "evaluations_per_person": per_person,
        "first_evaluation": records[0].get("recorded_at") if records else None,
        "last_evaluation": records[-1].get("recorded_at") if records else None,
    }


def format_summary(rec):
    return {
        "eval_id": rec.get("eval_id", "?"),
        "date": rec.get("recorded_at", "")[:10],
        "person": rec.get("person", "unknown"),
        "verdict": rec.get("verdict", "?"),
        "flags": rec.get("flags", []),
        "composite_risk": rec.get("composite_risk", None),
    }


def main():
    p = argparse.ArgumentParser()
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--record", help="JSON string of the evaluation to record")
    group.add_argument("--list", action="store_true")
    group.add_argument("--query", metavar="EVAL_ID")
    group.add_argument("--stats", action="store_true")
    p.add_argument("--last", type=int, default=20)
    args = p.parse_args()

    if args.record:
        try:
            record = json.loads(args.record)
        except json.JSONDecodeError as e:
            print(json.dumps({"status": "error", "message": f"Invalid JSON: {e}"}))
            return
        eval_id = append_record(record)
        print(json.dumps({"status": "recorded", "eval_id": eval_id}))

    elif args.list:
        records = load_records(last_n=args.last)
        summaries = [format_summary(r) for r in records]
        print(json.dumps({"status": "ok", "count": len(summaries), "records": summaries}, indent=2))

    elif args.query:
        rec = query_record(args.query)
        if rec:
            print(json.dumps({"status": "found", "record": rec}, indent=2))
        else:
            print(json.dumps({"status": "not_found", "eval_id": args.query}))

    elif args.stats:
        records = load_records()
        stats = compute_stats(records)
        print(json.dumps({"status": "ok", "stats": stats}, indent=2))


if __name__ == "__main__":
    main()
