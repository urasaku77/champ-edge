import sqlite3

conn = sqlite3.connect("database/battle.db")
cur = conn.cursor()

# 1. 新しいテーブルを作成
cur.execute(
    """
CREATE TABLE IF NOT EXISTS battle_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date INTEGER,
    rule INTEGER,
    result INTEGER,
    favorite TEXT,
    opponent_tn TEXT,
    opponent_rate TEXT,
    battle_memo TEXT,
    player_party_num INTEGER,
    player_party_subnum INTEGER,
    player_pokemon1 TEXT,
    player_pokemon2 TEXT,
    player_pokemon3 TEXT,
    player_pokemon4 TEXT,
    player_pokemon5 TEXT,
    player_pokemon6 TEXT,
    opponent_pokemon1 TEXT,
    opponent_pokemon2 TEXT,
    opponent_pokemon3 TEXT,
    opponent_pokemon4 TEXT,
    opponent_pokemon5 TEXT,
    opponent_pokemon6 TEXT,
    player_choice1 TEXT,
    player_choice2 TEXT,
    player_choice3 TEXT,
    player_choice4 TEXT,
    opponent_choice1 TEXT,
    opponent_choice2 TEXT,
    opponent_choice3 TEXT,
    opponent_choice4 TEXT
)
"""
)

# 2. データ移行
cur.execute(
    """
INSERT INTO battle_new (
    id, date, rule, result, favorite,
    opponent_tn, opponent_rate, battle_memo,
    player_party_num, player_party_subnum,
    player_pokemon1, player_pokemon2, player_pokemon3,
    player_pokemon4, player_pokemon5, player_pokemon6,
    opponent_pokemon1, opponent_pokemon2, opponent_pokemon3,
    opponent_pokemon4, opponent_pokemon5, opponent_pokemon6,
    player_choice1, player_choice2, player_choice3,
    player_choice4,
    opponent_choice1, opponent_choice2, opponent_choice3,
    opponent_choice4
)
SELECT
    id, date, 1, result, favorite,
    opponent_tn, opponent_rate, battle_memo,
    player_party_num, player_party_subnum,
    player_pokemon1, player_pokemon2, player_pokemon3,
    player_pokemon4, player_pokemon5, player_pokemon6,
    opponent_pokemon1, opponent_pokemon2, opponent_pokemon3,
    opponent_pokemon4, opponent_pokemon5, opponent_pokemon6,
    player_choice1, player_choice2, player_choice3,
    '-1',  -- player_choice4
    opponent_choice1, opponent_choice2, opponent_choice3,
    '-1'   -- opponent_choice4
FROM battle
"""
)

# 3. テーブルの置き換え
cur.execute("DROP TABLE battle")
cur.execute("ALTER TABLE battle_new RENAME TO battle")

conn.commit()
conn.close()
