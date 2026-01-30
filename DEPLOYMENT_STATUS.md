# Deployment Status - OC7 RAG API

> **Last Updated**: 2026-01-30 12:00 CET
> **Current Status**: ✅ Production-Ready - Track A Complete

---

## Production Environment

### Server Details
- **Host**: hetzner3-oc7api (2a01:4f8:c2c:5fbe::1)
- **User**: oc7api (dedicated, minimal permissions)
- **Location**: `/home/oc7api/oc7-rag`
- **Python**: 3.12.3
- **Port**: 8000

### Current Deployment
- **PID**: 3176152
- **Status**: Running (degraded - expected)
- **Index Loaded**: No (Step 3 pending)
- **LLM Available**: Yes ✓
- **Health Check**: http://localhost:8000/health (accessible from server)

### SSH Access
```bash
# Direct connection
ssh oc7api@2a01:4f8:c2c:5fbe::1

# Via alias
ssh hetzner3-oc7api

# Check API status
ssh hetzner3-oc7api 'curl -s http://localhost:8000/health | python3 -m json.tool'

# View logs
ssh hetzner3-oc7api 'tail -f ~/oc7-rag/api.log'

# Restart API
ssh hetzner3-oc7api 'kill $(cat ~/oc7-rag/api.pid) && cd ~/oc7-rag && source venv/bin/activate && nohup python scripts/run_api.py > api.log 2>&1 & echo $! > api.pid'
```

---

## Deployment Scripts

### Manual Deployment
```bash
# Interactive
./deploy_to_server.sh hetzner3-oc7api oc7api

# Non-interactive
export DEPLOY_HOST=hetzner3-oc7api
export DEPLOY_USER=oc7api
export MISTRAL_API_KEY='your_key'
./scripts/deploy.sh
```

### CI/CD Deployment
- **Workflow**: `.github/workflows/deploy.yml`
- **Trigger**: Push to `main` branch
- **Status**: Configured (requires GitHub Secrets)
- **GitHub Secrets needed**:
  - `HETZNER_HOST`: hetzner3-oc7api
  - `HETZNER_USER`: oc7api
  - `HETZNER_SSH_KEY`: Private key content
  - `MISTRAL_API_KEY`: Mistral API key

---

## User Setup

### oc7api User
- **Created**: 2026-01-29
- **UID/GID**: 1003/1003
- **Groups**: oc7api (no sudo)
- **Home**: `/home/oc7api`
- **Shell**: `/bin/bash`
- **SSH Key**: Same as ghislain user (~/.ssh/id_ghislain)

### Security
- ✅ Minimal permissions (no sudo access)
- ✅ Cannot modify system files
- ✅ Cannot access other users' files
- ✅ Can only manage own home directory
- ✅ Can bind to ports >1024 (8000)
- ✅ Principle of least privilege

---

## Dependency Management

### Local Development
```bash
# 1. Conda for ML packages
conda env create -f environment.yml
conda activate OC7

# 2. uv for small packages
pip install uv
uv pip install -e .

# 3. Dev dependencies
uv pip install -e ".[dev]"
```

### Server (Production)
```bash
# Traditional pip + venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Files**:
- `environment.yml` - Conda packages (pandas, numpy, faiss, jupyter)
- `pyproject.toml` - uv packages (fastapi, langchain, pydantic)
- `requirements.txt` - Server deployment (all packages)

---

## API Endpoints Status

| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /health` | ✅ Working | Returns healthy (index loaded, LLM available) |
| `GET /api/v1/rag/info` | ✅ Working | Returns system info |
| `POST /api/v1/ask` | ✅ Working | RAG query with 3 methods (basic, hybrid, advanced) |
| `POST /api/v1/rebuild` | ✅ Working | Index rebuild functionality implemented |

### Health Check Response
```json
{
    "status": "healthy",
    "index_loaded": true,
    "index_size": 8547,
    "llm_available": true,
    "timestamp": "2026-01-30T11:00:00.000000+00:00"
}
```

**Status**: All endpoints fully functional. Track A - API Development complete.

---

## Testing

### Local Tests
```bash
# Run all API tests
pytest tests/test_api.py -v

# Current status: 8 passed, 5 skipped
# Passing: Health endpoint, RAG info, fixtures
# Skipped: /ask, /rebuild, error handling (not implemented yet)
```

### Server Testing
```bash
# Via SSH tunnel
ssh -L 8000:localhost:8000 hetzner3-oc7api

# Then on local machine
curl http://localhost:8000/health
curl http://localhost:8000/docs
```

---

## Known Issues

### External Access
- **Issue**: Port 8000 not accessible from outside
- **Cause**: Not firewall (UFW disabled) - likely Hetzner network/IPv6
- **Workaround**: SSH tunnel or setup nginx reverse proxy
- **Priority**: Low (API accessible from server)

### Status "degraded"
- **Issue**: Health shows "degraded"
- **Cause**: FAISS index not loaded (expected)
- **Fix**: Step 3 - implement actual RAG logic
- **Priority**: Normal development flow

