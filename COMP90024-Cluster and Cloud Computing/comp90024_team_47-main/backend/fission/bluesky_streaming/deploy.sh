#!/bin/bash
set -e
cd "$(dirname "$0")"
FUNCTION_NAME="bluesky-streaming"
ZIP_FILE="bluesky_streaming.zip"

./build.sh

fission function delete --name "$FUNCTION_NAME" 2>/dev/null || true

echo ""
echo "Creating Fission function $FUNCTION_NAME..."
fission function create \
  --name "$FUNCTION_NAME" \
  --env python-39 \
  --src "$ZIP_FILE" \
  --entrypoint "main.main" \
  --secret es-creds \
  --secret bluesky-creds \
  --configmap fission-es-config \
  --executortype poolmgr \
  --fntimeout 180

echo ""
echo "✅ Function created: $FUNCTION_NAME"
echo ""
echo "Test:  fission function test --name $FUNCTION_NAME --timeout 180s"
