# キャプチャ設定画面
import json
import tkinter
from tkinter import filedialog, ttk

from component.parts.button import MyButton


class CaptureSetting(tkinter.Toplevel):
    def __init__(
        self, title: str = "キャプチャ設定", width: int = 400, height: int = 300
    ):
        super().__init__()
        self.title(title)
        self.path = "recog/capture.json"

        # JSONファイルから初期値を読み取り
        try:
            with open(self.path, "r") as json_file:
                self.initial_data = json.load(json_file)
        except FileNotFoundError:
            self.initial_data = {
                "source_name": "",
                "host_name": "",
                "port": "",
                "password": "",
            }

        # ラベルとエントリーの作成
        self.source_label = tkinter.Label(self, text="ソース名:")
        self.source_label.grid(row=0, column=0, padx=10, pady=5, sticky="e")
        self.source_entry = tkinter.Entry(self)
        self.source_entry.insert(0, self.initial_data["source_name"])
        self.source_entry.grid(row=0, column=1, padx=10, pady=5)

        self.host_label = tkinter.Label(self, text="ホスト名:")
        self.host_label.grid(row=1, column=0, padx=10, pady=5, sticky="e")
        self.host_entry = tkinter.Entry(self)
        self.host_entry.insert(0, self.initial_data["host_name"])
        self.host_entry.grid(row=1, column=1, padx=10, pady=5)

        self.port_label = tkinter.Label(self, text="ポート:")
        self.port_label.grid(row=2, column=0, padx=10, pady=5, sticky="e")
        self.port_entry = tkinter.Entry(self)
        self.port_entry.insert(0, self.initial_data["port"])
        self.port_entry.grid(row=2, column=1, padx=10, pady=5)

        self.password_label = tkinter.Label(self, text="パスワード:")
        self.password_label.grid(row=3, column=0, padx=10, pady=5, sticky="e")
        self.password_entry = tkinter.Entry(self)
        self.password_entry.insert(0, self.initial_data["password"])
        self.password_entry.grid(row=3, column=1, padx=10, pady=5)

        self.submit_button = MyButton(self, text="保存", command=self.submit_form)
        self.submit_button.grid(row=4, column=0, pady=10)
        self.cancel_button = MyButton(
            self, text="キャンセル", command=self.on_push_button
        )
        self.cancel_button.grid(row=4, column=1, pady=10)

    def open(self, location=tuple[int, int]):
        self.grab_set()
        self.focus_set()
        self.geometry("+{0}+{1}".format(location[0], location[1]))

    def submit_form(self):
        # 入力された値を取得
        self.source_name = self.source_entry.get()
        self.host_name = self.host_entry.get()
        self.port = self.port_entry.get()
        self.password = self.password_entry.get()

        # 入力された値をJSONファイルに保存
        data = {
            "source_name": self.source_name,
            "host_name": self.host_name,
            "port": self.port,
            "password": self.password,
        }

        with open(self.path, "w") as json_file:
            json.dump(data, json_file, indent=2)

        self.destroy()

    def on_push_button(self):
        self.destroy()


