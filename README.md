# OC7-RAG: Cultural Events Recommendation Assistant 🎭

[![Version](https://img.shields.io/badge/version-1.1-blue.svg)](VERSION_HISTORY.md)
[![Python](https://img.shields.io/badge/python-3.11+-green.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://hub.docker.com/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![CI/CD](https://github.com/ghislaindelabie/OC7-RAG/actions/workflows/deploy.yml/badge.svg)](https://github.com/ghislaindelabie/OC7-RAG/actions)
[![Tests](https://img.shields.io/badge/tests-87%20passing-brightgreen.svg)](tests/)

> **A production-ready Retrieval-Augmented Generation (RAG) system for discovering cultural events in the French Alps region.**

Welcome! This project showcases a complete, production-ready RAG system that helps users discover cultural events in Savoie (73), Haute-Savoie (74), and Isère (38). Built with modern AI/ML technologies and deployed with CI/CD automation.

## What is this?

**OC7-RAG** (Puls-Events) is an intelligent chatbot that answers natural language questions about cultural events using real data from OpenAgenda. Unlike traditional keyword search or pure LLM systems, it combines:

- **Retrieval**: Searches a verified database of 10,000+ real events
- **Augmentation**: Enriches responses with relevant context
- **Generation**: Uses AI (Mistral) to provide natural, accurate answers

**Key Features:**
- 🎯 Three RAG implementations (Basic, Hybrid, Advanced)
- 🚀 Production REST API with FastAPI
- 🐳 Full Docker containerization + CI/CD pipeline
- 🧪 87 comprehensive unit tests (100% passing)
- 📊 Automated LLM-as-Judge evaluation framework
- 💬 Interactive web chat interface
- 📚 Complete technical documentation

## Quick Links

📖 **Documentation**
- [Technical Report](docs/technical_report.md) - Complete 15-page technical documentation
- [Deployment Guide](DEPLOYMENT_STATUS.md) - Production deployment instructions
- [Setup Guide](docs/reference/SETUP.md) - Local development setup
- [Version History](VERSION_HISTORY.md) - Changelog and release notes
- [Known Issues](docs/KNOWN_ISSUES.md) - Current limitations and workarounds
- [HTTPS Setup](docs/HTTPS_SETUP.md) - SSL certificate configuration guide

🚀 **Live Deployment** (Hetzner Cloud - Docker + CI/CD)
- **Web Chat Interface**: http://188.34.205.146:8000/ - Interactive chat UI
- **API Base URL**: http://188.34.205.146:8000
  - Main endpoint: `POST /api/v1/ask` - Submit questions
  - Health check: `GET /health` - System status
  - System info: `GET /api/v1/rag/info` - RAG statistics
- **API Documentation**: http://188.34.205.146:8000/docs - Interactive OpenAPI (Swagger UI)

📊 **Resources**
- [Jupyter Notebook](notebooks/01_baseline_rag.ipynb) - Interactive RAG exploration
- [Test Dataset](tests/test_data/test_questions.csv) - 56 annotated evaluation questions
- [GitHub Repository](https://github.com/ghislaindelabie/OC7-RAG) - Source code and issues

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         User Query                          │
│                "Quels concerts à Annecy?"                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI REST API                       │
│  Endpoints: /health, /api/v1/ask, /api/v1/info, /rebuild   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    RAG Service Layer                        │
│    ┌──────────┐  ┌──────────┐  ┌──────────────────────┐   │
│    │  Basic   │  │  Hybrid  │  │     Advanced         │   │
│    │  FAISS   │  │FAISS+BM25│  │ Query Analysis+HyDE  │   │
│    │          │  │   +RRF   │  │    +Reranking        │   │
│    └──────────┘  └──────────┘  └──────────────────────┘   │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
┌────────────┐ ┌──────────┐ ┌─────────────┐
│   FAISS    │ │   BM25   │ │ FlashRank   │
│ Vector DB  │ │ Sparse   │ │  Reranker   │
│ (10k docs) │ │ Retriever│ │             │
└────────────┘ └──────────┘ └─────────────┘
        │            │            │
        └────────────┼────────────┘
                     ▼
        ┌───────────────────────────┐
        │    Mistral AI LLM         │
        │  - Embeddings (1024-dim)  │
        │  - Generation (small)     │
        │  - Evaluation (large)     │
        └───────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  Generated Response                         │
│  "Voici 3 concerts à Annecy ce weekend: ..."               │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **User Query** → FastAPI endpoint receives natural language question
2. **RAG Selection** → Choose method: Basic (fast), Hybrid (balanced), Advanced (quality)
3. **Retrieval** → Search FAISS vector store and/or BM25 index
4. **Augmentation** → Gather relevant event documents (top 5-10)
5. **Generation** → Mistral LLM synthesizes natural response from context
6. **Response** → JSON with answer, sources, and metadata

### Geographic Coverage

- 🏔️ Savoie (73)
- 🏔️ Haute-Savoie (74)
- 🏔️ Isère (38)

**Data Source**: [OpenAgenda](https://openagenda.com/) via [OpenDataSoft](https://public.opendatasoft.com/explore/dataset/evenements-publics-openagenda/) (10,648 events, updated weekly)

---

## Key Features

### Three RAG Implementations

| Method | Description | Best For | Speed |
|--------|-------------|----------|-------|
| **Basic** | FAISS vector similarity only | Standard semantic queries | ⚡⚡⚡ Fastest |
| **Hybrid** | FAISS + BM25 with RRF fusion | Keyword-heavy queries (names, places) | ⚡⚡ Fast |
| **Advanced** | Hybrid + Query Analysis + Reranking | Complex multi-criteria queries | ⚡ Quality-focused |

### Production Features

- ✅ **REST API**: 4 endpoints with comprehensive error handling
- ✅ **Docker Ready**: Multi-stage Dockerfile, docker-compose orchestration
- ✅ **CI/CD Pipeline**: GitHub Actions for automated build/test/deploy
- ✅ **Auto-Rebuild**: FAISS index automatically built on first container startup
- ✅ **Web Interface**: Interactive chat UI for testing
- ✅ **Health Monitoring**: Container health checks and status endpoints
- ✅ **Comprehensive Testing**: 87 unit tests (100% passing)
- ✅ **LLM-as-Judge**: Automated evaluation with 56 test questions
- ✅ **Smart Query Handling**: Off-topic detection and query reformulation

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

---

## 🚀 Quick Start

Choose your deployment method:

### Option 1: Docker (Recommended for Production)

**Prerequisites:**
- Docker + Docker Compose installed
- Mistral API key ([get one free](https://console.mistral.ai/))

**Steps:**

1. **Clone the repository**
   ```bash
   git clone https://github.com/ghislaindelabie/OC7-RAG.git
   cd OC7-RAG
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   nano .env  # Add your MISTRAL_API_KEY
   ```

3. **Start with Docker Compose**
   ```bash
   docker-compose up -d
   ```

   First startup takes 3-5 minutes (downloads data + builds index automatically).

4. **Test the API**
   ```bash
   # Health check
   curl http://localhost:8000/health

   # Ask a question
   curl -X POST http://localhost:8000/api/v1/ask \
     -H "Content-Type: application/json" \
     -d '{"question": "Quels concerts à Annecy ce weekend?"}'
   ```

5. **Access the web interface**

   Open http://localhost:8000 in your browser for the interactive chat interface.

6. **View API documentation**

   Open http://localhost:8000/docs for interactive OpenAPI documentation.

**That's it!** 🎉 Your RAG system is running.

---

### Option 2: Local Development (Python)

**Prerequisites:**
- Python 3.11 or higher
- Conda (recommended) or pip
- Mistral API key ([get one free](https://console.mistral.ai/))

**Step-by-step setup:**

1. **Clone the repository**
   ```bash
   git clone https://github.com/ghislaindelabie/OC7-RAG.git
   cd OC7-RAG
   ```

2. **Create Python environment**

   Using Conda (recommended):
   ```bash
   conda create -n OC7 python=3.11
   conda activate OC7
   ```

   Or using venv:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

   This installs:
   - LangChain (RAG framework)
   - Mistral AI SDK (embeddings + LLM)
   - FAISS (vector store)
   - FastAPI (REST API)
   - pytest (testing)
   - And more...

4. **Configure API key**
   ```bash
   cp .env.example .env
   nano .env  # Or use your favorite editor
   ```

   Add your Mistral API key:
   ```
   MISTRAL_API_KEY=your_key_here
   ```

5. **Download and prepare data** (first time only)
   ```bash
   python scripts/download_data.py
   python scripts/filter_data.py
   ```

   This downloads events from OpenAgenda (~72MB) and filters to target departments.

6. **Build FAISS index** (first time only)
   ```bash
   python scripts/build_index.py
   ```

   Takes 2-3 minutes to embed ~10,000 events.

7. **Start the API server**
   ```bash
   python scripts/run_api.py
   ```

   Server starts at http://localhost:8000

8. **Test the setup**
   ```bash
   # In another terminal
   curl http://localhost:8000/health

   # Ask a question
   curl -X POST http://localhost:8000/api/v1/ask \
     -H "Content-Type: application/json" \
     -d '{"question": "Quels concerts à Annecy?"}'
   ```

9. **Explore the Jupyter notebook** (optional)
   ```bash
   jupyter notebook notebooks/01_baseline_rag.ipynb
   ```

   Interactive exploration of all three RAG methods with live examples.

**Troubleshooting:**
- Missing API key? Check `.env` file exists and contains valid `MISTRAL_API_KEY`
- Import errors? Verify you activated the environment: `conda activate OC7`
- FAISS index not found? Run `python scripts/build_index.py`
- For more help, see [Known Issues](docs/KNOWN_ISSUES.md)

---

## REST API

The FastAPI application provides the following endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check with index and LLM status |
| `/api/v1/rag/info` | GET | RAG system information and statistics |
| `/api/v1/ask` | POST | Submit a question, get an augmented response |
| `/api/v1/rebuild` | POST | Rebuild the FAISS vector index |

### Running the API

```bash
# Activate environment
conda activate OC7

# Run the API server
python scripts/run_api.py

# API available at http://localhost:8000
# Interactive docs at http://localhost:8000/docs
```

### Example Usage

```bash
# Health check
curl http://localhost:8000/health

# Ask a question (using hybrid RAG method)
curl -X POST http://localhost:8000/api/v1/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Quels concerts à Annecy ce weekend?", "rag_method": "hybrid"}'

# Get RAG system info
curl http://localhost:8000/api/v1/rag/info
```

### RAG Methods

- `basic` - FAISS vector similarity only (fastest)
- `hybrid` - FAISS + BM25 keyword search (recommended)
- `advanced` - Hybrid + FlashRank reranking (highest quality)

## Docker Deployment

### Quick Start with Docker

```bash
# Build the image
docker build -t oc7-rag-api .

# Run with docker-compose
docker-compose up -d

# Or run directly
docker run -d \
  --name oc7-rag-api \
  -p 8000:8000 \
  -e MISTRAL_API_KEY="your-key" \
  oc7-rag-api
```

### Docker Features

- **Multi-stage build**: Optimized image size (~2GB)
- **Non-root user**: Security best practice
- **Health checks**: Container orchestration ready
- **Auto-rebuild**: FAISS index built on first startup, persisted via volumes

### Testing the Container

```bash
# Health check
curl http://localhost:8000/health

# Test RAG query
curl -X POST http://localhost:8000/api/v1/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Quels concerts à Annecy?"}'
```

## Development Status

### Project Completion: v1.0.0 ✅

All development phases completed and production-ready:

**Phase 1-2: Data Collection & Preprocessing** ✅
- OpenAgenda data ingestion with API-level filtering
- Geographic filtering (Savoie, Haute-Savoie, Isère)
- Data cleaning and structuring (10,648 events)

**Phase 3: Core RAG System** ✅
- Three RAG implementations (Basic, Hybrid, Advanced)
- Interactive Jupyter notebook with live examples
- Performance comparisons and ablation studies

**Phase 4: REST API** ✅
- 4 production endpoints (health, info, ask, rebuild)
- FastAPI with automatic OpenAPI documentation
- Pydantic schemas for request/response validation
- Comprehensive error handling and logging

**Phase 5: Testing & Evaluation** ✅
- 87 unit tests (100% passing)
- 56 annotated evaluation questions
- LLM-as-Judge framework with Chain-of-Thought
- Automated evaluation pipeline

**Phase 6: Production Deployment** ✅
- Docker containerization (multi-stage build)
- CI/CD pipeline with GitHub Actions
- Automated build/test/deploy on push to main
- Production server running on Hetzner Cloud
- Auto-rebuild feature for FAISS index
- Web chat interface

**Phase 7: Documentation** ✅
- 15-page technical report
- Comprehensive README and setup guides
- API documentation and examples
- Known issues and troubleshooting guides

### CI/CD Pipeline

The project uses GitHub Actions for full automation:

```yaml
Trigger: Push to main branch
│
├─ Job 1: Run Tests (pytest)
│   └─ Exit if tests fail
│
├─ Job 2: Build Docker Image
│   ├─ Build multi-stage Dockerfile
│   ├─ Push to GitHub Container Registry (GHCR)
│   └─ Tag: latest + commit SHA
│
└─ Job 3: Deploy to Production
    ├─ SSH to Hetzner server
    ├─ Pull latest image from GHCR
    ├─ Stop old container
    ├─ Start new container
    ├─ Wait for health check (300s)
    └─ Verify deployment success
```

**Deployment URL**: `.github/workflows/deploy.yml`

See [DEPLOYMENT_STATUS.md](DEPLOYMENT_STATUS.md) for production server details.

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

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run unit tests only (fast, no API calls)
pytest tests/test_indexation.py tests/test_retriever.py -v

# Run API tests
pytest tests/test_api.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=term-missing
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
| **API** | FastAPI + Uvicorn |
| **Containerization** | Docker, docker-compose |
| **Testing** | pytest, httpx |
| **Data Processing** | Pandas, BeautifulSoup |
| **Evaluation** | LLM-as-Judge (mistral-large) |

## Evaluation Framework

### Test Dataset

Located in `tests/test_data/test_questions.csv` with 56 annotated questions:

| Category | Count | Description |
|----------|-------|-------------|
| **Factual** | 30+ | Direct questions about specific events |
| **Complex** | 10+ | Multi-criteria queries (location + type + audience) |
| **Off-topic** | 8+ | Questions unrelated to cultural events |
| **Vague** | 8+ | Incomplete questions requiring clarification |

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

---

## 📚 Documentation

### Getting Started

| Document | Description |
|----------|-------------|
| [**README.md**](README.md) | This file - main project overview and quick start |
| [**Setup Guide**](docs/reference/SETUP.md) | Detailed local and server setup instructions |
| [**Deployment Guide**](DEPLOYMENT_STATUS.md) | Production deployment on Hetzner server |
| [**HTTPS Setup**](docs/HTTPS_SETUP.md) | SSL certificate configuration with Let's Encrypt |

### Technical Documentation

| Document | Description |
|----------|-------------|
| [**Technical Report**](docs/technical_report.md) | 15-page complete technical documentation (PDF export pending) |
| [**API Reference**](http://localhost:8000/docs) | Interactive OpenAPI documentation (when server running) |
| [**Architecture Details**](notebooks/01_baseline_rag.ipynb) | Jupyter notebook with RAG system deep-dive |
| [**Known Issues**](docs/KNOWN_ISSUES.md) | Current limitations, workarounds, and fixes |

### Development Resources

| Document | Description |
|----------|-------------|
| [**VERSION_HISTORY.md**](VERSION_HISTORY.md) | Complete changelog and release notes |
| [**CLAUDE.md**](CLAUDE.md) | Development guidelines, git workflow, and coding standards |
| [**Dependencies**](docs/reference/DEPENDENCY_MANAGEMENT.md) | Dependency management strategy |
| [**Chat Interface**](docs/reference/CHATBOT_INTERFACE.md) | Web UI documentation |

### Evaluation & Testing

| Resource | Description |
|----------|-------------|
| [Test Dataset](tests/test_data/test_questions.csv) | 56 annotated questions across 4 categories |
| [Unit Tests](tests/) | 87 comprehensive tests (indexation, retrieval, API) |
| [Evaluation Notebook](notebooks/01_baseline_rag.ipynb) | Cells 24-31: LLM-as-Judge framework |

### Future Enhancements

| Document | Description |
|----------|-------------|
| [Vector Store Migration](docs/future/VECTOR_STORE_MIGRATION.md) | Guide for migrating to Chroma/Qdrant |
| [API Authentication](docs/future/API_AUTHENTICATION.md) | Adding authentication to endpoints |

### Project Archives

Historical development records available in `docs/archive/` (session summaries, completion reports).

---

---

## 💡 Usage Examples

### Example 1: Simple Query (Basic RAG)
```bash
curl -X POST http://localhost:8000/api/v1/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Quels sont les concerts à Chambéry?",
    "rag_method": "basic"
  }'
```

**Response:**
```json
{
  "answer": "Voici les concerts prévus à Chambéry : [event details...]",
  "rag_method": "basic",
  "sources": ["event_id_1", "event_id_2", "event_id_3"],
  "processing_time_ms": 847
}
```

### Example 2: Complex Query (Hybrid RAG)
```bash
curl -X POST http://localhost:8000/api/v1/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Je cherche des activités familiales dans le 74 ce weekend",
    "rag_method": "hybrid"
  }'
```

### Example 3: Quality-focused (Advanced RAG)
```bash
curl -X POST http://localhost:8000/api/v1/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Événements culturels gratuits près du lac Léman en juillet?",
    "rag_method": "advanced"
  }'
```

### Example 4: Python Client
```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/ask",
    json={
        "question": "Quels festivals de musique en Haute-Savoie cet été?",
        "rag_method": "hybrid"
    }
)

data = response.json()
print(data["answer"])
```

### Example 5: Health Check
```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "index_loaded": true,
  "llm_available": true,
  "num_documents": 10648,
  "last_updated": "2026-02-04T12:00:00Z"
}
```

---

## 🤝 Contributing

This project was developed as part of OpenClassrooms Data Science training. While it's primarily an educational project, feedback and suggestions are welcome!

**For questions or feedback:**
1. Open an issue on [GitHub](https://github.com/ghislaindelabie/OC7-RAG/issues)
2. Review the [development guidelines](CLAUDE.md)
3. Check [known issues](docs/KNOWN_ISSUES.md) first

---

## 📄 License

This project is licensed under the **Apache License 2.0** - see the [LICENSE](LICENSE) file for details.

```
Copyright 2026 Ghislain de Labie

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

**Author**: Ghislain de Labie
**Project**: OC7-RAG - Retrieval-Augmented Generation System
**Date**: February 2026

**Academic Context**: This project was developed as part of the **OpenClassrooms AI Engineer** learning path, a master-level accredited degree program.

---

## 🙏 Acknowledgments

### Data Source
Event data provided by [OpenAgenda](https://openagenda.com/) via [OpenDataSoft](https://public.opendatasoft.com/explore/dataset/evenements-publics-openagenda/) under open data license.

### Technologies
- **LangChain** - RAG framework
- **Mistral AI** - Embeddings and LLM
- **FAISS** (Meta AI) - Vector similarity search
- **FastAPI** - Modern Python web framework
- **Docker** - Containerization

### Academic Program
Developed as part of the OpenClassrooms **AI Engineer** learning path (master-level accredited degree).

---

## 📞 Contact & Support

**Project Repository**: https://github.com/ghislaindelabie/OC7-RAG

**For issues**: See [Known Issues](docs/KNOWN_ISSUES.md) or [open an issue](https://github.com/ghislaindelabie/OC7-RAG/issues)

**Documentation**: All docs available in the `docs/` directory

---

**Made with ❤️ in the French Alps** 🏔️
