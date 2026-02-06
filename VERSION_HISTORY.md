# Version History - Puls-Events RAG

Complete changelog documenting the evolution of the RAG Cultural Events Assistant.

---

## v1.2.0 (2026-02-05) - Temporal Awareness

**Status**: ✅ Complete
**Focus**: Temporal intelligence — date filtering, proximity reranking, query analysis

### 🎯 Key Features

#### ISO Date Metadata (Feature 1)
- Parse `firstdate_begin` and `lastdate_end` into ISO `event_start_date`, `event_end_date`
- Add `event_year`, `event_month` convenience fields
- Graceful handling of missing/malformed dates

#### Reference Date API (Feature 2)
- `reference_date` parameter on `/api/v1/ask` (ISO YYYY-MM-DD, default `2024-02-06`)
- Temporal prompt instructions: "Date du jour", past event warning, weekend interpretation
- `_format_date_french()` for natural French date display in prompts

#### Manual Pipeline (Feature 3)
- Replace `RetrievalQA` chains with explicit retrieve-then-generate pipeline
- `top_k` now honestly controls retrieval (was cosmetic before)
- `fetch_k = top_k * 10` for date filtering headroom
- `_filter_past_events()` removes events ending before reference_date

#### Enhanced Query Analysis (Feature 4)
- Advanced method: LLM-based off-topic detection + temporal window extraction
- `_filter_temporal_window()` with overlap logic and empty-result safeguard
- Basic/Hybrid unaffected (no extra LLM call)

#### Temporal Proximity Reranking (Feature 5)
- Exponential decay: `score = 0.5 ^ (|days_away| / 14)`
- Events closer to target date rank first; no-date events pushed to end
- All 3 methods benefit (lightweight sort, no LLM call)

#### Temporal Evaluation Questions (Feature 6)
- 12 data-driven temporal questions (replacing 4 generic ones)
- Based on real events around reference date 2024-02-06
- Categories: weekend, demain, ce soir, month, season, past reference, combination

### 📊 Test Coverage
- **145 tests** (74 indexation + 39 API + 28 retriever + 4 integration/skipped)
- 62 new tests added across Features 1-5

### 📦 Commits on v1.2.0 branch
- `feat: add ISO date metadata to event indexing (Feature 1)`
- `feat: add reference_date parameter and temporal prompt (Feature 2)`
- `feat: replace RetrievalQA chains with manual retrieve-then-generate pipeline (Feature 3)`
- `feat: add enhanced query analysis and temporal window filter for advanced method (Feature 4)`
- `feat: add temporal proximity reranking for all RAG methods (Feature 5)`
- `feat: add temporal evaluation questions and update docs (Feature 6)`

---

## v1.1.0 (2026-02-05) - Developer Experience Enhancements

**Status**: ✅ Complete
**Focus**: Developer tooling, documentation, and code quality

### 🎯 Key Features

#### Developer Tools
- **Makefile** with 26 commands (`make test`, `make docker-up`, `make clean`, etc.)
- **Setup verification script** (`scripts/verify_setup.py`) — validates environment before running
- **API test script** (`scripts/test_api.sh`) — quick validation of API deployment

#### Documentation
- **Demo scenarios** (`docs/DEMO_SCENARIOS.md`) — 10 example queries with expected responses
- **Troubleshooting guide** (`docs/TROUBLESHOOTING.md`) — 17 common issues with solutions
- **Enhancement plan** (`docs/V1.0_ENHANCEMENT_PLAN.md`) — roadmap for future improvements

#### Code Quality
- Code formatted with **black** (7 files reformatted)
- GitHub badges added to README (CI/CD status, test count)

### 📦 Merged Pull Request

| PR | Title | Impact |
|----|-------|--------|
| #24 | Release v1.1: Developer Experience Enhancements | Makefile, scripts, docs, formatting |

---

## v1.0.0 (2026-02-05) - Production-Ready Release

**Status**: ✅ Complete
**Focus**: README overhaul, public-facing documentation, license

### 🎯 Key Features

