import tkinter as tk
from tkinter import ttk
import subprocess
import sys
import os
import tkinter.messagebox # メッセージボックスのインポート

class LauncherWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("AITuber Launcher")
        self.root.geometry("400x450")

        self.active_modules = {} # 起動中のモジュールを管理

        # スタイル設定
        style = ttk.Style()
        style.theme_use('clam') # モダンなテーマを選択 (aqua, clam, alt, default, classicなど)

        # フォント設定
        default_font = ("Yu Gothic UI", 10) # Windowsで利用可能な日本語フォント
        if sys.platform == "darwin": # macOS
            default_font = ("Hiragino Sans", 12)
        elif sys.platform.startswith("linux"): # Linux
            default_font = ("Noto Sans CJK JP", 10) # 必要に応じてインストール

        style.configure("TButton", padding=6, relief="flat", font=default_font)
        style.configure("TLabel", font=default_font)
        style.configure("TFrame", background="#f0f0f0")
        style.configure("Launcher.TFrame", background="#e0e0e0", borderwidth=2, relief="groove")


        main_frame = ttk.Frame(root, padding="20 20 20 20", style="Launcher.TFrame")
        main_frame.pack(expand=True, fill=tk.BOTH)

        header_label = ttk.Label(main_frame, text="AITuber 機能ランチャー", font=(default_font[0], 16, "bold"))
        header_label.pack(pady=(0, 20))

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(expand=True)

        buttons = [
            ("設定画面", "settings_window.py"),
            ("キャラクター管理", "character_management_window.py"),
            ("デバッグ", "debug_window.py"),
            ("YoutubeLive", "youtube_live_window.py"),
            ("AI劇場", "ai_theater_window.py"),
            ("AIチャット", "ai_chat_window.py"),
            ("ヘルプ", "help_window.py")
        ]

        for i, (text, module_name) in enumerate(buttons):
            button = ttk.Button(
                button_frame,
                text=text,
                command=lambda m=module_name: self.launch_module(m),
                width=25 # ボタンの幅を統一
            )
            # グリッドレイアウトでボタンを配置
            row, col = divmod(i, 2) # 2列で配置
            button.grid(row=row, column=col, padx=10, pady=10, sticky="ew")

        # グリッドの列幅を均等に設定
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        self.check_active_modules() # 起動中モジュールの状態確認を開始

    def launch_module(self, module_name):
        # アクティブなモジュールリストから終了したプロセスをクリーンアップ
        # (check_active_modulesでも行われるが、起動直前にも行うことでより確実に)
        ended_modules = [m for m, p in self.active_modules.items() if p.poll() is not None]
        for m in ended_modules:
            del self.active_modules[m]
            print(f"Cleaned up ended module: {m}")

        if module_name in self.active_modules:
            process = self.active_modules[module_name]
            if process.poll() is None: # プロセスがまだ実行中
                print(f"{module_name} is already running.")
                tk.messagebox.showinfo("情報", f"{module_name} は既に起動しています。")
                return
            else: # プロセスは終了しているが、リストに残っていた場合 (念のため)
                print(f"{module_name} was in active_modules but process ended. Removing.")
                del self.active_modules[module_name]

        print(f"Launching {module_name}...")
        try:
            python_executable = sys.executable
            script_path = os.path.join(os.path.dirname(__file__), module_name)

            if not os.path.exists(script_path):
                print(f"Error: {script_path} not found.")
                tk.messagebox.showerror("起動エラー", f"{module_name} が見つかりません。")
                return

            process = subprocess.Popen([python_executable, script_path])
            self.active_modules[module_name] = process # 起動したプロセスを登録
            print(f"{module_name} launched and registered.")

        except Exception as e:
            print(f"Error launching {module_name}: {e}")
            tk.messagebox.showerror("起動エラー", f"{module_name} の起動中にエラーが発生しました:\n{e}")

    def check_active_modules(self):
        """起動中のモジュールの状態を定期的に確認し、終了したものをリストから削除する"""
        ended_modules = []
        for module_name, process in self.active_modules.items():
            if process.poll() is not None: # プロセスが終了した
                ended_modules.append(module_name)
                print(f"Module {module_name} has ended (PID: {process.pid}).")

        for module_name in ended_modules:
            if module_name in self.active_modules: # 二重チェック (稀なケースだが安全のため)
                del self.active_modules[module_name]
                print(f"Removed {module_name} from active modules.")

        # 次回のチェックをスケジュール (1000ms = 1秒後)
        self.root.after(1000, self.check_active_modules)


def main():
    root = tk.Tk()
    app = LauncherWindow(root)
    root.mainloop()

if __name__ == "__main__":
    main()
