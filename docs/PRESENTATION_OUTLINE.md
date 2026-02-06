# Presentation Outline — Puls-Events RAG System

**Format**: PowerPoint, 10-15 slides
**Audience**: Technical evaluators + business stakeholders (Jérémy, product/marketing teams)
**Duration**: ~20-25 minutes presentation + Q&A
**Language**: French (presentation), English (code snippets)

---

## Slide 1 — Title Slide

**Title**: Puls-Events RAG — Assistant Intelligent pour les Événements Culturels

**Subtitle**: POC d'un chatbot basé sur le Retrieval-Augmented Generation

**Author**: Ghislain de Labie
**Context**: OpenClassrooms — Ingénieur IA (diplôme Bac+5)
**Date**: Février 2026

**Visual**: Puls-Events logo / French Alps landscape

---

## Slide 2 — Contexte et Problématique

**Title**: Le défi de la découverte d'événements culturels

**Key points**:
- **Client**: Puls-Events — plateforme de recommandations culturelles personnalisées
- **Problème**: Information fragmentée sur plusieurs plateformes, recherche par mots-clés insuffisante
- **Besoin**: Un chatbot intelligent capable de répondre en langage naturel aux questions des utilisateurs
- **Périmètre géographique**: Savoie (73), Haute-Savoie (74), Isère (38)
- **Source de données**: OpenAgenda via OpenDataSoft (~10 000 événements)

**Visual**: Map of the 3 departments with event density markers

**Speaker notes**: Explain why keyword search fails (semantic intent, temporal reasoning, multi-criteria)

---

## Slide 3 — Qu'est-ce que le RAG ?

**Title**: RAG — Retrieval-Augmented Generation

**Key points**:
- **Problème des LLM seuls**: Hallucinations, données non vérifiées, pas de source
- **Solution RAG**: Combiner recherche dans une base de données vérifiée + génération par LLM
- **3 étapes**: Retrieval (recherche) → Augmentation (contexte) → Generation (réponse naturelle)
- **Avantage clé**: Réponses fondées sur des données réelles, avec sources traçables

**Visual**: Simple 3-step diagram: User Query → Search DB → LLM + Context → Grounded Answer
Contrast with: User Query → LLM alone → Potential hallucination

**Speaker notes**: Quick explanation for non-technical audience. Emphasize the grounding aspect — answers are based on real events, not invented.

---

## Slide 4 — Architecture Technique Globale

**Title**: Architecture du système

**Visual**: Full architecture diagram (from README):
```
User Query + reference_date
    ↓
FastAPI REST API (/health, /ask, /info, /rebuild)
    ↓
RAG Service Layer (3 methods: Basic, Hybrid, Advanced)
    ↓
[FAISS Vector DB] + [BM25 Sparse] + [FlashRank Reranker]
    ↓
Temporal Pipeline: Filter → Rerank → Slice
    ↓
Mistral AI (Embeddings + LLM Generation)
    ↓
Response (answer + sources + metadata)
```

**Key components to highlight**:
- FastAPI REST API (4 endpoints)
- 3 RAG methods with progressive sophistication
- Temporal pipeline (v1.2.0)
- Mistral AI for embeddings and generation

**Speaker notes**: Walk through the data flow. Mention that the API is stateless (no request/response storage).

---

## Slide 5 — Données et Pré-traitement

**Title**: Pipeline de données

**Key points**:
- **Source**: OpenAgenda via OpenDataSoft API
- **Filtrage API-level**: Seuls les 3 départements cibles téléchargés (~3 MB au lieu de ~72 MB)
- **Filtrage temporel**: Événements depuis 2023 uniquement
- **Résultat**: ~10 648 événements indexés
- **Stratégie de chunking**: 1 événement = 1 document (cohérence sémantique, métadonnées préservées)
- **Métadonnées structurées** (v1.2.0): Dates ISO (`event_start_date`, `event_end_date`), ville, département, catégorie, URL

