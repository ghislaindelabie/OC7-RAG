#!/usr/bin/env python3
"""
RAG Evaluation Script - Puls-Events

Runs full evaluation of all 3 RAG methods (Basic, Hybrid, Advanced) against
the test dataset using LLM-as-Judge evaluation.

SYNC NOTE: This script mirrors the evaluation logic in notebooks/01_baseline_rag.ipynb
(cells 24-31). Keep both in sync when making changes.

Usage:
    python scripts/run_evaluation.py [--output-dir PATH] [--max-questions N]

Requirements:
    - conda activate OC7
    - MISTRAL_API_KEY in .env
    - data/processed/events_filtered.json exists
    - tests/test_data/test_questions.csv exists
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from tqdm import tqdm

from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_mistralai import MistralAIEmbeddings, ChatMistralAI
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever
from langchain_community.document_compressors import FlashrankRerank
from langchain_classic.chains import RetrievalQA
from langchain_classic.retrievers import EnsembleRetriever, ContextualCompressionRetriever

# =============================================================================
# CONFIGURATION
# =============================================================================

# Paths (relative to project root)
PROJECT_ROOT = Path(__file__).parent.parent
DATA_PATH = PROJECT_ROOT / "data" / "processed" / "events_filtered.json"
INDEX_PATH = PROJECT_ROOT / "data" / "index" / "faiss_baseline"
TEST_DATA_PATH = PROJECT_ROOT / "tests" / "test_data" / "test_questions.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "evaluation_results"

# RAG prompt template
RAG_PROMPT_TEMPLATE = """Tu es un assistant spécialisé dans les événements culturels de Savoie, Haute-Savoie et Isère.
Utilise les informations suivantes pour répondre à la question de l'utilisateur.
Si tu ne trouves pas l'information dans le contexte, dis-le clairement.

Contexte:
{context}

Question: {question}

Réponse détaillée:"""

# LLM-as-Judge prompt template
JUDGE_PROMPT_TEMPLATE = """Tu es un évaluateur expert pour un système RAG d'événements culturels.

Question posée: {question}
Réponse attendue: {expected_answer}
Réponse générée: {generated_answer}

Évalue la réponse générée selon ces critères:

1. EXACTITUDE: Les informations (dates, lieux, noms) sont-elles correctes?
2. PERTINENCE: La réponse répond-elle à la question posée?
3. COMPLÉTUDE: Les éléments essentiels sont-ils présents?

