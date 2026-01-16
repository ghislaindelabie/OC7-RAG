# OC7 - RAG: Cultural Events Recommendation Assistant

A Retrieval-Augmented Generation (RAG) system for recommending cultural events in the French Alps region (Savoie, Haute-Savoie, Isère).

## Project Overview

This project implements an intelligent chatbot POC (Proof of Concept) for **Puls-Events**, capable of answering user questions about cultural events using data from OpenAgenda.

### Features

- **Three RAG Flavors**: Basic, Hybrid (FAISS + BM25), and Advanced (Query Analysis + HyDE + Reranking)
- **LLM Integration**: Mistral API for embeddings and generation
- **Vector Store**: FAISS for efficient similarity search
- **Smart Query Handling**: Off-topic detection and query reformulation
- **REST API**: FastAPI endpoints (coming soon)
- **Automated Evaluation**: RAGAS metrics and LLM-as-Judge (coming soon)

### Target Geographic Zone

- Savoie (73)
- Haute-Savoie (74)
- Isère (38)

## Project Structure

```
OC7-RAG/
├── data/               # Data files (raw, processed, index)
├── notebooks/          # Jupyter notebooks for exploration
├── src/                # Source code
│   ├── data/           # Data loading and preprocessing
│   ├── rag/            # RAG components
│   └── api/            # FastAPI application
├── tests/              # Unit tests and evaluation
├── scripts/            # Utility scripts
└── docs/               # Documentation
```

## RAG Implementations

This project implements three progressively sophisticated RAG approaches:

### 1. Basic RAG (Baseline)
- **Method**: FAISS vector similarity search
- **Strengths**: Fast, simple, good semantic matching
- **Best for**: Standard queries with clear intent

### 2. Hybrid RAG
- **Method**: FAISS (dense) + BM25 (sparse) with Reciprocal Rank Fusion
- **Strengths**: Combines semantic and keyword matching
- **Best for**: Keyword-heavy queries (place names, artist names)

### 3. Advanced RAG
- **Method**: Query Analysis → HyDE → FAISS → FlashRank Reranking
- **Components**:
  - Query Analysis: Detects off-topic queries, reformulates questions
  - HyDE: Generates hypothetical documents for better matching
  - Reranking: Re-orders top-10 results to get best 5
- **Best for**: Complex queries, quality over speed

See `notebooks/01_baseline_rag.ipynb` for interactive comparison.

## Quick Start

### Prerequisites

- Python >= 3.11
- Conda
- Mistral API key

### Installation

1. Create conda environment:
```bash
conda create -n OC7 python=3.11
conda activate OC7
```

2. Install dependencies:
```bash
pip install langchain langchain-community langchain-mistralai \
    faiss-cpu pandas python-dotenv jupyter \
    rank_bm25 flashrank
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your MISTRAL_API_KEY
```

4. Run the baseline notebook:
```bash
jupyter notebook notebooks/01_baseline_rag.ipynb
```

## API Endpoints (Coming Soon)

The FastAPI implementation is planned for Phase 4:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ask` | POST | Submit a question, get an augmented response |
| `/rebuild` | POST | Rebuild the vector index |
| `/health` | GET | Health check |

## Development

### Current Status

**Phase 3 (Core RAG System): ✅ Completed**
- Three RAG implementations (Basic, Hybrid, Advanced)
- Interactive notebook with comprehensive testing
- Performance comparisons and metrics

**Next Phase: FastAPI API Development**

### Git Workflow

This project uses a version-based branching strategy:

- `main`: Protected, production-ready code (merge via PR only)
- `v{x}.{y}.{z}`: Version branches for development
- `feature/*`: Feature branches (merged into version branches)
- `hotfix/*`: Critical fixes (from main)

### Testing (Coming Soon)

```bash
pytest tests/
```

### Evaluation (Coming Soon)

```bash
python tests/evaluate_rag.py
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| **LLM** | Mistral API (mistral-small-latest) |
| **Embeddings** | Mistral AI (mistral-embed, 1024 dimensions) |
| **Vector Store** | FAISS (IndexFlatL2) |
| **Sparse Retrieval** | BM25 (rank_bm25) |
| **Reranking** | FlashRank (ms-marco-MiniLM-L-12-v2) |
| **Framework** | LangChain |
| **Notebooks** | Jupyter |
| **Data Processing** | Pandas, BeautifulSoup |
| **API** | FastAPI (planned) |
| **Evaluation** | RAGAS (planned) |

## Documentation

- Technical implementation in `notebooks/01_baseline_rag.ipynb`
- [Technical Report](docs/technical_report.pdf) - Coming soon

## License

This project is developed as part of OpenClassrooms training.

## Data Source

Event data from [OpenAgenda](https://openagenda.com/) via [OpenDataSoft](https://public.opendatasoft.com/explore/dataset/evenements-publics-openagenda/).
