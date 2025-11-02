import json
import threading
from pathlib import Path

DEFAULT_PARAMS = {
    "EUR_USD": {"k_atr": 1.25, "ema": 50, "atr": 14, "tp_mult": 1.3, "sl_mult": 0.5},
    "GBP_USD": {"k_atr": 1.25, "ema": 50, "atr": 14, "tp_mult": 1.3, "sl_mult": 0.5},
    "AUD_USD": {"k_atr": 1.25, "ema": 50, "atr": 14, "tp_mult": 1.3, "sl_mult": 0.5},
    "USD_JPY": {"k_atr": 1.00, "ema": 50, "atr": 14, "tp_mult": 1.6, "sl_mult": 0.4},
    "XAU_USD": {"k_atr": 1.50, "ema": 50, "atr": 14, "tp_mult": 1.0, "sl_mult": 0.5},
}


class AdaptiveStore:
    def __init__(self, path: str = "/opt/quant_system_clean/adaptive_params.json") -> None:
        self._path = Path(path)
        self._lock = threading.Lock()
        self._params = DEFAULT_PARAMS.copy()
        self._load()

    def _load(self) -> None:
        try:
            if self._path.exists():
                data = json.loads(self._path.read_text())
                if isinstance(data, dict):
                    for k, v in data.items():
                        if isinstance(v, dict):
                            self._params.setdefault(k, {}).update(v)
        except Exception:
            # Safe fallback to defaults
            pass

    def _save(self) -> None:
        try:
            self._path.write_text(json.dumps(self._params, indent=2))
        except Exception:
            pass

    def get(self, instrument: str) -> dict:
        return self._params.get(instrument, DEFAULT_PARAMS.get(instrument, DEFAULT_PARAMS["EUR_USD"]))

    def set_param(self, instrument: str, key: str, value) -> None:
        with self._lock:
            self._params.setdefault(instrument, {}).update({key: value})
            self._save()


