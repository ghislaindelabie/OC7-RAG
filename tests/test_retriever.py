"""
Unit tests for retriever functionality.

Tests cover:
- FAISS (dense/semantic) retriever
- BM25 (sparse/keyword) retriever
- Hybrid (Ensemble) retriever with RRF
- Edge cases and error handling

Uses FakeEmbeddings to avoid API calls for fast unit tests.
"""

import pytest
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever
from langchain_community.embeddings import FakeEmbeddings
from langchain_classic.retrievers import EnsembleRetriever


# ============== FIXTURES ==============


@pytest.fixture
def sample_documents():
    """Test documents with varied content for retrieval testing."""
    return [
        Document(
            page_content="Concert de jazz à Annecy le 15 mars",
            metadata={"city": "Annecy", "type": "concert", "id": "1"},
        ),
        Document(
            page_content="Exposition art contemporain Chambéry musée",
            metadata={"city": "Chambéry", "type": "exposition", "id": "2"},
        ),
        Document(
            page_content="Festival musique classique Grenoble été",
            metadata={"city": "Grenoble", "type": "festival", "id": "3"},
        ),
        Document(
            page_content="Atelier créatif enfants Annecy samedi",
            metadata={"city": "Annecy", "type": "atelier", "id": "4"},
        ),
        Document(
            page_content="Visite guidée patrimoine Thonon-les-Bains",
            metadata={"city": "Thonon-les-Bains", "type": "visite", "id": "5"},
        ),
        Document(
            page_content="Job dating recrutement France Travail Grenoble",
            metadata={"city": "Grenoble", "type": "emploi", "id": "6"},
        ),
        Document(
            page_content="Journées du patrimoine château Chambéry",
            metadata={"city": "Chambéry", "type": "patrimoine", "id": "7"},
        ),
    ]


@pytest.fixture
def fake_embeddings():
    """Fake embeddings for fast unit tests."""
    return FakeEmbeddings(size=1024)


@pytest.fixture
def faiss_vectorstore(sample_documents, fake_embeddings):
    """FAISS vectorstore built from sample documents."""
    return FAISS.from_documents(sample_documents, fake_embeddings)


@pytest.fixture
def faiss_retriever(faiss_vectorstore):
    """FAISS retriever with k=3."""
    return faiss_vectorstore.as_retriever(search_kwargs={"k": 3})


@pytest.fixture
def bm25_retriever(sample_documents):
    """BM25 retriever with k=3."""
    retriever = BM25Retriever.from_documents(sample_documents)
    retriever.k = 3
    return retriever


@pytest.fixture
def hybrid_retriever(faiss_retriever, bm25_retriever):
    """Hybrid (Ensemble) retriever combining FAISS and BM25."""
    return EnsembleRetriever(retrievers=[faiss_retriever, bm25_retriever], weights=[0.5, 0.5])


# ============== FAISS RETRIEVER TESTS ==============


class TestFAISSRetriever:
    """Test FAISS (dense/semantic) retriever."""

    def test_retriever_returns_k_docs(self, faiss_vectorstore):
        """Retriever returns exactly k documents."""
        retriever = faiss_vectorstore.as_retriever(search_kwargs={"k": 3})
        results = retriever.invoke("concert")
        assert len(results) == 3

    def test_retriever_respects_k_parameter(self, faiss_vectorstore):
        """Different k values return different numbers of results."""
        retriever_2 = faiss_vectorstore.as_retriever(search_kwargs={"k": 2})
        retriever_5 = faiss_vectorstore.as_retriever(search_kwargs={"k": 5})

        results_2 = retriever_2.invoke("festival")
        results_5 = retriever_5.invoke("festival")

        assert len(results_2) == 2
        assert len(results_5) == 5

    def test_retriever_returns_document_objects(self, faiss_retriever):
        """Retriever returns Document objects."""
        results = faiss_retriever.invoke("jazz")
        assert all(isinstance(doc, Document) for doc in results)

    def test_retriever_preserves_metadata(self, faiss_retriever):
        """Retrieved documents include their metadata."""
        results = faiss_retriever.invoke("Annecy")

        for doc in results:
            assert hasattr(doc, "metadata")
            assert "city" in doc.metadata
            assert "type" in doc.metadata

    def test_retriever_returns_page_content(self, faiss_retriever):
        """Retrieved documents have page_content."""
        results = faiss_retriever.invoke("concert")

        for doc in results:
            assert hasattr(doc, "page_content")
            assert len(doc.page_content) > 0


