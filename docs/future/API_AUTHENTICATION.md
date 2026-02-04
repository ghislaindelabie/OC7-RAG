# API Authentication Documentation

## Current Security Status

### Local Development
- API binds to `0.0.0.0:8000` but only accessible from local machine
- Protected by OS-level firewall and network configuration
- **No authentication required** for local testing

### Server Deployment (Current)
- API runs on `hetzner3-oc7api:8000`
- Port 8000 **NOT publicly accessible** from internet
- Access **only via SSH tunnel**: `ssh -L 8000:localhost:8000 hetzner3-oc7api`
- **Secured by SSH key authentication**
- This is the current production setup and is secure

### Why Add Authentication?

Currently NOT needed because SSH tunnel provides security. However, authentication becomes necessary if:

1. **Exposing via nginx** - Setting up public HTTPS endpoint
2. **Sharing with others** - Allowing access without SSH keys
3. **Rate limiting** - Tracking usage per user/client
4. **Logging/Analytics** - Identifying request sources
5. **Production best practice** - Defense in depth

---

## Option 1: Simple API Key Authentication (Recommended)

### Overview

- **Complexity**: Low (5-10 minutes implementation)
- **Standard**: HTTP Header-based (`X-API-Key`)
- **Flexibility**: Optional (can run without key for development)
- **Security**: Sufficient for internal/trusted use

### Implementation

#### 1. Update `src/api/main.py`

**Add imports:**
```python
from fastapi import Header, HTTPException, Depends
import os
```

**Add authentication dependency (after app creation, before routes):**
```python
# ============================================================================
# Authentication
# ============================================================================

# Load API key from environment
API_KEY = os.getenv("RAG_API_KEY")

async def verify_api_key(x_api_key: str = Header(None)):
    """
    Verify API key from X-API-Key header.

    If RAG_API_KEY is not set, authentication is disabled (for development).
    If set, all protected endpoints require matching X-API-Key header.

    Raises:
        HTTPException: 401 if API key is invalid or missing
    """
    # Skip auth if API key not configured
    if not API_KEY:
        return

    # Check if key provided
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required. Provide X-API-Key header."
        )

    # Verify key matches
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
```

**Add dependency to protected endpoints:**

```python
@app.post(
    "/api/v1/ask",
    response_model=AnswerResponse,
    tags=["RAG"],
    summary="Ask a question about cultural events",
    dependencies=[Depends(verify_api_key)]  # ADD THIS LINE
)
async def ask_question(request: QuestionRequest):
    # ... existing code unchanged


@app.post(
    "/api/v1/rebuild",
    response_model=RebuildResponse,
    tags=["Admin"],
    summary="Rebuild the FAISS index",
    dependencies=[Depends(verify_api_key)]  # ADD THIS LINE
)
async def rebuild_index(request: RebuildRequest):
    # ... existing code unchanged
```

**Leave public endpoints unprotected:**
- `GET /` - Chat interface (public)
- `GET /health` - Health check (public)
- `GET /api/v1/rag/info` - System info (public)
- `GET /docs` - API documentation (public)

#### 2. Set Environment Variable

**Development (.env file):**
```bash
# Optional: leave commented out to disable auth in development
# RAG_API_KEY=dev-secret-key-12345
```

**Production (server):**
```bash
# Generate secure key (example):
# python3 -c "import secrets; print(secrets.token_urlsafe(32))"

export RAG_API_KEY="your-secure-random-key-here"
```

**In deployment script:**
```bash
# scripts/run_api.py or systemd service file
# Ensure RAG_API_KEY is set before starting API
```

#### 3. Update Client Code

**Chat Interface (src/api/static/index.html):**

Add API key input or fetch from config:

