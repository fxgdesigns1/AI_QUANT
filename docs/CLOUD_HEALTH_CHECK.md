Cloud health check
==================

Purpose
- Quickly verify connectivity and reachability of cloud endpoints used by the trading system.
- Produce a machine-readable health summary suitable for automation.

Prerequisites
- Python 3.x
- PyYAML (optional if you want to customize endpoints via YAML config)
- The script uses default endpoints if no config is provided.

Usage
- Run locally or on your cloud host:
  ```bash
  python3 scripts/health_check_cloud.py
  ```
- Optionally override the config file path via environment variable CLOUD_HEALTH_CONFIG:
  ```bash
  CLOUD_HEALTH_CONFIG=/path/to/your/config.yaml python3 scripts/health_check_cloud.py
  ```
- A sample config (YAML) can be placed at:
  - `config/cloud_health_config.yaml`
  Example:
  ```yaml
  endpoints:
    - name: AWS
      host: ec2.amazonaws.com
      port: 443
    - name: GCP
      host: www.googleapis.com
      port: 443
  http_test_url: "https://your-internal-health.local/health"
  ```

Output
- The script prints a JSON object with:
  - timestamp
  - endpoints: for each endpoint, fields: host, port, reachable (bool), latency_ms (int|null)
- If http_test_url is configured, includes http_test with http_status and latency_ms.

Notes
- The health check is lightweight and designed to run in CI/CD pipelines or as a quick diagnostic on deployment targets.
- If you need more endpoints or deeper checks (e.g., API-specific health endpoints), extend the config and the script accordingly.





























