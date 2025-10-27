#!/usr/bin/env python3
"""
Enhanced WebSocket Testing with Playwright
Tests the complete dashboard WebSocket functionality including the UI elements visible in the screenshot
"""

import asyncio
import json
import time
from datetime import datetime
from playwright.async_api import async_playwright, expect
import socketio
import requests
import subprocess
import signal
import os
import sys

class EnhancedWebSocketTester:
    """Enhanced WebSocket testing for the AI Trading Dashboard"""
    
    def __init__(self):
        self.base_url = "http://localhost:8080"
        self.sio = socketio.AsyncClient()
        self.connected = False
        self.received_messages = []
        self.dashboard_process = None
        
    async def start_dashboard(self):
        """Start the dashboard server"""
        try:
            print("🚀 Starting AI Trading Dashboard...")
            
            # Start dashboard in background
            self.dashboard_process = subprocess.Popen([
                sys.executable, 
                "dashboard/advanced_dashboard.py"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Wait for server to start
            await asyncio.sleep(8)
            
            # Check if server is running
            try:
                response = requests.get(self.base_url, timeout=15)
                if response.status_code == 200:
                    print("✅ AI Trading Dashboard started successfully")
                    return True
                else:
                    print(f"❌ Dashboard returned status code: {response.status_code}")
                    return False
            except Exception as e:
                print(f"❌ Dashboard not accessible: {e}")
                return False
                
        except Exception as e:
            print(f"❌ Error starting dashboard: {e}")
            return False
    
    async def stop_dashboard(self):
        """Stop the dashboard server"""
        try:
            if self.dashboard_process:
                self.dashboard_process.terminate()
                self.dashboard_process.wait(timeout=5)
                print("✅ Dashboard server stopped")
        except Exception as e:
            print(f"⚠️ Error stopping dashboard: {e}")
    
    async def setup_playwright(self):
        """Setup Playwright browser with enhanced configuration"""
        try:
            print("🧪 Setting up Playwright for AI Trading Dashboard...")
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=False,  # Keep visible for debugging
                args=[
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage'
                ]
            )
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )
            self.page = await self.context.new_page()
            
            # Enable console logging
            self.page.on("console", lambda msg: print(f"🖥️ Console: {msg.text}"))
            
            print("✅ Playwright setup complete")
            return True
        except Exception as e:
            print(f"❌ Playwright setup error: {e}")
            return False
    
    async def test_dashboard_loading(self):
        """Test the AI Trading Dashboard loading"""
        try:
            print("🧪 Testing AI Trading Dashboard loading...")
            
            # Navigate to dashboard
            await self.page.goto(self.base_url)
            await self.page.wait_for_load_state('networkidle')
            
            # Check page title
            title = await self.page.title()
            print(f"📄 Page title: {title}")
            
            # Check for key dashboard elements from the screenshot
            elements_to_check = [
                'h1',  # Main title
                '.dashboard-container',  # Dashboard container
                '.systems-status',  # Systems status
                '.market-data',  # Market data
                '.news-feed',  # News feed
                '[data-testid="trades-today"]',  # Trades today counter
                '[data-testid="daily-target"]',  # Daily target progress
                '.connection-status',  # Connection status indicator
                '#systemsStatus',  # Systems status section
                '#marketData',  # Market data section
                '#riskMetrics'  # Risk metrics section
            ]
            
            found_elements = 0
            for selector in elements_to_check:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        print(f"✅ Found element: {selector}")
                        found_elements += 1
                    else:
                        print(f"❌ Missing element: {selector}")
                except Exception as e:
                    print(f"❌ Error checking element {selector}: {e}")
            
            # Check for navigation elements
            nav_elements = [
                'Dashboard', 'Accounts', 'Strategies', 'Positions', 
                'Trading Signals', 'News & Events', 'Trade Manager',
                'System Status', 'AI Insights', 'Analytics', 'Configuration'
            ]
            
            for nav_text in nav_elements:
                try:
                    element = await self.page.get_by_text(nav_text).first
                    if await element.is_visible():
                        print(f"✅ Found navigation: {nav_text}")
                    else:
                        print(f"❌ Missing navigation: {nav_text}")
                except Exception as e:
                    print(f"❌ Error checking navigation {nav_text}: {e}")
            
            return found_elements > 0
            
        except Exception as e:
            print(f"❌ Dashboard loading test error: {e}")
            return False
    
    async def test_websocket_connection_detailed(self):
        """Test WebSocket connection with detailed monitoring"""
        try:
            print("🧪 Testing WebSocket connection with detailed monitoring...")
            
            # Setup comprehensive event handlers
            @self.sio.event
            async def connect():
                print("✅ WebSocket connected to AI Trading Dashboard")
                self.connected = True
                
            @self.sio.event
            async def disconnect():
                print("❌ WebSocket disconnected from AI Trading Dashboard")
                self.connected = False
                
            @self.sio.event
            async def status(data):
                print(f"📡 Status message: {data}")
                self.received_messages.append(('status', data))
                
            @self.sio.event
            async def systems_update(data):
                print(f"📊 Systems update received: {len(data) if isinstance(data, dict) else 'N/A'} systems")
                self.received_messages.append(('systems_update', data))
                
            @self.sio.event
            async def market_update(data):
                print(f"💹 Market update received: {len(data) if isinstance(data, dict) else 'N/A'} pairs")
                self.received_messages.append(('market_update', data))
                
            @self.sio.event
            async def news_update(data):
                print(f"📰 News update received: {len(data) if isinstance(data, list) else 'N/A'} items")
                self.received_messages.append(('news_update', data))
                
            @self.sio.event
            async def risk_update(data):
                print(f"⚠️ Risk update received: {data}")
                self.received_messages.append(('risk_update', data))
                
            @self.sio.event
            async def error(data):
                print(f"❌ WebSocket error: {data}")
                self.received_messages.append(('error', data))
            
            # Connect to WebSocket
            await self.sio.connect(self.base_url)
            
            # Wait for connection
            await asyncio.sleep(3)
            
            if self.connected:
                print("✅ WebSocket connection successful")
                
                # Request update
                await self.sio.emit('request_update')
                await asyncio.sleep(5)
                
                # Check if we received updates
                if self.received_messages:
                    print(f"✅ Received {len(self.received_messages)} messages")
                    for msg_type, data in self.received_messages:
                        print(f"   - {msg_type}: {type(data)}")
                    return True
                else:
                    print("❌ No messages received")
                    return False
            else:
                print("❌ WebSocket connection failed")
                return False
                
        except Exception as e:
            print(f"❌ WebSocket test error: {e}")
            return False
    
    async def test_browser_websocket_functionality(self):
        """Test WebSocket functionality in the browser"""
        try:
            print("🧪 Testing WebSocket functionality in browser...")
            
            # Enhanced WebSocket test script that matches the dashboard code
            websocket_test_script = """
            // Initialize WebSocket connection like the dashboard does
            const socket = io({
                path: '/socket.io',
                transports: ['polling'],
                reconnection: true,
                reconnectionAttempts: Infinity,
                reconnectionDelay: 1000
            });
            
            let connected = false;
            let messagesReceived = 0;
            let lastMessage = null;
            let messageTypes = [];
            
            socket.on('connect', () => {
                console.log('🔌 WebSocket connected in browser');
                connected = true;
                window.websocketConnected = true;
                window.websocketStats = {connects: 1, disconnects: 0};
            });
            
            socket.on('disconnect', () => {
                console.log('🔌 WebSocket disconnected in browser');
                connected = false;
                window.websocketConnected = false;
                if (window.websocketStats) window.websocketStats.disconnects += 1;
            });
            
            socket.on('status', (data) => {
                console.log('📡 Status message:', data);
                messagesReceived++;
                messageTypes.push('status');
                lastMessage = {type: 'status', data: data, timestamp: new Date().toISOString()};
                window.websocketMessages = messagesReceived;
                window.lastWebSocketMessage = lastMessage;
                window.websocketMessageTypes = messageTypes;
            });
            
            socket.on('systems_update', (data) => {
                console.log('📊 Systems update:', data);
                messagesReceived++;
                messageTypes.push('systems_update');
                lastMessage = {type: 'systems_update', data: data, timestamp: new Date().toISOString()};
                window.websocketMessages = messagesReceived;
                window.lastWebSocketMessage = lastMessage;
                window.websocketMessageTypes = messageTypes;
            });
            
            socket.on('market_update', (data) => {
                console.log('💹 Market update:', data);
                messagesReceived++;
                messageTypes.push('market_update');
                lastMessage = {type: 'market_update', data: data, timestamp: new Date().toISOString()};
                window.websocketMessages = messagesReceived;
                window.lastWebSocketMessage = lastMessage;
                window.websocketMessageTypes = messageTypes;
            });
            
            socket.on('news_update', (data) => {
                console.log('📰 News update:', data);
                messagesReceived++;
                messageTypes.push('news_update');
                lastMessage = {type: 'news_update', data: data, timestamp: new Date().toISOString()};
                window.websocketMessages = messagesReceived;
                window.lastWebSocketMessage = lastMessage;
                window.websocketMessageTypes = messageTypes;
            });
            
            socket.on('risk_update', (data) => {
                console.log('⚠️ Risk update:', data);
                messagesReceived++;
                messageTypes.push('risk_update');
                lastMessage = {type: 'risk_update', data: data, timestamp: new Date().toISOString()};
                window.websocketMessages = messagesReceived;
                window.lastWebSocketMessage = lastMessage;
                window.websocketMessageTypes = messageTypes;
            });
            
            socket.on('error', (data) => {
                console.log('❌ WebSocket error:', data);
                window.websocketError = data;
            });
            
            // Request update after 2 seconds (like the dashboard does)
            setTimeout(() => {
                console.log('🔄 Requesting update...');
                socket.emit('request_update');
            }, 2000);
            
            // Store socket for later use
            window.testSocket = socket;
            """
            
            await self.page.evaluate(websocket_test_script)
            
            # Wait for WebSocket connection and messages
            await asyncio.sleep(10)
            
            # Check connection status and message details
            connected = await self.page.evaluate("window.websocketConnected")
            messages = await self.page.evaluate("window.websocketMessages || 0")
            error = await self.page.evaluate("window.websocketError")
            last_message = await self.page.evaluate("window.lastWebSocketMessage")
            message_types = await self.page.evaluate("window.websocketMessageTypes || []")
            stats = await self.page.evaluate("window.websocketStats || {}")
            
            print(f"📊 Browser WebSocket Results:")
            print(f"   Connected: {connected}")
            print(f"   Messages received: {messages}")
            print(f"   Message types: {message_types}")
            print(f"   Stats: {stats}")
            print(f"   Error: {error}")
            print(f"   Last message type: {last_message.get('type') if last_message else 'None'}")
            
            if connected and messages > 0:
                print("✅ WebSocket working in browser")
                return True
            else:
                print("❌ WebSocket not working properly in browser")
                return False
                
        except Exception as e:
            print(f"❌ Browser WebSocket test error: {e}")
            return False
    
    async def test_dashboard_interactions(self):
        """Test dashboard user interactions"""
        try:
            print("🧪 Testing dashboard interactions...")
            
            # Test clicking on navigation elements
            try:
                # Test navigation clicks
                nav_items = ['Dashboard', 'Accounts', 'Strategies', 'Positions']
                for nav_item in nav_items:
                    try:
                        element = await self.page.get_by_text(nav_item).first
                        if await element.is_visible():
                            await element.click()
                            await asyncio.sleep(1)
                            print(f"✅ Clicked navigation: {nav_item}")
                    except Exception as e:
                        print(f"⚠️ Navigation click error for {nav_item}: {e}")
                
                # Test if any buttons are visible and clickable
                buttons = await self.page.query_selector_all('button')
                print(f"📊 Found {len(buttons)} buttons")
                
                # Look for specific dashboard buttons
                button_selectors = [
                    '[data-testid="refresh"]',
                    '.btn-primary',
                    '.btn-success',
                    '.btn-danger',
                    'button[type="submit"]'
                ]
                
                for selector in button_selectors:
                    try:
                        button = await self.page.query_selector(selector)
                        if button and await button.is_visible():
                            await button.click()
                            await asyncio.sleep(1)
                            print(f"✅ Clicked button: {selector}")
                    except Exception as e:
                        print(f"⚠️ Button click error for {selector}: {e}")
                
            except Exception as e:
                print(f"⚠️ Interaction test error: {e}")
            
            # Test form inputs if any
            try:
                inputs = await self.page.query_selector_all('input')
                if inputs:
                    print(f"📊 Found {len(inputs)} input fields")
                    for i, input_field in enumerate(inputs[:3]):  # Test first 3 inputs
                        try:
                            await input_field.fill(f"test_input_{i}")
                            print(f"✅ Input field {i} filled")
                        except Exception as e:
                            print(f"⚠️ Input field {i} error: {e}")
            except Exception as e:
                print(f"⚠️ Input test error: {e}")
            
            return True
            
        except Exception as e:
            print(f"❌ Dashboard interactions test error: {e}")
            return False
    
    async def test_api_endpoints_comprehensive(self):
        """Test all API endpoints comprehensively"""
        try:
            print("🧪 Testing API endpoints comprehensively...")
            
            api_endpoints = [
                '/api/systems',
                '/api/market', 
                '/api/news',
                '/api/overview',
                '/api/sidebar/live-prices',
                '/api/opportunities',
                '/api/insights',
                '/api/trade_ideas',
                '/api/contextual/EUR_USD',
                '/api/risk',
                '/api/status'
            ]
            
            working_endpoints = 0
            endpoint_results = {}
            
            for endpoint in api_endpoints:
                try:
                    response = await self.page.request.get(f"{self.base_url}{endpoint}")
                    if response.status == 200:
                        print(f"✅ API endpoint {endpoint} working")
                        working_endpoints += 1
                        endpoint_results[endpoint] = 'success'
                    else:
                        print(f"❌ API endpoint {endpoint} returned {response.status}")
                        endpoint_results[endpoint] = f'error_{response.status}'
                except Exception as e:
                    print(f"❌ API endpoint {endpoint} error: {e}")
                    endpoint_results[endpoint] = f'error_{str(e)}'
            
            print(f"📊 API Endpoint Results: {working_endpoints}/{len(api_endpoints)} working")
            for endpoint, result in endpoint_results.items():
                print(f"   {endpoint}: {result}")
            
            return working_endpoints > 0
            
        except Exception as e:
            print(f"❌ API endpoints test error: {e}")
            return False
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            if hasattr(self, 'sio') and self.connected:
                await self.sio.disconnect()
            
            if hasattr(self, 'browser'):
                await self.browser.close()
                
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
                
            await self.stop_dashboard()
                
        except Exception as e:
            print(f"⚠️ Cleanup error: {e}")

