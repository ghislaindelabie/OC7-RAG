# Troubleshooting Guide - OC7-RAG

**Last Updated**: 2026-02-05
**Version**: v1.1

This guide covers common issues and their solutions. If your issue isn't listed here, check [Known Issues](KNOWN_ISSUES.md) or [open an issue](https://github.com/ghislaindelabie/OC7-RAG/issues).

---

## Table of Contents

1. [Setup & Installation Issues](#setup--installation-issues)
2. [API Runtime Issues](#api-runtime-issues)
3. [Docker Issues](#docker-issues)
4. [FAISS Index Issues](#faiss-index-issues)
5. [Performance Issues](#performance-issues)
6. [Data Issues](#data-issues)

---

## Setup & Installation Issues

### Issue 1: "MISTRAL_API_KEY not set"

**Symptom**:
```
ERROR: MISTRAL_API_KEY environment variable not set
```

**Solution**:
1. Check `.env` file exists:
   ```bash
   ls -la .env
   ```

2. Verify file format (check without exposing the key):
   ```bash
   grep -q "MISTRAL_API_KEY=" .env && echo "Key found" || echo "Key missing"
   ```

3. Check key format (no spaces, no quotes):
   ```
   ✅ Correct: MISTRAL_API_KEY=abc123xyz
   ❌ Wrong:   MISTRAL_API_KEY = abc123xyz  (spaces)
   ❌ Wrong:   MISTRAL_API_KEY="abc123xyz" (quotes)
   ```

4. Restart API after changes:
   ```bash
   # Local
   python scripts/run_api.py

   # Docker
   docker compose restart api
   ```

---

### Issue 2: "ModuleNotFoundError: No module named 'langchain'"

**Symptom**:
```
ModuleNotFoundError: No module named 'langchain'
```

**Cause**: Dependencies not installed or wrong Python environment

**Solution**:
1. Activate correct environment:
   ```bash
   # If using conda
   conda activate OC7

   # If using venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Verify installation:
   ```bash
   python -c "import langchain; print('OK')"
   ```

---

### Issue 3: Python version too old

**Symptom**:
```
SyntaxError: invalid syntax (pattern matching requires Python 3.10+)
```

**Cause**: Python version < 3.11

**Solution**:
1. Check Python version:
   ```bash
   python --version  # Should be 3.11 or higher
   ```

2. Install Python 3.11+:
   ```bash
   # Using conda
   conda create -n OC7 python=3.11
   conda activate OC7

   # Using pyenv
   pyenv install 3.11.8
   pyenv local 3.11.8
   ```

---

## API Runtime Issues

### Issue 4: "503 Service Unavailable" on /api/v1/ask

**Symptom**:
```json
{
  "detail": "RAG service not available: Index not loaded"
}
```

**Cause**: FAISS index not loaded yet

**Solution**:

**Option A: Wait for auto-rebuild** (first startup only)
```bash
# Check logs
docker compose logs -f api

# Look for:
# "Auto-rebuilding FAISS index..."
# "Index built successfully"

# This takes 3-5 minutes on first run
```

**Option B: Manual rebuild**
```bash
curl -X POST http://localhost:8000/api/v1/rebuild
```

**Option C: Check index exists**
```bash
ls data/index/faiss_baseline/index.faiss

# If missing, trigger rebuild or check data files
```

---

### Issue 5: API starts but /health returns unhealthy

**Symptom**:
```json
{
  "status": "unhealthy",
  "index_loaded": false,
  "llm_available": true
}
```

**Cause**: FAISS index failed to load

**Solution**:
1. Check logs for errors:
   ```bash
   docker compose logs api | grep -i error
   ```

2. Check index directory:
   ```bash
   ls -lh data/index/faiss_baseline/
   # Should contain: index.faiss, index.pkl
   ```

3. If index is corrupted, rebuild:
   ```bash
   rm -rf data/index/faiss_baseline/*
   curl -X POST http://localhost:8000/api/v1/rebuild
   ```

---

### Issue 6: "Connection refused" when calling API

**Symptom**:
```
curl: (7) Failed to connect to localhost port 8000: Connection refused
```

**Cause**: API not running

**Solution**:
1. Check if API is running:
   ```bash
   # Local
   ps aux | grep run_api.py

   # Docker
   docker compose ps
   ```

2. Start API:
   ```bash
   # Local
   python scripts/run_api.py

   # Docker
   docker compose up -d
   ```

3. Check port not already in use:
   ```bash
   lsof -i :8000  # Shows what's using port 8000
   ```

---

## Docker Issues

### Issue 7: "docker: command not found"

**Symptom**:
```bash
$ docker compose up
docker: command not found
```

**Solution**:
1. Install Docker: https://docs.docker.com/get-docker/

2. Verify installation:
   ```bash
   docker --version
   docker compose version
   ```

3. Check Docker is running:
   ```bash
   docker ps  # Should not error
   ```

---

### Issue 8: "permission denied" when running Docker

**Symptom**:
```
permission denied while trying to connect to the Docker daemon socket
```

**Solution**:

**Linux**:
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Log out and back in, then verify
docker ps
```

**Mac/Windows**: Docker Desktop should handle permissions automatically

---

### Issue 9: Container exits immediately after starting

**Symptom**:
```bash
$ docker compose ps
NAME    STATUS
api     Exited (1) 2 seconds ago
```

**Solution**:
1. Check container logs:
   ```bash
   docker compose logs api
   ```

2. Common causes:
   - Missing `.env` file → Create from `.env.example`
   - Invalid `MISTRAL_API_KEY` → Check key in `.env`
   - Port already in use → Change port in `docker-compose.yml`

3. Try interactive mode to see errors:
   ```bash
   docker compose run --rm api python scripts/run_api.py
   ```

---

### Issue 10: "No space left on device"

**Symptom**:
```
ERROR: failed to create shim: OCI runtime create failed
no space left on device
```

**Solution**:
1. Clean up Docker:
   ```bash
   docker system prune -a  # Remove unused images, containers
   docker volume prune     # Remove unused volumes
   ```

2. Check disk space:
   ```bash
   df -h
   ```

3. Free up space if needed:
   ```bash
   # Remove old build artifacts
   make clean

   # Remove __pycache__ and .pyc files
   find . -type d -name __pycache__ -exec rm -rf {} +
   ```

---

## FAISS Index Issues

### Issue 11: Index build hangs during data download

**Symptom**:
API logs show "Downloading data..." but hangs for > 5 minutes

**Cause**: Network issue or large data download

**Solution**:
1. Check network connectivity:
   ```bash
   curl -I https://public.opendatasoft.com
   ```

2. Try manual download:
   ```bash
   python scripts/download_data.py
   ```

3. If still fails, check firewall/proxy settings

4. See [KNOWN_ISSUES.md](KNOWN_ISSUES.md) for download optimization details

---

### Issue 12: "RuntimeError: FAISS index has wrong dimensions"

**Symptom**:
```
RuntimeError: FAISS index has wrong dimensions (expected 1024, got 768)
```

**Cause**: Index built with different embedding model

**Solution**:
Rebuild index from scratch:
```bash
rm -rf data/index/faiss_baseline/*
curl -X POST http://localhost:8000/api/v1/rebuild
```

---

### Issue 13: Index rebuild takes too long (> 10 minutes)

**Symptom**:
Rebuild hangs or takes extremely long

**Solution**:
1. Check data size:
   ```bash
   du -sh data/processed/events_filtered.json
   # Should be ~70MB
   ```

2. Check system resources:
   ```bash
   top  # Check CPU/memory usage
   ```

3. If data is too large, filter first:
   ```bash
   python scripts/filter_data.py
   ```

4. For large datasets, consider batch processing (see docs/future/)

---

## Performance Issues

### Issue 14: API responses are very slow (> 10 seconds)

**Symptom**:
Queries take longer than expected

**Diagnosis**:
```bash
# Check response time
time curl -X POST http://localhost:8000/api/v1/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Concerts à Annecy?"}'
```

**Solutions**:

**A. Use faster RAG method**:
```json
{
  "question": "...",
  "rag_method": "basic"  // Fastest (vs hybrid or advanced)
}
```

**B. Check system resources**:
```bash
# CPU/Memory usage
docker stats api

# If high, consider increasing resources
# Edit docker-compose.yml:
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 4G
```

**C. Check if embedding cache is working**:
Look for repeated slow responses for same query - should be faster on second try.

---

### Issue 15: High memory usage

**Symptom**:
```
OOMKilled: container killed due to out-of-memory
```

**Solution**:
1. Increase Docker memory limit:
   ```yaml
   # docker-compose.yml
   services:
     api:
       deploy:
         resources:
           limits:
             memory: 4G  # Increase from default
   ```

2. Or use smaller model (trade-off: accuracy vs memory):
   Update `src/api/rag_service.py` to use smaller embedding model

3. Reduce batch size for indexing (if building custom index)

---

## Data Issues

### Issue 16: "No events found" for valid queries

**Symptom**:
API returns "Je n'ai pas trouvé d'événements..." for queries that should have results

**Diagnosis**:
1. Check index has data:
   ```bash
   curl http://localhost:8000/api/v1/rag/info | jq '.index_info.documents_count'
   # Should be > 10000
   ```

2. Check event dates:
   ```bash
   # Events might be outdated
   curl http://localhost:8000/api/v1/rag/info | jq '.index_info.last_updated'
   ```

**Solution**:
Rebuild with fresh data:
```bash
curl -X POST http://localhost:8000/api/v1/rebuild
```

---

### Issue 17: Wrong events returned (wrong location/date)

**Symptom**:
API returns events from wrong department or wrong time period

**Cause**: Query not specific enough or RAG method not optimal

**Solution**:
1. Make query more specific:
   ```
   ❌ Vague: "Concerts ce weekend?"
   ✅ Better: "Concerts à Chambéry ce weekend?"
   ```

2. Try different RAG method:
   ```json
   {
     "question": "...",
     "rag_method": "advanced"  // Better for complex queries
   }
   ```

3. Check if events exist in database:
   ```bash
   # Check what's in the index
   curl http://localhost:8000/api/v1/rag/info
   ```

---

## Getting More Help

### Enable Debug Logging

**Local**:
```bash
export LOG_LEVEL=DEBUG
python scripts/run_api.py
```

**Docker**:
```yaml
# .env
LOG_LEVEL=DEBUG
```

Then restart and check logs:
```bash
docker compose restart api
docker compose logs -f api
```

### Check System Status

Run verification script:
```bash
python scripts/verify_setup.py
```

### Test API

Run test script:
```bash
bash scripts/test_api.sh
```

### Still Having Issues?

1. Check [KNOWN_ISSUES.md](KNOWN_ISSUES.md) for documented problems
2. Review logs carefully:
   ```bash
   docker compose logs api | grep -i error
   ```
3. Open an issue: https://github.com/ghislaindelabie/OC7-RAG/issues
   - Include error messages
   - Include steps to reproduce
   - Include environment details (OS, Python version, Docker version)

---

## Quick Reference

### Useful Commands

```bash
# Check setup
python scripts/verify_setup.py

# Test API
bash scripts/test_api.sh

# View logs
docker compose logs -f api

# Restart API
docker compose restart api

# Rebuild index
curl -X POST http://localhost:8000/api/v1/rebuild

# Check health
curl http://localhost:8000/health | jq

# Clean Docker
docker system prune -a

# Clean Python cache
make clean
```

### Common File Locations

- **Config**: `.env` (create from `.env.example`)
- **Logs**: `docker compose logs api`
- **Index**: `data/index/faiss_baseline/`
- **Data**: `data/processed/events_filtered.json`
- **Tests**: `tests/`

### Getting Help Quickly

1. Run `make verify` to check setup
2. Run `make test-api` to test endpoints
3. Check logs: `docker compose logs api`
4. Try rebuild: `curl -X POST http://localhost:8000/api/v1/rebuild`
5. Check docs: `README.md`, `KNOWN_ISSUES.md`, `DEPLOYMENT_STATUS.md`

---

**Last Resort**: If all else fails, try a fresh start:
```bash
docker compose down -v  # Remove volumes
rm -rf data/index/*     # Remove index
docker compose up -d    # Start fresh
```

This will trigger a complete rebuild from scratch.
