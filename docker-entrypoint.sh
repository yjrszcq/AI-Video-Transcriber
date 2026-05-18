#!/bin/sh
set -e

: "${PRELOADED_HF_HOME:=/opt/preloaded-hf-cache}"
: "${HF_HOME:=/data/huggingface}"
: "${HUGGINGFACE_HUB_CACHE:=$HF_HOME/hub}"
export PRELOADED_HF_HOME HF_HOME HUGGINGFACE_HUB_CACHE

mkdir -p "$HF_HOME"

preloaded_has_files="$(find "$PRELOADED_HF_HOME" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null || true)"

if [ -n "$preloaded_has_files" ]; then
  echo "Merging preloaded Hugging Face cache into runtime cache..."
  cp -an "$PRELOADED_HF_HOME"/. "$HF_HOME"/
fi

exec "$@"
