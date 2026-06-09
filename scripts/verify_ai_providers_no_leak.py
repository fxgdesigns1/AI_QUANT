#!/usr/bin/env python3
import os
import hashlib
import re

from src.core.settings import settings


def mark(v: str | None) -> str:
    return "SET" if (v is not None and v != "") else "MISSING"


def sha_prefix(v: str | None) -> str:
    if not v:
        return "NA"
    return hashlib.sha256(v.encode()).hexdigest()[:12]


def main() -> None:
    # Never print key values.
    print("AI_INSIGHTS_ENABLED:", os.getenv("AI_INSIGHTS_ENABLED", "0"))
    print("AI_INSIGHTS_MODE:", os.getenv("AI_INSIGHTS_MODE", "advisory"))
    print("AI_PROVIDER:", os.getenv("AI_PROVIDER", "openai"))
    print("AI_PROVIDER_CHAIN:", os.getenv("AI_PROVIDER_CHAIN", ""))

    print("OPENAI_API_KEY:", mark(settings.openai_api_key))
    print("OPENAI_MODEL:", os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    print("OPENAI_API_KEY_SHA256_PREFIX:", sha_prefix(settings.openai_api_key))

    # Accept GOOGLE_API_KEY or GEMINI_API_KEY
    print("GOOGLE_API_KEY:", mark(settings.google_api_key))
    print("GEMINI_MODEL:", os.getenv("GEMINI_MODEL", "gemini-1.5-flash"))
    print("GOOGLE_API_KEY_SHA256_PREFIX:", sha_prefix(settings.google_api_key))

    if os.getenv("AI_INSIGHTS_ENABLED", "0") not in ("1", "true", "True", "YES", "yes"):
        print("OK: AI insights disabled; nothing to call")
        return

    # Optional smoke: do NOT run unless explicitly requested
    if os.getenv("AI_INSIGHTS_CALL_SMOKE", "0") in ("1", "true", "True", "YES", "yes"):
        from src.ai.ai_insights import get_ai_insight

        ctx = {
            "pair": "EUR_USD",
            "price": 1.0,
            "note": "smoke_test",
        }
        insight, meta = get_ai_insight(ctx)
        # Print only safe meta and whether we got any insight.
        print("SMOKE_RESULT_HAS_INSIGHT:", bool(insight))
        print("SMOKE_META:", {k: meta[k] for k in ("providers_tried","provider_used","latency_ms","error")})


if __name__ == "__main__":
    main()
