# HUST RAG Chatbot - Complete Deployment & Operations Guide

A production-ready Retrieval-Augmented Generation (RAG) chatbot for Hanoi University of Science and Technology, deployed on Google Kubernetes Engine (GKE) with full monitoring and auto-scaling.

## 🚀 Quick Start

### Option 1: Full GCP Deployment (Recommended)
```bash
export PROJECT_ID=your-gcp-project-id
./complete_setup.sh
```

This single command does everything:
- ✅ Setup local Python environment & run tests
- ✅ Build and push Docker image to Artifact Registry
- ✅ Provision GKE cluster with Terraform
- ✅ Deploy RAG service with Helm
- ✅ Install Prometheus/Grafana monitoring
- ✅ Enable service auto-scaling (HPA)

**Total time: ~30-35 minutes**

### Option 2: Local Development Only
```bash
./start_local.sh
```
Starts the API server on `http://localhost:8000` without any GCP resources.

### Option 3: Docker Compose (With Optional Services)
```bash
docker-compose up
```
Runs RAG API, Weaviate, Prometheus, Grafana locally on Docker.

## 📊 Accessing Services

Once deployment is complete, use the monitoring script:
```bash
./access_monitoring.sh
```

This port-forwards all services and displays credentials:
- **Grafana**: http://localhost:3000 (admin/changeme)
- **Prometheus**: http://localhost:9090
- **RAG API**: http://localhost:8000

## 🧪 Testing the RAG API

### Health Check
```bash
curl http://localhost:8000/healthz
# Response: {"status":"ok"}
```

### Ask a Question
```bash
curl -X POST http://localhost:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{
    "question": "Học phí chương trình IT năm 2025?",
    "top_k": 5
  }'
```

### Response Example
```json
{
  "answer": "The IT program's tuition is 50 million VND per year...",
  "contexts": [
    {
      "text": "Program details...",
      "metadata": {"source": "IT1.json", "chunk": 0}
    }
  ]
}
```

## 🏗️ Architecture Overview

### Components

**RAG Service (FastAPI)**
- Runs on GKE with 2-5 replicas (auto-scaled)
- Retrieves documents using hybrid search (BM25 + dense embeddings)
- Generates answers using OpenAI API or self-hosted LLM

**Vector Database (Optional)**
- Weaviate for large-scale deployments
- In-memory BM25 index for local/small deployments

**Monitoring Stack**
- **Prometheus**: Metrics collection (CPU, memory, request rates)
- **Grafana**: Dashboards and visualizations
- **AlertManager**: Alert routing and notifications

**Infrastructure**
- **GKE**: Kubernetes cluster with auto-scaling node pools
- **Artifact Registry**: Container image storage
- **Terraform**: Infrastructure as Code

## 🔧 Environment Variables

### Core RAG Configuration
```bash
OPENAI_API_KEY=sk-...                          # Optional, for LLM generation
OPENAI_MODEL=gpt-4o-mini                       # LLM model name
EMBEDDING_PROVIDER=sentence-transformers       # or 'openai'
EMBEDDING_MODEL=bkai-foundation-models/vietnamese-bi-encoder
TOP_K=5                                        # Number of context chunks to retrieve
HYBRID_ALPHA=0.55                              # BM25 weight (0-1), 1-alpha = embedding weight
CHUNK_SIZE=500                                 # Words per chunk
CHUNK_OVERLAP=75                               # Overlap between chunks
```

### Weaviate Configuration (if using vector DB)
```bash
WEAVIATE_URL=http://weaviate-svc:80
WEAVIATE_API_KEY=...
WEAVIATE_CLASS=HUSTDocChunk
```

### GCP Configuration
```bash
GCP_PROJECT_ID=your-project-id
GCP_REGION=asia-southeast1
```

## 📁 Project Structure

```
mlops-uni-chatbot-gcp/
├── src/
│   ├── data/
│   │   ├── indexing/          # Weaviate indexing helper
│   │   ├── process_pdf/       # PDF → markdown conversion
│   │   ├── retrieval/         # BM25, embeddings, hybrid search
│   │   └── scraping/          # Web scraping for program data
│   └── rag/
│       ├── config.py          # Configuration dataclasses
│       ├── run_rag.py         # CLI entry point
│       └── server.py          # FastAPI server
├── data/
│   ├── processed/             # Processed markdown files
│   ├── detailed_programs/     # Program metadata (JSON)
│   └── raw/                   # Raw PDFs and downloads
├── rag-controller/
│   ├── helm-charts/
│   │   └── rag-chatbot/       # Helm chart for RAG service
│   └── terraform/             # GKE infrastructure code
├── monitoring/
│   ├── kube-prometheus-stack-values.yaml  # Prometheus config
│   ├── alerts.yaml            # Alert rules
│   └── prometheus.yml         # Prometheus scrape config
├── tests/                     # Unit tests
├── Dockerfile                 # Container image
├── docker-compose.yml         # Local orchestration
├── requirements.txt           # Python dependencies
└── Scripts
    ├── complete_setup.sh      # Full GCP deployment
    ├── start_local.sh         # Local development
    └── access_monitoring.sh   # Port-forward monitoring
```

