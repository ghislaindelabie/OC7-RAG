# Macro Plan - Puls-Events RAG Project
## AI Assistant for Cultural Event Recommendations

---

## 0. Project Guidelines

### Language Policy
- **All code comments**: English
- **All documentation**: English
- **Git commit messages**: English
- **Variable/function names**: English

### Git Policy
- **IMPORTANT**: Do NOT mention "Claude Code", "Claude", "AI assistant", or any AI tool in commit messages, PR descriptions, or any versioned documentation
- Commit messages should describe the changes made, not how they were made
- Example of what NOT to do: "Added feature X with help from Claude"
- Example of correct commit: "Add event filtering by department"

### Git Branching Strategy

```
main (protected - merge only via PR)
  │
  ├── v0.0.1 (version branch)
  │     ├── feature/data-exploration
  │     ├── feature/rag-baseline
  │     └── feature/api-endpoints
  │
  ├── v0.1.0 (version branch)
  │     ├── feature/hybrid-rag
  │     └── feature/evaluation-pipeline
  │
  └── hotfix/critical-bug (from main, merged back to main + version branches)
```

#### Branch Types

| Branch Type | Naming Convention | Created From | Merged Into | Purpose |
|-------------|-------------------|--------------|-------------|---------|
| **main** | `main` | - | - | Production-ready code, protected |
| **version** | `v{major}.{minor}.{patch}` | `main` | `main` (via PR) | Development for a specific version |
| **feature** | `feature/{description}` | version branch | version branch | New features or enhancements |
| **hotfix** | `hotfix/{description}` | `main` | `main` + active version branches | Critical bug fixes |

#### Workflow Rules

1. **main branch**:
   - Protected: no direct commits
   - Only accepts merges via Pull Requests
   - Requires at least 1 approval (when working in team)
   - All tests must pass before merge

2. **Version branches** (e.g., `v0.0.1`, `v0.1.0`):
   - Created from `main` at the start of a new version cycle
   - Feature branches are merged here
   - When version is complete and tested, PR to `main`
   - Tag created on `main` after merge: `v0.0.1`, `v0.1.0`, etc.

3. **Feature branches**:
   - Created from the current version branch
   - Use descriptive names: `feature/add-bm25-retriever`
   - Merged back to version branch via PR (can be more relaxed)
   - Delete after merge

4. **Hotfix branches**:
   - Created from `main` for critical production fixes
   - Merged to `main` via PR
   - Cherry-picked or merged to active version branches

#### Commit Message Convention

```
<type>: <short description>

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```
feat: Add BM25 retriever for hybrid search
fix: Handle missing date fields in event data
docs: Update README with installation instructions
test: Add unit tests for FAISS indexing
```

---

## 1. Project Overview

**Objective**: Develop a POC for an intelligent chatbot capable of answering user questions about cultural events in Savoie (73), Haute-Savoie (74), and Isère (38), based on a RAG system.

**Expected Deliverables**:
- Functional RAG system (LangChain + Mistral + FAISS)
- REST API with FastAPI exposing `/ask` and `/rebuild` endpoints
- Annotated test dataset (question/answer pairs as ground truth)
- Unit tests + automated evaluation metrics
- Docker containerization
- Technical report + PowerPoint presentation (10-15 slides)

---

## 2. Answers to Your Specific Questions

### 2.1 API vs Bulk Download - Recommendation: **Bulk Download JSON**

| Criterion | API | Bulk Download |
|-----------|-----|---------------|
| Data volume | Pagination required | Complete download |
| Geographic filtering | Via ODSQL `where` clause | Local post-filtering |
| Reproducibility | Depends on API availability | Versionable file |
| Simplicity | More complex | Simpler |

**Recommendation**: Download as **JSON** via bulk export with geographic filter.

**Why JSON over CSV/GeoJSON**:
- **JSON**: Hierarchical structure preserved, better for multivalued fields (keywords, accessibility), native Python parsing
- **CSV**: Loses nested field structure, potential encoding issues
- **GeoJSON**: Useful for map visualization, but heavier and geo-oriented structure

**Export URL with department filter**:
```
https://public.opendatasoft.com/api/explore/v2.1/catalog/datasets/evenements-publics-openagenda/exports/json?where=location_department IN ('Savoie', 'Haute-Savoie', 'Isère')&limit=-1
```

**Available geographic fields**: `location_department`, `location_region`, `location_city`, `location_postalcode`, `location_coordinates`

### 2.2 Notebook vs Scripts

**Recommendation**: Hybrid approach

| Phase | Tool | Justification |
|-------|------|---------------|
| Data exploration | **Notebook** | Visualization, rapid iteration |
| RAG prototyping | **Notebook** | Interactive testing, debugging |
| Production code | **Python Scripts** | Modularity, testing, Docker |

**Suggested structure**:
```
notebooks/
  01_data_exploration.ipynb
  02_chunking_experiments.ipynb
  03_rag_prototyping.ipynb
