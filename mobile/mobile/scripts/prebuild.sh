#!/usr/bin/env bash
# Flutter ビルド前フック: PC マスター (database/, image/, recog/, stats/) から
# Flutter が参照する assets/ を生成・同期する (Issue #26)。
# `flutter build` / `flutter run` の前に実行すること。
set -euo pipefail

# このスクリプトは mobile/mobile/scripts/ にある。リポジトリ root は 3 つ上。
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
python3 "$ROOT/scripts/sync_to_mobile.py"
echo "✅ prebuild: assets synced"
