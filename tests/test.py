import unittest

import numpy as np

from src.data.retrieval.bm25 import BM25Index
from src.data.retrieval.hybrid import Document, LocalHybridRetriever
from src.rag.run_rag import chunk_text


class BagOfWordsEmbedder:
	"""Deterministic embedding model for tests (no external downloads)."""

	def __init__(self):
		self.vocab: list[str] = []

	def _tokenize(self, text: str) -> list[str]:
		return text.lower().split()

	def _vectorize(self, text: str) -> np.ndarray:
		vec = np.zeros(len(self.vocab), dtype=float)
		for token in self._tokenize(text):
			if token in self.vocab:
				vec[self.vocab.index(token)] += 1.0
		norm = np.linalg.norm(vec)
		return vec if norm == 0 else vec / norm

	def embed_documents(self, texts):
		tokens = set()
		for text in texts:
			tokens.update(self._tokenize(text))
		self.vocab = sorted(tokens)
		return [self._vectorize(text) for text in texts]

	def embed_queries(self, queries):
		if not self.vocab:
			# Build a tiny default vocab to avoid zero-size vectors
			self.vocab = sorted(set(token for q in queries for token in self._tokenize(q)))
		return [self._vectorize(query) for query in queries]


class ChunkingTests(unittest.TestCase):
	def test_chunking_overlap(self):
		text = "one two three four five six seven eight nine ten"
		chunks = chunk_text(text, size=4, overlap=2)
		self.assertGreaterEqual(len(chunks), 3)
		self.assertEqual(chunks[0], "one two three four")
		self.assertTrue(chunks[1].startswith("three four"))


class RetrievalTests(unittest.TestCase):
	def setUp(self):
		self.documents = [
			Document(text="admissions tuition deadline", metadata={"id": 1}),
			Document(text="dormitory housing information", metadata={"id": 2}),
			Document(text="scholarship policy for freshmen", metadata={"id": 3}),
		]

	def test_bm25_prefers_relevant_doc(self):
		bm25 = BM25Index(self.documents)
		results = bm25.query("tuition fee", top_k=2)
		top_doc, score = results[0]
		self.assertEqual(top_doc.metadata["id"], 1)
		self.assertGreater(score, 0)

	def test_hybrid_returns_top_context(self):
		retriever = LocalHybridRetriever(self.documents, embedder=BagOfWordsEmbedder(), alpha=0.5)
		top_doc, score = retriever.retrieve("freshmen scholarship", top_k=1)[0]
		self.assertEqual(top_doc.metadata["id"], 3)
		self.assertGreater(score, 0)


if __name__ == "__main__":
	unittest.main()
