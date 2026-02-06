"""
RAG Service - Singleton service for managing the RAG system.

This service loads and manages the FAISS index, retrievers, and LLM,
providing a clean interface for the API endpoints.
"""

import json
import logging
import os
import re
import time
import tempfile
import shutil
import requests
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from urllib.parse import urlencode

from bs4 import BeautifulSoup
from dotenv import load_dotenv

from langchain_core.documents import Document
from langchain_mistralai import MistralAIEmbeddings, ChatMistralAI
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever
from langchain_community.document_compressors import FlashrankRerank
from langchain_classic.retrievers import EnsembleRetriever, ContextualCompressionRetriever

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Default reference date for temporal queries.
# The OpenAgenda dataset peaks in 2024 (47% of events). This date places
# the user in the densest data period for meaningful temporal queries.
DEFAULT_REFERENCE_DATE = os.getenv("DEFAULT_REFERENCE_DATE", "2024-05-16")

# RAG prompt template with temporal awareness
RAG_PROMPT_TEMPLATE = """Tu es un assistant spécialisé dans les événements culturels de Savoie (73), Haute-Savoie (74) et Isère (38).

Date du jour : {reference_date_formatted}

Instructions temporelles :
- Ne recommande JAMAIS d'événements dont la date est passée par rapport à la date du jour.
- Si l'utilisateur demande "ce weekend", il s'agit du samedi et dimanche les plus proches après la date du jour.
- Trie les événements par date, les plus proches en premier.
- Si tous les événements du contexte sont passés, indique-le clairement.

Utilise les informations suivantes pour répondre à la question de l'utilisateur.
Si tu ne trouves pas l'information dans le contexte, dis-le clairement.

Contexte :
{context}

Question : {question}

Réponse détaillée :"""

# Query analysis prompt for advanced method (Feature 4).
# Extends the existing off-topic detection with temporal window extraction.
# Single LLM call — no additional latency cost for the advanced method.
QUERY_ANALYSIS_PROMPT = """Analyse cette question sur les événements culturels.
Date du jour : {reference_date}

Réponds en JSON strict :
{{
  "is_relevant": true/false,
  "temporal_window": {{
    "start_date": "YYYY-MM-DD" ou null,
    "end_date": "YYYY-MM-DD" ou null
  }},
  "reasoning": "explication courte"
}}

Exemples :
- "Concerts ce weekend" (ref: 2024-05-16) → {{"is_relevant": true, "temporal_window": {{"start_date": "2024-05-18", "end_date": "2024-05-19"}}, "reasoning": "ce weekend = samedi-dimanche suivants"}}
- "Ce soir ou demain à Annecy" (ref: 2024-05-16) → {{"is_relevant": true, "temporal_window": {{"start_date": "2024-05-16", "end_date": "2024-05-17"}}, "reasoning": "ce soir + demain = aujourd'hui et lendemain"}}
- "Festivals cet été" (ref: 2024-05-16) → {{"is_relevant": true, "temporal_window": {{"start_date": "2024-06-01", "end_date": "2024-08-31"}}, "reasoning": "été = juin à août"}}
- "Quels sont les meilleurs restaurants?" → {{"is_relevant": false, "temporal_window": null, "reasoning": "pas lié aux événements culturels"}}
- "Que faire à Annecy?" → {{"is_relevant": true, "temporal_window": null, "reasoning": "pas de contrainte temporelle explicite"}}

Question : {question}
"""


def _format_date_french(iso_date: str) -> str:
    """Format an ISO date string as a French date.

    Example: "2024-05-16" → "jeudi 16 mai 2024"
    """
    DAYS_FR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
    MONTHS_FR = [
        "", "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre",
    ]
    try:
        dt = datetime.strptime(iso_date, "%Y-%m-%d")
        day_name = DAYS_FR[dt.weekday()]
        return f"{day_name} {dt.day} {MONTHS_FR[dt.month]} {dt.year}"
    except (ValueError, IndexError):
        return iso_date


def _clean_html(html_text: str) -> str:
    """Remove HTML tags from text."""
    if not html_text:
        return ""
    soup = BeautifulSoup(html_text, "lxml")
    return soup.get_text(separator=" ", strip=True)


