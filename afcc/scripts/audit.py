#!/usr/bin/env python3
"""
AFCC audit.py — Immutable audit trail management.

Usage:
  python audit.py --record '{"amount":5000,"verdict":"APPROVE",...}'
  python audit.py --list [--last N]
  python audit.py --query TXN-XXXXXXXX
  python audit.py --stats

Always exits 0. Always returns JSON.
"""
import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(SKILL_DIR, "state")
AUDIT_PATH = os.path.join(STATE_DIR, "audit_trail.jsonl")


def ensure_state_dir():
    os.makedirs(STATE_DIR, exist_ok=True)
    if not os.path.exists(AUDIT_PATH):
        open(AUDIT_PATH, "w").close()


def append_record(record: dict):
    """Append a single record to the immutable audit trail."""
    ensure_state_dir()
    if "transaction_id" not in record:
        record["transaction_id"] = f"TXN-{uuid.uuid4().hex[:8].upper()}"
    if "recorded_at" not in record:
        record["recorded_at"] = datetime.now(timezone.utc).isoformat()

    with open(AUDIT_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")

    return record["transaction_id"]


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


def query_record(txn_id):
    for rec in load_records():
        if rec.get("transaction_id") == txn_id:
            return rec
    return None


def compute_stats(records):
    if not records:
        return {"total": 0}

    verdicts = {}
    total_blocked = 0
    total_amount = 0.0
    blocked_amount = 0.0
    fraud_vetoes = 0
    policy_vetoes = 0

    for r in records:
        v = r.get("verdict", "UNKNOWN")
        verdicts[v] = verdicts.get(v, 0) + 1
        amt = r.get("amount", 0)
        try:
            amt = float(amt)
        except (TypeError, ValueError):
            amt = 0.0
        total_amount += amt

        if v == "BLOCK":
            total_blocked += 1
            blocked_amount += amt
            if "scam" in str(r.get("veto_agents", [])).lower():
                fraud_vetoes += 1
            if r.get("constitutional_violations"):
                policy_vetoes += 1

    return {
        "total_decisions": len(records),
        "verdict_breakdown": verdicts,
        "total_amount_evaluated": round(total_amount, 2),
        "total_amount_blocked": round(blocked_amount, 2),
        "block_rate": round(total_blocked / len(records), 3) if records else 0,
        "fraud_vetoes": fraud_vetoes,
        "policy_vetoes": policy_vetoes,
        "first_decision": records[0].get("recorded_at") if records else None,
        "last_decision": records[-1].get("recorded_at") if records else None,
    }


def format_record_summary(rec):
    """Return a short human-readable summary line for a record."""
    txn = rec.get("transaction_id", "?")
    amt = rec.get("amount", 0)
    ben = rec.get("beneficiary", "unknown")
    verdict = rec.get("verdict", "?")
    ts = rec.get("recorded_at", "")[:10]
    explanation = rec.get("explanation", "")[:60]
    return {
        "transaction_id": txn,
        "date": ts,
        "amount": amt,
        "beneficiary": ben,
        "verdict": verdict,
        "explanation_preview": explanation,
    }


def main():
    p = argparse.ArgumentParser()
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--record", help="JSON string of the decision to record")
    group.add_argument("--list", action="store_true", help="List audit trail")
    group.add_argument("--query", metavar="TXN_ID", help="Query by transaction ID")
    group.add_argument("--stats", action="store_true", help="Show audit statistics")

    p.add_argument("--last", type=int, default=20,
                   help="Number of recent records to show (with --list)")

    args = p.parse_args()

    if args.record:
        try:
            record = json.loads(args.record)
        except json.JSONDecodeError as e:
            print(json.dumps({"status": "error", "message": f"Invalid JSON: {e}"}))
            return
        txn_id = append_record(record)
        print(json.dumps({"status": "recorded", "transaction_id": txn_id}))

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
            print(json.dumps({"status": "not_found", "transaction_id": args.query}))

    elif args.stats:
        records = load_records()
        stats = compute_stats(records)
        print(json.dumps({"status": "ok", "stats": stats}, indent=2))


if __name__ == "__main__":
    main()
