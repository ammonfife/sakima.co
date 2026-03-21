#!/usr/bin/env bash
# deploy.sh — build & deploy Sakima SMS bot to GCP Cloud Run
# Usage: ./deploy.sh [--region us-central1]
set -euo pipefail

PROJECT="heimdall-8675309"
SERVICE="sakima-sms"
REGION="${1:-us-central1}"
IMAGE="gcr.io/${PROJECT}/${SERVICE}"

# ---- Secrets (read from vault at deploy time) --------------------------------
SURGE_API_KEY="${SURGE_API_KEY:-$(secrets get surge_api_key 2>/dev/null || echo 'PLACEHOLDER_SET_IN_SURGE_DASHBOARD')}"
TURSO_URL=$(secrets get sakima_turso_url 2>/dev/null)
TURSO_TOKEN=$(secrets get sakima_turso_token 2>/dev/null)
REDIS_HOST=$(secrets get sakima_redis_host 2>/dev/null)
REDIS_TOKEN=$(secrets get sakima_redis_token 2>/dev/null)

echo "🏗  Building Docker image: ${IMAGE}"
docker build --platform linux/amd64 -t "${IMAGE}" .

echo "📤 Pushing to GCR..."
docker push "${IMAGE}"

echo "🚀 Deploying to Cloud Run (region: ${REGION})..."
gcloud run deploy "${SERVICE}" \
  --project="${PROJECT}" \
  --image="${IMAGE}" \
  --region="${REGION}" \
  --platform=managed \
  --allow-unauthenticated \
  --port=8080 \
  --memory=512Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=10 \
  --set-env-vars="SURGE_API_KEY=${SURGE_API_KEY},TURSO_URL=${TURSO_URL},TURSO_TOKEN=${TURSO_TOKEN},REDIS_HOST=${REDIS_HOST},REDIS_TOKEN=${REDIS_TOKEN}"

echo ""
WEBHOOK_URL=$(gcloud run services describe "${SERVICE}" \
  --project="${PROJECT}" \
  --region="${REGION}" \
  --format='value(status.url)')/webhook/sms

echo "✅ Deployed!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Webhook URL (paste into Surge dashboard):"
echo "  ${WEBHOOK_URL}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Next steps:"
echo "  1. Copy the webhook URL above"
echo "  2. In Surge dashboard → Phone Numbers → your number → Inbound Webhook"
echo "  3. Paste the URL and save"
echo "  4. Set SURGE_API_KEY env var (see README.md)"
