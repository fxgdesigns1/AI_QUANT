import json
from pathlib import Path
runtime_path = Path("/opt/quant_system_clean/runtime/marketaux_usage.json")
if runtime_path.exists():
    data = json.loads(runtime_path.read_text())
    keys = [k.get("key") for k in data.get("keys", []) if k.get("key")]
else:
    keys = []
if not keys:
    raise SystemExit("No keys found in runtime usage")
line = "MARKETAUX_KEYS=\"" + ",".join(keys) + "\"\n"
# Append to env file
env_path = Path("/opt/quant_system_clean/google-cloud-trading-system/oanda_config.env")
text = env_path.read_text()
lines = [ln for ln in text.splitlines() if not ln.startswith("MARKETAUX_KEYS=") and not ln.startswith("MARKETAUX_KEY=")]
lines.append(line.strip())
env_path.write_text("\n".join(lines) + "\n")
print("Updated env file with", len(keys), "keys")
