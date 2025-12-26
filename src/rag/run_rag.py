"""Minimal local RAG runner for the HUST chatbot.

It loads processed markdowns plus structured program JSON, chunks them, builds a
hybrid retriever, and optionally calls an LLM to synthesize an answer.
"""

import argparse
import json
import os
import sys
from typing import Iterable, List, Sequence

from dotenv import load_dotenv

__root__ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if __root__ not in sys.path:
	sys.path.append(__root__)

from src.data.retrieval.hybrid import Document, LocalHybridRetriever
from src.data.retrieval.bkai_emb import EmbeddingModel
from .config import load_config

load_dotenv()


def chunk_text(text: str, size: int, overlap: int) -> List[str]:
	words = text.split()
	chunks: List[str] = []
	start = 0
	while start < len(words):
		end = start + size
		chunks.append(" ".join(words[start:end]))
		start = end - overlap
	return [c for c in chunks if c.strip()]


def _read_file(path: str) -> str:
	with open(path, "r", encoding="utf-8") as handle:
		return handle.read()


def load_markdown_documents(directory: str, size: int, overlap: int) -> List[Document]:
	documents: List[Document] = []
	if not os.path.isdir(directory):
		return documents

	for filename in sorted(os.listdir(directory)):
		if not filename.endswith(".md"):
			continue
		text = _read_file(os.path.join(directory, filename))
		for idx, chunk in enumerate(chunk_text(text, size=size, overlap=overlap)):
			documents.append(Document(text=chunk, metadata={"source": filename, "chunk": idx}))
	return documents


def load_program_documents(directory: str, size: int, overlap: int) -> List[Document]:
	documents: List[Document] = []
	if not os.path.isdir(directory):
		return documents

	for filename in sorted(os.listdir(directory)):
		if not filename.endswith(".json"):
			continue
		payload = json.loads(_read_file(os.path.join(directory, filename)))
		serialized = json.dumps(payload, ensure_ascii=False)
		for idx, chunk in enumerate(chunk_text(serialized, size=size, overlap=overlap)):
			documents.append(Document(text=chunk, metadata={"source": filename, "chunk": idx}))
	return documents


def build_retriever(cfg) -> LocalHybridRetriever:
	data_cfg = cfg["data"]
	model_cfg = cfg["model"]
	retr_cfg = cfg["retrieval"]

	docs = load_markdown_documents(
		data_cfg.processed_markdown_dir, size=data_cfg.chunk_size, overlap=data_cfg.chunk_overlap
	)
	docs += load_program_documents(
		data_cfg.detailed_program_dir, size=data_cfg.chunk_size, overlap=data_cfg.chunk_overlap
	)

	if not docs:
		raise FileNotFoundError("No documents found to build the index. Run data processing first.")

	embedder = EmbeddingModel(model_name=model_cfg.embedding_model, provider=model_cfg.embedding_provider)
	return LocalHybridRetriever(docs, embedder=embedder, alpha=retr_cfg.alpha)


def generate_answer(question: str, contexts: Sequence[Document], model_cfg) -> str:
	if not model_cfg.openai_api_key:
		joined = "\n\n".join([c.text for c in contexts])
		return f"(OpenAI API key not set) Top contexts:\n{joined}"

	from openai import OpenAI

	client = OpenAI(api_key=model_cfg.openai_api_key)
	context_text = "\n\n".join([c.text for c in contexts])
	messages = [
		{
			"role": "system",
			"content": (
				"You are a helpful assistant for Hanoi University of Science and Technology. "
				"Answer the question using only the provided context."
			),
		},
		{"role": "user", "content": f"Context:\n{context_text}\n\nQuestion: {question}"},
	]

	completion = client.chat.completions.create(
		model=model_cfg.openai_model,
		messages=messages,
		temperature=0.2,
	)
	return completion.choices[0].message.content or ""


def answer_question(question: str) -> str:
	cfg = load_config()
	retriever = build_retriever(cfg)
	top_docs = [doc for doc, _ in retriever.retrieve(question, top_k=cfg["retrieval"].top_k)]
	return generate_answer(question, top_docs, cfg["model"])


def parse_args():
	parser = argparse.ArgumentParser(description="Run a local RAG query against HUST data")
	parser.add_argument("--question", "-q", help="Question to ask", required=False)
	return parser.parse_args()


def main():
	args = parse_args()
	if args.question:
		print(answer_question(args.question))
	else:
		print("Enter an empty line to exit.")
		while True:
			user_q = input("Question> ").strip()
			if not user_q:
				break
			print(answer_question(user_q))


if __name__ == "__main__":
	main()
