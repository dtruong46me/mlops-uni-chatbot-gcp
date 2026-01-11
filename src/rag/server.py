"""Minimal FastAPI wrapper for the local RAG pipeline.

Loads the retriever once on startup and serves a `/ask` endpoint. This keeps the
app lightweight for experimentation and containerization.
"""

import os
import sys
from functools import lru_cache
from typing import Optional, List, Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

__root__ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if __root__ not in sys.path:
    sys.path.append(__root__)

from src.rag.config import load_config
from src.rag.run_rag import build_retriever, generate_answer
from src.rag.rerank_client import maybe_rerank_documents
from src.llm.client import get_llm_client
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import pathlib

app = FastAPI(title="HUST RAG Chatbot", version="0.1.0")

# Serve a minimal UI using Jinja templates and a static assets mount
ui_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ui"))
ui_static_dir = os.path.join(ui_root, "static")
ui_templates_dir = os.path.join(ui_root, "templates")

# serve static assets at /ui/static
if os.path.isdir(ui_static_dir):
    app.mount("/ui/static", StaticFiles(directory=ui_static_dir), name="ui_static")
else:
    print(f"UI static directory not found: {ui_static_dir}")

# render index via Jinja templates at /ui/
if os.path.isdir(ui_templates_dir):
    from fastapi.templating import Jinja2Templates
    from fastapi import Request
    templates = Jinja2Templates(directory=ui_templates_dir)

    @app.get("/ui/")
    def ui_index(request: Request):
        try:
            return templates.TemplateResponse("index.html", {"request": request, "title": "HUST Unified Chatbot"})
        except Exception:
            raise HTTPException(status_code=404, detail="UI template not available")
else:
    print(f"UI templates directory not found: {ui_templates_dir}")


@app.get("/")
def root():
    # Redirect root directly to the UI index route
    return RedirectResponse(url="/ui/")


@app.get("/ui")
def ui_plain():
    # Redirect bare /ui to the template index route
    return RedirectResponse(url="/ui/")


class AskRequest(BaseModel):
    question: str
    top_k: Optional[int] = None


class LLMRequest(BaseModel):
    prompt: str
    model: Optional[str] = None
    temperature: Optional[float] = 0.2
    max_tokens: Optional[int] = None


class ChatRequest(BaseModel):
    message: str
    use_rag: Optional[bool] = True
    top_k: Optional[int] = None
    model: Optional[str] = None
    temperature: Optional[float] = 0.2
    max_tokens: Optional[int] = None


@app.post("/chat")
def chat(payload: ChatRequest):
    """Unified chat endpoint. By default, uses RAG (retrieval + generation). Set `use_rag=false` to call the LLM directly."""
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message must not be empty")

    # If RAG mode, retrieve documents and generate an answer using contexts
    if payload.use_rag:
        cfg, retriever = _get_components()
        top_k = payload.top_k or cfg["retrieval"].top_k
        results = retriever.retrieve(payload.message, top_k=top_k)
        top_docs = [doc for doc, _ in results]

        try:
            top_docs = maybe_rerank_documents(payload.message, top_docs)
        except Exception:
            pass

        # Allow a string model override (e.g., "gpt-4o-mini"). If provided, create
        # a shallow copy of the ModelConfig with the new openai_model value so
        # generate_answer sees the expected attributes.
        model_cfg = cfg["model"]
        if payload.model and isinstance(payload.model, str):
            try:
                # Create new ModelConfig instance preserving keys
                model_cfg = type(model_cfg)(
                    embedding_model=model_cfg.embedding_model,
                    embedding_provider=model_cfg.embedding_provider,
                    openai_model=payload.model,
                    openai_api_key=model_cfg.openai_api_key,
                )
            except Exception:
                # Fallback: keep original config
                model_cfg = cfg["model"]

        answer = generate_answer(payload.message, top_docs, model_cfg)
        return {
            "answer": answer,
            "contexts": [{"text": d.text, "metadata": d.metadata} for d in top_docs],
            "source": "rag",
        }

    # Otherwise call LLM-only
    model = payload.model or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
    messages: List[Dict] = [{"role": "user", "content": payload.message}]

    import src.llm.client as llm_client_module
    client = llm_client_module.get_llm_client()
    try:
        answer = client.chat_completion(messages=messages, model=model, temperature=payload.temperature or 0.2, max_tokens=payload.max_tokens)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {"answer": answer, "contexts": [], "source": "llm"}


@lru_cache(maxsize=1)
def _get_components():
    cfg = load_config()
    retriever = build_retriever(cfg)
    return cfg, retriever


@app.post("/ask")
def ask(payload: AskRequest):
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question must not be empty")

    cfg, retriever = _get_components()
    top_k = payload.top_k or cfg["retrieval"].top_k
    results = retriever.retrieve(payload.question, top_k=top_k)
    top_docs = [doc for doc, _ in results]

    # Optionally rerank top documents using a reranker service or local reranker
    try:
        top_docs = maybe_rerank_documents(payload.question, top_docs)
    except Exception:
        # If reranking fails, continue with original order
        pass

    answer = generate_answer(payload.question, top_docs, cfg["model"])

    return {
        "answer": answer,
        "contexts": [
            {"text": d.text, "metadata": d.metadata}
            for d in top_docs
        ],
    }


@app.get("/healthz")
def health():
    return {"status": "ok"}


@app.post("/llm/answer")
def llm_answer(payload: LLMRequest):
    if not payload.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt must not be empty")

    model = payload.model or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
    messages: List[Dict] = [{"role": "user", "content": payload.prompt}]

    # Import at call time so tests can monkeypatch src.llm.client.get_llm_client
    import src.llm.client as llm_client_module
    client = llm_client_module.get_llm_client()
    try:
        answer = client.chat_completion(messages=messages, model=model, temperature=payload.temperature or 0.2, max_tokens=payload.max_tokens)
    except Exception as exc:  # pragma: no cover - runtime errors depend on env
        raise HTTPException(status_code=500, detail=str(exc))

    return {"answer": answer}
