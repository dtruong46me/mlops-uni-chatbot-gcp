"""Simple FastAPI service for re-ranking contexts.

POST /rerank
Payload: {"question": str, "contexts": [{"text": str, "metadata": {...}}, ...]}
Response: {"results": [{"text": str, "metadata": {...}, "score": float}, ...]}

Modes: similarity (default) or openai controlled by RERANK_MODE env var.
"""
from __future__ import annotations

import os
from typing import List, Dict, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="HUST Rerank LLM", version="0.1")


class ContextIn(BaseModel):
    text: str
    metadata: Dict[str, Any] | None = None


class RerankRequest(BaseModel):
    question: str
    contexts: List[ContextIn]


class ContextOut(BaseModel):
    text: str
    metadata: Dict[str, Any] | None = None
    score: float


class RerankResponse(BaseModel):
    results: List[ContextOut]


@app.post("/rerank", response_model=RerankResponse)
def rerank(req: RerankRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question must not be empty")

    from src.rerank_llm.reranker import Reranker

    try:
        r = Reranker()
        texts = [c.text for c in req.contexts]
        scored = r.rerank(req.question, texts)
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=str(exc))

    results = []
    # scored is list of (text, score) sorted desc
    text_to_meta = {c.text: c.metadata for c in req.contexts}
    for text, score in scored:
        results.append(ContextOut(text=text, metadata=text_to_meta.get(text, None), score=float(score)))

    return RerankResponse(results=results)