src/
  data/
  rag/
  api/
```

### 2.3 RAG Architectures to Investigate (from simplest to most advanced)

#### Level 1: Naive RAG (Mandatory baseline)
```
Query → Embedding → FAISS Search → Top-K docs → LLM → Response
```
- Fixed chunking (400-512 tokens)
- Embedding: `sentence-transformers/all-MiniLM-L6-v2` or Mistral embeddings
- FAISS IndexFlatL2

#### Level 2: Hybrid RAG (Recommended for production)
```
Query → [BM25 + Vector Search] → RRF Fusion → Rerank → LLM → Response
```
- Add BM25 for lexical search (place names, artists)
- Reciprocal Rank Fusion to combine results
- LangChain `EnsembleRetriever`

#### Level 3: Advanced RAG (For quality improvement)
```
Query → Query Rewriting → Hybrid Search → Cross-Encoder Rerank → LLM → Self-Reflection
```
Options to explore:
- **HyDE**: Generate hypothetical document before embedding (useful for short queries)
- **Multi-Query**: Generate 3-5 query reformulations
- **Reranking**: Cross-encoder (`ms-marco-MiniLM-L-6-v2`) on top-50 → top-5

#### Level 4: Agentic/Corrective RAG (If time permits)
```
Query → Retrieve → Grade Documents → [Web Search if low quality] → Generate → Self-Critique
```
- **CRAG** (Corrective RAG): Verifies document quality before generation
- **Self-RAG**: Self-evaluation of generated response
- Implementation via **LangGraph** for state machine

**Recommendation**: Start with Level 1, implement Level 2 as the main target, document Level 3 experiments in the report.

### 2.4 Recommended Chunking Strategies

| Strategy | Use Case | Implementation |
|----------|----------|----------------|
| **Fixed-size** (baseline) | Short/standard events | `RecursiveCharacterTextSplitter(chunk_size=400, overlap=50)` |
| **Semantic** | Long varied descriptions | LangChain `SemanticChunker` |
| **Per event** | One chunk = one event | Custom splitter |

**Recommendation for this project**: **One chunk per event** seems most suitable because:
- Each event is a coherent unit
- Metadata (date, location) must stay associated with description
- Generally reasonable size (< 512 tokens)

### 2.5 Test Dataset Creation

#### Method 1: Manual creation (mandatory for ground truth)
- 20-30 typical questions covering different cases:
  - Factual questions: "What concerts are happening in Annecy this weekend?"
  - Recommendation questions: "What family activities are there in Grenoble?"
  - Complex questions: "Are there any free jazz festivals in Savoie this summer?"
- Manually annotate reference answers

#### Method 2: Synthetic generation with LLM (RAGAS)
```python
from ragas.testset import TestsetGenerator
from ragas.testset.evolutions import simple, reasoning, multi_context

generator = TestsetGenerator.from_langchain(
    generator_llm=ChatMistral(model="mistral-large"),
    critic_llm=ChatMistral(model="mistral-large"),
    embeddings=HuggingFaceEmbeddings()
)

testset = generator.generate_with_langchain_docs(
    documents=event_docs,
    test_size=100,
    distributions={simple: 0.5, reasoning: 0.3, multi_context: 0.2}
)
```

**Generated question types**:
- **Simple**: Direct questions about a single event
- **Reasoning**: Questions requiring inference
- **Multi-context**: Questions requiring multiple events

### 2.6 LLM-as-Judge for Evaluation

#### Automated RAGAS Metrics
```python
from ragas import evaluate
from ragas.metrics import (
    faithfulness,      # Is response faithful to context?
    answer_relevancy,  # Is response relevant to question?
    context_precision, # Are retrieved docs relevant?
    context_recall     # Were all necessary docs retrieved?
)

