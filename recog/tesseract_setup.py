# coding: utf-8
"""Tesseract OCR セットアップウィザード。

ダウンロード・インストール・日本語パック取得・パス指定を一括で行う。
tessdata (jpn/eng/osd) はアプリフォルダ直下の tessdata/ に保存する。
"""
import json
import os
import subprocess
import sys
import tempfile
import threading
import tkinter
from tkinter import filedialog, ttk
from urllib.request import urlopen

_SETTINGS_PATH = "recog/setting.json"
_TESSDATA_DIR = "tessdata"
_TESSDATA_URLS = {
    "jpn": "https://github.com/tesseract-ocr/tessdata/raw/main/jpn.traineddata",
    "eng": "https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata",
    "osd": "https://github.com/tesseract-ocr/tessdata/raw/main/osd.traineddata",
}
_WIN_DEFAULT_PATHS = [
    r"C:\Program Files\Tesseract-OCR",
    r"C:\Program Files (x86)\Tesseract-OCR",
]


def detect_tesseract() -> str:
    """インストール済み Tesseract のフォルダを自動検出。未検出は空文字列。"""
    if sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Tesseract-OCR")
            path, _ = winreg.QueryValueEx(key, "InstallDir")
            if os.path.isfile(os.path.join(path, "tesseract.exe")):
                return str(path)
        except OSError:
            pass
        for loc in _WIN_DEFAULT_PATHS:
            if os.path.isfile(os.path.join(loc, "tesseract.exe")):
                return loc
    elif sys.platform == "darwin":
        for prefix in ["/opt/homebrew", "/usr/local"]:
            if os.path.isfile(os.path.join(prefix, "bin", "tesseract")):
                return os.path.join(prefix, "bin")
    return ""


def _download_file(url: str, dest: str, label: str, log_fn) -> None:
    with urlopen(url) as resp:
        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        last_reported = -1
        with open(dest, "wb") as f:
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if total > 0:
                    pct = downloaded * 100 // total
                    milestone = pct // 25 * 25
                    if milestone != last_reported:
                        log_fn(f"  {label}: {milestone}%")
                        last_reported = milestone
    size_mb = downloaded / 1024 / 1024
    log_fn(f"  {label}: 完了 ({size_mb:.1f} MB)")


