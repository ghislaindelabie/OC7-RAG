#!/usr/bin/env python3
"""
RAG Evaluation Script (API-based) - Puls-Events v1.2.0

Runs evaluation against a live RAG API endpoint using LLM-as-Judge.
Designed to run on the server with minimal dependencies (only requests).

Usage:
    python3 run_evaluation_api.py [--api-url URL] [--methods basic,hybrid] [--max-questions N]

Requirements:
    - Python 3.8+
    - requests library
    - MISTRAL_API_KEY environment variable (or in .env file)
    - test_questions.csv in same directory
"""

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

# =============================================================================
# CONFIGURATION
# =============================================================================

DEFAULT_API_URL = "http://localhost:8000"
MISTRAL_JUDGE_MODEL = "mistral-large-latest"
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

# LLM-as-Judge prompt
JUDGE_PROMPT = """Tu es un évaluateur expert pour un système RAG d'événements culturels.

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

Pour les questions TEMPORAL:
- Si le système interprète correctement la référence temporelle (ce weekend, demain, etc.) par rapport à la date de référence → PASS
- Si le système retourne des événements aux bonnes dates mais pas exactement ceux attendus → PASS (les événements spécifiques peuvent varier)
- Si le système ignore complètement la dimension temporelle → FAIL

Raisonne étape par étape (Chain of Thought), puis donne ton verdict final.

Format de réponse:
RAISONNEMENT: [ton analyse détaillée]
VERDICT: [PASS/PARTIAL/FAIL]"""


# =============================================================================
# FUNCTIONS
# =============================================================================

def load_env(env_path: str = ".env"):
    """Load environment variables from .env file."""
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_questions(csv_path: str) -> list:
    """Load test questions from CSV."""
    questions = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            questions.append(row)
    return questions


def call_rag_api(api_url: str, question: str, method: str, top_k: int = 5) -> dict:
    """Call the RAG API endpoint."""
    url = f"{api_url}/api/v1/ask"
    payload = {
        "question": question,
        "rag_method": method,
        "top_k": top_k,
    }

    try:
        resp = requests.post(url, json=payload, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "answer": data["answer"],
                "sources_count": len(data.get("sources", [])),
                "response_time_ms": data["metadata"]["response_time_ms"],
                "reference_date": data["metadata"].get("reference_date"),
                "error": None,
            }
        else:
            return {
                "answer": f"[HTTP {resp.status_code}] {resp.text[:200]}",
                "sources_count": 0,
                "response_time_ms": 0,
                "reference_date": None,
                "error": f"HTTP {resp.status_code}",
            }
    except requests.Timeout:
        return {
            "answer": "[TIMEOUT]",
            "sources_count": 0,
            "response_time_ms": 0,
            "reference_date": None,
            "error": "Request timed out (60s)",
        }
    except Exception as e:
        return {
            "answer": f"[ERROR] {str(e)}",
            "sources_count": 0,
            "response_time_ms": 0,
            "reference_date": None,
            "error": str(e),
        }


