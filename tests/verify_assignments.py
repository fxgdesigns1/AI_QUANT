import sys
import os
import unittest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass

# Add root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock things before importing working_trading_system if they are top-level execution risks
# But working_trading_system protects main execution with if __name__ == "__main__"

from working_trading_system import WorkingTradingSystem

class TestStrategyAssignments(unittest.TestCase):
    @patch('working_trading_system.get_account_manager')
    @patch('working_trading_system.ExecutionGate')
    @patch('src.control_plane.config_store.ConfigStore')
    @patch('src.control_plane.strategy_registry.get_strategy_info')
    def test_strict_assignments(self, mock_get_strat_info, mock_config_store, mock_gate, mock_get_acc_man):
        print("Starting test_strict_assignments...")
        # Setup Mocks
        mock_acc_man = MagicMock()
        mock_acc_man.get_active_accounts.return_value = ['001', '002']
        mock_acc_man.account_configs = {}
        mock_get_acc_man.return_value = mock_acc_man
        
        # Mock Config
        mock_config = MagicMock()
        
        # Create mock assignments
        mock_assignment1 = MagicMock()
        mock_assignment1.account_id = '001'
        mock_assignment1.strategy_key = 'gold'
        mock_assignment1.enabled = True
        
        mock_assignment2 = MagicMock()
        mock_assignment2.account_id = '002'
        mock_assignment2.strategy_key = 'eur_usd_5m_safe'
        mock_assignment2.enabled = True
        
        mock_config.strategy_assignments = [mock_assignment1, mock_assignment2]
        mock_config.account_risk_limits = {}
        mock_config.risk = MagicMock()
        mock_config.risk.max_daily_trades_per_account = 10
        mock_config.risk.max_positions = 10
        
        mock_store_instance = mock_config_store.return_value
        mock_store_instance.load.return_value = mock_config
        
        # Mock Strategy Registry
        def get_info_side_effect(key):
            info = MagicMock()
            if key == 'gold':
                info.instruments = ['XAU_USD']
            elif key == 'eur_usd_5m_safe':
                info.instruments = ['EUR_USD']
            else:
                return None
            return info
        mock_get_strat_info.side_effect = get_info_side_effect
        
        # Initialize System
        # Mock _can_execute to return True, "test"
        with patch('working_trading_system._can_execute', return_value=(True, "test_mode")):
            system = WorkingTradingSystem()
        
        # Mock client and market data
        mock_client = MagicMock()
        # Return data for ALL instruments to verify filtering
        # Use a high enough timestamp so it's not "stale"
        ts_now = 2000000000.0
        
        mock_client.get_current_prices.return_value = {
            'XAU_USD': MagicMock(mid=2000.0, bid=1999.0, ask=2001.0, ts_utc=ts_now), 
            'EUR_USD': MagicMock(mid=1.1000, bid=1.0999, ask=1.1001, ts_utc=ts_now),
            'GBP_USD': MagicMock(mid=1.2500, bid=1.2499, ask=1.2501, ts_utc=ts_now)
        }
        mock_acc_man.get_account_client.return_value = mock_client
        
        # Mock strategies
        system.strategies['gold'] = MagicMock()
        system.strategies['eur_usd_5m_safe'] = MagicMock()
        
        # Mock order manager to prevent "No order manager" warning/skip
        system.order_managers['001'] = MagicMock()
        system.order_managers['002'] = MagicMock()
        
        # Run Scan
        with patch('src.control_plane.news_provider.fetch_news_with_registry', side_effect=ImportError):
             # Mock time to ensure freshness checks pass
             with patch('working_trading_system.datetime') as mock_datetime:
                 mock_datetime.now.return_value.timestamp.return_value = ts_now + 1 # 1s after price
                 
                 # Create a proper date object for comparison
                 from datetime import date
                 mock_date = date(2023, 1, 1)
                 mock_datetime.now.return_value.date.return_value = mock_date
                 mock_datetime.utcnow.return_value.isoformat.return_value = "2023-01-01T00:00:00"
                 
                 # Also need to mock timezone.utc
                 mock_datetime.timezone.utc = MagicMock()
                 
                 # Update system's last reset to match type
                 system._last_daily_reset = mock_date
                 
                 print("Running scan_and_execute...")
                 system.scan_and_execute()
        
        print("Verifying calls...")
        
        # Verify Gold Strategy received ONLY XAU_USD
        call_args_gold = system.strategies['gold'].analyze_market.call_args
        if call_args_gold is None:
            self.fail("Gold strategy was NOT called")
            
        market_data_gold = call_args_gold[0][0]
        self.assertIn('XAU_USD', market_data_gold, "Gold strategy should have XAU_USD")
        self.assertNotIn('EUR_USD', market_data_gold, "Gold strategy should NOT have EUR_USD")
        self.assertNotIn('GBP_USD', market_data_gold, "Gold strategy should NOT have GBP_USD")
        print("Gold strategy verification PASSED")
        
        # Verify EURUSD Strategy received ONLY EUR_USD
        call_args_eur = system.strategies['eur_usd_5m_safe'].analyze_market.call_args
        if call_args_eur is None:
            self.fail("EURUSD strategy was NOT called")
            
        market_data_eur = call_args_eur[0][0]
        self.assertIn('EUR_USD', market_data_eur, "EURUSD strategy should have EUR_USD")
        self.assertNotIn('XAU_USD', market_data_eur, "EURUSD strategy should NOT have XAU_USD")
        self.assertNotIn('GBP_USD', market_data_eur, "EURUSD strategy should NOT have GBP_USD")
        print("EURUSD strategy verification PASSED")

if __name__ == '__main__':
    unittest.main()
