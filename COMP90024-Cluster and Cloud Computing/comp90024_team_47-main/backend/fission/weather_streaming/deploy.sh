#!/bin/bash
# Deploy weather_streaming to Fission cluster.
set -e

cd "$(dirname "$0")"
FUNCTION_NAME="weather-streaming"
ZIP_FILE="weather_streaming.zip"

# 1. Build
./build.sh

# 2. Delete previous version (idempotent)
fission function delete --name "$FUNCTION_NAME" 2>/dev/null || true

# 3. Create function with ES URL via ConfigMap, ES creds via Secret
echo ""
echo "Creating Fission function $FUNCTION_NAME..."
fission function create \
  --name "$FUNCTION_NAME" \
  --env python-39 \
  --src "$ZIP_FILE" \
  --entrypoint "main.main" \
  --secret es-creds \
  --configmap fission-es-config \
  --executortype poolmgr

echo "✅ Function deployed: $FUNCTION_NAME"
echo ""
echo "Test it:"
echo "  fission function test --name $FUNCTION_NAME"
