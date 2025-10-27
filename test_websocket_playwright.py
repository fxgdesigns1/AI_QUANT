#!/usr/bin/env python3
"""
WebSocket Testing with Playwright
Comprehensive testing of websocket connections and dashboard functionality
"""

import asyncio
import json
import time
from datetime import datetime
from playwright.async_api import async_playwright, expect
import socketio
import requests

class WebSocketTester:
    """WebSocket testing with Playwright integration"""
    
    def __init__(self):
        self.base_url = "http://localhost:8080"
        self.sio = socketio.AsyncClient()
        self.connected = False
        self.received_messages = []
        
    async def setup_playwright(self):
        """Setup Playwright browser"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=False)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        
    async def test_dashboard_accessibility(self):
        """Test if dashboard is accessible"""
        try:
            print("🧪 Testing dashboard accessibility...")
            response = requests.get(self.base_url, timeout=10)
            if response.status_code == 200:
                print("✅ Dashboard is accessible")
                return True
            else:
                print(f"❌ Dashboard returned status code: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Cannot access dashboard: {e}")
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
                print(f"📊 Systems update received: {len(data)} systems")
                self.received_messages.append(('systems_update', data))
                
            @self.sio.event
            async def market_update(data):
                print(f"💹 Market update received: {len(data)} pairs")
                self.received_messages.append(('market_update', data))
                
            @self.sio.event
            async def error(data):
                print(f"❌ WebSocket error: {data}")
                self.received_messages.append(('error', data))
            
            # Connect to WebSocket
            await self.sio.connect(self.base_url)
            
            # Wait for connection
            await asyncio.sleep(2)
            
            if self.connected:
                print("✅ WebSocket connection successful")
                
                # Request update
                await self.sio.emit('request_update')
                await asyncio.sleep(3)
                
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
    
    async def test_dashboard_with_playwright(self):
        """Test dashboard functionality with Playwright"""
        try:
            print("🧪 Testing dashboard with Playwright...")
            
            # Navigate to dashboard
            await self.page.goto(self.base_url)
            await self.page.wait_for_load_state('networkidle')
            
            # Check if page loaded correctly
            title = await self.page.title()
            print(f"📄 Page title: {title}")
            
            # Test API endpoints
            api_endpoints = [
                '/api/systems',
                '/api/market', 
                '/api/news',
                '/api/overview',
                '/api/sidebar/live-prices'
            ]
            
            for endpoint in api_endpoints:
                try:
                    response = await self.page.request.get(f"{self.base_url}{endpoint}")
                    if response.status == 200:
                        print(f"✅ API endpoint {endpoint} working")
                    else:
                        print(f"❌ API endpoint {endpoint} returned {response.status}")
                except Exception as e:
                    print(f"❌ API endpoint {endpoint} error: {e}")
            
            # Test WebSocket connection in browser
            print("🧪 Testing WebSocket in browser...")
            
            # Inject WebSocket test script
            websocket_test_script = """
            const socket = io();
            let connected = false;
            let messagesReceived = 0;
            
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
                window.websocketMessages = messagesReceived;
            });
            
            socket.on('systems_update', (data) => {
                console.log('Systems update:', data);
                messagesReceived++;
                window.websocketMessages = messagesReceived;
            });
            
            socket.on('market_update', (data) => {
                console.log('Market update:', data);
                messagesReceived++;
                window.websocketMessages = messagesReceived;
            });
            
            socket.on('error', (data) => {
                console.log('WebSocket error:', data);
                window.websocketError = data;
            });
            
            // Request update after 2 seconds
            setTimeout(() => {
                socket.emit('request_update');
            }, 2000);
            """
            
            await self.page.evaluate(websocket_test_script)
            
            # Wait for WebSocket connection
            await asyncio.sleep(5)
            
            # Check connection status
            connected = await self.page.evaluate("window.websocketConnected")
            messages = await self.page.evaluate("window.websocketMessages || 0")
            error = await self.page.evaluate("window.websocketError")
            
            if connected:
                print("✅ WebSocket connected in browser")
            else:
                print("❌ WebSocket not connected in browser")
                
            if messages > 0:
                print(f"✅ Received {messages} WebSocket messages in browser")
            else:
                print("❌ No WebSocket messages received in browser")
                
            if error:
                print(f"❌ WebSocket error in browser: {error}")
            
            # Test dashboard elements
            print("🧪 Testing dashboard elements...")
            
            # Check for key dashboard elements
            elements_to_check = [
                'h1',  # Main title
                '.dashboard-container',  # Dashboard container
                '.systems-status',  # Systems status
                '.market-data',  # Market data
                '.news-feed'  # News feed
            ]
            
            for selector in elements_to_check:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        print(f"✅ Found element: {selector}")
                    else:
                        print(f"❌ Missing element: {selector}")
                except Exception as e:
                    print(f"❌ Error checking element {selector}: {e}")
            
            return True
            
        except Exception as e:
            print(f"❌ Playwright test error: {e}")
            return False
    
    async def test_websocket_stress(self):
        """Test WebSocket under stress conditions"""
        try:
            print("🧪 Testing WebSocket stress conditions...")
            
            # Multiple rapid connections
            connections = []
            for i in range(5):
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
                
        except Exception as e:
            print(f"⚠️ Cleanup error: {e}")

async def main():
    """Main test function"""
    print("🧪 WebSocket Testing with Playwright")
    print("=" * 60)
    
    tester = WebSocketTester()
    
    try:
        # Test dashboard accessibility
        if not await tester.test_dashboard_accessibility():
            print("\n❌ Dashboard not accessible. Please start the dashboard first:")
            print("   python dashboard/advanced_dashboard.py")
            return False
        
        # Setup Playwright
        await tester.setup_playwright()
        
        # Test WebSocket connection
        websocket_ok = await tester.test_websocket_connection()
        
        # Test dashboard with Playwright
        playwright_ok = await tester.test_dashboard_with_playwright()
        
        # Test stress conditions
        stress_ok = await tester.test_websocket_stress()
        
        print("\n📊 Test Results:")
        print(f"   WebSocket Connection: {'✅ PASS' if websocket_ok else '❌ FAIL'}")
        print(f"   Playwright Tests: {'✅ PASS' if playwright_ok else '❌ FAIL'}")
        print(f"   Stress Tests: {'✅ PASS' if stress_ok else '❌ FAIL'}")
        
        overall_success = websocket_ok and playwright_ok and stress_ok
        print(f"\n🎯 Overall Result: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
        
        return overall_success
        
    except Exception as e:
        print(f"❌ Test suite error: {e}")
        return False
        
    finally:
        await tester.cleanup()

if __name__ == '__main__':
    asyncio.run(main())
