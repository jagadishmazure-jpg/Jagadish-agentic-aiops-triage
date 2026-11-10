#!/usr/bin/env bash
# Download the open-weight GGUF files listed in scripts/models.json into models/ and verify SHA-256.
# Only needed to re-measure (scripts/run_triage.py); tests, CI and the eval replay need no weights.
# Gemma 4 E2B QAT Q4_0 is about 3.4 GB.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p models
python3 - <<'PY' | while read -r file url sha; do
import json
for m in json.load(open("scripts/models.json"))["gguf"]:
    print(m["file"], m["url"], m["sha256"])
PY
  if [[ ! -f "models/$file" ]]; then
    curl -fL --retry 3 -o "models/$file.part" "$url" && mv "models/$file.part" "models/$file"
  fi
  echo "$sha  models/$file" | sha256sum -c -
done
