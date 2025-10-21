#!/bin/bash

# Deploy Memory-Optimized Trading System
# Optimized for F1 FREE TIER with additional strategy capacity

echo "🚀 Deploying Memory-Optimized Trading System..."

# Set project
gcloud config set project ai-quant-trading

# Create optimized deployment directory
mkdir -p /tmp/memory_optimized_deploy
cd /tmp/memory_optimized_deploy

# Copy optimized files
echo "📋 Copying optimized system files..."
cp /Users/mac/quant_system_clean/google-cloud-trading-system/main_optimized.py ./main.py
cp /Users/mac/quant_system_clean/google-cloud-trading-system/app_memory_optimized.yaml ./app.yaml
cp /Users/mac/quant_system_clean/google-cloud-trading-system/requirements.txt ./

# Copy essential directories with memory optimization
echo "📁 Copying optimized directories..."
cp -r /Users/mac/quant_system_clean/google-cloud-trading-system/src ./src
cp -r /Users/mac/quant_system_clean/google-cloud-trading-system/static ./static
cp -r /Users/mac/quant_system_clean/google-cloud-trading-system/templates ./templates

# Create optimized requirements.txt (minimal dependencies)
cat > requirements.txt << EOF
Flask==2.3.3
Flask-SocketIO==5.3.6
Werkzeug==2.3.7
requests==2.31.0
websocket-client==1.6.4
python-socketio==5.9.0
psutil==5.9.6
pandas==2.1.4
numpy==1.24.4
python-dateutil==2.8.2
EOF

# Create .gcloudignore for memory optimization
cat > .gcloudignore << EOF
# Memory optimization - exclude unnecessary files
*.log
*.pyc
__pycache__/
*.db
*.sqlite
*.sqlite3
test_*
*_test.py
examples/
docs/
.git/
.gitignore
README.md
*.md
*.txt
!requirements.txt
*.zip
*.tar.gz
node_modules/
.env
.env.local
.env.production
*.key
*.pem
*.p12
*.pfx
EOF

echo "✅ Memory-optimized deployment package created"

# Deploy to Google Cloud
echo "🚀 Deploying to Google Cloud App Engine..."
VERSION_NAME="memory-optimized-$(date +%Y%m%d-%H%M%S)"

gcloud app deploy --version=$VERSION_NAME --promote --quiet

if [ $? -eq 0 ]; then
    echo "✅ Memory-optimized system deployed successfully!"
    echo "📊 Version: $VERSION_NAME"
    echo "🌐 URL: https://ai-quant-trading.uc.r.appspot.com"
    echo ""
    echo "🔍 Verification commands:"
    echo "curl https://ai-quant-trading.uc.r.appspot.com/api/health"
    echo "curl https://ai-quant-trading.uc.r.appspot.com/api/memory/status"
    echo ""
    echo "📈 System now supports up to 10 strategies with optimized memory usage!"
else
    echo "❌ Deployment failed!"
    exit 1
fi

# Cleanup
cd /Users/mac/quant_system_clean
rm -rf /tmp/memory_optimized_deploy

echo "🎉 Memory optimization deployment complete!"




