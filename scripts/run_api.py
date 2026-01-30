#!/usr/bin/env python
"""
Run the RAG API development server.

Usage:
    python scripts/run_api.py
"""

import os
import sys
from pathlib import Path

# Add src to path to allow imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import uvicorn

# Environment-based configuration
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

if __name__ == "__main__":
    print("=" * 60)
    print("Starting Puls-Events RAG API Development Server")
    print("=" * 60)
    print()
    print("API Documentation:")
    print("  - Swagger UI: http://localhost:8000/docs")
    print("  - ReDoc:      http://localhost:8000/redoc")
    print("  - Health:     http://localhost:8000/health")
    print()
    print("Press CTRL+C to stop")
    print("=" * 60)
    print()

    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=DEBUG,  # Only reload in debug mode (set DEBUG=true env var)
        log_level="info"
    )
