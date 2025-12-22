"""Lightweight BM25 retrieval for local experimentation."""

import re
from typing import Iterable, List, Sequence, Tuple

import numpy as np
from rank_bm25 import BM25Okapi

from .types import Document


def _tokenize(text: str) -> List[str]:
	"""Simple whitespace + punctuation splitter for Vietnamese/English text."""

	return re.findall(r"[\w\d]+", text.lower())


class BM25Index:
	"""Wraps BM25Okapi with a friendlier API for Document objects."""

	def __init__(self, documents: Sequence[Document]):
		self.documents = list(documents)
		corpus = [_tokenize(doc.text) for doc in self.documents]
		self.index = BM25Okapi(corpus)

	def query(self, query: str, top_k: int = 5) -> List[Tuple[Document, float]]:
		tokens = _tokenize(query)
		scores = self.index.get_scores(tokens)
		order = np.argsort(scores)[::-1][:top_k]
		return [(self.documents[i], float(scores[i])) for i in order]
