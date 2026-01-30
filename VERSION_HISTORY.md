# Version History - Puls-Events RAG

Complete changelog documenting the evolution of the RAG Cultural Events Assistant.

---

## v0.3.0 (2026-01-30) - REST API & Deployment

**Status**: ✅ Complete
**Focus**: Production-ready REST API with comprehensive testing

### 🎯 Key Features

#### REST API (FastAPI)
- ✅ `GET /health` - Service health check with detailed status
- ✅ `POST /api/v1/ask` - RAG query with 3 methods (basic, hybrid, advanced)
- ✅ `GET /api/v1/rag/info` - System information and statistics
- ✅ `POST /api/v1/rebuild` - Index rebuild with hot-swap (placeholder)
- ✅ OpenAPI documentation at `/docs` and `/redoc`

#### Error Handling & Validation
- Custom exception handlers (ValidationError, ValueError, RuntimeError, Global)
- Field-level validation with user-friendly error messages
- Input sanitization (min/max length, whitespace, repeated chars)
- Consistent `ErrorResponse` schema across all endpoints

#### Testing & Quality
- **31 API tests** (health, ask, info, rebuild, error handling)
- **18 indexation tests** (FAISS operations, document processing)
- **28 retriever tests** (basic, hybrid, advanced RAG methods)
- **Total**: 77 tests passing
- Test-Driven Development approach

#### Deployment Infrastructure
- Production server setup (hetzner3-oc7api)
- `scripts/run_api.py` for easy API launch
- `scripts/deploy.sh` for automated deployment
- GitHub Actions for CI/CD (planned)
- Comprehensive deployment documentation

### 📦 Merged Pull Requests

| PR | Title | Impact |
|----|-------|--------|
| #7 | Implement POST /ask endpoint | 13 tests, full RAG integration |
| #8 | Complete Track A with deployment | Deployment scripts, docs |
| #9 | Implement POST /rebuild endpoint | 6 tests, data download, hot-swap |
| #10 | Add comprehensive error handling | 11 tests, custom validators |
| #11 | Address Claude Review feedback | Code quality improvements |

### 🔧 Technical Improvements

**Code Quality**:
- PEP 8 compliant import organization
- Type hints throughout
- Comprehensive docstrings
- Clean separation of concerns (service, schemas, routes)

**Security**:
- Input validation on all endpoints
- Service readiness checks before processing
- Graceful error handling (no stack traces to clients)
- Environment-based configuration

**Performance**:
- Lazy loading of RAG service (singleton pattern)
- Efficient FAISS operations
- Response time tracking
- Configurable top_k parameter (1-20)

### 📚 Documentation Updates

- **README.md**: Full API section with examples
- **PHASE4_COMPLETION.md**: Comprehensive completion report
- **DEPLOYMENT_STATUS.md**: Production server status
- **DEPLOYMENT.md**: Deployment procedures
- **QUICK_START_DEPLOYMENT.md**: Quick start guide

### 🧪 Testing Highlights

**Remote Server Testing**:
- Validated on production-like environment
- All 31 API tests passing
- Python 3.12.3 compatibility confirmed

**Code Review**:
- All Claude Review feedback addressed
- Import organization fixed
- Error detection logic improved
- Test determinism ensured

---

## v0.2.0 (2026-01-26) - Evaluation Framework

**Status**: ✅ Complete
**Focus**: Comprehensive evaluation and testing

### 🎯 Key Features

#### Evaluation Framework
- **56 annotated test questions** (expanded from 18)
  - Factual: 30+ questions
  - Complex: 10+ questions
  - Off-topic: 8+ questions
  - Vague: 8+ questions
- **LLM-as-Judge** evaluation with mistral-large
- **Chain-of-Thought** reasoning for verdicts
- **Semantic Equivalence** rubric (PASS/PARTIAL/FAIL)

#### Unit Tests
- **18 indexation tests** - FAISS operations, document processing
- **28 retriever tests** - All 3 RAG methods comprehensively tested
- **FakeEmbeddings** for fast unit tests (no API calls)
- Mock-based testing patterns

