#!/bin/bash
# Deploy Analytics System to Google Cloud
# This script deploys the complete trading system with analytics to Google Cloud

set -e

echo "=========================================="
echo "DEPLOYING TRADING ANALYTICS TO GOOGLE CLOUD"
echo "=========================================="

# Configuration
PROJECT_ID="your-project-id"  # Replace with your actual project ID
REGION="us-central1"
SERVICE_NAME="trading-analytics-system"
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"

# Check if we're logged into gcloud
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "@"; then
    echo "❌ Not logged into gcloud. Please run: gcloud auth login"
    exit 1
fi

# Set project
echo "📋 Setting project to: $PROJECT_ID"
gcloud config set project $PROJECT_ID

# Build and push Docker image
echo "🐳 Building Docker image..."
docker build -t $IMAGE_NAME .

echo "📤 Pushing image to Google Container Registry..."
docker push $IMAGE_NAME

# Create Cloud Run service configuration
echo "⚙️ Creating Cloud Run service configuration..."
cat > cloud_run_config.yaml << EOF
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: $SERVICE_NAME
  annotations:
    run.googleapis.com/ingress: all
    run.googleapis.com/execution-environment: gen2
spec:
  template:
    metadata:
      annotations:
        run.googleapis.com/execution-environment: gen2
        run.googleapis.com/cpu-throttling: "false"
        run.googleapis.com/memory: "2Gi"
        run.googleapis.com/cpu: "2"
        run.googleapis.com/timeout: "3600s"
    spec:
      containerConcurrency: 100
      timeoutSeconds: 3600
      containers:
      - image: $IMAGE_NAME
        ports:
        - containerPort: 8080
        env:
        - name: PORT
          value: "8080"
        - name: OANDA_API_KEY
          valueFrom:
            secretKeyRef:
              name: oanda-credentials
              key: api-key
        - name: OANDA_ENVIRONMENT
          value: "practice"
        - name: PRIMARY_ACCOUNT
          valueFrom:
            secretKeyRef:
              name: oanda-credentials
              key: primary-account
        - name: GOLD_SCALP_ACCOUNT
          valueFrom:
            secretKeyRef:
              name: oanda-credentials
              key: gold-account
        - name: STRATEGY_ALPHA_ACCOUNT
          valueFrom:
            secretKeyRef:
              name: oanda-credentials
              key: alpha-account
        - name: FLASK_SECRET_KEY
          value: "your-flask-secret-key-here"
        resources:
          limits:
            cpu: "2"
            memory: "2Gi"
          requests:
            cpu: "1"
            memory: "1Gi"
        startupProbe:
          httpGet:
            path: /api/analytics/health
            port: 8080
          initialDelaySeconds: 30
          timeoutSeconds: 10
          failureThreshold: 3
        livenessProbe:
          httpGet:
            path: /api/analytics/health
            port: 8080
          initialDelaySeconds: 60
          timeoutSeconds: 10
          periodSeconds: 30
EOF

# Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
gcloud run services replace cloud_run_config.yaml --region=$REGION

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)")

echo "=========================================="
echo "✅ DEPLOYMENT COMPLETE!"
echo "=========================================="
echo ""
echo "🌐 Service URL: $SERVICE_URL"
echo "📊 Main Dashboard: $SERVICE_URL"
echo "📈 Analytics Dashboard: $SERVICE_URL:8081"
echo ""
echo "🔐 Make sure your OANDA credentials are set in Google Secret Manager:"
echo "   - oanda-credentials/api-key"
echo "   - oanda-credentials/primary-account"
echo "   - oanda-credentials/gold-account"
echo "   - oanda-credentials/alpha-account"
echo ""
echo "📋 To view logs:"
echo "   gcloud run services logs tail $SERVICE_NAME --region=$REGION"
echo ""
echo "🔄 To update deployment:"
echo "   ./deploy_analytics_to_cloud.sh"
echo ""


