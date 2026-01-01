#!/usr/bin/env python3
"""
Momentum Trading Strategy
Production-ready momentum trading strategy for Google Cloud deployment
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np
import pandas as pd

from .momentum_v2_improved import MomentumV2Improved

def get_momentum_trading_strategy():
    """
    Factory function to return an instance of the Momentum V2 Improved strategy.
    """
    return MomentumV2Improved()