results = evaluate(
    dataset=test_dataset,
    metrics=[faithfulness, answer_relevancy, context_precision, context_recall]
)
```

#### Custom LLM-as-Judge
```python
judge_prompt = """
Evaluate the following response on a scale of 1-5:

Question: {question}
Retrieved context: {context}
Generated response: {response}
Reference answer: {reference}

Criteria:
1. Faithfulness: Is the response based on the provided context?
2. Relevance: Does the response answer the question?
3. Completeness: Are all important pieces of information present?
4. Factual accuracy: Are dates, locations, names correct?

Reason step by step before giving your score.
"""
```

**LLM-as-Judge best practices**:
- Use Chain-of-Thought (reasoning before score)
- Scale 1-4 rather than 1-5 (avoids middle bias)
- Calibrate with human annotations (10-20 examples)

---

## 3. Macro Plan by Phases

### Phase 1: Setup & Exploration (Week 1)

#### 1.1 Environment Configuration
- [ ] Create conda environment `OC7`
- [ ] Initialize project with `uv init`
- [ ] Configure `pyproject.toml` with dependencies
- [ ] Create `.env` for API keys (Mistral)
- [ ] Create appropriate `.gitignore`
- [ ] Initialize Git repository

**Main dependencies**:
```toml
[project]
dependencies = [
    "langchain>=0.3",
    "langchain-community",
    "langchain-mistralai",
    "faiss-cpu",
    "sentence-transformers",
    "pandas",
    "fastapi",
    "uvicorn",
    "httpx",
    "python-dotenv",
    "ragas",
    "pytest",
]
```

#### 1.2 Data Acquisition and Exploration
- [ ] Download Open Agenda data (JSON filtered for 73/74/38)
- [ ] Exploration notebook: structure, fields, quality
- [ ] Statistics: event count, temporal/geographic distribution
- [ ] Identify useful fields for RAG

### Phase 2: Preprocessing & Indexing (Week 2)

#### 2.1 Preprocessing Pipeline
- [ ] Data cleaning script
- [ ] Handle missing values
- [ ] Date normalization (filter < 1 year)
- [ ] Build text for vectorization (title + description + location + date)

#### 2.2 Chunking and Vectorization
- [ ] Implement chunking (1 event = 1 chunk with metadata)
- [ ] Choose embedding model (quick benchmark)
- [ ] FAISS index creation script
- [ ] Index save/load functionality

### Phase 3: Core RAG System (Week 3)

#### 3.1 Baseline RAG (Naive)
- [ ] LangChain + FAISS integration
- [ ] Mistral API configuration
- [ ] Prompt engineering for cultural event responses
- [ ] Interactive manual testing

#### 3.2 Hybrid RAG (improvement)
- [ ] Add BM25 retriever
- [ ] Implement EnsembleRetriever
- [ ] Comparative tests baseline vs hybrid

#### 3.3 Advanced Experiments (optional)
- [ ] Query rewriting
- [ ] Reranking with cross-encoder
- [ ] Document results

### Phase 4: FastAPI API (Week 4)

#### 4.1 API Development
- [ ] FastAPI project structure
- [ ] `POST /ask` endpoint (question → response)
- [ ] `POST /rebuild` endpoint (index reconstruction)
- [ ] `GET /health` endpoint (status)
- [ ] Error handling
- [ ] Automatic Swagger documentation

#### 4.2 API Testing
- [ ] Endpoint unit tests
- [ ] `api_test.py` script
- [ ] Basic load tests

### Phase 5: Evaluation & Testing (Week 5)

#### 5.1 Test Dataset Creation
- [ ] 20-30 manually annotated questions
- [ ] RAGAS synthetic generation (50-100 questions)
- [ ] Cross-validation manual/synthetic

#### 5.2 Evaluation Pipeline
- [ ] `evaluate_rag.py` script with RAGAS metrics
- [ ] LLM-as-Judge for qualitative evaluation
- [ ] Automated metrics report
- [ ] Unit tests for indexing

### Phase 6: Containerization & Documentation (Week 6)

#### 6.1 Docker
- [ ] Multi-stage Dockerfile
- [ ] docker-compose.yml (optional)
- [ ] Index build script
- [ ] Local container testing

#### 6.2 Documentation
- [ ] Complete README.md
- [ ] Technical report (PDF)
- [ ] PowerPoint presentation (10-15 slides)

#### 6.3 Demo Preparation
- [ ] 2-3 demonstration scenarios
- [ ] Functional local version without internet
- [ ] Presentation rehearsal

---

## 4. Recommended Project Structure

```
OC7-RAG/
├── .env                          # Environment variables (not versioned)
├── .gitignore
├── pyproject.toml                # UV dependencies
├── README.md
├── Dockerfile
├── docker-compose.yml
│
├── data/
│   ├── raw/                      # Raw Open Agenda data
│   ├── processed/                # Cleaned data
│   └── index/                    # Saved FAISS index
│
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   ├── 02_chunking_experiments.ipynb
│   ├── 03_rag_prototyping.ipynb
│   └── 04_evaluation_analysis.ipynb
│
├── src/
│   ├── __init__.py
│   ├── config.py                 # Centralized configuration
│   ├── data/
│   │   ├── __init__.py
│   │   ├── loader.py             # Data loading
│   │   └── preprocessor.py       # Cleaning and chunking
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── embeddings.py         # Embedding models
│   │   ├── retriever.py          # Retrievers (FAISS, BM25, Hybrid)
│   │   ├── chain.py              # LangChain RAG chain
│   │   └── index_builder.py      # Index construction
│   └── api/
│       ├── __init__.py
│       ├── main.py               # FastAPI app
│       ├── routes.py             # Endpoints
│       └── schemas.py            # Pydantic models
│
├── tests/
│   ├── __init__.py
│   ├── test_data/
│   │   └── test_questions.json   # Annotated test dataset
│   ├── test_indexation.py
│   ├── test_retriever.py
│   ├── test_api.py
│   └── evaluate_rag.py           # RAGAS evaluation
│
├── scripts/
│   ├── download_data.py          # Open Agenda download
│   ├── build_index.py            # FAISS index construction
│   └── run_evaluation.py         # Run evaluation
│
└── docs/
    ├── technical_report.pdf
    └── presentation.pptx
