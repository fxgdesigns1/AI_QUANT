"""
Minimal compatibility shim for execution_gate.

Always blocks execution in paper mode.
"""

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