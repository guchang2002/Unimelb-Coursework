#!/bin/bash
# Build Fission function zip: bundle main.py + shared/ + requirements.txt
set -e

cd "$(dirname "$0")"
FUNCTION_NAME="weather_streaming"
REPO_ROOT="$(cd ../../.. && pwd)"

echo "Building $FUNCTION_NAME..."

# 1. Clean previous build
rm -rf build/ "$FUNCTION_NAME.zip"

# 2. Stage: main.py + requirements.txt + shared/
mkdir -p build
cp main.py requirements.txt build/
cp -r "$REPO_ROOT/backend/shared" build/

# 3. Zip from inside build/ (so paths are relative)
cd build
zip -rq "../$FUNCTION_NAME.zip" .
cd ..

echo "✅ Built: $(pwd)/$FUNCTION_NAME.zip"
echo "   Size: $(du -h "$FUNCTION_NAME.zip" | cut -f1)"
echo "   Contents:"
unzip -l "$FUNCTION_NAME.zip" | head -25
