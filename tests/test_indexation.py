"""
Unit tests for FAISS indexation functionality.

Tests cover:
- Index creation from documents
- Index persistence (save/load)
- Index search functionality
- Edge cases and error handling

Uses FakeEmbeddings to avoid API calls for fast unit tests.
"""

import pytest
from pathlib import Path
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import FakeEmbeddings


# ============== FIXTURES ==============


@pytest.fixture
def sample_documents():
    """Small set of test documents for unit tests."""
    return [
        Document(
            page_content="Concert de jazz à Annecy le 15 mars 2026",
            metadata={"city": "Annecy", "type": "concert", "id": "1"},
        ),
        Document(
            page_content="Exposition d'art contemporain à Chambéry",
            metadata={"city": "Chambéry", "type": "exposition", "id": "2"},
        ),
        Document(
            page_content="Festival de musique classique à Grenoble",
            metadata={"city": "Grenoble", "type": "festival", "id": "3"},
        ),
        Document(
            page_content="Atelier créatif pour enfants à Annecy",
            metadata={"city": "Annecy", "type": "atelier", "id": "4"},
        ),
        Document(
            page_content="Visite guidée du patrimoine à Thonon-les-Bains",
            metadata={"city": "Thonon-les-Bains", "type": "visite", "id": "5"},
        ),
    ]


@pytest.fixture
def fake_embeddings():
    """Fake embeddings for fast unit tests (no API calls)."""
    return FakeEmbeddings(size=1024)  # Match Mistral embedding dimension


@pytest.fixture
def sample_vectorstore(sample_documents, fake_embeddings):
    """Pre-built vectorstore for tests that need an existing index."""
    return FAISS.from_documents(sample_documents, fake_embeddings)


# ============== INDEX CREATION TESTS ==============


class TestIndexCreation:
    """Test FAISS index creation from documents."""

    def test_index_creation_from_documents(self, sample_documents, fake_embeddings):
        """Index can be created from a list of documents."""
        vectorstore = FAISS.from_documents(sample_documents, fake_embeddings)
        assert vectorstore is not None
        assert vectorstore.index is not None

    def test_index_size_matches_documents(self, sample_documents, fake_embeddings):
        """Index contains the correct number of vectors."""
        vectorstore = FAISS.from_documents(sample_documents, fake_embeddings)
        assert vectorstore.index.ntotal == len(sample_documents)

    def test_single_document_index(self, fake_embeddings):
        """Index can be created from a single document."""
        docs = [Document(page_content="Test document", metadata={"id": "1"})]
        vectorstore = FAISS.from_documents(docs, fake_embeddings)
        assert vectorstore.index.ntotal == 1

    def test_index_preserves_metadata(self, sample_documents, fake_embeddings):
        """Document metadata is preserved in the index."""
        vectorstore = FAISS.from_documents(sample_documents, fake_embeddings)
        results = vectorstore.similarity_search("concert", k=1)

        assert len(results) == 1
        assert "city" in results[0].metadata
        assert "type" in results[0].metadata
        assert "id" in results[0].metadata


# ============== INDEX PERSISTENCE TESTS ==============


class TestIndexPersistence:
    """Test index save/load functionality."""

    def test_index_save_creates_files(self, sample_vectorstore, tmp_path):
        """Saving index creates the expected files."""
        save_path = tmp_path / "test_index"
        sample_vectorstore.save_local(str(save_path))

        assert save_path.exists()
        assert (save_path / "index.faiss").exists()
        assert (save_path / "index.pkl").exists()

    def test_index_save_load_cycle(self, sample_documents, fake_embeddings, tmp_path):
        """Index can be saved and reloaded correctly."""
        # Create and save
        vectorstore = FAISS.from_documents(sample_documents, fake_embeddings)
        save_path = tmp_path / "test_index"
        vectorstore.save_local(str(save_path))

        # Reload
        loaded = FAISS.load_local(
            str(save_path), fake_embeddings, allow_dangerous_deserialization=True
        )

        # Verify same size
        assert loaded.index.ntotal == vectorstore.index.ntotal

    def test_loaded_index_is_searchable(self, sample_documents, fake_embeddings, tmp_path):
        """Reloaded index can perform searches."""
        # Create, save, reload
        vectorstore = FAISS.from_documents(sample_documents, fake_embeddings)
        save_path = tmp_path / "test_index"
        vectorstore.save_local(str(save_path))

        loaded = FAISS.load_local(
            str(save_path), fake_embeddings, allow_dangerous_deserialization=True
        )

        # Search should work
        results = loaded.similarity_search("concert", k=2)
        assert len(results) == 2

    def test_load_nonexistent_index_raises(self, fake_embeddings, tmp_path):
        """Loading from nonexistent path raises appropriate error."""
        with pytest.raises(Exception):
            FAISS.load_local(
                str(tmp_path / "nonexistent"), fake_embeddings, allow_dangerous_deserialization=True
            )


