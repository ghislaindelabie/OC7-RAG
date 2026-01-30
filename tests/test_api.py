"""
API endpoint tests.

Tests are organized by endpoint and follow the test-driven approach:
- Write tests alongside implementation
- Each feature has corresponding tests
- Tests serve as documentation
"""

import pytest
from fastapi import status


# ============================================================================
# Test Infrastructure
# ============================================================================

def test_fixtures_available(client, mock_rag_service):
    """Verify that test fixtures are properly configured."""
    assert client is not None
    assert mock_rag_service is not None
    assert mock_rag_service.is_ready() is True


# ============================================================================
# Health Endpoint Tests (Step 2)
# ============================================================================

class TestHealthEndpoint:
    """Tests for GET /health endpoint."""

    def test_health_returns_200_when_service_ready(self, client):
        """Health check should return 200 when service is ready."""
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK

    def test_health_response_structure(self, client):
        """Health check should return proper response structure."""
        response = client.get("/health")
        data = response.json()

        # Check required fields
        assert "status" in data
        assert "index_loaded" in data
        assert "index_size" in data
        assert "llm_available" in data
        assert "timestamp" in data

    def test_health_shows_healthy_status_when_all_ready(self, client):
        """Health should be 'healthy' when index and LLM are available."""
        response = client.get("/health")
        data = response.json()

        assert data["status"] == "healthy"
        assert data["index_loaded"] is True
        assert data["llm_available"] is True
        assert data["index_size"] == 8547

    def test_health_shows_unhealthy_when_service_not_ready(self, client_unhealthy):
        """Health should be 'unhealthy' when service is not ready."""
        response = client_unhealthy.get("/health")
        data = response.json()

        assert data["status"] == "unhealthy"
        assert data["index_loaded"] is False
        assert data["llm_available"] is False
        assert data["index_size"] is None


# ============================================================================
# Ask Endpoint Tests (Step 3)
# ============================================================================