def call_judge(api_key: str, question: str, expected: str, generated: str) -> dict:
    """Call Mistral API for LLM-as-Judge evaluation."""
    prompt = JUDGE_PROMPT.format(
        question=question,
        expected_answer=expected,
        generated_answer=generated,
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MISTRAL_JUDGE_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }

    try:
        resp = requests.post(MISTRAL_API_URL, headers=headers, json=payload, timeout=60)
        if resp.status_code == 200:
            content = resp.json()["choices"][0]["message"]["content"]

            # Parse verdict
            verdict = "ERROR"
            if "VERDICT:" in content:
                verdict_line = content.split("VERDICT:")[-1].strip()
                for v in ["PASS", "PARTIAL", "FAIL"]:
                    if v in verdict_line.upper():
                        verdict = v
                        break

            # Parse reasoning
            reasoning = ""
            if "RAISONNEMENT:" in content:
                reasoning = content.split("RAISONNEMENT:")[-1].split("VERDICT:")[0].strip()

            return {"verdict": verdict, "reasoning": reasoning, "error": None}
        else:
            return {"verdict": "ERROR", "reasoning": f"HTTP {resp.status_code}", "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"verdict": "ERROR", "reasoning": str(e), "error": str(e)}


def print_progress(current: int, total: int, question: str, method: str, verdict: str):
    """Print progress line."""
    status = {"PASS": "✓", "PARTIAL": "~", "FAIL": "✗", "ERROR": "!"}
    symbol = status.get(verdict, "?")
    q_short = question[:50] + "..." if len(question) > 50 else question
    print(f"  [{current}/{total}] {symbol} {method:<8} {verdict:<8} {q_short}")


def calculate_stats(results: list) -> dict:
    """Calculate statistics per method and per category."""
    stats = {}

    # Per method
    methods = sorted(set(r["method"] for r in results))
    for method in methods:
        method_results = [r for r in results if r["method"] == method]
        total = len(method_results)
        pass_n = sum(1 for r in method_results if r["verdict"] == "PASS")
        partial_n = sum(1 for r in method_results if r["verdict"] == "PARTIAL")
        fail_n = sum(1 for r in method_results if r["verdict"] == "FAIL")
        error_n = sum(1 for r in method_results if r["verdict"] == "ERROR")
        avg_time = sum(r["response_time_ms"] for r in method_results) / max(total, 1)

        stats[method] = {
            "total": total,
            "pass": pass_n,
            "partial": partial_n,
            "fail": fail_n,
            "error": error_n,
            "pass_pct": (pass_n / total * 100) if total else 0,
            "partial_pct": (partial_n / total * 100) if total else 0,
            "fail_pct": (fail_n / total * 100) if total else 0,
            "avg_time_ms": avg_time,
        }

    # Per category per method
    categories = sorted(set(r["category"] for r in results))
    for method in methods:
        stats[method]["by_category"] = {}
        for cat in categories:
            cat_results = [r for r in results if r["method"] == method and r["category"] == cat]
            total = len(cat_results)
            pass_n = sum(1 for r in cat_results if r["verdict"] == "PASS")
            stats[method]["by_category"][cat] = {
                "total": total,
                "pass": pass_n,
                "pass_pct": (pass_n / total * 100) if total else 0,
            }

    return stats


def print_summary(stats: dict):
    """Print formatted summary."""
    print("\n" + "=" * 78)
    print(" " * 20 + "EVALUATION RESULTS — v1.2.0")
    print("=" * 78)
    print(f"{'Method':<12} {'PASS':<16} {'PARTIAL':<16} {'FAIL':<16} {'Avg Time':<12} {'Total':<6}")
    print("-" * 78)

    for method in sorted(stats.keys()):
        s = stats[method]
        print(
            f"{method.capitalize():<12} "
            f"{s['pass_pct']:>5.1f}% ({s['pass']:>2})   "
            f"{s['partial_pct']:>5.1f}% ({s['partial']:>2})   "
            f"{s['fail_pct']:>5.1f}% ({s['fail']:>2})   "
            f"{s['avg_time_ms']:>7.0f}ms   "
            f"{s['total']:>3}"
        )

    print("-" * 78)

    # Per category breakdown
    print("\nBreakdown by category:")
    categories = list(next(iter(stats.values()))["by_category"].keys())
    header = f"{'Category':<12}"
    for method in sorted(stats.keys()):
        header += f" {method.capitalize():<18}"
    print(header)
    print("-" * (12 + 18 * len(stats)))

    for cat in categories:
        line = f"{cat:<12}"
        for method in sorted(stats.keys()):
            c = stats[method]["by_category"][cat]
            line += f" {c['pass_pct']:>5.1f}% ({c['pass']:>2}/{c['total']:>2})     "
        print(line)

    print("=" * 78)


def export_results(results: list, stats: dict, output_dir: str):
    """Export results to CSV and JSON."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # CSV
    csv_path = os.path.join(output_dir, f"evaluation_results_{timestamp}.csv")
    fieldnames = [
        "question_id", "question", "expected_answer", "category", "difficulty",
        "method", "generated_answer", "verdict", "reasoning",
        "response_time_ms", "sources_count", "reference_date", "error",
    ]
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    print(f"  CSV: {csv_path}")

    # JSON with stats
    json_path = os.path.join(output_dir, f"evaluation_results_{timestamp}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"stats": stats, "results": results}, f, ensure_ascii=False, indent=2)
    print(f"  JSON: {json_path}")

    # Summary text
    summary_path = os.path.join(output_dir, f"evaluation_summary_{timestamp}.txt")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write("RAG EVALUATION SUMMARY — v1.2.0 (Temporal Awareness)\n")
        f.write("=" * 70 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"API URL: {args.api_url}\n")
        f.write(f"Methods: {', '.join(args.methods.split(','))}\n")
        f.write(f"Total Questions: {len(set(r['question_id'] for r in results))}\n")
        f.write("=" * 70 + "\n\n")

        for method in sorted(stats.keys()):
            s = stats[method]
            f.write(f"{method.upper()}:\n")
            f.write(f"  PASS:    {s['pass_pct']:>5.1f}% ({s['pass']}/{s['total']})\n")
            f.write(f"  PARTIAL: {s['partial_pct']:>5.1f}% ({s['partial']}/{s['total']})\n")
            f.write(f"  FAIL:    {s['fail_pct']:>5.1f}% ({s['fail']}/{s['total']})\n")
            f.write(f"  Avg response time: {s['avg_time_ms']:.0f}ms\n")

            f.write("  By category:\n")
            for cat, c in s["by_category"].items():
                f.write(f"    {cat:<12} {c['pass_pct']:>5.1f}% ({c['pass']}/{c['total']})\n")
            f.write("\n")

    print(f"  Summary: {summary_path}")
    return csv_path, json_path, summary_path


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RAG Evaluation (API-based)")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help="RAG API base URL")
    parser.add_argument("--methods", default="basic,hybrid", help="Comma-separated RAG methods to test")
    parser.add_argument("--max-questions", type=int, default=None, help="Limit number of questions")
    parser.add_argument("--output-dir", default="evaluation_results", help="Output directory")
    parser.add_argument("--csv-path", default="test_questions.csv", help="Path to test questions CSV")
    parser.add_argument("--top-k", type=int, default=5, help="Number of documents to retrieve")
    parser.add_argument("--env-file", default=".env", help="Path to .env file")
    args = parser.parse_args()

    # Load env
    load_env(args.env_file)
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        print("ERROR: MISTRAL_API_KEY not found. Set it in environment or .env file.")
        sys.exit(1)

    methods = [m.strip() for m in args.methods.split(",")]

    print("=" * 60)
    print("RAG EVALUATION — v1.2.0 (API-based)")
    print("=" * 60)
    print(f"  API URL:  {args.api_url}")
    print(f"  Methods:  {', '.join(methods)}")
    print(f"  Judge:    {MISTRAL_JUDGE_MODEL}")
    print(f"  Top-k:    {args.top_k}")

    # Check API health
    try:
        health = requests.get(f"{args.api_url}/health", timeout=10).json()
        print(f"  API:      {health['status']} ({health['index_size']} events)")
    except Exception as e:
        print(f"  ERROR: Cannot reach API at {args.api_url}: {e}")
        sys.exit(1)

    # Load questions
    questions = load_questions(args.csv_path)
    if args.max_questions:
        questions = questions[: args.max_questions]
    print(f"  Questions: {len(questions)}")
    print()

    # Run evaluation
    total_calls = len(questions) * len(methods)
    results = []
    call_num = 0
    start_time = time.time()

    for q in questions:
        for method in methods:
            call_num += 1

            # Call RAG API
            rag_result = call_rag_api(args.api_url, q["question"], method, args.top_k)

            # Call judge
            judge_result = call_judge(api_key, q["question"], q["expected_answer"], rag_result["answer"])

            result = {
                "question_id": q["id"],
                "question": q["question"],
                "expected_answer": q["expected_answer"],
                "category": q["category"],
                "difficulty": q["difficulty"],
                "method": method,
                "generated_answer": rag_result["answer"],
                "verdict": judge_result["verdict"],
                "reasoning": judge_result["reasoning"],
                "response_time_ms": rag_result["response_time_ms"],
                "sources_count": rag_result["sources_count"],
                "reference_date": rag_result["reference_date"],
                "error": rag_result["error"] or judge_result["error"],
            }
            results.append(result)

            print_progress(call_num, total_calls, q["question"], method, judge_result["verdict"])

            # Small delay to avoid rate limiting
            time.sleep(0.5)

    elapsed = time.time() - start_time
    print(f"\nCompleted {total_calls} evaluations in {elapsed:.0f}s")

    # Calculate and print stats
    stats = calculate_stats(results)
    print_summary(stats)

    # Export
    print("\nExporting results...")
    export_results(results, stats, args.output_dir)

    print(f"\nDone! Total time: {elapsed:.0f}s")
