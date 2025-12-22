#!/bin/bash

# Quick access script for monitoring stack

echo "=== HUST RAG Chatbot - Monitoring Access ==="
echo ""

# Get Grafana password
GRAFANA_PASSWORD=$(kubectl --namespace monitoring get secret prometheus-grafana -o jsonpath="{.data.admin-password}" | base64 -d)

echo "Grafana Credentials:"
echo "  Username: admin"
echo "  Password: $GRAFANA_PASSWORD"
echo ""

echo "Starting port-forwards..."
echo ""

# Kill existing port forwards
pkill -f "port-forward.*3000" 2>/dev/null || true
pkill -f "port-forward.*9090" 2>/dev/null || true
pkill -f "port-forward.*8000" 2>/dev/null || true
sleep 1

# Port forward Grafana
echo "Grafana: http://localhost:3000"
kubectl --namespace monitoring port-forward svc/prometheus-grafana 3000:80 > /dev/null 2>&1 &

# Port forward Prometheus
echo "Prometheus: http://localhost:9090"
kubectl --namespace monitoring port-forward svc/prometheus-kube-prometheus-prometheus 9090:9090 > /dev/null 2>&1 &

# Port forward RAG API
echo "RAG API: http://localhost:8000"
kubectl -n rag port-forward svc/rag-rag-chatbot 8000:8000 > /dev/null 2>&1 &

sleep 2
echo ""
echo "All services ready! Press Ctrl+C to stop port-forwards."
echo ""
echo "Test RAG API:"
echo "  curl http://localhost:8000/healthz"
echo "  curl -X POST http://localhost:8000/ask -H 'Content-Type: application/json' -d '{\"question\":\"Học phí?\"}'"
echo ""

wait
