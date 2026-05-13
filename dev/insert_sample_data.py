# coding: utf-8
"""サンプルデータ投入スクリプト - box.csv と battle.db にサンプルデータを挿入する"""
import os, sys, sqlite3, time, random, csv

os.chdir(r"e:\champ-edge")
sys.path.insert(0, r"e:\champ-edge")

# ---------- box.csv ----------
BOX_ROWS = [
    # 名前,個体値,努力値,性格,持ち物,特性,テラス,メモ,技,技,技,技
    ["マスカーニャ","","A32B1D1S32","いじっぱり","きあいのタスキ","しんりょく","","","トリックフラワー","はたきおとす","トリプルアクセル","ふいうち"],
    ["ルカリオ","","H2A32S32","ようき","ルカリオナイト","せいしんりょく","","","インファイト","しんそく","じしん","コメットパンチ"],
    ["ガブリアス","","H32B19D12S3","わんぱく","オボンのみ","さめはだ","","","ドラゴンテール","じしん","ステルスロック","まきびし"],
    ["イダイトウ♂","","H2A32S32","ようき","こだわりスカーフ","てきおうりょく","","","ウェーブタックル","おはかまいり","アクアジェット","クイックターン"],
    ["アシレーヌ","","H32B32C1D1","ずぶとい","たべのこし","げきりゅう","","","うたかたのアリア","ムーンフォース","クイックターン","アンコール"],
    ["リザードン","","H18B3C13D1S31","ひかえめ","リザードナイトY","もうか","","","かえんほうしゃ","ソーラービーム","りゅうのはどう","みがわり"],
    ["ガブリアス","","H2A32S32","いじっぱり","オボンのみ","さめはだ","","","じしん","げきりん","つるぎのまい","ストーンエッジ"],
    ["ミミッキュ","","H1A32B1S32","ようき","のろいのおふだ","ばけのかわ","","","じゃれつく","シャドークロー","かげうち","つるぎのまい"],
    ["ドラパルト","","H2C32S32","おくびょう","きあいのタスキ","すりぬけ","","","ドラゴンアロー","シャドーボール","でんじは","おにび"],
    ["ドドゲザン","","H12A32S22","いじっぱり","くろいメガネ","そうだいしょう","","","ドゲザン","ふいうち","アイアンヘッド","つるぎのまい"],
    ["アーマーガア","","H32B31S3","わんぱく","たべのこし","ミラーアーマー","","","ブレイブバード","ちょうはつ","ビルドアップ","はねやすめ"],
    ["ハバタクカミ","","C32S32","おくびょう","こだわりメガネ","こだいかっせい","","","ムーンフォース","シャドーボール","サイコショック","マジカルシャイン"],
    ["カイリュー","","H25B16S25","ずぶとい","カイリュナイト","マルチスケイル","","","りゅうせいぐん","かえんほうしゃ","しんそく","でんじは"],
    ["サーフゴー","","H4C252S252","おくびょう","こだわりメガネ","おうごんのからだ","","","ゴールドラッシュ","シャドーボール","トリック","じこさいせい"],
]

header = ["名前","個体値","努力値","性格","持ち物","特性","テラス","メモ","技","技","技","技"]
with open("party/csv/box.csv", "w", encoding="cp932", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(header)
    writer.writerows(BOX_ROWS)
print(f"box.csv: {len(BOX_ROWS)} ポケモン書き込み完了")

# ---------- battle.db ----------
MY_PARTY = ["908-0", "448-0", "445-0", "902-0", "730-0", "6-0"]
MY_CHOICE_SETS = [
    ["908-0", "448-0", "445-0", None],
    ["908-0", "445-0", "730-0", None],
    ["448-0", "445-0", "6-0", None],
    ["908-0", "902-0", "730-0", None],
    ["908-0", "448-0", "730-0", None],
]
OPP_PARTIES = [
    ["445-0", "778-0", "887-0", "983-0", "823-0", "149-0"],
    ["149-0", "1018-0", "959-0", "908-0", "887-0", "445-0"],
    ["778-0", "983-0", "448-0", "823-0", "445-0", "730-0"],
    ["887-0", "1018-0", "959-0", "149-0", "823-0", "908-0"],
    ["983-0", "445-0", "778-0", "448-0", "730-0", "887-0"],
    ["1018-0", "959-0", "149-0", "908-0", "445-0", "778-0"],
]
OPP_CHOICE_SETS = [
    ["445-0", "778-0", "149-0", None],
    ["1018-0", "959-0", "149-0", None],
    ["778-0", "983-0", "448-0", None],
    ["887-0", "1018-0", "823-0", None],
    ["983-0", "445-0", "778-0", None],
]
TNS = ["たかし", "はなこ", "あきら", "ゆうた", "さとし", "けんじ", "みさき",
       "りょう", "トレーナー", "まなぶ", "かずき", "そうた", "ひろし", "ゆか"]

conn = sqlite3.connect("database/battle.db")
cur = conn.cursor()

# 既存サンプルは残し、新規データのみ追加（IDが962のものを除く）
# ただし962以外のデモデータがあれば全削除して入れ直す
cur.execute("SELECT COUNT(*) FROM battle WHERE id != 962")
existing_demo = cur.fetchone()[0]
if existing_demo > 0:
    cur.execute("DELETE FROM battle WHERE id != 962")
    conn.commit()
    print(f"既存サンプルデータ {existing_demo} 件削除")

# 2026-03-01 〜 2026-05-12 の期間でサンプル生成
base_date = int(time.mktime(time.strptime("2026-03-01", "%Y-%m-%d")))
end_date  = int(time.mktime(time.strptime("2026-05-12", "%Y-%m-%d")))
interval  = (end_date - base_date) // 30

battles = []
random.seed(42)
for i in range(30):
    ts = base_date + interval * i + random.randint(0, 3600 * 4)
    result = random.choice([1, 1, 1, 0, 0, -1])
    opp = random.choice(OPP_PARTIES)
    my_ch = random.choice(MY_CHOICE_SETS)
    op_ch = random.choice(OPP_CHOICE_SETS)
    tn = random.choice(TNS)
    rate = str(random.randint(1750, 2050) + random.random()).split(".")[0] + "." + str(random.randint(0, 999)).zfill(3)
    row = (
        ts,           # date
        1,            # rule
        result,       # result
        "0",          # favorite
        tn,           # opponent_tn
        rate,         # opponent_rate
        "",           # battle_memo
        2,            # player_party_num
        1,            # player_party_subnum
        MY_PARTY[0], MY_PARTY[1], MY_PARTY[2], MY_PARTY[3], MY_PARTY[4], MY_PARTY[5],
        opp[0], opp[1], opp[2], opp[3], opp[4], opp[5],
        my_ch[0], my_ch[1], my_ch[2], my_ch[3],
        op_ch[0], op_ch[1], op_ch[2], op_ch[3],
    )
    battles.append(row)

cur.executemany(
    "INSERT INTO battle (date,rule,result,favorite,opponent_tn,opponent_rate,battle_memo,"
    "player_party_num,player_party_subnum,"
    "player_pokemon1,player_pokemon2,player_pokemon3,player_pokemon4,player_pokemon5,player_pokemon6,"
    "opponent_pokemon1,opponent_pokemon2,opponent_pokemon3,opponent_pokemon4,opponent_pokemon5,opponent_pokemon6,"
    "player_choice1,player_choice2,player_choice3,player_choice4,"
    "opponent_choice1,opponent_choice2,opponent_choice3,opponent_choice4"
    ") VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
    battles,
)
conn.commit()
conn.close()
print(f"battle.db: {len(battles)} 件追加完了")
