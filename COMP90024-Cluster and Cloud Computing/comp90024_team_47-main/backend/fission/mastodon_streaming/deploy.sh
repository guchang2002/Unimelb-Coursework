#!/bin/bash
# Deploy mastodon_streaming to Fission cluster.
set -e

cd "$(dirname "$0")"
FUNCTION_NAME="mastodon-streaming"
ZIP_FILE="mastodon_streaming.zip"

# 1. Build local zip
./build.sh

# 2. Delete previous version
fission function delete --name "$FUNCTION_NAME" 2>/dev/null || true

# 3. Create function — Fission's python-builder will auto-run pip install
echo ""
echo "Creating Fission function $FUNCTION_NAME..."
fission function create \
  --name "$FUNCTION_NAME" \
  --env python-39 \
  --src "$ZIP_FILE" \
  --entrypoint "main.main" \
  --secret es-creds \
  --secret mastodon-creds \
  --configmap fission-es-config \
  --executortype poolmgr \
  --fntimeout 180

echo ""
echo "✅ Function created: $FUNCTION_NAME"
echo ""
echo "Wait 1-3 minutes for builder Pod to pip install dependencies."
echo ""
echo "Watch build progress:"
echo "  fission package list | grep mastodon"
echo ""
echo "Then test:"
echo "  fission function test --name $FUNCTION_NAME --timeout 180s"