## 🛠️ Common Operations

### Check Deployment Status
```bash
# RAG pods
kubectl -n rag get pods

# Monitoring stack
kubectl -n monitoring get pods

# HPA scaling
kubectl -n rag get hpa
```

### View Logs
```bash
# RAG service logs
kubectl -n rag logs -f deployment/rag-rag-chatbot

# Specific pod
kubectl -n rag logs POD_NAME

# Follow logs
kubectl -n rag logs -f deployment/rag-rag-chatbot --all-containers=true
```

### Scale Manually
```bash
# Set exact replicas
kubectl -n rag scale deployment rag-rag-chatbot --replicas=5

# Watch HPA scale automatically
kubectl -n rag get hpa -w
```

### Update Configuration
```bash
# Update via Helm
helm upgrade rag rag-controller/helm-charts/rag-chatbot \
  --namespace rag \
  --set configmap.data.TOP_K=10 \
  --set configmap.data.HYBRID_ALPHA=0.6
```

### Monitoring

**Access Prometheus directly:**
```bash
kubectl -n monitoring port-forward svc/prometheus-kube-prometheus-prometheus 9090:9090
# Then visit http://localhost:9090
```

**Query metrics in Prometheus UI:**
- `up{job="rag-rag-chatbot"}` - Service uptime
- `rate(http_requests_total[5m])` - Request rate
- `http_requests_total{status=~"5.."}` - Error rate
- `container_cpu_usage_seconds_total` - CPU usage

**Check alerts:**
```bash
kubectl -n monitoring port-forward svc/prometheus-kube-prom-alertmanager 9093:9093
# Then visit http://localhost:9093
```

## 🚨 Troubleshooting

### Pods not starting
```bash
kubectl -n rag describe pod POD_NAME
kubectl -n rag logs POD_NAME --previous
```

### High memory usage
```bash
# Increase limits
helm upgrade rag rag-controller/helm-charts/rag-chatbot \
  --namespace rag \
  --set resources.limits.memory=2Gi \
  --set resources.requests.memory=1Gi
```

### ServiceMonitor not scraping
```bash
# Verify ServiceMonitor exists
kubectl -n rag get servicemonitor

# Check Prometheus targets
kubectl -n monitoring port-forward svc/prometheus-kube-prometheus-prometheus 9090:9090
# Visit http://localhost:9090/targets
```

### Image pull errors
```bash
# Check image exists
gcloud artifacts docker images list REGION-docker.pkg.dev/PROJECT/chatbot

# Check Docker credentials
kubectl -n rag get events
```

## 📈 Performance Tuning

### Auto-scaling Configuration (in `values.yaml`)
```yaml
hpa:
  enabled: true
  minReplicas: 2
  maxReplicas: 5
  cpu:
    targetAverageUtilization: 70
```

### Resource Limits (in `values.yaml`)
```yaml
resources:
  limits:
    cpu: 500m
    memory: 1Gi
  requests:
    cpu: 250m
    memory: 512Mi
```

### Retrieval Tuning
```bash
# Increase context chunks
--set configmap.data.TOP_K=10

# Adjust hybrid search weight
--set configmap.data.HYBRID_ALPHA=0.4  # More embedding-based
```

## 🧹 Cleanup

### Destroy GKE Resources
```bash
cd rag-controller/terraform
terraform destroy -var project_id=YOUR_PROJECT -var region=asia-southeast1
```

### Delete Kubernetes Namespaces
```bash
kubectl delete namespace rag
kubectl delete namespace monitoring
```

## 📚 Additional Resources

- [SETUP_AND_RUN.md](SETUP_AND_RUN.md) - Detailed step-by-step guide
- [README.md](README.md) - Project overview
- [Helm Chart Documentation](rag-controller/helm-charts/rag-chatbot/README.md) - Deployment options

## 🤝 Support

For issues or questions:
1. Check logs: `kubectl logs -f deployment/rag-rag-chatbot`
2. Review configuration: `helm values rag -n rag`
3. Check events: `kubectl describe pod POD_NAME -n rag`
4. Review monitoring dashboards in Grafana

## 📝 License

This project is developed for Hanoi University of Science and Technology (HUST).
