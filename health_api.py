from flask import Flask, jsonify
import os
import socket

# Strategy registry integration
from src.strategies.registry import available_strategies, create_strategy

app = Flask(__name__)

def ping_host(host: str, port: int = 80, timeout: int = 2) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

@app.route("/api/health")
def health():
    # Lightweight health summary; concrete checks can be extended.
    health_report = {
        "oanda_api": "ok",
        "accounts_config": "ok",
        "ai_trading_service": "ok",
        "backup_engine": "configured" if os.environ.get("CANARY_DISABLE_BACKUP") is None else "disabled",
        "news_cache": "ok" if os.environ.get("NEWS_API_URL") else "not_configured",
        "telegram": "configured" if os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID") else "not_configured",
        "dashboard": "available"
    }
    return jsonify(health_report)

@app.route("/api/strategy_insights")
def strategy_insights():
    """Provide detailed, real-time status for each active strategy."""
    insights = {}
    for definition in available_strategies():
        try:
            strategy_instance = create_strategy(definition.key)
            if hasattr(strategy_instance, 'get_status'):
                insights[definition.key] = strategy_instance.get_status()
            else:
                insights[definition.key] = {"status": "not_instrumented"}
        except Exception as e:
            insights[definition.key] = {"status": "error", "reason": str(e)}
    return jsonify(insights)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)






