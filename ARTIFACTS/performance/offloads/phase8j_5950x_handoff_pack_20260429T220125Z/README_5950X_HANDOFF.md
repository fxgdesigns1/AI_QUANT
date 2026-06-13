phase8j_5950x_handoff_pack_20260429T220125Z

This is a compact research-offload handoff pack for the 5950X research estate.
It is evidence-only and does not grant any live permission.

Contents:
- manifest: manifest.json
- checksums: checksums.sha256
- compact source artifacts copied under ARTIFACTS/performance/

Strict rules (non-negotiable):
- Do not place trades
- Do not call broker execution APIs for order placement
- Do not enable NY live execution
- Do not change Send Trade unlock logic
- Do not loosen fail-closed gates
- Do not modify lane 010 manual_only policy
- Do not degrade lane 011 automated paper behavior
- Do not edit runtime/config.yaml
- Do not restart ai-quant-runner
- Do not run heavy backtests on ALPHA
- Do not pull large OANDA historical datasets on ALPHA
- Do not run Monte Carlo or parameter sweeps on ALPHA
- Do not copy huge candle caches back to ALPHA
- Do not copy the entire ARTIFACTS tree blindly

Expected 5950X outputs (compact result pack contract):
- phase8j_replay_summary.json
- phase8j_replay_samples_compact.jsonl
- phase8j_monthly_persistence.json
- phase8j_recommendation.json
- phase8j_run_manifest.json
- checksums.sha256

