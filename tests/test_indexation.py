"""
Unit tests for FAISS indexation functionality.

Tests cover:
- Index creation from documents
- Index persistence (save/load)
- Index search functionality
- Metadata date parsing (ISO dates)
- Edge cases and error handling

Uses FakeEmbeddings to avoid API calls for fast unit tests.
"""

import logging
import pytest
from pathlib import Path
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import FakeEmbeddings

from src.api.rag_service import (
    _build_metadata,
    _filter_past_events,
    _filter_temporal_window,
    _format_date_french,
    _parse_query_analysis_response,
    DEFAULT_REFERENCE_DATE,
    QUERY_ANALYSIS_PROMPT,
    RAG_PROMPT_TEMPLATE,
)


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


# ============== METADATA DATE PARSING TESTS ==============


class TestMetadataDateParsing:
    """Test ISO date metadata extraction from event data."""

    def test_valid_dates_parsed_to_iso(self):
        """Events with valid dates produce ISO-formatted metadata fields."""
        event = {
            "uid": "evt-001",
            "title_fr": "Concert de Jazz",
            "location_city": "Annecy",
            "location_department": "Haute-Savoie",
            "daterange_fr": "Samedi 15 juin 2024, 20h00",
            "firstdate_begin": "2024-06-15T20:00:00+02:00",
            "lastdate_end": "2024-06-15T23:00:00+02:00",
            "category": "concert",
            "canonicalurl": "https://example.com/evt-001",
        }
        metadata = _build_metadata(event)

        assert metadata["event_start_date"] == "2024-06-15"
        assert metadata["event_end_date"] == "2024-06-15"
        assert metadata["event_year"] == 2024
        assert metadata["event_month"] == 6

    def test_multiday_event_dates(self):
        """Multi-day events have different start and end dates."""
        event = {
            "firstdate_begin": "2024-07-01T10:00:00+02:00",
            "lastdate_end": "2024-07-05T22:00:00+02:00",
        }
        metadata = _build_metadata(event)

        assert metadata["event_start_date"] == "2024-07-01"
        assert metadata["event_end_date"] == "2024-07-05"
        assert metadata["event_year"] == 2024
        assert metadata["event_month"] == 7

    def test_missing_firstdate_gives_none(self):
        """Events without firstdate_begin get None for date fields."""
        event = {
            "uid": "evt-002",
            "title_fr": "Mystery Event",
            "lastdate_end": "2024-06-15T23:00:00+02:00",
        }
        metadata = _build_metadata(event)

        assert metadata["event_start_date"] is None
        assert metadata["event_end_date"] == "2024-06-15"
        assert metadata["event_year"] is None
        assert metadata["event_month"] is None

    def test_missing_lastdate_gives_none(self):
        """Events without lastdate_end get None for end_date only."""
        event = {
            "uid": "evt-003",
            "firstdate_begin": "2024-03-10T14:00:00+02:00",
        }
        metadata = _build_metadata(event)

        assert metadata["event_start_date"] == "2024-03-10"
        assert metadata["event_end_date"] is None
        assert metadata["event_year"] == 2024
        assert metadata["event_month"] == 3

    def test_missing_both_dates_gives_none(self):
        """Events with no date fields get None for all date metadata."""
        event = {"uid": "evt-004", "title_fr": "No Date Event"}
        metadata = _build_metadata(event)

        assert metadata["event_start_date"] is None
        assert metadata["event_end_date"] is None
        assert metadata["event_year"] is None
        assert metadata["event_month"] is None

    def test_malformed_date_gives_none_and_logs_warning(self, caplog):
        """Malformed date strings produce None and log a warning."""
        event = {
            "uid": "evt-005",
            "firstdate_begin": "not-a-date",
            "lastdate_end": "also-not-valid",
        }
        with caplog.at_level(logging.WARNING):
            metadata = _build_metadata(event)

        assert metadata["event_start_date"] is None
        assert metadata["event_end_date"] is None
        assert metadata["event_year"] is None
        assert metadata["event_month"] is None
        assert "date" in caplog.text.lower()

    def test_year_and_month_are_integers(self):
        """event_year and event_month are integers, not strings."""
        event = {
            "firstdate_begin": "2024-12-25T10:00:00Z",
            "lastdate_end": "2024-12-25T18:00:00Z",
        }
        metadata = _build_metadata(event)

        assert isinstance(metadata["event_year"], int)
        assert isinstance(metadata["event_month"], int)
        assert metadata["event_year"] == 2024
        assert metadata["event_month"] == 12

    def test_utc_z_suffix_parsed(self):
        """Dates with Z (UTC) suffix are parsed correctly."""
        event = {
            "firstdate_begin": "2024-01-15T08:00:00Z",
            "lastdate_end": "2024-01-15T17:00:00Z",
        }
        metadata = _build_metadata(event)

        assert metadata["event_start_date"] == "2024-01-15"
        assert metadata["event_end_date"] == "2024-01-15"

    def test_legacy_fields_preserved(self):
        """Original metadata fields (uid, title, city, etc.) are still present."""
        event = {
            "uid": "evt-006",
            "title_fr": "Test Event",
            "location_city": "Grenoble",
            "location_department": "Isère",
            "daterange_fr": "Lundi 1 avril, 10h00",
            "category": "exposition",
            "canonicalurl": "https://example.com/evt-006",
            "firstdate_begin": "2024-04-01T10:00:00+02:00",
            "lastdate_end": "2024-04-01T18:00:00+02:00",
        }
        metadata = _build_metadata(event)

        assert metadata["uid"] == "evt-006"
        assert metadata["title"] == "Test Event"
        assert metadata["city"] == "Grenoble"
        assert metadata["department"] == "Isère"
        assert metadata["daterange"] == "Lundi 1 avril, 10h00"
        assert metadata["category"] == "exposition"
        assert metadata["url"] == "https://example.com/evt-006"

    def test_index_with_date_metadata(self, fake_embeddings):
        """FAISS index works correctly with date metadata fields."""
        docs = [
            Document(
                page_content="Concert de jazz à Annecy",
                metadata={
                    "event_start_date": "2024-06-15",
                    "event_end_date": "2024-06-15",
                    "event_year": 2024,
                    "event_month": 6,
                    "city": "Annecy",
                },
            ),
            Document(
                page_content="Festival à Grenoble",
                metadata={
                    "event_start_date": "2024-07-01",
                    "event_end_date": "2024-07-05",
                    "event_year": 2024,
                    "event_month": 7,
                    "city": "Grenoble",
                },
            ),
        ]
        vectorstore = FAISS.from_documents(docs, fake_embeddings)
        assert vectorstore.index.ntotal == 2

        results = vectorstore.similarity_search("concert", k=1)
        assert "event_start_date" in results[0].metadata
        assert "event_year" in results[0].metadata


