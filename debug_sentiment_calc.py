import sys
sys.path.insert(0, "/opt/quant_system_clean")
from news_manager import NewsManager
from datetime import datetime, timedelta

n = NewsManager()
window_minutes = 60
window_hours = window_minutes / 60.0
cached_articles = n._get_cached_articles_in_window(max_age_hours=int(window_hours) + 1)
print("cached articles len", len(cached_articles))
cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
total_score = 0.0
total_count = 0
articles_used = 0
for article in cached_articles:
    published_str = article.get("published_at")
    if published_str:
        published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        if published < cutoff:
            continue
    score = article.get("sentiment")
    if isinstance(score, (int, float)):
        total_score += float(score)
        total_count += 1
    articles_used += 1
print(total_count, total_count, articles_used, articles_used)
