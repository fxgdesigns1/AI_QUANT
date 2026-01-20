#!/usr/bin/env python3
"""
Offline Training Job - Session Regime Policy Generation

Analyzes audit log to generate policy participation scores.
Offline-only: No runtime dependency. Manual execution required.
"""

import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, Any


AUDIT_PATH = Path("logs/session_regime_gate_audit.jsonl")
OUTPUT_PATH = Path("data/policies/session_regime_policy.json")
THRESHOLD = 0.6


def train_policy_from_audit_log() -> Dict[str, Any]:
    """
    Analyze audit log and generate policy participation scores.
    
    Returns:
        Dictionary mapping policy keys to participation scores
    """
    if not AUDIT_PATH.exists():
        print(f"⚠️  Audit log not found: {AUDIT_PATH}")
        return {}
    
    # Collect statistics by policy key
    stats = defaultdict(lambda: {"count": 0, "wins": 0})
    
    try:
        with AUDIT_PATH.open("r") as f:
            for line_num, line in enumerate(f, 1):
                if not line.strip():
                    continue
                
                try:
                    r = json.loads(line)
                    # Generate policy key: session|regime|news_state|bias_alignment
                    session = r.get("session", "unknown")
                    regime = r.get("regime", "UNKNOWN")
                    news_state = r.get("news_state", "normal")
                    # Use roadmap_aligned for bias_alignment
                    bias_alignment = "aligned" if r.get("roadmap_aligned", False) else "misaligned"
                    
                    key = f"{session}|{regime}|{news_state}|{bias_alignment}"
                    
                    stats[key]["count"] += 1
                    if r.get("allowed", False):
                        stats[key]["wins"] += 1
                        
                except json.JSONDecodeError as e:
                    print(f"⚠️  Skipping invalid JSON at line {line_num}: {e}")
                    continue
    
    except Exception as e:
        print(f"❌ Error reading audit log: {e}")
        return {}
    
    # Generate policies from statistics
    policies = {}
    for key, stat in stats.items():
        count = stat["count"]
        wins = stat["wins"]
        score = wins / max(1, count)  # Avoid division by zero
        
        policies[key] = {
            "participation_score": round(score, 3),
            "enabled": score >= THRESHOLD,
            "count": count,
            "wins": wins,
            "threshold": THRESHOLD,
        }
    
    return policies


def main():
    """Main training function"""
    print("📊 Training session regime policy from audit log...")
    
    policies = train_policy_from_audit_log()
    
    if not policies:
        print("❌ No policies generated (check audit log)")
        return
    
    # Ensure output directory exists
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Write policies to JSON file
    output_data = {
        "policies": policies,
        "threshold": THRESHOLD,
        "total_policies": len(policies),
        "enabled_policies": sum(1 for p in policies.values() if p.get("enabled", False)),
    }
    
    OUTPUT_PATH.write_text(json.dumps(output_data, indent=2))
    
    print(f"✅ Generated {len(policies)} policies")
    print(f"   Enabled: {output_data['enabled_policies']}")
    print(f"   Output: {OUTPUT_PATH}")
    
    # Print summary
    print("\n📋 Policy Summary:")
    for key, policy in sorted(policies.items()):
        status = "✅" if policy["enabled"] else "❌"
        print(f"   {status} {key}: {policy['participation_score']:.3f} ({policy['wins']}/{policy['count']})")


if __name__ == "__main__":
    main()
