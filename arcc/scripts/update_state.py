#!/usr/bin/env python3
"""
RCC update_state.py — Mutate relationship graph, commitments, and energy budget.

Usage:
  python update_state.py --add-relationship '{"name":"Partner","type":"partner","notes":"..."}'
  python update_state.py --log-contact '{"person":"Partner","quality":0.8,"duration_hours":1}'
  python update_state.py --set-tension '{"person":"Partner","tension":0.6}'
  python update_state.py --add-commitment '{"person":"Partner","description":"Call back tomorrow","due":"2026-05-10"}'
  python update_state.py --resolve-commitment '{"index":0}'
  python update_state.py --set-policy '{"path":"conflict_policy.unresolved_conflict_limit_hours","value":48}'
  python update_state.py --update-energy '{"spent_hours":2.5}'
  python update_state.py --reset-energy-week

Always exits 0. Always returns JSON.
"""
import argparse
import json
import os
from datetime import datetime, timezone

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(SKILL_DIR, "state")


def file_path(name):
    return os.path.join(STATE_DIR, name)


def load(name):
    path = file_path(name)
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def save(name, data):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(file_path(name), "w") as f:
        json.dump(data, f, indent=2)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def set_nested(d, path, value):
    """Set a nested key by dot-path, e.g. 'conflict_policy.unresolved_conflict_limit_hours'."""
    keys = path.split(".")
    for k in keys[:-1]:
        d = d.setdefault(k, {})
    d[keys[-1]] = value


