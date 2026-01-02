import os
import time
import hashlib

from src.core.settings import settings


def mark(v: str) -> str:
    return "SET" if (v is not None and str(v).strip() != "") else "MISSING"


def main() -> None:
    print("AI_INSIGHTS_ENABLED:", "ON" if settings.ai_insights_enabled else "OFF")
    print("AI_INSIGHTS_MODE:", settings.ai_insights_mode)
    print("OPENAI_API_KEY:", mark(settings.openai_api_key or ""))
    print("OPENAI_MODEL:", settings.openai_model or "MISSING")

    # Optional: hashed prefix only (not reversible) to confirm key changed without revealing it
    if settings.openai_api_key:
        h = hashlib.sha256(settings.openai_api_key.encode()).hexdigest()[:12]
        print("OPENAI_API_KEY_SHA256_PREFIX:", h)

    # If disabled, stop here.
    if not settings.ai_insights_enabled:
        print("OK: AI insights disabled; nothing to call")
        return

    # If enabled, do a tiny import check (no network call by default).
    from src.ai.ai_insights import get_ai_insight
    print("OK: imported get_ai_insight")

    # Optional network call only if explicit flag set.
    if os.getenv("AI_INSIGHTS_CALL_SMOKE", "0") == "1":
        ctx = {"instrument": "EUR_USD", "price": "1.0000", "note": "smoke"}
        t0 = time.time()
        r = get_ai_insight(ctx)
        dt = time.time() - t0
        print("OK: AI call returned (summary_len):", len(r.summary or ""), "seconds:", round(dt, 2))


if __name__ == "__main__":
    main()
