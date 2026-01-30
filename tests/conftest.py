"""
Pytest configuration and shared fixtures for API tests.
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def mock_rag_service():
    """
    Mock RAG service for testing without loading actual index.

    Returns a MagicMock configured with typical RAG service responses.
    """
    mock = MagicMock()

    # Configure default behavior
    mock.is_ready.return_value = True
    mock.is_llm_available.return_value = True
    mock.get_index_size.return_value = 8547

    # Mock query response
    mock.query.return_value = {
        "answer": "Voici les événements trouvés: Festival de Jazz à Annecy...",
        "sources": [
            {
                "title": "Festival de Jazz",
                "location": "Annecy",
                "date_start": "2026-07-15",
                "description_snippet": "Un festival de jazz exceptionnel...",
                "relevance_score": 0.85
            },
            {
                "title": "Concert Rock",
                "location": "Grenoble",
                "date_start": "2026-07-20",
                "description_snippet": "Concert de rock avec groupes locaux...",
                "relevance_score": 0.78
            }
        ],
        "metadata": {
            "rag_method": "hybrid",
            "response_time_ms": 1250,
            "retrieved_docs_count": 2,
            "timestamp": "2026-01-29T18:30:00.000000Z",
            "model_version": "mistral-small-latest"
        }
    }

    # Mock get_info response
    mock.get_info.return_value = {
        "version": "0.3.0",
        "available_methods": ["basic", "hybrid", "advanced"],
        "index_info": {
            "documents_count": 8547,
            "embedding_model": "mistral-embed",
            "embedding_dimension": 1024,
            "last_updated": "2026-01-29T10:00:00Z"
        },
        "model_info": {
            "llm_model": "mistral-small-latest",
            "provider": "Mistral AI"
        }
    }

    # Mock rebuild_index response
    mock.rebuild_index.return_value = {
        "status": "success",
        "message": "Index rebuilt successfully",
        "events_indexed": 8547,
        "build_time_seconds": 45.2,
        "index_path": "data/index/faiss_baseline"
    }

    return mock


@pytest.fixture
def client(mock_rag_service):
    """
    FastAPI test client with mocked RAG service.

    This client can be used to test endpoints without loading
    the actual FAISS index or calling the Mistral API.
    """
    # Patch the get_rag_service function to return our mock
    with patch("src.api.main.get_rag_service", return_value=mock_rag_service):
        from src.api.main import app
        with TestClient(app) as test_client:
            yield test_client


@pytest.fixture
def client_unhealthy():
    """
    Test client with RAG service in unhealthy state.

    Useful for testing error handling when service is not ready.
    """
    mock = MagicMock()
    mock._initialized = False  # Service not initialized
    mock.is_ready.return_value = False
    mock.is_llm_available.return_value = False
    mock.get_index_size.return_value = None

    with patch("src.api.main.get_rag_service", return_value=mock):
        from src.api.main import app
        with TestClient(app) as test_client:
            yield test_client


@pytest.fixture
def sample_question_request():
    """Sample valid question request payload."""
    return {
        "question": "Quels sont les événements gratuits à Grenoble ce mois-ci?",
        "rag_method": "hybrid",
        "top_k": 5
    }


@pytest.fixture
def sample_rebuild_request():
    """Sample valid rebuild request payload."""
    return {
        "force": False,
        "download_fresh_data": True
    }