def main():
    p = argparse.ArgumentParser()
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--add-relationship", help="JSON with name, type, notes")
    group.add_argument("--log-contact", help="JSON with person, quality, duration_hours")
    group.add_argument("--set-tension", help="JSON with person, tension (0-1)")
    group.add_argument("--add-commitment", help="JSON with person, description, due")
    group.add_argument("--resolve-commitment", help="JSON with index or description")
    group.add_argument("--set-policy", help="JSON with path (dot-notation) and value")
    group.add_argument("--update-energy", help="JSON with spent_hours to add")
    group.add_argument("--reset-energy-week", action="store_true")
    args = p.parse_args()

    # ── Add / update relationship ─────────────────────────────────────────────
    if args.add_relationship:
        payload = json.loads(args.add_relationship)
        rg = load("relationship_graph.json") or {"version": "1.0", "relationships": {}}
        name = payload.get("name", "unknown")
        existing = rg["relationships"].get(name, {})
        existing.update({
            "relationship_type": payload.get("type", existing.get("relationship_type", "other")),
            "notes": payload.get("notes", existing.get("notes", "")),
            "trust_score": payload.get("trust_score", existing.get("trust_score", 0.8)),
            "current_tension": existing.get("current_tension", 0.0),
            "last_contact": existing.get("last_contact"),
            "added_at": existing.get("added_at", now_iso()),
            "history": existing.get("history", []),
        })
        rg["relationships"][name] = existing
        rg["last_updated"] = now_iso()
        save("relationship_graph.json", rg)
        print(json.dumps({"status": "ok", "action": "add_relationship", "name": name}))

    # ── Log contact ───────────────────────────────────────────────────────────
    elif args.log_contact:
        payload = json.loads(args.log_contact)
        person = payload.get("person", "unknown")
        rg = load("relationship_graph.json") or {"version": "1.0", "relationships": {}}
        rel = rg["relationships"].setdefault(person, {
            "relationship_type": "other", "trust_score": 0.8,
            "current_tension": 0.0, "added_at": now_iso(), "history": []
        })
        entry = {
            "date": now_iso(),
            "quality": payload.get("quality", 0.7),
            "duration_hours": payload.get("duration_hours", 0),
            "notes": payload.get("notes", ""),
        }
        rel.setdefault("history", []).append(entry)
        rel["last_contact"] = now_iso()
        rg["last_updated"] = now_iso()
        save("relationship_graph.json", rg)

        # Update energy budget
        dur = payload.get("duration_hours", 0)
        if dur > 0:
            energy = load("energy_budget.json") or {}
            energy["current_week_spent_hours"] = energy.get("current_week_spent_hours", 0) + dur
            per_rel = energy.setdefault("per_relationship_hours", {})
            per_rel[person] = per_rel.get(person, 0) + dur
            energy["last_updated"] = now_iso()
            save("energy_budget.json", energy)

        print(json.dumps({"status": "ok", "action": "log_contact", "person": person}))

    # ── Set tension ───────────────────────────────────────────────────────────
    elif args.set_tension:
        payload = json.loads(args.set_tension)
        person = payload.get("person", "unknown")
        tension = float(payload.get("tension", 0.0))
        rg = load("relationship_graph.json") or {"version": "1.0", "relationships": {}}
        rg["relationships"].setdefault(person, {})["current_tension"] = tension
        rg["last_updated"] = now_iso()
        save("relationship_graph.json", rg)
        print(json.dumps({"status": "ok", "action": "set_tension", "person": person, "tension": tension}))

    # ── Add commitment ────────────────────────────────────────────────────────
    elif args.add_commitment:
        payload = json.loads(args.add_commitment)
        commitments = load("commitments.json") or {"version": "1.0", "commitments": []}
        entry = {
            "person": payload.get("person", "unknown"),
            "description": payload.get("description", ""),
            "due": payload.get("due", None),
            "added_at": now_iso(),
            "status": "pending",
        }
        commitments["commitments"].append(entry)
        commitments["last_updated"] = now_iso()
        save("commitments.json", commitments)
        print(json.dumps({"status": "ok", "action": "add_commitment", "entry": entry}))

    # ── Resolve commitment ────────────────────────────────────────────────────
    elif args.resolve_commitment:
        payload = json.loads(args.resolve_commitment)
        commitments = load("commitments.json") or {"version": "1.0", "commitments": []}
        all_c = commitments.get("commitments", [])
        idx = payload.get("index", None)
        desc = payload.get("description", None)
        resolved = False
        if idx is not None and 0 <= int(idx) < len(all_c):
            all_c[int(idx)]["status"] = "resolved"
            all_c[int(idx)]["resolved_at"] = now_iso()
            resolved = True
        elif desc:
            for c in all_c:
                if c.get("description", "") == desc and c.get("status") == "pending":
                    c["status"] = "resolved"
                    c["resolved_at"] = now_iso()
                    resolved = True
                    break
        commitments["commitments"] = all_c
        commitments["last_updated"] = now_iso()
        save("commitments.json", commitments)
        print(json.dumps({"status": "ok", "action": "resolve_commitment", "resolved": resolved}))

    # ── Set policy ────────────────────────────────────────────────────────────
    elif args.set_policy:
        payload = json.loads(args.set_policy)
        policies = load("policies.json") or {}
        path = payload.get("path", "")
        value = payload.get("value")
        if path and value is not None:
            set_nested(policies, path, value)
            policies["last_updated"] = now_iso()
            save("policies.json", policies)
        print(json.dumps({"status": "ok", "action": "set_policy", "path": path, "value": value}))

    # ── Update energy ─────────────────────────────────────────────────────────
    elif args.update_energy:
        payload = json.loads(args.update_energy)
        energy = load("energy_budget.json") or {"current_week_spent_hours": 0}
        energy["current_week_spent_hours"] = (
            energy.get("current_week_spent_hours", 0) + float(payload.get("spent_hours", 0))
        )
        energy["last_updated"] = now_iso()
        save("energy_budget.json", energy)
        print(json.dumps({"status": "ok", "action": "update_energy",
                          "current_week_spent_hours": energy["current_week_spent_hours"]}))

    # ── Reset energy week ─────────────────────────────────────────────────────
    elif args.reset_energy_week:
        energy = load("energy_budget.json") or {}
        energy["current_week_spent_hours"] = 0
        energy["week_start"] = now_iso()
        energy["per_relationship_hours"] = {}
        energy["last_updated"] = now_iso()
        save("energy_budget.json", energy)
        print(json.dumps({"status": "ok", "action": "reset_energy_week"}))


if __name__ == "__main__":
    main()
