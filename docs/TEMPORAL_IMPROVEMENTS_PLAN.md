# Temporal Improvements Plan - Puls-Events RAG

**Created**: 2026-02-05
**Status**: Draft — Awaiting Approval
**Branch**: To be created from `main` as `v1.2.0` then `feature/temporal-awareness`
**Estimated Effort**: 2-3 days (6 features, incremental)

---

## Problem Statement

The RAG system currently has **no temporal awareness**. It retrieves events purely by semantic similarity, ignoring dates entirely. This leads to:

- Geographically correct but **temporally irrelevant** results
- No ability to handle queries like "ce weekend", "demain", "en juillet"
- No reference date — the LLM doesn't know what "today" is
- Past events mixed with future events in results
- No structured date fields in metadata (only French text `daterange_fr`)

### Data Context

The OpenAgenda dataset effectively peaks in **2024** (47% of events). The system must define a **reference date** to make temporal queries meaningful. We choose **2024-02-06** as the default reference date, placing the user in the middle of the densest data period.

### Current State (Before)

| Layer | Current Behavior |
|-------|-----------------|
| API schema | No date parameter |
| Prompt | No "today" or temporal instructions |
| Metadata | `daterange: "Jeudi 4 avril, 09h00"` (French text, unparsable) |
| Retrieval | Pure semantic/keyword, no date filtering |
| Reranking | FlashRank relevance only, no temporal signal |
| Generation | LLM guesses dates with no context |

### Target State (After)

| Layer | Basic/Hybrid | Advanced |
|-------|-------------|----------|
| API schema | `reference_date` param (ISO, default `2024-02-06`) | Same |
| Query analysis | None (no extra LLM call) | Enhanced: off-topic detection + temporal window extraction |
| Prompt | Injects reference date + temporal instructions | Same |
| Metadata | `event_start_date` and `event_end_date` as ISO strings | Same |
| Retrieval | FAISS with `fetch_k` increase | Same |
| Post-retrieval | Past event filter only | Past event filter + temporal window filter |
| Reranking | Temporal proximity to reference_date | Temporal proximity to extracted window (or reference_date) + FlashRank |
| Generation | LLM interprets temporal expressions via prompt context | Same, with higher-quality filtered context |

---

## Design Decisions

### DD-1: Reference Date via API Parameter

The `/api/v1/ask` endpoint will accept an optional `reference_date` field (ISO 8601 format: `YYYY-MM-DD`).

- **Default**: `2024-02-06` (hardcoded constant, configurable via env var `DEFAULT_REFERENCE_DATE`)
- **Rationale**: API consumers can set their own reference date for flexibility. The default places queries in the densest data period (2024).
- **Web app**: Will display a notice: "For demonstration purposes, the reference date is set to February 6, 2024" and will not expose a date picker (demo app, fixed date).

### DD-2: ISO Dates Everywhere

All dates in the system will use ISO 8601 (`YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SS`):
- Metadata fields: `event_start_date`, `event_end_date`
- API request/response fields
- Internal date comparisons
- Prompt injection

**No French text dates for machine processing.** The `daterange_fr` field remains in the chunk text for LLM readability but is not used for filtering.

### DD-3: Past Events Filtered Out (Design Choice)

Events with `event_end_date < reference_date` are **excluded from results** after retrieval.

**This is a deliberate design choice**: the system recommends upcoming/current events only. This should be clearly documented because:
- A different system could show past events (e.g., "What happened last month?")
- Our choice prioritizes actionable recommendations over historical queries
- The filter is applied post-retrieval, not at indexing time (all events remain in the index)

### DD-4: LLM-Based Temporal Understanding (No Regex)

~~Original plan used regex for temporal expressions.~~ **Revised**: regex is inherently brittle for combinatory queries like "ce soir ou demain", "avant la fin du mois", or "pendant les vacances". Instead:

- **Basic/Hybrid methods**: No temporal query parsing. The prompt (with reference date + temporal instructions) gives the LLM enough context to interpret temporal expressions naturally during generation. This avoids false negatives from rigid pattern matching.
- **Advanced method**: The existing Query Analysis LLM call (which already detects off-topic queries) is extended to also extract a temporal window. This is a single LLM call, not an additional one.

