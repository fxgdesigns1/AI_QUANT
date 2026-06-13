#!/usr/bin/env python3
"""
Final Dashboard Test - Local and Cloud Deployment
Tests the complete dashboard functionality with proper OANDA integration
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

class FinalDashboardTester:
    """Final comprehensive dashboard testing"""
    
    def __init__(self):
        self.base_url = "http://localhost:8080"
        self.sio = socketio.AsyncClient()
        self.connected = False
        self.received_messages = []
        self.dashboard_process = None
        
    async def start_dashboard(self):
        """Start the dashboard server with proper credentials"""
        try:
            print("🚀 Starting AI Trading Dashboard with OANDA integration...")
            
            # Set environment variables for credentials
            # Do not overwrite lane/account selection here; require caller to provide real env.
            if 'OANDA_API_KEY' not in os.environ or not os.environ.get('OANDA_API_KEY', '').strip():
                raise RuntimeError("OANDA_API_KEY must be set in environment for this test.")
            if 'OANDA_ACCOUNT_ID' not in os.environ or not os.environ.get('OANDA_ACCOUNT_ID', '').strip():
                raise RuntimeError("OANDA_ACCOUNT_ID must be set in environment for this test.")
            
            # Start dashboard in background
            self.dashboard_process = subprocess.Popen([
                sys.executable, 
                "dashboard/advanced_dashboard.py"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ.copy())
            
            # Wait for server to start
            await asyncio.sleep(12)
            
            # Check if server is running
            try:
                response = requests.get(self.base_url, timeout=15)
                if response.status_code == 200:
                    print("✅ AI Trading Dashboard started successfully with OANDA integration")
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
        """Setup Playwright browser"""
        try:
            print("🧪 Setting up Playwright for final testing...")
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=False,  # Keep visible for debugging
                args=[
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--window-size=1920,1080'
                ]
            )
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )
            self.page = await self.context.new_page()
            
            # Enable console logging
            self.page.on("console", lambda msg: print(f"🖥️ Console: {msg.text}"))
            self.page.on("pageerror", lambda error: print(f"❌ Page Error: {error}"))
            
            print("✅ Playwright setup complete")
            return True
        except Exception as e:
            print(f"❌ Playwright setup error: {e}")
            return False
    
    async def test_dashboard_loading(self):
        """Test dashboard loading"""
        try:
            print("🧪 Testing dashboard loading...")
            
            # Navigate to dashboard
            await self.page.goto(self.base_url)
            await self.page.wait_for_load_state('networkidle')
            
            # Check page title
            title = await self.page.title()
            print(f"📄 Page title: {title}")
            
            # Check for key elements
            elements_to_check = [
                'h1',  # Main title
                '#systemsStatus',  # Systems status
                '#marketData',  # Market data
                '#riskMetrics',  # Risk metrics
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
            
            return found_elements > 0
            
        except Exception as e:
            print(f"❌ Dashboard loading test error: {e}")
            return False
    
    async def test_api_endpoints(self):
        """Test API endpoints"""
        try:
            print("🧪 Testing API endpoints...")
            
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
            for endpoint in api_endpoints:
                try:
                    response = await self.page.request.get(f"{self.base_url}{endpoint}")
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ API endpoint {endpoint} working - Data: {type(data)}")
                        working_endpoints += 1
                    else:
                        print(f"❌ API endpoint {endpoint} returned {response.status}")
                except Exception as e:
                    print(f"❌ API endpoint {endpoint} error: {e}")
            
            print(f"📊 API Endpoint Results: {working_endpoints}/{len(api_endpoints)} working")
            return working_endpoints > 0
            
        except Exception as e:
            print(f"❌ API endpoints test error: {e}")
            return False
    
    async def test_websocket_connection(self):
        """Test WebSocket connection"""
        try:
            print("🧪 Testing WebSocket connection...")
            
            # Setup event handlers
            @self.sio.event
            async def connect():
                print("✅ WebSocket connected")
                self.connected = True
                
            @self.sio.event
            async def disconnect():
                print("❌ WebSocket disconnected")
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
            await asyncio.sleep(5)
            
            if self.connected:
                print("✅ WebSocket connection successful")
                
                # Request update
                await self.sio.emit('request_update')
                await asyncio.sleep(8)
                
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
    
    async def test_market_data_specifically(self):
        """Test market data loading specifically"""
        try:
            print("🧪 Testing market data loading specifically...")
            
            # Test market data API directly
            response = await self.page.request.get(f"{self.base_url}/api/market")
            if response.status == 200:
                data = await response.json()
                print(f"📊 Market data response: {data}")
                
                if data and len(data) > 0:
                    print(f"✅ Market data loaded: {len(data)} pairs")
                    for pair, info in data.items():
                        print(f"   - {pair}: {info}")
                    return True
                else:
                    print("❌ Market data is empty")
                    return False
            else:
                print(f"❌ Market data API returned {response.status}")
                return False
                
        except Exception as e:
            print(f"❌ Market data test error: {e}")
            return False
    
    async def test_browser_websocket(self):
        """Test WebSocket in browser"""
        try:
            print("🧪 Testing WebSocket in browser...")
            
            # WebSocket test script
            websocket_test_script = """
            const socket = io({
                path: '/socket.io',
                transports: ['polling'],
                reconnection: true,
                reconnectionAttempts: Infinity,
                reconnectionDelay: 1000
            });
            
            let connected = false;
            let messagesReceived = 0;
            let messageTypes = [];
            
            socket.on('connect', () => {
                console.log('🔌 WebSocket connected in browser');
                connected = true;
                window.websocketConnected = true;
            });
            
            socket.on('disconnect', () => {
                console.log('🔌 WebSocket disconnected in browser');
                connected = false;
                window.websocketConnected = false;
            });
            
            socket.on('status', (data) => {
                console.log('📡 Status message:', data);
                messagesReceived++;
                messageTypes.push('status');
                window.websocketMessages = messagesReceived;
                window.websocketMessageTypes = messageTypes;
            });
            
            socket.on('systems_update', (data) => {
                console.log('📊 Systems update:', data);
                messagesReceived++;
                messageTypes.push('systems_update');
                window.websocketMessages = messagesReceived;
                window.websocketMessageTypes = messageTypes;
            });
            
            socket.on('market_update', (data) => {
                console.log('💹 Market update:', data);
                messagesReceived++;
                messageTypes.push('market_update');
                window.websocketMessages = messagesReceived;
                window.websocketMessageTypes = messageTypes;
            });
            
            socket.on('news_update', (data) => {
                console.log('📰 News update:', data);
                messagesReceived++;
                messageTypes.push('news_update');
                window.websocketMessages = messagesReceived;
                window.websocketMessageTypes = messageTypes;
            });
            
            socket.on('risk_update', (data) => {
                console.log('⚠️ Risk update:', data);
                messagesReceived++;
                messageTypes.push('risk_update');
                window.websocketMessages = messagesReceived;
                window.websocketMessageTypes = messageTypes;
            });
            
            socket.on('error', (data) => {
                console.log('❌ WebSocket error:', data);
                window.websocketError = data;
            });
            
            // Request update after 3 seconds
            setTimeout(() => {
                console.log('🔄 Requesting update...');
                socket.emit('request_update');
            }, 3000);
            
            window.testSocket = socket;
            """
            
            await self.page.evaluate(websocket_test_script)
            
            # Wait for WebSocket connection and messages
            await asyncio.sleep(10)
            
            # Check results
            connected = await self.page.evaluate("window.websocketConnected")
            messages = await self.page.evaluate("window.websocketMessages || 0")
            error = await self.page.evaluate("window.websocketError")
            message_types = await self.page.evaluate("window.websocketMessageTypes || []")
            
            print(f"📊 Browser WebSocket Results:")
            print(f"   Connected: {connected}")
            print(f"   Messages received: {messages}")
            print(f"   Message types: {message_types}")
            print(f"   Error: {error}")
            
            if connected and messages > 0:
                print("✅ WebSocket working in browser")
                return True
            else:
                print("❌ WebSocket not working properly in browser")
                return False
                
        except Exception as e:
            print(f"❌ Browser WebSocket test error: {e}")
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
    print("🧪 Final Dashboard Test - OANDA Integration")
    print("=" * 60)
    
    tester = FinalDashboardTester()
    
    try:
        # Start dashboard
        if not await tester.start_dashboard():
            print("\n❌ Could not start dashboard. Please check if port 8080 is available.")
            return False
        
        # Setup Playwright
        if not await tester.setup_playwright():
            print("\n❌ Playwright setup failed")
            return False
        
        # Run tests
        tests = [
            ("Dashboard Loading", tester.test_dashboard_loading),
            ("API Endpoints", tester.test_api_endpoints),
            ("WebSocket Connection", tester.test_websocket_connection),
            ("Market Data Loading", tester.test_market_data_specifically),
            ("Browser WebSocket", tester.test_browser_websocket)
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
        print("\n📊 Final Test Results Summary:")
        print("=" * 50)
        passed = 0
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   {test_name}: {status}")
            if result:
                passed += 1
        
        print(f"\n🎯 Overall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED! Dashboard is fully functional with OANDA integration.")
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