# ============== TEMPORAL CONSTANTS TESTS ==============


class TestTemporalConstants:
    """Test temporal constants and helpers (Feature 2)."""

    def test_default_reference_date_is_valid_iso(self):
        """DEFAULT_REFERENCE_DATE is a valid ISO date string."""
        from datetime import datetime

        dt = datetime.strptime(DEFAULT_REFERENCE_DATE, "%Y-%m-%d")
        assert dt.year == 2024
        assert dt.month == 2
        assert dt.day == 6

    def test_prompt_template_has_reference_date_placeholder(self):
        """RAG_PROMPT_TEMPLATE contains the reference_date_formatted variable."""
        assert "{reference_date_formatted}" in RAG_PROMPT_TEMPLATE

    def test_prompt_template_has_temporal_instructions(self):
        """RAG_PROMPT_TEMPLATE contains temporal instructions for the LLM."""
        assert "Date du jour" in RAG_PROMPT_TEMPLATE
        assert "JAMAIS" in RAG_PROMPT_TEMPLATE
        assert "ce weekend" in RAG_PROMPT_TEMPLATE.lower()

    def test_prompt_template_has_context_and_question(self):
        """RAG_PROMPT_TEMPLATE still has context and question placeholders."""
        assert "{context}" in RAG_PROMPT_TEMPLATE
        assert "{question}" in RAG_PROMPT_TEMPLATE

    def test_format_date_french_standard(self):
        """_format_date_french formats dates correctly in French."""
        # 2024-02-06 is a Tuesday
        result = _format_date_french("2024-02-06")
        assert result == "mardi 6 février 2024"

    def test_format_date_french_weekend(self):
        """_format_date_french handles weekend days."""
        # 2024-02-10 is a Saturday
        result = _format_date_french("2024-02-10")
        assert result == "samedi 10 février 2024"

    def test_format_date_french_december(self):
        """_format_date_french handles December correctly."""
        result = _format_date_french("2024-12-25")
        assert result == "mercredi 25 décembre 2024"

    def test_format_date_french_invalid_returns_input(self):
        """_format_date_french returns input string for invalid dates."""
        result = _format_date_french("not-a-date")
        assert result == "not-a-date"


