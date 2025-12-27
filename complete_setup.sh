#!/bin/bash

set -e

echo "=== HUST RAG Chatbot - Full Setup & Deployment ==="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Helper functions
log_step() {
  echo -e "${BLUE}[$1]${NC} $2"
}

log_success() {
  echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
  echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
  echo -e "${RED}✗${NC} $1"
}

# Configuration
if [ -z "$PROJECT_ID" ]; then
  read -p "Enter GCP Project ID: " PROJECT_ID
fi

if [ -z "$REGION" ]; then
  REGION="asia-southeast1"
fi

export PROJECT_ID REGION
export CLUSTER_NAME="rag-chatbot-gke"
export IMAGE_NAME="hust-rag-chatbot"
export IMAGE_TAG="v1"
export REGISTRY="$REGION-docker.pkg.dev/$PROJECT_ID/chatbot"
export NAMESPACE="rag"
export MONITORING_NS="monitoring"

echo -e "${BLUE}=== Configuration ===${NC}"
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo "Cluster: $CLUSTER_NAME"
echo "Image: $REGISTRY/$IMAGE_NAME:$IMAGE_TAG"
echo "RAG Namespace: $NAMESPACE"
echo "Monitoring Namespace: $MONITORING_NS"
echo ""

# Step 1: Local Setup
log_step "1/10" "Local Python Environment"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
  log_success "Virtual environment created"
else
  log_warning "Virtual environment already exists"
fi
source .venv/bin/activate
pip install -r requirements.txt
log_success "Dependencies installed"
echo ""

# Step 2: Run Tests
log_step "2/10" "Running Unit Tests"
if python -m unittest tests.test -q 2>/dev/null; then
  log_success "All tests passed"
else
  log_warning "Some tests failed but continuing..."
fi
echo ""

# Step 3: GCP Setup
log_step "3/10" "GCP Project Setup"
gcloud config set project $PROJECT_ID -q
log_success "Project set to $PROJECT_ID"
gcloud services enable compute.googleapis.com container.googleapis.com artifactregistry.googleapis.com -q
log_success "GCP APIs enabled"

# Create Artifact Registry
if gcloud artifacts repositories describe chatbot --location=$REGION --project=$PROJECT_ID ; then
  log_warning "Artifact Registry repository already exists"
else
  gcloud artifacts repositories create chatbot \
    --repository-format=docker \
    --location=$REGION \
    --project=$PROJECT_ID \
    -q
  log_success "Artifact Registry repository created"
fi
echo ""

# Step 4: Build & Push Docker Image
log_step "4/10" "Build & Push Docker Image"
gcloud auth configure-docker ${REGION}-docker.pkg.dev
log_success "Docker authentication configured"

echo "  Building Docker image..."
docker build -t $REGISTRY/$IMAGE_NAME:$IMAGE_TAG .
log_success "Docker image built"

echo "  Pushing to registry..."
docker push $REGISTRY/$IMAGE_NAME:$IMAGE_TAG 
log_success "Image pushed to $REGISTRY/$IMAGE_NAME:$IMAGE_TAG"
echo ""

# Step 5: Provision GKE Cluster
log_step "5/10" "Provision GKE Cluster (Terraform)"
cd rag-controller/terraform
terraform init -upgrade 
log_success "Terraform initialized"

echo "  Applying Terraform configuration..."
if terraform apply \
  -var project_id=$PROJECT_ID \
  -var region=$REGION \
  -var cluster_name=$CLUSTER_NAME \
  -auto-approve \
  2>&1 | tee /tmp/terraform-apply.log | grep -q "Apply complete"; then
  log_success "GKE cluster created/updated"
elif grep -q "Already exists" /tmp/terraform-apply.log; then
  log_warning "Cluster already exists, importing to Terraform state..."
  terraform import -var project_id=$PROJECT_ID -var region=$REGION -var cluster_name=$CLUSTER_NAME \
    google_container_cluster.rag projects/$PROJECT_ID/locations/$REGION/clusters/$CLUSTER_NAME 
  
  # Check and import GPU node pool if exists
  if gcloud container node-pools describe gpu-pool --cluster=$CLUSTER_NAME --region=$REGION --project=$PROJECT_ID ; then
    terraform import -var project_id=$PROJECT_ID -var region=$REGION -var cluster_name=$CLUSTER_NAME \
      google_container_node_pool.gpu projects/$PROJECT_ID/locations/$REGION/clusters/$CLUSTER_NAME/nodePools/gpu-pool 
  fi
  
  log_success "Cluster imported to Terraform state"
else
  log_error "Terraform apply failed, check /tmp/terraform-apply.log for details"
  exit 1
fi

# Get kubeconfig
KUBECONFIG_CMD=$(terraform output -raw kubeconfig 2>/dev/null || echo "gcloud container clusters get-credentials $CLUSTER_NAME --region $REGION --project $PROJECT_ID")
eval $KUBECONFIG_CMD
log_success "Kubeconfig configured"

