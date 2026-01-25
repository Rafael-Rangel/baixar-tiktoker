#!/bin/bash
# Testes locais da API Content Orchestrator
# Uso: ./scripts/test-local.sh [BASE_URL]
# Ex.: ./scripts/test-local.sh http://localhost:8000

BASE_URL="${1:-http://localhost:8000}"
pretty() { python3 -m json.tool 2>/dev/null || cat; }

echo "=== Base URL: $BASE_URL ==="
echo ""

echo "1. GET /v1/n8n/health"
out=$(curl -s -w "\n%{http_code}" "$BASE_URL/v1/n8n/health")
code=$(echo "$out" | tail -n1)
body=$(echo "$out" | sed '$d')
if [ "$code" = "200" ]; then
  echo "$body" | pretty
else
  echo "(HTTP $code) $body"
fi
echo ""

echo "2. POST /v1/n8n/process-sources (YouTube Shorts, 1 vídeo)"
out=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/v1/n8n/process-sources" \
  -H "Content-Type: application/json" \
  -d '{
    "sources": [{
      "platform": "youtube",
      "external_id": "@ShortsPodcuts",
      "group_name": "teste",
      "video_type": "shorts"
    }],
    "limit": 1
  }')
code=$(echo "$out" | tail -n1)
body=$(echo "$out" | sed '$d')
if [ "$code" = "200" ]; then
  echo "$body" | pretty
else
  echo "(HTTP $code) $body"
fi
echo ""

echo "3. POST /v1/download (exemplo com Shorts)"
echo "   Para rodar: descomente o bloco no script ou use:"
echo "   curl -X POST $BASE_URL/v1/download -H 'Content-Type: application/json' -d '{...}'"
# curl -s -X POST "$BASE_URL/v1/download" \
#   -H "Content-Type: application/json" \
#   -d '{
#     "video_url": "https://www.youtube.com/shorts/q70k78OJpic",
#     "platform": "youtube",
#     "external_video_id": "q70k78OJpic",
#     "group_name": "teste",
#     "source_name": "shorts"
#   }' | pretty

echo ""
echo "=== Fim dos testes ==="
