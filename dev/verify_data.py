import os, sys, sqlite3
os.chdir(r"e:\champ-edge")
conn = sqlite3.connect("database/battle.db")
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM battle")
print("Total battles:", cur.fetchone()[0])
cur.execute("SELECT date, result, opponent_tn FROM battle ORDER BY date DESC LIMIT 5")
for r in cur.fetchall():
    import datetime
    d = datetime.datetime.fromtimestamp(r[0])
    print(f"  {d.date()} result={r[1]} tn={r[2]}")
conn.close()
