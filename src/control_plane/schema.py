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
class StrategyAssignment:
    """Strategy assignment to a specific account"""
    account_id: str
    strategy_key: str
    enabled: bool = True


@dataclass
class RiskSettings:
    """Risk management settings"""
    max_risk_per_trade_pct: float = 1.0  # Max % of account balance per trade
    max_positions: int = 3  # Max concurrent positions
    max_daily_loss_pct: float = 5.0  # Max daily loss as % of balance
    max_drawdown_pct: float = 10.0  # Max drawdown before pausing
    max_daily_trades_per_account: int = 10  # Max daily trades per account (global default) - RAISED FOR PAPER TESTING


@dataclass
class AccountRiskLimits:
    """Per-account risk limits (overrides global RiskSettings)"""
    max_daily_trades: Optional[int] = None  # None = use global default, 0 = unlimited, >0 = specific limit
    enabled: bool = True  # If False, daily limit check is disabled for this account


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
class TradeSelectionSettings:
    """Trade selection and quality ranking settings"""
    mode: str = "SPEED"  # SPEED|QUALITY_OVER_SPEED|TOP_N_DAILY
    daily_trade_limit: int = 3
    min_confidence_threshold: float = 0.65
    early_session_penalty_minutes: int = 60
    re_rank_on_each_scan: bool = True
    
    # TOP_N_DAILY settings
    execution_cutoff: str = "NY_CLOSE"
    allow_exceptional_early_execution: bool = True
    exceptional_confidence_threshold: float = 0.85


@dataclass
class RuntimeConfig:
    """Runtime configuration - NON-SENSITIVE ONLY
    
    SECRETS HYGIENE RULE:
    - OANDA_API_KEY must come from environment only
    - Never write secrets to this config file
    - Never log or return secrets via API
    """
    
    # Active strategy (legacy - used only when strategy_assignments is empty)
    active_strategy_key: str = "momentum"  # momentum|gold|range|eur_usd_5m_safe|momentum_v2
    
    # Multi-account strategy assignments (one strategy per account, up to 10)
    strategy_assignments: Optional[List[StrategyAssignment]] = None
    max_strategy_assignments: int = 10  # Hard upper bound
    
    # Scan settings
    scan_interval_seconds: int = 30
    
    # Instruments to scan (can be overridden per account in account configs)
    default_instruments: List[str] = field(default_factory=lambda: [
        "EUR_USD", "GBP_USD", "XAU_USD", "USD_JPY", "AUD_USD"
    ])
    
    # Risk settings
    risk: RiskSettings = field(default_factory=RiskSettings)
    
    # Per-account risk limits (account_id -> AccountRiskLimits)
    # If account not in dict, uses global risk.max_daily_trades_per_account
    account_risk_limits: Dict[str, AccountRiskLimits] = field(default_factory=dict)
    
    # Execution policy (advisory)
    execution_policy: ExecutionPolicy = field(default_factory=ExecutionPolicy)
    
    # Trade Selection (Quality over Quantity)
    trade_selection: TradeSelectionSettings = field(default_factory=TradeSelectionSettings)
    
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
        
        # Validate strategy_assignments if present
        if self.strategy_assignments is not None:
            if len(self.strategy_assignments) > self.max_strategy_assignments:
                errors.append(f"strategy_assignments count ({len(self.strategy_assignments)}) exceeds max_strategy_assignments ({self.max_strategy_assignments})")
            
            # Check for unique account_id (allow account 006 to have multiple strategies)
            account_ids = [a.account_id for a in self.strategy_assignments if a.enabled]
            account_006_id = None
            for aid in account_ids:
                if aid.endswith("006") or (len(aid) >= 3 and aid[-3:] == "006"):
                    account_006_id = aid
                    break
            
            # Allow account 006 to have multiple strategies, but other accounts must be unique
            other_account_ids = [aid for aid in account_ids if aid != account_006_id]
            if len(other_account_ids) != len(set(other_account_ids)):
                errors.append("strategy_assignments: duplicate account_id found (each account except 006 can only have one strategy)")
            
            # Note: Multiple accounts CAN share the same strategy_key (removed unique strategy_key requirement)
            
            # Validate each strategy_key exists in registry
            for assignment in self.strategy_assignments:
                if assignment.enabled and assignment.strategy_key not in valid_strategies:
                    errors.append(f"Invalid strategy_key in assignment: {assignment.strategy_key}. Must be one of {valid_strategies}")
        
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
        
        if not 0 <= self.risk.max_daily_trades_per_account <= 100:
            errors.append(f"risk.max_daily_trades_per_account must be 0-100 (0=unlimited), got {self.risk.max_daily_trades_per_account}")
        
        # Validate account_risk_limits
        for account_id, limits in self.account_risk_limits.items():
            if limits.max_daily_trades is not None and not 0 <= limits.max_daily_trades <= 100:
                errors.append(f"account_risk_limits[{account_id}].max_daily_trades must be 0-100 (0=unlimited, None=use global), got {limits.max_daily_trades}")
        
        # Validate trade_selection settings
        if self.trade_selection.mode not in ["SPEED", "QUALITY_OVER_SPEED", "TOP_N_DAILY"]:
            errors.append(f"trade_selection.mode must be SPEED, QUALITY_OVER_SPEED or TOP_N_DAILY, got {self.trade_selection.mode}")
        
        if not 0 <= self.trade_selection.min_confidence_threshold <= 1.0:
            errors.append(f"trade_selection.min_confidence_threshold must be 0.0-1.0, got {self.trade_selection.min_confidence_threshold}")
            
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
            
        if "trade_selection" in data and isinstance(data["trade_selection"], dict):
            data["trade_selection"] = TradeSelectionSettings(**data["trade_selection"])
        
        # Handle account_risk_limits dict
        if "account_risk_limits" in data and isinstance(data["account_risk_limits"], dict):
            data["account_risk_limits"] = {
                account_id: AccountRiskLimits(**limits) if isinstance(limits, dict) else limits
                for account_id, limits in data["account_risk_limits"].items()
            }
        
        # Handle strategy_assignments list
        if "strategy_assignments" in data and isinstance(data["strategy_assignments"], list):
            data["strategy_assignments"] = [
                StrategyAssignment(**item) if isinstance(item, dict) else item
                for item in data["strategy_assignments"]
            ]
        
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
