# assets/

旧リポジトリ `champ-edge` (E:\champ-edge) からコピーした再利用可能なアセット群。

## ディレクトリ構成

```
assets/
├── image/
│   ├── pokemon/      # ポケモン画像（図鑑番号別、PNG）
│   ├── typeicon/     # タイプアイコン（PNG, 日本語ファイル名）
│   ├── menu/         # UI メニューアイコン
│   ├── other/        # その他 UI 素材
│   └── favicon.ico   # アプリアイコン
└── data/
    ├── pokemon.db    # ポケモン / 技 / 特性 / 持ち物マスタデータ (SQLite)
    └── stats/        # HOME 使用率データ / ランキング / メタデータ
        ├── home_doryoku.csv   # 努力値
        ├── home_motimono.csv  # 持ち物
        ├── home_seikaku.csv   # 性格
        ├── home_tokusei.csv   # 特性
        ├── home_waza.csv      # 技
        ├── ranking.json
        ├── ranking.txt
        ├── season.txt
        ├── last_update.txt
        └── last_update_battle.txt
```

## 利用上の注意

- ポケモン関連の画像・データの取り扱いは個人利用範囲を逸脱しないこと（イシュー#25 制約事項）
- 商標・著作権に配慮した素材選定を継続すること
- 本リポジトリは **private** で運用すること

## 由来とアップデート方針

- 由来: `E:\champ-edge\image\*`, `E:\champ-edge\database\pokemon.db`, `E:\champ-edge\stats\*`
- マスタデータ（pokemon.db / stats）はサーバー側からの差分配信に移行予定（Phase 1 後半）。
  当面は初期同梱データとして使用。
- 画像アセットは Phase 1 では同梱、将来的に CDN 配信を検討。
