"""
RAG Service - Singleton service for managing the RAG system.

This service loads and manages the FAISS index, retrievers, and LLM,
providing a clean interface for the API endpoints.
"""

import json
import logging
import os
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
from langchain_core.prompts import PromptTemplate
from langchain_mistralai import MistralAIEmbeddings, ChatMistralAI
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever
from langchain_community.document_compressors import FlashrankRerank
from langchain_classic.chains import RetrievalQA
from langchain_classic.retrievers import EnsembleRetriever, ContextualCompressionRetriever

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# RAG prompt template (same as in evaluation script)
RAG_PROMPT_TEMPLATE = """Tu es un assistant spécialisé dans les événements culturels de Savoie, Haute-Savoie et Isère.
Utilise les informations suivantes pour répondre à la question de l'utilisateur.
Si tu ne trouves pas l'information dans le contexte, dis-le clairement.

Contexte:
{context}

Question: {question}

Réponse détaillée:"""


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
    """Extract metadata from event."""
    return {
        "uid": event.get("uid", ""),
        "title": event.get("title_fr", ""),
        "city": event.get("location_city", ""),
        "department": event.get("location_department", ""),
        "daterange": event.get("daterange_fr", ""),
        "category": event.get("category", ""),
        "url": event.get("canonicalurl", ""),
    }


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
        self.chains = {}  # Cache for RAG chains
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

            # Load FAISS index
            if self.index_path.exists():
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
                logger.warning(f"FAISS index not found at {self.index_path}")
                self._index_loaded = False

            # Setup RAG chains if index is loaded
            if self._index_loaded and self.documents:
                self._setup_chains()

        except Exception as e:
            logger.error(f"Error loading RAG components: {e}")
            self._llm_available = False
            self._index_loaded = False
            raise

    def _setup_chains(self):
        """Set up all three RAG chains: Basic, Hybrid, Advanced."""
        if not self.vectorstore or not self.llm:
            return

        prompt = PromptTemplate(
            template=RAG_PROMPT_TEMPLATE, input_variables=["context", "question"]
        )

        # Basic RAG (FAISS only)
        logger.info("Setting up Basic RAG chain...")
        basic_retriever = self.vectorstore.as_retriever(search_kwargs={"k": 5})
        self.chains["basic"] = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=basic_retriever,
            return_source_documents=True,
            chain_type_kwargs={"prompt": prompt},
        )

        # Hybrid RAG (FAISS + BM25)
        logger.info("Setting up Hybrid RAG chain...")
        bm25_retriever = BM25Retriever.from_documents(self.documents)
        bm25_retriever.k = 5
        faiss_retriever = self.vectorstore.as_retriever(search_kwargs={"k": 5})
        ensemble_retriever = EnsembleRetriever(
            retrievers=[faiss_retriever, bm25_retriever], weights=[0.5, 0.5]
        )
        self.chains["hybrid"] = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=ensemble_retriever,
            return_source_documents=True,
            chain_type_kwargs={"prompt": prompt},
        )

        # Advanced RAG (with reranking)
        # Uses FlashrankRerank for re-ordering retrieved documents by relevance.
        # If FlashRank is unavailable (missing dependency, incompatible environment),
        # we fall back to hybrid method to ensure the API remains functional.
        logger.info("Setting up Advanced RAG chain...")
        try:
            compressor = FlashrankRerank(top_n=5)
            compression_retriever = ContextualCompressionRetriever(
                base_compressor=compressor, base_retriever=ensemble_retriever
            )
            self.chains["advanced"] = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=compression_retriever,
                return_source_documents=True,
                chain_type_kwargs={"prompt": prompt},
            )
        except Exception as e:
            # Fallback to hybrid for advanced - API remains functional but without reranking
            logger.warning(
                f"FlashrankRerank unavailable ({e}), 'advanced' method will use hybrid retrieval. "
                "Install flashrank package for reranking support."
            )
            self.chains["advanced"] = self.chains["hybrid"]
            self._advanced_uses_fallback = True

        logger.info("All RAG chains ready")

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

    def query(self, question: str, method: str = "hybrid", top_k: int = 5) -> Dict[str, Any]:
        """
        Query the RAG system.

        Args:
            question: User question
            method: RAG method ("basic", "hybrid", or "advanced")
            top_k: Number of documents to retrieve

        Returns:
            Dictionary with answer, sources, and metadata
        """
        if not self.is_ready():
            raise RuntimeError("RAG service not ready - index not loaded")

        if method not in self.chains:
            raise ValueError(f"Unknown RAG method: {method}. Available: {list(self.chains.keys())}")

        start_time = time.time()

        try:
            # Get the appropriate chain
            chain = self.chains[method]

            # Run the query
            result = chain.invoke({"query": question})

            # Extract answer and source documents
            answer = result.get("result", "")
            source_docs = result.get("source_documents", [])

            # Format sources for response
            sources = []
            for doc in source_docs[:top_k]:
                source = {
                    "title": doc.metadata.get("title", "Unknown"),
                    "location": doc.metadata.get("city", None),
                    "date_start": doc.metadata.get("daterange", None),
                    "description_snippet": (
                        doc.page_content[:200] + "..."
                        if len(doc.page_content) > 200
                        else doc.page_content
                    ),
                    "relevance_score": None,  # FAISS doesn't provide score in chain
                }
                sources.append(source)

            response_time_ms = int((time.time() - start_time) * 1000)

            return {
                "answer": answer,
                "sources": sources,
                "metadata": {
                    "rag_method": method,
                    "response_time_ms": response_time_ms,
                    "retrieved_docs_count": len(sources),
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "model_version": self.llm_model,
                },
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

            # Rebuild RAG chains with new index
            if self.llm:
                logger.info("Rebuilding RAG chains...")
                self._setup_chains()

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
            "version": "1.1.0",
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