class TestAskEndpoint:
    """Tests for POST /api/v1/ask endpoint."""

    def test_ask_valid_question_returns_200(self, client, sample_question_request):
        """Ask endpoint should return 200 for valid question."""
        response = client.post("/api/v1/ask", json=sample_question_request)
        assert response.status_code == status.HTTP_200_OK

    def test_ask_returns_answer_response_structure(self, client, sample_question_request):
        """Ask endpoint should return proper response structure."""
        response = client.post("/api/v1/ask", json=sample_question_request)
        data = response.json()

        # Check required fields
        assert "answer" in data
        assert "sources" in data
        assert "metadata" in data

        # Check metadata structure
        assert "rag_method" in data["metadata"]
        assert "response_time_ms" in data["metadata"]
        assert "retrieved_docs_count" in data["metadata"]
        assert "timestamp" in data["metadata"]

    def test_ask_returns_sources_with_structure(self, client, sample_question_request):
        """Ask endpoint should return sources with proper structure."""
        response = client.post("/api/v1/ask", json=sample_question_request)
        data = response.json()

        assert len(data["sources"]) > 0
        source = data["sources"][0]

        assert "title" in source
        assert "location" in source
        assert "date_start" in source
        assert "description_snippet" in source

    def test_ask_empty_question_returns_422(self, client):
        """Ask endpoint should return 422 for empty question."""
        response = client.post("/api/v1/ask", json={"question": "", "rag_method": "hybrid"})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_ask_short_question_returns_422(self, client):
        """Ask endpoint should return 422 for question shorter than 3 chars."""
        response = client.post("/api/v1/ask", json={"question": "ab", "rag_method": "hybrid"})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_ask_invalid_rag_method_returns_422(self, client):
        """Ask endpoint should return 422 for invalid RAG method."""
        response = client.post(
            "/api/v1/ask",
            json={"question": "Test question", "rag_method": "invalid_method"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_ask_basic_method(self, client):
        """Ask endpoint should accept basic RAG method."""
        response = client.post(
            "/api/v1/ask",
            json={"question": "Quels concerts à Annecy?", "rag_method": "basic"}
        )
        assert response.status_code == status.HTTP_200_OK
        # Note: Mock returns static response; actual rag_method verification is in integration tests

    def test_ask_advanced_method(self, client):
        """Ask endpoint should work with advanced RAG method."""
        response = client.post(
            "/api/v1/ask",
            json={"question": "Quels concerts à Annecy?", "rag_method": "advanced"}
        )
        assert response.status_code == status.HTTP_200_OK

    def test_ask_default_method_is_hybrid(self, client):
        """Ask endpoint should use hybrid as default method."""
        response = client.post(
            "/api/v1/ask",
            json={"question": "Quels concerts à Annecy?"}
        )
        assert response.status_code == status.HTTP_200_OK

    def test_ask_top_k_parameter(self, client):
        """Ask endpoint should accept top_k parameter."""
        response = client.post(
            "/api/v1/ask",
            json={"question": "Quels concerts?", "rag_method": "hybrid", "top_k": 3}
        )
        assert response.status_code == status.HTTP_200_OK

    def test_ask_top_k_out_of_range_returns_422(self, client):
        """Ask endpoint should return 422 for top_k > 20."""
        response = client.post(
            "/api/v1/ask",
            json={"question": "Quels concerts?", "rag_method": "hybrid", "top_k": 25}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_ask_returns_503_when_service_not_ready(self, client_unhealthy):
        """Ask endpoint should return 503 when RAG service is not ready."""
        response = client_unhealthy.post(
            "/api/v1/ask",
            json={"question": "Quels concerts?", "rag_method": "hybrid"}
        )
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


# ============================================================================
# Rebuild Endpoint Tests (Step 4)
# ============================================================================

class TestRebuildEndpoint:
    """Tests for POST /api/v1/rebuild endpoint."""

    def test_rebuild_returns_200(self, client, sample_rebuild_request):
        """Rebuild endpoint should return 200 for valid request."""
        response = client.post("/api/v1/rebuild", json=sample_rebuild_request)
        assert response.status_code == status.HTTP_200_OK

    def test_rebuild_response_structure(self, client, sample_rebuild_request):
        """Rebuild endpoint should return proper response structure."""
        response = client.post("/api/v1/rebuild", json=sample_rebuild_request)
        data = response.json()

        # Check required fields
        assert "status" in data
        assert "message" in data
        assert "build_time_seconds" in data
        assert "index_path" in data

        # status should be one of: success, skipped, failed
        assert data["status"] in ["success", "skipped", "failed"]

    def test_rebuild_with_force_true(self, client):
        """Rebuild endpoint should accept force=true."""
        response = client.post(
            "/api/v1/rebuild",
            json={"force": True, "download_fresh_data": False}
        )
        assert response.status_code == status.HTTP_200_OK

    def test_rebuild_with_force_false(self, client):
        """Rebuild endpoint should accept force=false."""
        response = client.post(
            "/api/v1/rebuild",
            json={"force": False, "download_fresh_data": False}
        )
        assert response.status_code == status.HTTP_200_OK

    def test_rebuild_without_download(self, client):
        """Rebuild endpoint should work without downloading fresh data."""
        response = client.post(
            "/api/v1/rebuild",
            json={"force": False, "download_fresh_data": False}
        )
        assert response.status_code == status.HTTP_200_OK

    def test_rebuild_returns_503_when_service_not_ready(self, client_unhealthy):
        """Rebuild endpoint should return 503 when service not initialized."""
        response = client_unhealthy.post(
            "/api/v1/rebuild",
            json={"force": False, "download_fresh_data": False}
        )
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


# ============================================================================
# RAG Info Endpoint Tests
# ============================================================================

class TestRAGInfoEndpoint:
    """Tests for GET /api/v1/rag/info endpoint."""

    def test_rag_info_returns_200_when_ready(self, client):
        """RAG info should return 200 when service is ready."""
        response = client.get("/api/v1/rag/info")
        assert response.status_code == status.HTTP_200_OK

    def test_rag_info_returns_503_when_not_ready(self, client_unhealthy):
        """RAG info should return 503 when service is not ready."""
        response = client_unhealthy.get("/api/v1/rag/info")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    def test_rag_info_response_structure(self, client):
        """RAG info should return proper response structure."""
        response = client.get("/api/v1/rag/info")
        data = response.json()

        assert "version" in data
        assert "available_methods" in data
        assert "index_info" in data
        assert "model_info" in data

        # Check nested structure
        assert "documents_count" in data["index_info"]
        assert "llm_model" in data["model_info"]


# ============================================================================
# Error Handling Tests (Step 5 - placeholder)
# ============================================================================

class TestErrorHandling:
    """Tests for error handling and edge cases."""

    @pytest.mark.skip(reason="Will be implemented in Step 5")
    def test_invalid_rag_method_returns_error(self, client):
        """Invalid RAG method should return validation error."""
        pass

    @pytest.mark.skip(reason="Will be implemented in Step 5")
    def test_malformed_request_returns_422(self, client):
        """Malformed request should return 422."""
        pass