class TesseractSetupDialog(tkinter.Toplevel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.title("Tesseract セットアップ")
        self.resizable(False, False)
        self._build_ui()
        self._refresh_status()
        self.grab_set()
        self.focus_set()

    def _build_ui(self):
        # 状態表示
        status_frame = ttk.LabelFrame(self, text="現在の状態", padding=8)
        status_frame.pack(fill="x", padx=12, pady=(12, 4))
        self._status_var = tkinter.StringVar(value="確認中...")
        tkinter.Label(
            status_frame,
            textvariable=self._status_var,
            justify="left",
            wraplength=420,
            font=("", 9),
        ).pack(anchor="w")

        # パス入力
        path_frame = ttk.LabelFrame(self, text="Tesseract フォルダ（手動指定）", padding=8)
        path_frame.pack(fill="x", padx=12, pady=4)
        self._path_var = tkinter.StringVar()
        tkinter.Entry(path_frame, textvariable=self._path_var, width=42).pack(
            side="left", padx=(0, 4)
        )
        ttk.Button(path_frame, text="参照", command=self._browse).pack(side="left")

        # ボタン群
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=12, pady=4)

        if sys.platform == "win32":
            self._auto_btn = ttk.Button(
                btn_frame,
                text="自動セットアップ（インストール＋日本語パック取得）",
                command=self._start_auto_setup,
            )
            self._auto_btn.pack(fill="x", pady=(0, 4))

        self._jpn_btn = ttk.Button(
            btn_frame,
            text="日本語パックのみ取得（Tesseract インストール済みの場合）",
            command=self._start_jpn_only,
        )
        self._jpn_btn.pack(fill="x")

        if sys.platform == "darwin":
            ttk.Label(
                btn_frame,
                text="Mac: ターミナルで  brew install tesseract tesseract-lang  を実行してください。",
                foreground="gray",
                font=("", 9),
            ).pack(anchor="w", pady=(4, 0))

        # 進捗・ログ
        log_frame = ttk.LabelFrame(self, text="進捗ログ", padding=8)
        log_frame.pack(fill="both", expand=True, padx=12, pady=4)
        self._progress = ttk.Progressbar(log_frame, mode="indeterminate")
        self._progress.pack(fill="x", pady=(0, 4))
        self._log_text = tkinter.Text(
            log_frame, height=7, width=52, state="disabled", font=("Consolas", 9)
        )
        self._log_text.pack(fill="both", expand=True)

        # 保存・閉じるボタン
        close_frame = ttk.Frame(self)
        close_frame.pack(fill="x", padx=12, pady=(4, 12))
        ttk.Button(close_frame, text="保存して閉じる", command=self._save_and_close).pack(
            side="right", padx=(4, 0)
        )
        ttk.Button(close_frame, text="キャンセル", command=self.destroy).pack(side="right")

    # ------------------------------------------------------------------
    # 状態更新
    # ------------------------------------------------------------------

    def _refresh_status(self):
        configured = self._load_saved_path()
        detected = detect_tesseract()
        path = configured or detected
        if path:
            self._path_var.set(path)

        exe = "tesseract.exe" if sys.platform == "win32" else "tesseract"
        has_exe = path != "" and os.path.isfile(os.path.join(path, exe))

        local_tessdata = os.path.abspath(_TESSDATA_DIR)
        jpn_local = os.path.isfile(os.path.join(local_tessdata, "jpn.traineddata"))
        jpn_system = path != "" and os.path.isfile(
            os.path.join(path, "tessdata", "jpn.traineddata")
        )
        if jpn_local:
            jpn_label = f"✓  {local_tessdata}"
        elif jpn_system:
            jpn_label = f"✓  {os.path.join(path, 'tessdata')}"
        else:
            jpn_label = "✗  未取得"

        lines = [
            f"Tesseract 実行ファイル: {'✓  ' + path if has_exe else '✗  未検出'}",
            f"日本語パック (jpn):     {jpn_label}",
        ]
        self._status_var.set("\n".join(lines))

    def _load_saved_path(self) -> str:
        try:
            with open(_SETTINGS_PATH, encoding="utf-8") as f:
                return json.load(f).get("tesseract_path", "")
        except Exception:
            return ""

    # ------------------------------------------------------------------
    # UI 操作
    # ------------------------------------------------------------------

    def _browse(self):
        current = self._path_var.get()
        folder = filedialog.askdirectory(
            title="Tesseract のインストールフォルダを選択",
            initialdir=current if current else "C:\\",
        )
        if folder:
            self._path_var.set(folder.replace("/", "\\"))
            self._refresh_status()

    def _set_buttons(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        if hasattr(self, "_auto_btn"):
            self._auto_btn.configure(state=state)
        self._jpn_btn.configure(state=state)

    def _log(self, msg: str):
        self.after(0, self._log_main, msg)

    def _log_main(self, msg: str):
        self._log_text.configure(state="normal")
        self._log_text.insert("end", msg + "\n")
        self._log_text.see("end")
        self._log_text.configure(state="disabled")

    # ------------------------------------------------------------------
    # 自動セットアップ（Windows）
    # ------------------------------------------------------------------

    def _start_auto_setup(self):
        self._set_buttons(False)
        self._progress.start()
        threading.Thread(target=self._run_auto_setup, daemon=True).start()

    def _run_auto_setup(self):
        try:
            # インストール済みチェック
            existing = detect_tesseract()
            if existing:
                self._log(f"Tesseract は既にインストールされています: {existing}")
                self.after(0, lambda p=existing: self._path_var.set(p))
            else:
                # 1. インストーラをダウンロード
                self._log("Tesseract インストーラを取得中...")
                resp = urlopen(
                    "https://api.github.com/repos/UB-Mannheim/tesseract/releases/latest"
                )
                release = json.loads(resp.read())
                asset = next(
                    (
                        a
                        for a in release["assets"]
                        if "w64-setup" in a["name"] and a["name"].endswith(".exe")
                    ),
                    None,
                )
                if not asset:
                    self._log("ERROR: インストーラが見つかりませんでした。")
                    return

                self._log(
                    f"ダウンロード中: {asset['name']}"
                    f" ({asset['size'] // 1024 // 1024} MB)"
                )
                with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as tmp:
                    tmp_path = tmp.name
                _download_file(asset["browser_download_url"], tmp_path, "installer", self._log)

                # 2. サイレントインストール（UAC が必要な場合はダイアログが表示される）
                self._log("インストール中（UAC ダイアログが表示される場合があります）...")
                result = subprocess.run([tmp_path, "/S"], timeout=180)
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                if result.returncode != 0:
                    self._log(f"WARNING: インストーラが終了コード {result.returncode} で終了しました。")
                else:
                    self._log("Tesseract インストール完了。")

                # 3. パス自動検出
                path = detect_tesseract()
                if path:
                    self._log(f"検出パス: {path}")
                    self.after(0, lambda p=path: self._path_var.set(p))
                else:
                    self._log("WARNING: インストールパスを自動検出できませんでした。手動で指定してください。")

            # 4. 日本語パック取得（ローカル or システム tessdata にあればスキップ）
            tess_path = self._path_var.get()
            system_tessdata = os.path.join(tess_path, "tessdata") if tess_path else ""
            local_tessdata = os.path.abspath(_TESSDATA_DIR)
            missing = [
                lang for lang in _TESSDATA_URLS
                if not os.path.isfile(os.path.join(local_tessdata, f"{lang}.traineddata"))
                and not (system_tessdata and os.path.isfile(
                    os.path.join(system_tessdata, f"{lang}.traineddata")
                ))
            ]
            if missing:
                self._download_tessdata()
            else:
                self._log("日本語パックは取得済みです。スキップします。")

        except Exception as e:
            self._log(f"ERROR: {e}")
        finally:
            self.after(0, self._setup_done)

    # ------------------------------------------------------------------
    # 日本語パックのみ取得
    # ------------------------------------------------------------------

    def _start_jpn_only(self):
        self._set_buttons(False)
        self._progress.start()
        threading.Thread(target=self._run_jpn_only, daemon=True).start()

    def _run_jpn_only(self):
        try:
            self._download_tessdata()
        except Exception as e:
            self._log(f"ERROR: {e}")
        finally:
            self.after(0, self._setup_done)

    def _download_tessdata(self):
        """jpn / eng / osd を tessdata/ に保存する。"""
        tessdata_dir = os.path.abspath(_TESSDATA_DIR)
        os.makedirs(tessdata_dir, exist_ok=True)
        self._log(f"tessdata 保存先: {tessdata_dir}")
        for lang, url in _TESSDATA_URLS.items():
            dest = os.path.join(tessdata_dir, f"{lang}.traineddata")
            if os.path.isfile(dest):
                self._log(f"  {lang}.traineddata: 既存ファイルを使用")
                continue
            self._log(f"  {lang}.traineddata をダウンロード中...")
            _download_file(url, dest, lang, self._log)

    # ------------------------------------------------------------------
    # 完了・保存
    # ------------------------------------------------------------------

    def _setup_done(self):
        self._progress.stop()
        self._set_buttons(True)
        self._refresh_status()

    def _save_and_close(self):
        path = self._path_var.get().strip()
        try:
            try:
                with open(_SETTINGS_PATH, encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
            data["tesseract_path"] = path
            with open(_SETTINGS_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self._log(f"保存エラー: {e}")
            return
        self.destroy()
