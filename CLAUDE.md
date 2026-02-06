# Claude Code Project Instructions - Puls-Events RAG

## Project Context
POC for an intelligent chatbot answering questions about cultural events in Savoie (73), Haute-Savoie (74), and Isère (38) using a RAG system (LangChain + Mistral + FAISS).

## Language Policy
- **All code, comments, documentation**: English
- **Git commits**: English, conventional commit format

## Git Rules (CRITICAL)

### What NOT to do
- NEVER mention "Claude Code", "Claude", "AI assistant" in commits/PRs
- NEVER commit directly to `main` (protected branch)
- NEVER merge PRs to `main` - user must review and merge manually
- NEVER force push or destructive operations without explicit request
- NEVER use `git add -A` or `git add .` — stage specific files by name

### Branching Strategy
```
main (protected)
  └── v{X}.{Y}.{Z} (version branch)
        └── feature/{description}
```

### Commit Format
```
<type>: <short description>

[optional body]

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

### Branch Workflow
1. Feature branches created from version branch (e.g., `v1.2.0`)
2. Features merged back to version branch via PR (can be merged by Claude)
3. Version branch merged to `main` via PR when complete
4. **IMPORTANT**: PRs to `main` must be created but NEVER merged by Claude - user reviews and merges manually
5. Tag created after merge: `v1.2.0`

## Production Server Rules (CRITICAL)

### Never disrupt production
- **NEVER stop, restart, or modify production containers** without explicit user permission
- **NEVER deploy or run heavy operations** on the server without checking RAM first (`free -m`)
- Production server has **3.7GB RAM** — memory-intensive operations (FlashRank reranking, index rebuild) can exhaust it
- Before any server operation, verify available memory: `ssh root@server 'free -m'`

### Server Deployment Policy
- **NEVER patch code or configuration directly on production server**
- All changes MUST go through Git → PR → CI/CD pipeline
- **Exception**: Emergency debugging (read-only operations only):
  - Viewing logs: `docker compose logs`
  - Checking status: `docker ps`, `curl /health`, `free -m`
  - Testing connectivity: `curl`, `ping`
- **No exceptions for**: modifying code, changing config, installing packages, editing docker-compose.yml on server

### Server Access
- SSH: `ssh root@<server-ip>` (use root; oc7api SSH key not available)
- Production: `/home/oc7api/oc7-rag-docker/` on port 8000
- Hetzner Cloud Firewall controls port access (not UFW)
- After heavy Docker operations, clean up: `docker system prune`, check `df -h`

## Security Guidelines (CRITICAL)

### Secret Management
- **NEVER** expose secrets (API keys, passwords, tokens) in plain text:
  - ❌ DON'T: `cat .env` (displays secrets)
  - ❌ DON'T: `echo $MISTRAL_API_KEY` (displays secret value)
  - ✅ DO: `test -f .env && echo "File exists"` (checks without displaying)
  - ✅ DO: `printenv | grep -q MISTRAL_API_KEY && echo "Key is set"` (checks without displaying value)

- **Check secret existence without exposing values**:
  ```bash
  ssh user@server 'grep -q "MISTRAL_API_KEY" .env && echo "✓ Key configured" || echo "✗ Key missing"'
  ```

- **If a secret is accidentally exposed**:
  1. Immediately inform the user
  2. Mark the secret as compromised
  3. Provide rotation instructions
  4. Document in project (e.g., `docs/KNOWN_ISSUES.md`)

### Environment Variables
- Secrets stored in `.env` files (NEVER commit to git)
- `.env` is in `.gitignore` - verify before any git operations
- GitHub Actions secrets managed via repository Settings → Secrets
- Container secrets passed via docker-compose `env_file` or `environment`

## Code Style
- Follow existing patterns in codebase
- Use type hints for function signatures
- Keep functions focused and small
- Prefer composition over inheritance

## API Development Guidelines
- FastAPI with automatic OpenAPI docs
- Pydantic models for request/response schemas
- Async endpoints where beneficial
- Proper error handling with HTTPException
- Health check endpoint for container orchestration

## Testing Guidelines
- Test data in `tests/test_data/test_questions.csv` (64 annotated questions)
- LLM-as-Judge evaluation (PASS/PARTIAL/FAIL) via `scripts/run_evaluation_api.py`
- pytest for unit tests
- Use `FakeEmbeddings` in unit tests to avoid API calls
- Run tests before every commit: `python -m pytest tests/ -v -m "not integration"`

### Test Files
- `tests/test_indexation.py` - FAISS index + temporal pipeline tests (74 tests)
- `tests/test_retriever.py` - Retriever tests (28 tests)
- `tests/test_api.py` - API endpoint tests (39 tests)
- `tests/conftest.py` - Shared fixtures

### Running Tests
```bash
# Activate environment first
source /opt/anaconda3/etc/profile.d/conda.sh && conda activate OC7

# Unit tests (fast, no API calls)
python -m pytest tests/ -v -m "not integration"

# With coverage
python -m pytest tests/ --cov=src --cov-report=term-missing
```

## Evaluation
- **Script**: `scripts/run_evaluation_api.py` — calls production API + LLM-as-Judge
- **Judge model**: mistral-large-latest (temperature=0)
- **RAG model**: mistral-small-latest
- **Results**: `evaluation_results/` directory (CSV, JSON, summary)
- **Run on server** (where .env has MISTRAL_API_KEY):
  ```bash
  python3 run_evaluation_api.py --api-url http://localhost:8000 --methods basic,hybrid
  ```

## Key Files Reference
- **RAG Service**: `src/api/rag_service.py` — main RAG service, all retrieval/generation logic
- **API Schemas**: `src/api/schemas.py` — Pydantic models
- **API Endpoints**: `src/api/main.py` — FastAPI app
- **Web UI**: `src/api/static/index.html` — chat interface
- **Test Fixtures**: `tests/conftest.py` — API test fixtures (mock RAG service)
- **Test Questions**: `tests/test_data/test_questions.csv` — 64 annotated evaluation questions
- **Evaluation Script**: `scripts/run_evaluation_api.py` — API-based evaluation
- **Known Issues**: `docs/KNOWN_ISSUES.md` — bugs, improvements, future tasks
- **Technical Report**: `docs/technical_report.md`

## Session Coordination

**Note**: `SESSION-COORDINATION.md` is **not tracked in git** (listed in `.gitignore`). This avoids merge conflicts when multiple sessions work in parallel.

Before starting work:
1. Read `SESSION-COORDINATION.md` for current status
2. Check which track/tasks are assigned
3. Update status when starting/completing tasks

## Environment
- Conda environment: `OC7` (Python 3.12)
- Package manager: `uv`
- API keys in `.env` (never commit)
- Activate: `source /opt/anaconda3/etc/profile.d/conda.sh && conda activate OC7`
