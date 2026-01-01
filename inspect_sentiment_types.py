import json
from pathlib import Path
data = json.loads(Path("/opt/quant_system_clean/runtime/news_articles_cache.json").read_text())
articles = list(data["articles"].values())
print([type(a.get("sentiment")) for a in articles])
print([a.get("sentiment") for a in articles])