**Visual**: Data pipeline diagram:
```
OpenDataSoft API → Filter (departments + dates) → Clean (HTML, text) → Metadata (ISO dates) → FAISS Index
```

**Speaker notes**: Explain why 1 event = 1 document (events are semantically coherent, metadata must stay together). Mention the ISO date addition for temporal features.

---

## Slide 6 — Trois Implémentations RAG

**Title**: 3 méthodes RAG — du simple au sophistiqué

**Table**:

| Méthode | Description | Vitesse | Cas d'usage |
|---------|-------------|---------|-------------|
| **Basic** | FAISS (similarité vectorielle) | ⚡⚡⚡ ~1-2s | Requêtes standard |
| **Hybrid** | FAISS + BM25 + fusion RRF | ⚡⚡ ~2s | Noms propres, mots-clés |
| **Advanced** | Hybrid + Query Analysis + FlashRank Reranking | ⚡ ~3-4s | Requêtes complexes |

**Key insight**: Les 3 méthodes ont le même PASS rate (66.7%) mais des profils de fiabilité différents :
- Basic : 0% échec (le plus robuste)
- Advanced : le moins de résultats partiels (meilleure précision)

**Visual**: Side-by-side comparison diagram of the 3 pipelines

**Speaker notes**: Explain the trade-off: Basic is safest (never fails), Advanced is most precise. Hybrid is the recommended default.

---

## Slide 7 — Intelligence Temporelle (v1.2.0)

**Title**: Gestion du temps — "Ce weekend à Annecy ?"

**Problem**: Sans conscience temporelle, le système retourne des événements passés mélangés avec les futurs

**Solution en 6 fonctionnalités**:
1. **Dates ISO** dans les métadonnées (parsing automatique)
2. **Date de référence** via API (`reference_date`, défaut: 2024-05-16)
3. **Pipeline manuel**: retrieve → filter → rerank → generate
4. **Filtre événements passés**: exclusion automatique
5. **Reranking de proximité**: les événements les plus proches en premier (décroissance exponentielle, demi-vie = 14 jours)
6. **Analyse temporelle** (advanced): extraction de fenêtre temporelle par le LLM ("ce weekend" → 10-11 février)

**Visual**: Before/After comparison:
- Before: "Concerts à Annecy" → events from 2023 mixed with 2024
- After: Same query with reference_date → only future events, closest first

**Speaker notes**: Emphasize that no regex is used — the LLM handles temporal understanding via the prompt. Explain the "no regex" design decision briefly (combinations, vague expressions).

---

## Slide 8 — API REST et Conteneurisation

**Title**: API REST FastAPI + Docker

**Left column — API**:
- 4 endpoints: `/health`, `/api/v1/ask`, `/api/v1/rag/info`, `/api/v1/rebuild`
- Documentation Swagger automatique (`/docs`)
- Validation Pydantic (types, contraintes, erreurs explicites)
- Interface web de chat intégrée

**Right column — Docker & CI/CD**:
- Dockerfile multi-stage (image optimisée: 1.45 GB)
- docker-compose pour déploiement local
- Auto-rebuild de l'index au premier démarrage
- Pipeline GitHub Actions: Test → Build → Push → Deploy
- Serveur Hetzner Cloud (production)

**Visual**: Screenshot of Swagger UI + Docker pipeline diagram

**Speaker notes**: Demo will show a live query through the web interface. Mention the auto-rebuild feature (no data files in repo).

---

## Slide 9 — Démonstration Live

**Title**: Démo — Le système en action

**Scenario 1** (Basic):
```
POST /api/v1/ask
{"question": "Quels concerts à Annecy?", "rag_method": "basic"}
```
→ Show response with events, sources, timing

**Scenario 2** (Temporal, Hybrid):
```
POST /api/v1/ask
{"question": "Que faire ce weekend à Chambéry?", "rag_method": "hybrid", "reference_date": "2024-05-16"}
```
→ Show temporal filtering in action (only Feb 10-11 events)

