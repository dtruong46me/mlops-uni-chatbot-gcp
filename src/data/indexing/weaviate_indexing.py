"""Helper to push document chunks into a Weaviate collection.

This keeps networking code separate from the core RAG runner so local tests can
stay dependency-light. It is safe to import even without Weaviate installed; an
ImportError is raised only when `index_documents` executes.
"""

import json
import os
import sys
from typing import Iterable, List

from dotenv import load_dotenv

__root__ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if __root__ not in sys.path:
	sys.path.append(__root__)

from src.data.retrieval.types import Document
from src.rag.config import DataConfig, WeaviateConfig
from src.rag.run_rag import chunk_text

load_dotenv()


def _load_documents(data_cfg: DataConfig) -> List[Document]:
	documents: List[Document] = []

	md_dir = data_cfg.processed_markdown_dir
	if os.path.isdir(md_dir):
		for filename in sorted(os.listdir(md_dir)):
			if not filename.endswith(".md"):
				continue
			with open(os.path.join(md_dir, filename), "r", encoding="utf-8") as handle:
				text = handle.read()
			for idx, chunk in enumerate(
				chunk_text(text, size=data_cfg.chunk_size, overlap=data_cfg.chunk_overlap)
			):
				documents.append(Document(text=chunk, metadata={"source": filename, "chunk": idx}))

	json_dir = data_cfg.detailed_program_dir
	if os.path.isdir(json_dir):
		for filename in sorted(os.listdir(json_dir)):
			if not filename.endswith(".json"):
				continue
			with open(os.path.join(json_dir, filename), "r", encoding="utf-8") as handle:
				payload = json.load(handle)
			serialized = json.dumps(payload, ensure_ascii=False)
			for idx, chunk in enumerate(
				chunk_text(serialized, size=data_cfg.chunk_size, overlap=data_cfg.chunk_overlap)
			):
				documents.append(Document(text=chunk, metadata={"source": filename, "chunk": idx}))

	return documents


def _ensure_client(weav_cfg: WeaviateConfig):
	try:
		import weaviate
		from weaviate.auth import AuthApiKey
	except ImportError as exc:  # pragma: no cover - defensive
		raise ImportError("Install 'weaviate-client' to use the indexing helper") from exc

	if not weav_cfg.url:
		raise ValueError("WEAVIATE_URL must be set")

	auth = AuthApiKey(api_key=weav_cfg.api_key) if weav_cfg.api_key else None
	return weaviate.Client(url=weav_cfg.url, auth_client_secret=auth)


def index_documents(data_cfg: DataConfig | None = None, weav_cfg: WeaviateConfig | None = None):
	"""Create/update the Weaviate class and push document chunks."""

	data_cfg = data_cfg or DataConfig()
	weav_cfg = weav_cfg or WeaviateConfig()

	client = _ensure_client(weav_cfg)
	class_name = weav_cfg.class_name

	# Create collection if missing
	schema = client.schema.get()
	class_names = {c["class"] for c in schema.get("classes", [])}
	if class_name not in class_names:
		client.schema.create_class(
			{
				"class": class_name,
				"description": weav_cfg.collection_description,
				"vectorizer": "none",
				"properties": [
					{"name": "text", "dataType": ["text"], "description": "Document chunk"},
					{"name": "source", "dataType": ["string"]},
					{"name": "chunk", "dataType": ["int"]},
				],
			}
		)

	docs = _load_documents(data_cfg)
	if not docs:
		raise FileNotFoundError("No documents found to index. Check processed data paths.")

	with client.batch as batch:
		batch.batch_size = 50
		for doc in docs:
			batch.add_data_object(
				data_object={
					"text": doc.text,
					"source": doc.metadata.get("source"),
					"chunk": doc.metadata.get("chunk"),
				},
				class_name=class_name,
			)

	print(f"Indexed {len(docs)} chunks into Weaviate class '{class_name}'.")


if __name__ == "__main__":  # pragma: no cover - manual execution helper
	index_documents()