# ============== PAST EVENT FILTER TESTS ==============


class TestFilterPastEvents:
    """Test _filter_past_events() function (Feature 3)."""

    def _make_doc(self, content, end_date=None, start_date=None):
        """Helper to create a Document with date metadata."""
        metadata = {}
        if end_date is not None:
            metadata["event_end_date"] = end_date
        if start_date is not None:
            metadata["event_start_date"] = start_date
        return Document(page_content=content, metadata=metadata)

    def test_future_events_kept(self):
        """Events ending after reference_date are kept."""
        docs = [
            self._make_doc("Future event", end_date="2024-03-15"),
            self._make_doc("Another future", end_date="2024-06-01"),
        ]
        result = _filter_past_events(docs, "2024-02-06")
        assert len(result) == 2

    def test_past_events_removed(self):
        """Events ending before reference_date are removed."""
        docs = [
            self._make_doc("Past event", end_date="2024-01-15"),
            self._make_doc("Very past", end_date="2023-06-01"),
        ]
        result = _filter_past_events(docs, "2024-02-06")
        assert len(result) == 0

    def test_same_day_events_kept(self):
        """Events ending on reference_date are kept (end_date >= ref)."""
        docs = [self._make_doc("Today event", end_date="2024-02-06")]
        result = _filter_past_events(docs, "2024-02-06")
        assert len(result) == 1

    def test_mixed_past_and_future(self):
        """Mix of past and future events: only future kept."""
        docs = [
            self._make_doc("Past", end_date="2024-01-01"),
            self._make_doc("Future", end_date="2024-03-01"),
            self._make_doc("Past too", end_date="2023-12-31"),
            self._make_doc("Also future", end_date="2024-02-10"),
        ]
        result = _filter_past_events(docs, "2024-02-06")
        assert len(result) == 2
        assert result[0].page_content == "Future"
        assert result[1].page_content == "Also future"

    def test_none_end_date_kept(self):
        """Events with no end_date are kept (benefit of the doubt)."""
        docs = [self._make_doc("No date event")]
        result = _filter_past_events(docs, "2024-02-06")
        assert len(result) == 1

    def test_malformed_end_date_kept(self):
        """Events with malformed end_date are kept."""
        docs = [self._make_doc("Bad date event", end_date="not-a-date")]
        result = _filter_past_events(docs, "2024-02-06")
        assert len(result) == 1

    def test_empty_list_returns_empty(self):
        """Empty document list returns empty list."""
        result = _filter_past_events([], "2024-02-06")
        assert result == []

    def test_all_filtered_returns_empty(self):
        """If all events are past, returns empty list (graceful)."""
        docs = [
            self._make_doc("Old 1", end_date="2023-01-01"),
            self._make_doc("Old 2", end_date="2023-06-01"),
        ]
        result = _filter_past_events(docs, "2024-02-06")
        assert len(result) == 0


