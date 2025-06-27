import tkinter as tk
from tkinter import ttk
import subprocess
import sys
import os

class LauncherWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("AITuber Launcher")
        self.root.geometry("400x450")

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


    def launch_module(self, module_name):
        print(f"Launching {module_name}...")
        try:
            # Pythonインタープリタのパスを取得
            python_executable = sys.executable
            # スクリプトの絶対パスを取得
            script_path = os.path.join(os.path.dirname(__file__), module_name)

            if not os.path.exists(script_path):
                print(f"Error: {script_path} not found.")
                # ここでユーザーにエラーを通知するUI要素を追加することも検討
                tk.messagebox.showerror("起動エラー", f"{module_name} が見つかりません。")
                return

            # 新しいプロセスとして各機能ウィンドウを起動
            subprocess.Popen([python_executable, script_path])
        except Exception as e:
            print(f"Error launching {module_name}: {e}")
            tk.messagebox.showerror("起動エラー", f"{module_name} の起動中にエラーが発生しました:\n{e}")


def main():
    root = tk.Tk()
    app = LauncherWindow(root)
    root.mainloop()

if __name__ == "__main__":
    main()
