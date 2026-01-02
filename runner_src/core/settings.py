from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Optional, List

def _get_env(name: str) -> Optional[str]:
    v = os.getenv(name)
    if v is None:
        return None
    v = v.strip()
    return v if v else None

def _split_csv(v: Optional[str]) -> List[str]:
    if not v:
        return []
    parts = [p.strip() for p in v.split(',')]
    return [p for p in parts if p]

@dataclass(frozen=True)
class Settings:
    # OANDA
    oanda_api_key: Optional[str]
    oanda_account_id: Optional[str]
    oanda_env: str  # practice|live

    # TELEGRAM
    telegram_bot_token: Optional[str]
    telegram_chat_id: Optional[str]

    # NEWS / DATA
    newsapi_api_key: Optional[str]
    marketaux_keys: List[str]
    alphavantage_api_key: Optional[str]

    # AI Insights (OpenAI)
    openai_api_key: Optional[str]
    openai_model: str
    ai_insights_enabled: bool
    ai_insights_mode: str

    # AI Insights (Gemini/Google)
    google_api_key: Optional[str]
    gemini_model: str

    # AI Provider Routing
    ai_provider: str
    ai_provider_chain: List[str]

    def require_oanda(self) -> None:
        if not self.oanda_api_key:
            raise RuntimeError("Missing OANDA_API_KEY")
        if not self.oanda_account_id:
            raise RuntimeError("Missing OANDA_ACCOUNT_ID")

    def telegram_configured(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)

    def require_telegram(self) -> None:
        if not self.telegram_configured():
            raise RuntimeError("Missing TELEGRAM_BOT_TOKEN and/or TELEGRAM_CHAT_ID")

    def require_openai(self) -> None:
        if not self.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required when using OpenAI AI insights")

    def require_gemini(self) -> None:
        if not self.google_api_key:
            raise RuntimeError("GOOGLE_API_KEY (or GEMINI_API_KEY) is required when using Gemini AI insights")

def load_settings() -> Settings:
    # Keep env var NAMES stable; accept minimal aliases for backwards compatibility.
    oanda_api_key = _get_env("OANDA_API_KEY")
    oanda_account_id = _get_env("OANDA_ACCOUNT_ID")
    oanda_env = (_get_env("OANDA_ENV") or "practice").lower()
    if oanda_env not in ("practice", "live"):
        # fail-closed with a clear message (but no secret values).
        raise RuntimeError("OANDA_ENV must be 'practice' or 'live'")

    telegram_bot_token = _get_env("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = _get_env("TELEGRAM_CHAT_ID")

    newsapi_api_key = _get_env("NEWSAPI_API_KEY")

    # MarketAux: support MARKETAUX_KEYS (csv) and legacy MARKETAUX_KEY (single).
    marketaux_csv = _get_env("MARKETAUX_KEYS")
    marketaux_single = _get_env("MARKETAUX_KEY")
    marketaux_keys = _split_csv(marketaux_csv) or ([marketaux_single] if marketaux_single else [])

    alphavantage_api_key = _get_env("ALPHAVANTAGE_API_KEY")

    # AI Insights (OpenAI)
    openai_api_key = _get_env("OPENAI_API_KEY")
    openai_model = _get_env("OPENAI_MODEL") or "gpt-4o-mini"
    ai_insights_enabled = _get_env("AI_INSIGHTS_ENABLED") == "1"
    ai_insights_mode = _get_env("AI_INSIGHTS_MODE") or "advisory"

    # AI Insights (Gemini/Google)
    google_api_key = _get_env("GOOGLE_API_KEY") or _get_env("GEMINI_API_KEY")
    gemini_model = _get_env("GEMINI_MODEL") or "gemini-1.5-flash"

    # AI Provider Routing
    ai_provider = (_get_env("AI_PROVIDER") or "openai").lower()
    ai_provider_chain_raw = _get_env("AI_PROVIDER_CHAIN")
    ai_provider_chain = (
        [p.strip().lower() for p in ai_provider_chain_raw.split(',') if p.strip()]
        if ai_provider_chain_raw
        else [ai_provider]
    )

    return Settings(
        oanda_api_key=oanda_api_key,
        oanda_account_id=oanda_account_id,
        oanda_env=oanda_env,
        telegram_bot_token=telegram_bot_token,
        telegram_chat_id=telegram_chat_id,
        newsapi_api_key=newsapi_api_key,
        marketaux_keys=marketaux_keys,
        alphavantage_api_key=alphavantage_api_key,
        openai_api_key=openai_api_key,
        openai_model=openai_model,
        ai_insights_enabled=ai_insights_enabled,
        ai_insights_mode=ai_insights_mode,
        google_api_key=google_api_key,
        gemini_model=gemini_model,
        ai_provider=ai_provider,
        ai_provider_chain=ai_provider_chain,
    )

# Canonical singleton
settings = load_settings()
