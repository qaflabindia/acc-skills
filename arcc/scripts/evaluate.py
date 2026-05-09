#!/usr/bin/env python3
"""
RCC evaluate.py — Core 5-layer relational evaluation engine.

Applies Control Layer logic (Layer 3) using cognitive scores from Claude's
Layer 1-2 reasoning. Produces a structured relational verdict JSON.

Usage:
  python evaluate.py \\
    --person "Partner" \\
    --relationship-type partner \\
    --last-contact-days 3 \\
    --interaction-quality 0.70 \\
    --reciprocity 0.30 \\
    --tension-level 0.60 \\
    --commitment-breach 0.20 \\
    --emotional-load 0.55 \\
    --boundary-risk 0.10 \\
    --repair-readiness 0.50 \\
    --format compact

Always exits 0. Always returns JSON.
"""
import argparse
import json
import os
import uuid
from datetime import datetime, timezone

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(SKILL_DIR, "state")

# ── Verdict constants ─────────────────────────────────────────────────────────

STABLE    = "STABLE"
NUDGE     = "NUDGE"
ADVISORY  = "ADVISORY"
INTERVENE = "INTERVENE"
PROTECT   = "PROTECT"

# ── Frequency decay tables ────────────────────────────────────────────────────

EXPECTED_CONTACT_DAYS = {
    "partner":  1,
    "family":   7,
    "friend":   30,
    "work":     5,
    "other":    30,
}


# ── Loaders ───────────────────────────────────────────────────────────────────

def load_policies():
    path = os.path.join(STATE_DIR, "policies.json")
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


def load_relationship(person):
    path = os.path.join(STATE_DIR, "relationship_graph.json")
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        rg = json.load(f)
    return rg.get("relationships", {}).get(person, {})


# ── Argument parsing ──────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="RCC relational evaluator")
    p.add_argument("--person", default="unknown")
    p.add_argument("--relationship-type", dest="rel_type", default="other",
                   choices=["partner", "family", "friend", "work", "other"])
    p.add_argument("--last-contact-days", type=float, default=0.0)
    p.add_argument("--interaction-quality", type=float, default=1.0,
                   help="0=toxic, 1=excellent")
    p.add_argument("--reciprocity", type=float, default=0.5,
                   help="0=fully user-initiated, 1=balanced/counterpart-led")
    p.add_argument("--tension-level", type=float, default=0.0,
                   help="0=no tension, 1=active unresolved conflict")
    p.add_argument("--commitment-breach", type=float, default=0.0,
                   help="0=all commitments met, 1=all broken")
    p.add_argument("--emotional-load", type=float, default=0.0,
                   help="0=energizing, 1=fully draining")
    p.add_argument("--boundary-risk", type=float, default=0.0,
                   help="0=healthy, 1=coercive/exploitative")
    p.add_argument("--repair-readiness", type=float, default=1.0,
                   help="0=no repair possible, 1=both ready")
    p.add_argument("--context", default="",
                   help="Brief free-text description for audit")
    p.add_argument("--format", dest="output_format", default="compact",
                   choices=["compact", "full"])
    return p.parse_args()


# ── Drift score computation ───────────────────────────────────────────────────

def compute_drift_score(last_contact_days, rel_type, policies):
    expected = policies.get("frequency_expectations", {}).get(rel_type, "monthly")
    expected_map = {"daily": 1, "weekly": 7, "monthly": 30, "quarterly": 90}
    expected_days = expected_map.get(expected, EXPECTED_CONTACT_DAYS.get(rel_type, 30))
    if expected_days <= 0:
        return 0.0
    ratio = last_contact_days / expected_days
    # Sigmoid-like mapping: 0x=0, 1x=0.30, 2x=0.60, 3x=0.80, 4x+=0.95
    if ratio <= 0:
        return 0.0
    if ratio <= 1.0:
        return round(ratio * 0.30, 3)
    if ratio <= 2.0:
        return round(0.30 + (ratio - 1.0) * 0.30, 3)
    if ratio <= 3.0:
        return round(0.60 + (ratio - 2.0) * 0.20, 3)
    return min(round(0.80 + (ratio - 3.0) * 0.05, 3), 0.95)


