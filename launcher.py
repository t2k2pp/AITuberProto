import customtkinter
import subprocess
import sys
import os
import tkinter.messagebox
import tkinter as tk
import time # 追加

# pygetwindow の条件付きインポート
if not sys.platform.startswith("linux"):
    try:
        import pygetwindow
    except ImportError:
        pygetwindow = None # インポート失敗時は None に設定
else:
    pygetwindow = None # Linuxでは使用しないため None

# CommunicationLogWindow と CommunicationLogger をインポート
from communication_log_window import CommunicationLogWindow
from communication_logger import CommunicationLogger
from i18n_setup import get_translator # 翻訳関数を取得

_ = get_translator() # モジュールレベルで翻訳関数を取得

class LauncherWindow:
    def __init__(self, root: customtkinter.CTk):
        self.root = root
        self.root.title(_("launcher.title"))
        self.root.geometry("450x550")

        # --- CommunicationLoggerの初期化と環境変数設定 ---
        # ランチャーが最初にロガーを初期化し、パスを決定する
        # log_dir は CommunicationLogger のデフォルト値 "communication_logs" を使用する
        # もしランチャーで特定のログディレクトリを指定したい場合は、ここで指定する
        # 例: logger = CommunicationLogger(log_dir="launcher_defined_logs")
        logger = CommunicationLogger()
        session_log_path = logger.get_session_log_filepath()
        log_dir_path = CommunicationLogger._log_dir # クラス変数から取得 (getterがあればそれが望ましい)

        if session_log_path:
            os.environ['GLOBAL_SESSION_LOG_PATH'] = os.path.abspath(session_log_path)
            print(_("launcher.log.env_set", env_var_name="GLOBAL_SESSION_LOG_PATH", env_var_value=os.environ['GLOBAL_SESSION_LOG_PATH']))
        else:
            print(_("launcher.log.error_get_session_log_path"))
            tkinter.messagebox.showwarning(_("launcher.logger_init_error.title"), _("launcher.logger_init_error.session_log_path_failure"))

        if log_dir_path:
            os.environ['GLOBAL_LOG_DIR_PATH'] = os.path.abspath(log_dir_path)
            print(_("launcher.log.env_set", env_var_name="GLOBAL_LOG_DIR_PATH", env_var_value=os.environ['GLOBAL_LOG_DIR_PATH']))
        else:
            print(_("launcher.log.error_get_log_dir_path"))
            tkinter.messagebox.showwarning(_("launcher.logger_init_error.title"), _("launcher.logger_init_error.log_dir_path_failure"))
        # --- ここまで追加 ---

        self.active_modules = {}
        self.communication_log_window = None

        # フォント設定
        # プラットフォームごとのフォント選択ロジックは維持
        font_name = "Yu Gothic UI"
        font_size_normal = 12
        font_size_header = 18
        if sys.platform == "darwin": # macOS
            font_name = "Hiragino Sans"
            font_size_normal = 14
            font_size_header = 20
        elif sys.platform.startswith("linux"): # Linux
            font_name = "Noto Sans CJK JP" # 必要に応じてインストール
            # font_size_normal と font_size_header はデフォルトのまま

        default_font_tuple = (font_name, font_size_normal)
        header_font_tuple = (font_name, font_size_header, "bold")

        # メインフレーム (CTkFrameに置き換え、paddingはCTkFrameのパラメータで調整)
        # style="Launcher.TFrame" は削除
        main_frame = customtkinter.CTkFrame(root, corner_radius=10) # fg_colorで背景色も指定可能
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)

        header_label = customtkinter.CTkLabel(main_frame, text=_("launcher.header_label"), font=header_font_tuple)
        header_label.pack(pady=(10, 25))

        # メイン機能とサブ機能のボタン設定を分離
        # ボタンのテキストとタイトルも翻訳対象とする
        main_features_config = [
            {"text_key": "launcher.button.youtube_live", "module_name": "youtube_live_window.py", "title_key": "launcher.window_title.youtube_live"},
            {"text_key": "launcher.button.ai_theater", "module_name": "ai_theater_window.py", "title_key": "launcher.window_title.ai_theater"},
            {"text_key": "launcher.button.ai_chat", "module_name": "ai_chat_window.py", "title_key": "launcher.window_title.ai_chat"},
            {"text_key": "launcher.button.character_management", "module_name": "character_management_window.py", "title_key": "launcher.window_title.character_management"},
        ]

        sub_features_config = [
            {"text_key": "launcher.button.settings", "module_name": "settings_window.py", "title_key": "launcher.window_title.settings"},
            {"text_key": "launcher.button.debug", "module_name": "debug_window.py", "title_key": "launcher.window_title.debug"},
            {"text_key": "launcher.button.help", "module_name": "help_window.py", "title_key": "launcher.window_title.help"},
            {"text_key": "launcher.button.communication_log", "module_name": "communication_log_window.py", "title_key": "launcher.window_title.communication_log"} # 新しいボタン情報を追加
        ]

        button_width = 180  # CTkButtonの幅
        button_height = 40 # CTkButtonの高さ

        # メイン機能ボタン用フレーム
        main_button_outer_frame = customtkinter.CTkFrame(main_frame, fg_color="transparent")
        main_button_outer_frame.pack(pady=(10, 5), fill="x", expand=False) # 上部に配置、余白調整
        customtkinter.CTkLabel(main_button_outer_frame, text=_("launcher.label.main_features"), font=(default_font_tuple[0], default_font_tuple[1], "bold")).pack(anchor="w", padx=10)
        main_button_frame = customtkinter.CTkFrame(main_button_outer_frame, fg_color="transparent")
        main_button_frame.pack(fill="x")


        for i, btn_config in enumerate(main_features_config):
            button = customtkinter.CTkButton(
                main_button_frame, # 親フレームを main_button_frame に変更
                text=_(btn_config["text_key"]),
                command=lambda m=btn_config["module_name"], tk=btn_config["title_key"]: self.launch_module(m, _(tk)),
                font=default_font_tuple,
                width=button_width,
                height=button_height,
                corner_radius=8
            )
            row, col = divmod(i, 2)
            main_button_frame.grid_columnconfigure(col, weight=1) # 各列のウェイト設定
            button.grid(row=row, column=col, padx=10, pady=5, sticky="ew")


        # サブ機能ボタン用フレーム
        sub_button_outer_frame = customtkinter.CTkFrame(main_frame, fg_color="transparent")
        # サブ機能フレームをメインフレームの下部に配置するために、
        # メイン機能フレームとサブ機能フレームの間にスペーサーを挟むか、
        # main_frame の pack expand をうまく使う必要がある。
        # ここでは、サブ機能フレームを main_frame の下部に配置するために side=tk.BOTTOM を使う
        sub_button_outer_frame.pack(pady=(10, 20), fill="x", expand=False, side="top") # 下部に配置, pady調整
        customtkinter.CTkLabel(sub_button_outer_frame, text=_("launcher.label.sub_features"), font=(default_font_tuple[0], default_font_tuple[1], "bold")).pack(anchor="w", padx=10)
        sub_button_frame = customtkinter.CTkFrame(sub_button_outer_frame, fg_color="transparent")
        sub_button_frame.pack(fill="x")

        for i, btn_config in enumerate(sub_features_config):
            button = customtkinter.CTkButton(
                sub_button_frame, # 親フレームを sub_button_frame に変更
                text=_(btn_config["text_key"]),
                command=lambda m=btn_config["module_name"], tk=btn_config["title_key"]: self.launch_module(m, _(tk)),
                font=default_font_tuple,
                width=button_width,
                height=button_height,
                corner_radius=8
            )
            row, col = divmod(i, 2)
            sub_button_frame.grid_columnconfigure(col, weight=1) # 各列のウェイト設定
            button.grid(row=row, column=col, padx=10, pady=5, sticky="ew")

        exit_button_frame = customtkinter.CTkFrame(main_frame, fg_color="transparent")
        exit_button_frame.pack(pady=(10,10), fill="x", side="bottom") # pady調整

        self.exit_button = customtkinter.CTkButton(
            exit_button_frame,
            text=_("launcher.button.exit"),
            command=self.on_launcher_close,
            font=default_font_tuple,
            fg_color="tomato",
            hover_color="darkred",
            width=150 # ボタン幅を少し指定
        )
        # ボタンを右寄せにする
        self.exit_button.pack(side="right", padx=10, pady=10) # side="right" と padx を追加

        self.check_active_modules()

    def on_launcher_close(self):
        if tkinter.messagebox.askyesno(_("launcher.exit_confirmation.title"), _("launcher.exit_confirmation.message"), parent=self.root):
            print("Launcher closing. Terminating active modules...")
            active_processes_terminated = 0
            # イテレート中に変更する可能性があるのでリストのコピーを取る
            for module_name, data in list(self.active_modules.items()):
                process = data["process"]
                if process.poll() is None: # プロセスがまだ実行中の場合
                    try:
                        process.terminate() # SIGTERMを送信
                        print(f"Terminating {module_name} (PID: {process.pid})...")
                        active_processes_terminated +=1
                    except Exception as e:
                        print(f"Error terminating {module_name}: {e}")

            if active_processes_terminated > 0:
                print(f"Waiting for {active_processes_terminated} processes to terminate...")
                time.sleep(0.5) # 0.5秒待機

            print("Exiting launcher.")
            self.root.destroy()

    def launch_module(self, module_name, window_title):
        # 既存のプロセスをクリーンアップ
        ended_modules_keys = [key for key, data in self.active_modules.items() if data["process"].poll() is not None]
        for key in ended_modules_keys:
            del self.active_modules[key]
            print(f"Cleaned up ended module: {key}")

        if module_name in self.active_modules:
            process_data = self.active_modules[module_name]
            if process_data["process"].poll() is None:
                print(f"{module_name} is already running.")
                try:
                    if pygetwindow: # pygetwindowがインポートされている場合のみ実行
                        if sys.platform.startswith("linux"): # Linuxの場合はpygetwindowがNoneのはずだが念のため
                            print("Window activation is not supported on Linux (pygetwindow module logic). Skipping.")
                            tkinter.messagebox.showinfo(_("launcher.info.title"), _("launcher.info.already_running_activation_failed", module_name=module_name, error="Not supported on Linux (pygetwindow check)"))
                        else:
                            # ウィンドウタイトルでウィンドウを検索してアクティブ化
                            target_window = pygetwindow.getWindowsWithTitle(window_title)
                            if target_window:
                                win = target_window[0]
                                if win.isMinimized:
                                    win.restore()
                                win.activate()
                                print(f"Activated window: {window_title}")
                            else:
                                tkinter.messagebox.showinfo(_("launcher.info.title"), _("launcher.info.window_not_found", window_title=window_title))
                    else:
                        print("pygetwindow is not available. Skipping window activation.")
                        # pygetwindow がない場合もユーザーに通知
                        tkinter.messagebox.showinfo(_("launcher.info.title"), _("launcher.info.already_running_activation_failed", module_name=module_name, error="pygetwindow not available"))
                except Exception as e:
                    print(f"Error activating window {window_title}: {e}")
                    tkinter.messagebox.showinfo(_("launcher.info.title"), _("launcher.info.already_running_activation_failed", module_name=module_name, error=e))
                return
            else:
                print(f"{module_name} was in active_modules but process ended. Removing.")
                del self.active_modules[module_name]

        print(f"Launching {module_name}...")
        try:
            python_executable = sys.executable
            script_path = os.path.join(os.path.dirname(__file__), module_name)

            if not os.path.exists(script_path):
                print(f"Error: {script_path} not found.")
                tkinter.messagebox.showerror(_("launcher.launch_error.title"), _("launcher.launch_error.module_not_found", module_name=module_name))
                return

            # --- communication_log_window.py の特別扱い ---
            if module_name == "communication_log_window.py":
                if self.communication_log_window is None or not self.communication_log_window.winfo_exists():
                    self.communication_log_window = CommunicationLogWindow(self.root)
                    # ウィンドウが閉じられたときに self.communication_log_window を None にする
                    self.communication_log_window.protocol("WM_DELETE_WINDOW", self._on_comm_log_close)
                    print(f"{module_name} window created.")
                else:
                    self.communication_log_window.deiconify() # ウィンドウを再表示
                    self.communication_log_window.lift() # ウィンドウを前面に表示
                    self.communication_log_window.focus_set() # フォーカスを当てる
                    print(f"{module_name} window reactivated.")
                return # subprocess.Popen を実行しない
            # --- ここまで特別扱い ---

            process = subprocess.Popen([python_executable, script_path])
            # active_modules にプロセスとウィンドウタイトルを保存
            self.active_modules[module_name] = {"process": process, "title": window_title}
            print(f"{module_name} launched and registered with title '{window_title}'.")

        except Exception as e:
            print(f"Error launching {module_name}: {e}")
            tkinter.messagebox.showerror(_("launcher.launch_error.title"), _("launcher.launch_error.generic_error", module_name=module_name, error=e))

    def _on_comm_log_close(self):
        """CommunicationLogWindowが閉じられたときのコールバック"""
        if self.communication_log_window:
            self.communication_log_window.destroy()
        self.communication_log_window = None
        print("CommunicationLogWindow closed and reference reset.")

    def check_active_modules(self):
        ended_modules_keys = []
        for module_name, data in self.active_modules.items(): # active_modules の構造変更に対応
            if data["process"].poll() is not None: # data["process"] を参照
                ended_modules_keys.append(module_name)
                print(f"Module {module_name} has ended (PID: {data['process'].pid}).")

        for module_name in ended_modules_keys:
            if module_name in self.active_modules:
                del self.active_modules[module_name]
                print(f"Removed {module_name} from active modules.")

        self.root.after(1000, self.check_active_modules)


def main():
    # main.py で外観モードとテーマは設定済みと想定
    # customtkinter.set_appearance_mode("System")
    # customtkinter.set_default_color_theme("blue")
    root = customtkinter.CTk()
    app = LauncherWindow(root)
    root.mainloop()

if __name__ == "__main__":
    # このファイルが直接実行された場合の処理
    # main.py側で設定されることを期待するが、単体テスト用にここにも記述しておく
    customtkinter.set_appearance_mode("System")
    customtkinter.set_default_color_theme("blue")
    main()
