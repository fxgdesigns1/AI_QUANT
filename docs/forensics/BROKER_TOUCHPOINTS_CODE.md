./verify_config_sync.py:4:Checks if running configuration matches accounts.yaml
./verify_config_sync.py:24:    yaml_accounts = yaml_mgr.get_all_accounts()
./verify_config_sync.py:26:    print(f"\n📄 accounts.yaml Configuration:")
./verify_config_sync.py:27:    print(f"  • Total accounts: {len(yaml_accounts)}")
./verify_config_sync.py:28:    print(f"  • Active accounts: {len([a for a in yaml_accounts if a.get('active')])}")
./verify_config_sync.py:30:    for account in yaml_accounts:
./verify_config_sync.py:40:        print(f"  • Loaded accounts: {len(scanner.accounts)}")
./verify_config_sync.py:42:        for strategy_name, account_id in scanner.accounts.items():
./verify_config_sync.py:52:        for acc in yaml_accounts:
./FIND_WHY_NO_SIGNALS.py:19:load_dotenv('google-cloud-trading-system/oanda_config.env')
./FIND_WHY_NO_SIGNALS.py:21:from src.core.oanda_client import get_oanda_client
./FIND_WHY_NO_SIGNALS.py:28:    oanda = get_oanda_client()
./FIND_WHY_NO_SIGNALS.py:38:    prices = oanda.get_current_prices(test_pairs)
./FIND_WHY_NO_SIGNALS.py:154:    candles = oanda.get_candles('EUR_USD', count=60, granularity='M5')
./migrate_credentials_to_secret_manager.py:21:        "google-cloud-trading-system/oanda_config.env",
./migrate_credentials_to_secret_manager.py:43:        'oanda-api-key': os.getenv('OANDA_API_KEY'),
./send_telegram_update.py:15:env_path = os.path.join(os.path.dirname(__file__), 'google-cloud-trading-system', 'oanda_config.env')
./send_telegram_update.py:58:✅ Drawdown accounts have low exposure
./send_telegram_update.py:59:🟡 2 accounts at 54-55% exposure
./simple_agent.py:21:    Tracks health/metrics and enforces guardrails; does not place real orders.
./check_12hour_trades.py:3:Check actual trades executed in last 12 hours across all accounts
./check_12hour_trades.py:9:from src.core.oanda_client import OandaClient
./check_12hour_trades.py:62:            # Count only filled orders
./dashboard/agent_controller.py:16:    Tracks health/metrics and enforces guardrails; does not place real orders.
./enhanced_websocket_test.py:163:    async def test_websocket_connection_detailed(self):
./enhanced_websocket_test.py:239:    async def test_browser_websocket_functionality(self):
./enhanced_websocket_test.py:245:            websocket_test_script = """
./enhanced_websocket_test.py:263:                window.websocketConnected = true;
./enhanced_websocket_test.py:264:                window.websocketStats = {connects: 1, disconnects: 0};
./enhanced_websocket_test.py:270:                window.websocketConnected = false;
./enhanced_websocket_test.py:271:                if (window.websocketStats) window.websocketStats.disconnects += 1;
./enhanced_websocket_test.py:279:                window.websocketMessages = messagesReceived;
./enhanced_websocket_test.py:281:                window.websocketMessageTypes = messageTypes;
./enhanced_websocket_test.py:289:                window.websocketMessages = messagesReceived;
./enhanced_websocket_test.py:291:                window.websocketMessageTypes = messageTypes;
./enhanced_websocket_test.py:299:                window.websocketMessages = messagesReceived;
./enhanced_websocket_test.py:301:                window.websocketMessageTypes = messageTypes;
./enhanced_websocket_test.py:309:                window.websocketMessages = messagesReceived;
./enhanced_websocket_test.py:311:                window.websocketMessageTypes = messageTypes;
./enhanced_websocket_test.py:319:                window.websocketMessages = messagesReceived;
./enhanced_websocket_test.py:321:                window.websocketMessageTypes = messageTypes;
./enhanced_websocket_test.py:326:                window.websocketError = data;
./enhanced_websocket_test.py:339:            await self.page.evaluate(websocket_test_script)
./enhanced_websocket_test.py:345:            connected = await self.page.evaluate("window.websocketConnected")
./enhanced_websocket_test.py:346:            messages = await self.page.evaluate("window.websocketMessages || 0")
./enhanced_websocket_test.py:347:            error = await self.page.evaluate("window.websocketError")
./enhanced_websocket_test.py:349:            message_types = await self.page.evaluate("window.websocketMessageTypes || []")
./enhanced_websocket_test.py:350:            stats = await self.page.evaluate("window.websocketStats || {}")
./enhanced_websocket_test.py:521:            ("WebSocket Connection", tester.test_websocket_connection_detailed),
./enhanced_websocket_test.py:522:            ("Browser WebSocket", tester.test_browser_websocket_functionality),
./fixed_dashboard.py:77:@app.route('/api/accounts')
./fixed_dashboard.py:78:def api_accounts():
./fixed_dashboard.py:80:    data = get_api_data('/api/accounts')
./fixed_dashboard.py:84:        return jsonify({'accounts': [], 'total_balance': 0, 'timestamp': datetime.now().isoformat()})
./fixed_dashboard.py:102:        return jsonify({'accounts': {}, 'total_accounts': 0, 'timestamp': datetime.now().isoformat()})
./fixed_dashboard.py:119:    accounts_data = get_api_data('/api/accounts')
./fixed_dashboard.py:124:        'accounts': accounts_data or {'accounts': []},
./optimized_all_strategies_system.py:22:from src.core.oanda_client import OandaClient
./optimized_all_strategies_system.py:31:        self.active_accounts = self.account_manager.get_active_accounts()
./optimized_all_strategies_system.py:33:        # Load accounts.yaml to get strategy mappings
./optimized_all_strategies_system.py:34:        self.accounts_config = self._load_accounts_config()
./optimized_all_strategies_system.py:41:        logger.info(f"🎯 OPTIMIZED ALL STRATEGIES SYSTEM initialized with {len(self.active_accounts)} accounts")
./optimized_all_strategies_system.py:44:    def _load_accounts_config(self):
./optimized_all_strategies_system.py:45:        """Load accounts configuration"""
./optimized_all_strategies_system.py:47:            config_path = '/Users/mac/quant_system_clean/google-cloud-trading-system/accounts.yaml'
./optimized_all_strategies_system.py:51:            logger.error(f"❌ Failed to load accounts config: {e}")
./optimized_all_strategies_system.py:57:        for account in self.accounts_config.get('accounts', []):
./optimized_all_strategies_system.py:66:            for account in self.accounts_config.get('accounts', []):
./optimized_all_strategies_system.py:77:            for account in self.accounts_config.get('accounts', []):
./optimized_all_strategies_system.py:189:        # Process ALL accounts
./optimized_all_strategies_system.py:190:        for account_id in self.active_accounts:
./optimized_all_strategies_system.py:220:                                for account in self.accounts_config.get('accounts', []):
./dashboard/trade_suggestions_api.py:29:from src.core.oanda_client import OandaClient
./dashboard/trade_suggestions_api.py:44:        # Load accounts
./dashboard/trade_suggestions_api.py:45:        self.load_accounts()
./dashboard/trade_suggestions_api.py:47:    def load_accounts(self):
./dashboard/trade_suggestions_api.py:48:        """Load all trading accounts"""
./dashboard/trade_suggestions_api.py:51:            self.accounts_config = yaml_mgr.get_all_accounts()
./dashboard/trade_suggestions_api.py:52:            logger.info(f"✅ Loaded {len(self.accounts_config)} accounts for trade suggestions")
./dashboard/trade_suggestions_api.py:54:            logger.error(f"❌ Error loading accounts: {e}")
./dashboard/trade_suggestions_api.py:55:            self.accounts_config = []
./market_overview_today.py:18:    load_dotenv('google-cloud-trading-system/oanda_config.env')
./market_overview_today.py:20:    from src.core.oanda_client import OandaClient
./send_notification.py:26:- Stop loss & take profit orders
./dashboard/api_usage_tracker.py:55:            'oanda': APIUsageStats(
./dashboard/oanda_client.py:25:            self.base_url = 'https://api-fxpractice.oanda.com'
./dashboard/oanda_client.py:27:            self.base_url = 'https://api-fxtrade.oanda.com'
./dashboard/oanda_client.py:40:            oanda_instruments = []
./dashboard/oanda_client.py:43:                    oanda_instruments.append(instrument.replace('_', '_'))
./dashboard/oanda_client.py:45:                    oanda_instruments.append(instrument)
./dashboard/oanda_client.py:48:            url = f"{self.base_url}/v3/accounts/{self.account_id}/pricing"
./dashboard/oanda_client.py:50:                'instruments': ','.join(oanda_instruments)
./dashboard/oanda_client.py:88:            url = f"{self.base_url}/v3/accounts/{self.account_id}"
./place_test_trades.py:3:Place small test trades on all accounts to verify trading capability
./place_test_trades.py:14:OANDA_BASE_URL = f'https://api-fx{OANDA_ENV}.oanda.com/v3' if OANDA_ENV == 'practice' else 'https://api-fxtrade.oanda.com/v3'
./place_test_trades.py:28:# Test accounts and instruments - CLOUD ACTIVE ACCOUNTS
./place_test_trades.py:52:    url = f'{OANDA_BASE_URL}/accounts/{account_id}/pricing'
./place_test_trades.py:75:    url = f'{OANDA_BASE_URL}/accounts/{account_id}/orders'
./place_test_trades.py:156:    send_telegram("🧪 TEST TRADES STARTING NOW!\n\nPlacing small test orders on all accounts to verify trading capability...")
./place_test_trades.py:244:        message += f"⚠️ {successful} accounts working!\n\nPartial success - investigate failed accounts.\nWorking accounts can trade PPI/CPI!"
./working_beautiful_dashboard.py:28:        'accounts': [
./working_beautiful_dashboard.py:142:        'accounts': len(data['accounts']),
./working_beautiful_dashboard.py:145:        'active_accounts': len(data['accounts']),
./working_beautiful_dashboard.py:168:@app.route('/api/accounts')
./working_beautiful_dashboard.py:169:def api_accounts():
./working_beautiful_dashboard.py:173:        'accounts': data['accounts'],
./working_beautiful_dashboard.py:174:        'total_balance': sum(acc['balance'] for acc in data['accounts']),
./working_beautiful_dashboard.py:192:        'total_accounts': len(data['accounts']),
./working_beautiful_dashboard.py:193:        'accounts': {acc['id']: acc for acc in data['accounts']},
./monitor_ppi_and_news.py:18:OANDA_API_KEY = settings.oanda_api_key
./monitor_ppi_and_news.py:21:OANDA_URL = f'https://api-fx{OANDA_ENV}.oanda.com/v3/accounts/{OANDA_ACCOUNT}/pricing' if OANDA_ENV == "practice" else f"https://api-fxtrade.oanda.com/v3/accounts/{OANDA_ACCOUNT}/pricing"
./working_auto_scanner.py:23:from src.core.oanda_client import OandaClient
./working_auto_scanner.py:34:        self.active_accounts = self.account_manager.get_active_accounts()
./working_auto_scanner.py:42:        logger.info(f"✅ Working Auto Scanner initialized with {len(self.active_accounts)} accounts")
./working_auto_scanner.py:52:        # Get market data for all accounts
./working_auto_scanner.py:53:        for account_id in self.active_accounts:
./dashboard/advanced_dashboard.py:63:                'oanda': {
./dashboard/advanced_dashboard.py:67:                    'base_url': 'https://api-fxpractice.oanda.com'
./dashboard/advanced_dashboard.py:281:            from src.core.oanda_client import OandaClient
./dashboard/advanced_dashboard.py:433:        accounts_response = get_accounts()
./dashboard/advanced_dashboard.py:434:        if hasattr(accounts_response, 'get_json'):
./dashboard/advanced_dashboard.py:435:            accounts_data = accounts_response.get_json()
./dashboard/advanced_dashboard.py:436:            if accounts_data.get('status') == 'success':
./dashboard/advanced_dashboard.py:437:                accounts = accounts_data.get('accounts', {})
./dashboard/advanced_dashboard.py:439:                accounts = {}
./dashboard/advanced_dashboard.py:441:            accounts = {}
./dashboard/advanced_dashboard.py:442:        total_balance = sum(acc.get('balance', 0) for acc in accounts.values())
./dashboard/advanced_dashboard.py:443:        total_positions = sum(acc.get('open_positions', 0) for acc in accounts.values())
./dashboard/advanced_dashboard.py:446:        total_systems = len(accounts)
./dashboard/advanced_dashboard.py:447:        running_systems = len([acc for acc in accounts.values() if acc.get('active', False)])
./dashboard/advanced_dashboard.py:473:                    'active_accounts': running_systems,
./dashboard/advanced_dashboard.py:511:        accounts_response = get_accounts()
./dashboard/advanced_dashboard.py:512:        if hasattr(accounts_response, 'get_json'):
./dashboard/advanced_dashboard.py:513:            accounts_data = accounts_response.get_json()
./dashboard/advanced_dashboard.py:514:            if accounts_data.get('status') == 'success':
./dashboard/advanced_dashboard.py:515:                accounts = accounts_data.get('accounts', {})
./dashboard/advanced_dashboard.py:517:                accounts = {}
./dashboard/advanced_dashboard.py:519:            accounts = {}
./dashboard/advanced_dashboard.py:524:        for account_id, account in accounts.items():
./dashboard/advanced_dashboard.py:600:        accounts_response = get_accounts()
./dashboard/advanced_dashboard.py:601:        if hasattr(accounts_response, 'get_json'):
./dashboard/advanced_dashboard.py:602:            accounts_data = accounts_response.get_json()
./dashboard/advanced_dashboard.py:603:            if accounts_data.get('status') == 'success':
./dashboard/advanced_dashboard.py:604:                accounts = accounts_data.get('accounts', {})
./dashboard/advanced_dashboard.py:606:                accounts = {}
./dashboard/advanced_dashboard.py:608:            accounts = {}
./dashboard/advanced_dashboard.py:611:        total_balance = sum(acc.get('balance', 0) for acc in accounts.values())
./dashboard/advanced_dashboard.py:612:        total_positions = sum(acc.get('open_positions', 0) for acc in accounts.values())
./dashboard/advanced_dashboard.py:652:                    'active_accounts': len(accounts),
./dashboard/advanced_dashboard.py:1268:        from src.core.oanda_client import OandaClient
./dashboard/advanced_dashboard.py:1297:        strategy_accounts = {
./dashboard/advanced_dashboard.py:1303:        for strategy_name, account_id in strategy_accounts.items():
./dashboard/advanced_dashboard.py:1361:@app.route('/api/accounts')
./dashboard/advanced_dashboard.py:1362:def get_accounts():
./dashboard/advanced_dashboard.py:1366:        from src.core.oanda_client import OandaClient
./dashboard/advanced_dashboard.py:1369:        all_accounts = {
./dashboard/advanced_dashboard.py:1384:        accounts_data = {}
./dashboard/advanced_dashboard.py:1390:        for account_id, account_name in all_accounts.items():
./dashboard/advanced_dashboard.py:1395:                accounts_data[account_id] = {
./dashboard/advanced_dashboard.py:1419:                # Add placeholder data for failed accounts
./dashboard/advanced_dashboard.py:1420:                accounts_data[account_id] = {
./dashboard/advanced_dashboard.py:1438:            'accounts': accounts_data,
./dashboard/advanced_dashboard.py:1906:        # Get active accounts for each strategy
./dashboard/advanced_dashboard.py:1907:        accounts = yaml_mgr.get_all_accounts()
./dashboard/advanced_dashboard.py:1910:        for account in accounts:
./dashboard/advanced_dashboard.py:1928:                'assigned_accounts': account_by_strategy.get(name, []),
./dashboard/advanced_dashboard.py:1953:        accounts = yaml_mgr.get_all_accounts()
./dashboard/advanced_dashboard.py:1956:        for account in accounts:
./check_positions_and_opportunities.py:4:Checks current positions, market conditions, and trading opportunities across all accounts
./check_positions_and_opportunities.py:16:env_path = os.path.join(os.path.dirname(__file__), 'google-cloud-trading-system', 'oanda_config.env')
./check_positions_and_opportunities.py:19:from src.core.oanda_client import OandaClient
./check_positions_and_opportunities.py:167:                        client.update_trade_protective_orders(trade['id'], stop_loss=sl_price)
./check_positions_and_opportunities.py:241:        print("Please check your oanda_config.env file")
./check_positions_and_opportunities.py:335:        print(f"   ✅ All accounts monitored")
./check_positions_and_opportunities.py:341:        print("\n❌ No accounts were successfully checked")
./comprehensive_trading_system.py:4:This system uses ALL strategies from accounts.yaml and executes them properly
./comprehensive_trading_system.py:22:from src.core.oanda_client import OandaClient
./comprehensive_trading_system.py:42:        self.active_accounts = self.account_manager.get_active_accounts()
./comprehensive_trading_system.py:44:        # Load accounts.yaml to get strategy mappings
./comprehensive_trading_system.py:45:        self.accounts_config = self._load_accounts_config()
./comprehensive_trading_system.py:65:        logger.info(f"🎯 COMPREHENSIVE SYSTEM initialized with {len(self.active_accounts)} accounts")
./comprehensive_trading_system.py:68:    def _load_accounts_config(self):
./comprehensive_trading_system.py:69:        """Load accounts configuration"""
./comprehensive_trading_system.py:71:            config_path = '/Users/mac/quant_system_clean/google-cloud-trading-system/accounts.yaml'
./comprehensive_trading_system.py:75:            logger.error(f"❌ Failed to load accounts config: {e}")
./comprehensive_trading_system.py:81:            for account in self.accounts_config.get('accounts', []):
./comprehensive_trading_system.py:97:            for account in self.accounts_config.get('accounts', []):
./comprehensive_trading_system.py:106:        """Comprehensive scan - execute ALL strategies for ALL accounts"""
./comprehensive_trading_system.py:114:        for account_id in self.active_accounts:
./comprehensive_trading_system.py:145:                                for account in self.accounts_config.get('accounts', []):
./DIRECT_STRATEGY_TEST.py:9:from src.core.oanda_client import OandaClient
./execute_current_opportunities.py:9:load_dotenv('google-cloud-trading-system/oanda_config.env')
./execute_current_opportunities.py:16:BASE_URL = f'https://api-fx{OANDA_ENV}.oanda.com/v3' if OANDA_ENV == 'practice' else 'https://api-fxtrade.oanda.com/v3'
./execute_current_opportunities.py:95:    url = f'{BASE_URL}/accounts/{account}/pricing'
./execute_current_opportunities.py:124:    url = f'{BASE_URL}/accounts/{account}/orders'
./complete_ai_analysis.py:8:OANDA_API_KEY = settings.oanda_api_key
./complete_ai_analysis.py:11:OANDA_BASE_URL = f'https://api-fx{OANDA_ENV}.oanda.com' if OANDA_ENV == "practice" else "https://api-fxtrade.oanda.com"
./complete_ai_analysis.py:24:    url = f'{OANDA_BASE_URL}/v3/accounts/{OANDA_ACCOUNT_ID}'
./complete_ai_analysis.py:38:    url = f'{OANDA_BASE_URL}/v3/accounts/{OANDA_ACCOUNT_ID}/positions'
./complete_ai_analysis.py:63:    url = f'{OANDA_BASE_URL}/v3/accounts/{OANDA_ACCOUNT_ID}/pricing'
./complete_ai_analysis.py:111:    url = f'{OANDA_BASE_URL}/v3/accounts/{OANDA_ACCOUNT_ID}/transactions'
./execute_safe_swing_trade.py:18:from core.oanda_client import OandaClient
./execute_safe_swing_trade.py:29:accounts = yaml_mgr.get_all_accounts()
./execute_safe_swing_trade.py:32:for account in accounts:
./working_trading_system.py:34:        self.active_accounts = self.account_manager.get_active_accounts()
./working_trading_system.py:42:        for account_id in self.active_accounts:
./working_trading_system.py:45:        logger.info(f"✅ Working Trading System initialized with {len(self.active_accounts)} accounts")
./working_trading_system.py:53:        # Get market data for all accounts
./working_trading_system.py:54:        for account_id in self.active_accounts:
./working_trading_system.py:86:                account_info = order_manager.oanda_client.get_account_info()
./working_trading_system.py:98:                result = order_manager.oanda_client.place_market_order(
./dashboard/simple_trade_suggestions.py:23:from src.core.oanda_client import OandaClient
./dashboard/simple_trade_suggestions.py:40:        # Load accounts
./dashboard/simple_trade_suggestions.py:41:        self.load_accounts()
./dashboard/simple_trade_suggestions.py:43:    def load_accounts(self):
./dashboard/simple_trade_suggestions.py:44:        """Load all trading accounts"""
./dashboard/simple_trade_suggestions.py:47:            self.accounts_config = yaml_mgr.get_all_accounts()
./dashboard/simple_trade_suggestions.py:48:            logger.info(f"✅ Loaded {len(self.accounts_config)} accounts")
./dashboard/simple_trade_suggestions.py:50:            logger.error(f"❌ Error loading accounts: {e}")
./dashboard/simple_trade_suggestions.py:51:            self.accounts_config = []
./take_gold_profit.py:15:env_path = os.path.join(os.path.dirname(__file__), 'google-cloud-trading-system', 'oanda_config.env')
./take_gold_profit.py:18:from src.core.oanda_client import OandaClient
./test_trade_execution.py:44:                # Show details for accounts with signals
./test_market_conditions.py:14:OANDA_API_KEY = settings.oanda_api_key
./test_market_conditions.py:28:url = f"https://api-fxpractice.oanda.com/v3/accounts/{ACCOUNT_ID}/instruments/{inst}/candles"
./BRUTAL_DIAGNOSTIC_WHY_NO_EXECUTION.py:25:    load_dotenv('google-cloud-trading-system/oanda_config.env')
./BRUTAL_DIAGNOSTIC_WHY_NO_EXECUTION.py:54:    socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("api-fxpractice.oanda.com", 443))
./BRUTAL_DIAGNOSTIC_WHY_NO_EXECUTION.py:65:    from src.core.oanda_client import OandaClient
./BRUTAL_DIAGNOSTIC_WHY_NO_EXECUTION.py:117:        if hasattr(order_mgr, 'place_order'):
./BRUTAL_DIAGNOSTIC_WHY_NO_EXECUTION.py:118:            print("✓ place_order method exists")
./BRUTAL_DIAGNOSTIC_WHY_NO_EXECUTION.py:120:            print("✗ FAILURE: place_order method missing")
./BRUTAL_DIAGNOSTIC_WHY_NO_EXECUTION.py:265:    yaml_path = "google-cloud-trading-system/accounts.yaml"
./BRUTAL_DIAGNOSTIC_WHY_NO_EXECUTION.py:268:        accounts = yaml_mgr.get_all_accounts()
./BRUTAL_DIAGNOSTIC_WHY_NO_EXECUTION.py:270:        print(f"✓ Found {len(accounts)} configured accounts")
./BRUTAL_DIAGNOSTIC_WHY_NO_EXECUTION.py:272:        active_count = sum(1 for acc in accounts if acc.get('active', False))
./BRUTAL_DIAGNOSTIC_WHY_NO_EXECUTION.py:273:        print(f"✓ Active accounts: {active_count}")
./BRUTAL_DIAGNOSTIC_WHY_NO_EXECUTION.py:277:            print("  → This is THE problem - all accounts disabled")
./BRUTAL_DIAGNOSTIC_WHY_NO_EXECUTION.py:279:        for acc in accounts[:3]:
./BRUTAL_DIAGNOSTIC_WHY_NO_EXECUTION.py:284:        print("✗ FAILURE: accounts.yaml not found")
./BRUTAL_DIAGNOSTIC_WHY_NO_EXECUTION.py:287:    print(f"✗ FAILURE checking accounts: {e}")
./BRUTAL_DIAGNOSTIC_WHY_NO_EXECUTION.py:374:    print("   cat oanda_config.env")
./stable_trading_system.py:22:from src.core.oanda_client import OandaClient
./stable_trading_system.py:31:        self.active_accounts = self.account_manager.get_active_accounts()
./stable_trading_system.py:33:        # Load accounts.yaml to get strategy mappings
./stable_trading_system.py:34:        self.accounts_config = self._load_accounts_config()
./stable_trading_system.py:41:        logger.info(f"🎯 STABLE SYSTEM initialized with {len(self.active_accounts)} accounts")
./stable_trading_system.py:43:    def _load_accounts_config(self):
./stable_trading_system.py:44:        """Load accounts configuration"""
./stable_trading_system.py:46:            config_path = '/Users/mac/quant_system_clean/google-cloud-trading-system/accounts.yaml'
./stable_trading_system.py:50:            logger.error(f"❌ Failed to load accounts config: {e}")
./stable_trading_system.py:56:            for account in self.accounts_config.get('accounts', []):
./stable_trading_system.py:123:        for account_id in self.active_accounts:
./stable_trading_system.py:152:                                for account in self.accounts_config.get('accounts', []):
./force_all_accounts_trade.py:4:This will place trades on ALL active accounts
./force_all_accounts_trade.py:20:from src.core.oanda_client import OandaClient
./force_all_accounts_trade.py:26:def force_trades_all_accounts():
./force_all_accounts_trade.py:27:    """Force place trades on ALL accounts"""
./force_all_accounts_trade.py:32:    active_accounts = account_manager.get_active_accounts()
./force_all_accounts_trade.py:34:    logger.info(f"📊 Found {len(active_accounts)} active accounts")
./force_all_accounts_trade.py:38:    for i, account_id in enumerate(active_accounts):
./force_all_accounts_trade.py:40:            logger.info(f"🎯 ACCOUNT {i+1}/{len(active_accounts)}: {account_id}")
./force_all_accounts_trade.py:133:            time.sleep(1)  # Brief pause between accounts
./force_all_accounts_trade.py:142:    force_trades_all_accounts()
./test_all_accounts.py:3:"""Place test trades on ALL accounts"""
./test_all_accounts.py:9:OANDA_API_KEY = settings.oanda_api_key
./test_all_accounts.py:14:BASE_URL = 'https://api-fxpractice.oanda.com/v3'
./test_all_accounts.py:27:def place_order(account_id, instrument, units):
./test_all_accounts.py:31:    url = f'{BASE_URL}/accounts/{account_id}/pricing'
./test_all_accounts.py:71:    url = f'{BASE_URL}/accounts/{account_id}/orders'
./test_all_accounts.py:89:print("Testing ALL accounts...")
./test_all_accounts.py:99:    result = place_order(account_id, instrument, units)
./test_websocket_playwright.py:4:Comprehensive testing of websocket connections and dashboard functionality
./test_websocket_playwright.py:46:    async def test_websocket_connection(self):
./test_websocket_playwright.py:146:            websocket_test_script = """
./test_websocket_playwright.py:154:                window.websocketConnected = true;
./test_websocket_playwright.py:160:                window.websocketConnected = false;
./test_websocket_playwright.py:166:                window.websocketMessages = messagesReceived;
./test_websocket_playwright.py:172:                window.websocketMessages = messagesReceived;
./test_websocket_playwright.py:178:                window.websocketMessages = messagesReceived;
./test_websocket_playwright.py:183:                window.websocketError = data;
./test_websocket_playwright.py:192:            await self.page.evaluate(websocket_test_script)
./test_websocket_playwright.py:198:            connected = await self.page.evaluate("window.websocketConnected")
./test_websocket_playwright.py:199:            messages = await self.page.evaluate("window.websocketMessages || 0")
./test_websocket_playwright.py:200:            error = await self.page.evaluate("window.websocketError")
./test_websocket_playwright.py:243:    async def test_websocket_stress(self):
./test_websocket_playwright.py:310:        websocket_ok = await tester.test_websocket_connection()
./test_websocket_playwright.py:316:        stress_ok = await tester.test_websocket_stress()
./test_websocket_playwright.py:319:        print(f"   WebSocket Connection: {'✅ PASS' if websocket_ok else '❌ FAIL'}")
./test_websocket_playwright.py:323:        overall_success = websocket_ok and playwright_ok and stress_ok
./send_gold_alert.py:15:env_path = os.path.join(os.path.dirname(__file__), 'google-cloud-trading-system', 'oanda_config.env')
./check_current_market_status.py:10:from core.oanda_client import OandaClient
./check_current_market_status.py:22:# Get all active accounts
./check_current_market_status.py:24:accounts = [a for a in yaml_mgr.get_all_accounts() if a.get('active', False)]
./check_current_market_status.py:26:print(f'📊 Checking {len(accounts)} active accounts...')
./check_current_market_status.py:30:account = accounts[0]
./check_current_market_status.py:49:for acc in accounts:
./check_current_market_status.py:65:# Check all accounts for positions
./check_current_market_status.py:70:for acc in accounts:
./check_current_market_status.py:91:# Check for pending orders
./check_current_market_status.py:95:for acc in accounts:
./check_current_market_status.py:98:        orders = client.get_pending_orders()
./check_current_market_status.py:99:        if orders:
./check_current_market_status.py:101:            for order in orders:
./check_current_market_status.py:105:            print(f"{acc['name']}: No pending orders")
./src/core/settings.py:22:    oanda_api_key: Optional[str]
./src/core/settings.py:23:    oanda_account_id: Optional[str]
./src/core/settings.py:24:    oanda_env: str  # practice|live
./src/core/settings.py:49:    def require_oanda(self) -> None:
./src/core/settings.py:50:        if not self.oanda_api_key:
./src/core/settings.py:52:        if not self.oanda_account_id:
./src/core/settings.py:72:    oanda_api_key = _get_env("OANDA_API_KEY")
./src/core/settings.py:73:    oanda_account_id = _get_env("OANDA_ACCOUNT_ID")
./src/core/settings.py:74:    oanda_env = (_get_env("OANDA_ENV") or "practice").lower()
./src/core/settings.py:75:    if oanda_env not in ("practice", "live"):
./src/core/settings.py:111:        oanda_api_key=oanda_api_key,
./src/core/settings.py:112:        oanda_account_id=oanda_account_id,
./src/core/settings.py:113:        oanda_env=oanda_env,
./monitor_cpi_tomorrow.py:18:OANDA_API_KEY = settings.oanda_api_key
./monitor_cpi_tomorrow.py:21:OANDA_URL = f'https://api-fx{OANDA_ENV}.oanda.com/v3/accounts/{OANDA_ACCOUNT}/pricing' if OANDA_ENV == "practice" else f"https://api-fxtrade.oanda.com/v3/accounts/{OANDA_ACCOUNT}/pricing"
./test_complete_system.py:43:        active_accounts = account_manager.get_active_accounts()
./test_complete_system.py:44:        print(f"✅ Account Manager: {len(active_accounts)} active accounts")
./test_complete_system.py:45:        for account_id in active_accounts:
./test_complete_system.py:66:        test_client = account_manager.get_account_client(active_accounts[0])
./test_complete_system.py:83:        test_client = account_manager.get_account_client(active_accounts[0])
./test_complete_system.py:116:    for account_id in active_accounts[:2]:  # Test first 2 accounts
./test_complete_system.py:167:        for account_id in active_accounts:
./test_complete_system.py:177:        for account_id in active_accounts:
./test_complete_system.py:192:        for account_id in active_accounts:
./force_trading_test.py:44:        active_accounts = account_manager.get_active_accounts()
./force_trading_test.py:45:        print(f"✅ {len(active_accounts)} active accounts loaded")
./force_trading_test.py:47:        for account_id in active_accounts:
./force_trading_test.py:66:    for account_id in active_accounts:
./force_trading_test.py:99:                    account_info = order_manager.oanda_client.get_account_info()
./force_trading_test.py:173:    print(f"✅ Accounts: {len(active_accounts)} active")
./test_dashboard_final.py:185:    async def test_websocket_connection(self):
./test_dashboard_final.py:288:    async def test_browser_websocket(self):
./test_dashboard_final.py:294:            websocket_test_script = """
./test_dashboard_final.py:310:                window.websocketConnected = true;
./test_dashboard_final.py:316:                window.websocketConnected = false;
./test_dashboard_final.py:323:                window.websocketMessages = messagesReceived;
./test_dashboard_final.py:324:                window.websocketMessageTypes = messageTypes;
./test_dashboard_final.py:331:                window.websocketMessages = messagesReceived;
./test_dashboard_final.py:332:                window.websocketMessageTypes = messageTypes;
./test_dashboard_final.py:339:                window.websocketMessages = messagesReceived;
./test_dashboard_final.py:340:                window.websocketMessageTypes = messageTypes;
./test_dashboard_final.py:347:                window.websocketMessages = messagesReceived;
./test_dashboard_final.py:348:                window.websocketMessageTypes = messageTypes;
./test_dashboard_final.py:355:                window.websocketMessages = messagesReceived;
./test_dashboard_final.py:356:                window.websocketMessageTypes = messageTypes;
./test_dashboard_final.py:361:                window.websocketError = data;
./test_dashboard_final.py:373:            await self.page.evaluate(websocket_test_script)
./test_dashboard_final.py:379:            connected = await self.page.evaluate("window.websocketConnected")
./test_dashboard_final.py:380:            messages = await self.page.evaluate("window.websocketMessages || 0")
./test_dashboard_final.py:381:            error = await self.page.evaluate("window.websocketError")
./test_dashboard_final.py:382:            message_types = await self.page.evaluate("window.websocketMessageTypes || []")
./test_dashboard_final.py:440:            ("WebSocket Connection", tester.test_websocket_connection),
./test_dashboard_final.py:442:            ("Browser WebSocket", tester.test_browser_websocket)
./fixed_sniper_system.py:22:from src.core.oanda_client import OandaClient
./fixed_sniper_system.py:33:        self.active_accounts = self.account_manager.get_active_accounts()
./fixed_sniper_system.py:41:        logger.info(f"🎯 FIXED SNIPER SYSTEM initialized with {len(self.active_accounts)} accounts")
./fixed_sniper_system.py:51:        # Get market data for all accounts
./fixed_sniper_system.py:52:        for account_id in self.active_accounts:
./playwright_websocket_test.py:4:Tests websocket connections, dashboard functionality, and real-time updates
./playwright_websocket_test.py:164:    async def test_websocket_connection(self):
./playwright_websocket_test.py:233:    async def test_websocket_in_browser(self):
./playwright_websocket_test.py:239:            websocket_test_script = """
./playwright_websocket_test.py:248:                window.websocketConnected = true;
./playwright_websocket_test.py:254:                window.websocketConnected = false;
./playwright_websocket_test.py:261:                window.websocketMessages = messagesReceived;
./playwright_websocket_test.py:269:                window.websocketMessages = messagesReceived;
./playwright_websocket_test.py:277:                window.websocketMessages = messagesReceived;
./playwright_websocket_test.py:285:                window.websocketMessages = messagesReceived;
./playwright_websocket_test.py:291:                window.websocketError = data;
./playwright_websocket_test.py:303:            await self.page.evaluate(websocket_test_script)
./playwright_websocket_test.py:309:            connected = await self.page.evaluate("window.websocketConnected")
./playwright_websocket_test.py:310:            messages = await self.page.evaluate("window.websocketMessages || 0")
./playwright_websocket_test.py:311:            error = await self.page.evaluate("window.websocketError")
./playwright_websocket_test.py:382:    async def test_websocket_stress(self):
./playwright_websocket_test.py:455:            ("WebSocket Connection", tester.test_websocket_connection),
./playwright_websocket_test.py:456:            ("Browser WebSocket", tester.test_websocket_in_browser),
./playwright_websocket_test.py:458:            ("WebSocket Stress", tester.test_websocket_stress)
./working_dashboard.py:28:    'accounts': [
./working_dashboard.py:63:        'accounts': len(dashboard_data['accounts']),
./working_dashboard.py:84:@app.route('/api/accounts')
./working_dashboard.py:85:def api_accounts():
./working_dashboard.py:88:        'accounts': dashboard_data['accounts'],
./working_dashboard.py:89:        'total_balance': sum(acc['balance'] for acc in dashboard_data['accounts']),
./EMERGENCY_FIX_IMMEDIATE.py:12:from core.oanda_client import OandaClient
./EMERGENCY_FIX_IMMEDIATE.py:51:accounts = yaml_mgr.get_all_accounts()
./EMERGENCY_FIX_IMMEDIATE.py:52:active_accounts = [a for a in accounts if a.get('active', False)]
./EMERGENCY_FIX_IMMEDIATE.py:54:print(f'Total accounts: {len(accounts)}')
./EMERGENCY_FIX_IMMEDIATE.py:55:print(f'Active accounts: {len(active_accounts)}')
./EMERGENCY_FIX_IMMEDIATE.py:57:for i, acc in enumerate(active_accounts[:3]):  # Show first 3
./comprehensive_dashboard_test.py:220:    async def test_websocket_connection_comprehensive(self):
./comprehensive_dashboard_test.py:296:    async def test_browser_websocket_comprehensive(self):
./comprehensive_dashboard_test.py:302:            websocket_test_script = """
./comprehensive_dashboard_test.py:321:                window.websocketConnected = true;
./comprehensive_dashboard_test.py:322:                window.websocketStats = {connects: 1, disconnects: 0};
./comprehensive_dashboard_test.py:328:                window.websocketConnected = false;
./comprehensive_dashboard_test.py:329:                if (window.websocketStats) window.websocketStats.disconnects += 1;
./comprehensive_dashboard_test.py:337:                window.websocketMessages = messagesReceived;
./comprehensive_dashboard_test.py:339:                window.websocketMessageTypes = messageTypes;
./comprehensive_dashboard_test.py:347:                window.websocketMessages = messagesReceived;
./comprehensive_dashboard_test.py:349:                window.websocketMessageTypes = messageTypes;
./comprehensive_dashboard_test.py:357:                window.websocketMessages = messagesReceived;
./comprehensive_dashboard_test.py:359:                window.websocketMessageTypes = messageTypes;
./comprehensive_dashboard_test.py:367:                window.websocketMessages = messagesReceived;
./comprehensive_dashboard_test.py:369:                window.websocketMessageTypes = messageTypes;
./comprehensive_dashboard_test.py:377:                window.websocketMessages = messagesReceived;
./comprehensive_dashboard_test.py:379:                window.websocketMessageTypes = messageTypes;
./comprehensive_dashboard_test.py:385:                window.websocketError = data;
./comprehensive_dashboard_test.py:386:                window.websocketErrors = errors;
./comprehensive_dashboard_test.py:399:            await self.page.evaluate(websocket_test_script)
./comprehensive_dashboard_test.py:405:            connected = await self.page.evaluate("window.websocketConnected")
./comprehensive_dashboard_test.py:406:            messages = await self.page.evaluate("window.websocketMessages || 0")
./comprehensive_dashboard_test.py:407:            error = await self.page.evaluate("window.websocketError")
./comprehensive_dashboard_test.py:409:            message_types = await self.page.evaluate("window.websocketMessageTypes || []")
./comprehensive_dashboard_test.py:410:            stats = await self.page.evaluate("window.websocketStats || {}")
./comprehensive_dashboard_test.py:411:            errors = await self.page.evaluate("window.websocketErrors || []")
./comprehensive_dashboard_test.py:562:            ("WebSocket Connection", tester.test_websocket_connection_comprehensive),
./comprehensive_dashboard_test.py:563:            ("Browser WebSocket", tester.test_browser_websocket_comprehensive),
./sniper_trading_system.py:22:from src.core.oanda_client import OandaClient
./sniper_trading_system.py:33:        self.active_accounts = self.account_manager.get_active_accounts()
./sniper_trading_system.py:42:        logger.info(f"🎯 SNIPER SYSTEM initialized with {len(self.active_accounts)} accounts")
./sniper_trading_system.py:137:        # Get market data for all accounts
./sniper_trading_system.py:138:        for account_id in self.active_accounts:
./cloud_declutter_v2/planned_deployment/ai_trading_system.py:63:ACCOUNTS_YAML_PATH = os.environ.get("ACCOUNTS_YAML_PATH", os.path.join(BASE_DIR, "src", "core", "accounts.yaml"))
./cloud_declutter_v2/planned_deployment/ai_trading_system.py:65:def load_accounts_from_secret_v2() -> Dict[str, Any] | None:
./cloud_declutter_v2/planned_deployment/ai_trading_system.py:77:                    return load_accounts(tf.name)
./cloud_declutter_v2/planned_deployment/ai_trading_system.py:80:        logging.error(f"Secret-based accounts load failed (v2): {exc}")
./cloud_declutter_v2/planned_deployment/ai_trading_system.py:86:    from price_feed import fetch_prices_for_accounts as cloud_price_fetch
./cloud_declutter_v2/planned_deployment/ai_trading_system.py:88:    from order_interface import place_order as cloud_place_order
./cloud_declutter_v2/planned_deployment/ai_trading_system.py:92:    cloud_place_order = None
./cloud_declutter_v2/planned_deployment/ai_trading_system.py:98:    from price_feed import fetch_prices_for_accounts as cloud_price_fetch
./cloud_declutter_v2/planned_deployment/ai_trading_system.py:100:    from order_interface import place_order as cloud_place_order
./cloud_declutter_v2/planned_deployment/ai_trading_system.py:104:    cloud_place_order = None
./cloud_declutter_v2/planned_deployment/ai_trading_system.py:121:def maybe_send_daily_report(cycle: int, cycles: int, accounts: list[str]):
./cloud_declutter_v2/planned_deployment/ai_trading_system.py:130:            msg = f"Daily PAPER report {today}: cycle {cycle}/{cycles}, accounts={accounts}"
./cloud_declutter_v2/planned_deployment/ai_trading_system.py:141:def load_accounts_from_secret() -> Dict[str, Any] | None:
./cloud_declutter_v2/planned_deployment/ai_trading_system.py:182:        logging.error(f"Secret-based accounts load failed: {exc}")
./cloud_declutter_v2/planned_deployment/ai_trading_system.py:186:def load_accounts(path: str) -> Dict[str, Any]:
./cloud_declutter_v2/planned_deployment/ai_trading_system.py:189:        secret_accounts = load_accounts_from_secret_v2()
./cloud_declutter_v2/planned_deployment/ai_trading_system.py:190:        if secret_accounts is not None:
./cloud_declutter_v2/planned_deployment/ai_trading_system.py:191:            return secret_accounts
./cloud_declutter_v2/planned_deployment/ai_trading_system.py:193:        logging.warning(f"Accounts YAML not found at {path}; continuing with empty accounts.")
./cloud_declutter_v2/planned_deployment/ai_trading_system.py:200:        logging.error(f"Failed to load accounts: {exc}")
./cloud_declutter_v2/planned_deployment/ai_trading_system.py:210:def load_accounts_from_secret_v2() -> Dict[str, Any] | None:
./cloud_declutter_v2/planned_deployment/ai_trading_system.py:235:        logging.error(f"Secret-based accounts load failed (v2): {exc}")
./cloud_declutter_v2/planned_deployment/ai_trading_system.py:239:def run_trading_loop(accounts: Dict[str, Any], cycles: int = 2, local_mock: bool = False) -> int:
./cloud_declutter_v2/planned_deployment/ai_trading_system.py:255:        mock_accounts = accounts or {
./cloud_declutter_v2/planned_deployment/ai_trading_system.py:266:                # Use live price feed for paper trading (no real orders)
./cloud_declutter_v2/planned_deployment/ai_trading_system.py:267:                for acc, cfg in (mock_accounts or {}).items():
./cloud_declutter_v2/planned_deployment/ai_trading_system.py:273:                    # Try with accounts first, if supported
./cloud_declutter_v2/planned_deployment/ai_trading_system.py:274:                    news = cloud_news_fetch(mock_accounts)
./cloud_declutter_v2/planned_deployment/ai_trading_system.py:289:                        prices = cloud_price_fetch(mock_accounts)
./cloud_declutter_v2/planned_deployment/ai_trading_system.py:294:                    for acc, cfg in (mock_accounts or {}).items():
./cloud_declutter_v2/planned_deployment/ai_trading_system.py:298:            signals = {acc: "mock_strategy" for acc in mock_accounts}
./cloud_declutter_v2/planned_deployment/ai_trading_system.py:300:            if cloud_place_order:
./cloud_declutter_v2/planned_deployment/ai_trading_system.py:304:                            placed = cloud_place_order(acc, sig)
./cloud_declutter_v2/planned_deployment/ai_trading_system.py:321:                "accounts": list(mock_accounts.keys()),
./cloud_declutter_v2/planned_deployment/ai_trading_system.py:327:            if 'mock_accounts' in locals():
./cloud_declutter_v2/planned_deployment/ai_trading_system.py:328:                maybe_send_daily_report(cycle, cycles, list(mock_accounts.keys()))
./cloud_declutter_v2/planned_deployment/ai_trading_system.py:341:    if not accounts:
./cloud_declutter_v2/planned_deployment/ai_trading_system.py:342:        logging.info("No accounts configured; nothing to run.")
./cloud_declutter_v2/planned_deployment/ai_trading_system.py:373:                data = load_accounts_from_secret_v2()
./cloud_declutter_v2/planned_deployment/ai_trading_system.py:379:    accounts = load_accounts(ACCOUNTS_YAML_PATH)
./cloud_declutter_v2/planned_deployment/ai_trading_system.py:380:    return run_trading_loop(accounts, cycles=args.cycles, local_mock=args.local_mock)
./cloud_declutter_v2/planned_deployment/tests/phase2_secret_simulator.py:3:Phase 2 secret mgmt simulation: verify that loading accounts.yaml from Secret Manager works
./cloud_declutter_v2/planned_deployment/tests/phase2_secret_simulator.py:31:    load_accounts_from_secret = getattr(ai_trading_system, "load_accounts_from_secret", None)
./cloud_declutter_v2/planned_deployment/tests/phase2_secret_simulator.py:32:    if not load_accounts_from_secret:
./cloud_declutter_v2/planned_deployment/tests/phase2_secret_simulator.py:33:        print("Cannot locate load_accounts_from_secret; ensure the loader exports it.")
./cloud_declutter_v2/planned_deployment/tests/phase2_secret_simulator.py:45:        loaded = load_accounts_from_secret()
./CRITICAL_FIXES_NOW.py:77:from core.oanda_client import OandaClient
./CRITICAL_FIXES_NOW.py:83:# Get accounts
./CRITICAL_FIXES_NOW.py:85:accounts = [a for a in yaml_mgr.get_all_accounts() if a.get('active', False)]
./CRITICAL_FIXES_NOW.py:87:print(f'Found {len(accounts)} active accounts')
./CRITICAL_FIXES_NOW.py:91:gbp_accounts = [a for a in accounts if 'GBP_USD' in a.get('instruments', [])]
./CRITICAL_FIXES_NOW.py:93:if gbp_accounts:
./CRITICAL_FIXES_NOW.py:94:    account = gbp_accounts[0]
./CRITICAL_FIXES_NOW.py:122:    print('❌ No GBP/USD accounts found')
./scripts/verify_env_no_leak.py:7:print("OANDA_API_KEY:", mark(settings.oanda_api_key))
./scripts/verify_env_no_leak.py:8:print("OANDA_ACCOUNT_ID:", mark(settings.oanda_account_id))
./scripts/verify_env_no_leak.py:9:print("OANDA_ENV:", settings.oanda_env)
./final_system_verification.py:42:        active_accounts = account_manager.get_active_accounts()
./final_system_verification.py:43:        print(f"✅ Account Manager: {len(active_accounts)} active accounts loaded")
./final_system_verification.py:46:        for account_id in active_accounts:
./final_system_verification.py:80:            test_client = account_manager.get_account_client(active_accounts[0])
./final_system_verification.py:114:            for account_id in active_accounts:
./final_system_verification.py:246:    print("   ✅ Account Manager: 3 active accounts loaded")
./final_system_verification.py:256:    print(f"   📊 Active Accounts: {len(active_accounts)}")
./automated_trading_system.py:17:OANDA_API_KEY = settings.oanda_api_key
./automated_trading_system.py:20:OANDA_BASE_URL = f"https://api-fx{OANDA_ENV}.oanda.com" if OANDA_ENV == "practice" else "https://api-fxtrade.oanda.com"
./automated_trading_system.py:21:OANDA_STREAM_URL = f"https://stream-fx{OANDA_ENV}.oanda.com" if OANDA_ENV == "practice" else "https://stream-fxtrade.oanda.com"
./automated_trading_system.py:61:            url = f"{OANDA_BASE_URL}/v3/accounts/{self.account_id}"
./automated_trading_system.py:75:            url = f"{OANDA_BASE_URL}/v3/accounts/{self.account_id}/pricing"
./automated_trading_system.py:243:            # Adjust units for SELL orders
./automated_trading_system.py:260:            url = f"{OANDA_BASE_URL}/v3/accounts/{self.account_id}/orders"
./automated_trading_system.py:320:            url = f"{OANDA_BASE_URL}/v3/accounts/{self.account_id}/positions"
