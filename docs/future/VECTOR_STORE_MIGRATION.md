# Vector Store Migration Guide

> **Context**: This project currently uses FAISS with pickle serialization for the vector store. While acceptable for a POC with controlled data, migrating to a safer alternative is recommended for production or if handling untrusted indices.

---

## Current Implementation (FAISS)

**Files:**
- `data/index/faiss_baseline/index.faiss` - Vector index (binary)
- `data/index/faiss_baseline/index.pkl` - Document store (pickle) ⚠️

**Security consideration:**
- Pickle deserialization can execute arbitrary code
- Safe in our context (we control the index source)
- See `src/api/rag_service.py:214-220` for documentation

---

## Recommended Migration: FAISS → Chroma

### Why Chroma?

| Aspect | FAISS | Chroma |
|--------|-------|--------|
| Serialization | Pickle (⚠️ security risk) | SQLite (✅ safe) |
| Deployment | File-based | File-based OR server |
| Code changes | N/A | Minimal (~10 lines) |
| Performance | Excellent | Very good |
| Migration time | N/A | ~30 minutes |

### Migration Steps

#### 1. Install Chroma

```bash
conda activate OC7
pip install chromadb
```

#### 2. Update `src/api/rag_service.py`

**Change imports:**
```python
# Before
from langchain_community.vectorstores import FAISS

# After
from langchain_community.vectorstores import Chroma
```

**Update initialization (lines ~214-225):**
```python
# Before
if self.index_path.exists():
    logger.info(f"Loading FAISS index from {self.index_path}")
    self.vectorstore = FAISS.load_local(
        str(self.index_path),
        self.embeddings,
        allow_dangerous_deserialization=True  # ← No longer needed!
    )

# After
if self.index_path.exists():
    logger.info(f"Loading Chroma index from {self.index_path}")
    self.vectorstore = Chroma(
        persist_directory=str(self.index_path),
        embedding_function=self.embeddings
    )
```

**Update index creation (if building new index):**
```python
# Before
self.vectorstore = FAISS.from_documents(documents, embeddings)
INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
vectorstore.save_local(str(INDEX_PATH))

# After
self.vectorstore = Chroma.from_documents(
    documents,
    embeddings,
    persist_directory=str(INDEX_PATH)
)
# No need for save_local - auto-persists!
```

#### 3. Update Configuration

```python
# Update index path in rag_service.py
self.index_path = self.project_root / "data" / "index" / "chroma_baseline"
```

#### 4. Rebuild Index

```bash
# Option 1: Use existing script (if you have one)
python scripts/build_index.py --vectorstore chroma

# Option 2: Rebuild via API (if POST /rebuild is implemented)
curl -X POST http://localhost:8000/api/v1/rebuild

# Option 3: Run notebook cell to rebuild
# (Modify notebooks/01_baseline_rag.ipynb to use Chroma)
```

#### 5. Update Tests

```python
# In tests/conftest.py or tests/test_indexation.py
# Change FAISS imports to Chroma where needed
```

#### 6. Verify

```bash
# Run tests
pytest tests/ -v

# Check new index files
ls -lh data/index/chroma_baseline/
# Should see: chroma.sqlite3, .parquet files (no .pkl!)

# Test API
python scripts/run_api.py
curl http://localhost:8000/api/v1/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Concerts à Annecy?"}'
```

### Advantages Gained

- ✅ **No pickle security risk** - SQLite is safe
- ✅ **Auto-persistence** - No manual `save_local()` needed
- ✅ **Better tooling** - Can inspect with SQLite browser
- ✅ **Optional scaling** - Can switch to server mode later

### Rollback Plan

Keep the old FAISS index:
```bash
cp -r data/index/faiss_baseline data/index/faiss_baseline.backup
```

If issues arise, revert code changes and use backup.

---

## Alternative: Qdrant (Server-Based)

### When to Choose Qdrant

- Need multi-user access
- Want web UI for debugging
- Planning production deployment
- Comfortable with Docker

### Quick Start

**1. Start Qdrant server:**
```bash
docker run -p 6333:6333 -p 6334:6334 \
  -v $(pwd)/data/qdrant_storage:/qdrant/storage \
  qdrant/qdrant
```

**2. Install client:**
```bash
pip install qdrant-client
```

**3. Update code:**
```python
from langchain_community.vectorstores import Qdrant
from qdrant_client import QdrantClient

client = QdrantClient(url="http://localhost:6333")
vectorstore = Qdrant.from_documents(
    documents,
    embeddings,
    url="http://localhost:6333",
    collection_name="puls_events",
    prefer_grpc=False
)
```