```javascript
// Option A: Add input field for users to enter key
<input type="password" id="apiKeyInput" placeholder="API Key (optional)">

// Option B: Hardcode for trusted users (not recommended)
const API_KEY = "your-key-here";

// Update sendQuestion function:
async function sendQuestion() {
    const question = questionInput.value.trim();
    if (!question) return;

    const headers = {
        'Content-Type': 'application/json',
    };

    // Add API key if configured
    const apiKey = document.getElementById('apiKeyInput')?.value;
    if (apiKey) {
        headers['X-API-Key'] = apiKey;
    }

    const response = await fetch('/api/v1/ask', {
        method: 'POST',
        headers: headers,
        body: JSON.stringify({
            question: question,
            rag_method: methodSelector.value,
            top_k: 5
        })
    });

    // Handle 401 errors
    if (response.status === 401) {
        addMessage('Erreur: Clé API invalide ou manquante', false);
        return;
    }

    // ... rest of code
}
```

**Python Client:**
```python
import requests

API_KEY = "your-key-here"

response = requests.post(
    "http://server:8000/api/v1/ask",
    headers={"X-API-Key": API_KEY},
    json={
        "question": "Quels concerts à Chambéry?",
        "rag_method": "hybrid",
        "top_k": 5
    }
)
```

**curl:**
```bash
curl -X POST http://server:8000/api/v1/ask \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key-here" \
  -d '{"question": "Quels concerts?", "rag_method": "hybrid", "top_k": 5}'
```

---

## Testing

### Test Authentication Enabled

```bash
# Set API key
export RAG_API_KEY="test-key-12345"

# Start API
python scripts/run_api.py

# Test without key (should fail)
curl http://localhost:8000/api/v1/ask -d '{...}'
# Expected: 401 Unauthorized

# Test with wrong key (should fail)
curl -H "X-API-Key: wrong-key" http://localhost:8000/api/v1/ask -d '{...}'
# Expected: 401 Unauthorized

# Test with correct key (should work)
curl -H "X-API-Key: test-key-12345" http://localhost:8000/api/v1/ask -d '{...}'
# Expected: 200 OK

# Test public endpoints still work
curl http://localhost:8000/health
# Expected: 200 OK (no key required)
```

### Test Authentication Disabled

```bash
# Don't set RAG_API_KEY
unset RAG_API_KEY

# Start API
python scripts/run_api.py

# Test without key (should work)
curl http://localhost:8000/api/v1/ask -d '{...}'
# Expected: 200 OK (auth disabled for development)
```

---

## Deployment Considerations

### 1. Generate Secure Keys

```bash
# Python method (recommended)
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Output example: xJ8kP_mNq2vL9wR3hT6yU4zA1sD5fG7bK0cV8nM2xQ4

# OpenSSL method
openssl rand -base64 32
```

### 2. Store Keys Securely

**DO NOT:**
- ❌ Commit keys to git
- ❌ Hardcode in source code
- ❌ Share in plain text (email, Slack)
- ❌ Store in logs

**DO:**
- ✅ Use environment variables
- ✅ Add to `.gitignore` (`.env` file)
- ✅ Use secrets management (GitHub Secrets for CI/CD)
- ✅ Rotate keys periodically
- ✅ Use different keys for dev/staging/prod

### 3. nginx Configuration (if exposing publicly)

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # Pass API key header
        proxy_set_header X-API-Key $http_x_api_key;
    }

    # Optional: Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20;
}
```

### 4. Rate Limiting (Additional Layer)

Consider adding FastAPI middleware for rate limiting:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/api/v1/ask")
@limiter.limit("10/minute")  # 10 requests per minute per IP
async def ask_question(request: QuestionRequest):
    # ...
```

---

## Alternative Authentication Options

### Option 2: HTTP Basic Auth

**Pros:** Browser support, simpler for some clients
**Cons:** Less flexible, sends credentials with every request

```python
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets

security = HTTPBasic()

async def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, "admin")
    correct_password = secrets.compare_digest(credentials.password, os.getenv("API_PASSWORD", ""))
    if not (correct_username and correct_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
```

### Option 3: JWT Tokens

**Pros:** Stateless, can include claims, expiration
**Cons:** More complex, requires token management