def _build_document_text(event: dict) -> str:
    """Build comprehensive document text from event data."""
    parts = []

    title = event.get("title_fr", "")
    if title:
        parts.append(f"Événement: {title}")

    long_desc = _clean_html(event.get("longdescription_fr", ""))
    short_desc = event.get("description_fr", "")
    description = long_desc if long_desc else short_desc
    if description:
        parts.append(f"Description: {description}")

    city = event.get("location_city", "")
    location_name = event.get("location_name", "")
    address = event.get("location_address", "")
    department = event.get("location_department", "")

    location_parts = []
    if location_name:
        location_parts.append(location_name)
    if address:
        location_parts.append(address)
    if city:
        location_parts.append(city)
    if department:
        location_parts.append(department)

    if location_parts:
        parts.append(f"Lieu: {', '.join(location_parts)}")

    daterange = event.get("daterange_fr", "")
    if daterange:
        parts.append(f"Date: {daterange}")

    category = event.get("category", "")
    if category:
        parts.append(f"Catégorie: {category}")

    keywords = event.get("keywords_fr", [])
    if keywords:
        parts.append(f"Mots-clés: {', '.join(keywords[:10])}")

    return "\n".join(parts)


def _build_metadata(event: dict) -> dict:
    """Extract metadata from event, including ISO date fields.

    Parses firstdate_begin and lastdate_end into structured date fields
    for temporal filtering. Falls back to None for missing/malformed dates.
    """
    logger = logging.getLogger(__name__)

    metadata = {
        "uid": event.get("uid", ""),
        "title": event.get("title_fr", ""),
        "city": event.get("location_city", ""),
        "department": event.get("location_department", ""),
        "daterange": event.get("daterange_fr", ""),
        "category": event.get("category", ""),
        "url": event.get("canonicalurl", ""),
        "event_start_date": None,
        "event_end_date": None,
        "event_year": None,
        "event_month": None,
    }

    firstdate = event.get("firstdate_begin")
    if firstdate:
        try:
            dt = datetime.fromisoformat(firstdate.replace("Z", "+00:00"))
            metadata["event_start_date"] = dt.strftime("%Y-%m-%d")
            metadata["event_year"] = dt.year
            metadata["event_month"] = dt.month
        except (ValueError, AttributeError):
            logger.warning("Failed to parse start date '%s' for event '%s'",
                           firstdate, event.get("uid", "unknown"))

    lastdate = event.get("lastdate_end")
    if lastdate:
        try:
            dt = datetime.fromisoformat(lastdate.replace("Z", "+00:00"))
            metadata["event_end_date"] = dt.strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            logger.warning("Failed to parse end date '%s' for event '%s'",
                           lastdate, event.get("uid", "unknown"))

    return metadata


def _filter_past_events(
    documents: List[Document], reference_date: str
) -> List[Document]:
    """Remove events that ended before the reference date.

    Design choice: This system recommends upcoming/current events only.
    Past events are excluded to provide actionable recommendations.
    Events with missing or unparseable dates are kept (benefit of the doubt).

    Args:
        documents: List of retrieved documents
        reference_date: ISO YYYY-MM-DD date string

    Returns:
        Filtered list with only current/future events
    """
    ref = datetime.strptime(reference_date, "%Y-%m-%d").date()
    filtered = []
    for doc in documents:
        end_date_str = doc.metadata.get("event_end_date")
        if end_date_str is None:
            filtered.append(doc)
            continue
        try:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            if end_date >= ref:
                filtered.append(doc)
        except ValueError:
            filtered.append(doc)
    return filtered


def _parse_query_analysis_response(text: str) -> dict:
    """Parse LLM response from query analysis into structured dict.

    Handles JSON potentially wrapped in markdown code blocks.
    Returns a safe default (is_relevant=True) on parse failure to avoid
    false negatives — better to attempt retrieval than to reject a valid query.
    """
    try:
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return {
                "is_relevant": result.get("is_relevant", True),
                "temporal_window": result.get("temporal_window"),
                "reasoning": result.get("reasoning", ""),
            }
    except (json.JSONDecodeError, AttributeError):
        pass
    return {"is_relevant": True, "temporal_window": None, "reasoning": "parse_error"}