- **Complete README rewrite** — architecture diagram, quick start guides, usage examples
- **Apache License 2.0** added
- **Live deployment URLs** documented (Hetzner Cloud)
- **Known Issues** guide (`docs/KNOWN_ISSUES.md`)
- **HTTPS setup guide** (`docs/HTTPS_SETUP.md`)

### 📦 Merged Pull Requests

| PR | Title | Impact |
|----|-------|--------|
| #23 | Prepare README for v1.0.0 release | Full README rewrite, license |
| #21 | Add HTTPS setup guide | Future SSL documentation |

---

## v0.4.1 (2026-02-04) - Hotfix: Auto-rebuild Timeout

**Status**: ✅ Complete
**Focus**: Fix auto-rebuild timeout with API-level data filtering

### 🎯 Key Fix

- **API-level filtering**: Data download now filters by department at the API level instead of downloading the full French dataset and filtering locally
- **Timeout fix**: Reduces download from ~72 MB (all France) to ~3 MB (target departments only)
- **Faster startup**: Container first-start time reduced from 5+ minutes to ~2 minutes

### 📦 Merged Pull Request

| PR | Title | Impact |
|----|-------|--------|
| #20 | Hotfix v0.4.1: Fix auto-rebuild timeout | API-level filtering, faster startup |

---

## v0.4.0 (2026-01-30 / 2026-02-04) - Docker, CI/CD & Documentation

**Status**: ✅ Complete
**Focus**: Docker containerization, CI/CD pipeline, web interface, technical report

### 🎯 Key Features

#### Docker Containerization
- **Multi-stage Dockerfile** — optimized image (1.45 GB)
- **docker-compose.yml** — local/dev deployment
- **docker-compose.prod.yml** — production deployment (GHCR)
- **.dockerignore** — excludes raw data, notebooks, tests
- **Non-root user** — security best practice
- **Health checks** — container orchestration ready

#### CI/CD Pipeline
- **GitHub Actions workflow** (`deploy.yml`) — test → build → push → deploy
- **Automated deployment** on push to `main`
- **GitHub Container Registry** (GHCR) for image hosting
- **SSH deploy** to Hetzner production server

#### Auto-Rebuild Feature
- Container downloads data from OpenDataSoft on first start
- Builds FAISS index automatically (~2-3 min)
- Data persisted in Docker volume for subsequent restarts
- Controlled by `AUTO_REBUILD_INDEX` env var

#### Web Chat Interface
- Modern web UI at `GET /`
- Support for all 3 RAG methods
- Source document display with links
- Health status indicator
- Responsive mobile layout
- Vanilla JavaScript (zero dependencies)

#### Technical Report
- 15-page comprehensive documentation (`docs/technical_report.md`)
- Covers architecture, implementation, evaluation, deployment
- PDF conversion helper script

#### Documentation Organization
- Docs reorganized into `docs/archive/`, `docs/reference/`, `docs/future/`
- Root directory cleaned up (6 essential files only)

### 📦 Merged Pull Requests

| PR | Title | Impact |
|----|-------|--------|
| #16 | Add web-based chat interface | Vanilla JS chat UI |
| #17 | Docker containerization with CI/CD | Dockerfile, compose, deploy.yml |
| #18 | Release v0.4.0: Docker CI/CD + Web Chat | Initial release merge |
| #19 | Fix: Auto-rebuild FAISS index on startup | Auto-rebuild, volume persistence |
| #22 | Release v0.4.0: Complete with Technical Documentation | Technical report, docs cleanup |

### 🔧 Technical Details

- **Docker**: 29.1.3 + Compose v5.0.0 on server
- **Image**: `ghcr.io/ghislaindelabie/oc7-rag-api:latest`
- **Server**: Hetzner Cloud VPS, dedicated `oc7api` user
- **GitHub Secrets**: HETZNER_HOST, HETZNER_USER, HETZNER_SSH_KEY, MISTRAL_API_KEY

---

## v0.3.0 (2026-01-30) - REST API & Deployment

**Status**: ✅ Complete
**Focus**: Production-ready REST API with comprehensive testing

### 🎯 Key Features

