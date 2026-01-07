#!/bin/bash
#
# Quick Deploy Script - Emergency Manual Deployment
#
# Use this for emergency deployments when GitHub Actions is down
# or you need to deploy immediately without running tests.
#
# WARNING: This skips tests! Use only in emergencies.
#

set -e  # Exit on error

# Configuration
PROJECT_ID="castal"
SERVICE_NAME="resume-processor"
REGION="europe-west9"
IMAGE_TAG=$(date +%Y%m%d-%H%M%S)

echo "========================================================================"
echo "  Emergency Quick Deploy - Resume Processor"
echo "  ⚠️  WARNING: This skips automated tests!"
echo "========================================================================"
echo ""

# Check if environment variables are set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ ERROR: OPENAI_API_KEY not set"
    echo "   Run: export OPENAI_API_KEY='your-key'"
    exit 1
fi

if [ -z "$API_SECRET_KEY" ]; then
    echo "❌ ERROR: API_SECRET_KEY not set"
    echo "   Run: export API_SECRET_KEY='your-key'"
    exit 1
fi

echo "✓ Environment variables set"
echo ""

# Confirm deployment
echo "This will deploy to:"
echo "  Project: $PROJECT_ID"
echo "  Service: $SERVICE_NAME"
echo "  Region: $REGION"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled"
    exit 1
fi

echo ""
echo "========================================================================"
echo "  Step 1: Building Docker Image"
echo "========================================================================"

docker build -f deployment/Dockerfile -t gcr.io/$PROJECT_ID/$SERVICE_NAME:$IMAGE_TAG .
docker tag gcr.io/$PROJECT_ID/$SERVICE_NAME:$IMAGE_TAG gcr.io/$PROJECT_ID/$SERVICE_NAME:latest

echo ""
echo "========================================================================"
echo "  Step 2: Pushing to Container Registry"
echo "========================================================================"

gcloud auth configure-docker gcr.io --quiet
docker push gcr.io/$PROJECT_ID/$SERVICE_NAME:$IMAGE_TAG
docker push gcr.io/$PROJECT_ID/$SERVICE_NAME:latest

echo ""
echo "========================================================================"
echo "  Step 3: Deploying to Cloud Run"
echo "========================================================================"

gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME:$IMAGE_TAG \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --memory 8Gi \
  --cpu 4 \
  --timeout 600 \
  --concurrency 100 \
  --min-instances 1 \
  --max-instances 3 \
  --set-env-vars "OPENAI_API_KEY=${OPENAI_API_KEY},API_SECRET_KEY=${API_SECRET_KEY},WORKERS=4"

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
  --region $REGION \
  --format 'value(status.url)')

echo ""
echo "========================================================================"
echo "  Deployment Complete! ✅"
echo "========================================================================"
echo ""
echo "  Service URL: $SERVICE_URL"
echo "  Image: gcr.io/$PROJECT_ID/$SERVICE_NAME:$IMAGE_TAG"
echo ""
echo "  Quick Health Check:"
echo "    curl $SERVICE_URL/health"
echo ""
echo "========================================================================"