# ============== INDEX SEARCH TESTS ==============


class TestIndexSearch:
    """Test index search functionality."""

    def test_search_returns_k_documents(self, sample_vectorstore):
        """Search returns the requested number of documents."""
        results = sample_vectorstore.similarity_search("concert", k=3)
        assert len(results) == 3

    def test_search_returns_fewer_if_not_enough_docs(self, fake_embeddings):
        """Search returns fewer docs if k > total documents."""
        docs = [
            Document(page_content="Doc 1", metadata={"id": "1"}),
            Document(page_content="Doc 2", metadata={"id": "2"}),
        ]
        vectorstore = FAISS.from_documents(docs, fake_embeddings)

        results = vectorstore.similarity_search("doc", k=10)
        assert len(results) == 2  # Only 2 docs exist

    def test_search_returns_documents_with_metadata(self, sample_vectorstore):
        """Search results include document metadata."""
        results = sample_vectorstore.similarity_search("Annecy", k=2)

        for doc in results:
            assert hasattr(doc, "metadata")
            assert isinstance(doc.metadata, dict)

    def test_search_with_score(self, sample_vectorstore):
        """Search with score returns tuples of (doc, score)."""
        results = sample_vectorstore.similarity_search_with_score("jazz", k=2)

        assert len(results) == 2
        for doc, score in results:
            assert isinstance(doc, Document)
            # Score can be float or numpy float type
            assert isinstance(score, (float, int)) or hasattr(score, "__float__")

    def test_search_scores_are_non_negative(self, sample_vectorstore):
        """Search scores are non-negative (distance-based)."""
        results = sample_vectorstore.similarity_search_with_score("concert", k=3)

        for doc, score in results:
            assert score >= 0


# ============== EDGE CASES TESTS ==============


class TestEdgeCases:
    """Test edge cases and special inputs."""

    def test_special_characters_in_content(self, fake_embeddings):
        """Documents with emojis and special characters are handled."""
        docs = [
            Document(page_content="🎵 Concert à Grenoble 🎶", metadata={"id": "1"}),
            Document(page_content="Événement spécial été 2026!", metadata={"id": "2"}),
            Document(
                page_content="Prix: 15€ - Réservation: contact@event.fr", metadata={"id": "3"}
            ),
        ]
        vectorstore = FAISS.from_documents(docs, fake_embeddings)
        assert vectorstore.index.ntotal == 3

    def test_french_accents_in_content(self, fake_embeddings):
        """Documents with French accents are handled correctly."""
        docs = [
            Document(page_content="Événement à Château-d'Œx", metadata={"id": "1"}),
            Document(page_content="Fête de la crêpe à Béziers", metadata={"id": "2"}),
        ]
        vectorstore = FAISS.from_documents(docs, fake_embeddings)

        results = vectorstore.similarity_search("événement", k=1)
        assert len(results) == 1

    def test_very_long_document(self, fake_embeddings):
        """Very long documents are handled."""
        long_text = "Concert de jazz à Annecy. " * 500  # ~13000 chars
        docs = [Document(page_content=long_text, metadata={"id": "1"})]

        vectorstore = FAISS.from_documents(docs, fake_embeddings)
        assert vectorstore.index.ntotal == 1

    def test_empty_metadata(self, fake_embeddings):
        """Documents with empty metadata are handled."""
        docs = [
            Document(page_content="Document sans metadata", metadata={}),
        ]
        vectorstore = FAISS.from_documents(docs, fake_embeddings)

        results = vectorstore.similarity_search("document", k=1)
        assert len(results) == 1
        assert results[0].metadata == {}

    def test_duplicate_documents(self, fake_embeddings):
        """Duplicate documents are indexed separately."""
        docs = [
            Document(page_content="Same content", metadata={"id": "1"}),
            Document(page_content="Same content", metadata={"id": "2"}),
        ]
        vectorstore = FAISS.from_documents(docs, fake_embeddings)

        # Both should be indexed
        assert vectorstore.index.ntotal == 2


# ============== INTEGRATION TESTS ==============


@pytest.mark.integration
@pytest.mark.slow
class TestIndexIntegration:
    """Integration tests with real index (slower, requires data files)."""

    def test_production_index_exists(self):
        """Verify the production index files exist."""
        index_path = Path("data/index/faiss_baseline")
        assert index_path.exists(), f"Index path does not exist: {index_path}"
        assert (index_path / "index.faiss").exists(), "index.faiss not found"
        assert (index_path / "index.pkl").exists(), "index.pkl not found"

    def test_production_index_has_documents(self):
        """Production index contains expected number of documents."""
        # This test requires the actual embeddings model
        # Skip if not available
        pytest.skip("Requires Mistral API key for real embeddings")
