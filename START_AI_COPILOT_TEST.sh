#!/bin/bash
# Quick Start Script for AI Trading Copilot Testing
# Safe, read-only testing - NO LIVE TRADING

echo "=================================================="
echo "🤖 AI TRADING COPILOT - SAFE TEST MODE"
echo "=================================================="
echo ""
echo "This will start the AI copilot in DEMO mode"
echo "Features to test:"
echo "  ✓ Strategy optimization"
echo "  ✓ Pre-trade risk validation"
echo "  ✓ Backtest metrics"
echo "  ✓ Risk console"
echo ""
echo "⚠️  COMPLETELY SAFE - No live trading access"
echo "=================================================="
echo ""

# Navigate to copilot directory
cd /Users/mac/quant_system_clean/ai-trading-copilot-starter

# Start backend in background
echo "🔧 Starting backend API on port 8000..."
cd backend

# Create venv if doesn't exist
if [ ! -d ".venv" ]; then
    echo "   Creating Python virtual environment..."
    python3 -m venv .venv
fi

# Activate and install
source .venv/bin/activate
echo "   Installing dependencies..."
pip install -q -r requirements.txt

# Set environment
export PORT=8000
export SHARED_DIR=../shared
export PYTHONPATH=/Users/mac/quant_system_clean/ai-trading-copilot-starter/backend:$PYTHONPATH

# Start backend
echo "   Starting FastAPI backend..."
nohup python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > ../backend.log 2>&1 &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"

# Wait for backend to start
echo "   Waiting for backend to initialize..."
sleep 5

# Check backend health
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "   ✅ Backend is healthy!"
else
    echo "   ⚠️  Backend not responding yet (may need more time)"
fi

# Start frontend
cd ../frontend
echo ""
echo "🎨 Starting frontend on port 3000..."

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "   Installing Node.js dependencies..."
    npm install
fi

# Set environment
export NEXT_PUBLIC_API_BASE=http://localhost:8000/api

# Start frontend
echo "   Starting Next.js frontend..."
nohup npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
echo "   Frontend PID: $FRONTEND_PID"

echo ""
echo "=================================================="
echo "✅ AI COPILOT IS STARTING UP!"
echo "=================================================="
echo ""
echo "📊 Access Points:"
echo "   • Copilot UI:  http://localhost:3000"
echo "   • Backend API: http://localhost:8000/docs"
echo "   • Health Check: http://localhost:8000/health"
echo ""
echo "📝 Logs:"
echo "   • Backend:  tail -f backend.log"
echo "   • Frontend: tail -f frontend.log"
echo ""
echo "🛑 To stop:"
echo "   kill $BACKEND_PID $FRONTEND_PID"
echo "   (or run: pkill -f 'uvicorn app.main' && pkill -f 'next-server')"
echo ""
echo "⏰ Waiting 10 seconds for services to fully start..."
sleep 10

# Check if services are running
echo ""
echo "🔍 Service Status Check:"
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "   ✅ Backend API: RUNNING"
else
    echo "   ⚠️  Backend API: NOT READY (check backend.log)"
fi

if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "   ✅ Frontend UI: RUNNING"
else
    echo "   ⏳ Frontend UI: STILL STARTING (Next.js takes 30-60 seconds)"
fi

echo ""
echo "=================================================="
echo "🚀 READY TO TEST!"
echo "=================================================="
echo ""
echo "Open your browser to: http://localhost:3000"
echo ""
echo "Try these tests:"
echo "  1. Click 'Optimize' - See strategy optimization in action"
echo "  2. Click 'Backtest' - Run a mock backtest"
echo "  3. Click 'Pre-Trade Check' - Test risk validation"
echo ""
echo "💡 TIP: This is using MOCK data only"
echo "    To wire to your real system, edit:"
echo "    backend/app/routers/tools.py"
echo ""
echo "=================================================="
echo "📖 Full guide: AI_COPILOT_INTEGRATION_ANALYSIS.md"
echo "=================================================="