def _filter_temporal_window(
    documents: List[Document], temporal_window: dict
) -> List[Document]:
    """Keep events overlapping with the LLM-extracted temporal window.

    Unlike _filter_past_events (hard filter), this is a best-effort filter:
    - Events overlapping the window are kept
    - Events with missing dates are kept (benefit of the doubt)
    - If filtering would empty the list, return original (never return nothing)

    Args:
        documents: List of retrieved documents
        temporal_window: Dict with "start_date" and/or "end_date" (ISO YYYY-MM-DD or None)

    Returns:
        Filtered list, or original list if filtering would empty it
    """
    if not documents:
        return documents

    start = temporal_window.get("start_date")
    end = temporal_window.get("end_date")

    if not start and not end:
        return documents

    try:
        window_start = datetime.strptime(start, "%Y-%m-%d").date() if start else None
        window_end = datetime.strptime(end, "%Y-%m-%d").date() if end else None
    except ValueError:
        return documents  # Invalid window dates, skip filtering

    filtered = []
    for doc in documents:
        event_start_str = doc.metadata.get("event_start_date")
        event_end_str = doc.metadata.get("event_end_date")

        if event_start_str is None and event_end_str is None:
            filtered.append(doc)
            continue

        try:
            ev_start = (
                datetime.strptime(event_start_str, "%Y-%m-%d").date()
                if event_start_str
                else None
            )
            ev_end = (
                datetime.strptime(event_end_str, "%Y-%m-%d").date()
                if event_end_str
                else None
            )
        except ValueError:
            filtered.append(doc)  # keep events with unparseable dates
            continue

        # Check overlap: event overlaps window if
        # event_start <= window_end AND event_end >= window_start
        # Handle None values generously (assume overlap when unknown)
        overlaps = True
        if window_end and ev_start:
            if ev_start > window_end:
                overlaps = False
        if window_start and ev_end:
            if ev_end < window_start:
                overlaps = False

        if overlaps:
            filtered.append(doc)

    # Safeguard: if filtering removed everything, return original
    if not filtered and documents:
        return documents

    return filtered


def _temporal_rerank(
    documents: List[Document],
    target_date: str,
    half_life_days: int = 14,
) -> List[Document]:
    """Rerank documents by temporal proximity to a target date.

    Uses exponential decay: events further from target_date are pushed down.
    Score formula: temporal_score = 0.5 ^ (|event_start_date - target_date| / half_life_days)

    Events with missing or malformed dates get score 0 and are placed at the end,
    preserving their relative order.

    Args:
        documents: List of retrieved documents
        target_date: ISO YYYY-MM-DD date to rank proximity against
        half_life_days: Events this many days away score 50%. Default 14.

    Returns:
        Documents sorted by temporal proximity (closest first)
    """
    if not documents:
        return documents

    target = datetime.strptime(target_date, "%Y-%m-%d").date()

    scored = []
    for i, doc in enumerate(documents):
        start_str = doc.metadata.get("event_start_date")
        if start_str:
            try:
                start = datetime.strptime(start_str, "%Y-%m-%d").date()
                days_away = abs((start - target).days)
                score = 0.5 ** (days_away / half_life_days)
            except ValueError:
                score = 0.0
        else:
            score = 0.0
        # Use (score, -i) so that ties preserve original order (stable sort)
        scored.append((score, i, doc))

    # Sort by score descending, then by original index ascending (stable)
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [doc for _, _, doc in scored]