#### REST API (FastAPI)
- ✅ `GET /health` — Service health check with detailed status
- ✅ `POST /api/v1/ask` — RAG query with 3 methods (basic, hybrid, advanced)
- ✅ `GET /api/v1/rag/info` — System information and statistics
- ✅ `POST /api/v1/rebuild` — Index rebuild with hot-swap
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
- Comprehensive deployment documentation

### 📦 Merged Pull Requests

| PR | Title | Impact |
|----|-------|--------|
| #7 | Implement POST /ask endpoint | 13 tests, full RAG integration |
| #8 | Complete Track A with deployment | Deployment scripts, docs |
| #9 | Implement POST /rebuild endpoint | 6 tests, data download, hot-swap |
| #10 | Add comprehensive error handling | 11 tests, custom validators |
| #11 | Address code review feedback | Code quality improvements |
| #14 | Comprehensive documentation update | v0.3.0 docs |
| #15 | Release v0.3.0 | Merge to main |

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
- **18 indexation tests** — FAISS operations, document processing
- **28 retriever tests** — All 3 RAG methods comprehensively tested
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

| PR | Title | Impact |
|----|-------|--------|
| #2 | Release v0.2.0: Evaluation Framework | Merge to main |
| #5 | Evaluation framework and expanded test dataset | 56 questions, LLM-as-Judge |
| #6 | Unit tests for indexation and retriever | 46 tests |

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

| PR | Title | Impact |
|----|-------|--------|
| #1 | Phase 3: Three RAG Implementations | Complete RAG system |

---

## v0.0.1 (2026-01-16) - Foundation

**Status**: ✅ Complete
**Focus**: Project setup and data pipeline

### 🎯 Key Features

#### Data Pipeline
- **Data Source**: OpenAgenda via OpenDataSoft
- **Geographic Filter**: Departments 73, 74, 38
- **Date Filter**: Events ≥ 2023
- **8,547 events** in initial dataset

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
- `data/raw/` — Raw JSON from OpenDataSoft
- `data/processed/` — Filtered and cleaned data
- `data/index/faiss_baseline/` — FAISS vector index

---

## Statistics Summary

### Code Metrics (as of v1.2.0)
- **Total Tests**: 145 (74 indexation + 39 API + 28 retriever + 4 integration/skipped)
- **API Endpoints**: 4 (health, ask, info, rebuild)
- **RAG Methods**: 3 (basic, hybrid, advanced)
- **Test Questions**: 64 annotated questions (12 temporal)
- **Events Indexed**: ~8,500 cultural events
- **Docker Image**: 1.45 GB (multi-stage build)
- **Makefile Commands**: 26

### Merged PRs

| Version | PRs | Highlights |
|---------|-----|------------|
| v0.0.1 | — | Foundation (initial commit) |
| v0.1.0 | #1 | RAG implementation |
| v0.2.0 | #2, #5, #6 | Evaluation + unit tests |
| v0.3.0 | #7-#11, #14, #15 | REST API + deployment |
| v0.4.0 | #16-#19, #22 | Docker, CI/CD, chat UI, technical report |
| v0.4.1 | #20 | Hotfix: API-level filtering |
| v1.0.0 | #21, #23 | README, license, public docs |
| v1.1.0 | #24 | Developer experience |
| v1.2.0 | TBD | Temporal awareness |
| **Total** | **24+ PRs merged** | |

### Technology Stack
- **Language**: Python 3.11+
- **LLM**: Mistral API (mistral-small-latest)
- **Embeddings**: Mistral AI (mistral-embed, 1024 dim)
- **Vector Store**: FAISS (IndexFlatL2)
- **Sparse Retrieval**: BM25 (rank_bm25)
- **Reranking**: FlashRank (ms-marco-MiniLM-L-12-v2)
- **API**: FastAPI + Uvicorn
- **Containerization**: Docker + Docker Compose
- **CI/CD**: GitHub Actions
- **Testing**: pytest
- **Evaluation**: LLM-as-Judge (mistral-large)
- **License**: Apache License 2.0

---

*Last Updated: 2026-02-06*
*Project: OpenClassrooms - OC7 RAG*