**Scenario 3** (Off-topic, Advanced):
```
POST /api/v1/ask
{"question": "Comment faire une tarte aux pommes?", "rag_method": "advanced"}
```
→ Show off-topic detection and polite refusal

**Speaker notes**: Run these live via the web interface or curl. Have screenshots as backup in case of network issues.

---

## Slide 10 — Framework d'Évaluation

**Title**: Évaluation rigoureuse — LLM-as-Judge

**Methodology**:
- **64 questions annotées** (factual, complex, off-topic, vague, temporal)
- **LLM-as-Judge**: mistral-large évalue les réponses de mistral-small
- **Rubrique**: PASS / PARTIAL / FAIL (équivalence sémantique)
- **Chain-of-Thought**: Le juge explique son raisonnement pour chaque verdict

**Visual**: Pie chart or bar chart of evaluation results

**Results table**:

| Méthode | PASS | PARTIAL | FAIL |
|---------|------|---------|------|
| Basic | 66.7% | 33.3% | **0.0%** |
| Hybrid | 66.7% | 16.7% | 16.7% |
| Advanced | 66.7% | 11.1% | 16.7% |

**Key insights**:
- Factual queries: 93% PASS (excellent)
- Off-topic: 44% FAIL (known weakness)
- Basic RAG is most robust (0% failure)

**Speaker notes**: Explain that PASS = factually correct (not necessarily exhaustive). Explain why a larger model (mistral-large) judges the smaller one.

---

## Slide 11 — Tests Unitaires et Qualité

**Title**: 145 tests — Qualité et fiabilité

**Breakdown**:
- 74 tests d'indexation (FAISS, dates ISO, filtrage temporel, reranking)
- 39 tests API (endpoints, validation, erreurs, reference_date)
- 28 tests retriever (basic, hybrid, advanced, edge cases)
- 4 tests d'intégration

