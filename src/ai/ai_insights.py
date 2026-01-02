from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional, Tuple, List

from src.core.settings import settings

# Advisory-only AI insights router.
# - Never blocks execution.
# - Never prints secrets.
# - Uses provider chain with failover.

DEFAULT_TIMEOUT_S = 12


def _now_ms() -> int:
    return int(time.time() * 1000)


def _safe_err(e: Exception) -> str:
    # Never include environment variables or request payloads in errors.
    return f"{type(e).__name__}: {str(e)[:200]}"


def _build_prompt(context: Dict[str, Any]) -> str:
    # Keep it short + structured. The trading system should pass already-sanitized context.
    # DO NOT include secrets in context.
    j = json.dumps(context, ensure_ascii=False)
    return (
        "You are an FX trading assistant. Provide advisory-only insight. "
        "Return concise bullet points:\n"
        "- Market regime / key drivers\n"
        "- Risk flags\n"
        "- Suggested bias (LONG/SHORT/FLAT) + confidence (0-1)\n"
        "- What data is missing\n\n"
        f"Context JSON: {j}"
    )


def _call_openai(prompt: str, timeout_s: int = DEFAULT_TIMEOUT_S) -> str:
    settings.require_openai()

    # Lazy import to avoid dependency unless used
    try:
        from openai import OpenAI
    except Exception as e:
        raise RuntimeError("OpenAI SDK not installed. Install: pip install openai") from e

    client = OpenAI(api_key=settings.openai_api_key)
    model = settings.openai_model

    # Use a small, safe token budget.
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are concise and risk-aware."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=350,
        timeout=timeout_s,
    )
    return (resp.choices[0].message.content or "").strip()


def _call_gemini(prompt: str, timeout_s: int = DEFAULT_TIMEOUT_S) -> str:
    settings.require_gemini()

    # Lazy import to avoid dependency unless used
    try:
        from google import genai
    except Exception as e:
        raise RuntimeError(
            "Gemini SDK not installed. Install: pip install google-genai"
        ) from e

    client = genai.Client(api_key=settings.google_api_key)
    
    # Normalize model name: strip "models/" prefix if present, default to gemini-2.0-flash-lite
    model_name = settings.gemini_model or "gemini-2.0-flash-lite"
    if model_name.startswith("models/"):
        model_name = model_name[7:]  # Strip "models/" prefix
    
    # Use google-genai API: client.models.generate_content
    resp = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config={
            "temperature": 0.2,
            "max_output_tokens": 400,
        },
    )
    
    # Extract text safely: prefer resp.text, fallback to candidates structure
    text = getattr(resp, "text", None)
    if text is None:
        # fall back to candidate extraction if needed
        try:
            text = resp.candidates[0].content.parts[0].text
        except (AttributeError, IndexError, KeyError):
            text = ""
    return (text or "").strip()


def get_ai_insight(context: Dict[str, Any]) -> Tuple[Optional[str], Dict[str, Any]]:
    """Return (insight_text_or_none, meta).

    meta fields are safe for logs (no secrets):
      - enabled, mode, providers_tried, provider_used, latency_ms, error

    Advisory-only: caller must not treat this as an execution directive.
    """

    enabled = bool(settings.ai_insights_enabled)
    mode = (settings.ai_insights_mode or "advisory").lower()

    meta: Dict[str, Any] = {
        "enabled": enabled,
        "mode": mode,
        "providers_tried": [],
        "provider_used": None,
        "latency_ms": None,
        "error": None,
    }

    if not enabled:
        return None, meta

    # Guardrail: only advisory supported in this system
    if mode not in ("advisory",):
        meta["error"] = f"unsupported_mode:{mode}"
        return None, meta

    prompt = _build_prompt(context)

    chain: List[str] = settings.ai_provider_chain or [settings.ai_provider]
    chain = [c.lower().strip() for c in chain if c.strip()]
    if not chain:
        chain = ["openai"]

    t0 = _now_ms()

    last_err: Optional[str] = None
    for provider in chain:
        meta["providers_tried"].append(provider)
        try:
            if provider in ("openai", "oai"):
                out = _call_openai(prompt)
            elif provider in ("gemini", "google"):
                out = _call_gemini(prompt)
            else:
                raise ValueError(f"unknown_provider:{provider}")

            meta["provider_used"] = provider
            meta["latency_ms"] = _now_ms() - t0
            return (out if out else None), meta

        except Exception as e:
            last_err = _safe_err(e)
            # Fail-soft for advisory: continue to next provider
            continue

    meta["latency_ms"] = _now_ms() - t0
    meta["error"] = last_err or "all_providers_failed"
    return None, meta
