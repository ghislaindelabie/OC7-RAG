# OC7 - RAG: Cultural Events Recommendation Assistant

A Retrieval-Augmented Generation (RAG) system for recommending cultural events in the French Alps region (Savoie, Haute-Savoie, Isère).

## Project Overview

This project implements an intelligent chatbot POC (Proof of Concept) for **Puls-Events**, capable of answering user questions about cultural events using data from OpenAgenda.

### Features

- **Three RAG Flavors**: Basic, Hybrid (FAISS + BM25), and Advanced (Query Analysis + HyDE + Reranking)
- **LLM Integration**: Mistral API for embeddings and generation
- **Vector Store**: FAISS for efficient similarity search
- **Smart Query Handling**: Off-topic detection and query reformulation
- **REST API**: FastAPI endpoints (Phase 4 - planned)
- **Automated Evaluation**: LLM-as-Judge with Chain-of-Thought reasoning ✅
- **Test Dataset**: 18 annotated questions across 4 categories ✅

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

**Phase 5 (Evaluation & Testing): ✅ Completed**
- Test dataset: 18 annotated questions (factual, complex, off-topic, vague)
- LLM-as-Judge evaluation with mistral-large and Chain-of-Thought
- Automated test runner for all 3 RAG methods
- Statistics generation (PASS/PARTIAL/FAIL breakdown)
- Results export to CSV/JSON/TXT formats

**Next Phase: FastAPI API Development (Phase 4)**

### Git Workflow

This project uses a version-based branching strategy:

- `main`: Protected, production-ready code (merge via PR only)
- `v{x}.{y}.{z}`: Version branches for development
- `feature/*`: Feature branches (merged into version branches)
- `hotfix/*`: Critical fixes (from main)

### Evaluation

The evaluation framework is implemented in notebook cells 24-31:

1. **Load test dataset** from `tests/test_data/test_questions.csv`
2. **Run automated tests** through all 3 RAG methods
3. **LLM-as-Judge evaluation** with semantic equivalence rubric
4. **Generate statistics** (% PASS/PARTIAL/FAIL by category and difficulty)
5. **Export results** to CSV/JSON/TXT

To run the evaluation:
```bash
jupyter notebook notebooks/01_baseline_rag.ipynb
# Execute cells 1-31, set RUN_FULL_EVALUATION = True in cell 28 for full test suite
```

### Testing (Unit Tests - Planned)

```bash
pytest tests/
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
| **Evaluation** | LLM-as-Judge (mistral-large), RAGAS (optional) |

## Evaluation Framework

### Test Dataset

Located in `tests/test_data/test_questions.csv` with 18 annotated questions:

| Category | Count | Description |
|----------|-------|-------------|
| **Factual** | 10 | Direct questions about specific events |
| **Complex** | 3 | Multi-criteria queries (location + type + audience) |
| **Off-topic** | 3 | Questions unrelated to cultural events |
| **Vague** | 2 | Incomplete questions requiring clarification |

### LLM-as-Judge Evaluation

**Model**: mistral-large-latest with Chain-of-Thought reasoning

**Rubric** (Semantic Equivalence):
- **PASS**: Correct events with accurate information (dates, locations, types)
- **PARTIAL**: Some correct but missing key elements or minor inaccuracies
- **FAIL**: Wrong/fabricated events, incorrect details, or irrelevant responses

**Key Principle**: Focus on factual correctness, not completeness. An answer with fewer events that are all correct receives PASS, not PARTIAL.

### Evaluation Results

Run `notebooks/01_baseline_rag.ipynb` cells 24-31 to:
- Execute all 18 test questions through 3 RAG methods
- Generate automated verdicts with LLM judge
- View statistics breakdown by category and difficulty
- Export results to `evaluation_results/` directory

## Documentation

- Technical implementation in `notebooks/01_baseline_rag.ipynb`
- Evaluation framework: notebook cells 24-31
- [Technical Report](docs/technical_report.pdf) - Coming soon

## License

This project is developed as part of OpenClassrooms training.

## Data Source

Event data from [OpenAgenda](https://openagenda.com/) via [OpenDataSoft](https://public.opendatasoft.com/explore/dataset/evenements-publics-openagenda/).
