# Resume Processing Microservice - Production Build

AI-powered resume and cover letter generation API optimized for high-concurrency deployment.

## Overview

This microservice provides a JSON-only API that takes job descriptions and user data as input, and returns:
- Structured job analysis
- Tailored resume (JSON format)
- Customized cover letter text

**No PDF generation. No Google Drive integration. Pure JSON I/O.**

## Architecture

```
build/
├── api.py                    # FastAPI application entry point
├── orchestrator.py           # Async pipeline orchestration
├── modules/                  # Core processing modules
│   ├── structuring/          # Job description analysis
│   ├── enhancing/            # Resume enhancement (coordinator, bullets, profile, skills)
│   └── cover_letter/         # Cover letter generation
├── deployment/               # Deployment files
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── deploy_cloudrun.sh
│   └── deploy_cloudrun.ps1
└── requirements.txt          # Python dependencies
```

## Features

- **High Concurrency**: 4 Uvicorn workers, 100 concurrent requests per instance
- **Async Pipeline**: Maximized parallelization (3 parallel bullet generations)
- **Auto-scaling**: 1-3 instances on Cloud Run (300 max concurrent users)
- **JSON Output**: Resume and cover letter returned as structured JSON
- **Multi-language**: Supports English and French job descriptions
- **ATS Optimized**: Keyword matching and scoring for applicant tracking systems

## API Endpoints

### `POST /process`
**Main endpoint** - Full pipeline processing

**Request:**
```json
{
  "job_text": "Job description text here...",
  "user_json": { /* user data */ },
  "config_json": { /* configuration */ }
}
```

**Response:**
```json
{
  "success": true,
  "structured_job": { /* analyzed job data */ },
  "resume": {
    "personal": { "name": "...", "title": "..." },
    "contact": { "email": "...", "phone": "..." },
    "profile": "Professional summary text...",
    "experience": [
      {
        "role": "Software Engineer",
        "company": "Company Name",
        "location": "Paris, France",
        "start_date": "2023-01",
        "end_date": "2024-12",
        "bullets": ["Bullet 1", "Bullet 2", "..."]
      }
    ],
    "skills": {
      "technical": ["Python", "FastAPI", "..."],
      "soft": ["Leadership", "Communication", "..."]
    },
    "education": [...],
    "certifications": [...],
    "languages": [...]
  },
  "cover_letter": "Cover letter text...",
  "metadata": {
    "processing_time_seconds": 12.5,
    "language": "en",
    "projects_selected": ["Project A", "Project B"],
    "average_ats_score": 85.3
  }
}
```

### `POST /structure`
Job description structuring only

### `GET /health`
Health check endpoint

### `GET /`
Service information

## Local Development

### Prerequisites
- Python 3.13+
- OpenAI API key

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export OPENAI_API_KEY="your-openai-key"
export API_SECRET_KEY="your-secret-key"

# Run locally
python api.py
```

API will be available at:
- API: http://localhost:8080
- Docs: http://localhost:8080/docs

## Deployment to Google Cloud Run

### Prerequisites
- Google Cloud SDK installed and configured
- Docker Desktop installed
- Environment variables set:
  - `OPENAI_API_KEY`
  - `API_SECRET_KEY`

### Deploy (Windows)
```powershell
cd deployment
.\deploy_cloudrun.ps1
```

### Deploy (Linux/Mac)
```bash
cd deployment
./deploy_cloudrun.sh
```

### Manual Deployment
```bash
# Build Docker image locally
docker build -f deployment/Dockerfile -t gcr.io/castal-job-tracker/resume-processor .

# Configure Docker auth
gcloud auth configure-docker gcr.io

# Push image
docker push gcr.io/castal-job-tracker/resume-processor

# Deploy to Cloud Run
gcloud run deploy resume-processor \
  --image gcr.io/castal-job-tracker/resume-processor \
  --region europe-west9 \
  --memory 8Gi \
  --cpu 4 \
  --timeout 600 \
  --concurrency 100 \
  --min-instances 1 \
  --max-instances 3 \
  --set-env-vars "OPENAI_API_KEY=${OPENAI_API_KEY},API_SECRET_KEY=${API_SECRET_KEY},WORKERS=4" \
  --allow-unauthenticated
```

## Configuration

### Concurrency Settings
- **Workers per instance**: 4
- **Requests per instance**: 100
- **Min instances**: 1 (always warm, no cold starts)
- **Max instances**: 3 (budget constraint: <$100/month)
- **Total capacity**: 300 concurrent users

### Cost Estimation
- **Baseline**: ~$40/month (1 instance always running)
- **Typical**: ~$60-80/month (1-2 instances average)
- **Maximum**: ~$120/month (3 instances 24/7)

## Testing

```bash
# Health check
curl https://your-service-url.run.app/health

# Full pipeline test
curl -X POST "https://your-service-url.run.app/process" \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d @test_request.json
```

## Performance

**Expected metrics:**
- Processing time: 10-20s per request
- Success rate: >95%
- Median latency: <30s
- Throughput: ~5-10 req/s (with auto-scaling)

## Security

- API key authentication required (Bearer token)
- Secrets passed via environment variables (never in code)
- No file storage (stateless service)
- HTTPS only (enforced by Cloud Run)

## Monitoring

View logs and metrics:
```bash
# Logs
gcloud run services logs tail resume-processor --region europe-west9

# Metrics dashboard
https://console.cloud.google.com/run/detail/europe-west9/resume-processor/metrics
```

## Troubleshooting

### High latency
- Check OpenAI API response times
- Verify worker count is appropriate
- Check instance memory usage

### Rate limiting
- Increase `max-instances` if needed
- Check OpenAI API quotas

### Out of memory
- Reduce concurrency per instance
- Increase memory allocation

## Support

For issues or questions, refer to the main project documentation.

## Version

**v2.0.0** - Production JSON-only API (December 2024)
"Deploying via CI/CD" 
