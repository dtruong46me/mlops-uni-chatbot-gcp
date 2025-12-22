"""Embedding helper that defaults to a multilingual sentence-transformer.

If `EMBEDDING_PROVIDER=openai` is set, it will fall back to the OpenAI
Embeddings API. This keeps the code flexible between local and hosted runs.
"""

import os
from typing import Iterable, List, Sequence

import numpy as np

from dotenv import load_dotenv

load_dotenv()


class EmbeddingModel:
	"""Unified interface to produce dense embeddings for text inputs."""

	def __init__(
		self,
		model_name: str | None = None,
		provider: str | None = None,
		openai_api_key: str | None = None,
	):
		self.provider = (provider or os.getenv("EMBEDDING_PROVIDER") or "sentence-transformers").lower()
		self.model_name = model_name or os.getenv(
			"EMBEDDING_MODEL", "bkai-foundation-models/vietnamese-bi-encoder"
		)
		self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")

		if self.provider == "openai":
			try:
				from openai import OpenAI
			except ImportError as exc:  # pragma: no cover - defensive
				raise ImportError("openai package required for OpenAI embeddings") from exc

			if not self.openai_api_key:
				raise ValueError("OPENAI_API_KEY must be set for OpenAI embeddings")

			self.client = OpenAI(api_key=self.openai_api_key)
			self._embedding_fn = self._embed_openai
		else:
			try:
				from sentence_transformers import SentenceTransformer
			except ImportError as exc:  # pragma: no cover - defensive
				raise ImportError(
					"sentence-transformers package is required for local embeddings"
				) from exc

			self.model = SentenceTransformer(self.model_name)
			self._embedding_fn = self._embed_sentence_transformer

	def _embed_sentence_transformer(self, texts: Sequence[str]) -> List[np.ndarray]:
		return [np.array(vec, dtype=float) for vec in self.model.encode(list(texts), convert_to_numpy=True)]

	def _embed_openai(self, texts: Sequence[str]) -> List[np.ndarray]:
		response = self.client.embeddings.create(model=self.model_name, input=list(texts))
		return [np.array(item.embedding, dtype=float) for item in response.data]  # type: ignore

	def embed_documents(self, texts: Sequence[str]) -> List[np.ndarray]:
		return self._embedding_fn(texts)

	def embed_queries(self, queries: Sequence[str]) -> List[np.ndarray]:
		return self._embedding_fn(queries)
