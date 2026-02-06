# Known Issues - OC7 RAG System

**Last updated**: 2026-02-06
**Version**: v1.2.0

---

## 1. Auto-rebuild fails when index directory exists but is empty — FIXED in v1.2.0 ✅

**Severity**: Medium
**Status**: **FIXED** in v1.2.0
**Discovered**: 2026-02-04 during CI/CD deployment validation
**Confirmed**: 2026-02-06 during v1.2.0 test deployment on port 8001
**Fixed**: 2026-02-06 — check for `index.faiss` file instead of directory

### Description

The auto-rebuild feature (introduced in PR #19) fails to trigger when:
1. The FAISS index directory `/app/data/index/faiss_baseline/` exists
2. But the directory is empty (no `index.faiss` file)

### Root Cause

In `src/api/rag_service.py` (lines ~509-537 in v1.2.0):

```python
# Load FAISS index
if self.index_path.exists():  # ← Checks directory exists, not file
    logger.info(f"Loading FAISS index from {self.index_path}")
    self.vectorstore = FAISS.load_local(  # ← Throws exception if index.faiss missing
        str(self.index_path),
        self.embeddings,
        allow_dangerous_deserialization=True
    )
    # ... success path ...
else:
    logger.warning(f"FAISS index not found at {self.index_path}")
    self._index_loaded = False

except Exception as e:
    logger.error(f"Error loading RAG components: {e}")
    self._llm_available = False  # ← BUG: Resets LLM flag even though LLM initialized successfully
    self._index_loaded = False
    raise
```

**The problem**:
1. `self.index_path.exists()` returns TRUE when the directory exists
2. `FAISS.load_local()` tries to open `index.faiss` file inside the directory
3. File doesn't exist → Exception raised
4. Exception handler sets `_llm_available = False` (line 265)
5. Auto-rebuild condition requires `_llm_available == True` (line 169)
6. Auto-rebuild never triggers

### Impact

- Fresh container deployments won't auto-rebuild
- Manual intervention required to trigger rebuild
- Service starts in degraded mode (unhealthy)

### Workaround

Before restarting container, remove empty index directory:

```bash
docker compose -f docker-compose.prod.yml exec api rm -rf /app/data/index/faiss_baseline
docker compose -f docker-compose.prod.yml restart api
```

### Fix Applied (v1.2.0)

**Option 1 was implemented**: Check for actual index file before loading.

```python
# Load FAISS index (check for actual index file, not just directory)
index_file = self.index_path / "index.faiss"
if index_file.exists():
    # ... load index ...
else:
    logger.warning(f"FAISS index not found at {index_file}")
    self._index_loaded = False
```

This prevents the exception cascade and allows the auto-rebuild path to trigger correctly.

---

## 2. Web UI does not display the demo reference date — FIXED in v1.2.0 ✅

**Severity**: Medium (UX / clarity)
**Status**: **FIXED** in v1.2.0
**Discovered**: 2026-02-06 during v1.2.0 manual testing
**Fixed**: 2026-02-06 — added yellow info banner below header

### Description

The RAG system uses a fixed **reference date** (`2024-02-06`) for all temporal queries ("ce weekend", "demain", "événements en cours", etc.). This date is the default `reference_date` parameter in the API and reflects the period when the dataset has the most events.

However, the web chat UI does **not** display this information anywhere. Users testing the app see "today's date" in the browser but the system interprets temporal queries relative to 2024-02-06. This creates confusion when results don't match the user's expectation of "today".

### Impact

- Users think the system is broken when "ce weekend" returns events from February 2024
- Demo reviewers may not understand the temporal context
- No visual indication that this is a demo with a fixed reference date

### Proposed Fix (v1.3.0)

Add a visible banner or notice on the web chat interface:

**Option 1**: Info banner at the top of the chat area
```html
<div class="demo-notice">
  Demo mode — "Aujourd'hui" = 6 février 2024
  (les requêtes temporelles sont relatives à cette date de référence)
</div>
```

**Option 2**: Display in the system's first message / welcome text

**Option 3**: Show the reference date alongside each response in the metadata

**Recommended**: Option 1 — most visible, immediately sets expectations.

Additionally, consider:
- Displaying the reference date in the `/health` or `/api/v1/rag/info` response
- Adding a tooltip or "?" icon explaining why a fixed date is used

---

## 3. Download timeout issue - FIXED in v0.4.1 ✅

**Severity**: **CRITICAL** (blocking production deployment)
**Status**: **FIXED** in v0.4.1
**Discovered**: 2026-02-04 during CI/CD deployment validation
**Fixed**: 2026-02-04 via hotfix/api-filtering

### Original Problem

When triggering rebuild (auto or manual), the download from OpenDataSoft API would hang indefinitely, blocking the entire service.

### Root Cause Analysis

The issue was NOT a timeout problem - it was downloading unnecessary data:

1. **Full dataset download**: 4GB (all France, all events)
2. **Download time**: > 5 minutes (exceeded 300s timeout)
3. **Inefficiency**: Downloaded 4GB to keep ~72MB (98% waste)
4. **Filtering**: Done client-side AFTER download

### The Fix (v0.4.1)

**Use API-level filtering** to download only relevant data:

```python
# Before (v0.4.0): Download entire 4GB dataset
api_url = ".../exports/json"

# After (v0.4.1): Filter at API level
dept_filter = '"Savoie","Haute-Savoie","Isère"'
api_url = f".../exports/json?where=location_department in ({dept_filter})"
```

**Results**:
- **Download size**: 4GB → 72MB (98% reduction)
- **Download time**: 5+ minutes → ~11 seconds (97% faster)
- **Timeout**: No longer an issue

**Files changed**:
- `src/api/rag_service.py:_download_openagenda_data()` - Add API filtering
- `src/api/rag_service.py:_filter_events()` - Remove department filter (now at API level)
- `scripts/filter_data.py` - Add deprecation notice

### Benefits

1. **Deployment unblocked**: Auto-rebuild now completes in ~11s
2. **Resource efficiency**: 98% less bandwidth, memory, and processing
3. **Faster rebuilds**: Manual rebuilds also benefit
4. **Scalability**: Can handle more frequent refreshes

### Migration Notes

No migration needed - change is backward compatible. Existing index data remains valid.

---

## 4. Security: API key exposure in documentation

**Severity**: **CRITICAL** 🔴
**Status**: Immediate action required
**Discovered**: 2026-02-04

### Description

During troubleshooting, the Mistral API key was exposed in plain text when checking `.env` file contents.

**Impact**: API key compromised and requires rotation.

### Required Actions

1. ✅ Rotate Mistral API key immediately
   - Go to Mistral console
   - Revoke compromised key
   - Generate new API key

2. ✅ Update server configuration
   ```bash
   ssh oc7api@188.34.205.146
   nano ~/oc7-rag-docker/.env
   # Update MISTRAL_API_KEY with new value
   sg docker "docker compose -f ~/oc7-rag-docker/docker-compose.prod.yml restart api"
   ```

3. ✅ Update GitHub secret
   - Go to repository Settings → Secrets → Actions
   - Update `MISTRAL_API_KEY` with new value

4. ✅ Re-deploy via CI/CD to verify new key works

### Prevention

- Never use `cat` or `echo` on files containing secrets
- Use `grep -q` to check presence without displaying values
- Use environment variable existence checks: `printenv | grep -q MISTRAL_API_KEY`
- Always mask secrets in logs and conversation transcripts

---

## 5. Docker Compose version warning

**Severity**: Informational
**Status**: Won't fix (cosmetic)

### Description

Docker Compose shows warning:
```
level=warning msg="the attribute `version` is obsolete, it will be ignored"
```

### Explanation

Docker Compose v2 no longer requires `version` field in `docker-compose.yml`. The field is ignored but harmless.

### Resolution

No action needed. Can remove `version: '3.8'` line in future update for cleaner output.

---

## Reporting New Issues

If you discover additional issues, please:
1. Document symptoms, reproduction steps, and impact
2. Add to this file with severity and status
3. Link to relevant GitHub issues if created
4. Propose workarounds and potential fixes

**Template**:
```markdown
## N. Issue Title

**Severity**: Critical/High/Medium/Low/Informational
**Status**: Open/Investigating/Workaround/Fixed
**Discovered**: YYYY-MM-DD

### Description
[Clear description of the issue]

### Root Cause
[Technical explanation if known]

### Impact
[How it affects users/system]

### Workaround
[Temporary fix if available]

### Proposed Fix
[Long-term solution]
```