# ── Composite relational risk ─────────────────────────────────────────────────

def compute_composite_risk(drift, reciprocity_imbalance, tension, commitment_breach,
                            emotional_load, boundary_risk):
    """
    Higher = more relational distress. Clamp 0-1.
    Boundary risk and tension are weighted highest.
    """
    scores = [
        boundary_risk * 1.5,
        tension * 1.3,
        drift * 1.0,
        reciprocity_imbalance * 0.9,
        emotional_load * 0.8,
        commitment_breach * 0.7,
    ]
    return min(max(scores), 1.0)


# ── Control rules ─────────────────────────────────────────────────────────────

def evaluate_control(args, policies, drift_score, reciprocity_imbalance, composite_risk):
    flags = []
    rules_triggered = []

    boundary_pol = policies.get("boundary_policy", {})
    conflict_pol = policies.get("conflict_policy", {})
    commitment_pol = policies.get("commitment_policy", {})
    reciprocity_pol = policies.get("reciprocity_policy", {})

    auto_protect_thresh = boundary_pol.get("manipulation_auto_protect_threshold", 0.80)
    emotional_load_thresh = boundary_pol.get("emotional_load_alert_threshold", 0.75)
    conflict_limit_h = conflict_pol.get("unresolved_conflict_limit_hours", 72)
    commit_breach_thresh = commitment_pol.get("critical_breach_threshold", 0.60)
    reciprocity_thresh = reciprocity_pol.get("imbalance_alert_threshold", 0.65)

    # ── PROTECT (non-negotiable constitutional blocks) ────────────────────────

    if args.boundary_risk >= auto_protect_thresh:
        flags.append(f"boundary_risk_{args.boundary_risk:.2f}_exceeds_protect_threshold")
        rules_triggered.append("CR-B01: Boundary risk >= auto-protect threshold")
        return (PROTECT, flags, rules_triggered)

    if args.emotional_load >= emotional_load_thresh and args.boundary_risk >= 0.50:
        flags.append("emotional_exhaustion_with_elevated_boundary_risk")
        rules_triggered.append("CR-B02: Emotional overload + boundary risk → protect")
        return (PROTECT, flags, rules_triggered)

    # ── INTERVENE ─────────────────────────────────────────────────────────────

    if args.tension_level >= 0.70:
        flags.append(f"high_tension_{args.tension_level:.2f}_active_conflict")
        rules_triggered.append("CR-C01: High tension level — active conflict requires attention")
        return (INTERVENE, flags, rules_triggered)

    if args.commitment_breach >= commit_breach_thresh:
        flags.append(f"commitment_breach_{args.commitment_breach:.2f}_exceeds_critical_threshold")
        rules_triggered.append("CR-K01: Critical commitment breach — repair needed")
        return (INTERVENE, flags, rules_triggered)

    if args.repair_readiness < 0.20 and args.tension_level >= 0.40:
        flags.append("low_repair_readiness_with_moderate_tension")
        rules_triggered.append("CR-C02: Repair blocked — tension sustained without resolution path")
        return (INTERVENE, flags, rules_triggered)

    # ── ADVISORY ──────────────────────────────────────────────────────────────

    if reciprocity_imbalance >= reciprocity_thresh:
        flags.append(f"reciprocity_imbalance_{reciprocity_imbalance:.2f}_above_threshold")
        rules_triggered.append("CR-R01: Sustained reciprocity imbalance — advisory")

    if drift_score >= 0.60:
        flags.append(f"drift_score_{drift_score:.2f}_significant_continuity_gap")
        rules_triggered.append("CR-D01: Significant continuity drift detected")

    if args.emotional_load >= emotional_load_thresh:
        flags.append(f"emotional_load_{args.emotional_load:.2f}_approaching_burnout")
        rules_triggered.append("CR-E01: Emotional load near burnout threshold")

    if args.tension_level >= 0.40:
        flags.append(f"tension_{args.tension_level:.2f}_accumulating")
        rules_triggered.append("CR-C03: Moderate tension accumulating — watch trajectory")

    if flags:
        return (ADVISORY, flags, rules_triggered)

    # ── NUDGE ─────────────────────────────────────────────────────────────────

    if drift_score >= 0.30:
        flags.append(f"drift_score_{drift_score:.2f}_mild_continuity_gap")
        rules_triggered.append("CR-D02: Mild continuity gap — consider reaching out")
        return (NUDGE, flags, rules_triggered)

    if reciprocity_imbalance >= 0.40:
        flags.append(f"reciprocity_imbalance_{reciprocity_imbalance:.2f}_mild")
        rules_triggered.append("CR-R02: Mild reciprocity imbalance — monitor")
        return (NUDGE, flags, rules_triggered)

    if args.commitment_breach >= 0.20:
        flags.append(f"commitment_breach_{args.commitment_breach:.2f}_pending")
        rules_triggered.append("CR-K02: Pending commitment breach — follow up")
        return (NUDGE, flags, rules_triggered)

    # ── STABLE ────────────────────────────────────────────────────────────────

    return (STABLE, [], ["All relational indicators within healthy range"])


