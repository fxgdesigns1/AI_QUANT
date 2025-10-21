#!/usr/bin/env python3
"""
Direct patch to fix instrument mappings in running system
This modifies the account_manager and dynamic_account_manager in-place
"""
import os
import sys

# Files to patch
files_to_patch = [
    'src/core/account_manager.py',
    'src/core/dynamic_account_manager.py'
]

# Patches to apply
patches = {
    "instruments=['GBP_USD']  # Multi-Portfolio": "instruments=os.getenv('ACCOUNT_008_INSTRUMENTS', 'GBP_USD,NZD_USD,XAU_USD').split(',')",
    "'instruments': ['GBP_USD', 'NZD_USD', 'XAU_USD']": "'instruments': os.getenv('ACCOUNT_008_INSTRUMENTS', 'GBP_USD,NZD_USD,XAU_USD').split(',')",
    "instruments=['GBP_USD', 'XAU_USD']": "instruments=os.getenv('ACCOUNT_007_INSTRUMENTS', 'GBP_USD,XAU_USD').split(',')",
    "'instruments': ['GBP_USD', 'XAU_USD']": "'instruments': os.getenv('ACCOUNT_007_INSTRUMENTS', 'GBP_USD,XAU_USD').split(',')",
    "instruments=['EUR_JPY', 'USD_CAD']": "instruments=os.getenv('ACCOUNT_006_INSTRUMENTS', 'EUR_JPY,USD_CAD').split(',')",
    "'instruments': ['EUR_JPY', 'USD_CAD']": "'instruments': os.getenv('ACCOUNT_006_INSTRUMENTS', 'EUR_JPY,USD_CAD').split(',')",
}

print("🔧 PATCHING INSTRUMENT CONFIGURATIONS...")

for file_path in files_to_patch:
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        continue
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    patched = False
    
    for old, new in patches.items():
        if old in content:
            content = content.replace(old, new)
            patched = True
            print(f"✅ Patched in {file_path}: {old[:50]}...")
    
    if patched:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"✅ Updated: {file_path}")
    else:
        print(f"ℹ️  No changes needed: {file_path}")

print("\n✅ PATCHING COMPLETE!")
print("\nNow set these environment variables in Google Cloud Console:")
print("ACCOUNT_006_INSTRUMENTS=EUR_JPY,USD_CAD")
print("ACCOUNT_007_INSTRUMENTS=GBP_USD,XAU_USD")
print("ACCOUNT_008_INSTRUMENTS=GBP_USD,NZD_USD,XAU_USD")





