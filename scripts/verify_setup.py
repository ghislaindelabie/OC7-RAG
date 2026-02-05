#!/usr/bin/env python3
"""
Setup verification script for OC7-RAG.

Checks:
- Environment variables
- Python dependencies
- Data files
- Directory structure

Usage:
    python scripts/verify_setup.py
"""

import os
import sys
from pathlib import Path


def print_header(text):
    """Print formatted section header."""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def print_check(name, status, detail=""):
    """Print check result."""
    symbol = "✅" if status else "❌"
    print(f"{symbol} {name}")
    if detail:
        print(f"   {detail}")


def check_env_vars():
    """Check required environment variables."""
    print_header("Environment Variables")

    # Check for .env file
    env_file = Path(".env")
    if env_file.exists():
        print_check(".env file", True, "Found")
    else:
        print_check(".env file", False, "Missing - copy from .env.example")
        return False

    # Check MISTRAL_API_KEY
    api_key = os.getenv("MISTRAL_API_KEY")
    if api_key and api_key != "your_mistral_api_key_here":
        print_check("MISTRAL_API_KEY", True, f"Set ({len(api_key)} characters)")
        success = True
    else:
        print_check("MISTRAL_API_KEY", False, "Not set or using placeholder")
        print("   Get your key from: https://console.mistral.ai/")
        success = False

    return success


def check_dependencies():
    """Check Python dependencies."""
    print_header("Python Dependencies")

    dependencies = {
        "langchain": "LangChain framework",
        "langchain_mistralai": "Mistral AI integration",
        "faiss": "FAISS vector store (faiss-cpu or faiss-gpu)",
        "fastapi": "FastAPI web framework",
        "uvicorn": "ASGI server",
        "pydantic": "Data validation",
    }

    all_ok = True
    for module, description in dependencies.items():
        try:
            __import__(module)
            print_check(module, True, description)
        except ImportError:
            print_check(module, False, f"Missing - {description}")
            all_ok = False

    if not all_ok:
        print("\n   Install dependencies: pip install -r requirements.txt")

    return all_ok


def check_data_files():
    """Check data files and index."""
    print_header("Data Files")

    # Check for FAISS index
    index_dir = Path("data/index/faiss_baseline/")
    index_file = index_dir / "index.faiss"

    if index_file.exists():
        print_check("FAISS index", True, f"Found at {index_file}")
        index_exists = True
    else:
        index_exists = False
        if index_dir.exists():
            print_check("FAISS index", False, "Directory exists but index.faiss missing")
        else:
            print_check("FAISS index", False, "Not found - will be built on first run")

    # Check for processed data
    processed_data = Path("data/processed/events_filtered.json")
    if processed_data.exists():
        size_mb = processed_data.stat().st_size / (1024 * 1024)
        print_check("Processed data", True, f"Found ({size_mb:.1f} MB)")
    else:
        print_check("Processed data", False, "Not found")

    # Check for raw data
    raw_data = Path("data/raw/evenements-publics-openagenda.json")
    if raw_data.exists():
        size_mb = raw_data.stat().st_size / (1024 * 1024)
        print_check("Raw data", True, f"Found ({size_mb:.1f} MB)")
    else:
        print_check("Raw data", False, "Not found")

    if not index_exists:
        print("\n   ℹ️  Index will be automatically built on first API startup")
        print("   ℹ️  This may take 3-5 minutes (download + embedding)")

    return True  # Data files are optional (auto-downloaded)


def check_directory_structure():
    """Check project directory structure."""
    print_header("Directory Structure")

    required_dirs = {
        "src/": "Source code",
        "src/api/": "API implementation",
        "tests/": "Test suite",
        "scripts/": "Utility scripts",
        "data/": "Data directory",
    }

    all_ok = True
    for dir_path, description in required_dirs.items():
        path = Path(dir_path)
        if path.exists():
            print_check(dir_path, True, description)
        else:
            print_check(dir_path, False, f"Missing - {description}")
            all_ok = False

    return all_ok


def check_python_version():
    """Check Python version."""
    print_header("Python Version")

    major, minor = sys.version_info[:2]
    version_str = f"Python {major}.{minor}"

    if major == 3 and minor >= 11:
        print_check(version_str, True, "Compatible")
        return True
    else:
        print_check(version_str, False, "Requires Python 3.11 or higher")
        return False


def main():
    """Run all verification checks."""
    print("\n🔍 OC7-RAG Setup Verification")
    print("=" * 60)

    checks = [
        ("Python version", check_python_version),
        ("Environment variables", check_env_vars),
        ("Dependencies", check_dependencies),
        ("Directory structure", check_directory_structure),
        ("Data files", check_data_files),
    ]

    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Error checking {name}: {e}")
            results.append((name, False))

    # Summary
    print_header("Summary")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:10} {name}")

    print(f"\n{'='*60}")
    if passed == total:
        print("✅ All checks passed! You're ready to run OC7-RAG.")
        print("\nNext steps:")
        print("  - Local: python scripts/run_api.py")
        print("  - Docker: docker compose up -d")
        print(f"{'='*60}\n")
        sys.exit(0)
    else:
        print(f"⚠️  {passed}/{total} checks passed. Fix issues above before running.")
        print(f"{'='*60}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