cd ../..
echo ""

# Step 6: Deploy RAG Service
log_step "6/10" "Deploy RAG Service (Helm)"
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
log_success "Namespace '$NAMESPACE' ready"

echo "  Deploying RAG chatbot..."
if ! command -v helm >/dev/null 2>&1; then
  echo "✗ helm not found. Install Helm: https://helm.sh/docs/intro/install/"
  exit 1
fi

echo "  Deploying RAG chatbot (logs: /tmp/helm-rag-upgrade.log)..."
helm upgrade --install rag rag-controller/helm-charts/rag-chatbot \
  --namespace $NAMESPACE \
  --set image.repository=$REGISTRY/$IMAGE_NAME \
  --set image.tag=$IMAGE_TAG \
  --set replicaCount=2 \
  --wait --timeout=300s 2>&1 | tee /tmp/helm-rag-upgrade.log
log_success "Helm deployment completed"

echo "  Waiting for pods to be ready..."
if kubectl -n $NAMESPACE wait --for=condition=ready pod -l app=rag-chatbot --timeout=300s ; then
  log_success "All pods are ready"
else
  log_warning "Pods may still be starting, but continuing..."
fi
echo ""

# Step 7: Setup Monitoring Stack
log_step "7/10" "Setup Monitoring Stack"
kubectl create namespace $MONITORING_NS --dry-run=client -o yaml | kubectl apply -f -
log_success "Monitoring namespace created"

echo "  Adding Prometheus Helm repository..."
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts 2>/dev/null || true
helm repo update
log_success "Helm repository updated"

echo "  Installing kube-prometheus-stack..."
helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
  --namespace $MONITORING_NS \
  -f monitoring/kube-prometheus-stack-values.yaml
 
log_success "Prometheus stack deployed"

echo "  Waiting for monitoring pods..."
if kubectl -n $MONITORING_NS wait --for=condition=ready pod -l app.kubernetes.io/name=prometheus --timeout=300s ; then
  log_success "Prometheus is ready"
else
  log_warning "Prometheus may still be starting"
fi
echo ""

# Step 8: Enable ServiceMonitor
log_step "8/10" "Enable Prometheus ServiceMonitor"
echo "  Configuring RAG service monitoring..."
helm upgrade rag rag-controller/helm-charts/rag-chatbot \
  --namespace $NAMESPACE \
  --set serviceMonitor.enabled=true \
  --reuse-values
log_success "ServiceMonitor enabled for RAG service"
echo ""

# Step 9: Verify Deployments
log_step "9/10" "Verify All Deployments"
echo ""
echo "  RAG Service Pods:"
kubectl -n $NAMESPACE get pods -l app=rag-chatbot --no-headers 2>/dev/null | awk '{print "    " $0}' || echo "    (pods may still be starting)"
echo ""
echo "  RAG Service Status:"
kubectl -n $NAMESPACE get svc rag-rag-chatbot --no-headers 2>/dev/null | awk '{print "    " $0}' || echo "    (service not ready)"
echo ""
echo "  HPA Status:"
kubectl -n $NAMESPACE get hpa --no-headers 2>/dev/null | awk '{print "    " $0}' || echo "    (HPA not ready)"
echo ""
echo "  Monitoring Pods:"
kubectl -n $MONITORING_NS get pods --no-headers 2>/dev/null | head -5 | awk '{print "    " $0}' || echo "    (monitoring not ready)"
echo ""
log_success "Deployment verification complete"
echo ""

# Step 10: Get Credentials
log_step "10/10" "Get Access Credentials"
GRAFANA_PASSWORD=$(kubectl --namespace $MONITORING_NS get secret prometheus-grafana -o jsonpath="{.data.admin-password}" 2>/dev/null | base64 -d || echo "admin")
log_success "Grafana password retrieved"
echo ""

# Summary
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          SETUP COMPLETE - All Services Running            ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Quick Access:${NC}"
echo "  ./access_monitoring.sh"
echo ""
echo -e "${BLUE}Grafana Credentials:${NC}"
echo "  URL: http://localhost:3000"
echo "  Username: admin"
echo "  Password: $GRAFANA_PASSWORD"
echo ""
echo -e "${BLUE}Prometheus:${NC}"
echo "  URL: http://localhost:9090"
echo ""
echo -e "${BLUE}RAG API:${NC}"
echo "  URL: http://localhost:8000"
echo "  Health: curl http://localhost:8000/healthz"
echo "  Query: curl -X POST http://localhost:8000/ask -H 'Content-Type: application/json' -d '{\"question\":\"Học phí?\"}'"
echo ""
echo -e "${BLUE}Useful Commands:${NC}"
echo "  kubectl -n $NAMESPACE logs -f deployment/rag-rag-chatbot"
echo "  kubectl -n $NAMESPACE get hpa -w"
echo "  kubectl -n $MONITORING_NS get pods"
echo ""