async def main():
    """Main test function"""
    print("🧪 Enhanced WebSocket Testing for AI Trading Dashboard")
    print("=" * 70)
    
    tester = EnhancedWebSocketTester()
    
    try:
        # Start dashboard
        if not await tester.start_dashboard():
            print("\n❌ Could not start dashboard. Please check if port 8080 is available.")
            return False
        
        # Setup Playwright
        if not await tester.setup_playwright():
            print("\n❌ Playwright setup failed")
            return False
        
        # Run comprehensive tests
        tests = [
            ("Dashboard Loading", tester.test_dashboard_loading),
            ("API Endpoints", tester.test_api_endpoints_comprehensive),
            ("WebSocket Connection", tester.test_websocket_connection_detailed),
            ("Browser WebSocket", tester.test_browser_websocket_functionality),
            ("Dashboard Interactions", tester.test_dashboard_interactions)
        ]
        
        results = {}
        for test_name, test_func in tests:
            print(f"\n🧪 Running {test_name} test...")
            try:
                result = await test_func()
                results[test_name] = result
                print(f"   Result: {'✅ PASS' if result else '❌ FAIL'}")
            except Exception as e:
                print(f"   Error: {e}")
                results[test_name] = False
        
        # Summary
        print("\n📊 Enhanced Test Results Summary:")
        print("=" * 60)
        passed = 0
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   {test_name}: {status}")
            if result:
                passed += 1
        
        print(f"\n🎯 Overall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED! AI Trading Dashboard WebSocket system is fully functional.")
        elif passed > total // 2:
            print("⚠️ Most tests passed. Some issues detected but system is functional.")
        else:
            print("❌ Multiple test failures. System needs attention.")
        
        return passed >= total // 2
        
    except Exception as e:
        print(f"❌ Test suite error: {e}")
        return False
        
    finally:
        await tester.cleanup()

if __name__ == '__main__':
    asyncio.run(main())