# モード切替画面
class ModeSetting(tkinter.Toplevel):
    def __init__(self, title: str = "モード切替", width: int = 400, height: int = 450):
        super().__init__()
        self.title(title)
        self.path = "recog/setting.json"

        # JSONファイルから初期値を読み取り
        try:
            with open(self.path, "r") as json_file:
                self.initial_data = json.load(json_file)
        except FileNotFoundError:
            self.initial_data = {
                "rule": 1,
                "active_chosen_auto": True,
                "capture_monitor_auto": True,
                "doryoku_reset_auto": True,
                "similar_party_auto": False,
                "search_record_auto": False,
                "panipani_auto": True,
                "terastal_enabled": True,
                "tesseract_path": "",
            }

        # ルールの選択
        self.rule_var = tkinter.IntVar()
        self.rule_var.set(self.initial_data["rule"])
        self.rule_button1 = tkinter.Radiobutton(
            self, text="シングル", variable=self.rule_var, value=1
        )
        self.rule_button1.grid(row=0, column=0, pady=5)
        self.rule_button2 = tkinter.Radiobutton(
            self, text="ダブル", variable=self.rule_var, value=2
        )
        self.rule_button2.grid(row=0, column=1, pady=5)

        # チェックボックス1
        self.active_chosen_auto_var = tkinter.BooleanVar()
        self.active_chosen_auto_var.set(self.initial_data["active_chosen_auto"])
        self.active_chosen_auto_checkbox = tkinter.Checkbutton(
            self, text="相手選出自動登録モード", variable=self.active_chosen_auto_var
        )
        self.active_chosen_auto_checkbox.grid(row=1, column=0, columnspan=2, pady=5)

        # チェックボックス2
        self.capture_monitor_auto_var = tkinter.BooleanVar()
        self.capture_monitor_auto_var.set(self.initial_data["capture_monitor_auto"])
        self.capture_monitor_auto_checkbox = tkinter.Checkbutton(
            self,
            text="キャプチャ監視自動開始モード",
            variable=self.capture_monitor_auto_var,
        )
        self.capture_monitor_auto_checkbox.grid(row=2, column=0, columnspan=2, pady=5)

        # チェックボックス3
        self.doryoku_reset_auto_var = tkinter.BooleanVar()
        self.doryoku_reset_auto_var.set(self.initial_data["doryoku_reset_auto"])
        self.doryoku_reset_auto_checkbox = tkinter.Checkbutton(
            self,
            text="相手性格変更時自動努力値変更モード",
            variable=self.doryoku_reset_auto_var,
        )
        self.doryoku_reset_auto_checkbox.grid(row=3, column=0, columnspan=2, pady=5)

        # チェックボックス4
        self.similar_party_auto_var = tkinter.BooleanVar()
        self.similar_party_auto_var.set(self.initial_data["similar_party_auto"])
        self.similar_party_auto_checkbox = tkinter.Checkbutton(
            self,
            text="類似パーティ自動検索モード（構築記事）",
            variable=self.similar_party_auto_var,
        )
        self.similar_party_auto_checkbox.grid(row=4, column=0, columnspan=2, pady=5)

        # チェックボックス5
        self.search_record_auto_var = tkinter.BooleanVar()
        self.search_record_auto_var.set(self.initial_data["search_record_auto"])
        self.search_record_auto_checkbox = tkinter.Checkbutton(
            self,
            text="類似パーティ自動検索モード（対戦履歴）",
            variable=self.search_record_auto_var,
        )
        self.search_record_auto_checkbox.grid(row=5, column=0, columnspan=2, pady=5)

        # チェックボックス6
        self.panipani_auto_var = tkinter.BooleanVar()
        self.panipani_auto_var.set(self.initial_data["panipani_auto"])
        self.panipani_auto_checkbox = tkinter.Checkbutton(
            self,
            text="ぱにぱにツール自動起動モード",
            variable=self.panipani_auto_var,
        )
        self.panipani_auto_checkbox.grid(row=6, column=0, columnspan=2, pady=5)

        # チェックボックス7
        self.terastal_enabled_var = tkinter.BooleanVar()
        self.terastal_enabled_var.set(self.initial_data.get("terastal_enabled", True))
        self.terastal_enabled_checkbox = tkinter.Checkbutton(
            self,
            text="テラスタル有効",
            variable=self.terastal_enabled_var,
        )
        self.terastal_enabled_checkbox.grid(row=7, column=0, columnspan=2, pady=5)

        # Tesseractフォルダ
        tess_frame = ttk.Frame(self)
        tkinter.Label(tess_frame, text="Tesseractフォルダ:").pack(side="left", padx=5)
        self.tesseract_path_var = tkinter.StringVar()
        self.tesseract_path_var.set(self.initial_data.get("tesseract_path", ""))
        tkinter.Entry(tess_frame, textvariable=self.tesseract_path_var, width=30).pack(
            side="left", padx=5
        )
        MyButton(tess_frame, text="参照", command=self.browse_tesseract_path).pack(
            side="left", padx=5
        )
        tess_frame.grid(row=8, column=0, columnspan=2, pady=5)

        self.submit_button = MyButton(self, text="保存", command=self.submit_form)
        self.submit_button.grid(row=9, column=0, pady=10)
        self.cancel_button = MyButton(
            self, text="キャンセル", command=self.on_push_button
        )
        self.cancel_button.grid(row=9, column=1, pady=10)
        caution = ttk.Label(
            self,
            text="※設定を反映するには、再起動が必要です。",
            foreground="red",
            padding=10,
        )
        caution.grid(row=10, column=0, columnspan=2, pady=5)

    def open(self, location=tuple[int, int]):
        self.grab_set()
        self.focus_set()
        self.geometry("+{0}+{1}".format(location[0], location[1]))

    def browse_tesseract_path(self):
        current = self.tesseract_path_var.get()
        folder = filedialog.askdirectory(
            title="Tesseractのインストールフォルダを選択",
            initialdir=current if current else "C:\\",
        )
        if folder:
            self.tesseract_path_var.set(folder.replace("/", "\\"))

    def submit_form(self):
        # 入力された値をJSONファイルに保存
        data = {
            "rule": self.rule_var.get(),
            "active_chosen_auto": self.active_chosen_auto_var.get(),
            "capture_monitor_auto": self.capture_monitor_auto_var.get(),
            "doryoku_reset_auto": self.doryoku_reset_auto_var.get(),
            "similar_party_auto": self.similar_party_auto_var.get(),
            "search_record_auto": self.search_record_auto_var.get(),
            "panipani_auto": self.panipani_auto_var.get(),
            "terastal_enabled": self.terastal_enabled_var.get(),
            "tesseract_path": self.tesseract_path_var.get(),
        }

        with open(self.path, "w") as json_file:
            json.dump(data, json_file, indent=2)

        self.destroy()

    def on_push_button(self):
        self.destroy()


def get_recog_value(key: str):
    """
    認識設定の値を取得する関数
    :param key: 取得したい設定のキー
    :return: 設定の値
    """

    if key not in [
        "rule",
        "active_chosen_auto",
        "capture_monitor_auto",
        "doryoku_reset_auto",
        "similar_party_auto",
        "search_record_auto",
        "panipani_auto",
        "terastal_enabled",
        "tesseract_path",
        "source_name",
        "host_name",
        "port",
        "password",
    ]:
        raise ValueError("Invalid key provided for recognition settings.")

    try:
        if key in ["source_name", "host_name", "port", "password"]:
            with open("recog/capture.json", "r") as json_file:
                capture_json = json.load(json_file)
                return capture_json[key]
        else:
            with open("recog/setting.json", "r") as json_file:
                settings_json = json.load(json_file)
                return settings_json[key]
    except FileNotFoundError:
        return {
            "rule": 1,
            "active_chosen_auto": True,
            "capture_monitor_auto": True,
            "doryoku_reset_auto": True,
            "similar_party_auto": False,
            "search_record_auto": False,
            "panipani_auto": True,
            "terastal_enabled": True,
            "tesseract_path": "",
            "source_name": "",
            "host_name": "",
            "port": "",
            "password": "",
        }[key]
