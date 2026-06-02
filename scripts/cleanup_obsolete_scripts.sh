#!/bin/bash
# Cleanup Obsolete Scripts - One-time fixes, audits, and redundant verification scripts
# SAFE: Only removes scripts that are clearly one-time fixes or duplicates

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Create backup directory first
BACKUP_DIR="../.BACKUPS/scripts_cleanup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "📦 Backing up scripts to: $BACKUP_DIR"

# List of obsolete scripts to remove (one-time fixes, audits, redundant verifications)
OBSOLETE=(
    # One-time deployment fixes
    "deploy_active_trades_fix.sh"
    "deploy_all_fixes_safe.sh"
    "deploy_multi_strategy_4_accounts.sh"
    "deploy_vm_end_to_end.sh"
    
    # One-time audits
    "audit_authenticated_browser.py"
    "audit_cloud_readiness_complete.sh"
    "audit_dashboard_brutal_truth.py"
    "audit_vm_phases.sh"
    
    # One-time dashboard verification/fixes
    "verify_dashboard_fixes.py"
    "verify_dashboard_now.py"
    "verify_dashboard_compat.sh"
    "verify_dashboard_and_trades.sh"
    "verify_browser_fixes.py"
    "comprehensive_dashboard_audit.py"
    "comprehensive_playwright_audit.py"
    "brutal_truth_playwright_verification.py"
    "dashboard_probe.py"
    "dashboard_truth_probe.sh"
    "probe_dashboard_backend.py"
    "repair_dashboard_flow.py"
    "final_verification_dashboard.py"
    
    # One-time verification scripts
    "verify_alpha_e2e.sh"
    "verify_alpha_strategy_inputs.sh"
    "verify_truth_only_dashboard.sh"
    "verify_truth_only_news.sh"
    "verify_ai_insights_no_leak.py"
    "verify_ai_providers_no_leak.py"
    "verify_env_no_leak.py"
    "verify_m13_price_sanity.py"
    "verify_price_sanity_and_tp_fix.sh"
    "verify_strategy_independence.py"
    "test_strategy_independence.py"
    "test_endpoints_once_connected.py"
    
    # One-time assignments/config
    "assign_5_strategies_to_5_accounts.sh"
    "update_config_quality_mode.py"
    "autonomy_signoff.py"
    "update_md_probe_results.py"
    
    # One-time test/debug scripts
    "force_one_cycle_paper.sh"
    "resume_paper.sh"
    "complete_restart_and_verify.sh"
    "local_run_and_verify.sh"
    "local_preflight.sh"
    "bringup_local_full.sh"
    "connect_and_verify.sh"
    "verify_all_local.sh"
    "verify_vm_full_stack.sh"
    
    # Redundant VM bootstrap (if provision_vm.sh covers it)
    "vm_bootstrap_control_plane.sh"
    "vm_bootstrap_deploy_verify.sh"
    "vm_deploy_gated.sh"
    
    # Redundant notification (if telegram_health_check.py covers it)
    "notify_status_telegram.py"
    
    # Redundant system probe (keep system_probe.py, remove full)
    "system_probe_full.py"
)

# Move obsolete scripts to backup
for script in "${OBSOLETE[@]}"; do
    if [ -f "$script" ]; then
        echo "  → Moving $script to backup"
        mv "$script" "$BACKUP_DIR/"
    fi
done

echo ""
echo "✅ Cleanup complete. Removed ${#OBSOLETE[@]} obsolete scripts."
echo "📦 Backup location: $BACKUP_DIR"
echo ""
echo "Remaining essential scripts:"
ls -1 *.sh *.py 2>/dev/null | sort
