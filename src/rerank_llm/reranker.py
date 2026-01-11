"""Reranker helper to score and re-order contexts for a query.

Modes:
- "similarity" (default): use embedding cosine similarity between query and context text
- "openai": call OpenAI chat completions to ask the model to score each context
- "cross": use a Hugging Face Cross-Encoder (sentence_transformers.CrossEncoder) to score (query, context) pairs
"""
from __future__ import annotations

import os
from typing import List, Sequence, Tuple
import re

import numpy as np

from dotenv import load_dotenv

load_dotenv()

from src.data.retrieval.bkai_emb import EmbeddingModel


class Reranker:
    def __init__(self, mode: str | None = None, model_name: str | None = None, provider: str | None = None, openai_api_key: str | None = None):
        self.mode = (mode or os.getenv("RERANK_MODE") or "similarity").lower()
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.embedder = EmbeddingModel(model_name=model_name, provider=provider)
        # Model used for cross-encoder mode (optional)
        self.model_name = model_name or os.getenv("RERANK_MODEL")
        self._cross_model = None

    def _cosine_scores(self, query: str, contexts: Sequence[str]) -> List[float]:
        # Ensure document embeddings are created first so the embedder's vocab
        # is built from the contexts (avoids query/doc vector size mismatch).
        doc_vecs = np.vstack(self.embedder.embed_documents(list(contexts)))
        query_vec = self.embedder.embed_queries([query])[0]
        dots = doc_vecs @ query_vec
        norms = (np.linalg.norm(doc_vecs, axis=1) * np.linalg.norm(query_vec) + 1e-8)
        sims = (dots / norms).tolist()
        return sims

    def _openai_score(self, question: str, contexts: Sequence[str]) -> List[float]:
        # Light wrapper: ask the model to assign a relevance score 0-1 for each context.
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - defensive
            raise ImportError("openai package required for OpenAI reranker") from exc

        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY must be set for openai reranking mode")

        client = OpenAI(api_key=self.openai_api_key)

        prompt = (
            "You are a relevance scoring assistant. For the given question, score each provided context "
            "with a float between 0 and 1 where 1.0 is highly relevant. Return a JSON array of numbers only.\n\n"
            f"Question: {question}\n\n"
            "Contexts:\n"
        )
        for i, c in enumerate(contexts, start=1):
            prompt += f"[{i}] {c}\n"

        messages = [
            {"role": "system", "content": "You score contexts for relevance to a question."},
            {"role": "user", "content": prompt},
        ]

        completion = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=messages,
            temperature=0.0,
            max_tokens=256,
        )

        text = completion.choices[0].message.content or ""
        # Try to extract JSON array from response
        import json

        try:
            scores = json.loads(text)
            if isinstance(scores, list) and all(isinstance(s, (int, float)) for s in scores):
                return [float(s) for s in scores]
        except Exception:
            pass

        # Fallback: crude parse numbers from the response
        nums = [float(x) for x in re.findall(r"[0-9]*\.?[0-9]+", text)]
        return nums[: len(contexts)] if nums else [0.0] * len(contexts)

    def _normalize(self, scores: np.ndarray) -> List[float]:
        if scores.size == 0:
            return []
        min_s, max_s = float(scores.min()), float(scores.max())
        if max_s - min_s < 1e-9:
            return [1.0 for _ in range(scores.size)]
        return ((scores - min_s) / (max_s - min_s)).tolist()

    def _cross_scores(self, query: str, contexts: Sequence[str]) -> List[float]:
        # Use Hugging Face CrossEncoder to score (query, context) pairs.
        if not contexts:
            return []

        # Allow tests to inject a fake cross model via self._cross_model
        model = getattr(self, "_cross_model", None)
        if model is None:
            try:
                from sentence_transformers import CrossEncoder
            except ImportError as exc:  # pragma: no cover - defensive
                raise ImportError("sentence-transformers is required for cross-encoder reranking") from exc

            model_name = self.model_name or "cross-encoder/ms-marco-MiniLM-L-6-v2"
            model = CrossEncoder(model_name)
            self._cross_model = model

        pairs = [(query, c) for c in contexts]
        raw_scores = np.array(model.predict(pairs, show_progress_bar=False))
        return self._normalize(raw_scores)

    def rerank(self, question: str, contexts: Sequence[str]) -> List[Tuple[str, float]]:
        """Return list of (context, score) sorted by descending score."""
        if not contexts:
            return []

        if self.mode == "openai":
            scores = self._openai_score(question, contexts)
        elif self.mode in ("cross", "cross-encoder"):
            scores = self._cross_scores(question, contexts)
        else:
            scores = self._cosine_scores(question, contexts)

        paired = list(zip(contexts, [float(s) for s in scores]))
        paired.sort(key=lambda x: x[1], reverse=True)
        return paired
