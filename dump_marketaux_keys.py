import json
from pathlib import Path
p = Path("/opt/quant_system_clean/runtime/marketaux_usage.json")
if p.exists():
    data = json.loads(p.read_text())
    keys = [k.get("key") for k in data.get("keys", []) if k.get("key")]
    print("keys", len(keys))
    for k in keys:
        print(k)
else:
    print("file missing")
