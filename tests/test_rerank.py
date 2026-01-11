import unittest

from src.rerank_llm.reranker import Reranker

import numpy as np


class BagOfWordsEmbedder:
    def __init__(self):
        self.vocab = []

    def _tokenize(self, text: str):
        return text.lower().split()

    def _vectorize(self, text: str):
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
            self.vocab = sorted(set(token for q in queries for token in q.lower().split()))
        return [self._vectorize(q) for q in queries]


class RerankTests(unittest.TestCase):
    def test_similarity_rerank(self):
        contexts = [
            "Admissions tuition deadline",
            "Dorms and housing information",
            "Scholarship policy for freshmen",
        ]
        r = Reranker(mode="similarity")
        r.embedder = BagOfWordsEmbedder()
        ranked = r.rerank("freshmen scholarship", contexts)
        top_text, top_score = ranked[0]
        self.assertIn("Scholarship", top_text, "Top context should mention scholarship")
        self.assertGreater(top_score, 0)

    def test_cross_rerank_with_fake_model(self):
        contexts = [
            "Admissions tuition deadline",
            "Dorms and housing information",
            "Scholarship policy for freshmen",
        ]

        class FakeCross:
            def predict(self, pairs, show_progress_bar=False):
                # return scores where the 3rd context is most relevant
                return [0.1, 0.2, 0.95]

        r = Reranker(mode="cross")
        # inject fake cross encoder to avoid heavy downloads
        r._cross_model = FakeCross()
        ranked = r.rerank("freshmen scholarship", contexts)
        top_text, top_score = ranked[0]
        self.assertIn("Scholarship", top_text)
        self.assertGreater(top_score, 0)


if __name__ == "__main__":
    unittest.main()