# ============== QUERY ANALYSIS TESTS (Feature 4) ==============


class TestQueryAnalysisPrompt:
    """Test QUERY_ANALYSIS_PROMPT constant (Feature 4)."""

    def test_prompt_has_reference_date_placeholder(self):
        """Prompt contains {reference_date} for injection."""
        assert "{reference_date}" in QUERY_ANALYSIS_PROMPT

    def test_prompt_has_question_placeholder(self):
        """Prompt contains {question} for injection."""
        assert "{question}" in QUERY_ANALYSIS_PROMPT

    def test_prompt_requests_json_with_required_fields(self):
        """Prompt instructs LLM to return JSON with is_relevant and temporal_window."""
        assert "is_relevant" in QUERY_ANALYSIS_PROMPT
        assert "temporal_window" in QUERY_ANALYSIS_PROMPT
        assert "start_date" in QUERY_ANALYSIS_PROMPT
        assert "end_date" in QUERY_ANALYSIS_PROMPT

    def test_prompt_has_examples(self):
        """Prompt contains at least one example to guide the LLM."""
        assert "ce weekend" in QUERY_ANALYSIS_PROMPT.lower()


class TestParseQueryAnalysis:
    """Test _parse_query_analysis_response() helper (Feature 4)."""

    def test_valid_json_parsed(self):
        """Valid JSON with all fields is parsed correctly."""
        text = '{"is_relevant": true, "temporal_window": {"start_date": "2024-02-10", "end_date": "2024-02-11"}, "reasoning": "ce weekend"}'
        result = _parse_query_analysis_response(text)
        assert result["is_relevant"] is True
        assert result["temporal_window"]["start_date"] == "2024-02-10"
        assert result["temporal_window"]["end_date"] == "2024-02-11"
        assert result["reasoning"] == "ce weekend"

    def test_json_in_markdown_code_block(self):
        """JSON wrapped in markdown code block is extracted."""
        text = '```json\n{"is_relevant": true, "temporal_window": null, "reasoning": "no temporal"}\n```'
        result = _parse_query_analysis_response(text)
        assert result["is_relevant"] is True
        assert result["temporal_window"] is None

    def test_off_topic_parsed(self):
        """Off-topic response (is_relevant=false) is parsed correctly."""
        text = '{"is_relevant": false, "temporal_window": null, "reasoning": "restaurants"}'
        result = _parse_query_analysis_response(text)
        assert result["is_relevant"] is False
        assert result["temporal_window"] is None

    def test_invalid_json_returns_default(self):
        """Invalid JSON returns safe default (is_relevant=True)."""
        result = _parse_query_analysis_response("This is not JSON at all")
        assert result["is_relevant"] is True
        assert result["temporal_window"] is None

    def test_empty_string_returns_default(self):
        """Empty string returns safe default."""
        result = _parse_query_analysis_response("")
        assert result["is_relevant"] is True
        assert result["temporal_window"] is None


# ============== TEMPORAL WINDOW FILTER TESTS (Feature 4) ==============