#### Evaluation Results (18 questions)
| Method | PASS | PARTIAL | FAIL |
|--------|------|---------|------|
| Basic | 66.7% | 33.3% | 0.0% |
| Hybrid | 66.7% | 16.7% | 16.7% |
| Advanced | 66.7% | 11.1% | 16.7% |

**Key Finding**: Basic RAG has best robustness (no failures)

### 📦 Merged Pull Requests
- #5: Evaluation framework and expanded test dataset
- #6: Unit tests for indexation and retriever

### 📚 Documentation
- Test dataset in `tests/test_data/test_questions.csv`
- Evaluation results in `evaluation_results/`
- Updated README with evaluation section

---

## v0.1.0 (2026-01-23) - RAG Implementation

**Status**: ✅ Complete
**Focus**: Core RAG system with three methods

### 🎯 Key Features

#### Three RAG Implementations

**1. Basic RAG**
- FAISS vector similarity search
- Mistral embeddings (1024 dimensions)
- Simple and fast

**2. Hybrid RAG**
- FAISS (dense) + BM25 (sparse)
- Reciprocal Rank Fusion
- Best keyword + semantic matching

**3. Advanced RAG**
- Query Analysis (off-topic detection)
- HyDE (Hypothetical Document Embeddings)
- FAISS retrieval
- FlashRank reranking (ms-marco-MiniLM-L-12-v2)
- Highest quality results

#### Components
- **Vector Store**: FAISS with IndexFlatL2
- **LLM**: Mistral API (mistral-small-latest)
- **Embeddings**: Mistral AI (mistral-embed)
- **Framework**: LangChain
- **Data**: OpenAgenda events (Savoie, Haute-Savoie, Isère)

### 📓 Interactive Notebook
- `notebooks/01_baseline_rag.ipynb` with 31 cells
- Step-by-step implementation
- Side-by-side comparisons
- Performance metrics

### 📦 Merged Pull Request
- #1: Complete RAG implementations with notebook

---

## v0.0.1 (2026-01-16) - Foundation

**Status**: ✅ Complete
**Focus**: Project setup and data pipeline

### 🎯 Key Features

#### Data Pipeline
- **Data Source**: OpenAgenda via OpenDataSoft
- **Geographic Filter**: Departments 73, 74, 38
- **Date Filter**: Events ≥ 2023
- **8,547 events** in final dataset

#### FAISS Index
- Initial index creation
- Document preprocessing
- Text cleaning (HTML, special chars)
- Metadata extraction

#### Project Structure
- Repository setup
- Conda environment (OC7)
- Dependencies management
- .gitignore configuration

### 📂 Data Files
- `data/raw/` - Raw JSON from OpenDataSoft
- `data/processed/` - Filtered and cleaned data
- `data/index/faiss_baseline/` - FAISS vector index

---

## Next Version: v0.4.0 (Planned)

### Docker & Documentation (Track C)

**Pending**:
- Multi-stage Dockerfile
- docker-compose.yml
- Container testing
- Technical report (PDF)
- PowerPoint presentation (10-15 slides)
- Demo scenarios

---

## Statistics Summary

### Code Metrics
- **Total Tests**: 77 (31 API + 18 indexation + 28 retriever)
- **API Endpoints**: 4 (health, ask, info, rebuild)
- **RAG Methods**: 3 (basic, hybrid, advanced)
- **Test Questions**: 56 annotated questions
- **Events Indexed**: 8,547 cultural events

### Merged PRs
- **v0.0.1**: 1 PR (foundation)
- **v0.1.0**: 1 PR (RAG implementation)
- **v0.2.0**: 2 PRs (evaluation + unit tests)
- **v0.3.0**: 5 PRs (API development)
- **Total**: 9 PRs merged

### Documentation Files
- README.md - Main project documentation
- CLAUDE.md - Development guidelines
- PHASE4_COMPLETION.md - API completion report
- DEPLOYMENT.md - Deployment procedures
- DEPLOYMENT_STATUS.md - Server status
- VECTOR_STORE_MIGRATION.md - Migration guide
- VERSION_HISTORY.md - This file

---

*Last Updated: 2026-01-30*
*Project: OpenClassrooms - OC7 RAG*
