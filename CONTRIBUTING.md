# Contributing to AI Trading System

Thank you for your interest in contributing! This document provides guidelines and best practices for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Commit Message Guidelines](#commit-message-guidelines)
- [Pull Request Process](#pull-request-process)
- [Adding New Strategies](#adding-new-strategies)
- [Security Guidelines](#security-guidelines)

## Code of Conduct

### Our Standards

- Be respectful and inclusive
- Provide constructive feedback
- Focus on what's best for the community
- Show empathy towards other contributors

### Trading-Specific Ethics

- **Always prioritize safety:** All changes must maintain proper risk controls
- **Paper trading first:** Test with demo accounts before suggesting live trading changes
- **Transparent about risks:** Document potential risks of new strategies
- **No guarantees:** Never promise or imply guaranteed returns

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally
3. **Set up your development environment** (see `SETUP_GUIDE.md`)
4. **Create a branch** for your feature/fix
5. **Make your changes**
6. **Test thoroughly**
7. **Submit a pull request**

## Development Workflow

### Branch Naming Convention

```
feature/short-description    # New features
fix/short-description        # Bug fixes
docs/short-description       # Documentation updates
refactor/short-description   # Code refactoring
strategy/strategy-name       # New trading strategies
```

Examples:
- `feature/add-rsi-indicator`
- `fix/position-sizing-bug`
- `strategy/macd-crossover`
- `docs/update-setup-guide`

### Development Process

1. **Update your main branch:**
   ```bash
   git checkout main
   git pull upstream main
   ```

2. **Create a feature branch:**
   ```bash
   git checkout -b feature/my-feature
   ```

3. **Make changes in small, logical commits**

4. **Test your changes:**
   ```bash
   python3 -m pytest tests/
   python3 src/main.py --test
   ```

5. **Push to your fork:**
   ```bash
   git push origin feature/my-feature
   ```

6. **Create a Pull Request** on GitHub

## Coding Standards

### Python Style Guide

- Follow [PEP 8](https://pep8.org/) style guidelines
- Use 4 spaces for indentation (no tabs)
- Maximum line length: 100 characters
- Use descriptive variable names

### Code Structure

```python
# Good
def calculate_position_size(account_balance, risk_percent, stop_loss_pips):
    """
    Calculate position size based on account balance and risk.
    
    Args:
        account_balance (float): Current account balance
        risk_percent (float): Risk percentage (e.g., 0.02 for 2%)
        stop_loss_pips (float): Stop loss in pips
        
    Returns:
        float: Position size in units
    """
    risk_amount = account_balance * risk_percent
    position_size = risk_amount / stop_loss_pips
    return position_size

# Bad
def calc(bal, risk, sl):
    return bal * risk / sl
```

### Documentation

- **Docstrings:** All functions and classes must have docstrings
- **Comments:** Explain *why*, not *what*
- **README updates:** Update documentation for new features
- **Type hints:** Use type hints where applicable

```python
from typing import List, Dict, Optional

def get_active_positions(account_id: str) -> List[Dict]:
    """
    Retrieve all active positions for an account.
    
    Args:
        account_id: The OANDA account identifier
        
    Returns:
        List of position dictionaries with instrument, units, PnL
    """
    pass
```

## Testing Guidelines

### Test Requirements

- **All new features** must include tests
- **Bug fixes** should include a test that would have caught the bug
- **Strategies** must include backtesting validation
- **Risk management** changes require extensive testing

### Running Tests

```bash
# Run all tests
python3 -m pytest tests/

# Run specific test file
python3 -m pytest tests/test_strategies.py

# Run with coverage
python3 -m pytest --cov=src tests/
```

### Writing Tests

```python
import pytest
from src.strategies.momentum import calculate_ema

def test_calculate_ema_basic():
    """Test EMA calculation with known values."""
    prices = [10, 11, 12, 13, 14]
    period = 3
    expected = [10.0, 10.5, 11.25, 12.125, 13.0625]
    
    result = calculate_ema(prices, period)
    
    assert len(result) == len(expected)
    for r, e in zip(result, expected):
        assert abs(r - e) < 0.0001

def test_position_size_never_exceeds_limit():
    """Test that position sizing respects maximum limits."""
    max_risk = 0.02  # 2%
    balance = 10000
    
    for _ in range(100):  # Test multiple scenarios
        position = calculate_position_size(balance, max_risk)
        risk = (position / balance)
        assert risk <= max_risk, "Position size exceeded risk limit"
```

## Commit Message Guidelines

### Format

```
Type: Short summary (50 chars or less)

More detailed explanation if needed. Wrap at 72 characters.
Explain the problem and why this change fixes it.

- Bullet points are okay
- Reference issues like #123
```

### Types

- **Add:** New feature or capability
- **Fix:** Bug fix
- **Update:** Modify existing functionality
- **Remove:** Delete code or features
- **Refactor:** Code restructuring without behavior change
- **Docs:** Documentation changes
- **Test:** Add or modify tests
- **Style:** Formatting, no functional changes
- **Perf:** Performance improvements

### Examples

```
Add: RSI indicator to momentum strategy

Implements Relative Strength Index (RSI) calculation and integrates
it into the momentum strategy for overbought/oversold detection.

- Added rsi.py with calculation logic
- Updated momentum strategy to use RSI
- Added tests for RSI calculation
- Updated documentation

Closes #42
```

```
Fix: Position sizing exceeding risk limits

Bug was calculating position size before applying account-level
risk limits. Now checks both trade-level and account-level limits.

- Modified calculate_position_size() to check account exposure
- Added validation in trade execution
- Added regression test

Fixes #87
```

## Pull Request Process

### Before Submitting

- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] New tests added for new features
- [ ] Documentation updated
- [ ] No sensitive data in commits
- [ ] Commit messages are clear and descriptive

### PR Template

When creating a PR, include:

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How has this been tested?

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Commented complex code
- [ ] Documentation updated
- [ ] No warnings generated
- [ ] Tests pass locally
- [ ] No sensitive data included

## Related Issues
Closes #123
```

### Review Process

1. **Automated checks** must pass (if configured)
2. **At least one approval** from maintainer required
3. **All comments** must be addressed or discussed
4. **Merge conflicts** must be resolved
5. **Maintainer** will merge after approval

## Adding New Strategies

### Strategy Development Checklist

- [ ] Strategy logic implemented in `src/strategies/`
- [ ] Configuration added to strategy registry
- [ ] Backtesting performed (minimum 3 months data)
- [ ] Risk management properly implemented
- [ ] Edge cases handled (low liquidity, gaps, etc.)
- [ ] Documentation written
- [ ] Paper trading tested
- [ ] Performance metrics documented

### Strategy Template

```python
from typing import Dict, Optional
from .base_strategy import BaseStrategy

class MyNewStrategy(BaseStrategy):
    """
    Brief description of strategy logic and market conditions.
    
    Entry Conditions:
    - List entry conditions
    
    Exit Conditions:
    - List exit conditions
    
    Risk Management:
    - Position sizing method
    - Stop loss approach
    - Take profit approach
    """
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.name = "my_new_strategy"
        # Initialize parameters
        
    def generate_signal(self, market_data: Dict) -> Optional[str]:
        """
        Generate trading signal based on market data.
        
        Args:
            market_data: Dictionary with OHLCV and indicators
            
        Returns:
            'BUY', 'SELL', or None
        """
        # Implement strategy logic
        pass
        
    def calculate_position_size(self, signal_strength: float) -> float:
        """Calculate appropriate position size."""
        # Implement position sizing
        pass
```

### Backtesting Requirements

```python
# Include backtesting results in PR
backtest_results = {
    "period": "2024-01-01 to 2024-10-01",
    "total_trades": 150,
    "win_rate": 0.68,
    "profit_factor": 2.1,
    "sharpe_ratio": 1.8,
    "max_drawdown": 0.12,
    "instruments": ["EUR_USD", "GBP_USD"],
    "risk_per_trade": 0.02
}
```

## Security Guidelines

### Never Commit

- ❌ API keys or tokens
- ❌ Account IDs or passwords
- ❌ Private keys or certificates
- ❌ Personal trading data
- ❌ Real account information

### Always Check

```bash
# Before committing, verify:
git diff

# Check what will be committed:
git status

# Search for potential secrets:
grep -r "api_key" .
grep -r "password" .
```

### If You Accidentally Commit Secrets

1. **Immediately** revoke the compromised credentials
2. Contact maintainers
3. Use `git filter-branch` or BFG Repo-Cleaner to remove from history
4. Force push with caution (requires maintainer approval)

## Questions?

- **Documentation:** Check `README.md` and `SETUP_GUIDE.md` first
- **Issues:** Search existing issues on GitHub
- **New Issue:** Create a new issue with detailed description
- **Discussion:** Use GitHub Discussions for general questions

## Recognition

Contributors will be:
- Listed in `CONTRIBUTORS.md`
- Credited in release notes
- Acknowledged in documentation

Thank you for contributing to the AI Trading System! 🚀

---

**Remember:** The financial markets are unforgiving. Always prioritize safety, proper testing, and risk management in your contributions.