# ── Agent panel ───────────────────────────────────────────────────────────────

def compute_agent_panel(args, verdict, drift_score, reciprocity_imbalance):
    agents = {}

    # Continuity Agent
    if drift_score >= 0.60:
        agents["continuity_agent"] = {"verdict": "CONCERN", "evidence": f"Drift {drift_score:.2f} — contact overdue"}
    elif drift_score >= 0.30:
        agents["continuity_agent"] = {"verdict": "WATCH", "evidence": f"Drift {drift_score:.2f} — approaching threshold"}
    else:
        agents["continuity_agent"] = {"verdict": "CLEAR", "evidence": f"Drift {drift_score:.2f} — contact frequency healthy"}

    # Reciprocity Agent
    if reciprocity_imbalance >= 0.65:
        agents["reciprocity_agent"] = {"verdict": "CONCERN", "evidence": f"Imbalance {reciprocity_imbalance:.2f} — user over-contributing"}
    elif reciprocity_imbalance >= 0.40:
        agents["reciprocity_agent"] = {"verdict": "WATCH", "evidence": f"Imbalance {reciprocity_imbalance:.2f} — mild asymmetry"}
    else:
        agents["reciprocity_agent"] = {"verdict": "CLEAR", "evidence": f"Imbalance {reciprocity_imbalance:.2f} — balanced exchange"}

    # Conflict Agent
    if args.tension_level >= 0.70:
        agents["conflict_agent"] = {"verdict": "CONCERN", "evidence": f"Tension {args.tension_level:.2f} — active unresolved conflict"}
    elif args.tension_level >= 0.40:
        agents["conflict_agent"] = {"verdict": "WATCH", "evidence": f"Tension {args.tension_level:.2f} — accumulating, needs attention"}
    else:
        agents["conflict_agent"] = {"verdict": "CLEAR", "evidence": f"Tension {args.tension_level:.2f} — no active conflict"}

    # Boundary Agent (veto authority)
    if args.boundary_risk >= 0.80:
        agents["boundary_agent"] = {
            "verdict": "VETO", "evidence": f"Boundary risk {args.boundary_risk:.2f} — protective action required",
            "veto_authority": True
        }
    elif args.boundary_risk >= 0.50:
        agents["boundary_agent"] = {
            "verdict": "CONCERN", "evidence": f"Boundary risk {args.boundary_risk:.2f} — stress indicators present",
            "veto_authority": True
        }
    else:
        agents["boundary_agent"] = {
            "verdict": "CLEAR", "evidence": f"Boundary risk {args.boundary_risk:.2f} — healthy interaction pattern",
            "veto_authority": True
        }

    # Memory Agent
    if args.commitment_breach >= 0.60:
        agents["memory_agent"] = {"verdict": "CONCERN", "evidence": f"Commitment breach {args.commitment_breach:.2f} — critical unfulfilled obligations"}
    elif args.commitment_breach >= 0.20:
        agents["memory_agent"] = {"verdict": "WATCH", "evidence": f"Commitment breach {args.commitment_breach:.2f} — follow-ups pending"}
    else:
        agents["memory_agent"] = {"verdict": "CLEAR", "evidence": f"Commitment breach {args.commitment_breach:.2f} — obligations on track"}

    # Emotional Load Agent
    if args.emotional_load >= 0.75:
        agents["load_agent"] = {"verdict": "CONCERN", "evidence": f"Emotional load {args.emotional_load:.2f} — near burnout"}
    elif args.emotional_load >= 0.50:
        agents["load_agent"] = {"verdict": "WATCH", "evidence": f"Emotional load {args.emotional_load:.2f} — elevated, monitor pacing"}
    else:
        agents["load_agent"] = {"verdict": "CLEAR", "evidence": f"Emotional load {args.emotional_load:.2f} — sustainable"}

    return agents


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    args = parse_args()
    policies = load_policies()

    # Derived scores
    drift_score = compute_drift_score(args.last_contact_days, args.rel_type, policies)
    reciprocity_imbalance = max(0.0, 1.0 - (args.reciprocity * 2))  # 0.5 reciprocity → 0 imbalance
    reciprocity_imbalance = round(min(reciprocity_imbalance, 1.0), 3)

    composite_risk = compute_composite_risk(
        drift_score, reciprocity_imbalance,
        args.tension_level, args.commitment_breach,
        args.emotional_load, args.boundary_risk
    )

    verdict, flags, rules = evaluate_control(
        args, policies, drift_score, reciprocity_imbalance, composite_risk
    )

    eval_id = f"REL-{uuid.uuid4().hex[:8].upper()}"

    if args.output_format == "compact":
        flag_str = " · ".join(flags) if flags else "healthy"
        compact = {
            "eval_id": eval_id,
            "person": args.person,
            "verdict": verdict,
            "flags": flags,
            "flag_str": flag_str,
            "drift": round(drift_score, 3),
            "reciprocity_imbalance": reciprocity_imbalance,
            "tension": round(args.tension_level, 3),
            "emotional_load": round(args.emotional_load, 3),
            "boundary_risk": round(args.boundary_risk, 3),
            "composite_risk": round(composite_risk, 3),
            "rules": rules,
        }
        print(json.dumps(compact))
        return

    # Full output
    result = {
        "eval_id": eval_id,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "input": {
            "person": args.person,
            "relationship_type": args.rel_type,
            "last_contact_days": args.last_contact_days,
            "context": args.context,
        },
        "cognitive_scores": {
            "drift_score": round(drift_score, 3),
            "reciprocity_imbalance": reciprocity_imbalance,
            "tension_level": round(args.tension_level, 3),
            "commitment_breach": round(args.commitment_breach, 3),
            "emotional_load": round(args.emotional_load, 3),
            "boundary_risk": round(args.boundary_risk, 3),
            "repair_readiness": round(args.repair_readiness, 3),
            "interaction_quality": round(args.interaction_quality, 3),
        },
        "composite_risk": round(composite_risk, 3),
        "control_decision": {
            "verdict": verdict,
            "flags": flags,
            "policy_rules_triggered": rules,
        },
        "agent_panel": compute_agent_panel(args, verdict, drift_score, reciprocity_imbalance),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
