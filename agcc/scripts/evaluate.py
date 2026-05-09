#!/usr/bin/env python3
"""
AGCC evaluate.py — Constitutional execution evaluation engine.

Implements Layers 3 (SIMULATE), 4 (CONTROL), and 5 (ARBITRATION).
Accepts risk scores from Claude's Layer 2 reasoning and produces
a structured governance verdict.

Usage (compact):
  python evaluate.py \\
    --action-type deployment --reversibility hard_to_reverse \\
    --scope production --confidence 0.72 --authorized false \\
    --urgency high --cascade-potential 0.60 --uncertainty 0.40 \\
    --irreversibility-risk 0.70 --scope-risk 1.00 \\
    --authorization-deficit 0.85 --behavioral-anomaly 0.10 \\
    --policy-compliance 0.00 --agent-id deploy-agent \\
    --format compact

Usage (simulate):
  python evaluate.py ... --format simulate

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

# ── Verdict constants ─────────────────────────────────────────────────────────

EXECUTE = "EXECUTE"
ADVISORY = "EXECUTE_WITH_ADVISORY"
DEFER = "DEFER"
CONSTRAIN = "CONSTRAIN"
ESCALATE = "ESCALATE"
HALT = "HALT"

# ── Action type classifications ───────────────────────────────────────────────

POLICY_MUTATION_TYPES = {"policy_mutation", "policy_change", "policy_update", "constraint_removal"}
IRREVERSIBLE_TYPES = {"irreversible", "deployment", "agent_spawn", "data_deletion", "state_destroy"}
HIGH_BLAST_TYPES = {"deployment", "agent_spawn", "external_service", "communication"}

URGENCY_SCORES = {
    "none": 0.00, "low": 0.20, "medium": 0.40,
    "high": 0.70, "critical": 0.95
}

SCOPE_RISK_MAP = {
    "production": 1.00, "external_service": 0.80, "shared_system": 0.70,
    "staging": 0.40, "test": 0.10, "local": 0.05, "unknown": 0.50
}

REVERSIBILITY_RISK_MAP = {
    "irreversible": 1.00, "hard_to_reverse": 0.70,
    "reversible": 0.25, "read_only": 0.00, "unknown": 0.50
}


# ── State loaders ─────────────────────────────────────────────────────────────

def load_policies():
    path = os.path.join(STATE_DIR, "policies.json")
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


def load_agent_registry():
    path = os.path.join(STATE_DIR, "agent_registry.json")
    if not os.path.exists(path):
        return {"agents": {}}
    with open(path) as f:
        return json.load(f)


def load_behavior_history():
    path = os.path.join(STATE_DIR, "behavior_history.json")
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


# ── Argument parsing ──────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="AGCC constitutional evaluation engine")
    p.add_argument("--action-type", dest="action_type", default="unknown")
    p.add_argument("--reversibility", default="unknown",
                   choices=["irreversible", "hard_to_reverse", "reversible", "read_only", "unknown"])
    p.add_argument("--scope", default="unknown",
                   choices=["local", "shared_system", "external_service", "production",
                            "staging", "test", "unknown"])
    p.add_argument("--confidence", type=float, default=0.50)
    p.add_argument("--authorized", default="false")
    p.add_argument("--urgency", default="none",
                   choices=["none", "low", "medium", "high", "critical"])
    p.add_argument("--cascade-potential", dest="cascade_potential", type=float, default=0.30)
    p.add_argument("--uncertainty", type=float, default=0.30)
    p.add_argument("--irreversibility-risk", dest="irreversibility_risk", type=float, default=None)
    p.add_argument("--scope-risk", dest="scope_risk", type=float, default=None)
    p.add_argument("--authorization-deficit", dest="authorization_deficit", type=float, default=None)
    p.add_argument("--behavioral-anomaly", dest="behavioral_anomaly", type=float, default=0.00)
    p.add_argument("--policy-compliance", dest="policy_compliance", type=float, default=0.00)
    p.add_argument("--agent-id", dest="agent_id", default="unknown")
    p.add_argument("--context", default="")
    p.add_argument("--format", dest="output_format", default="compact",
                   choices=["compact", "full", "simulate"])
    return p.parse_args()


def bool_arg(val):
    return str(val).lower() in ("true", "1", "yes")


# ── Score derivation ──────────────────────────────────────────────────────────

def derive_scores(args, policies):
    """Fill in any scores not explicitly provided using standard mappings."""
    exec_policy = policies.get("execution_policy", {})

    ir = args.irreversibility_risk
    if ir is None:
        ir = REVERSIBILITY_RISK_MAP.get(args.reversibility, 0.50)
        if args.action_type.lower() in IRREVERSIBLE_TYPES:
            ir = max(ir, 0.70)

    sr = args.scope_risk
    if sr is None:
        sr = SCOPE_RISK_MAP.get(args.scope, 0.50)

    ad = args.authorization_deficit
    if ad is None:
        if bool_arg(args.authorized):
            ad = 0.00
        elif args.urgency in ("high", "critical"):
            ad = 0.85
        else:
            ad = 0.50

    return ir, sr, ad


def compute_exec_confidence(ir, sr, uncertainty, ad, cascade, anomaly, compliance):
    """Composite execution confidence: 0=no confidence, 1=full confidence."""
    scores = [
        ir * 1.5,
        sr * 1.2,
        uncertainty * 1.3,
        ad * 1.4,
        cascade * 1.1,
        anomaly * 0.9,
        compliance * 1.6,
    ]
    composite_risk = min(max(scores), 1.0)
    return round(1.0 - composite_risk, 3)


# ── Constitutional control rules ──────────────────────────────────────────────

def evaluate_control(args, policies, ir, sr, ad, exec_conf):
    flags = []
    rules_triggered = []
    delay_minutes = None
    constraints = None
    override_allowed = True

    authorized = bool_arg(args.authorized)
    action_lower = args.action_type.lower()
    is_policy_mutation = action_lower in POLICY_MUTATION_TYPES
    is_irreversible = (args.reversibility == "irreversible" or action_lower in IRREVERSIBLE_TYPES)
    is_read_only = args.reversibility == "read_only"

    exec_policy = policies.get("execution_policy", {})
    override_policy = policies.get("override_policy", {})

    prod_threshold = exec_policy.get("production_confidence_threshold", 0.75)
    max_cascade = exec_policy.get("max_cascade_risk", 0.85)
    max_uncertainty = exec_policy.get("max_uncertainty", 0.80)
    anomaly_threshold = exec_policy.get("behavioral_anomaly_threshold", 0.85)

    # ── CR-AG01: Authorization Gate ──────────────────────────────────────────
    if is_irreversible and not authorized:
        flags.append("CR-AG01:irreversible_without_authorization")
        rules_triggered.append("CR-AG01: Irreversible action requires explicit human authorization")
        return (HALT, None, None, False, flags, rules_triggered)

    # ── CR-AG03: Policy Lock Under Pressure ──────────────────────────────────
    if is_policy_mutation and args.urgency in ("high", "critical"):
        flags.append("CR-AG03:policy_mutation_under_pressure")
        rules_triggered.append("CR-AG03: Policy mutation prohibited under high/critical urgency")
        return (HALT, None, None, False, flags, rules_triggered)

    # ── CR-AG07: Urgency ≠ Authorization ─────────────────────────────────────
    if args.urgency == "critical" and not authorized and ad >= 0.80:
        flags.append("CR-AG07:urgency_used_as_authorization_substitute")
        rules_triggered.append("CR-AG07: Critical urgency cannot substitute for explicit authorization")
        return (HALT, None, None, False, flags, rules_triggered)

    # ── CR-AG06: Behavioral Anomaly Gate ─────────────────────────────────────
    if args.behavioral_anomaly > anomaly_threshold:
        flags.append(f"CR-AG06:behavioral_anomaly_{args.behavioral_anomaly:.2f}_exceeds_{anomaly_threshold}")
        rules_triggered.append("CR-AG06: Behavioral anomaly exceeds threshold — agent state suspect")
        override_allowed = False
        return (ESCALATE, None, None, override_allowed, flags, rules_triggered)

    # ── CR-AG04: Cascade Veto ────────────────────────────────────────────────
    if args.cascade_potential > max_cascade:
        flags.append(f"CR-AG04:cascade_risk_{args.cascade_potential:.2f}_exceeds_{max_cascade}")
        rules_triggered.append("CR-AG04: Cascade risk exceeds veto threshold")
        override_allowed = (exec_conf >= override_policy.get("medium_risk_max", 0.50))
        return (ESCALATE, None, None, override_allowed, flags, rules_triggered)

    # ── CR-AG05: Uncertainty Floor ───────────────────────────────────────────
    if args.uncertainty > max_uncertainty:
        flags.append(f"CR-AG05:uncertainty_{args.uncertainty:.2f}_exceeds_floor_{max_uncertainty}")
        rules_triggered.append("CR-AG05: Uncertainty above floor — mandatory 30-minute deferral")
        delay_minutes = 30
        override_allowed = (args.urgency in ("none", "low"))
        return (DEFER, delay_minutes, None, override_allowed, flags, rules_triggered)

    # ── CR-AG02: Production Gate ─────────────────────────────────────────────
    if args.scope == "production" and exec_conf < prod_threshold:
        flags.append(f"CR-AG02:production_gate_confidence_{exec_conf:.2f}_below_{prod_threshold}")
        rules_triggered.append("CR-AG02: Production scope requires confidence ≥ production threshold")
        override_allowed = False
        return (ESCALATE, None, None, override_allowed, flags, rules_triggered)

    # ── Behavioral anomaly advisory ──────────────────────────────────────────
    if args.behavioral_anomaly > 0.50:
        flags.append(f"behavioral_anomaly_{args.behavioral_anomaly:.2f}_advisory")
        rules_triggered.append("BEHAVIORAL: Elevated anomaly score — execution advisory")

    # ── Cascade advisory ─────────────────────────────────────────────────────
    if args.cascade_potential > 0.50:
        flags.append(f"cascade_potential_{args.cascade_potential:.2f}_monitor_downstream")
        rules_triggered.append("CASCADE: Moderate cascade risk — monitor downstream effects")

    # ── Policy compliance violation (non-constitutional) ─────────────────────
    if args.policy_compliance > 0.50:
        flags.append(f"policy_compliance_violation_{args.policy_compliance:.2f}")
        rules_triggered.append("POLICY: Non-trivial policy compliance gap detected")
        constraints = "constrain_to_policy_compliant_subset"
        override_allowed = (exec_conf >= override_policy.get("medium_risk_max", 0.50))
        return (CONSTRAIN, None, constraints, override_allowed, flags, rules_triggered)

    # ── Scope-based constraint ────────────────────────────────────────────────
    if sr >= 0.70 and not authorized and not is_read_only:
        flags.append(f"scope_risk_{sr:.2f}_requires_constraint")
        rules_triggered.append("SCOPE: High scope risk without authorization — constrain blast radius")
        constraints = f"limit_scope_to_minimum_necessary"
        override_allowed = True
        return (CONSTRAIN, None, constraints, override_allowed, flags, rules_triggered)

    # ── General advisory threshold ────────────────────────────────────────────
    if exec_conf < 0.75 and not is_read_only:
        flags.append(f"exec_confidence_{exec_conf:.2f}_below_advisory_threshold")
        rules_triggered.append("RISK: Execution confidence below advisory threshold")
        override_allowed = True
        return (ADVISORY, None, None, override_allowed, flags, rules_triggered)

    # ── Clean execute ─────────────────────────────────────────────────────────
    if not flags:
        rules_triggered.append("All constitutional checks passed")
    return (EXECUTE, None, None, True, flags, rules_triggered)


# ── Agent panel arbitration ───────────────────────────────────────────────────

def compute_agent_panel(args, verdict, ir, sr, ad):
    agents = {}

    # Reversibility Agent
    if ir >= 0.70:
        authorized = bool_arg(args.authorized)
        veto = (ir >= 1.00 and not authorized)
        agents["reversibility_agent"] = {
            "verdict": "VETO" if veto else "CONCERN",
            "evidence": f"Irreversibility risk {ir:.2f} — {'unauthorized irreversible' if veto else 'high reversal cost'}",
            "veto_authority": True
        }
    elif ir >= 0.25:
        agents["reversibility_agent"] = {
            "verdict": "CONCERN",
            "evidence": f"Irreversibility risk {ir:.2f} — ensure rollback path exists",
            "veto_authority": True
        }
    else:
        agents["reversibility_agent"] = {
            "verdict": "CLEAR",
            "evidence": f"Reversibility risk {ir:.2f} — action is reversible or read-only",
            "veto_authority": True
        }

    # Scope Agent
    if sr >= 0.80:
        agents["scope_agent"] = {
            "verdict": "CONCERN",
            "evidence": f"Scope risk {sr:.2f} — external or production blast radius",
            "veto_authority": False
        }
    elif sr >= 0.50:
        agents["scope_agent"] = {
            "verdict": "CONCERN",
            "evidence": f"Scope risk {sr:.2f} — shared system affected",
            "veto_authority": False
        }
    else:
        agents["scope_agent"] = {
            "verdict": "CLEAR",
            "evidence": f"Scope risk {sr:.2f} — contained blast radius",
            "veto_authority": False
        }

    # Cascade Agent
    if args.cascade_potential >= 0.85:
        agents["cascade_agent"] = {
            "verdict": "VETO",
            "evidence": f"Cascade risk {args.cascade_potential:.2f} — extreme downstream exposure",
            "veto_authority": True
        }
    elif args.cascade_potential >= 0.55:
        agents["cascade_agent"] = {
            "verdict": "CONCERN",
            "evidence": f"Cascade risk {args.cascade_potential:.2f} — monitor downstream systems",
            "veto_authority": True
        }
    else:
        agents["cascade_agent"] = {
            "verdict": "CLEAR",
            "evidence": f"Cascade risk {args.cascade_potential:.2f} — limited downstream exposure",
            "veto_authority": True
        }

    # Behavioral Integrity Agent
    if args.behavioral_anomaly >= 0.85:
        agents["behavioral_integrity_agent"] = {
            "verdict": "VETO",
            "evidence": f"Anomaly score {args.behavioral_anomaly:.2f} — agent behavior is aberrant",
            "veto_authority": True
        }
    elif args.behavioral_anomaly >= 0.50:
        agents["behavioral_integrity_agent"] = {
            "verdict": "CONCERN",
            "evidence": f"Anomaly score {args.behavioral_anomaly:.2f} — elevated deviation from baseline",
            "veto_authority": True
        }
    else:
        agents["behavioral_integrity_agent"] = {
            "verdict": "CLEAR",
            "evidence": f"Anomaly score {args.behavioral_anomaly:.2f} — within normal operating range",
            "veto_authority": True
        }

    # Authorization Agent
    if ad >= 0.85:
        agents["authorization_agent"] = {
            "verdict": "CONCERN",
            "evidence": f"Authorization deficit {ad:.2f} — explicit authorization absent",
            "veto_authority": True
        }
    elif ad >= 0.40:
        agents["authorization_agent"] = {
            "verdict": "CONCERN",
            "evidence": f"Authorization deficit {ad:.2f} — authorization is implied not explicit",
            "veto_authority": True
        }
    else:
        agents["authorization_agent"] = {
            "verdict": "CLEAR",
            "evidence": f"Authorization deficit {ad:.2f} — explicit authorization present",
            "veto_authority": True
        }

    # Constitutional Policy Agent
    if verdict == HALT:
        agents["constitutional_policy_agent"] = {
            "verdict": "VETO",
            "evidence": "Constitutional rule violated — execution absolutely prohibited",
            "veto_authority": True
        }
    elif verdict in (ESCALATE, DEFER):
        agents["constitutional_policy_agent"] = {
            "verdict": "CONCERN",
            "evidence": "Policy constraints require delay or human review before execution",
            "veto_authority": True
        }
    else:
        agents["constitutional_policy_agent"] = {
            "verdict": "CLEAR",
            "evidence": "No constitutional violations detected",
            "veto_authority": True
        }

    return agents


# ── Simulation scenarios ──────────────────────────────────────────────────────

def generate_simulation(args, ir, sr, ad, exec_conf, verdict):
    scenarios = {}

    # Scenario 1: Execute now
    execute_risk = 1.0 - exec_conf
    scenarios["execute_now"] = {
        "description": "Proceed with action immediately",
        "risk_delta": round(execute_risk, 3),
        "viable": verdict in (EXECUTE, ADVISORY),
        "notes": "Recommended only if exec_confidence > 0.75 and no CR violations"
    }

    # Scenario 2: Defer
    defer_benefit = min(0.30, args.uncertainty * 0.50)
    scenarios["defer_30min"] = {
        "description": "Wait 30 minutes, gather more information, re-evaluate",
        "risk_delta": round(execute_risk - defer_benefit, 3),
        "viable": True,
        "notes": "Reduces uncertainty; recommended when uncertainty_score > 0.60"
    }

    # Scenario 3: Constrain and execute
    constrain_risk = execute_risk * 0.70
    scenarios["constrain_and_execute"] = {
        "description": "Execute with reduced scope / blast radius",
        "risk_delta": round(constrain_risk, 3),
        "viable": (sr >= 0.50 and verdict != HALT),
        "notes": "Limit scope to minimum necessary; verify rollback mechanism first"
    }

    # Scenario 4: Escalate then execute
    scenarios["escalate_then_execute"] = {
        "description": "Obtain explicit human authorization, then execute",
        "risk_delta": round(execute_risk * 0.40, 3),
        "viable": (verdict in (ESCALATE, ADVISORY, CONSTRAIN, DEFER)),
        "notes": "Required for irreversible actions; eliminates authorization deficit"
    }

    # Scenario 5: Reject
    scenarios["reject"] = {
        "description": "Do not execute this action",
        "risk_delta": 0.000,
        "viable": True,
        "notes": "Always available; mandatory when HALT verdict is issued"
    }

    worst_case = max(
        execute_risk,
        args.cascade_potential,
        ir,
        ad * 0.80
    )

    return {
        "scenarios": scenarios,
        "worst_case_risk": round(worst_case, 3),
        "recommended_scenario": _recommended_scenario(verdict),
        "exec_confidence": exec_conf
    }


def _recommended_scenario(verdict):
    mapping = {
        EXECUTE: "execute_now",
        ADVISORY: "execute_now",
        DEFER: "defer_30min",
        CONSTRAIN: "constrain_and_execute",
        ESCALATE: "escalate_then_execute",
        HALT: "reject"
    }
    return mapping.get(verdict, "defer_30min")


# ── Override level ────────────────────────────────────────────────────────────

def override_level(verdict, exec_conf, override_allowed, policies):
    if not override_allowed:
        return "DISABLED"
    override_policy = policies.get("override_policy", {})
    low_max = override_policy.get("low_risk_max", 0.25)
    medium_max = override_policy.get("medium_risk_max", 0.50)

    if verdict == HALT:
        return "DISABLED"
    if verdict == ESCALATE and not override_allowed:
        return "DISABLED"
    conf_risk = 1.0 - exec_conf
    if conf_risk <= low_max:
        return "ALLOWED"
    if conf_risk <= medium_max:
        return "ALLOWED_WITH_REASON"
    return "CONDITIONAL"


# ── Escalation targets ────────────────────────────────────────────────────────

def compute_escalation_targets(args, verdict, policies):
    targets = []
    if verdict in (ESCALATE, HALT):
        targets.append("human_operator")
    if args.behavioral_anomaly > 0.70:
        targets.append("security_review")
    if args.scope in ("production", "external_service"):
        targets.append("ops_team")
    if args.cascade_potential > 0.70:
        targets.append("downstream_system_owners")

    escalation_policy = policies.get("escalation_policy", {})
    registered = escalation_policy.get("escalation_targets", [])
    for t in registered:
        if t not in targets:
            targets.append(t)

    return targets


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    args = parse_args()
    policies = load_policies()

    ir, sr, ad = derive_scores(args, policies)
    exec_conf = compute_exec_confidence(
        ir, sr, args.uncertainty, ad,
        args.cascade_potential, args.behavioral_anomaly, args.policy_compliance
    )

    verdict, delay_min, constraints, override_ok, flags, rules = \
        evaluate_control(args, policies, ir, sr, ad, exec_conf)

    ol = override_level(verdict, exec_conf, override_ok, policies)
    escalation_targets = compute_escalation_targets(args, verdict, policies)
    decision_id = f"AGC-{uuid.uuid4().hex[:8].upper()}"

    # ── Simulate format ───────────────────────────────────────────────────────
    if args.output_format == "simulate":
        simulation = generate_simulation(args, ir, sr, ad, exec_conf, verdict)
        print(json.dumps({
            "decision_id": decision_id,
            "verdict": verdict,
            "simulation": simulation
        }, indent=2))
        return

    # ── Compact format ────────────────────────────────────────────────────────
    if args.output_format == "compact":
        verdict_str = verdict
        if verdict == DEFER and delay_min:
            verdict_str = f"DEFER {delay_min}min"
        elif verdict == CONSTRAIN and constraints:
            verdict_str = f"CONSTRAIN ({constraints})"

        flag_str = " · ".join(flags) if flags else "clean"

        compact = {
            "decision_id": decision_id,
            "verdict": verdict_str,
            "override": ol,
            "flags": flags,
            "flag_str": flag_str,
            "exec_confidence": round(exec_conf, 3),
            "irreversibility_risk": round(ir, 3),
            "scope_risk": round(sr, 3),
            "authorization_deficit": round(ad, 3),
            "rules": rules,
        }
        print(json.dumps(compact))
        return

    # ── Full format ───────────────────────────────────────────────────────────
    simulation = generate_simulation(args, ir, sr, ad, exec_conf, verdict)
    agent_panel = compute_agent_panel(args, verdict, ir, sr, ad)

    result = {
        "decision_id": decision_id,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "input": {
            "action_type": args.action_type,
            "reversibility": args.reversibility,
            "scope": args.scope,
            "agent_id": args.agent_id,
            "urgency": args.urgency,
            "authorized": bool_arg(args.authorized),
            "context": args.context,
        },
        "risk_scores": {
            "irreversibility_risk": round(ir, 3),
            "scope_risk": round(sr, 3),
            "uncertainty_score": round(args.uncertainty, 3),
            "authorization_deficit": round(ad, 3),
            "cascade_risk": round(args.cascade_potential, 3),
            "behavioral_anomaly": round(args.behavioral_anomaly, 3),
            "policy_compliance_violation": round(args.policy_compliance, 3),
        },
        "exec_confidence": round(exec_conf, 3),
        "control_decision": {
            "verdict": verdict,
            "delay_minutes": delay_min,
            "constraints": constraints,
            "override_status": ol,
            "risk_flags": flags,
            "policy_rules_triggered": rules,
        },
        "simulation": simulation,
        "agent_panel": agent_panel,
        "escalation_targets": escalation_targets,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
