"""Config schema and validation for runtime config

NON-NEGOTIABLE: Config files contain ONLY non-sensitive settings.
Secrets must come from environment variables only.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
import yaml

from .strategy_registry import get_strategy_registry


@dataclass
class RiskSettings:
    """Risk management settings"""
    max_risk_per_trade_pct: float = 1.0  # Max % of account balance per trade
    max_positions: int = 3  # Max concurrent positions
    max_daily_loss_pct: float = 5.0  # Max daily loss as % of balance
    max_drawdown_pct: float = 10.0  # Max drawdown before pausing


@dataclass
class ExecutionPolicy:
    """Execution policy settings (ADVISORY ONLY - runner enforces actual gates)"""
    # These settings are hints/preferences; actual execution gate logic remains authoritative
    signals_only: bool = True  # Default: signals-only mode
    paper_execution_enabled: bool = False  # Must match env PAPER_EXECUTION_ENABLED
    live_trading_allowed: bool = False  # Must match env LIVE_TRADING + LIVE_TRADING_CONFIRM
    
    # Note: changing these in config does NOT bypass execution gate
    # Runner must check environment variables as final authority


@dataclass
class RuntimeConfig:
    """Runtime configuration - NON-SENSITIVE ONLY
    
    SECRETS HYGIENE RULE:
    - OANDA_API_KEY must come from environment only
    - Never write secrets to this config file
    - Never log or return secrets via API
    """
    
    # Active strategy
    active_strategy_key: str = "momentum"  # momentum|gold|range|eur_usd_5m_safe|momentum_v2
    
    # Scan settings
    scan_interval_seconds: int = 30
    
    # Instruments to scan (can be overridden per account in account configs)
    default_instruments: List[str] = field(default_factory=lambda: [
        "EUR_USD", "GBP_USD", "XAU_USD", "USD_JPY", "AUD_USD"
    ])
    
    # Risk settings
    risk: RiskSettings = field(default_factory=RiskSettings)
    
    # Execution policy (advisory)
    execution_policy: ExecutionPolicy = field(default_factory=ExecutionPolicy)
    
    # News integration toggles
    news_integration_enabled: bool = False
    news_impact_threshold: str = "medium"  # low|medium|high
    
    # UI-only hints (not used by runner)
    ui_theme: str = "dark"
    ui_show_advanced_metrics: bool = False
    
    def validate(self) -> List[str]:
        """Validate config and return list of errors (empty if valid)"""
        errors = []
        
        # Validate strategy key (use registry as source of truth to prevent drift)
        strategy_registry = get_strategy_registry()
        valid_strategies = set(strategy_registry.keys())
        if self.active_strategy_key not in valid_strategies:
            errors.append(f"Invalid active_strategy_key: {self.active_strategy_key}. Must be one of {valid_strategies}")
        
        # Validate scan interval
        if self.scan_interval_seconds < 1:
            errors.append(f"scan_interval_seconds must be >= 1, got {self.scan_interval_seconds}")
        if self.scan_interval_seconds > 3600:
            errors.append(f"scan_interval_seconds must be <= 3600 (1 hour), got {self.scan_interval_seconds}")
        
        # Validate risk settings
        if not 0.1 <= self.risk.max_risk_per_trade_pct <= 10.0:
            errors.append(f"risk.max_risk_per_trade_pct must be 0.1-10.0, got {self.risk.max_risk_per_trade_pct}")
        
        if not 1 <= self.risk.max_positions <= 20:
            errors.append(f"risk.max_positions must be 1-20, got {self.risk.max_positions}")
        
        if not 1.0 <= self.risk.max_daily_loss_pct <= 50.0:
            errors.append(f"risk.max_daily_loss_pct must be 1.0-50.0, got {self.risk.max_daily_loss_pct}")
        
        # Ensure no secrets in config
        config_dict = asdict(self)
        config_str = str(config_dict).lower()
        secret_patterns = ["api_key", "password", "secret", "token", "credential"]
        for pattern in secret_patterns:
            if pattern in config_str and pattern != "active_strategy_key":
                errors.append(f"Config contains forbidden secret pattern: {pattern}")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RuntimeConfig:
        """Load from dict (supports partial updates)"""
        # Handle nested objects
        if "risk" in data and isinstance(data["risk"], dict):
            data["risk"] = RiskSettings(**data["risk"])
        
        if "execution_policy" in data and isinstance(data["execution_policy"], dict):
            data["execution_policy"] = ExecutionPolicy(**data["execution_policy"])
        
        return cls(**data)
    
    @classmethod
    def load_from_yaml(cls, path: str) -> RuntimeConfig:
        """Load config from YAML file"""
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)
    
    def save_to_yaml(self, path: str) -> None:
        """Save config to YAML file"""
        with open(path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(self.to_dict(), f, default_flow_style=False, sort_keys=False)


def get_default_config() -> RuntimeConfig:
    """Get safe default config"""
    return RuntimeConfig()
