"""Minimal FastAPI wrapper for the local RAG pipeline.

Loads the retriever once on startup and serves a `/ask` endpoint. This keeps the
app lightweight for experimentation and containerization.
"""

import os
import sys
from functools import lru_cache
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

__root__ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if __root__ not in sys.path:
    sys.path.append(__root__)

from src.rag.config import load_config
from src.rag.run_rag import build_retriever, generate_answer

app = FastAPI(title="HUST RAG Chatbot", version="0.1.0")


class AskRequest(BaseModel):
    question: str
    top_k: Optional[int] = None


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
