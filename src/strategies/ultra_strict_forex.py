#!/usr/bin/env python3
"""
Ultra Strict Forex Trading Strategy
Production-ready high-precision forex trading with strict risk controls
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np
import pandas as pd

from .ultra_strict_v2_regime_aware import UltraStrictV2RegimeAware

class UltraStrictForexStrategy(UltraStrictV2RegimeAware):
    """Alias/wrapper class for compatibility with older code paths."""
    pass

def get_ultra_strict_forex_strategy():
    """
    Factory function to return an instance of the Ultra Strict Forex strategy.
    """
    return UltraStrictForexStrategy()