class TestFilterTemporalWindow:
    """Test _filter_temporal_window() function (Feature 4)."""

    def _make_doc(self, content, start_date=None, end_date=None):
        """Helper to create a Document with date metadata."""
        metadata = {}
        if start_date is not None:
            metadata["event_start_date"] = start_date
        if end_date is not None:
            metadata["event_end_date"] = end_date
        return Document(page_content=content, metadata=metadata)

    def test_events_inside_window_kept(self):
        """Events fully inside the temporal window are kept."""
        docs = [
            self._make_doc("Concert", start_date="2024-02-10", end_date="2024-02-10"),
            self._make_doc("Expo", start_date="2024-02-11", end_date="2024-02-11"),
        ]
        window = {"start_date": "2024-02-10", "end_date": "2024-02-11"}
        result = _filter_temporal_window(docs, window)
        assert len(result) == 2

    def test_events_before_window_removed(self):
        """Events ending before the window start are removed (when other matches exist)."""
        docs = [
            self._make_doc("Old event", start_date="2024-02-01", end_date="2024-02-05"),
            self._make_doc("Current event", start_date="2024-02-10", end_date="2024-02-10"),
        ]
        window = {"start_date": "2024-02-10", "end_date": "2024-02-11"}
        result = _filter_temporal_window(docs, window)
        assert len(result) == 1
        assert result[0].page_content == "Current event"

    def test_events_after_window_removed(self):
        """Events starting after the window end are removed (when other matches exist)."""
        docs = [
            self._make_doc("Future event", start_date="2024-03-01", end_date="2024-03-05"),
            self._make_doc("Current event", start_date="2024-02-11", end_date="2024-02-11"),
        ]
        window = {"start_date": "2024-02-10", "end_date": "2024-02-11"}
        result = _filter_temporal_window(docs, window)
        assert len(result) == 1
        assert result[0].page_content == "Current event"

    def test_multiday_event_overlapping_window_kept(self):
        """Multi-day event overlapping the window is kept."""
        docs = [
            self._make_doc("Festival", start_date="2024-02-08", end_date="2024-02-12"),
        ]
        window = {"start_date": "2024-02-10", "end_date": "2024-02-11"}
        result = _filter_temporal_window(docs, window)
        assert len(result) == 1

    def test_events_with_no_dates_kept(self):
        """Events with missing dates are kept (benefit of the doubt)."""
        docs = [self._make_doc("Unknown date event")]
        window = {"start_date": "2024-02-10", "end_date": "2024-02-11"}
        result = _filter_temporal_window(docs, window)
        assert len(result) == 1

    def test_events_with_malformed_dates_kept(self):
        """Events with malformed dates are kept."""
        docs = [self._make_doc("Bad date", start_date="not-a-date", end_date="bad")]
        window = {"start_date": "2024-02-10", "end_date": "2024-02-11"}
        result = _filter_temporal_window(docs, window)
        assert len(result) == 1

    def test_empty_result_safeguard(self):
        """If all events would be filtered, return original list (safeguard)."""
        docs = [
            self._make_doc("Before", start_date="2024-01-01", end_date="2024-01-05"),
            self._make_doc("After", start_date="2024-06-01", end_date="2024-06-05"),
        ]
        window = {"start_date": "2024-02-10", "end_date": "2024-02-11"}
        result = _filter_temporal_window(docs, window)
        assert len(result) == 2  # all returned, safeguard activated

    def test_empty_list_returns_empty(self):
        """Empty document list returns empty list."""
        result = _filter_temporal_window([], {"start_date": "2024-02-10", "end_date": "2024-02-11"})
        assert result == []

    def test_window_with_only_start_date(self):
        """Window with only start_date filters events before it."""
        docs = [
            self._make_doc("Before", start_date="2024-01-01", end_date="2024-01-05"),
            self._make_doc("After", start_date="2024-03-01", end_date="2024-03-05"),
        ]
        window = {"start_date": "2024-02-01", "end_date": None}
        result = _filter_temporal_window(docs, window)
        assert len(result) == 1
        assert result[0].page_content == "After"

    def test_null_window_returns_all(self):
        """Window with both null dates returns all documents."""
        docs = [
            self._make_doc("Event 1", start_date="2024-01-01", end_date="2024-01-05"),
            self._make_doc("Event 2", start_date="2024-06-01", end_date="2024-06-05"),
        ]
        window = {"start_date": None, "end_date": None}
        result = _filter_temporal_window(docs, window)
        assert len(result) == 2


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
