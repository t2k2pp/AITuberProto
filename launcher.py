import customtkinter
import subprocess
import sys
import os
import tkinter.messagebox # メッセージボックスのインポート (customtkinterには直接の代替がないため維持)
import tkinter as tk # subprocess起動のため (tk.Tk()を直接呼び出さないようにするため)

# CommunicationLogWindowをインポート
from communication_log_window import CommunicationLogWindow

class LauncherWindow:
    def __init__(self, root: customtkinter.CTk): # rootの型ヒントをCTkに
        self.root = root
        self.root.title("AITuber Launcher")
        self.root.geometry("450x550") # ボタン追加のため少し拡大

        self.active_modules = {} # 起動中のモジュールを管理
        self.communication_log_window = None # ログウィンドウのインスタンスを管理

        # フォント設定 (customtkinterではウィジェットごとに指定するか、CTkFontオブジェクトを使用)
        # ここでは、各ウィジェットでタプル形式で指定する方針とする
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

        header_label = customtkinter.CTkLabel(main_frame, text="AITuber 機能ランチャー", font=header_font_tuple)
        header_label.pack(pady=(10, 25)) # パディング調整

        button_frame = customtkinter.CTkFrame(main_frame, fg_color="transparent") # ボタン用のフレームは背景色なし
        button_frame.pack(expand=True, fill="x")

        buttons = [
            ("設定画面", "settings_window.py"),
            ("キャラクター管理", "character_management_window.py"),
            ("デバッグ", "debug_window.py"),
            ("YoutubeLive", "youtube_live_window.py"),
            ("AI劇場", "ai_theater_window.py"),
            ("AIチャット", "ai_chat_window.py"),
            ("ヘルプ", "help_window.py"),
            ("通信詳細", "communication_log_window.py") # 新しいボタン情報を追加
        ]

        button_width = 180 # CTkButtonの幅
        button_height = 40  # CTkButtonの高さ

        for i, (text, module_name_or_action) in enumerate(buttons):
            command_to_run = None
            if module_name_or_action == "communication_log_window.py":
                command_to_run = self.launch_communication_log_window
            else:
                # 既存のモジュール起動ロジック
                command_to_run = lambda m=module_name_or_action: self.launch_module(m)

            button = customtkinter.CTkButton(
                button_frame,
                text=text,
                command=command_to_run,
                font=default_font_tuple,
                width=button_width,
                height=button_height,
                corner_radius=8
            )
            # グリッドレイアウトでボタンを配置
            row, col = divmod(i, 2) # 2列で配置
            button.grid(row=row, column=col, padx=10, pady=10, sticky="ew")

        # グリッドの列幅を均等に設定
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        self.check_active_modules() # 起動中モジュールの状態確認を開始

    def launch_communication_log_window(self):
        """通信詳細ログウィンドウを起動または表示する"""
        if self.communication_log_window is None or not self.communication_log_window.winfo_exists():
            self.communication_log_window = CommunicationLogWindow(self.root)
            # self.communication_log_window.grab_set()  # モーダル表示を解除
        else:
            self.communication_log_window.deiconify() # 最小化されていたら表示
            self.communication_log_window.lift() # 最前面に表示
            self.communication_log_window.focus_set() # フォーカスを当てる
            # 必要であればログを更新
            if hasattr(self.communication_log_window, 'refresh_logs'):
                self.communication_log_window.refresh_logs()


    def launch_module(self, module_name):
        ended_modules = [m for m, p in self.active_modules.items() if p.poll() is not None]
        for m in ended_modules:
            del self.active_modules[m]
            print(f"Cleaned up ended module: {m}")

        if module_name in self.active_modules:
            process = self.active_modules[module_name]
            if process.poll() is None:
                print(f"{module_name} is already running.")
                tkinter.messagebox.showinfo("情報", f"{module_name} は既に起動しています。")
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
                tkinter.messagebox.showerror("起動エラー", f"{module_name} が見つかりません。")
                return

            process = subprocess.Popen([python_executable, script_path])
            self.active_modules[module_name] = process
            print(f"{module_name} launched and registered.")

        except Exception as e:
            print(f"Error launching {module_name}: {e}")
            tkinter.messagebox.showerror("起動エラー", f"{module_name} の起動中にエラーが発生しました:\n{e}")

    def check_active_modules(self):
        ended_modules = []
        for module_name, process in self.active_modules.items():
            if process.poll() is not None:
                ended_modules.append(module_name)
                print(f"Module {module_name} has ended (PID: {process.pid}).")

        for module_name in ended_modules:
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