---

## Track A Status: ✅ COMPLETE

### ✅ Step 1-2: API Foundation (DONE)
- [x] FastAPI structure with 4 endpoints
- [x] Pydantic schemas for validation
- [x] Singleton RAG service pattern
- [x] Development server script
- [x] Pytest fixtures and test suite

### ✅ Step 3: /ask Endpoint (DONE)
- [x] Extract RAG logic from notebook
- [x] Load FAISS index in rag_service.py
- [x] Implement POST /api/v1/ask endpoint
- [x] Write tests for /ask endpoint (13 tests)
- [x] Test locally with real queries
- [x] Deploy to oc7api user

### ✅ Step 4: /rebuild Endpoint (DONE)
- [x] Implement index rebuild logic
- [x] Download fresh data from OpenDataSoft
- [x] Filter and process events
- [x] Hot-swap index functionality
- [x] Test rebuild functionality
- [x] Deploy

### ✅ Step 5: Error Handling & Polish (DONE)
- [x] Comprehensive error handling
- [x] Code review fixes applied (14/14)
- [x] Python 3.12+ compatibility
- [x] Production-ready deployment
- [x] Documentation complete

## Next Phase: Track B - Docker Containerization

**Prerequisites**: ✅ All complete
- API fully functional
- Deployment infrastructure working
- Code review addressed
- Documentation comprehensive

**Docker Tasks**:
- [ ] Multi-stage Dockerfile
- [ ] docker-compose.yml configuration
- [ ] Volume management (FAISS index, data)
- [ ] Environment variable handling
- [ ] Container orchestration strategy
- [ ] Production deployment testing

---

## Deployment History

| Date | User | Action | Result |
|------|------|--------|--------|
| 2026-01-29 19:34 | ghislain | Initial deployment | ✅ Success |
| 2026-01-29 20:43 | oc7api | Created dedicated user | ✅ Success |
| 2026-01-29 20:47 | oc7api | First deployment | ✅ Success |
| 2026-01-29 20:48 | ghislain | Cleanup old deployment | ✅ Complete |

---

## Quick Reference

### Useful Commands
```bash
# Deploy
./deploy_to_server.sh hetzner3-oc7api oc7api

# Check API status
ssh hetzner3-oc7api 'ps aux | grep python | grep api'

# View logs (last 50 lines)
ssh hetzner3-oc7api 'tail -50 ~/oc7-rag/api.log'

# Follow logs live
ssh hetzner3-oc7api 'tail -f ~/oc7-rag/api.log'

# Stop API
ssh hetzner3-oc7api 'kill $(cat ~/oc7-rag/api.pid)'

# Get API PID
ssh hetzner3-oc7api 'cat ~/oc7-rag/api.pid'

# Check disk usage
ssh hetzner3-oc7api 'du -sh ~/oc7-rag'

# Test health endpoint
ssh hetzner3-oc7api 'curl -s localhost:8000/health'
```

### Documentation Files
- `SETUP.md` - Local + server setup instructions
- `DEPLOYMENT.md` - Deployment architecture & consistency
- `QUICK_START_DEPLOYMENT.md` - Quick guide for deployment
- `SERVER_TEST.md` - Server testing guide
- `DEPENDENCY_MANAGEMENT.md` - Dependency strategy
- `deploy_to_server.sh` - Manual deployment wrapper
- `scripts/deploy.sh` - Core deployment script
- `.github/workflows/deploy.yml` - CI/CD workflow

---

## Monitoring

### Health Checks
```bash
# Simple check
curl -f http://localhost:8000/health || echo "API down"

# Detailed check
curl -s http://localhost:8000/health | python3 -m json.tool
```

### Logs
```bash
# Recent errors
ssh hetzner3-oc7api 'grep -i error ~/oc7-rag/api.log | tail -20'

# Recent requests
ssh hetzner3-oc7api 'grep "HTTP/1.1" ~/oc7-rag/api.log | tail -20'

# API startup
ssh hetzner3-oc7api 'grep "Starting up" ~/oc7-rag/api.log'
```

---

## Rollback Procedure

If deployment fails:

1. **Check logs**:
   ```bash
   ssh hetzner3-oc7api 'tail -50 ~/oc7-rag/api.log'
   ```

2. **Stop broken API**:
   ```bash
   ssh hetzner3-oc7api 'kill $(cat ~/oc7-rag/api.pid) 2>/dev/null'
   ```

3. **Redeploy previous version**:
   ```bash
   # Checkout previous commit locally
   git checkout <previous-commit>

   # Deploy
   ./deploy_to_server.sh hetzner3-oc7api oc7api
   ```

4. **Or restore from backup** (if you created one):
   ```bash
   ssh hetzner3-oc7api 'mv ~/oc7-rag.backup ~/oc7-rag'
   ```

---

## Contact & Support

- **User**: Ghislain
- **Server Admin**: Ghislain (via root@2a01:4f8:c2c:5fbe::1)
- **API User**: oc7api (dedicated, no sudo)
- **Documentation**: This file + other docs in project root