# ============== BM25 RETRIEVER TESTS ==============


class TestBM25Retriever:
    """Test BM25 (sparse/keyword) retriever."""

    def test_bm25_returns_results(self, bm25_retriever):
        """BM25 retriever returns results for a query."""
        results = bm25_retriever.invoke("concert")
        assert len(results) > 0

    def test_bm25_returns_k_docs(self, sample_documents):
        """BM25 retriever respects k parameter."""
        retriever = BM25Retriever.from_documents(sample_documents)
        retriever.k = 2

        results = retriever.invoke("Grenoble")
        assert len(results) == 2

    def test_bm25_keyword_matching(self, bm25_retriever):
        """BM25 finds documents containing exact keywords."""
        results = bm25_retriever.invoke("Annecy")

        # At least one result should contain "Annecy"
        texts = [doc.page_content for doc in results]
        assert any("Annecy" in text for text in texts)

    def test_bm25_finds_specific_city(self, sample_documents):
        """BM25 correctly retrieves documents for specific city."""
        retriever = BM25Retriever.from_documents(sample_documents)
        retriever.k = 5

        results = retriever.invoke("Thonon-les-Bains")
        texts = [doc.page_content for doc in results]

        # Should find the Thonon document
        assert any("Thonon" in text for text in texts)

    def test_bm25_handles_french_terms(self, bm25_retriever):
        """BM25 handles French terms correctly."""
        results = bm25_retriever.invoke("patrimoine")

        texts = [doc.page_content for doc in results]
        assert any("patrimoine" in text.lower() for text in texts)

    def test_bm25_returns_document_objects(self, bm25_retriever):
        """BM25 returns Document objects with metadata."""
        results = bm25_retriever.invoke("festival")

        for doc in results:
            assert isinstance(doc, Document)
            assert hasattr(doc, "metadata")


# ============== HYBRID RETRIEVER TESTS ==============


class TestHybridRetriever:
    """Test Ensemble (Hybrid) retriever combining FAISS + BM25."""

    def test_hybrid_returns_results(self, hybrid_retriever):
        """Hybrid retriever returns results."""
        results = hybrid_retriever.invoke("concert jazz")
        assert len(results) > 0

    def test_hybrid_returns_document_objects(self, hybrid_retriever):
        """Hybrid retriever returns Document objects."""
        results = hybrid_retriever.invoke("festival musique")

        for doc in results:
            assert isinstance(doc, Document)

    def test_hybrid_combines_both_retrievers(self, faiss_vectorstore, sample_documents):
        """Hybrid retriever uses both dense and sparse retrieval."""
        faiss_ret = faiss_vectorstore.as_retriever(search_kwargs={"k": 3})
        bm25_ret = BM25Retriever.from_documents(sample_documents)
        bm25_ret.k = 3

        hybrid = EnsembleRetriever(retrievers=[faiss_ret, bm25_ret], weights=[0.5, 0.5])

        # Query that benefits from both semantic and keyword matching
        results = hybrid.invoke("emploi recrutement")
        assert len(results) > 0

    def test_hybrid_different_weights(self, faiss_vectorstore, sample_documents):
        """Different weight configurations work correctly."""
        faiss_ret = faiss_vectorstore.as_retriever(search_kwargs={"k": 3})
        bm25_ret = BM25Retriever.from_documents(sample_documents)
        bm25_ret.k = 3

        # Dense-heavy
        hybrid_dense = EnsembleRetriever(retrievers=[faiss_ret, bm25_ret], weights=[0.9, 0.1])

        # Sparse-heavy
        hybrid_sparse = EnsembleRetriever(retrievers=[faiss_ret, bm25_ret], weights=[0.1, 0.9])

        results_dense = hybrid_dense.invoke("concert")
        results_sparse = hybrid_sparse.invoke("concert")

        # Both should return results
        assert len(results_dense) > 0
        assert len(results_sparse) > 0

    def test_hybrid_preserves_metadata(self, hybrid_retriever):
        """Hybrid retriever preserves document metadata."""
        results = hybrid_retriever.invoke("Chambéry")

        for doc in results:
            assert "city" in doc.metadata


