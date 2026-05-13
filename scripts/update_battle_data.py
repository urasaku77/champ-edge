#!/usr/bin/env python3
import datetime
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_LAST_UPDATE_FILE = "stats/last_update.txt"
_LAST_BATTLE_UPDATE_FILE = "stats/last_update_battle.txt"

_STATS_FILES = [
    "stats/home_waza.csv", "stats/home_tokusei.csv",
    "stats/home_motimono.csv", "stats/home_seikaku.csv",
    "stats/home_doryoku.csv",
    "stats/ranking.json", "stats/ranking.txt", "stats/season.txt",
    "stats/last_update.txt", "stats/last_update_battle.txt",
]


def _run_git(args: list[str]):
    result = subprocess.run(["git"] + args, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} 失敗\n{result.stderr}")


def update_home() -> str:
    print("=== HOMEデータ更新 ===")
    from stats.home import main as home_main
    home_main()
    today = datetime.date.today().isoformat()
    with open(_LAST_UPDATE_FILE, "w", encoding="utf-8") as f:
        f.write(today)
    print(f"last_update.txt → {today}")
    return today


def update_battle() -> str:
    print("=== 構築記事データ更新 ===")
    from stats.search import Search
    Search().search_latest_party()
    today = datetime.date.today().isoformat()
    with open(_LAST_BATTLE_UPDATE_FILE, "w", encoding="utf-8") as f:
        f.write(today)
    print(f"last_update_battle.txt → {today}")
    return today


def git_push(today: str):
    existing = [f for f in _STATS_FILES if os.path.exists(f)]
    _run_git(["add"] + existing)
    diff = subprocess.run(["git", "diff", "--cached", "--stat"], capture_output=True, text=True)
    if not diff.stdout.strip():
        print("変更なし、コミットスキップ")
        return
    _run_git(["commit", "-m", f"data: バトルデータ更新 ({today})"])
    _run_git(["pull", "--rebase", "--autostash", "origin", "main"])
    _run_git(["push"])
    print("プッシュ完了")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    today = datetime.date.today().isoformat()

    home_ok = False
    battle_ok = False

    try:
        update_home()
        home_ok = True
    except Exception as e:
        print(f"HOMEデータ更新失敗: {e}", file=sys.stderr)

    try:
        update_battle()
        battle_ok = True
    except Exception as e:
        print(f"構築記事データ更新失敗: {e}", file=sys.stderr)

    if home_ok or battle_ok:
        try:
            git_push(today)
        except Exception as e:
            print(f"プッシュ失敗: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print("両方の更新が失敗したためスキップ", file=sys.stderr)
        sys.exit(1)
