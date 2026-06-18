## Why

ステータス編集ポップアップの操作性改善（ユーザー要望）。努力値はスライダーのみで微調整しづらい。
ランククリアのボタンが「ランク」ラベル＋更新アイコン（refresh）でクリアの意味が伝わらない。あわせて
テラスを一旦機能無効化する。

## What Changes

- **努力値編集**：スライダーをやめ、各能力に **0／32 のワンクリックボタン＋ ±1 ステップボタン**（数値中央表示）
  を置く（0〜32 クランプ）。
- **ランククリアの明確化**：HP 行のランク列のボタンを **アイコン＝掃き出し（delete_sweep）・ラベル＝
  「ランククリア」** にし、全能力のランクを 0 にする操作と分かるようにする。
- **テラスの無効化**：サンプルパーティの `tera` を none にし、テラスは計算にも UI にも反映しない
  （エンジンのテラス対応は P4 再導入用に温存。`tera` を計算へ渡さない対応は別途実施済み）。

## Capabilities

### Modified Capabilities
- `battle-screen-ui`: 「ステータス（努力値・ランク）の編集」を更新する。

## Impact

- `mobile/lib/src/screens/home_screen.dart`（_StatEditorDialog の努力値ボタン・ランククリア）
- `mobile/lib/src/data/sample_party.dart`（tera を none に）