**4. Access web UI:**
```
http://localhost:6333/dashboard
```

### Advantages

- ✅ True database with ACID
- ✅ REST API (language-agnostic)
- ✅ Built-in monitoring
- ✅ Horizontal scaling support
- ⚠️ Requires Docker/server management

---

## Alternative: Supabase (pgvector in the Cloud)

### When to Choose Supabase

- **Already using Supabase** (e.g., from OC5 project) ✅
- Want managed PostgreSQL with pgvector
- Need cloud hosting without DevOps
- Want to combine with API request logging
- Prefer dashboard/UI for monitoring

### Setup

**1. Enable pgvector in your Supabase project:**

Go to SQL Editor in Supabase Dashboard and run:

```sql
-- Enable vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create table for events
CREATE TABLE puls_events (
  id BIGSERIAL PRIMARY KEY,
  content TEXT NOT NULL,
  metadata JSONB,
  embedding VECTOR(1024),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create similarity search function
CREATE OR REPLACE FUNCTION match_documents(
  query_embedding VECTOR(1024),
  match_count INT DEFAULT 5
)
RETURNS TABLE (
  id BIGINT,
  content TEXT,
  metadata JSONB,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    puls_events.id,
    puls_events.content,
    puls_events.metadata,
    1 - (puls_events.embedding <=> query_embedding) AS similarity
  FROM puls_events
  ORDER BY puls_events.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- Create index for fast search
CREATE INDEX ON puls_events
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

**2. Install Supabase client:**
```bash
pip install supabase
```

**3. Update code:**
```python
from langchain_community.vectorstores import SupabaseVectorStore
from supabase.client import create_client
import os

# Use your existing Supabase credentials
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_ANON_KEY")

supabase = create_client(supabase_url, supabase_key)

# One-time: Upload documents
vectorstore = SupabaseVectorStore.from_documents(
    documents,
    embeddings,
    client=supabase,
    table_name="puls_events",
    query_name="match_documents"
)

# In production: Load existing vectorstore
vectorstore = SupabaseVectorStore(
    client=supabase,
    embedding=embeddings,
    table_name="puls_events",
    query_name="match_documents"
)
```

**4. Add environment variables:**
```bash
# .env file (you probably already have these from OC5!)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOi...
```

### Advantages

- ✅ **Reuse OC5 infrastructure** - Same Supabase project
- ✅ **Managed service** - No server management
- ✅ **Free tier** (500 MB) or Pro ($25/month for 8 GB)
- ✅ **Dashboard** - View/query vectors via Supabase UI
- ✅ **SQL access** - Can join with API request logs
- ✅ **Automatic backups** - Included in Supabase
- ✅ **Real-time subscriptions** - Can watch for new events
- ⚠️ **Cloud dependency** - Requires internet (but so does Mistral API)

### Cost for This Project

- **Current data**: ~8.5 MB (8,500 events)
- **Free tier**: 500 MB ✅ More than enough
- **If you scale**: Pro plan $25/month = 8 GB

### Synergy with OC5

If you have API request logging from OC5, you can unify monitoring:

```sql
-- Same database for both projects!
SELECT
  DATE(created_at) as date,
  COUNT(*) as requests,
  AVG(response_time_ms) as avg_response_time
FROM rag_queries  -- OC7 table
GROUP BY DATE(created_at);

-- Compare with OC5 predictions table
SELECT * FROM predictions WHERE created_at > NOW() - INTERVAL '7 days';
```

---

## Alternative: Self-Hosted pgvector (PostgreSQL)

### When to Choose Self-Hosted pgvector

- Already managing PostgreSQL locally
- Need full control (no cloud)
- Want to avoid recurring costs
- Prefer mature database ecosystem

### Setup

**1. Install PostgreSQL with vector extension:**
```bash
# macOS
brew install postgresql pgvector

# Docker
docker run -p 5432:5432 \
  -e POSTGRES_PASSWORD=postgres \
  ankane/pgvector
```

**2. Enable extension:**
```sql
CREATE EXTENSION vector;
```

**3. Install Python package:**
```bash
pip install pgvector psycopg2-binary
```

**4. Update code:**
```python
from langchain_community.vectorstores import PGVector

CONNECTION_STRING = "postgresql://user:pass@localhost:5432/mydb"

