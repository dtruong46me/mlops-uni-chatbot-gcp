#!/bin/bash

URL="http://localhost:8000/ask"
PAYLOAD='{"question":"Học phí?"}'

for i in {1..100}; do
  curl -s -X POST "$URL" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD" &
done

wait
echo "All 100 requests done"
