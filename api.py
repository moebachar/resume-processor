"""
Resume Processing Microservice - FastAPI Server

Pure JSON API for resume and cover letter generation.
Optimized for high-concurrency deployment on Cloud Run.
"""

from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import os
import time
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import async modules with updated paths
from modules.structuring.main import structure_job_description
from orchestrator import process_resume_pipeline

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Resume Processing Microservice",
    version="2.0.0 - JSON Only",
    description="AI-powered resume and cover letter generation service (JSON output only)"
)

# API Key authentication
API_KEYS = {os.getenv("API_SECRET_KEY", "dev-secret-key-12345")}


def verify_api_key(authorization: Optional[str] = Header(None)):
    """Verify API key from Authorization header"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    token = authorization.replace("Bearer ", "")
    if token not in API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return True


# Request/Response Models
class StructuringRequest(BaseModel):
    """Request model for structuring endpoint"""
    job_text: str
    source_url: Optional[str] = ""
    model: Optional[str] = None


class StructuringResponse(BaseModel):
    """Response model for structuring endpoint"""
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None
    usage: Optional[dict] = None
    processing_time_seconds: float


class ProcessRequest(BaseModel):
    """Request model for full pipeline processing"""
    job_text: str
    user_json: Dict[str, Any]
    config_json: Dict[str, Any]


class ExperienceItem(BaseModel):
    """Single experience/project in resume"""
    role: str
    company: str
    location: str
    start_date: str
    end_date: str
    bullets: List[str]
    context: str


class ResumeData(BaseModel):
    """Complete resume data structure"""
    personal: Dict[str, str]
    contact: Dict[str, str]
    profile: str
    experience: List[ExperienceItem]
    skills: Dict[str, List[str]]
    education: List[Dict[str, str]]
    certifications: List[Dict[str, str]]
    languages: List[Dict[str, str]]


class ProcessResponse(BaseModel):
    """Response model for full pipeline processing"""
    success: bool
    structured_job: Optional[dict] = None
    resume: Optional[ResumeData] = None
    cover_letter: Optional[str] = None
    metadata: Optional[dict] = None
    error: Optional[str] = None


@app.get("/")
async def root():
    """Root endpoint with service info"""
    return {
        "service": "Resume Processing Microservice",
        "version": "2.0.0",
        "status": "operational",
        "output_format": "JSON only (no PDF generation)",
        "modules_implemented": ["structuring", "enhancing", "mapping", "cover_letter"],
        "endpoints": {
            "process": "/process (Full pipeline - POST)",
            "structure": "/structure (Job structuring only - POST)",
            "health": "/health (Health check - GET)"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "service": "resume-processor",
        "version": "2.0.0",
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "modules": {
            "structuring": "ready",
            "enhancing": "ready",
            "cover_letter": "ready"
        }
    }


@app.post("/structure")
async def structure_job(
    request: StructuringRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Structure a job description using AI.

    This endpoint extracts structured information from raw job text.

    Args:
        request: Job text and configuration
        authorization: Authorization header (Bearer token)

    Returns:
        Structured job data with metadata
    """
    # Verify API key
    verify_api_key(authorization)

    start_time = time.time()

    logger.info(f"Processing structuring request (model: {request.model or 'default'})")

    try:
        # Validate input
        if not request.job_text or len(request.job_text.strip()) < 50:
            raise HTTPException(
                status_code=400,
                detail="job_text must be at least 50 characters"
            )

        # Get OpenAI API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="OPENAI_API_KEY not configured on server"
            )

        # Call async structuring function
        result = await structure_job_description(
            job_text=request.job_text,
            source_url=request.source_url,
            api_key=api_key,
            model=request.model
        )

        processing_time = time.time() - start_time
        logger.info(f"Structuring completed in {processing_time:.2f}s")

        return StructuringResponse(
            success=result["success"],
            data=result.get("data"),
            error=result.get("error"),
            usage=result.get("usage"),
            processing_time_seconds=round(processing_time, 2)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Structuring failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Processing failed: {str(e)}"
        )


@app.post("/process")
async def process_resume(
    request: ProcessRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Process full resume pipeline: structuring, enhancing, and cover letter generation.

    This is the main endpoint that orchestrates the entire workflow.
    Returns JSON data for resume and cover letter (no PDF generation).

    Args:
        request: Job text, user data, and configuration
        authorization: Authorization header (Bearer token)

    Returns:
        Complete pipeline results including structured job, resume JSON, and cover letter text
    """
    # Verify API key
    verify_api_key(authorization)

    start_time = time.time()

    logger.info(f"Processing full pipeline request")

    try:
        # Validate input
        if not request.job_text or len(request.job_text.strip()) < 50:
            raise HTTPException(
                status_code=400,
                detail="job_text must be at least 50 characters"
            )

        if not request.user_json:
            raise HTTPException(
                status_code=400,
                detail="user_json is required"
            )

        if not request.config_json:
            raise HTTPException(
                status_code=400,
                detail="config_json is required"
            )

        # Get OpenAI API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="OPENAI_API_KEY not configured on server"
            )

        # Call async orchestrator
        result = await process_resume_pipeline(
            user_json=request.user_json,
            config_json=request.config_json,
            job_text=request.job_text,
            api_key=api_key
        )

        processing_time = time.time() - start_time
        logger.info(f"Full pipeline completed in {processing_time:.2f}s")

        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Pipeline processing failed")
            )

        return ProcessResponse(
            success=result["success"],
            structured_job=result.get("structured_job"),
            resume=result.get("resume"),
            cover_letter=result.get("cover_letter"),
            metadata=result.get("metadata"),
            error=None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Pipeline processing failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Processing failed: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    # Check for required environment variables
    if not os.getenv("OPENAI_API_KEY"):
        print("WARNING: OPENAI_API_KEY not set!")
        print("   Set it with: export OPENAI_API_KEY='your-key-here'")

    print("\nStarting Resume Processing Microservice...")
    print(f"   Version: 2.0.0 (JSON Only)")
    print(f"   URL: http://localhost:8080")
    print(f"   Docs: http://localhost:8080/docs")
    print(f"   API Key: {os.getenv('API_SECRET_KEY', 'dev-secret-key-12345')}")
    print(f"   Endpoints:")
    print(f"      - POST /process (Full pipeline)")
    print(f"      - POST /structure (Job structuring only)")
    print(f"      - GET /health (Health check)\n")

    uvicorn.run(app, host="0.0.0.0", port=8080)
