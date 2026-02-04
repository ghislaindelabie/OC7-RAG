# Claude Code Project Instructions - Puls-Events RAG

## Project Context
POC for an intelligent chatbot answering questions about cultural events in Savoie (73), Haute-Savoie (74), and Isere (38) using a RAG system (LangChain + Mistral + FAISS).

## Language Policy
- **All code, comments, documentation**: English
- **Git commits**: English, conventional commit format

## Git Rules (CRITICAL)

### What NOT to do
- NEVER mention "Claude Code", "Claude", "AI assistant" in commits/PRs
- NEVER commit directly to `main` (protected branch)
- NEVER merge PRs to `main` - user must review and merge manually
- NEVER force push or destructive operations without explicit request

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

```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

### Branch Workflow
1. Feature branches created from version branch (e.g., `v0.3.0`)
2. Features merged back to version branch via PR (can be merged by Claude)
3. Version branch merged to `main` via PR when complete
4. **IMPORTANT**: PRs to `main` must be created but NEVER merged by Claude - user reviews and merges manually
5. Tag created after merge: `v0.3.0`

## Security Guidelines (CRITICAL)

### Secret Management
- **NEVER** expose secrets (API keys, passwords, tokens) in plain text:
  - ❌ DON'T: `cat .env` (displays secrets)
  - ❌ DON'T: `echo $MISTRAL_API_KEY` (displays secret value)
  - ✅ DO: `test -f .env && echo "File exists"` (checks without displaying)
  - ✅ DO: `printenv | grep -q MISTRAL_API_KEY && echo "Key is set"` (checks without displaying value)

- **Check secret existence without exposing values**:
  ```bash
  # Good: Check if secret exists
  ssh user@server 'grep -q "MISTRAL_API_KEY" .env && echo "✓ Key configured" || echo "✗ Key missing"'

  # Good: Verify environment variable is set (without value)
  ssh user@server 'docker exec container printenv | grep -q MISTRAL_API_KEY && echo "✓ Set"'

  # Bad: Exposes the actual key value
  ssh user@server 'cat .env'  # DON'T DO THIS
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

### Server Deployment Policy

**CRITICAL**: NEVER patch code or configuration directly on production server.

**Wrong approach** ❌:
```bash
# DON'T: Direct editing on server
ssh user@server 'nano ~/app/config.py'
ssh user@server 'docker exec container sed -i "s/old/new/" /app/file.py'
```

**Correct approach** ✅:
```bash
# 1. Create hotfix branch from main
git checkout main
git pull
git checkout -b hotfix/fix-download-timeout

# 2. Make changes locally
edit src/api/rag_service.py

# 3. Test locally
docker build -t test .
docker run test

# 4. Commit and push
git add src/api/rag_service.py
git commit -m "fix: increase download timeout to 600s"
git push origin hotfix/fix-download-timeout

# 5. Create PR and merge to main (user reviews)
# 6. CI/CD automatically deploys to server
```

**Exception**: Emergency debugging only (read-only operations):
- Viewing logs: `docker compose logs`
- Checking status: `docker ps`, `curl /health`
- Testing connectivity: `curl`, `ping`

**No exceptions for**:
- Modifying code files
- Changing configuration
- Installing packages
- Editing docker-compose.yml on server

All changes MUST go through Git → PR → CI/CD pipeline.

## Code Style
- Follow existing patterns in `notebooks/01_baseline_rag.ipynb`
- Use type hints for function signatures
- Keep functions focused and small
- Prefer composition over inheritance

## API Development Guidelines (Phase 4)
- FastAPI with automatic OpenAPI docs
- Pydantic models for request/response schemas
- Async endpoints where beneficial
- Proper error handling with HTTPException
- Health check endpoint for container orchestration

## Testing Guidelines
- Test data in `tests/test_data/test_questions.csv` (56 annotated questions)
- LLM-as-Judge evaluation (PASS/PARTIAL/FAIL)
- pytest for unit tests
- Use `FakeEmbeddings` in unit tests to avoid API calls

### Test Files
- `tests/test_indexation.py` - FAISS index tests (18 tests)
- `tests/test_retriever.py` - Retriever tests (28 tests)
- `tests/test_api.py` - API endpoint tests
- `tests/conftest.py` - Shared fixtures

### Running Tests
```bash
# Unit tests (fast, no API calls)
python -m pytest tests/test_indexation.py tests/test_retriever.py -v -m "not integration"

# All tests
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ --cov=src --cov-report=term-missing
```

## Key Files Reference
- **Macro Plan**: `Documents de planification et cadrage/MACRO_PLAN.md`
- **RAG Implementation**: `notebooks/01_baseline_rag.ipynb`
- **Test Questions**: `tests/test_data/test_questions.csv`
- **Coordination**: `SESSION-COORDINATION.md`

## Session Coordination

**Note**: `SESSION-COORDINATION.md` is **not tracked in git** (listed in `.gitignore`). This avoids merge conflicts when multiple sessions work in parallel. Each session updates it locally for its own tracking.

Before starting work:
1. Read `SESSION-COORDINATION.md` for current status
2. Check which track/tasks are assigned
3. Update status when starting/completing tasks

## Environment
- Conda environment: `OC7`
- Package manager: `uv`
- Python: 3.11+
- API keys in `.env` (never commit)