```python
from fastapi.security import HTTPBearer
from jose import JWTError, jwt

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### Option 4: OAuth2/OpenID Connect

**Pros:** Industry standard, supports multiple providers
**Cons:** Significant complexity, requires auth server

Not recommended for simple internal API.

---

## Security Best Practices

### 1. HTTPS Only in Production

```python
# Force HTTPS in production
if os.getenv("ENVIRONMENT") == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["your-domain.com"]
    )
```

### 2. CORS Configuration

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend-domain.com"],  # Specific domain, not "*"
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["X-API-Key"],
)
```

### 3. Input Validation

Already implemented via Pydantic schemas. Continue this practice.

### 4. Logging (Don't Log API Keys)

```python
# Good: Log requests without sensitive headers
logger.info(f"Request from {request.client.host} to {request.url.path}")

# Bad: Don't log API keys
# logger.info(f"Headers: {request.headers}")  # Contains X-API-Key!
```

### 5. Error Messages

```python
# Good: Generic error
raise HTTPException(status_code=401, detail="Invalid API key")

# Bad: Leak information
# raise HTTPException(status_code=401, detail="API key abc123 not found in database")
```

---

## Migration Path

### Phase 1: Current (No Auth)
- SSH tunnel only
- Secure enough for current use
- **Status: ✅ Active**

### Phase 2: Add API Key (Optional)
- Implement Option 1
- Keep auth disabled by default (no RAG_API_KEY set)
- Test thoroughly
- **Status: 📋 Documented (this file)**

### Phase 3: Enable in Production
- Generate secure API key
- Set RAG_API_KEY on server
- Update clients to send key
- Monitor logs for 401 errors
- **Status: 🔜 Future**

### Phase 4: Public HTTPS (Optional)
- Set up nginx reverse proxy
- Configure SSL/TLS certificate (Let's Encrypt)
- Enable rate limiting
- Update DNS
- **Status: 🔜 Future (if needed)**

---

## FAQ

**Q: Should I enable auth now?**
A: No, not needed. SSH tunnel is secure. Enable only when making API publicly accessible.

**Q: How do I rotate API keys?**
A:
1. Generate new key
2. Update RAG_API_KEY on server
3. Update all clients
4. Restart API
5. Old key becomes invalid

**Q: Can I have multiple API keys?**
A: Current implementation supports one key. For multiple keys, maintain a list:

```python
VALID_KEYS = os.getenv("RAG_API_KEYS", "").split(",")

async def verify_api_key(x_api_key: str = Header(None)):
    if not VALID_KEYS or VALID_KEYS == [""]:
        return
    if x_api_key not in VALID_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")
```

**Q: What about the chat interface?**
A: Keep it public (no auth required). Users enter API key in the interface to make queries.

**Q: Is this production-ready?**
A: For internal/trusted use, yes. For public internet, also add:
- HTTPS (nginx + Let's Encrypt)
- Rate limiting
- Monitoring/alerting
- Regular key rotation

---

## Related Documentation

- **CHATBOT_INTERFACE.md** - Chat interface architecture
- **DEPLOYMENT_STATUS.md** - Current deployment status
- **SETUP.md** - Environment setup
- **.claude/settings.json** - Security settings and denied operations

---

## Implementation Checklist

When ready to implement:

- [ ] Update `src/api/main.py` with auth code
- [ ] Add tests for authentication in `tests/test_api.py`
- [ ] Update chat interface to handle API keys
- [ ] Generate production API key
- [ ] Document key in secure location (password manager)
- [ ] Add RAG_API_KEY to `.env.example` (not `.env`)
- [ ] Update deployment scripts to pass API key
- [ ] Test with key enabled
- [ ] Test with key disabled
- [ ] Update API documentation (`/docs`)
- [ ] Update client examples in README

---

**Status**: 📋 Documented - Ready for implementation when needed
**Last Updated**: 2026-01-30
**Author**: Development Team
