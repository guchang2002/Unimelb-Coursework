#!/bin/bash
# Build Fission function zip: bundle main.py + shared/ + requirements.txt
set -e

cd "$(dirname "$0")"
FUNCTION_NAME="mastodon_streaming"
REPO_ROOT="$(cd ../../.. && pwd)"

echo "Building $FUNCTION_NAME..."

# 1. Clean previous build
rm -rf build/ "$FUNCTION_NAME.zip"

# 2. Stage: main.py + requirements.txt + shared/
mkdir -p build
cp main.py requirements.txt build/
cp -r "$REPO_ROOT/backend/shared" build/

# 3. Remove __pycache__ and .pyc to keep zip clean
find build -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find build -name "*.pyc" -delete 2>/dev/null || true

# 4. Zip
cd build
zip -rq "../$FUNCTION_NAME.zip" .
cd ..

echo "✅ Built: $(pwd)/$FUNCTION_NAME.zip"
echo "   Size: $(du -h "$FUNCTION_NAME.zip" | cut -f1)"
echo "   Contents:"
unzip -l "$FUNCTION_NAME.zip"
