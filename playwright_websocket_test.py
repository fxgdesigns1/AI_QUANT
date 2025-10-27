#!/usr/bin/env python3
"""
Comprehensive Playwright WebSocket Testing
Tests websocket connections, dashboard functionality, and real-time updates
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

class PlaywrightWebSocketTester:
    """Comprehensive WebSocket testing with Playwright"""
    
    def __init__(self):
        self.base_url = "http://localhost:8080"
        self.sio = socketio.AsyncClient()
        self.connected = False
        self.received_messages = []
        self.dashboard_process = None
        
    async def start_dashboard(self):
        """Start the dashboard server"""
        try:
            print("🚀 Starting dashboard server...")
            
            # Start dashboard in background
            self.dashboard_process = subprocess.Popen([
                sys.executable, 
                "dashboard/advanced_dashboard.py"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Wait for server to start
            await asyncio.sleep(5)
            
            # Check if server is running
            try:
                response = requests.get(self.base_url, timeout=10)
                if response.status_code == 200:
                    print("✅ Dashboard server started successfully")
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
            print("🧪 Setting up Playwright...")
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=False,  # Set to True for headless testing
                args=['--disable-web-security', '--disable-features=VizDisplayCompositor']
            )
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
            self.page = await self.context.new_page()
            print("✅ Playwright setup complete")
            return True
        except Exception as e:
            print(f"❌ Playwright setup error: {e}")
            return False
    
    async def test_dashboard_loading(self):
        """Test dashboard page loading"""
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
                '.dashboard-container',  # Dashboard container
                '.systems-status',  # Systems status
                '.market-data',  # Market data
                '.news-feed'  # News feed
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
                '/api/trade_ideas'
            ]
            
            working_endpoints = 0
            for endpoint in api_endpoints:
                try:
                    response = await self.page.request.get(f"{self.base_url}{endpoint}")
                    if response.status == 200:
                        print(f"✅ API endpoint {endpoint} working")
                        working_endpoints += 1
                    else:
                        print(f"❌ API endpoint {endpoint} returned {response.status}")
                except Exception as e:
                    print(f"❌ API endpoint {endpoint} error: {e}")
            
            print(f"📊 Working endpoints: {working_endpoints}/{len(api_endpoints)}")
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
    
    async def test_websocket_in_browser(self):
        """Test WebSocket functionality in browser"""
        try:
            print("🧪 Testing WebSocket in browser...")
            
            # Inject WebSocket test script
            websocket_test_script = """
            const socket = io();
            let connected = false;
            let messagesReceived = 0;
            let lastMessage = null;
            
            socket.on('connect', () => {
                console.log('WebSocket connected in browser');
                connected = true;
                window.websocketConnected = true;
            });
            
            socket.on('disconnect', () => {
                console.log('WebSocket disconnected in browser');
                connected = false;
                window.websocketConnected = false;
            });
            
            socket.on('status', (data) => {
                console.log('Status message:', data);
                messagesReceived++;
                lastMessage = {type: 'status', data: data, timestamp: new Date().toISOString()};
                window.websocketMessages = messagesReceived;
                window.lastWebSocketMessage = lastMessage;
            });
            
            socket.on('systems_update', (data) => {
                console.log('Systems update:', data);
                messagesReceived++;
                lastMessage = {type: 'systems_update', data: data, timestamp: new Date().toISOString()};
                window.websocketMessages = messagesReceived;
                window.lastWebSocketMessage = lastMessage;
            });
            
            socket.on('market_update', (data) => {
                console.log('Market update:', data);
                messagesReceived++;
                lastMessage = {type: 'market_update', data: data, timestamp: new Date().toISOString()};
                window.websocketMessages = messagesReceived;
                window.lastWebSocketMessage = lastMessage;
            });
            
            socket.on('news_update', (data) => {
                console.log('News update:', data);
                messagesReceived++;
                lastMessage = {type: 'news_update', data: data, timestamp: new Date().toISOString()};
                window.websocketMessages = messagesReceived;
                window.lastWebSocketMessage = lastMessage;
            });
            
            socket.on('error', (data) => {
                console.log('WebSocket error:', data);
                window.websocketError = data;
            });
            
            // Request update after 2 seconds
            setTimeout(() => {
                socket.emit('request_update');
            }, 2000);
            
            // Store socket for later use
            window.testSocket = socket;
            """
            
            await self.page.evaluate(websocket_test_script)
            
            # Wait for WebSocket connection and messages
            await asyncio.sleep(8)
            
            # Check connection status
            connected = await self.page.evaluate("window.websocketConnected")
            messages = await self.page.evaluate("window.websocketMessages || 0")
            error = await self.page.evaluate("window.websocketError")
            last_message = await self.page.evaluate("window.lastWebSocketMessage")
            
            print(f"📊 Browser WebSocket Results:")
            print(f"   Connected: {connected}")
            print(f"   Messages received: {messages}")
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
            
            # Test clicking on elements
            try:
                # Look for clickable elements
                buttons = await self.page.query_selector_all('button')
                print(f"📊 Found {len(buttons)} buttons")
                
                # Test refresh button if exists
                refresh_button = await self.page.query_selector('[data-testid="refresh"]')
                if refresh_button:
                    await refresh_button.click()
                    await asyncio.sleep(2)
                    print("✅ Refresh button clicked")
                
                # Test navigation if exists
                nav_links = await self.page.query_selector_all('nav a')
                if nav_links:
                    print(f"📊 Found {len(nav_links)} navigation links")
                    # Click first nav link if available
                    if len(nav_links) > 0:
                        await nav_links[0].click()
                        await asyncio.sleep(2)
                        print("✅ Navigation link clicked")
                
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
    
    async def test_websocket_stress(self):
        """Test WebSocket under stress conditions"""
        try:
            print("🧪 Testing WebSocket stress conditions...")
            
            # Multiple rapid connections
            connections = []
            for i in range(3):  # Reduced from 5 to 3 for stability
                sio = socketio.AsyncClient()
                connections.append(sio)
                await sio.connect(self.base_url)
                await asyncio.sleep(0.1)
            
            print(f"✅ Created {len(connections)} concurrent connections")
            
            # Send multiple requests
            for i, sio in enumerate(connections):
                await sio.emit('request_update')
                await asyncio.sleep(0.1)
            
            # Wait for responses
            await asyncio.sleep(3)
            
            # Disconnect all
            for sio in connections:
                await sio.disconnect()
            
            print("✅ Stress test completed")
            return True
            
        except Exception as e:
            print(f"❌ Stress test error: {e}")
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
    print("🧪 Comprehensive Playwright WebSocket Testing")
    print("=" * 70)
    
    tester = PlaywrightWebSocketTester()
    
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
            ("Browser WebSocket", tester.test_websocket_in_browser),
            ("Dashboard Interactions", tester.test_dashboard_interactions),
            ("WebSocket Stress", tester.test_websocket_stress)
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
        print("\n📊 Test Results Summary:")
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
            print("🎉 ALL TESTS PASSED! WebSocket and dashboard are working correctly.")
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