**Rationale for dropping regex**:
- Regex cannot handle combinations ("ce soir ou demain"), vague expressions ("bientôt"), or domain knowledge ("pendant les vacances scolaires")
- The LLM already sees events with ISO dates in the context — it naturally understands temporal intent
- Risk of false negatives (filtering out relevant events) outweighs the marginal precision gain from regex
- Simpler codebase: no `temporal_parser.py` module, no pattern maintenance

### DD-5: Chroma Migration — Not Now, Documented for Future

**What is Chroma?** A lightweight, SQLite-based vector store that supports native metadata pre-filtering. Unlike FAISS (which does post-filtering: fetch N vectors, then filter), Chroma can filter metadata *before* the vector search, guaranteeing you always get `k` results matching your date criteria.

**Why not now?**
- FAISS post-filtering with generous `fetch_k` is sufficient for our dataset size (10k events)
- Chroma migration is well-documented in `docs/future/VECTOR_STORE_MIGRATION.md`
- Adding Chroma introduces a new dependency and storage format change

**When to migrate?**
- If date filtering causes too many empty results with FAISS (fetch_k exhaustion)
- If dataset grows beyond 50k events
- If we need multi-field compound filters frequently

### DD-6: fetch_k — Not Exposed as API Parameter

Currently `fetch_k` is not an API parameter, and `top_k` from the API is only used to slice final results — the retrievers internally hardcode `k=5` in `search_kwargs`.

**Plan**:
- Wire `top_k` from API request through to retriever `search_kwargs`
- Set `fetch_k = top_k * 10` internally (not exposed to API users)
- This gives the date filter enough candidates to work with
- Rationale: `fetch_k` is an implementation detail. API users control *how many results they want* (`top_k`), not *how the retrieval pipeline works internally*

### DD-7: Prompt-Based Temporal Understanding (Primary Mechanism)

The system prompt is the **primary temporal mechanism** for Basic/Hybrid methods and a **complementary mechanism** for Advanced:

- Injects the reference date ("Date du jour : jeudi 6 février 2024")
- Instructs the LLM to never recommend past events
- Instructs the LLM to interpret relative expressions ("ce weekend", "demain") relative to the reference date
- Instructs the LLM to sort events by date, closest first

For Basic/Hybrid, this is the **only** temporal intelligence (besides the hard past-event filter and proximity reranking). The LLM sees events with ISO dates in context and naturally handles temporal queries — including complex ones like "ce soir ou demain" that regex could never parse.

For Advanced, the prompt instructions act as a **safety net** on top of the LLM-extracted temporal window filter.

---

## Feature List (Implementation Order)

Each feature follows the workflow:
1. Prototype in notebook → 2. Write tests → 3. Adapt scripts/code → 4. Run all tests → 5. Update docs → 6. Report

### Feature 1: ISO Date Metadata at Indexing Time ✅

**Status**: Complete — 10 tests added (93 total), `_build_metadata()` updated.

**Goal**: Every document chunk carries structured, parseable date fields in its metadata.

**Changes**:
- `rag_service.py` → `_build_document_metadata()`: Parse `firstdate_begin` and `lastdate_end` into ISO `YYYY-MM-DD` strings
- Store: `event_start_date`, `event_end_date`, `event_year`, `event_month` in metadata
- Keep `daterange` (French text) for display purposes
- Handle missing/malformed dates gracefully (set to `None`, log warning)

**Metadata schema (after)**:
```python
{
    "uid": "abc123",
    "title": "Concert de Jazz",
    "city": "Annecy",
    "department": "Haute-Savoie",
    "daterange": "Samedi 15 juin, 20h00",          # display only
    "event_start_date": "2024-06-15",               # ISO, for filtering
    "event_end_date": "2024-06-15",                  # ISO, for filtering
    "event_year": 2024,                              # convenience
    "event_month": 6,                                # convenience
    "category": "concert",
    "url": "https://..."
}
```

**Tests**:
- Metadata contains ISO dates for events with valid dates
- Events with missing `firstdate_begin` get `None` dates
- Events with malformed date strings get `None` dates + warning logged
- `event_year` and `event_month` are integers, correctly parsed
- Index rebuilds successfully with new metadata schema

**Notebook validation**:
- Load a sample of events, verify date parsing accuracy
- Check distribution: how many events have valid vs missing dates
- Verify index still works for similarity search after metadata change

---

### Feature 2: Reference Date in API + Prompt Injection ✅

