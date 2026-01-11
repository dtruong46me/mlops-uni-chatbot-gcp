#!/usr/bin/env bash
set -euo pipefail

if [ -z "${OPENAI_API_KEY:-}" ]; then
  echo "Please set OPENAI_API_KEY in your environment before running this script"
  echo "  export OPENAI_API_KEY=\"sk-...\""
  exit 1
fi

NAMESPACE=${1:-rag}
SECRET_NAME=${2:-rag-secret}

kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic "$SECRET_NAME" \
  --namespace "$NAMESPACE" \
  --from-literal=OPENAI_API_KEY="$OPENAI_API_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "Created secret '$SECRET_NAME' in namespace '$NAMESPACE' (or updated it)."

echo "Now run Helm with secret.useExisting=true to reference the secret without Helm creating it:"
echo "  helm upgrade --install rag rag-controller/helm-charts/rag-chatbot -n $NAMESPACE --set secret.useExisting=true --timeout 10m"
