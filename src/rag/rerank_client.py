"""Client helper to optionally rerank contexts via local Reranker or remote service.

Provides `maybe_rerank_documents(question, documents)` -> List[Document]
"""
from __future__ import annotations

import os
from typing import List

from dotenv import load_dotenv

load_dotenv()

import requests

from src.data.retrieval.types import Document


RERANK_URL = os.getenv("RERANK_API_URL")


def maybe_rerank_documents(question: str, documents: List[Document]) -> List[Document]:
    if not documents:
        return documents

    texts = [d.text for d in documents]

    # If an external rerank service is configured, call it
    if RERANK_URL:
        try:
            resp = requests.post(
                f"{RERANK_URL.rstrip('/')}/rerank",
                json={"question": question, "contexts": [{"text": t, "metadata": docs.metadata if (docs := documents[i]) else None} for i, t in enumerate(texts)]},
                timeout=10,
            )
            resp.raise_for_status()
            body = resp.json()
            reordered_texts = [r["text"] for r in body.get("results", [])]
            # map back to documents preserving metadata
            text_to_doc = {d.text: d for d in documents}
            return [text_to_doc[t] for t in reordered_texts if t in text_to_doc] or documents
        except Exception:
            # On failure, fall back to local or original order
            pass

    # Try local reranker
    try:
        from src.rerank_llm.reranker import Reranker

        r = Reranker()
        scored = r.rerank(question, texts)
        ordered_texts = [t for t, _ in scored]
        text_to_doc = {d.text: d for d in documents}
        return [text_to_doc[t] for t in ordered_texts if t in text_to_doc] or documents
    except Exception:
        return documents