vectorstore = PGVector.from_documents(
    documents,
    embeddings,
    connection_string=CONNECTION_STRING,
    collection_name="puls_events"
)
```

### Advantages

- ✅ Full SQL capabilities
- ✅ ACID guarantees
- ✅ Mature ecosystem
- ✅ Can use with existing PostgreSQL
- ⚠️ Need to manage PostgreSQL

---

## Comparison Matrix

| Feature | FAISS | Chroma | Supabase | Qdrant | pgvector |
|---------|-------|--------|----------|--------|----------|
| **Setup Complexity** | ⭐ Easiest | ⭐⭐ Very Easy | ⭐⭐ Very Easy* | ⭐⭐⭐ Moderate | ⭐⭐⭐⭐ Complex |
| **Security** | ⚠️ Pickle risk | ✅ Safe | ✅ Safe | ✅ Safe | ✅ Safe |
| **Performance** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Scalability** | ⭐⭐ Single machine | ⭐⭐⭐⭐ Server mode | ⭐⭐⭐⭐⭐ Cloud | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Hosting** | Local files | Local/Server | Cloud (managed) | Docker/Cloud | Self-host |
| **Cost** | Free | Free | Free tier + $25/mo | $0.40/GB/mo | Server costs |
| **Dashboard** | ❌ No | ❌ No | ✅ Supabase UI | ✅ Web UI | pgAdmin |
| **SQL Access** | ❌ No | Limited | ✅ Full PostgreSQL | ❌ No | ✅ Full PostgreSQL |
| **Migration effort** | N/A | 30 min | 1 hour* | 2 hours | 4 hours |
| **Best for** | POC/Learning | POC→Production | **OC5 users!** ✅ | Production | PostgreSQL users |

*If already using Supabase from OC5 project

---

## Recommendation

**For this learning project (OC7 with OC5 background):**

### Immediate (v0.3.0)
1. **Keep FAISS** - It works, documented as safe, focus on RAG learning ✅

### Future Extension (Optional)

Choose based on your goals:

| Goal | Recommended | Why |
|------|-------------|-----|
| **Reuse OC5 skills** | **Supabase (pgvector)** ✅ | Same dashboard, same account, unified monitoring |
| **Simplest migration** | Chroma | File-based, 30 min migration |
| **Learn Docker/servers** | Qdrant | Modern architecture, great for resume |
| **Already use PostgreSQL** | Self-hosted pgvector | Full SQL control |

### Specific Recommendation for You

Since you have **OC5 deployed on Supabase**, I recommend:

**Phase 1 (Current):** FAISS ✅
**Phase 2 (Next extension):** **Supabase (pgvector)**
**Why:**
- Reuse your existing Supabase account/project
- Unify OC5 + OC7 monitoring in one dashboard
- Learn pgvector (valuable skill: "PostgreSQL + vectors" on resume)
- No additional infrastructure (already have Supabase)
- Cloud-hosted = easier deployment than FAISS files

**Timeline suggestion:**
- Phase 1: FAISS ✅ (finish v0.3.0)
- Phase 2: Migrate to **Supabase pgvector** (learning extension)
- Phase 3: (Optional) Qdrant if scaling to production

---

## Implementation Checklist

### Chroma Migration

- [ ] Install chromadb: `pip install chromadb`
- [ ] Update imports in `src/api/rag_service.py`
- [ ] Change index loading logic (remove pickle deserialization)
- [ ] Update index path configuration
- [ ] Rebuild index with Chroma
- [ ] Update tests if needed
- [ ] Run full test suite: `pytest tests/ -v`
- [ ] Test API endpoints manually
- [ ] Update documentation (this file)
- [ ] Commit changes: `git commit -m "feat: Migrate from FAISS to Chroma"`

### Qdrant Migration

- [ ] Start Qdrant Docker container
- [ ] Install qdrant-client
- [ ] Update rag_service.py with Qdrant integration
- [ ] Configure connection settings (environment variables)
- [ ] Rebuild index
- [ ] Update health check to verify Qdrant connection
- [ ] Add Qdrant to docker-compose.yml
- [ ] Test multi-user scenarios
- [ ] Update deployment documentation

---

## References

- [LangChain Vector Stores](https://python.langchain.com/docs/integrations/vectorstores/)
- [Chroma Documentation](https://docs.trychroma.com/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [pgvector GitHub](https://github.com/pgvector/pgvector)
- [FAISS Security Discussion](https://github.com/langchain-ai/langchain/discussions/8090)

---

## Notes

- FAISS will remain in LangChain for backward compatibility
- The `allow_dangerous_deserialization` flag was added in LangChain v0.1+
- Chroma uses DuckDB for analytics queries and SQLite for persistence
- All alternatives support the same LangChain `VectorStore` interface
