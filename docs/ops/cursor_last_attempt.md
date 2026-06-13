 M .gitignore
 M dashboard/control_plane.html
 M runner_src/core/execution_gate.py
 M scripts/push_repo_to_vm.sh
 M src/control_plane/api.py
 M src/control_plane/schema.py
 M src/control_plane/status_snapshot.py
 M src/control_plane/strategy_registry.py
 M src/core/dynamic_account_manager.py
 M src/core/execution_gate.py
 M src/core/order_manager.py
 M src/core/paper_broker.py
 M src/core/settings.py
 M src/strategies/momentum_trading.py
 M templates/forensic_command.html
 M working_trading_system.py
?? .BACKUPS/
?? HOW_TO_RUN.md
?? MULTI_STRATEGY_DEPLOYMENT_COMPLETE.md
?? XAU_USD_IMPLEMENTATION_COMPLETE.md
?? alpha_dashboard.png
?? analyze_gold_now.py
?? beta_dashboard.png
?? deploy/
?? docs/SYSTEM_STATUS_AND_PLAN_2026.md
?? docs/blueprints/
?? docs/ops/
?? docs/runbooks/CLOUD_DEPLOY_FULL.md
?? docs/runbooks/READY_TO_EXECUTE_PAPER.md
?? docs/runbooks/RUNNER_AND_ACCOUNTS.md
?? gold_analysis_report.md
?? sandbox/
?? scripts/backup/system_replication_backup.sh
?? scripts/bringup_local_full.sh
?? scripts/deploy_multi_strategy_4_accounts.sh
?? scripts/env_sanity_check.py
?? scripts/env_sanity_fix.py
?? scripts/force_one_cycle_paper.sh
?? scripts/install_git_filter_repo.sh
?? scripts/local_preflight.sh
?? scripts/local_run_and_verify.sh
?? scripts/preopen_gate_check.sh
?? scripts/provision_vm.sh
?? scripts/retention_cleanup.sh
?? scripts/start_runner_clean.sh
?? scripts/systemd/ai-quant-control-plane.service
?? scripts/systemd/ai-quant-dns-healthcheck.service
?? scripts/systemd/ai-quant-dns-healthcheck.timer
?? scripts/systemd/ai-quant-preopen-gate.service
?? scripts/systemd/ai-quant-preopen-gate.timer
?? scripts/systemd/ai-quant-retention.service
?? scripts/systemd/ai-quant-retention.timer
?? scripts/systemd/ai-quant-runner.service
?? scripts/systemd/install_units.sh
?? scripts/verify_live_prices.sh
?? scripts/verify_paper_readiness.sh
?? scripts/verify_telegram.sh
?? scripts/verify_vm_full_stack.sh
?? src/control_plane/macro_provider.py
?? src/control_plane/market_data_provider.py
?? src/control_plane/news_provider.py
?? src/control_plane/snapshot_store.py
?? src/control_plane/telegram_notifier.py
?? systemd/ai-quant-dns-healthcheck.service
?? systemd/ai-quant-dns-healthcheck.timer
?? systemd/ai-quant-preopen-gate.service
?? systemd/ai-quant-preopen-gate.timer
?? systemd/ai-quant-report-daily.service.template
?? systemd/ai-quant-report-daily.timer
?? systemd/ai-quant-report-monthly.service.template
?? systemd/ai-quant-report-monthly.timer
?? systemd/ai-quant-report-weekly.service.template
?? systemd/ai-quant-report-weekly.timer
?? systemd/ai-quant-retention.service
?? systemd/ai-quant-retention.timer

=== DIFF STAT ===
 .gitignore                             |    7 +
 dashboard/control_plane.html           |  130 +++-
 runner_src/core/execution_gate.py      |   67 +-
 scripts/push_repo_to_vm.sh             |    2 +
 src/control_plane/api.py               | 1109 +++++++++++++++++++++++++++++++-
 src/control_plane/schema.py            |   65 +-
 src/control_plane/status_snapshot.py   |   50 +-
 src/control_plane/strategy_registry.py |   85 +++
 src/core/dynamic_account_manager.py    |   61 +-
 src/core/execution_gate.py             |  264 +++++++-
 src/core/order_manager.py              |  300 ++++++++-
 src/core/paper_broker.py               |   51 +-
 src/core/settings.py                   |   35 +
 src/strategies/momentum_trading.py     |  128 +++-
 templates/forensic_command.html        |  755 ++++++++++++++++++----
 working_trading_system.py              |  608 ++++++++++++++---
 16 files changed, 3403 insertions(+), 314 deletions(-)