**Status**: Complete — 16 new tests (109 total). Schema, prompt, constant, wiring done.
Note: Prompt uses DEFAULT_REFERENCE_DATE at chain init. Per-request prompt injection in Feature 3.

**Goal**: API accepts `reference_date`, prompt tells the LLM what "today" is.

**Changes**:

**`schemas.py`** — Add `reference_date` to `QuestionRequest`:
```python
reference_date: Optional[str] = Field(
    default=None,
    description="Reference date for temporal queries (ISO format: YYYY-MM-DD). "
                "Defaults to 2024-02-06. The RAG system uses this as 'today' "
                "to interpret relative date expressions like 'ce weekend'.",
    examples=["2024-02-06", "2024-07-15"],
    pattern=r"^\d{4}-\d{2}-\d{2}$"
)
```

**`rag_service.py`** — New prompt template:
```python
RAG_PROMPT_TEMPLATE = """Tu es un assistant spécialisé dans les événements culturels
de Savoie (73), Haute-Savoie (74) et Isère (38).

Date du jour : {reference_date_formatted}

Instructions temporelles :
- Ne recommande JAMAIS d'événements dont la date est passée par rapport à la date du jour.
- Si l'utilisateur demande "ce weekend", il s'agit du samedi et dimanche les plus proches après la date du jour.
- Trie les événements par date, les plus proches en premier.
- Si tous les événements du contexte sont passés, indique-le clairement.

Contexte :
{context}

Question : {question}

Réponse détaillée :"""
```

**`main.py`** — Pass `reference_date` through the query pipeline.

**`static/index.html`** — Add visible notice:
```
⚠️ Demo mode: reference date is February 6, 2024 (dataset coverage period)
```

**Constants**:
```python
DEFAULT_REFERENCE_DATE = os.getenv("DEFAULT_REFERENCE_DATE", "2024-02-06")
```

**Tests**:
- Request without `reference_date` uses default `2024-02-06`
- Request with valid ISO date uses that date
- Request with invalid date format returns 422
- Prompt contains the formatted reference date
- Response metadata includes `reference_date` used

**Notebook validation**:
- Compare answers for "concerts ce weekend" with and without reference date
- Verify LLM correctly interprets "ce weekend" relative to the reference date

---

### Feature 3: Pipeline Rework + Past Event Filtering ✅

**Status**: Complete — 8 new tests (117 total). RetrievalQA chains replaced with manual retrieve-then-generate pipeline.

**Goal**: Fix the `top_k` disconnect, filter past events, and prepare the pipeline for temporal features.

#### Problem: `top_k` Is Currently Cosmetic

The API accepts `top_k` (1-20) but the retrievers **hardcode `k=5`** at chain initialization. The `top_k` parameter only slices the source documents in the JSON response — it never changes what the retriever fetches or what the LLM sees in its prompt.

| User sets `top_k` | Retriever fetches | LLM sees | Sources in response |
|---|---|---|---|
| `top_k=3` | 5 (hardcoded) | 5 docs | 3 docs |
| `top_k=10` | 5 (hardcoded) | 5 docs | 5 docs (max!) |