**Testing approach**:
- Test-Driven Development (TDD)
- `FakeEmbeddings` pour tests unitaires rapides (pas d'appel API)
- Mocks stratégiques pour isolation des composants
- CI/CD: tests exécutés automatiquement à chaque push

**Visual**: Test count evolution chart (87 → 145 with v1.2.0)

**Speaker notes**: Emphasize TDD approach — tests written before features. No API calls in unit tests (fast, free, deterministic).

---

## Slide 12 — Choix Technologiques et Justifications

**Title**: Stack technique — Pourquoi ces choix ?

| Composant | Choix | Justification |
|-----------|-------|---------------|
| **LLM** | Mistral API | Européen (RGPD), bon français, coût raisonnable |
| **Embeddings** | mistral-embed (1024 dim) | Intégration native, qualité compétitive |
| **Vector Store** | FAISS (IndexFlatL2) | Recherche exacte, simple, CPU-only, suffisant pour ~10k docs |
| **Sparse Retrieval** | BM25 (rank_bm25) | Complémente la recherche sémantique pour les mots-clés |
| **Reranking** | FlashRank | Cross-encoder léger, améliore la précision |
| **API** | FastAPI | Docs automatiques, validation Pydantic, async-ready |
| **Orchestration** | LangChain | Abstractions RAG, multi-modèle, écosystème riche |
| **Conteneurisation** | Docker | Reproductibilité, déploiement simplifié |

**Speaker notes**: Be ready to justify each choice vs alternatives. Key points: Mistral for GDPR, FAISS for POC simplicity (Chroma for production), LangChain for rapid prototyping.

---

## Slide 13 — Limites Connues et Difficultés

**Title**: Limites et défis rencontrés

**Challenges overcome**:
- ✅ Déploiement sans fichiers de données (auto-rebuild Docker)
- ✅ Requêtes temporelles (résolu en v1.2.0 — 6 features, 62 tests)
- ✅ `top_k` cosmétique (résolu — pipeline manuel)

**Remaining limitations**:
- ⚠️ Détection off-topic insuffisante (44% d'échec) — nécessite un classifieur fine-tuné
- ⚠️ Pas d'authentification API (single-user)
- ⚠️ Date de référence fixe (2024-05-16) — doit être mise à jour avec le dataset
- ⚠️ FAISS post-filtering peut retourner < top_k résultats si beaucoup d'événements passés

**Speaker notes**: Be honest about limitations. Show that you understand the trade-offs and have a plan for each limitation.

---

## Slide 14 — Perspectives d'Amélioration

**Title**: Prochaines étapes

**High priority**:
1. 🎯 **Améliorer la détection off-topic** — Classifieur binaire fine-tuné sur les requêtes événementielles
2. 🔐 **Authentification API** — JWT pour accès public sécurisé
3. 🗄️ **Migration vers Chroma** — Pré-filtrage natif par métadonnées (dates), élimine le risque pickle

**Medium priority**:
4. 🌍 **Support multilingue** — Anglais et italien (région alpine)
5. 👍 **Feedback utilisateur** — Thumbs up/down pour enrichir le dataset d'évaluation
6. 💬 **Mémoire conversationnelle** — Conversations multi-tours

**Low priority**:
7. 📊 **Métriques RAGAS** — Faithfulness, relevancy automatisées
8. ⚡ **Cache Redis** — Optimisation des requêtes fréquentes

**Visual**: Roadmap timeline or priority matrix

**Speaker notes**: Emphasize that the system is already production-ready — these are enhancements, not requirements.

---

## Slide 15 — Conclusion

**Title**: Bilan et recommandations

**Key achievements summary**:
- ✅ 3 méthodes RAG fonctionnelles (Basic, Hybrid, Advanced)
- ✅ Intelligence temporelle complète (v1.2.0)
- ✅ API REST production-ready (FastAPI, Docker, CI/CD)
- ✅ 145 tests unitaires (100% passing)
- ✅ 64 questions d'évaluation annotées
- ✅ Déploiement automatisé (GitHub Actions → Hetzner)

**Recommendation for Puls-Events**:
- Déployer avec la méthode **Hybrid** (meilleur équilibre qualité/vitesse)
- Ajouter l'authentification pour un accès public
- Mettre à jour le dataset régulièrement via `/rebuild`

**Closing statement**: Le POC démontre la faisabilité technique, la pertinence métier et la performance d'un système RAG pour les recommandations d'événements culturels.

**Visual**: Summary dashboard with key metrics

---

## Backup Slides (optional, for Q&A)

### Backup A — Reciprocal Rank Fusion (RRF)
- Formula: RRF_score(d) = Σ(1 / (k + rank_i(d))), k=60
- Why RRF: Parameter-free fusion, no weight tuning needed

### Backup B — Temporal Reranking Formula
- Score = 0.5^(|days_away| / 14)
- Event tomorrow: score ≈ 0.95
- Event in 2 weeks: score = 0.50
- Event in 1 month: score ≈ 0.25

### Backup C — Data Privacy
- API stateless: no request/response storage
- No database — only FAISS index (event data from public API)
- Mistral API calls: query sent to Mistral for embedding/generation (API terms apply)

### Backup D — Cost Analysis
- Mistral API: ~€0.002 per query (embedding + generation)
- Hetzner VPS: ~€5/month
- Total: < €10/month for POC-level traffic

---

## Presentation Tips

1. **Start with the problem** (Slide 2) — make the audience feel the pain of fragmented event discovery
2. **Demo early** (Slide 9) — show the working system before diving into technical details
3. **Be ready for questions on**:
   - Why Mistral vs OpenAI? → GDPR, cost, French language support
   - Why not Chroma? → FAISS sufficient for POC, Chroma is documented upgrade path
   - How do you handle hallucinations? → RAG grounding, explicit "no info found" response
   - What about conversation history? → Deliberate POC scope choice, documented for future
   - Performance at scale? → FAISS handles 1M+ vectors, current 10k is well within limits
4. **Close with confidence** — the system is production-ready, not just a prototype
