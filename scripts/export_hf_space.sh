#!/bin/sh
# Copies the files a Hugging Face Docker Space needs into a folder you can upload:
#   sh scripts/export_hf_space.sh ../ootk-space
# Full-size scans (static/images) and personal data are left out on purpose.
set -e
DEST="${1:?usage: sh scripts/export_hf_space.sh <folder>}"
cd "$(dirname "$0")/.."

rm -rf "$DEST"
mkdir -p "$DEST/static" "$DEST/database" "$DEST/deploy/huggingface"
cp Dockerfile .dockerignore pyproject.toml "$DEST/"
cp deploy/huggingface/README.md "$DEST/README.md"
cp deploy/huggingface/start.sh "$DEST/deploy/huggingface/"
cp -R src templates config "$DEST/"
cp -R static/js static/cards static/site "$DEST/static/"
cp database/schema.sql "$DEST/database/"
find "$DEST" -name __pycache__ -prune -exec rm -rf {} +
find "$DEST" -name '*.egg-info' -prune -exec rm -rf {} +

echo "Space files are in $DEST"
