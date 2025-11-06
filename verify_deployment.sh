#!/bin/bash
# Verify DNS Fix Deployment

echo "================================================================================"
echo "DEPLOYMENT VERIFICATION - DNS FIX"
echo "================================================================================"
echo ""

PROJECT="ai-quant-trading"
SERVICE="default"

echo "1. Checking Oanda client initialization..."
echo "------------------------------------------------------------------------"
gcloud logging read "resource.type=\"gae_app\" AND resource.labels.module_id=\"default\" AND textPayload:\"OANDA client initialized\"" \
  --project=$PROJECT \
  --limit=5 \
  --format="value(timestamp,textPayload)" \
  --freshness=10m | head -5

echo ""
echo "2. Checking for DNS/Connection issues..."
echo "------------------------------------------------------------------------"
gcloud logging read "resource.type=\"gae_app\" AND resource.labels.module_id=\"default\" AND (textPayload:\"194.168\" OR textPayload:\"Connection refused\" OR textPayload:\"Cloud environment\")" \
  --project=$PROJECT \
  --limit=10 \
  --format="value(timestamp,textPayload)" \
  --freshness=10m

echo ""
echo "3. Checking successful API connections..."
echo "------------------------------------------------------------------------"
gcloud logging read "resource.type=\"gae_app\" AND resource.labels.module_id=\"default\" AND (textPayload:\"Account info retrieved\" OR textPayload:\"Retrieved prices\" OR textPayload:\"Connection successful\")" \
  --project=$PROJECT \
  --limit=10 \
  --format="value(timestamp,textPayload)" \
  --freshness=10m

echo ""
echo "4. Checking trading activity..."
echo "------------------------------------------------------------------------"
gcloud logging read "resource.type=\"gae_app\" AND resource.labels.module_id=\"default\" AND (textPayload:\"TRADE EXECUTED\" OR textPayload:\"signal generated\" OR textPayload:\"scan complete\")" \
  --project=$PROJECT \
  --limit=10 \
  --format="value(timestamp,textPayload)" \
  --freshness=10m

echo ""
echo "5. Checking for errors..."
echo "------------------------------------------------------------------------"
gcloud logging read "resource.type=\"gae_app\" AND resource.labels.module_id=\"default\" AND severity>=ERROR" \
  --project=$PROJECT \
  --limit=10 \
  --format="value(timestamp,severity,textPayload)" \
  --freshness=10m

echo ""
echo "================================================================================"
echo "VERIFICATION COMPLETE"
echo "================================================================================"

