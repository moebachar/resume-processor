# deploy_cloudrun.ps1 - Deploy Resume Processing Microservice to Google Cloud Run
# Windows PowerShell version - Optimized for HIGH CONCURRENCY

# ============================================================================
# CONFIGURATION
# ============================================================================

$PROJECT_ID = "castal-job-tracker"
$SERVICE_NAME = "resume-processor"
$REGION = "europe-west9"

# Concurrency settings
$MEMORY = "8Gi"
$CPU = "4"
$TIMEOUT = "600"
$CONCURRENCY = "100"
$MIN_INSTANCES = "1"
$MAX_INSTANCES = "3"  # Limit to stay under $100/month (3 instances × $40 = ~$120 worst case, avg ~$70)

# ============================================================================
# VALIDATION
# ============================================================================

Write-Host "======================================================================"
Write-Host "  Resume Processing Microservice - Cloud Run Deployment"
Write-Host "  Optimized for Multi-User Concurrency"
Write-Host "======================================================================"
Write-Host ""

if (-not $env:OPENAI_API_KEY) {
    Write-Host "ERROR: OPENAI_API_KEY environment variable not set" -ForegroundColor Red
    Write-Host "Run: `$env:OPENAI_API_KEY = 'your-key-here'"
    exit 1
}

if (-not $env:API_SECRET_KEY) {
    Write-Host "ERROR: API_SECRET_KEY environment variable not set" -ForegroundColor Red
    Write-Host "Run: `$env:API_SECRET_KEY = 'your-secret-key-here'"
    exit 1
}

Write-Host "Environment variables validated" -ForegroundColor Green
Write-Host ""

# ============================================================================
# GCP SETUP
# ============================================================================

Write-Host "Setting GCP project..."
gcloud config set project $PROJECT_ID

Write-Host "Enabling required APIs..."
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com

Write-Host ""
Write-Host "======================================================================"
Write-Host "  Deployment Configuration"
Write-Host "======================================================================"
Write-Host "  Project ID:           $PROJECT_ID"
Write-Host "  Service Name:         $SERVICE_NAME"
Write-Host "  Region:               $REGION"
Write-Host ""
Write-Host "  CONCURRENCY SETTINGS:"
Write-Host "  - Memory:             $MEMORY"
Write-Host "  - CPU:                $CPU vCPUs"
Write-Host "  - Timeout:            ${TIMEOUT}s"
Write-Host "  - Concurrency/inst:   $CONCURRENCY requests"
Write-Host "  - Min Instances:      $MIN_INSTANCES (always warm)"
Write-Host "  - Max Instances:      $MAX_INSTANCES"
Write-Host "======================================================================"
Write-Host ""

$confirmation = Read-Host "Proceed with deployment? (y/n)"
if ($confirmation -ne 'y' -and $confirmation -ne 'Y') {
    Write-Host "Deployment cancelled"
    exit 1
}

# ============================================================================
# DEPLOYMENT
# ============================================================================

Write-Host ""
Write-Host "Deploying to Cloud Run..."
Write-Host ""

gcloud run deploy $SERVICE_NAME `
  --source . `
  --region $REGION `
  --allow-unauthenticated `
  --memory $MEMORY `
  --cpu $CPU `
  --timeout $TIMEOUT `
  --concurrency $CONCURRENCY `
  --min-instances $MIN_INSTANCES `
  --max-instances $MAX_INSTANCES `
  --set-env-vars "OPENAI_API_KEY=$env:OPENAI_API_KEY,API_SECRET_KEY=$env:API_SECRET_KEY,WORKERS=4" `
  --platform managed `
  --port 8080

# ============================================================================
# POST-DEPLOYMENT
# ============================================================================

Write-Host ""
Write-Host "======================================================================"
Write-Host "  Deployment Successful!" -ForegroundColor Green
Write-Host "======================================================================"
Write-Host ""

# Get service URL
$SERVICE_URL = gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)'

Write-Host "  Service URL: $SERVICE_URL"
Write-Host ""
Write-Host "  Test the service:"
Write-Host "    Health: $SERVICE_URL/health"
Write-Host ""
Write-Host "======================================================================"
Write-Host "  Concurrency Metrics"
Write-Host "======================================================================"
Write-Host ""
Write-Host "  Expected Capacity:"
Write-Host "    - Per Instance:  $CONCURRENCY concurrent requests"
$capacityMax = [int]$CONCURRENCY * [int]$MAX_INSTANCES
Write-Host "    - With $MAX_INSTANCES instances (max): $capacityMax concurrent requests"
Write-Host ""
Write-Host "  Estimated Cost:"
Write-Host "    - Minimum (1 instance): ~`$40/month"
Write-Host "    - Average (1-2 instances): ~`$50-70/month"
Write-Host "    - Maximum (3 instances full-time): ~`$120/month"
Write-Host "    - Typical for light-moderate usage: ~`$60-80/month"
Write-Host ""
Write-Host "======================================================================"
Write-Host ""
Write-Host "Deployment complete!"
Write-Host ""