This was not a deliberate design choice but a side-effect of using `RetrievalQA` chains, which bundle the retriever at construction time (PR #7). The `top_k` parameter was added to the schema forward-looking but the wiring was never completed.

#### Solution: Manual Retrieve-Then-Generate Pattern

Replace the `RetrievalQA` chain with an explicit pipeline where each step is controllable per-request:

```python
def query(self, question, method="hybrid", top_k=5, reference_date="2024-02-06"):
    # 1. Retrieve candidates (generous fetch_k for date filtering headroom)
    fetch_k = top_k * 10
    docs = self._retrieve(question, method, fetch_k=fetch_k)

    # 2. Filter past events
    docs = self._filter_past_events(docs, reference_date)

    # 3. Slice to top_k
    docs = docs[:top_k]

    # 4. Build prompt with exactly top_k documents + reference date
    context = "\n\n".join(doc.page_content for doc in docs)
    prompt = RAG_PROMPT_TEMPLATE.format(
        reference_date_formatted=format_date_french(reference_date),
        context=context,
        question=question
    )

    # 5. Generate answer
    answer = self.llm.invoke(prompt)
    return {"answer": answer, "sources": docs, ...}
```

**Key changes**:
- `top_k` now controls actual retrieval (honest API contract)
- `fetch_k = top_k * 10` gives date filtering enough candidates
- LLM sees exactly `top_k` documents after filtering (not more, not less)
- Pipeline is explicit — each step (retrieve, filter, generate) is independent and testable
- Retrievers created per-query with dynamic `k` instead of hardcoded at init

#### Past Event Filter

**`rag_service.py`** — New function `_filter_past_events()`:
```python
def _filter_past_events(
    documents: List[Document],
    reference_date: str  # ISO YYYY-MM-DD
) -> List[Document]:
    """Remove events that ended before the reference date.

    Design choice: This system recommends upcoming/current events only.
    Past events are excluded to provide actionable recommendations.
    Events with missing dates are kept (benefit of the doubt).
    """
    ref = datetime.strptime(reference_date, "%Y-%m-%d").date()
    filtered = []
    for doc in documents:
        end_date_str = doc.metadata.get("event_end_date")
        if end_date_str is None:
            filtered.append(doc)  # keep events with unknown dates
            continue
        try:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            if end_date >= ref:
                filtered.append(doc)
        except ValueError:
            filtered.append(doc)  # keep events with unparseable dates
    return filtered
```

**Integration point**: Applied after retrieval, before slicing to `top_k` and before LLM generation.

#### `fetch_k` Strategy

- `fetch_k = top_k * 10` by default (e.g., user wants 5 results → retrieve 50 candidates)
- Not exposed as API parameter (implementation detail)
- Compensates for documents removed by date filtering
- If 50 candidates still yields < `top_k` after filtering, the system returns what it has (graceful degradation)

**Tests**:
- `top_k=3` → retriever fetches 30, LLM sees 3 documents
- `top_k=10` → retriever fetches 100, LLM sees 10 documents
- Past events removed (event_end_date < reference_date)
- Current/future events kept
- Events with `None` end date kept (not filtered)
- Events with malformed end date kept (not filtered)
- Empty result set handled gracefully (returns message "no upcoming events found")
- `fetch_k` is correctly set to `top_k * 10`
- All 87 existing tests still pass (backwards compatibility)

**Notebook validation**:
- Query "concerts à Annecy" with `top_k=3` and `top_k=10`, verify different result counts
- Query with `reference_date=2024-02-06`, verify no events before February 2024
- Check that results are still relevant (not empty due to over-filtering)
- Compare answer quality before/after pipeline rework

---

### Feature 4: Enhanced Query Analysis for Advanced RAG ✅

**Status**: Complete — 19 new tests (136 total). Query analysis prompt, response parser, temporal window filter, and pipeline integration done.

**Goal**: Extend the advanced method's existing Query Analysis LLM call to also extract temporal intent, enabling smarter post-retrieval filtering.

**Scope**: Advanced method only. Basic/Hybrid rely on prompt-based temporal instructions (Feature 2) — no extra LLM call.

**Why not Basic/Hybrid?** Adding an LLM call for temporal parsing would double latency for these methods. The prompt instructions + past-event filter + temporal reranking already handle temporal queries well. The advanced method already pays for a Query Analysis call, so extending it costs nothing.

**Changes**:

**`rag_service.py`** — Enhanced Query Analysis prompt (advanced method):
```python
QUERY_ANALYSIS_PROMPT = """Analyse cette question sur les événements culturels.
Date du jour : {reference_date}

Réponds en JSON strict :
{{
  "is_relevant": true/false,
  "temporal_window": {{
    "start_date": "YYYY-MM-DD" ou null,
    "end_date": "YYYY-MM-DD" ou null
  }},
  "reasoning": "explication courte"
}}

Exemples :
- "Concerts ce weekend" (ref: 2024-02-06) → {{"is_relevant": true, "temporal_window": {{"start_date": "2024-02-10", "end_date": "2024-02-11"}}, "reasoning": "ce weekend = samedi-dimanche suivants"}}
- "Ce soir ou demain à Annecy" (ref: 2024-02-06) → {{"is_relevant": true, "temporal_window": {{"start_date": "2024-02-06", "end_date": "2024-02-07"}}, "reasoning": "ce soir + demain = aujourd'hui et lendemain"}}
- "Festivals cet été" (ref: 2024-02-06) → {{"is_relevant": true, "temporal_window": {{"start_date": "2024-06-01", "end_date": "2024-08-31"}}, "reasoning": "été = juin à août"}}
- "Quels sont les meilleurs restaurants?" → {{"is_relevant": false, "temporal_window": null, "reasoning": "pas lié aux événements culturels"}}
- "Que faire à Annecy?" → {{"is_relevant": true, "temporal_window": null, "reasoning": "pas de contrainte temporelle explicite"}}

Question : {question}
"""
```

**Integration in advanced pipeline**:
```python
def _query_advanced(self, question, top_k, reference_date):
    # 1. Enhanced Query Analysis (existing LLM call, extended)
    analysis = self._analyze_query(question, reference_date)

    if not analysis["is_relevant"]:
        return self._off_topic_response(question)

    # 2. Retrieve candidates
    docs = self._retrieve(question, "advanced", fetch_k=top_k * 10)

    # 3. Filter past events (all methods do this)
    docs = self._filter_past_events(docs, reference_date)

    # 4. Apply temporal window if extracted (advanced only)
    temporal_window = analysis.get("temporal_window")
    if temporal_window and temporal_window.get("start_date"):
        docs = self._filter_temporal_window(docs, temporal_window)

    # 5. Temporal rerank → take top_k → generate
    ...
```

**`_filter_temporal_window()`** — Soft filter for advanced method:
```python
def _filter_temporal_window(
    self,
    documents: List[Document],
    temporal_window: dict
) -> List[Document]:
    """Keep events overlapping with the LLM-extracted temporal window.

    Unlike _filter_past_events (hard filter), this is a best-effort filter:
    - Events overlapping the window are kept
    - Events with missing dates are kept (benefit of the doubt)
    - If filtering would empty the list, return original (never return nothing)
    """
```

**Design safeguard**: If the temporal window filter would remove ALL documents, it is skipped and all candidates are passed through. This prevents the LLM from over-filtering.

**Tests**:
- "Concerts ce weekend" (ref: 2024-02-06) → temporal_window = (2024-02-10, 2024-02-11)
- "Ce soir ou demain" (ref: 2024-02-06) → temporal_window = (2024-02-06, 2024-02-07)
- "Événements en mars" → temporal_window = (2024-03-01, 2024-03-31)
- "Que faire à Annecy?" → temporal_window = null (no temporal constraint)
- Off-topic query → is_relevant = false
- Temporal window filter keeps overlapping events
- Temporal window filter keeps events with missing dates
- Empty-result safeguard: if all filtered out, return unfiltered list
- Basic/Hybrid methods do NOT call query analysis (no extra LLM call)

**Notebook validation**:
- Run enhanced query analysis on 10+ temporal queries, verify extracted windows
- Compare advanced method results with and without temporal window filtering
- Verify no false negatives on combinatory queries like "ce soir ou demain"

---

### Feature 5: Temporal Proximity Reranking ✅

**Status**: Complete — 9 new tests (145 total). Exponential decay reranking integrated for all methods.

**Goal**: After retrieval and date filtering, boost events closer to the target date.

**Applies to**: All methods (basic, hybrid, advanced). This is a lightweight sort operation, no LLM call.

**Changes**:

**`rag_service.py`** — New function `_temporal_rerank()`:
```python
def _temporal_rerank(
    documents: List[Document],
    target_date: str,
    half_life_days: int = 14
) -> List[Document]:
    """Rerank documents by temporal proximity to a target date.

    Uses exponential decay: events further from target_date are pushed down.

    Score formula:
        temporal_score = 0.5 ^ (|event_start_date - target_date| / half_life_days)

    Documents are sorted by temporal_score descending. Events with missing
    dates are placed at the end (preserving their relative order).

    Args:
        target_date: ISO YYYY-MM-DD — the date to rank proximity against.
        half_life_days: Events this many days away score 50%.
                       14 days = events 2 weeks away get half the boost.
    """
```

**Target date selection** (done by caller, not by this function):
- **Basic/Hybrid**: `target_date = reference_date` (events closest to "today" rank first)
- **Advanced**: `target_date = temporal_window["start_date"]` if extracted, else `reference_date`

This keeps `_temporal_rerank()` simple — it just sorts by proximity to a given date. The caller decides what that date is.

**Scoring**:
```
temporal_score = 0.5 ^ (|event_start_date - target_date| / half_life_days)
```

Events with `event_start_date = None` get `temporal_score = 0` (pushed to bottom, but not removed).

**Tests**:
- Event tomorrow ranks higher than event next month
- Event in 2 weeks scores ~50% temporal weight (half-life = 14)
- Events with no date are placed at end (not removed)
- Different target dates produce different rankings
- Single-event list returns unchanged
- Empty list returns empty

**Notebook validation**:
- Compare top-5 results before and after temporal reranking
- Show that temporally closer events move up in ranking

---

### Feature 6: Integrated Pipeline + Documentation + Temporal Evaluation

**Goal**: Wire all features together end-to-end, update documentation, and add temporal evaluation questions.

**Changes**:

**Complete query pipeline** (in `rag_service.py`):

Basic/Hybrid:
```
1. Parse reference_date (from request or default)
2. Retrieve candidates with fetch_k = top_k * 10
3. Filter past events (event_end_date < reference_date)
4. Temporal reranking (proximity to reference_date)
5. Take top_k results
6. Build prompt with reference_date + temporal instructions
7. Generate response
```

Advanced:
```
1. Parse reference_date (from request or default)
2. Enhanced Query Analysis: off-topic detection + temporal window extraction
3. If off-topic → return off-topic response
4. Retrieve candidates with fetch_k = top_k * 10
5. Filter past events (event_end_date < reference_date)
6. If temporal_window extracted → filter to window (with empty-result safeguard)
7. Temporal reranking (proximity to temporal_window start or reference_date)
8. Take top_k results
9. FlashRank semantic reranking
10. Build prompt with reference_date + temporal instructions
11. Generate response
```

**Response metadata** — Add temporal info:
```python
{
    "rag_method": "advanced",
    "reference_date": "2024-02-06",
    "temporal_window": {                    # advanced only, null for basic/hybrid
        "start_date": "2024-02-10",
        "end_date": "2024-02-11"
    },
    "candidates_fetched": 50,
    "candidates_after_date_filter": 12,
    ...
}
```

#### Temporal Evaluation Questions

Extend `tests/test_data/test_questions.csv` with temporal queries. These must be **data-driven**: before writing expected answers, analyse the actual events in the dataset around the reference date (2024-02-06) to build realistic ground truth.

**Methodology**:
1. Query the dataset for events around 2024-02-06 (e.g., Feb 6-12 for "ce weekend", Feb 7 for "demain")
2. Identify real events that exist in the data for those dates
3. Build expected answers referencing actual event titles, locations, dates
4. Include edge cases where no events match (e.g., a very specific date with no events)

**Question categories to add**:

| Category | Example Query | What We Test |
|----------|--------------|--------------|
| Explicit day | "Que faire demain à Annecy?" | LLM interprets "demain" as 2024-02-07 |
| Weekend | "Concerts ce weekend en Savoie" | LLM picks Sat-Sun Feb 10-11 |
| Combination | "Ce soir ou demain à Grenoble" | LLM handles OR temporal logic |
| Month | "Événements en mars à Chambéry" | Correct month scoping |
| Vague | "Bientôt un festival en Isère?" | LLM picks temporally close events |
| No temporal | "Quels types d'événements à Annecy?" | No temporal bias in response |
| Past reference | "Qu'est-ce qui s'est passé la semaine dernière?" | System acknowledges it recommends upcoming events only |
| Season | "Festivals cet été en Haute-Savoie" | Summer 2024 scoping |

**Target**: 10-15 temporal evaluation questions, annotated with expected behavior.

**Documentation updates**:
- `docs/technical_report.md` — New section on temporal handling
- `README.md` — Update API examples with `reference_date`
- `DEPLOYMENT_STATUS.md` — Note the default reference date
- OpenAPI docs — Auto-updated via Pydantic schema changes
- Web app — Notice about demo reference date
- This file — Mark features as complete

**Integration tests**:
- Full pipeline test: "Concerts ce weekend à Annecy" with reference_date=2024-02-06
  → Returns only events on or after 2024-02-06
- Full pipeline test: Same query with reference_date=2024-07-15
  → Returns different events (July period)
- Advanced method extracts temporal window correctly
- Basic/Hybrid methods do NOT call query analysis
- All existing tests still pass (backwards compatibility)
- Temporal evaluation questions produce reasonable results

---

## Implementation Workflow (Per Feature)

```
┌─────────────────────────────────────────────────┐
│ 1. NOTEBOOK PROTOTYPE                           │
│    - Implement in notebook cells                │
│    - Verify results are as expected             │
│    - Document observations                      │
├─────────────────────────────────────────────────┤
│ 2. WRITE TESTS                                  │
│    - Main cases                                 │
│    - Edge cases                                 │
│    - Tests MUST FAIL initially (TDD)            │
├─────────────────────────────────────────────────┤
│ 3. ADAPT CODE                                   │
│    - Implement in src/ scripts                  │
│    - Follow existing patterns                   │
├─────────────────────────────────────────────────┤
│ 4. RUN ALL TESTS                                │
│    - New tests pass                             │
│    - ALL existing 87 tests still pass           │
│    - If failures: go back to step 3             │
├─────────────────────────────────────────────────┤
│ 5. UPDATE DOCUMENTATION                         │
│    - This plan file (mark complete)             │
│    - User-facing docs as needed                 │
├─────────────────────────────────────────────────┤
│ 6. SHORT REPORT                                 │
│    - What was done                              │
│    - Test results                               │
│    - Move to next feature                       │
└─────────────────────────────────────────────────┘
```

---

## Git Strategy

```
main
  └── v1.2.0
        ├── feature/iso-date-metadata        (Feature 1)
        ├── feature/reference-date-api       (Feature 2)
        ├── feature/pipeline-rework          (Feature 3)
        ├── feature/advanced-query-analysis  (Feature 4)
        ├── feature/temporal-reranking       (Feature 5)
        └── feature/temporal-integration     (Feature 6)
```

Each feature branch merged to `v1.2.0` via PR. Final `v1.2.0 → main` PR when all features complete.

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| LLM extracts wrong temporal window (advanced) | Medium | Low | Empty-result safeguard: if all filtered out, skip window filter |
| Over-filtering empties results | Medium | Medium | Keep events with missing dates, generous fetch_k, safeguards |
| fetch_k too low for large cities | Low | Medium | fetch_k = top_k * 10 (50 for default top_k=5) |
| Temporal reranking hurts semantic quality | Low | Medium | Semantic ranking done first, temporal is secondary sort |
| Existing tests break | Low | High | Run full suite after each feature, fix immediately |
| LLM query analysis adds latency (advanced) | Low | Low | Already paying for query analysis call, just extending prompt |
| Prompt-only temporal handling insufficient (basic/hybrid) | Medium | Low | Acceptable tradeoff — advanced method exists for higher precision |

---

## Open Questions (For Review)

1. **Default reference date**: `2024-02-06` — Is this the right choice? Should it be closer to the data peak (e.g., mid-2024)?
2. **fetch_k multiplier**: `top_k * 10` — Should it be higher for safety? Lower for performance?
3. **Half-life for temporal reranking**: `14 days` — Events 2 weeks away get 50% temporal score. Too aggressive? Too lenient?
4. **Temporal evaluation question count**: 10-15 seems right for a POC. Enough to validate, not overkill?

---

## Appendix: Chroma vs FAISS for Date Filtering

| Aspect | FAISS (Current) | Chroma (Future Option) |
|--------|-----------------|----------------------|
| **Filtering** | Post-filtering (fetch N, then filter) | Pre-filtering (filter, then search) |
| **Guarantee** | May return < k results if too many filtered | Always returns k results |
| **fetch_k needed?** | Yes, must over-fetch | No, native filtering |
| **Storage** | In-memory + pickle files | SQLite database |
| **Dependencies** | `faiss-cpu` | `chromadb` |
| **Migration effort** | — | ~4 hours (same LangChain interface) |
| **When to migrate** | — | If date filtering causes empty results frequently |
| **Overkill for us?** | — | Slightly, but not heavy. SQLite-based, no server needed |

**Verdict**: FAISS with generous `fetch_k` is sufficient for now. Chroma is a lightweight upgrade path if needed, not a heavy infrastructure change.

---

## Appendix: Temporal Hint in Retrieval Prompt (Alternative to Metadata Filtering)

An alternative to metadata filtering is enriching the search query with temporal context before embedding:

```python
# Original query
query = "concerts ce weekend"

# Enriched query (for embedding)
enriched = "concerts ce weekend (samedi 10 février 2024, dimanche 11 février 2024)"
```

**Pros**: No metadata filtering needed, works with vanilla FAISS
**Cons**: Pollutes the semantic vector, inconsistent results, events rarely mention specific dates in the same format

**Verdict**: Use as a complement, not a replacement. The enriched query can help vector search find temporally relevant events, but metadata filtering is the primary mechanism.

---

**Ready for review.** Once approved, implementation starts with Feature 1.
