"""Central configuration for the local RAG pipeline.

Values are pulled from environment variables when present so the same code can
run locally or in CI/CD. This module is intentionally lightweight and free of
heavy imports to avoid slowing down cold starts.
"""

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

# Load values from a .env file when available so local runs mimic prod
load_dotenv()


@dataclass
class DataConfig:
	"""File system locations for source data."""

	base_dir: str = os.getenv("DATA_DIR", os.path.join(os.getcwd(), "data"))
	processed_markdown_dir: str = os.path.join(base_dir, "processed", "markitdown_pdf")
	detailed_program_dir: str = os.path.join(base_dir, "detailed_programs")
	chunk_size: int = int(os.getenv("CHUNK_SIZE", "500"))
	chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "75"))


@dataclass
class ModelConfig:
	"""Model selection for embeddings and generation."""

	embedding_model: str = os.getenv(
		"EMBEDDING_MODEL", "bkai-foundation-models/vietnamese-bi-encoder"
	)
	embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "sentence-transformers")
	openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
	openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")


@dataclass
class RetrievalConfig:
	"""Tuning parameters for retrieval scoring."""

	top_k: int = int(os.getenv("TOP_K", "5"))
	alpha: float = float(os.getenv("HYBRID_ALPHA", "0.55"))  # weight for BM25 vs embedding


@dataclass
class WeaviateConfig:
	"""Optional Weaviate configuration used by the indexing helper."""

	url: Optional[str] = os.getenv("WEAVIATE_URL")
	api_key: Optional[str] = os.getenv("WEAVIATE_API_KEY")
	class_name: str = os.getenv("WEAVIATE_CLASS", "HUSTDocChunk")
	collection_description: str = "Document chunks for HUST chatbot"


def load_config():
	"""Convenience helper to grab all config buckets at once."""

	return {
		"data": DataConfig(),
		"model": ModelConfig(),
		"retrieval": RetrievalConfig(),
		"weaviate": WeaviateConfig(),
	}
