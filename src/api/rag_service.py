"""
RAG Service - Singleton service for managing the RAG system.

This service loads and manages the FAISS index, retrievers, and LLM,
providing a clean interface for the API endpoints.
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

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
    soup = BeautifulSoup(html_text, 'lxml')
    return soup.get_text(separator=' ', strip=True)


def _build_document_text(event: dict) -> str:
    """Build comprehensive document text from event data."""
    parts = []

    title = event.get('title_fr', '')
    if title:
        parts.append(f"Événement: {title}")

    long_desc = _clean_html(event.get('longdescription_fr', ''))
    short_desc = event.get('description_fr', '')
    description = long_desc if long_desc else short_desc
    if description:
        parts.append(f"Description: {description}")

    city = event.get('location_city', '')
    location_name = event.get('location_name', '')
    address = event.get('location_address', '')
    department = event.get('location_department', '')

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

    daterange = event.get('daterange_fr', '')
    if daterange:
        parts.append(f"Date: {daterange}")

    category = event.get('category', '')
    if category:
        parts.append(f"Catégorie: {category}")

    keywords = event.get('keywords_fr', [])
    if keywords:
        parts.append(f"Mots-clés: {', '.join(keywords[:10])}")

    return '\n'.join(parts)


def _build_metadata(event: dict) -> dict:
    """Extract metadata from event."""
    return {
        'uid': event.get('uid', ''),
        'title': event.get('title_fr', ''),
        'city': event.get('location_city', ''),
        'department': event.get('location_department', ''),
        'daterange': event.get('daterange_fr', ''),
        'category': event.get('category', ''),
        'url': event.get('canonicalurl', '')
    }


class RAGService:
    """
    Singleton service for RAG operations.

    Manages FAISS index, retrievers, and LLM for the API.
    """

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

        logger.info("Initializing RAG Service...")

        # Service state
        self._initialized = False
        self._index_loaded = False
        self._llm_available = False

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
            self._initialized = True
            logger.info("RAG Service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize RAG Service: {e}")
            self._initialized = False

    def _load_events_as_documents(self) -> List[Document]:
        """Load events JSON and convert to LangChain Documents."""
        if not self.data_path.exists():
            logger.warning(f"Data file not found: {self.data_path}")
            return []

        logger.info(f"Loading events from {self.data_path}...")
        with open(self.data_path, 'r', encoding='utf-8') as f:
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
            self.embeddings = MistralAIEmbeddings(
                model=self.embedding_model,
                api_key=api_key
            )

            # Initialize LLM
            self.llm = ChatMistralAI(
                model=self.llm_model,
                api_key=api_key,
                temperature=0.1
            )
            self._llm_available = True

            # Load documents (needed for BM25)
            self.documents = self._load_events_as_documents()

            # Load FAISS index
            if self.index_path.exists():
                logger.info(f"Loading FAISS index from {self.index_path}")
                self.vectorstore = FAISS.load_local(
                    str(self.index_path),
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                self._index_loaded = True
                self.index_metadata["last_updated"] = datetime.fromtimestamp(
                    self.index_path.stat().st_mtime
                ).isoformat() + "Z"
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
            template=RAG_PROMPT_TEMPLATE,
            input_variables=["context", "question"]
        )

        # Basic RAG (FAISS only)
        logger.info("Setting up Basic RAG chain...")
        basic_retriever = self.vectorstore.as_retriever(search_kwargs={"k": 5})
        self.chains["basic"] = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=basic_retriever,
            return_source_documents=True,
            chain_type_kwargs={"prompt": prompt}
        )

        # Hybrid RAG (FAISS + BM25)
        logger.info("Setting up Hybrid RAG chain...")
        bm25_retriever = BM25Retriever.from_documents(self.documents)
        bm25_retriever.k = 5
        faiss_retriever = self.vectorstore.as_retriever(search_kwargs={"k": 5})
        ensemble_retriever = EnsembleRetriever(
            retrievers=[faiss_retriever, bm25_retriever],
            weights=[0.5, 0.5]
        )
        self.chains["hybrid"] = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=ensemble_retriever,
            return_source_documents=True,
            chain_type_kwargs={"prompt": prompt}
        )

        # Advanced RAG (with reranking)
        logger.info("Setting up Advanced RAG chain...")
        try:
            compressor = FlashrankRerank(top_n=5)
            compression_retriever = ContextualCompressionRetriever(
                base_compressor=compressor,
                base_retriever=ensemble_retriever
            )
            self.chains["advanced"] = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=compression_retriever,
                return_source_documents=True,
                chain_type_kwargs={"prompt": prompt}
            )
        except Exception as e:
            logger.warning(f"Failed to setup Advanced RAG (reranking): {e}")
            # Fallback to hybrid for advanced
            self.chains["advanced"] = self.chains["hybrid"]

        logger.info("All RAG chains ready")

    def is_ready(self) -> bool:
        """Check if service is ready to handle requests."""
        return self._initialized and self._index_loaded

    def is_llm_available(self) -> bool:
        """Check if LLM is available."""
        return self._llm_available

    def get_index_size(self) -> Optional[int]:
        """Get number of documents in index."""
        if not self._index_loaded or not self.vectorstore:
            return None
        return self.vectorstore.index.ntotal

    def query(
        self,
        question: str,
        method: str = "hybrid",
        top_k: int = 5
    ) -> Dict[str, Any]:
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
                    "description_snippet": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                    "relevance_score": None  # FAISS doesn't provide score in chain
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
                    "model_version": self.llm_model
                }
            }

        except Exception as e:
            logger.error(f"Error during RAG query: {e}")
            raise

    def rebuild_index(
        self,
        force: bool = False,
        download_fresh_data: bool = True
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
            # TODO: Implement index rebuild logic
            # 1. Download data if requested
            # 2. Process and filter events
            # 3. Build FAISS index
            # 4. Hot-swap the index

            build_time = time.time() - start_time

            return {
                "status": "success",
                "message": "Index rebuilt successfully (placeholder)",
                "events_indexed": 0,  # Placeholder
                "build_time_seconds": build_time,
                "index_path": str(self.index_path)
            }

        except Exception as e:
            logger.error(f"Error rebuilding index: {e}")
            return {
                "status": "failed",
                "message": f"Failed to rebuild index: {str(e)}",
                "events_indexed": None,
                "build_time_seconds": time.time() - start_time,
                "index_path": None
            }

    def get_info(self) -> Dict[str, Any]:
        """
        Get information about the RAG system.

        Returns:
            Dictionary with system information
        """
        return {
            "version": "0.3.0",
            "available_methods": ["basic", "hybrid", "advanced"],
            "index_info": {
                "documents_count": self.get_index_size() or 0,
                "embedding_model": self.embedding_model,
                "embedding_dimension": 1024,
                "last_updated": self.index_metadata.get("last_updated", "unknown")
            },
            "model_info": {
                "llm_model": self.llm_model,
                "provider": "Mistral AI"
            }
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
