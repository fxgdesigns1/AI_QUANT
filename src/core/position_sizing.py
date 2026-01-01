from dataclasses import dataclass
from typing import Optional

@dataclass
class PositionSizing:
    """
    Minimal PositionSizing shim to satisfy strategy imports.
    This provides a simple, deterministic sizing method used when the
    production sizing module is unavailable. Replace with broker-aware
    logic for live risk-managed sizing.
    """
    default_unit_size: int = 100000

    def compute_units(self,
                      account_balance: float,
                      risk_per_trade: float,
                      entry_price: float,
                      stop_loss_price: Optional[float] = None,
                      instrument: Optional[str] = None) -> int:
        """
        Compute a conservative units estimate.

        Args:
            account_balance: account balance in account currency
            risk_per_trade: fraction of account to risk (e.g., 0.01 for 1%)
            entry_price: current entry price
            stop_loss_price: stop loss price (optional). If missing, falls back to ATR-based approximate.
            instrument: instrument symbol (optional) - used to adjust JPY-style sizing.

        Returns:
            int: units to place (positive integer)
        """
        try:
            risk_amount = max(0.0, float(account_balance) * float(risk_per_trade))
            if stop_loss_price and entry_price and entry_price != 0:
                stop_distance = abs(entry_price - stop_loss_price)
                # crude units estimate: risk_amount / (stop_distance * entry_price)
                # This assumes price units such that units * stop_distance * price_per_unit ~= risk_amount.
                # It's intentionally conservative and should be replaced with proper broker conversion.
                units = int(max(1000, (risk_amount / (stop_distance * entry_price)) * 1000))
            else:
                # fallback: use default unit sizing scaled by risk
                units = int(max(1000, self.default_unit_size * float(risk_per_trade)))

            # JPY pairs traditionally quoted with larger pip values -> increase base units
            if instrument and instrument.endswith('JPY'):
                units = int(units * 1.5)

            return int(max(100, units))
        except Exception:
            return int(self.default_unit_size)




























