# Quick Start Guide - CI/CD Setup

Complete setup guide from zero to automated deployments in ~30 minutes.

## Overview

You'll set up:
1. ✅ GCP Project (new "castal" project)
2. ✅ GitHub Actions CI/CD
3. ✅ Automated testing
4. ✅ Automated deployment to Cloud Run

**After setup, every push to `main` will:**
- Run tests automatically
- Deploy to Cloud Run (if tests pass)
- Verify the deployment
- Takes ~5 minutes per deployment

---

## Prerequisites

- [x] GitHub repo created: https://github.com/moebachar/resume-processor
- [x] Code pushed to GitHub
- [x] Google Cloud SDK installed ([Download](https://cloud.google.com/sdk/docs/install))
- [x] Docker Desktop installed ([Download](https://www.docker.com/products/docker-desktop))
- [x] OpenAI API key ([Get one](https://platform.openai.com/api-keys))

---

## Part 1: Set Up Google Cloud (15 minutes)

Follow `deployment/GCP_SETUP.md` step by step:

### Quick Checklist:
- [ ] Create GCP project named "castal"
- [ ] Note down your Project ID: `________________`
- [ ] Enable APIs (Cloud Run, Container Registry, Cloud Build, IAM)
- [ ] Create service account: `github-actions@castal.iam.gserviceaccount.com`
- [ ] Grant 4 required roles to service account
- [ ] Download service account JSON key
- [ ] Link billing account
- [ ] Test with `gcloud` CLI

**→ When done, continue to Part 2**

---

## Part 2: Configure GitHub Actions (10 minutes)

Follow `deployment/CICD_SETUP.md` step by step:

### Quick Checklist:
- [ ] Add `GCP_SA_KEY` secret (paste entire JSON key)
- [ ] Add `OPENAI_API_KEY` secret
- [ ] Add `API_SECRET_KEY` secret (choose a secure random string)
- [ ] Save your `API_SECRET_KEY` somewhere safe! You'll need it.
- [ ] Verify `.github/workflows/deploy.yml` has correct `PROJECT_ID`
- [ ] Push a change to trigger CI/CD
- [ ] Watch deployment in Actions tab

**→ When done, continue to Part 3**

---

## Part 3: Verify Deployment (5 minutes)

### Get Your Service URL

```bash
gcloud run services describe resume-processor \
  --region europe-west9 \
  --format 'value(status.url)'
```

Save this URL: `___________________________________________`

### Test Health Endpoint

```bash
curl https://your-service-url.run.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "resume-processor",
  "version": "2.0.0",
  "openai_configured": true,
  "modules": {
    "structuring": "ready",
    "enhancing": "ready",
    "cover_letter": "ready"
  }
}
```

### Test Full API

Create `test_prod.json`:
```json
{
  "job_text": "Senior Software Engineer\n\n5+ years experience in Python, FastAPI, Docker, and cloud platforms. Build scalable microservices...",
  "user_json": { /* your user.json data */ },
  "config_json": { /* your config.json data */ }
}
```

Call the API:
```bash
curl -X POST "https://your-service-url.run.app/process" \
  -H "Authorization: Bearer your-api-secret-key" \
  -H "Content-Type: application/json" \
  -d @test_prod.json
```

**✅ If you get a JSON response with resume and cover letter → SUCCESS!**

---

## Your New Workflow

### Daily Development

```bash
# 1. Make changes to code
code api.py

# 2. (Optional) Test locally
python scripts/test_local.py

# 3. Commit and push
git add .
git commit -m "feat: add new feature"
git push origin main

# 4. Watch deployment
# Go to: https://github.com/moebachar/resume-processor/actions
# Watch the workflow run (~5 minutes)

# 5. Done! Changes are live
```

### What Happens Automatically

1. **Tests run** (~30 seconds)
   - Health checks
   - API validation
   - If tests fail → deployment stops

2. **Build & Deploy** (~4 minutes)
   - Docker image built
   - Pushed to Container Registry
   - Deployed to Cloud Run

3. **Verification** (~15 seconds)
   - Smoke tests on deployed service
   - If fails → old version stays running

---

## Helper Scripts

### Test Locally Before Pushing

```bash
cd build
python scripts/test_local.py
```

**When to use:** Before pushing important changes to catch bugs early

### Emergency Manual Deploy

**Windows:**
```powershell
.\scripts\quick_deploy.ps1
```

**Linux/Mac:**
```bash
./scripts/quick_deploy.sh
```

**When to use:** GitHub Actions is down, need to deploy immediately

⚠️ **WARNING**: Skips automated tests!

---

## Monitoring & Logs

### View Real-Time Logs

```bash
gcloud run services logs tail resume-processor --region europe-west9
```

### View Recent Logs

```bash
gcloud run services logs read resume-processor --region europe-west9 --limit 50
```

### View Metrics (Web UI)

1. Go to https://console.cloud.google.com/run
2. Click `resume-processor`
3. Click "Metrics" tab

See:
- Request count
- Latency (P50, P95, P99)
- Instance count
- Error rate

### Set Up Alerts

1. Go to Cloud Monitoring > Alerting
2. Create alert for:
   - Error rate > 5%
   - Latency P95 > 30s
   - Instance count > 3 (budget protection!)

---

## Cost Management

### Current Configuration

- Memory: 8 GB per instance
- CPU: 4 vCPUs per instance
- Min instances: 1 (always running)
- Max instances: 3

**Estimated costs:**
- Baseline: ~$40/month (1 instance)
- Typical: ~$60-80/month (1-2 instances)
- Maximum: ~$120/month (3 instances 24/7)

### Monitor Costs

```bash
gcloud billing accounts list
```

Or in Console:
1. "Billing" > "Reports"
2. Filter by Product: "Cloud Run"

### Reduce Costs (if needed)

**Option 1: Remove always-on instance (slower cold starts)**
```bash
gcloud run services update resume-processor \
  --min-instances 0 \
  --region europe-west9
```
Savings: ~$40/month
Trade-off: First request after idle takes ~10s

**Option 2: Reduce max instances**
```bash
gcloud run services update resume-processor \
  --max-instances 2 \
  --region europe-west9
```
Savings: Caps maximum cost
Trade-off: Lower capacity (200 concurrent users instead of 300)

**Emergency: Pause service**
```bash
gcloud run services update resume-processor \
  --max-instances 0 \
  --region europe-west9
```
Savings: $0/month (service offline)

---

## Troubleshooting

### ❌ Deployment Failed in GitHub Actions

1. Go to Actions tab
2. Click failed workflow
3. Check which step failed:
   - **Tests failed**: Fix the bug, commit, push again
   - **Build failed**: Check Dockerfile syntax
   - **Deploy failed**: Check GCP permissions

### ❌ Tests Pass Locally but Fail in CI

**Possible causes:**
- Environment variable not set in GitHub
- Different Python version
- Missing dependency

**Fix:**
1. Check GitHub secrets are set correctly
2. Verify all dependencies in `requirements.txt`

### ❌ Service Returns 500 Error

**Check logs:**
```bash
gcloud run services logs tail resume-processor --region europe-west9
```

**Common causes:**
- OpenAI API key invalid
- Out of memory (rare with 8GB)
- Code bug (check stack trace in logs)

### ❌ High Latency (>30s)

**Check:**
1. OpenAI API status: https://status.openai.com
2. Instance count (should scale up under load)
3. Application logs for slow operations

---

## Next Steps

### Recommended Improvements

1. **Add More Tests**
   - Add tests in `tests/` folder
   - They'll run automatically on every push

2. **Set Up Staging Environment**
   - Create `staging` branch
   - Deploy to separate service for testing
   - Merge to `main` when ready

3. **Custom Domain** (optional)
   - Map your own domain to Cloud Run
   - Easier to remember than `.run.app` URL

4. **Monitoring Alerts**
   - Set up alerts for errors, latency, cost
   - Get notified before issues affect users

### Learning Resources

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [FastAPI Testing Guide](https://fastapi.tiangolo.com/tutorial/testing/)

---

## Summary

**You now have:**
- ✅ Automated testing on every push
- ✅ Automated deployment to production
- ✅ Zero-downtime rolling updates
- ✅ Automatic rollback on failure
- ✅ Real-time logs and monitoring
- ✅ Budget-controlled auto-scaling

**Your workflow:**
1. Write code
2. Push to GitHub
3. Wait 5 minutes
4. Changes are live!

**Support:**
- Documentation: See `deployment/` folder
- Logs: `gcloud run services logs tail resume-processor`
- Metrics: https://console.cloud.google.com/run

---

## Emergency Contacts

- **GCP Status**: https://status.cloud.google.com
- **GitHub Status**: https://www.githubstatus.com
- **OpenAI Status**: https://status.openai.com

---

**Happy Deploying! 🚀**
