# Phase 8P Replay-Ready Evidence Engine

## Purpose

Phase 8O proved that historical exact replay is blocked when the original
forward context was not archived as a complete record. NewsAPI/current-news
provider state and economic-calendar availability cannot be reconstructed
perfectly after the fact without guessing.

Phase 8P fixes the forward path: future NY `EUR_USD` paper-review rows must be
captured with a self-contained replay snapshot containing trade fields,
news payloads, news assessment, calendar payloads, provider status, source
artifact paths, and a canonical SHA256 hash.

## Safety Contract

Phase 8P is local research and paper-review evidence only.

- NY remains paper-review only.
- No live trading gate is changed.
- No execution endpoint behavior is changed.
- No OANDA order API or MT5 bridge routing is changed.
- No Send Trade unlock behavior is changed.
- No runner restart is required.

## Snapshot Rules

The canonical schema helper is `scripts/local_research/phase8p_replay_snapshot_schema.py`.

Required replay fields:

- `instrument`
- `session_bucket`
- `side`
- `entry`
- `stop_loss`
- `take_profit`

Required context snapshots:

- `news_snapshot`
- `news_assess_snapshot`
- `calendar_snapshot`
- `provider_status_snapshot`

If a provider endpoint is unavailable, the snapshot stores an explicit degraded
object with `http_status`, `error_class`, and `captured_at_utc`. Degraded or
missing context sets `replay_ready_exact=false`.

Secrets, tokens, headers, raw environment values, and credential-looking keys
are redacted before hashing or writing snapshots.

## Replay Loader

The deterministic loader is:

```powershell
python scripts/phase8p_exact_replay_from_archive.py --input ARTIFACTS/performance/pair_session_paper_review_log.jsonl --output ARTIFACTS/performance/latest_phase8p_exact_replay_from_archive.json --strict
```

The loader never calls external APIs. It validates `snapshot_hash` before any
row replay. If future price/outcome evidence is missing, it emits
`REPLAY_BLOCKED_MISSING_OUTCOME_DATA` instead of treating the row as a failed
trade.

## Readiness Artifact

The loader writes:

```text
ARTIFACTS/performance/latest_phase8p_replay_readiness.json
```

Expected fields include:

- `replay_ready_exact_count`
- `replay_not_ready_count`
- `missing_fields_histogram`
- `first_replay_ready_at_utc`
- `latest_replay_ready_at_utc`
- `blocking_reasons`

## Verification

Run:

```powershell
python -m unittest discover -s tests -p "test_phase8*.py" -v
python -m py_compile scripts/phase8p_exact_replay_from_archive.py
python scripts/phase8p_exact_replay_from_archive.py --input ARTIFACTS/performance/pair_session_paper_review_log.jsonl --output ARTIFACTS/performance/latest_phase8p_exact_replay_from_archive.json --strict
python -m json.tool ARTIFACTS/performance/latest_phase8p_exact_replay_from_archive.json
python -m json.tool ARTIFACTS/performance/latest_phase8p_replay_readiness.json
```

If the archive input does not exist yet, the replay output remains structured
and reports `REPLAY_BLOCKED_ARCHIVE_INPUT_MISSING`.
