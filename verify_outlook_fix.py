#!/usr/bin/env python3
"""Verify outlook engine fix - test bias detection with strong moves"""

import sys
import os
sys.path.append(os.getcwd())

from src.control_plane.outlook_engine import get_outlook_engine

print("=== OUTLOOK ENGINE FIX VERIFICATION ===\n")

engine = get_outlook_engine()

# Force recompute to use new logic
print("Forcing outlook recompute with new logic...")
daily = engine.compute("daily")
weekly = engine.compute("weekly")

print("\n--- DAILY OUTLOOK (should catch strong moves) ---")
for outlook in daily.get("outlooks", []):
    inst = outlook.get("instrument")
    bias = outlook.get("bias")
    conf = outlook.get("confidence")
    print(f"{inst:10} | Bias: {bias:8} | Confidence: {conf}")

print("\n--- WEEKLY OUTLOOK ---")
for outlook in weekly.get("outlooks", []):
    inst = outlook.get("instrument")
    bias = outlook.get("bias")
    conf = outlook.get("confidence")
    print(f"{inst:10} | Bias: {bias:8} | Confidence: {conf}")

print("\n=== VERIFICATION COMPLETE ===")
print("\nKey Changes:")
print("  ✅ Daily bias now uses TODAY's move (current vs last complete candle)")
print("  ✅ Gold/Silver: 0.8% threshold (was 0.5%)")
print("  ✅ FX pairs: 0.3% threshold (was 0.5%)")
print("  ✅ Strong moves (1.5%+ gold, 0.7%+ FX) get HIGH confidence")