class RAGService:
    """
    Singleton service for RAG operations.

    Manages FAISS index, retrievers, and LLM for the API.
    """

    # Target geographic departments for event filtering
    TARGET_DEPARTMENTS = ["Savoie", "Haute-Savoie", "Isère"]

    # Download timeout configuration (seconds)
    CONNECT_TIMEOUT = 10  # Max time to establish connection
    READ_TIMEOUT = 60  # Max silence between chunks

    _instance = None

    def __new__(cls):
        """Singleton pattern - only one instance exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize RAG service (called only once)."""
        if self._initialized:
            return

        # Mark as initialized immediately to prevent repeated init attempts on failure.
        # This ensures we only try once - subsequent calls will return early.
        self._initialized = True

        logger.info("Initializing RAG Service...")

        # Service state
        self._index_loaded = False
        self._llm_available = False
        self._advanced_uses_fallback = False  # Track if advanced method fell back to hybrid

        # Components (will be loaded on first use or explicitly)
        self.vectorstore = None
        self.embeddings = None
        self.llm = None
        self.documents = []  # Needed for BM25
        self._bm25_retriever = None
        self._flashrank_compressor = None
        self._available_methods = []
        self.index_metadata = {}

        # Configuration
        self.project_root = Path(__file__).parent.parent.parent
        self.index_path = self.project_root / "data" / "index" / "faiss_baseline"
        self.data_path = self.project_root / "data" / "processed" / "events_filtered.json"
        self.embedding_model = "mistral-embed"
        self.llm_model = "mistral-small-latest"

        # Try to load components
        try:
            self._load_components()

            # Auto-rebuild if index not found but LLM is available
            if not self._index_loaded and self._llm_available:
                auto_rebuild = os.getenv("AUTO_REBUILD_INDEX", "true").lower() == "true"
                if auto_rebuild:
                    logger.info("Index not found - triggering auto-rebuild...")
                    try:
                        result = self.rebuild_index(force=True, download_fresh_data=True)
                        if result.get("status") == "success":
                            logger.info(
                                f"Auto-rebuild complete: {result.get('events_indexed')} events indexed"
                            )
                        else:
                            logger.warning(f"Auto-rebuild returned: {result.get('status')}")
                    except Exception as rebuild_error:
                        logger.error(f"Auto-rebuild failed: {rebuild_error}")
                        logger.warning(
                            "Service will start in degraded mode - call POST /rebuild manually"
                        )
                else:
                    logger.info("Auto-rebuild disabled (AUTO_REBUILD_INDEX=false)")

            logger.info("RAG Service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize RAG Service: {e}")

    def _load_events_as_documents(self) -> List[Document]:
        """Load events JSON and convert to LangChain Documents."""
        if not self.data_path.exists():
            logger.warning(f"Data file not found: {self.data_path}")
            return []

        logger.info(f"Loading events from {self.data_path}...")
        with open(self.data_path, "r", encoding="utf-8") as f:
            events = json.load(f)

        documents = []
        for event in events:
            text = _build_document_text(event)
            metadata = _build_metadata(event)
            if text.strip():
                documents.append(Document(page_content=text, metadata=metadata))

        logger.info(f"  Loaded {len(documents):,} documents")
        return documents

    def _load_components(self):
        """Load RAG components (index, LLM, embeddings)."""
        # Check if Mistral API key is configured
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            logger.warning("MISTRAL_API_KEY not set - LLM will not be available")
            self._llm_available = False
            return

        try:
            # Initialize embeddings
            self.embeddings = MistralAIEmbeddings(model=self.embedding_model, api_key=api_key)

            # Initialize LLM
            self.llm = ChatMistralAI(model=self.llm_model, api_key=api_key, temperature=0.1)
            self._llm_available = True

            # Load documents (needed for BM25)
            self.documents = self._load_events_as_documents()

            # Load FAISS index (check for actual index file, not just directory)
            index_file = self.index_path / "index.faiss"
            if index_file.exists():
                logger.info(f"Loading FAISS index from {self.index_path}")
                # NOTE: allow_dangerous_deserialization=True is required by LangChain's FAISS
                # wrapper because it uses pickle for the docstore. This is safe in our context:
                # - We control the index source (built from our own data pipeline)
                # - No untrusted external indices are loaded
                # - The index path is hardcoded, not user-controllable
                # For production with untrusted indices, consider index signature verification.
                self.vectorstore = FAISS.load_local(
                    str(self.index_path), self.embeddings, allow_dangerous_deserialization=True
                )
                self._index_loaded = True
                self.index_metadata["last_updated"] = (
                    datetime.fromtimestamp(self.index_path.stat().st_mtime).isoformat() + "Z"
                )
                logger.info(f"  Index loaded with {self.vectorstore.index.ntotal} vectors")
            else:
                logger.warning(f"FAISS index not found at {index_file}")
                self._index_loaded = False

            # Setup retrievers if index is loaded
            if self._index_loaded and self.documents:
                self._setup_retrievers()

        except Exception as e:
            logger.error(f"Error loading RAG components: {e}")
            self._llm_available = False
            self._index_loaded = False
            raise

    def _setup_retrievers(self):
        """Set up retriever components for all three RAG methods.

        Unlike the previous RetrievalQA chain approach, retrievers are stored
        as components and assembled per-request in _retrieve(). This allows
        dynamic top_k and per-request reference_date injection.
        """
        if not self.vectorstore or not self.llm:
            return

        # BM25 retriever for hybrid and advanced methods
        logger.info("Setting up BM25 retriever...")
        self._bm25_retriever = BM25Retriever.from_documents(self.documents)

        # FlashRank reranker for advanced method
        logger.info("Setting up FlashRank reranker...")
        try:
            self._flashrank_compressor = FlashrankRerank(top_n=200)
            logger.info("  FlashRank reranker ready")
        except Exception as e:
            logger.warning(
                f"FlashrankRerank unavailable ({e}), 'advanced' method will use hybrid retrieval. "
                "Install flashrank package for reranking support."
            )
            self._flashrank_compressor = None
            self._advanced_uses_fallback = True

        self._available_methods = ["basic", "hybrid", "advanced"]
        logger.info("All retrievers ready")

    def _retrieve(self, question: str, method: str, fetch_k: int) -> List[Document]:
        """Retrieve documents using the specified method.

        Args:
            question: User query
            method: "basic", "hybrid", or "advanced"
            fetch_k: Number of candidates to retrieve (before filtering)

        Returns:
            List of retrieved documents
        """
        if method == "basic":
            return self.vectorstore.similarity_search(question, k=fetch_k)

        # Hybrid and Advanced both start with FAISS + BM25 ensemble
        faiss_retriever = self.vectorstore.as_retriever(search_kwargs={"k": fetch_k})
        self._bm25_retriever.k = fetch_k
        ensemble = EnsembleRetriever(
            retrievers=[faiss_retriever, self._bm25_retriever], weights=[0.5, 0.5]
        )

        if method == "advanced" and self._flashrank_compressor is not None:
            compression_retriever = ContextualCompressionRetriever(
                base_compressor=self._flashrank_compressor,
                base_retriever=ensemble,
            )
            return compression_retriever.invoke(question)

        return ensemble.invoke(question)

    def _analyze_query(self, question: str, reference_date: str) -> dict:
        """Analyze query for relevance and temporal intent (advanced method only).

        Calls the LLM once with QUERY_ANALYSIS_PROMPT to extract:
        - is_relevant: whether the query is about cultural events
        - temporal_window: extracted date range (if any temporal expression detected)
        - reasoning: short explanation of the analysis

        Returns safe defaults on parse failure (is_relevant=True, no temporal window).
        """
        prompt = QUERY_ANALYSIS_PROMPT.format(
            reference_date=reference_date,
            question=question,
        )
        response = self.llm.invoke(prompt)
        text = response.content if hasattr(response, "content") else str(response)
        return _parse_query_analysis_response(text)

    def is_ready(self) -> bool:
        """Check if service is ready to handle requests."""
        return self._initialized and self._index_loaded

    def is_initialized(self) -> bool:
        """Check if service has been initialized (attempted setup).

        Note: This is different from is_ready() - initialization may have
        failed but we still consider it "initialized" to prevent retry loops.
        """
        return self._initialized

    def is_llm_available(self) -> bool:
        """Check if LLM is available."""
        return self._llm_available

    def get_index_size(self) -> Optional[int]:
        """Get number of documents in index."""
        if not self._index_loaded or not self.vectorstore:
            return None
        return self.vectorstore.index.ntotal

    def _download_openagenda_data(self, output_path: Path) -> int:
        """
        Download filtered events data from OpenDataSoft API.

        Uses API-level filtering to download only events from target departments
        (Savoie, Haute-Savoie, Isère), significantly reducing download size and time.

        Performance comparison:
        - Full export: ~4GB, 5+ minutes (times out)
        - Filtered export: ~72MB, ~11 seconds

        Args:
            output_path: Where to save the downloaded JSON

        Returns:
            Number of events downloaded

        Raises:
            RuntimeError: If download fails or response is not valid JSON
        """
        # Build API URL with department filter
        # OpenDataSoft API v2.1 supports 'where' clause for server-side filtering
        # Format: where=location_department in ("Savoie","Haute-Savoie","Isère")
        base_url = "https://public.opendatasoft.com/api/explore/v2.1/catalog/datasets/evenements-publics-openagenda/exports/json"
        dept_filter = ",".join([f'"{dept}"' for dept in self.TARGET_DEPARTMENTS])
        where_clause = f"location_department in ({dept_filter})"

        # Use urlencode for proper URL parameter encoding
        params = {"where": where_clause}

        logger.info(f"Downloading filtered data from OpenDataSoft...")
        logger.info(f"  Target departments: {', '.join(self.TARGET_DEPARTMENTS)}")
        logger.info(f"  Filter: {where_clause}")

        try:
            # Download with streaming to handle large files
            # Timeout: (connect_timeout, read_timeout)
            # - CONNECT_TIMEOUT: Max time to establish connection
            # - READ_TIMEOUT: Max silence between chunks (server stall protection)
            response = requests.get(
                base_url,
                params=params,
                stream=True,
                timeout=(self.CONNECT_TIMEOUT, self.READ_TIMEOUT),
            )
            response.raise_for_status()

            # Save to temporary file first (atomic write)
            with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".json") as tmp_file:
                tmp_path = Path(tmp_file.name)
                total_size = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        tmp_file.write(chunk)
                        total_size += len(chunk)

            logger.info(f"  Downloaded {total_size / 1024 / 1024:.2f} MB")

            # Move to final location
            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(tmp_path), str(output_path))

            # Count events
            with open(output_path, "r", encoding="utf-8") as f:
                events = json.load(f)
                event_count = len(events) if isinstance(events, list) else 0

            logger.info(
                f"  Downloaded {event_count:,} events (filtered by department at API level)"
            )
            return event_count

        except requests.exceptions.Timeout as e:
            logger.error(
                f"Download timeout after {self.CONNECT_TIMEOUT}s connect / {self.READ_TIMEOUT}s read: {e}"
            )
            raise RuntimeError(
                f"Download timed out. The API may be slow or unavailable. Try again later."
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download data: {e}")
            raise RuntimeError(f"Failed to download data from OpenDataSoft: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            raise RuntimeError(f"Downloaded data is not valid JSON: {e}")

    def _filter_events(self, raw_data_path: Path) -> List[Dict]:
        """
        Filter events to keep only recent dates.

        Note: Department filtering (Savoie, Haute-Savoie, Isère) is now done
        at the API level during download to reduce data transfer and processing.
        This method only performs date filtering.

        Args:
            raw_data_path: Path to raw events JSON (already filtered by department)

        Returns:
            List of filtered event dictionaries
        """
        min_date = datetime(2023, 1, 1)

        logger.info("Filtering events by date...")
        logger.info(f"  Minimum date: {min_date.strftime('%Y-%m-%d')}")

        with open(raw_data_path, "r", encoding="utf-8") as f:
            events = json.load(f)

        filtered_events = []
        for event in events:
            # Check date
            firstdate = event.get("firstdate_begin")
            if not firstdate:
                continue

            try:
                event_date = datetime.fromisoformat(firstdate.replace("Z", "+00:00")).replace(
                    tzinfo=None
                )
                if event_date < min_date:
                    continue
            except (ValueError, AttributeError):
                continue

            filtered_events.append(event)

        logger.info(f"  Kept {len(filtered_events):,} events out of {len(events):,}")
        logger.info(
            f"  Filtered out {len(events) - len(filtered_events):,} events before {min_date.strftime('%Y-%m-%d')}"
        )
        return filtered_events

    def query(
        self,
        question: str,
        method: str = "hybrid",
        top_k: int = 5,
        reference_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Query the RAG system using a manual retrieve-then-generate pipeline.

        Pipeline steps (basic/hybrid):
        1. Retrieve candidates (fetch_k = top_k * 10 for filtering headroom)
        2. Filter past events (event_end_date < reference_date)
        3. Temporal proximity reranking (closest to reference_date first)
        4. Slice to top_k
        5. Build prompt with reference_date + context + question
        6. Generate answer via LLM

        Pipeline steps (advanced):
        1. Query Analysis: off-topic detection + temporal window extraction
        2. If off-topic → return off-topic response
        3-4. Same as basic/hybrid
        5. Apply temporal window filter (if extracted)
        6. Temporal reranking (proximity to window start or reference_date)

        Args:
            question: User question
            method: RAG method ("basic", "hybrid", or "advanced")
            top_k: Number of documents the LLM sees and returns as sources
            reference_date: ISO date (YYYY-MM-DD) used as "today" for temporal queries.
                           Defaults to DEFAULT_REFERENCE_DATE.

        Returns:
            Dictionary with answer, sources, and metadata
        """
        if not self.is_ready():
            raise RuntimeError("RAG service not ready - index not loaded")

        if method not in self._available_methods:
            raise ValueError(
                f"Unknown RAG method: {method}. Available: {self._available_methods}"
            )

        ref_date = reference_date or DEFAULT_REFERENCE_DATE
        start_time = time.time()

        try:
            # Advanced method: Enhanced Query Analysis (Feature 4)
            analysis = None
            if method == "advanced":
                analysis = self._analyze_query(question, ref_date)

                if not analysis.get("is_relevant", True):
                    response_time_ms = int((time.time() - start_time) * 1000)
                    return {
                        "answer": (
                            "Je suis spécialisé dans les événements culturels "
                            "de Savoie, Haute-Savoie et Isère. "
                            "Votre question ne semble pas porter sur ce sujet. "
                            "N'hésitez pas à me poser une question sur les "
                            "événements de la région !"
                        ),
                        "sources": [],
                        "metadata": {
                            "rag_method": method,
                            "response_time_ms": response_time_ms,
                            "retrieved_docs_count": 0,
                            "timestamp": datetime.utcnow().isoformat() + "Z",
                            "model_version": self.llm_model,
                            "reference_date": ref_date,
                            "query_analysis": analysis,
                        },
                    }

            # 1. Retrieve candidates with generous fetch_k
            fetch_k = top_k * 10
            docs = self._retrieve(question, method, fetch_k=fetch_k)

            # 2. Filter past events
            docs = _filter_past_events(docs, ref_date)

            # 3. Apply temporal window filter (advanced only, Feature 4)
            temporal_window = None
            if analysis and analysis.get("temporal_window"):
                temporal_window = analysis["temporal_window"]
                if temporal_window.get("start_date") or temporal_window.get("end_date"):
                    docs = _filter_temporal_window(docs, temporal_window)

            # 4. Temporal proximity reranking (Feature 5)
            # Advanced: rank by proximity to temporal window start (if extracted)
            # Basic/Hybrid: rank by proximity to reference_date
            rerank_target = ref_date
            if temporal_window and temporal_window.get("start_date"):
                rerank_target = temporal_window["start_date"]
            docs = _temporal_rerank(docs, target_date=rerank_target)

            # 5. Slice to top_k
            docs = docs[:top_k]

            # 6. Build prompt with per-request reference_date
            context = "\n\n".join(doc.page_content for doc in docs)
            prompt_text = RAG_PROMPT_TEMPLATE.format(
                reference_date_formatted=_format_date_french(ref_date),
                context=context if context else "Aucun événement trouvé.",
                question=question,
            )

            # 6. Generate answer
            response = self.llm.invoke(prompt_text)
            answer = response.content if hasattr(response, "content") else str(response)

            # Format sources for response
            sources = []
            for doc in docs:
                source = {
                    "title": doc.metadata.get("title", "Unknown"),
                    "location": doc.metadata.get("city", None),
                    "date_start": doc.metadata.get("event_start_date")
                    or doc.metadata.get("daterange", None),
                    "description_snippet": (
                        doc.page_content[:200] + "..."
                        if len(doc.page_content) > 200
                        else doc.page_content
                    ),
                    "relevance_score": None,
                }
                sources.append(source)

            response_time_ms = int((time.time() - start_time) * 1000)

            metadata = {
                "rag_method": method,
                "response_time_ms": response_time_ms,
                "retrieved_docs_count": len(sources),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "model_version": self.llm_model,
                "reference_date": ref_date,
            }
            if analysis:
                metadata["query_analysis"] = analysis

            return {
                "answer": answer,
                "sources": sources,
                "metadata": metadata,
            }

        except Exception as e:
            logger.error(f"Error during RAG query: {e}")
            raise

    def rebuild_index(
        self, force: bool = False, download_fresh_data: bool = True
    ) -> Dict[str, Any]:
        """
        Rebuild the FAISS index.

        Args:
            force: Force rebuild even if recent
            download_fresh_data: Download fresh data before rebuilding

        Returns:
            Dictionary with rebuild statistics
        """
        start_time = time.time()

        try:
            # Check if index is recent and force=False
            if not force and self.index_path.exists():
                index_age_hours = (time.time() - self.index_path.stat().st_mtime) / 3600
                if index_age_hours < 24:
                    logger.info(f"Index is recent ({index_age_hours:.1f}h old), skipping rebuild")
                    return {
                        "status": "skipped",
                        "message": f"Index is recent ({index_age_hours:.1f}h old). Use force=true to rebuild anyway.",
                        "events_indexed": None,
                        "build_time_seconds": time.time() - start_time,
                        "index_path": str(self.index_path),
                    }

            logger.info("Starting index rebuild...")

            # Step 1: Get data
            raw_data_path = (
                self.project_root / "data" / "raw" / "evenements-publics-openagenda.json"
            )

            if download_fresh_data:
                logger.info("Step 1/4: Downloading fresh data...")
                total_events = self._download_openagenda_data(raw_data_path)
            else:
                if not raw_data_path.exists():
                    raise FileNotFoundError(
                        f"Raw data not found at {raw_data_path}. Set download_fresh_data=true."
                    )
                logger.info(f"Step 1/4: Using existing data at {raw_data_path}")

            # Step 2: Filter events
            logger.info("Step 2/4: Filtering events...")
            filtered_events = self._filter_events(raw_data_path)

            # Save filtered data
            filtered_data_path = self.data_path
            filtered_data_path.parent.mkdir(parents=True, exist_ok=True)
            with open(filtered_data_path, "w", encoding="utf-8") as f:
                json.dump(filtered_events, f, ensure_ascii=False, indent=2)
            logger.info(f"  Saved to {filtered_data_path}")

            # Step 3: Convert to Documents
            logger.info("Step 3/4: Converting to LangChain Documents...")
            documents = []
            for event in filtered_events:
                text = _build_document_text(event)
                metadata = _build_metadata(event)
                if text.strip():
                    documents.append(Document(page_content=text, metadata=metadata))

            logger.info(f"  Created {len(documents):,} documents")

            # Step 4: Build new FAISS index
            logger.info("Step 4/4: Building FAISS index...")

            if not self.embeddings:
                raise RuntimeError("Embeddings not initialized. Cannot rebuild index.")

            new_vectorstore = FAISS.from_documents(documents, self.embeddings)

            # Save new index
            temp_index_path = self.index_path.parent / f"{self.index_path.name}_temp"
            temp_index_path.mkdir(parents=True, exist_ok=True)
            new_vectorstore.save_local(str(temp_index_path))
            logger.info(f"  Saved to temporary location: {temp_index_path}")

            # Hot-swap: replace old index with new one
            if self.index_path.exists():
                backup_path = self.index_path.parent / f"{self.index_path.name}_backup"
                if backup_path.exists():
                    shutil.rmtree(backup_path)
                shutil.move(str(self.index_path), str(backup_path))
                logger.info(f"  Backed up old index to {backup_path}")

            shutil.move(str(temp_index_path), str(self.index_path))
            logger.info(f"  Moved new index to {self.index_path}")

            # Update in-memory vectorstore and documents
            self.vectorstore = new_vectorstore
            self.documents = documents
            self._index_loaded = True
            self.index_metadata["last_updated"] = datetime.utcnow().isoformat() + "Z"

            # Rebuild retrievers with new index
            if self.llm:
                logger.info("Rebuilding retrievers...")
                self._setup_retrievers()

            build_time = time.time() - start_time
            logger.info(f"Index rebuild complete in {build_time:.2f}s")

            return {
                "status": "success",
                "message": "Index rebuilt successfully",
                "events_indexed": len(documents),
                "build_time_seconds": round(build_time, 2),
                "index_path": str(self.index_path),
            }

        except Exception as e:
            logger.error(f"Error rebuilding index: {e}", exc_info=True)
            return {
                "status": "failed",
                "message": f"Failed to rebuild index: {str(e)}",
                "events_indexed": None,
                "build_time_seconds": round(time.time() - start_time, 2),
                "index_path": None,
            }

    def get_info(self) -> Dict[str, Any]:
        """
        Get information about the RAG system.

        Returns:
            Dictionary with system information
        """
        return {
            "version": "1.2.0",
            "available_methods": ["basic", "hybrid", "advanced"],
            "index_info": {
                "documents_count": self.get_index_size() or 0,
                "embedding_model": self.embedding_model,
                "embedding_dimension": 1024,
                "last_updated": self.index_metadata.get("last_updated", "unknown"),
            },
            "model_info": {"llm_model": self.llm_model, "provider": "Mistral AI"},
        }


# Module-level function to get service instance
_rag_service_instance = None


def get_rag_service() -> RAGService:
    """
    Get the RAG service singleton instance.

    Returns:
        RAGService instance
    """
    global _rag_service_instance
    if _rag_service_instance is None:
        _rag_service_instance = RAGService()
    return _rag_service_instance
