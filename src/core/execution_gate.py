"""
Minimal compatibility shim for execution_gate.

Always blocks execution in paper mode.
"""

from dataclasses import dataclass

@dataclass
class ExecutionDecision:
    allowed: bool
    mode: str  # 'paper' or 'live'
    reason: str

class ExecutionGate:
    def __init__(self):
        self.paper_mode = True
        self.execution_enabled = False
    
    def is_execution_allowed(self):
        """Always false in paper mode"""
        return False
    
    def check_trading_hours(self):
        """Basic trading hours check"""
        return True
    
    def decision(self):
        """Return execution decision (compatibility method)"""
        return ExecutionDecision(
            allowed=False,
            mode='paper',
            reason='paper_mode_disabled'
        )