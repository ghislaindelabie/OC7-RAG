# Deployment Status - OC7 RAG API

> **Last Updated**: 2026-01-30 17:30 CET
> **Current Status**: ✅ v0.4.0 - Docker CI/CD + Web Chat Interface

---

## Production Environment

### Server Details
- **Host**: hetzner3-oc7api (2a01:4f8:c2c:5fbe::1)
- **User**: oc7api (dedicated, minimal permissions)
- **Location**: `/home/oc7api/oc7-rag-docker`
- **Python**: 3.12.3
- **Docker**: 29.1.3 + Compose v5.0.0
- **Port**: 8000

### Current Deployment
- **Method**: Docker container (manual deployment tested)
- **Image**: oc7-rag-api:latest (1.45GB)
- **Status**: Running, healthy
- **Index Loaded**: Yes ✓
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

### Docker Deployment (NEW in v0.4.0)
```bash
# Manual Docker deployment
cd ~/oc7-rag-docker
docker compose up -d
docker compose logs -f

# Using production compose (pulls from GHCR)
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

### CI/CD Deployment
- **Workflow**: `.github/workflows/deploy.yml`
- **Trigger**: Push to `main` branch
- **Status**: Configured and ready
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
- **Groups**: oc7api, docker
- **Home**: `/home/oc7api`
- **Shell**: `/bin/bash`
- **SSH Key**: Same as ghislain user (~/.ssh/id_ghislain)

### Security
- ✅ Minimal permissions (no sudo access)
- ✅ Cannot modify system files
- ✅ Cannot access other users' files
- ✅ Can only manage own home directory
- ✅ Can bind to ports >1024 (8000)
- ✅ Docker group access for container management
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
| `GET /` | ✅ Working | **NEW** Web chat interface |
| `GET /health` | ✅ Working | Returns healthy (index loaded, LLM available) |
| `GET /api/v1/rag/info` | ✅ Working | Returns system info |
| `POST /api/v1/ask` | ✅ Working | RAG query with 3 methods (basic, hybrid, advanced) |
| `POST /api/v1/rebuild` | ✅ Working | Index rebuild functionality implemented |

### Health Check Response
```json
{
    "status": "healthy",
    "index_loaded": true,
    "index_size": 8542,
    "llm_available": true,
    "timestamp": "2026-01-30T16:37:53.093122+00:00"
}
```

**Status**: All endpoints fully functional. v0.4.0 complete.

---

## Testing

### Local Tests
```bash
# Run all API tests
pytest tests/test_api.py -v

# Current status: 31+ tests passing
```

### Server Testing
```bash
# Via SSH tunnel
ssh -L 8000:localhost:8000 hetzner3-oc7api

# Then on local machine
curl http://localhost:8000/health
curl http://localhost:8000/docs
open http://localhost:8000  # Chat interface
```

---

## Known Issues

### External Access
- **Issue**: Port 8000 not accessible from outside
- **Cause**: Not firewall (UFW disabled) - likely Hetzner network/IPv6
- **Workaround**: SSH tunnel or setup nginx reverse proxy
- **Priority**: Low (API accessible from server)

---

## Version Status: v0.4.0 ✅ COMPLETE

### ✅ Track A: API Development (DONE)
- [x] FastAPI structure with 5 endpoints
- [x] Pydantic schemas for validation
- [x] Singleton RAG service pattern
- [x] POST /api/v1/ask with 3 RAG methods
- [x] POST /api/v1/rebuild with data download
- [x] Comprehensive error handling
- [x] 31+ tests passing

### ✅ Track B: Evaluation & Testing (DONE)
- [x] 56 annotated test questions
- [x] LLM-as-Judge evaluation
- [x] Unit tests (indexation + retriever)

### ✅ Track C: Docker & CI/CD (DONE)
- [x] Multi-stage Dockerfile (1.45GB image)
- [x] docker-compose.yml (local/dev)
- [x] docker-compose.prod.yml (production/GHCR)
- [x] .dockerignore (optimized build context)
- [x] CI/CD workflow (test → build → push → deploy)
- [x] Docker installed on server
- [x] Manual deployment tested

### ✅ Track D: Web Chat Interface (DONE)
- [x] Modern web UI at GET /
- [x] Support for 3 RAG methods
- [x] Source document display
- [x] Health status indicator
- [x] Responsive mobile layout

### ⏳ Remaining Tasks
- [ ] Technical report (PDF)
- [ ] PowerPoint presentation
- [ ] Demo scenarios

---

## Deployment History

| Date | User | Action | Result |
|------|------|--------|--------|
| 2026-01-29 19:34 | ghislain | Initial deployment | ✅ Success |
| 2026-01-29 20:43 | oc7api | Created dedicated user | ✅ Success |
| 2026-01-29 20:47 | oc7api | First deployment | ✅ Success |
| 2026-01-29 20:48 | ghislain | Cleanup old deployment | ✅ Complete |
| 2026-01-30 16:37 | oc7api | Docker container deployment | ✅ Success |

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

# Docker commands
ssh hetzner3-oc7api 'sg docker "docker ps"'
ssh hetzner3-oc7api 'cd ~/oc7-rag-docker && sg docker "docker compose logs --tail=50"'
```

### Documentation Files
- `SETUP.md` - Local + server setup instructions
- `DEPLOYMENT.md` - Deployment architecture & consistency
- `QUICK_START_DEPLOYMENT.md` - Quick guide for deployment
- `SERVER_TEST.md` - Server testing guide
- `DEPENDENCY_MANAGEMENT.md` - Dependency strategy
- `CHATBOT_INTERFACE.md` - Web chat interface guide
- `API_AUTHENTICATION.md` - Future authentication guide
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

# Docker logs
ssh hetzner3-oc7api 'cd ~/oc7-rag-docker && sg docker "docker compose logs --tail=100"'
```

---

## Rollback Procedure

If deployment fails:

1. **Check logs**:
   ```bash
   ssh hetzner3-oc7api 'tail -50 ~/oc7-rag/api.log'
   # Or for Docker:
   ssh hetzner3-oc7api 'cd ~/oc7-rag-docker && sg docker "docker compose logs --tail=50"'
   ```

2. **Stop broken API**:
   ```bash
   ssh hetzner3-oc7api 'kill $(cat ~/oc7-rag/api.pid) 2>/dev/null'
   # Or for Docker:
   ssh hetzner3-oc7api 'cd ~/oc7-rag-docker && sg docker "docker compose down"'
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
