#!/usr/bin/env python3
"""
PRE-DEPLOYMENT CHECKLIST
Runs ALL verifications before allowing deployment
MANDATORY - DO NOT SKIP
"""

import sys
import subprocess
import os
from datetime import datetime

def run_check(name, command, critical=True):
    """Run a check and return result"""
    print(f"\n{'='*70}")
    print(f"🔍 {name}")
    print(f"{'='*70}")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        
        if result.returncode == 0:
            print(f"✅ {name} - PASSED")
            return True
        else:
            if critical:
                print(f"❌ {name} - FAILED (CRITICAL)")
            else:
                print(f"⚠️  {name} - FAILED (NON-CRITICAL)")
            return not critical
    except Exception as e:
        print(f"❌ {name} - ERROR: {e}")
        return not critical


def main():
    """Run all pre-deployment checks"""
    
    print("\n" + "="*70)
    print("PRE-DEPLOYMENT CHECKLIST")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    checks_passed = []
    
    # 1. Verify scanner matches config
    checks_passed.append(
        run_check(
            "Scanner Configuration Match",
            "python3 verify_scanner_config.py",
            critical=True
        )
    )
    
    # 2. Check for syntax errors
    checks_passed.append(
        run_check(
            "Python Syntax Check",
            "python3 -m py_compile src/core/candle_based_scanner.py",
            critical=True
        )
    )
    
    # 3. Verify strategy files exist
    checks_passed.append(
        run_check(
            "Strategy Files Exist",
            "ls src/strategies/gold_scalping.py src/strategies/ultra_strict_forex.py src/strategies/momentum_trading.py src/strategies/gbp_usd_optimized.py",
            critical=True
        )
    )
    
    # 4. Check .gcloudignore exists
    checks_passed.append(
        run_check(
            ".gcloudignore File Exists",
            "test -f .gcloudignore && echo '✅ .gcloudignore found'",
            critical=True
        )
    )
    
    # 5. Verify large files are excluded
    checks_passed.append(
        run_check(
            "Large Files Check",
            "grep -q '^logs/$' .gcloudignore && grep -q '^node_modules/$' .gcloudignore && echo '✅ Large files excluded in .gcloudignore'",
            critical=True
        )
    )
    
    # 6. Check accounts.yaml is valid
    checks_passed.append(
        run_check(
            "accounts.yaml Validation",
            "python3 -c \"import yaml; yaml.safe_load(open('accounts.yaml'))\" && echo '✅ accounts.yaml is valid YAML'",
            critical=True
        )
    )
    
    # 7. Verify no hardcoded strategy calls
    checks_passed.append(
        run_check(
            "No Hardcoded Strategy Calls",
            "! grep -q 'get_aud_usd_high_return_strategy\\|get_eur_usd_safe_strategy\\|get_multi_strategy_portfolio' src/core/candle_based_scanner.py && echo '✅ No old hardcoded strategies found'",
            critical=True
        )
    )
    
    # Final summary
    print("\n" + "="*70)
    print("CHECKLIST SUMMARY")
    print("="*70)
    
    total = len(checks_passed)
    passed = sum(checks_passed)
    
    print(f"\nChecks passed: {passed}/{total}")
    
    if all(checks_passed):
        print("\n✅ ALL CHECKS PASSED - DEPLOYMENT APPROVED")
        print("\nYou can now deploy with:")
        print("  gcloud app deploy --version=<version-name> --quiet")
        print("="*70)
        return 0
    else:
        print("\n❌ SOME CHECKS FAILED - DEPLOYMENT BLOCKED")
        print("\nFix the issues above before deploying!")
        print("="*70)
        return 1


if __name__ == "__main__":
    sys.exit(main())