# ============== EDGE CASES TESTS ==============


class TestRetrieverEdgeCases:
    """Test edge cases for all retrievers."""

    def test_empty_query_bm25(self, bm25_retriever):
        """Empty query is handled gracefully by BM25."""
        # Should not crash
        results = bm25_retriever.invoke("")
        assert isinstance(results, list)

    def test_empty_query_faiss(self, faiss_retriever):
        """Empty query is handled by FAISS retriever."""
        # May return results or empty, but shouldn't crash
        results = faiss_retriever.invoke("")
        assert isinstance(results, list)

    def test_query_with_special_characters(self, bm25_retriever):
        """Query with special characters is handled."""
        results = bm25_retriever.invoke("concert! @Annecy #music")
        assert isinstance(results, list)

    def test_query_with_numbers(self, bm25_retriever):
        """Query with numbers is handled."""
        results = bm25_retriever.invoke("15 mars 2026")
        assert isinstance(results, list)

    def test_very_long_query(self, faiss_retriever):
        """Very long query is handled."""
        long_query = "concert festival musique jazz " * 100
        results = faiss_retriever.invoke(long_query)
        assert isinstance(results, list)

    def test_query_no_matches_bm25(self, bm25_retriever):
        """Query with no keyword matches returns results (BM25 behavior)."""
        results = bm25_retriever.invoke("xyznonexistent123abc")
        # BM25 may still return results with low scores
        assert isinstance(results, list)

    def test_unicode_query(self, bm25_retriever):
        """Unicode characters in query are handled."""
        results = bm25_retriever.invoke("événement été château")
        assert isinstance(results, list)

    def test_single_word_query(self, faiss_retriever):
        """Single word query works correctly."""
        results = faiss_retriever.invoke("jazz")
        assert len(results) > 0

    def test_multi_word_query(self, hybrid_retriever):
        """Multi-word query works correctly."""
        results = hybrid_retriever.invoke("concert de jazz à Annecy en mars")
        assert len(results) > 0


# ============== RETRIEVER CONFIGURATION TESTS ==============


class TestRetrieverConfiguration:
    """Test retriever configuration options."""

    def test_faiss_search_type_similarity(self, faiss_vectorstore):
        """FAISS retriever with similarity search type."""
        retriever = faiss_vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 3})
        results = retriever.invoke("concert")
        assert len(results) == 3

    def test_faiss_search_type_mmr(self, faiss_vectorstore):
        """FAISS retriever with MMR (maximal marginal relevance)."""
        retriever = faiss_vectorstore.as_retriever(
            search_type="mmr", search_kwargs={"k": 3, "fetch_k": 5}
        )
        results = retriever.invoke("concert")
        assert len(results) == 3

    def test_bm25_different_k_values(self, sample_documents):
        """BM25 retriever with different k values."""
        for k in [1, 3, 5]:
            retriever = BM25Retriever.from_documents(sample_documents)
            retriever.k = k

            results = retriever.invoke("concert")
            assert len(results) == min(k, len(sample_documents))


# ============== INTEGRATION TESTS ==============


@pytest.mark.integration
@pytest.mark.slow
class TestRetrieverIntegration:
    """Integration tests with real index (slower)."""

    def test_real_faiss_retriever_search(self):
        """Test search on real FAISS index."""
        # Skip if real embeddings not available
        pytest.skip("Requires Mistral API key for real embeddings")

    def test_hybrid_on_real_data(self):
        """Test hybrid retriever on real dataset."""
        pytest.skip("Requires Mistral API key for real embeddings")
