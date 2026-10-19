#!/bin/bash
set -e
cd "$(dirname "$0")"
FUNCTION_NAME="bluesky_streaming"
REPO_ROOT="$(cd ../../.. && pwd)"

echo "Building $FUNCTION_NAME..."

rm -rf build/ "$FUNCTION_NAME.zip"
mkdir -p build
cp main.py requirements.txt build/
cp -r "$REPO_ROOT/backend/shared" build/

find build -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find build -name "*.pyc" -delete 2>/dev/null || true

cd build
zip -rq "../$FUNCTION_NAME.zip" .
cd ..

echo "✅ Built: $(pwd)/$FUNCTION_NAME.zip"
echo "   Size: $(du -h "$FUNCTION_NAME.zip" | cut -f1)"
echo "   Contents:"
unzip -l "$FUNCTION_NAME.zip"
