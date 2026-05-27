import json
import os
import threading
import tkinter
from tkinter import messagebox, scrolledtext, ttk


def get_api_key() -> str:
    # 1. 現プロセスの環境変数
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        return key
    # 2. Windowsレジストリのユーザー環境変数（プロセス起動後に設定された場合に対応）
    if os.name == "nt":
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as reg:
                key, _ = winreg.QueryValueEx(reg, "ANTHROPIC_API_KEY")
            if key:
                return key
        except Exception:
            pass
    # 3. setting.json
    try:
        with open("recog/setting.json", "r") as f:
            return json.load(f).get("anthropic_api_key", "")
    except Exception:
        return ""


def _pid_to_name(pid) -> str:
    if not pid or pid == "-1":
        return ""
    try:
        from database.pokemon import DB_pokemon

        return DB_pokemon.get_pokemon_name_by_pid(str(pid)) or str(pid)
    except Exception:
        return str(pid)


def _result_label(result) -> str:
    try:
        v = int(result)
    except (TypeError, ValueError):
        return "不明"
    return {1: "勝ち", 2: "負け", 0: "負け", -1: "引き分け", 3: "引き分け"}.get(
        v, "不明"
    )


# battle テーブルの列インデックス
_P_POKE = [10, 11, 12, 13, 14, 15]
_O_POKE = [16, 17, 18, 19, 20, 21]
_P_CHOICE = [22, 23, 24, 25]
_O_CHOICE = [26, 27, 28, 29]
_RESULT = 3
_MEMO = 7


def _build_prompt(battles: list, user_note: str) -> str:
    if not battles:
        return ""

    party_names = [
        _pid_to_name(battles[0][i])
        for i in _P_POKE
        if battles[0][i] and battles[0][i] != "-1"
    ]

    lines = [
        "あなたはポケモン対戦（ポケモンチャンピオンズ）のコーチです。",
        "以下の対戦データをもとに、①環境に多いポケモンの型や並び②パーティの反省点と改善案の2つの内容を具体的にフィードバックしてください。",
        "",
        f"【使用パーティ】{' / '.join(party_names)}",
        "",
        "【対戦記録】",
    ]

    for i, b in enumerate(battles, 1):
        result = _result_label(b[_RESULT])
        my_choices = [_pid_to_name(b[j]) for j in _P_CHOICE if b[j] and b[j] != "-1"]
        opp_choices = [_pid_to_name(b[j]) for j in _O_CHOICE if b[j] and b[j] != "-1"]
        opp_party = [_pid_to_name(b[j]) for j in _O_POKE if b[j] and b[j] != "-1"]
        memo = b[_MEMO] or ""

        lines.append(f"\n--- 対戦{i} ({result}) ---")
        lines.append(f"  相手パーティ: {' / '.join(opp_party)}")
        lines.append(f"  自分の選出:   {' / '.join(my_choices)}")
        lines.append(f"  相手の選出:   {' / '.join(opp_choices)}")
        if memo:
            lines.append(f"  メモ: {memo}")

    if user_note.strip():
        lines.append(f"\n【ユーザーからの補足】\n{user_note.strip()}")

    lines += [
        "",
        "以下の観点でフィードバックをお願いします：",
        "1. 負けパターンの共通点・弱点",
        "2. 選出の傾向と改善点",
        "3. パーティ構成の課題と具体的な改善案",
        "4. 次に意識すべきポイント",
    ]

    return "\n".join(lines)


class Feedback(tkinter.Toplevel):
    def __init__(self, master=None, battles: list = None, note: str = ""):
        super().__init__(master)
        self.title("AI対戦フィードバック")
        self.resizable(True, True)
        self._battles = battles or []
        self._note = note
        self._thread: threading.Thread | None = None
        self._build_ui()

    def open(self):
        self.focus_set()
        self.geometry("700x500")
        self.after(0, self._on_generate)

    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", **pad)
        self._generate_btn = ttk.Button(
            btn_frame, text="フィードバック生成", command=self._on_generate
        )
        self._generate_btn.pack(side="left")
        count_text = (
            f"（{len(self._battles)}件）" if self._battles else "（データなし）"
        )
        ttk.Label(btn_frame, text=count_text, foreground="gray").pack(
            side="left", padx=4
        )
        self._status_var = tkinter.StringVar(value="")
        ttk.Label(btn_frame, textvariable=self._status_var, foreground="gray").pack(
            side="left"
        )

        result_frame = ttk.LabelFrame(self, text="フィードバック")
        result_frame.pack(fill="both", expand=True, **pad)
        self._result_text = scrolledtext.ScrolledText(
            result_frame, wrap="word", state="disabled", font=("Yu Gothic UI", 10)
        )
        self._result_text.pack(fill="both", expand=True, padx=4, pady=4)

    def _set_result(self, text: str):
        self._result_text.config(state="normal")
        self._result_text.delete("1.0", "end")
        self._result_text.insert("end", text)
        self._result_text.config(state="disabled")

    def _on_generate(self):
        if self._thread and self._thread.is_alive():
            return

        api_key = get_api_key()
        if not api_key:
            messagebox.showerror(
                "エラー",
                "APIキーが設定されていません。\nアプリ設定からAPIキーを設定してください。",
                parent=self,
            )
            return

        if not self._battles:
            messagebox.showinfo(
                "情報", "対戦データがありません。先に検索してください。", parent=self
            )
            return

        prompt = _build_prompt(self._battles, self._note)
        self._generate_btn.config(state="disabled")
        self._status_var.set("生成中...")
        self._set_result("")

        self._thread = threading.Thread(
            target=self._call_api, args=(api_key, prompt), daemon=True
        )
        self._thread.start()

    def _call_api(self, api_key: str, prompt: str):
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=api_key)
            message = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )
            text = message.content[0].text
        except Exception as e:
            text = f"エラー: {e}"
        self.after(0, self._on_api_done, text)

    def _on_api_done(self, text: str):
        self._set_result(text)
        self._status_var.set("")
        self._generate_btn.config(state="normal")
