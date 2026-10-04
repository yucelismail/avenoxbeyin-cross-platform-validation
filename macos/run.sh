#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo_root"

if command -v python3.13 >/dev/null 2>&1; then
  exec python3.13 ./run_validation.py
fi
if command -v python3 >/dev/null 2>&1; then
  exec python3 ./run_validation.py
fi

echo "Python bulunamadı. macos/README.md içindeki ilk adımı çalıştırın." >&2
exit 2

