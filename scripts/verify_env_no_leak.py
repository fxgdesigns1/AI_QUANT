import os
from src.core.settings import settings

def mark(v):
    return "SET" if v else "MISSING"

print("OANDA_API_KEY:", mark(settings.oanda_api_key))
print("OANDA_ACCOUNT_ID:", mark(settings.oanda_account_id))
print("OANDA_ENV:", settings.oanda_env)
print("TELEGRAM_BOT_TOKEN:", mark(settings.telegram_bot_token))
print("TELEGRAM_CHAT_ID:", mark(settings.telegram_chat_id))
print("NEWSAPI_API_KEY:", mark(settings.newsapi_api_key))
print("MARKETAUX_KEYS:", "SET" if settings.marketaux_keys else "MISSING")
print("ALPHAVANTAGE_API_KEY:", mark(settings.alphavantage_api_key))
