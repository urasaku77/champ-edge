# タスク: decide-damage-engine-language

## 決定フェーズ

- [x] `decide-damage-engine-language` change を作成し、候補と判断基準を明文化する
- [x] 旧リポジトリの `~/Documents/champ-edge/pokedata/calc.py` を参照し、機能要件とアルゴリズムの範囲を整理する
- [x] Dart 直実装と Rust 共有ライブラリ化の見積もり差を評価する（design.md 参照。Phase 1 は Dart 採用）

## Dart 直実装

- [x] Flutter プロジェクトにダメージ計算エンジンの Dart クラスを追加する（`lib/src/service/damage/`）
- [x] 計算入力モデルと結果モデルを定義する（`models.dart`: AttackerState/DefenderState/FieldState/MoveState/DamageResult）
- [x] 既存 Python ロジックの代表的なケースを Dart に移植し、正しい結果を返すことを確認する（calc.py 全 5 関数 + ステータス計算 + タイプ相性を忠実移植）
- [x] 100ms 未満の応答を目標に、計算ルートの性能測定を行う（実測 約 14.6µs/回）

## 検証 / テスト

- [x] `damage_engine` の単体テストを追加する（`test/damage_calc_test.dart` / `test/verify_damage.dart`）
- [x] Python 版 `calc.py` の代表ケースと Dart 実装結果を比較する（250 件 自動生成、250/250 一致）
- [x] 計算結果の妥当性と性能をドキュメント化する（`mobile/docs/damage_engine.md`）

## フォールバック検討（条件付き・未発動で決着）

- [x] Dart 直実装は性能（約14.6µs/回、要件100msを大幅充足）・保守性とも問題なく、Rust 共有ライブラリ化の再検討は**不要（未発動で決定）**
- [x] Rust FFI 経路の評価は Phase 1 では不要と判断（Dart で要件充足のため）
- [x] `decide-damage-engine-platform` change の作成は不要（必要が生じれば将来新規 change で対応）
