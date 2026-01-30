# Dependency Management Guide - OC7 RAG API

## Current Setup Analysis

### Local Development (macOS)
- **Environment**: Anaconda base (Python 3.12.7)
- **Package Manager**: pip (not using conda environment OC7 yet!)
- **Dependency Files**: 
  - `pyproject.toml` - Project metadata + dependencies
  - `requirements.txt` - Traditional format for deployment

### Installed Packages (Verified)
```
✓ fastapi==0.128.0
✓ uvicorn==0.40.0
✓ pydantic==2.12.5
✓ pytest==9.0.2
✓ pytest-asyncio==1.3.0
✓ httpx==0.28.1
✓ faiss-cpu==1.12.0
✓ langchain (already installed)
```

## Dependency Management Approaches

### Option 1: requirements.txt (Traditional - Good for Server)
**Current file**: `requirements.txt`

**Pros:**
- ✅ Universal - works everywhere
- ✅ Simple pip install -r requirements.txt
- ✅ Easy to version control
- ✅ Good for Docker/server deployment

**Cons:**
- ❌ No automatic version resolution
- ❌ Manual updates needed
- ❌ Can have conflicting versions

**Use for:**
- Hetzner server deployment
- Docker containers
- CI/CD pipelines

### Option 2: pyproject.toml (Modern - Good for Development)
**Current file**: `pyproject.toml`

**Pros:**
- ✅ Modern Python standard (PEP 621)
- ✅ Single source of truth
- ✅ Works with pip, uv, poetry
- ✅ Includes dev dependencies separately

**Cons:**
- ❌ Requires pip >= 21.3 or compatible tool
- ❌ Not all deployment tools support it yet

**Use for:**
- Local development
- Package distribution
- Modern workflows

### Option 3: Conda environment.yml (For Conda Users)
**Not currently used, but could add**

**Pros:**
- ✅ Reproducible environments
- ✅ Handles non-Python dependencies
- ✅ Good for data science projects

**Cons:**
- ❌ Slower than pip
- ❌ Not suitable for Docker/server
- ❌ Larger environments

## Recommended Workflow

### For Local Development
```bash
# Option A: Use conda environment (recommended for consistency)
conda activate OC7
pip install -e .  # Installs from pyproject.toml

# Option B: Use pip directly
pip install -r requirements.txt
```

### For Server Deployment (Hetzner)
```bash
# On server
git clone <repo>
cd OC7-RAG
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start API
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

### For Docker (Future)
```dockerfile
FROM python:3.11-slim
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# ... rest of Dockerfile
```

## Current Issues & Fixes Needed

### Issue 1: Not Using Conda Environment
**Problem:** Running in Anaconda base instead of OC7 env
**Fix:**
```bash
conda activate OC7
pip install fastapi uvicorn pydantic pytest pytest-asyncio httpx
```

### Issue 2: Dependency Conflict Warning
**Warning:** `wsproto requires h11<1,>=0.16.0, but you have h11 0.14.0`
**Impact:** Low - not critical for our API
**Fix (if needed):**
```bash
pip install --upgrade h11
```

### Issue 3: requirements.txt vs pyproject.toml Sync
**Problem:** Need to keep both in sync
**Fix:** Generate requirements.txt from pyproject.toml:
```bash
pip install pip-tools
pip-compile pyproject.toml -o requirements.txt
```

## Server Deployment Checklist

### Prerequisites
- [ ] Python 3.11+ on Hetzner server
- [ ] Git access to repository
- [ ] MISTRAL_API_KEY environment variable
- [ ] (Optional) Supabase database credentials

### Deployment Steps
1. **Clone repository**
   ```bash
   git clone <repo-url>
   cd OC7-RAG
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set environment variables**
   ```bash
   export MISTRAL_API_KEY="your-key-here"
   ```

5. **Test locally on server**
   ```bash
   python scripts/run_api.py
   # Or with uvicorn directly
   uvicorn src.api.main:app --host 0.0.0.0 --port 8000
   ```

6. **Access from outside**
   ```bash
   # From your local machine
   curl http://<server-ip>:8000/health
   ```

## When to Test on Server?

### ✅ Ready to Test Now (Recommended)
**Why:**
- Basic API structure working locally
- Health endpoint functional
- Dependencies clearly defined
- Can verify server environment early

**What to test:**
1. Health endpoint: `GET /health`
2. RAG info endpoint: `GET /api/v1/rag/info`
3. Dependency installation
4. Server environment compatibility

**Benefits:**
- Catch deployment issues early
- Verify Python version compatibility
- Test network/firewall setup
- Validate requirements.txt completeness

### 🔄 Can Wait Until Step 3 Complete
**Why:**
- No functional RAG queries yet (placeholder)
- Can't test core functionality
- More meaningful to test with working /ask endpoint

**When to do full deployment:**
- After Step 3 (POST /ask implemented)
- After extracting RAG logic from notebook
- When we have actual queries to test

## Recommendation

**Do a quick server test NOW to:**
1. Verify environment setup
2. Test dependency installation
3. Check health endpoints work
4. Identify any server-specific issues

**Then continue development locally and do full deployment after Step 3.**

## Test Commands for Server

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start API
python scripts/run_api.py

# 3. Test from another terminal/machine
curl http://localhost:8000/health | python -m json.tool
curl http://localhost:8000/api/v1/rag/info | python -m json.tool
curl http://localhost:8000/docs  # Should show Swagger UI HTML
```

