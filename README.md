# HUST RAG Chatbot on GCP

Retrieval-Augmented Generation (RAG) chatbot for Hanoi University of Science and Technology. It ingests official admissions PDFs and program pages, builds a hybrid retriever (BM25 + dense embeddings), and deploys to GCP via Terraform/Helm with full monitoring and auto-scaling.

## ⚡ Quick Start

**Full deployment (GCP + monitoring + auto-scaling):**
```bash
export PROJECT_ID=your-gcp-project-id
./complete_setup.sh
```

**⚠️ Note on Performance**: Current setup uses CPU-only nodes. Embedding inference is slow (5-10s). For **10-20x faster responses**, add GPU nodes. See [GPU_OPTIMIZATION.md](GPU_OPTIMIZATION.md).

**Local development only:**
```bash
./start_local.sh
```

**Access monitoring (Grafana/Prometheus/API):**
```bash
./access_monitoring.sh
```

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for complete documentation.

## Quickstart (local)
- Create a Python 3.10+ env and install deps: `pip install -r requirements.txt` (or install `rank-bm25`, `sentence-transformers`, `openai`, `python-dotenv`, `markitdown`, `beautifulsoup4`, `requests`).
- Put raw PDFs under `data/raw/pdf/` (see filenames in `src/data/process_pdf/markitdown_pdf.py`).
- Convert PDFs to markdown: `python src/data/process_pdf/markitdown_pdf.py` → outputs to `data/processed/markitdown_pdf/`.
- Scrape program metadata (optional; files already provided):
	- `python src/data/scraping/hust_programs.py`
	- `python src/data/scraping/detailed_hust_programs.py`
 - Run a question locally:
   - `python -m src.rag.run_rag -q "Học phí chương trình IT năm 2025?"`
   - If `OPENAI_API_KEY` is unset you will see the top retrieved contexts instead of a generated answer.

## Quick Scripts

- **`./complete_setup.sh`** – Full end-to-end GCP deployment (10 automated steps)
  - Local Python setup + tests
  - Build and push Docker image
  - Provision GKE cluster with Terraform
  - Deploy RAG service and monitoring
  - Configure auto-scaling and ServiceMonitor
  
- **`./start_local.sh`** – Local development (no GCP)
  - Setup venv, install deps, run tests
  - Start FastAPI server on :8000
  
- **`./access_monitoring.sh`** – Port-forward all services
  - Grafana (3000), Prometheus (9090), RAG API (8000)
  - Display Grafana credentials

## Environment variables
- `OPENAI_API_KEY` (optional) – enables answer generation.
- `OPENAI_MODEL` – default `gpt-4o-mini`.
- `EMBEDDING_PROVIDER` – `sentence-transformers` (default) or `openai`.
- `EMBEDDING_MODEL` – default `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`.
- Retrieval tuning: `TOP_K` (default 5), `HYBRID_ALPHA` (BM25 weight, default 0.55), `CHUNK_SIZE` (default 500 words), `CHUNK_OVERLAP` (default 75 words).
- Weaviate (for remote indexing): `WEAVIATE_URL`, `WEAVIATE_API_KEY`, `WEAVIATE_CLASS`.

## Indexing to Weaviate (optional)
```
python -m src.data.indexing.weaviate_indexing
```
Requires `weaviate-client` installed and the Weaviate env vars set. Chunks are inserted into `WEAVIATE_CLASS` (default `HUSTDocChunk`).

## Project layout
- `src/data/process_pdf/markitdown_pdf.py` – converts raw PDFs to markdown.
- `src/data/scraping/*.py` – scrapes program listings and detailed program pages.
- `src/data/retrieval/` – BM25, embeddings, and hybrid retriever utilities.
- `src/rag/run_rag.py` – CLI entry for local RAG.
- `rag-controller/` – Helm/GKE scaffolding (placeholder).
- `gce/`, `monitoring/`, `weaviate/` – IaC/observability placeholders.

## Testing
Run `python -m unittest tests.test`.

## LLMOps / Infrastructure

- **Container & Helm**: `Dockerfile` packages the FastAPI RAG API (`src/rag/server.py`). Deploy via Helm chart `rag-controller/helm-charts/rag-chatbot` with configurable image, env, ConfigMap, Secret, HPA, Ingress, and ServiceMonitor for Prometheus.

- **Terraform (GKE)**: `rag-controller/terraform` provisions a regional GKE cluster with auto-scaling node pool. Usage:
  ```bash
  cd rag-controller/terraform
  terraform apply -var project_id=YOUR_PROJECT -var region=asia-southeast1
  ```

- **Monitoring**: Prometheus + Grafana + AlertManager via `kube-prometheus-stack`. Includes alert rules for 5xx errors and high CPU. ServiceMonitor auto-configured for RAG service.

- **Auto-scaling**: HPA configured to scale 2–5 replicas based on CPU utilization (70% target).

## Testing

```bash
python -m unittest tests.test -v
```

## CI/CD

`Jenkinsfile` contains a 5-stage pipeline:
1. Checkout code
2. Install dependencies
3. Lint (compileall)
4. Run unit tests
5. Build and push Docker image
6. Deploy via Helm to GKE

Requires Jenkins credentials: `gcr-service-account-json` (service account JSON) and env vars `GCP_PROJECT_ID`, `GCP_REGION`, optional `K8S_NAMESPACE`.
