import sys
sys.path.insert(0, "/opt/quant_system_clean")
from news_manager import NewsManager
n = NewsManager()
print(n.fetch_sentiment(window_minutes=60))
