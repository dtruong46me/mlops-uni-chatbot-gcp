#!/bin/bash

# Local development quick start (without GCP deployment)

set -e

echo "=== HUST RAG Chatbot - Local Quick Start ==="

# Setup venv
echo "[1/4] Setting up Python environment..."
python3 -m venv .venv
source .venv/bin/activate
pip install -q -r requirements.txt
echo "✓ Dependencies installed"

# Run tests
echo "[2/4] Running tests..."
python -m unittest tests.test -q && echo "✓ All tests passed" || echo "⚠ Some tests failed"

# Start API server
echo "[3/4] Starting FastAPI server on port 8000..."
echo "Press Ctrl+C to stop"
echo ""
echo "Test endpoints:"
echo "  curl http://localhost:8000/healthz"
echo "  curl -X POST http://localhost:8000/ask -H 'Content-Type: application/json' -d '{\"question\":\"Học phí?\"}'"
echo ""

uvicorn src.rag.server:app --host 0.0.0.0 --port 8000 --reload
