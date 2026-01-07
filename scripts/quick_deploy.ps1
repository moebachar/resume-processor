# Quick Deploy Script - Emergency Manual Deployment (Windows PowerShell)
#
# Use this for emergency deployments when GitHub Actions is down
# or you need to deploy immediately without running tests.
#
# WARNING: This skips tests! Use only in emergencies.

$ErrorActionPreference = "Stop"

# Configuration
$PROJECT_ID = "castal"
$SERVICE_NAME = "resume-processor"
$REGION = "europe-west9"
$IMAGE_TAG = Get-Date -Format "yyyyMMdd-HHmmss"

Write-Host "========================================================================"
Write-Host "  Emergency Quick Deploy - Resume Processor"
Write-Host "  ⚠️  WARNING: This skips automated tests!"
Write-Host "========================================================================"
Write-Host ""

# Check environment variables
if (-not $env:OPENAI_API_KEY) {
    Write-Host "❌ ERROR: OPENAI_API_KEY not set" -ForegroundColor Red
    Write-Host "   Run: `$env:OPENAI_API_KEY = 'your-key'"
    exit 1
}

if (-not $env:API_SECRET_KEY) {
    Write-Host "❌ ERROR: API_SECRET_KEY not set" -ForegroundColor Red
    Write-Host "   Run: `$env:API_SECRET_KEY = 'your-key'"
    exit 1
}

Write-Host "✓ Environment variables set" -ForegroundColor Green
Write-Host ""

# Confirm deployment
Write-Host "This will deploy to:"
Write-Host "  Project: $PROJECT_ID"
Write-Host "  Service: $SERVICE_NAME"
Write-Host "  Region: $REGION"
Write-Host ""
$confirmation = Read-Host "Continue? (y/n)"
if ($confirmation -ne 'y' -and $confirmation -ne 'Y') {
    Write-Host "Deployment cancelled"
    exit 1
}

Write-Host ""
Write-Host "========================================================================"
Write-Host "  Step 1: Building Docker Image"
Write-Host "========================================================================"

docker build -f deployment/Dockerfile -t gcr.io/$PROJECT_ID/$SERVICE_NAME:$IMAGE_TAG .
docker tag gcr.io/$PROJECT_ID/$SERVICE_NAME:$IMAGE_TAG gcr.io/$PROJECT_ID/$SERVICE_NAME:latest

Write-Host ""
Write-Host "========================================================================"
Write-Host "  Step 2: Pushing to Container Registry"
Write-Host "========================================================================"

gcloud auth configure-docker gcr.io --quiet
docker push gcr.io/$PROJECT_ID/$SERVICE_NAME:$IMAGE_TAG
docker push gcr.io/$PROJECT_ID/$SERVICE_NAME:latest

Write-Host ""
Write-Host "========================================================================"
Write-Host "  Step 3: Deploying to Cloud Run"
Write-Host "========================================================================"

gcloud run deploy $SERVICE_NAME `
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME:$IMAGE_TAG `
  --region $REGION `
  --platform managed `
  --allow-unauthenticated `
  --memory 8Gi `
  --cpu 4 `
  --timeout 600 `
  --concurrency 100 `
  --min-instances 1 `
  --max-instances 3 `
  --set-env-vars "OPENAI_API_KEY=$env:OPENAI_API_KEY,API_SECRET_KEY=$env:API_SECRET_KEY,WORKERS=4"

# Get service URL
$SERVICE_URL = gcloud run services describe $SERVICE_NAME `
  --region $REGION `
  --format 'value(status.url)'

Write-Host ""
Write-Host "========================================================================"
Write-Host "  Deployment Complete! ✅" -ForegroundColor Green
Write-Host "========================================================================"
Write-Host ""
Write-Host "  Service URL: $SERVICE_URL"
Write-Host "  Image: gcr.io/$PROJECT_ID/${SERVICE_NAME}:$IMAGE_TAG"
Write-Host ""
Write-Host "  Quick Health Check:"
Write-Host "    curl $SERVICE_URL/health"
Write-Host ""
Write-Host "========================================================================"
