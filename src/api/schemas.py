"""
Pydantic schemas for API request/response validation.

These schemas define the contract between the RAG API and its clients.
"""

from typing import List, Literal, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator


# ============================================================================
# Ask Endpoint Schemas
# ============================================================================


class QuestionRequest(BaseModel):
    """Request schema for the /ask endpoint."""

    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="User question about cultural events",
        examples=["Quels concerts ont lieu à Annecy ce week-end?"],
    )
    rag_method: Literal["basic", "hybrid", "advanced"] = Field(
        default="hybrid", description="RAG retrieval method to use"
    )
    top_k: int = Field(default=5, ge=1, le=20, description="Number of documents to retrieve")
    reference_date: Optional[str] = Field(
        default=None,
        description="Reference date for temporal queries (ISO format: YYYY-MM-DD). "
        "Defaults to 2024-02-06. The RAG system uses this as 'today' "
        "to interpret relative date expressions like 'ce weekend'.",
        examples=["2024-02-06", "2024-07-15"],
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        """Validate and clean question input."""
        # Strip whitespace
        v = v.strip()

        # Check if question is not just whitespace
        if not v or v.isspace():
            raise ValueError("Question cannot be empty or only whitespace")

        # Check if question is meaningful (not just repeated characters)
        if len(set(v.replace(" ", ""))) < 3:
            raise ValueError("Question must contain meaningful text")

        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "question": "Quels sont les événements gratuits à Grenoble ce mois-ci?",
                "rag_method": "hybrid",
                "top_k": 5,
                "reference_date": "2024-02-06",
            }
        }
    )


class EventSource(BaseModel):
    """Information about a retrieved event document."""

    title: str = Field(..., description="Event title")
    location: Optional[str] = Field(None, description="Event location (city)")
    date_start: Optional[str] = Field(None, description="Event start date")
    description_snippet: Optional[str] = Field(None, description="Short snippet from description")
    relevance_score: Optional[float] = Field(None, description="Relevance score (if available)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Festival de Jazz",
                "location": "Annecy",
                "date_start": "2026-07-15",
                "description_snippet": "Un festival de jazz exceptionnel...",
                "relevance_score": 0.85,
            }
        }
    )


class QueryMetadata(BaseModel):
    """Metadata about the query execution."""

    rag_method: str = Field(..., description="RAG method used")
    response_time_ms: int = Field(..., description="Response time in milliseconds")
    retrieved_docs_count: int = Field(..., description="Number of documents retrieved")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    model_version: Optional[str] = Field(None, description="LLM model version")
    reference_date: Optional[str] = Field(
        None, description="Reference date used for temporal queries (ISO YYYY-MM-DD)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "rag_method": "hybrid",
                "response_time_ms": 1250,
                "retrieved_docs_count": 5,
                "timestamp": "2026-01-29T18:30:00.000000Z",
                "model_version": "mistral-small-latest",
                "reference_date": "2024-02-06",
            }
        }
    )


class AnswerResponse(BaseModel):
    """Response schema for the /ask endpoint."""

    answer: str = Field(..., description="Generated answer to the question")
    sources: List[EventSource] = Field(
        default_factory=list, description="Retrieved event documents used to generate answer"
    )
    metadata: QueryMetadata = Field(..., description="Query execution metadata")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "answer": "Voici les concerts à Annecy ce week-end : ...",
                "sources": [
                    {
                        "title": "Concert de Jazz",
                        "location": "Annecy",
                        "date_start": "2026-02-01",
                        "description_snippet": "Un concert exceptionnel...",
                    }
                ],
                "metadata": {
                    "rag_method": "hybrid",
                    "response_time_ms": 1250,
                    "retrieved_docs_count": 5,
                    "timestamp": "2026-01-29T18:30:00.000000Z",
                },
            }
        }
    )


# ============================================================================
# Rebuild Endpoint Schemas
# ============================================================================


class RebuildRequest(BaseModel):
    """Request schema for the /rebuild endpoint."""

    force: bool = Field(default=False, description="Force rebuild even if recent index exists")
    download_fresh_data: bool = Field(
        default=True, description="Download fresh data from OpenAgenda before rebuilding"
    )

    model_config = ConfigDict(
        json_schema_extra={"example": {"force": False, "download_fresh_data": True}}
    )


class RebuildResponse(BaseModel):
    """Response schema for the /rebuild endpoint."""

    status: Literal["success", "skipped", "failed"] = Field(..., description="Rebuild status")
    message: str = Field(..., description="Status message")
    events_indexed: Optional[int] = Field(None, description="Number of events indexed")
    build_time_seconds: Optional[float] = Field(None, description="Time taken to rebuild")
    index_path: Optional[str] = Field(None, description="Path to the rebuilt index")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "message": "Index rebuilt successfully",
                "events_indexed": 8547,
                "build_time_seconds": 45.2,
                "index_path": "data/index/faiss_baseline",
            }
        }
    )


# ============================================================================
# Health Endpoint Schemas
# ============================================================================


class HealthResponse(BaseModel):
    """Response schema for the /health endpoint."""

    status: Literal["healthy", "unhealthy", "degraded"] = Field(
        ..., description="Overall health status"
    )
    index_loaded: bool = Field(..., description="Is FAISS index loaded?")
    index_size: Optional[int] = Field(None, description="Number of documents in index")
    llm_available: bool = Field(..., description="Is LLM API accessible?")
    timestamp: str = Field(..., description="ISO 8601 timestamp")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "index_loaded": True,
                "index_size": 8547,
                "llm_available": True,
                "timestamp": "2026-01-29T18:30:00.000000Z",
            }
        }
    )


# ============================================================================
# RAG Info Endpoint Schemas
# ============================================================================


class RAGInfoResponse(BaseModel):
    """Response schema for the /api/v1/rag/info endpoint."""

    version: str = Field(..., description="RAG system version")
    available_methods: List[str] = Field(..., description="Available RAG methods")
    index_info: Dict[str, Any] = Field(..., description="Information about loaded index")
    model_info: Dict[str, Any] = Field(..., description="Information about LLM model")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "version": "0.3.0",
                "available_methods": ["basic", "hybrid", "advanced"],
                "index_info": {
                    "documents_count": 8547,
                    "embedding_model": "mistral-embed",
                    "embedding_dimension": 1024,
                    "last_updated": "2026-01-29T10:00:00Z",
                },
                "model_info": {"llm_model": "mistral-small-latest", "provider": "Mistral AI"},
            }
        }
    )


# ============================================================================
# Error Schemas
# ============================================================================


class ErrorResponse(BaseModel):
    """Standard error response schema."""

    error: str = Field(..., description="Error type/code")
    message: str = Field(..., description="Human-readable error message")
    detail: Optional[str] = Field(None, description="Additional error details")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "validation_error",
                "message": "Invalid question format",
                "detail": "Question must be between 3 and 1000 characters",
            }
        }
    )
