"""
FastAPI Application for RAG Cultural Events Assistant

Provides REST API endpoints for querying cultural events using RAG.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse

from .rag_service import get_rag_service
from .schemas import (
    AnswerResponse,
    ErrorResponse,
    HealthResponse,
    QuestionRequest,
    RAGInfoResponse,
    RebuildRequest,
    RebuildResponse,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    logger.info("Starting up RAG API...")

    # Get RAG service (triggers initialization)
    rag_service = get_rag_service()

    if rag_service.is_ready():
        logger.info("RAG service ready - index loaded")
    else:
        logger.warning("RAG service not ready - index not loaded")

    if rag_service.is_llm_available():
        logger.info("LLM available")
    else:
        logger.warning("LLM not available - check MISTRAL_API_KEY")

    logger.info("API startup complete")

    yield

    # Shutdown
    logger.info("Shutting down RAG API...")


# Create FastAPI app
app = FastAPI(
    title="Puls-Events RAG API",
    description="REST API for querying cultural events in Savoie, Haute-Savoie, and Isère using RAG",
    version="0.3.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ============================================================================
# Health Check Endpoint
# ============================================================================

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Check API health and service status.

    Returns health status, index state, and LLM availability.
    """
    rag_service = get_rag_service()

    # Determine overall status
    if rag_service.is_ready() and rag_service.is_llm_available():
        overall_status = "healthy"
    elif rag_service.is_ready() or rag_service.is_llm_available():
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"

    return HealthResponse(
        status=overall_status,
        index_loaded=rag_service.is_ready(),
        index_size=rag_service.get_index_size(),
        llm_available=rag_service.is_llm_available(),
        timestamp=datetime.utcnow().isoformat() + "Z",
    )


# ============================================================================
# RAG Query Endpoint (will be implemented in Step 3)
# ============================================================================

@app.post(
    "/api/v1/ask",
    response_model=AnswerResponse,
    tags=["RAG"],
    summary="Ask a question about cultural events"
)
async def ask_question(request: QuestionRequest):
    """
    Query the RAG system with a question about cultural events.

    This endpoint accepts a question and returns an answer generated
    using the RAG system with retrieved event documents as sources.

    **RAG Methods:**
    - `basic`: FAISS vector similarity search only
    - `hybrid`: FAISS + BM25 keyword search combined
    - `advanced`: Hybrid + FlashRank reranking for better relevance
    """
    rag_service = get_rag_service()

    # Check if service is ready
    if not rag_service.is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG service not ready - index not loaded"
        )

    if not rag_service.is_llm_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM not available - check API configuration"
        )

    try:
        # Query the RAG system
        result = rag_service.query(
            question=request.question,
            method=request.rag_method,
            top_k=request.top_k
        )

        # Build response with proper schema types
        from .schemas import EventSource, QueryMetadata

        sources = [
            EventSource(
                title=s["title"],
                location=s.get("location"),
                date_start=s.get("date_start"),
                description_snippet=s.get("description_snippet"),
                relevance_score=s.get("relevance_score")
            )
            for s in result["sources"]
        ]

        metadata = QueryMetadata(
            rag_method=result["metadata"]["rag_method"],
            response_time_ms=result["metadata"]["response_time_ms"],
            retrieved_docs_count=result["metadata"]["retrieved_docs_count"],
            timestamp=result["metadata"]["timestamp"],
            model_version=result["metadata"].get("model_version")
        )

        return AnswerResponse(
            answer=result["answer"],
            sources=sources,
            metadata=metadata
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error processing question: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing question"
        )


# ============================================================================
# Index Rebuild Endpoint (will be implemented in Step 4)
# ============================================================================

@app.post(
    "/api/v1/rebuild",
    response_model=RebuildResponse,
    tags=["Admin"],
    summary="Rebuild the FAISS index"
)
async def rebuild_index(request: RebuildRequest):
    """
    Rebuild the FAISS index from fresh or cached data.

    This endpoint downloads fresh event data (if requested) and
    rebuilds the vector index. Use with caution in production.
    """
    # TODO: Implement in Step 4
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Endpoint not yet implemented"
    )


# ============================================================================
# RAG Info Endpoint
# ============================================================================

@app.get(
    "/api/v1/rag/info",
    response_model=RAGInfoResponse,
    tags=["Info"],
    summary="Get RAG system information"
)
async def get_rag_info():
    """
    Get information about the RAG system.

    Returns system version, available methods, index statistics,
    and model information.
    """
    rag_service = get_rag_service()

    if not rag_service.is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG service not ready"
        )

    info = rag_service.get_info()
    return RAGInfoResponse(**info)


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="internal_server_error",
            message="An unexpected error occurred",
            detail=str(exc) if logger.level == logging.DEBUG else None
        ).model_dump(),
    )


# ============================================================================
# Development Server Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
