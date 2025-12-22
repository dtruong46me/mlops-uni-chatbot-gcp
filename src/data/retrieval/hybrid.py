"""Hybrid retrieval combining BM25 and dense embeddings."""

from typing import Iterable, List, Sequence, Tuple

import numpy as np

from .bm25 import BM25Index
from .bkai_emb import EmbeddingModel
from .types import Document


def _normalize(scores: np.ndarray) -> np.ndarray:
	if scores.size == 0:
		return scores
	min_s, max_s = float(scores.min()), float(scores.max())
	if max_s - min_s < 1e-9:
		return np.ones_like(scores)
	return (scores - min_s) / (max_s - min_s)


class LocalHybridRetriever:
	"""Local hybrid retrieval that merges sparse and dense scores."""

	def __init__(
		self,
		documents: Sequence[Document],
		embedder: EmbeddingModel | None = None,
		alpha: float = 0.55,
	):
		if not documents:
			raise ValueError("At least one document is required to build the retriever")

		self.documents = list(documents)
		self.alpha = alpha
		self.bm25 = BM25Index(self.documents)
		self.embedder = embedder or EmbeddingModel()

		# Pre-compute document embeddings once
		self.doc_embeddings = np.vstack(self.embedder.embed_documents([d.text for d in self.documents]))

	def retrieve(self, query: str, top_k: int = 5) -> List[Tuple[Document, float]]:
		bm25_results = self.bm25.query(query, top_k=max(top_k * 2, 10))
		bm25_docs, bm25_scores = zip(*bm25_results) if bm25_results else ([], [])

		# Dense scores for the same candidate set
		if bm25_docs:
			query_vec = self.embedder.embed_queries([query])[0]
			doc_vecs = self.doc_embeddings[[self.documents.index(doc) for doc in bm25_docs]]
			dense_scores = doc_vecs @ query_vec / (
				np.linalg.norm(doc_vecs, axis=1) * np.linalg.norm(query_vec) + 1e-8
			)
		else:
			dense_scores = np.array([])

		sparse_norm = _normalize(np.array(bm25_scores, dtype=float)) if bm25_scores else np.array([])
		dense_norm = _normalize(dense_scores) if dense_scores.size else np.array([])

		combined = self.alpha * sparse_norm + (1.0 - self.alpha) * dense_norm

		ranked = sorted(
			zip(bm25_docs, combined.tolist()), key=lambda item: item[1], reverse=True
		)
		return ranked[:top_k]
