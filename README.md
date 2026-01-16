# OC7 - RAG: Cultural Events Recommendation Assistant

A Retrieval-Augmented Generation (RAG) system for recommending cultural events in the French Alps region (Savoie, Haute-Savoie, Isère).

## Project Overview

This project implements an intelligent chatbot POC (Proof of Concept) for **Puls-Events**, capable of answering user questions about cultural events using data from OpenAgenda.

### Features

- **RAG System**: LangChain + Mistral + FAISS integration
- **REST API**: FastAPI endpoints for question-answering
- **Hybrid Search**: Vector search + BM25 for optimal retrieval
- **Automated Evaluation**: RAGAS metrics and LLM-as-Judge

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

## Quick Start

### Prerequisites

- Python >= 3.11
- Conda
- UV package manager
- Mistral API key

### Installation

1. Create conda environment:
```bash
conda create -n OC7 python=3.11
conda activate OC7
```

2. Install UV and dependencies:
```bash
pip install uv
uv sync
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

4. Download and index data:
```bash
python scripts/download_data.py
python scripts/build_index.py
```

5. Run the API:
```bash
uvicorn src.api.main:app --reload
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ask` | POST | Submit a question, get an augmented response |
| `/rebuild` | POST | Rebuild the vector index |
| `/health` | GET | Health check |

## Development

### Git Workflow

This project uses a version-based branching strategy:

- `main`: Protected, production-ready code (merge via PR only)
- `v{x}.{y}.{z}`: Version branches for development
- `feature/*`: Feature branches (merged into version branches)
- `hotfix/*`: Critical fixes (from main)

See [MACRO_PLAN.md](Documents%20de%20planification%20et%20cadrage/MACRO_PLAN.md) for detailed guidelines.

### Running Tests

```bash
pytest tests/
```

### Evaluation

```bash
python tests/evaluate_rag.py
```

## Tech Stack

- **LLM**: Mistral API
- **Embeddings**: sentence-transformers / Mistral
- **Vector Store**: FAISS
- **Framework**: LangChain
- **API**: FastAPI
- **Evaluation**: RAGAS

## Documentation

- [Macro Plan](Documents%20de%20planification%20et%20cadrage/MACRO_PLAN.md) - Detailed project plan
- [Technical Report](docs/technical_report.pdf) - Architecture and results (coming soon)

## License

This project is developed as part of OpenClassrooms training.

## Data Source

Event data from [OpenAgenda](https://openagenda.com/) via [OpenDataSoft](https://public.opendatasoft.com/explore/dataset/evenements-publics-openagenda/).