IMPORTANT - Critères d'évaluation:
- **PASS**: La réponse contient des événements corrects et pertinents. Les informations principales (dates, lieux, types d'événements) sont exactes. Peut inclure des événements supplémentaires valides non mentionnés dans la réponse attendue.
- **PARTIAL**: Certains événements sont corrects mais des éléments clés sont manquants, OU contient des inexactitudes mineures dans les détails, OU la réponse est incomplète mais pas fausse.
- **FAIL**: Les événements sont incorrects/inventés, mauvaises localisations/dates, réponse complètement hors sujet, ou aucune information utile fournie.

NOTE CRITIQUE: Une réponse avec moins d'événements que prévu mais tous corrects est PASS, pas PARTIAL.
Une réponse avec plus d'événements (tous valides) est aussi PASS.

Pour les questions OFF_TOPIC:
- Si le système détecte correctement que la question est hors sujet et refuse de chercher → PASS
- Si le système retourne des résultats non pertinents → FAIL
- Si le système dit "pas d'information" de manière appropriée → PARTIAL

Pour les questions VAGUE:
- Si le système demande des clarifications → PASS
- Si le système reformule intelligemment et trouve des résultats pertinents → PASS
- Si le système retourne des résultats aléatoires → FAIL

Raisonne étape par étape (Chain of Thought), puis donne ton verdict final.

Format de réponse:
RAISONNEMENT: [ton analyse détaillée]
VERDICT: [PASS/PARTIAL/FAIL]"""


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def clean_html(html_text: str) -> str:
    """Remove HTML tags from text."""
    if not html_text:
        return ""
    soup = BeautifulSoup(html_text, 'lxml')
    return soup.get_text(separator=' ', strip=True)


def build_document_text(event: dict) -> str:
    """Build comprehensive document text from event data."""
    parts = []

    title = event.get('title_fr', '')
    if title:
        parts.append(f"Événement: {title}")

    long_desc = clean_html(event.get('longdescription_fr', ''))
    short_desc = event.get('description_fr', '')
    description = long_desc if long_desc else short_desc
    if description:
        parts.append(f"Description: {description}")

    city = event.get('location_city', '')
    location_name = event.get('location_name', '')
    address = event.get('location_address', '')
    department = event.get('location_department', '')

    location_parts = []
    if location_name:
        location_parts.append(location_name)
    if address:
        location_parts.append(address)
    if city:
        location_parts.append(city)
    if department:
        location_parts.append(department)

    if location_parts:
        parts.append(f"Lieu: {', '.join(location_parts)}")

    daterange = event.get('daterange_fr', '')
    if daterange:
        parts.append(f"Date: {daterange}")

    category = event.get('category', '')
    if category:
        parts.append(f"Catégorie: {category}")

    keywords = event.get('keywords_fr', [])
    if keywords:
        parts.append(f"Mots-clés: {', '.join(keywords[:10])}")

    return '\n'.join(parts)


def build_metadata(event: dict) -> dict:
    """Extract metadata from event."""
    return {
        'uid': event.get('uid', ''),
        'title': event.get('title_fr', ''),
        'city': event.get('location_city', ''),
        'department': event.get('location_department', ''),
        'daterange': event.get('daterange_fr', ''),
        'category': event.get('category', ''),
        'url': event.get('canonicalurl', '')
    }


def load_events_as_documents(data_path: Path) -> list[Document]:
    """Load events JSON and convert to LangChain Documents."""
    print(f"Loading events from {data_path}...")
    with open(data_path, 'r', encoding='utf-8') as f:
        events = json.load(f)

    documents = []
    for event in events:
        text = build_document_text(event)
        metadata = build_metadata(event)
        if text.strip():
            documents.append(Document(page_content=text, metadata=metadata))

    print(f"  Loaded {len(documents):,} documents")
    return documents


# =============================================================================
# RAG CHAIN SETUP
# =============================================================================

def setup_rag_chains(documents: list[Document], embeddings, llm):
    """
    Set up all three RAG chains: Basic, Hybrid, Advanced.

    Returns:
        dict with 'basic', 'hybrid', 'advanced' chains and 'vectorstore'
    """
    prompt = PromptTemplate(
        template=RAG_PROMPT_TEMPLATE,
        input_variables=["context", "question"]
    )

    # Create or load FAISS index
    print("Setting up FAISS vectorstore...")
    if INDEX_PATH.exists():
        print(f"  Loading existing index from {INDEX_PATH}")
        vectorstore = FAISS.load_local(
            str(INDEX_PATH),
            embeddings,
            allow_dangerous_deserialization=True
        )
    else:
        print(f"  Creating new index...")
        vectorstore = FAISS.from_documents(documents, embeddings)
        INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        vectorstore.save_local(str(INDEX_PATH))

    # Basic RAG
    print("Setting up Basic RAG...")
    basic_retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
    basic_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=basic_retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt}
    )

    # Hybrid RAG (FAISS + BM25)
    print("Setting up Hybrid RAG...")
    bm25_retriever = BM25Retriever.from_documents(documents)
    bm25_retriever.k = 5
    faiss_retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
    ensemble_retriever = EnsembleRetriever(
        retrievers=[faiss_retriever, bm25_retriever],
        weights=[0.5, 0.5]
    )
    hybrid_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=ensemble_retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt}
    )

    # Advanced RAG (with reranking)
    print("Setting up Advanced RAG...")
    compressor = FlashrankRerank(top_n=5)
    compression_retriever = ContextualCompressionRetriever(
        base_compressor=compressor,
        base_retriever=ensemble_retriever
    )
    advanced_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=compression_retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt}
    )

    return {
        'basic': basic_chain,
        'hybrid': hybrid_chain,
        'advanced': advanced_chain,
        'vectorstore': vectorstore
    }


# =============================================================================
# EVALUATION FUNCTIONS
# =============================================================================

def run_rag_method(chain, query: str) -> dict:
    """Run a single RAG method and return result."""
    try:
        result = chain.invoke({"query": query})
        return {
            'answer': result['result'],
            'source_documents': result['source_documents'],
            'error': None
        }
    except Exception as e:
        return {
            'answer': f"[ERROR] {str(e)}",
            'source_documents': [],
            'error': str(e)
        }


def evaluate_with_judge(judge_llm, question: str, expected: str, generated: str) -> dict:
    """Evaluate a generated answer using LLM-as-Judge."""
    prompt = JUDGE_PROMPT_TEMPLATE.format(
        question=question,
        expected_answer=expected,
        generated_answer=generated
    )

    try:
        response = judge_llm.invoke(prompt)
        response_text = response.content

        # Parse verdict
        verdict = "ERROR"
        if "VERDICT:" in response_text:
            verdict_line = response_text.split("VERDICT:")[-1].strip()
            for v in ["PASS", "PARTIAL", "FAIL"]:
                if v in verdict_line.upper():
                    verdict = v
                    break

        # Parse reasoning
        reasoning = ""
        if "RAISONNEMENT:" in response_text:
            reasoning = response_text.split("RAISONNEMENT:")[-1].split("VERDICT:")[0].strip()

        return {
            'verdict': verdict,
            'reasoning': reasoning,
            'raw_response': response_text,
            'error': None
        }
    except Exception as e:
        return {
            'verdict': 'ERROR',
            'reasoning': str(e),
            'raw_response': '',
            'error': str(e)
        }


def calculate_statistics(results_df: pd.DataFrame) -> dict:
    """Calculate evaluation statistics per RAG method."""
    stats = {}

    for method in ['basic', 'hybrid', 'advanced']:
        method_results = results_df[results_df['method'] == method]
        total = len(method_results)

        if total == 0:
            stats[method] = {
                'total': 0, 'pass_count': 0, 'partial_count': 0,
                'fail_count': 0, 'error_count': 0,
                'pass_pct': 0.0, 'partial_pct': 0.0,
                'fail_pct': 0.0, 'error_pct': 0.0
            }
            continue

        pass_count = len(method_results[method_results['verdict'] == 'PASS'])
        partial_count = len(method_results[method_results['verdict'] == 'PARTIAL'])
        fail_count = len(method_results[method_results['verdict'] == 'FAIL'])
        error_count = len(method_results[method_results['verdict'] == 'ERROR'])

        stats[method] = {
            'total': total,
            'pass_count': pass_count,
            'partial_count': partial_count,
            'fail_count': fail_count,
            'error_count': error_count,
            'pass_pct': (pass_count / total) * 100,
            'partial_pct': (partial_count / total) * 100,
            'fail_pct': (fail_count / total) * 100,
            'error_pct': (error_count / total) * 100
        }

    return stats


def print_statistics(stats: dict):
    """Print formatted statistics table."""
    print("\n" + "=" * 78)
    print(" " * 28 + "EVALUATION RESULTS")
    print("=" * 78)
    print(f"{'Method':<15} {'PASS':<18} {'PARTIAL':<18} {'FAIL':<18} {'Total':<10}")
    print("-" * 78)

    for method in ['basic', 'hybrid', 'advanced']:
        s = stats[method]
        print(f"{method.capitalize():<15} "
              f"{s['pass_pct']:>5.1f}% ({s['pass_count']:>2})     "
              f"{s['partial_pct']:>5.1f}% ({s['partial_count']:>2})     "
              f"{s['fail_pct']:>5.1f}% ({s['fail_count']:>2})     "
              f"{s['total']:>3}")

    print("=" * 78)


def export_results(results_df: pd.DataFrame, stats: dict, output_dir: Path):
    """Export results to CSV, JSON, and summary text."""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # CSV
    csv_path = output_dir / f"evaluation_results_{timestamp}.csv"
    results_df.to_csv(csv_path, index=False, encoding='utf-8')
    print(f"  CSV: {csv_path}")

    # JSON
    json_path = output_dir / f"evaluation_results_{timestamp}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results_df.to_dict(orient='records'), f, ensure_ascii=False, indent=2)
    print(f"  JSON: {json_path}")

    # Summary
    summary_path = output_dir / f"evaluation_summary_{timestamp}.txt"
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("RAG EVALUATION SUMMARY REPORT\n")
        f.write("=" * 70 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Questions: {len(results_df) // 3}\n")
        f.write("=" * 70 + "\n\n")

        for method in ['basic', 'hybrid', 'advanced']:
            s = stats[method]
            f.write(f"{method.upper()}:\n")
            f.write(f"  PASS: {s['pass_pct']:.1f}% ({s['pass_count']}/{s['total']})\n")
            f.write(f"  PARTIAL: {s['partial_pct']:.1f}% ({s['partial_count']}/{s['total']})\n")
            f.write(f"  FAIL: {s['fail_pct']:.1f}% ({s['fail_count']}/{s['total']})\n\n")

    print(f"  Summary: {summary_path}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Run RAG evaluation")
    parser.add_argument('--output-dir', type=Path, default=DEFAULT_OUTPUT_DIR,
                        help="Output directory for results")
    parser.add_argument('--max-questions', type=int, default=None,
                        help="Limit number of questions (for testing)")
    args = parser.parse_args()

    # Load environment
    load_dotenv(PROJECT_ROOT / ".env")
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        print("ERROR: MISTRAL_API_KEY not found in .env")
        sys.exit(1)

    print("=" * 60)
    print("RAG EVALUATION SCRIPT")
    print("=" * 60)

    # Initialize models
    print("\nInitializing models...")
    embeddings = MistralAIEmbeddings(model="mistral-embed", api_key=api_key)
    llm = ChatMistralAI(model="mistral-small-latest", api_key=api_key, temperature=0.1)
    judge_llm = ChatMistralAI(model="mistral-large-latest", api_key=api_key, temperature=0)

    # Load documents and setup chains
    documents = load_events_as_documents(DATA_PATH)
    chains = setup_rag_chains(documents, embeddings, llm)

    # Load test data
    print(f"\nLoading test data from {TEST_DATA_PATH}...")
    test_df = pd.read_csv(TEST_DATA_PATH)
    if args.max_questions:
        test_df = test_df.head(args.max_questions)
    print(f"  {len(test_df)} questions to evaluate")

    # Run evaluation
    print("\n" + "=" * 60)
    print("RUNNING EVALUATION")
    print("=" * 60)

    all_results = []

    for idx, row in tqdm(test_df.iterrows(), total=len(test_df), desc="Questions"):
        question = row['question']
        expected = row['expected_answer']
        category = row['category']
        difficulty = row['difficulty']

        for method_name in ['basic', 'hybrid', 'advanced']:
            # Run RAG
            rag_result = run_rag_method(chains[method_name], question)

            # Evaluate with judge
            eval_result = evaluate_with_judge(
                judge_llm, question, expected, rag_result['answer']
            )

            all_results.append({
                'question_id': row['id'],
                'question': question,
                'expected_answer': expected,
                'category': category,
                'difficulty': difficulty,
                'method': method_name,
                'generated_answer': rag_result['answer'],
                'verdict': eval_result['verdict'],
                'reasoning': eval_result['reasoning'],
                'error': rag_result['error'] or eval_result['error']
            })

    # Create results DataFrame
    results_df = pd.DataFrame(all_results)

    # Calculate and print statistics
    stats = calculate_statistics(results_df)
    print_statistics(stats)

    # Export results
    print("\nExporting results...")
    export_results(results_df, stats, args.output_dir)

    print("\n" + "=" * 60)
    print("EVALUATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
