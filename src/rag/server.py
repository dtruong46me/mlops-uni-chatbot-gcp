"""Minimal FastAPI wrapper for the local RAG pipeline.

Loads the retriever once on startup and serves a `/ask` endpoint. This keeps the
app lightweight for experimentation and containerization.
"""

import os
import sys
from functools import lru_cache
from typing import Optional, List, Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

__root__ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if __root__ not in sys.path:
    sys.path.append(__root__)

from src.rag.config import load_config
from src.rag.run_rag import build_retriever, generate_answer
from src.rag.rerank_client import maybe_rerank_documents
from src.llm.client import get_llm_client
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import pathlib

app = FastAPI(title="HUST RAG Chatbot", version="0.1.0")

# Serve a minimal UI at /ui
ui_static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ui", "static"))
if os.path.isdir(ui_static_dir):
    app.mount("/ui", StaticFiles(directory=ui_static_dir), name="ui")


@app.get("/")
def root():
    # Redirect root to the UI for convenience
    return RedirectResponse(url="/ui/")


class AskRequest(BaseModel):
    question: str
    top_k: Optional[int] = None


class LLMRequest(BaseModel):
    prompt: str
    model: Optional[str] = None
    temperature: Optional[float] = 0.2
    max_tokens: Optional[int] = None


@lru_cache(maxsize=1)
def _get_components():
    cfg = load_config()
    retriever = build_retriever(cfg)
    return cfg, retriever


@app.post("/ask")
def ask(payload: AskRequest):
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question must not be empty")

    cfg, retriever = _get_components()
    top_k = payload.top_k or cfg["retrieval"].top_k
    results = retriever.retrieve(payload.question, top_k=top_k)
    top_docs = [doc for doc, _ in results]

    # Optionally rerank top documents using a reranker service or local reranker
    try:
        top_docs = maybe_rerank_documents(payload.question, top_docs)
    except Exception:
        # If reranking fails, continue with original order
        pass

    answer = generate_answer(payload.question, top_docs, cfg["model"])

    return {
        "answer": answer,
        "contexts": [
            {"text": d.text, "metadata": d.metadata}
            for d in top_docs
        ],
    }


@app.get("/healthz")
def health():
    return {"status": "ok"}


@app.post("/llm/answer")
def llm_answer(payload: LLMRequest):
    if not payload.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt must not be empty")

    model = payload.model or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
    messages: List[Dict] = [{"role": "user", "content": payload.prompt}]

    client = get_llm_client()
    try:
        answer = client.chat_completion(messages=messages, model=model, temperature=payload.temperature or 0.2, max_tokens=payload.max_tokens)
    except Exception as exc:  # pragma: no cover - runtime errors depend on env
        raise HTTPException(status_code=500, detail=str(exc))

    return {"answer": answer}
