#!/bin/bash
# TestFlight アップロード補助スクリプト
# 使い方:  ./upload_testflight.sh <ISSUER_ID>
#   <ISSUER_ID> は App Store Connect → ユーザーとアクセス → 統合(Integrations)
#   → App Store Connect API の「Issuer ID」(UUID形式)。
# APIキー(.p8)は ~/.appstoreconnect/private_keys/AuthKey_8FHTL4N8T9.p8 を自動使用。
set -euo pipefail
KEY_ID=8FHTL4N8T9
ISSUER="${1:-}"
IPA="build/ios/ipa/ChampEdge.ipa"
if [ -z "$ISSUER" ]; then
  echo "ERROR: Issuer ID を引数で渡してください: ./upload_testflight.sh <ISSUER_ID>" >&2
  exit 1
fi
echo "検証中..."
xcrun altool --validate-app -f "$IPA" -t ios --apiKey "$KEY_ID" --apiIssuer "$ISSUER"
echo "アップロード中..."
xcrun altool --upload-app -f "$IPA" -t ios --apiKey "$KEY_ID" --apiIssuer "$ISSUER"
echo "完了。App Store Connect の TestFlight に反映されるまで数分〜十数分かかります。"
