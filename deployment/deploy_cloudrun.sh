#!/bin/bash
# deploy_cloudrun.sh - Deploy Resume Processing Microservice to Google Cloud Run
# Optimized for HIGH CONCURRENCY and MULTIPLE SIMULTANEOUS USERS

set -e  # Exit on error

# ============================================================================
# CONFIGURATION - UPDATE THESE VALUES
# ============================================================================

PROJECT_ID="your-gcp-project-id"  # CHANGE THIS
SERVICE_NAME="resume-processor"
REGION="us-central1"  # Or your preferred region

# IMPORTANT: Set these environment variables before running:
# export OPENAI_API_KEY="your-openai-key-here"
# export API_SECRET_KEY="your-api-secret-key-here"

# ============================================================================
# CONCURRENCY SETTINGS - OPTIMIZED FOR MULTI-USER TRAFFIC
# ============================================================================

MEMORY="8Gi"              # 8GB RAM (handles multiple concurrent OpenAI calls)
CPU="4"                   # 4 vCPUs (parallel processing)
TIMEOUT="600"             # 10 minutes (max for complex jobs)
CONCURRENCY="100"         # 100 requests per instance (I/O-bound workload)
MIN_INSTANCES="1"         # Always keep 1 instance warm (no cold starts)
MAX_INSTANCES="100"       # Auto-scale up to 100 instances
MAX_CONCURRENT_REQUESTS="10000"  # Total concurrent requests across all instances

# ============================================================================
# VALIDATION
# ============================================================================

echo "======================================================================"
echo "  Resume Processing Microservice - Cloud Run Deployment"
echo "  Optimized for Multi-User Concurrency"
echo "======================================================================"
echo ""

if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ ERROR: OPENAI_API_KEY environment variable not set"
    echo "   Run: export OPENAI_API_KEY='your-key-here'"
    exit 1
fi

if [ -z "$API_SECRET_KEY" ]; then
    echo "❌ ERROR: API_SECRET_KEY environment variable not set"
    echo "   Run: export API_SECRET_KEY='your-secret-key-here'"
    exit 1
fi

echo "✓ Environment variables validated"
echo ""

# ============================================================================
# GCP SETUP
# ============================================================================

echo "Setting GCP project..."
gcloud config set project $PROJECT_ID

echo "Enabling required APIs..."
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com

echo ""
echo "======================================================================"
echo "  Deployment Configuration"
echo "======================================================================"
echo "  Project ID:           $PROJECT_ID"
echo "  Service Name:         $SERVICE_NAME"
echo "  Region:               $REGION"
echo ""
echo "  CONCURRENCY SETTINGS:"
echo "  - Memory:             $MEMORY"
echo "  - CPU:                $CPU vCPUs"
echo "  - Timeout:            ${TIMEOUT}s"
echo "  - Concurrency/inst:   $CONCURRENCY requests"
echo "  - Min Instances:      $MIN_INSTANCES (always warm)"
echo "  - Max Instances:      $MAX_INSTANCES"
echo "  - Max Total Requests: $MAX_CONCURRENT_REQUESTS"
echo "======================================================================"
echo ""

read -p "Proceed with deployment? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled"
    exit 1
fi

# ============================================================================
# DEPLOYMENT
# ============================================================================

echo ""
echo "Deploying to Cloud Run..."
echo ""

gcloud run deploy $SERVICE_NAME \
  --source . \
  --region $REGION \
  --allow-unauthenticated \
  --memory $MEMORY \
  --cpu $CPU \
  --timeout $TIMEOUT \
  --concurrency $CONCURRENCY \
  --min-instances $MIN_INSTANCES \
  --max-instances $MAX_INSTANCES \
  --set-env-vars "OPENAI_API_KEY=${OPENAI_API_KEY},API_SECRET_KEY=${API_SECRET_KEY},WORKERS=4" \
  --platform managed \
  --port 8080

# ============================================================================
# POST-DEPLOYMENT
# ============================================================================

echo ""
echo "======================================================================"
echo "  Deployment Successful!"
echo "======================================================================"
echo ""

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')

echo "  Service URL: $SERVICE_URL"
echo ""
echo "  Health Check:"
echo "    curl $SERVICE_URL/health"
echo ""
echo "  Test Request:"
echo "    curl -X POST \"$SERVICE_URL/process\" \\"
echo "      -H \"Authorization: Bearer \$API_SECRET_KEY\" \\"
echo "      -H \"Content-Type: application/json\" \\"
echo "      -d @test_request.json"
echo ""
echo "======================================================================"
echo "  Concurrency Metrics"
echo "======================================================================"
echo ""
echo "  Expected Capacity:"
echo "    - Per Instance:  $CONCURRENCY concurrent requests"
echo "    - With 10 instances: $((CONCURRENCY * 10)) concurrent requests"
echo "    - With 100 instances: $((CONCURRENCY * 100)) concurrent requests"
echo ""
echo "  Cost Estimate (rough):"
echo "    - 1 instance always warm: ~\$30-40/month baseline"
echo "    - Per 10k requests: ~\$15-20"
echo "    - Auto-scales based on demand"
echo ""
echo "======================================================================"
echo ""
echo "  View Logs:    gcloud run services logs tail $SERVICE_NAME --region $REGION"
echo "  View Metrics: https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME/metrics"
echo ""
echo "======================================================================"
