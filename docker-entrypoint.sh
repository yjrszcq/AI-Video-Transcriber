#!/bin/sh
set -e

: "${PRELOADED_HF_HOME:=/opt/preloaded-hf-cache}"
: "${HF_HOME:=/data/huggingface}"
: "${HUGGINGFACE_HUB_CACHE:=$HF_HOME/hub}"
: "${REPAIR_PRELOADED_HF_CACHE:=false}"
export PRELOADED_HF_HOME HF_HOME HUGGINGFACE_HUB_CACHE REPAIR_PRELOADED_HF_CACHE

mkdir -p "$HF_HOME"

preloaded_has_files="$(find "$PRELOADED_HF_HOME" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null || true)"

if [ -n "$preloaded_has_files" ]; then
  repair_preloaded_hf_cache="$(printf '%s' "$REPAIR_PRELOADED_HF_CACHE" | tr '[:upper:]' '[:lower:]')"
  if [ "$repair_preloaded_hf_cache" = "true" ]; then
    echo "Repairing runtime Hugging Face cache from preloaded models..."
    cp -af "$PRELOADED_HF_HOME"/. "$HF_HOME"/
  else
    echo "Merging preloaded Hugging Face cache into runtime cache..."
    tar -C "$PRELOADED_HF_HOME" -cf - . | tar -C "$HF_HOME" --skip-old-files -xf -
  fi
fi

exec "$@"
