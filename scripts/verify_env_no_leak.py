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
print("OPENAI_API_KEY:", mark(settings.openai_api_key or ""))
print("OPENAI_MODEL:", settings.openai_model or "MISSING")
print("AI_INSIGHTS_ENABLED:", "ON" if settings.ai_insights_enabled else "OFF")
print("AI_INSIGHTS_MODE:", settings.ai_insights_mode)
print("AI_PROVIDER:", settings.ai_provider)
print("AI_PROVIDER_CHAIN:", ",".join(settings.ai_provider_chain) if settings.ai_provider_chain else "")
print("GOOGLE_API_KEY:", mark(settings.google_api_key or ""))
print("GEMINI_MODEL:", settings.gemini_model or "MISSING")