```

---

## 5. Final Tech Stack

| Component | Technology |
|-----------|------------|
| Environment | Conda `OC7` + UV |
| Language | Python 3.11+ |
| RAG Orchestration | LangChain |
| LLM | Mistral API (mistral-small or mistral-large) |
| Embeddings | HuggingFace `sentence-transformers` or Mistral embeddings |
| Vector Store | FAISS (faiss-cpu) |
| Lexical Search | BM25 (rank-bm25 or LangChain BM25Retriever) |
| API | FastAPI + Uvicorn |
| Evaluation | RAGAS + pytest |
| Containerization | Docker |
| Versioning | Git + GitHub |

---

## 6. Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Insufficient Open Agenda data for the zone | Medium | High | Verify volume before starting, expand zone if needed |
| Poor RAG response quality | Medium | High | Iterate on prompting, test hybrid RAG |
| API response time too long | Low | Medium | Optimize FAISS, caching, reduce top-k |
| Mistral API costs | Low | Low | Use mistral-small for dev, large for eval |

---

## 7. Success Criteria

- [ ] FAISS index built with > 1000 events from target zone
- [ ] API responds in < 5 seconds
- [ ] RAGAS faithfulness score > 0.7
- [ ] RAGAS answer_relevancy score > 0.7
- [ ] Test dataset with 50+ annotated questions
- [ ] Functional Docker container
- [ ] Complete documentation

---

## 8. Immediate Next Steps

1. **Validate this plan** with you
2. **Configure environment** conda + UV
3. **Download and explore data** from Open Agenda for the 3 departments
4. **Verify data volume** available (target > 1000 events)

---

## Sources and References

- [OpenDataSoft Explore API v2.1](https://help.opendatasoft.com/apis/ods-explore-v2/)
- [Dataset evenements-publics-openagenda](https://public.opendatasoft.com/explore/dataset/evenements-publics-openagenda/)
- [LangChain Documentation](https://python.langchain.com/docs/)
- [RAGAS Documentation](https://docs.ragas.io/en/stable/)
- [FAISS Documentation](https://faiss.ai/)
- [Mistral AI Platform](https://console.mistral.ai/)
- [LangGraph Self-RAG Tutorial](https://langchain-ai.github.io/langgraph/tutorials/rag/langgraph_self_rag/)
- [Hybrid Search Best Practices](https://superlinked.com/vectorhub/articles/optimizing-rag-with-hybrid-search-reranking)
