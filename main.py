import tkinter as tk
from launcher import LauncherWindow # gui.py から launcher.py に変更
import sys # Pythonのバージョンチェック用
from tkinter import messagebox # エラー表示用

def check_python_version():
    """Pythonのバージョンが3.7以上であることを確認する"""
    if sys.version_info < (3, 7):
        root = tk.Tk()
        root.withdraw() # メインウィンドウは表示しない
        messagebox.showerror(
            "Pythonバージョンエラー",
            f"このアプリケーションにはPython 3.7以上が必要です。\n現在のバージョン: {sys.version_info.major}.{sys.version_info.minor}"
        )
        root.destroy()
        return False
    return True

def main():
    """アプリケーションのエントリーポイント"""
    if not check_python_version():
        return

    try:
        root = tk.Tk()
        app = LauncherWindow(root) # AITuberMainGUI から LauncherWindow に変更
        root.mainloop()
    except Exception as e:
        # 起動時の予期せぬエラーをキャッチして表示
        error_root = tk.Tk()
        error_root.withdraw()
        messagebox.showerror("致命的な起動エラー", f"アプリケーションの起動中に致命的なエラーが発生しました:\n{e}\n\n詳細はコンソールログを確認してください。")
        error_root.destroy()
        print(f"❌ アプリケーション起動エラー: {e}")
        import traceback
        print(traceback.format_exc())


if __name__ == "__main__":
    # 実行環境に関する情報を少し表示（デバッグ用）
    print("--------------------------------------------------")
    print(f"Python Version: {sys.version}")
    print(f"Tkinter Version: {tk.TkVersion}")
    print(f"Operating System: {sys.platform}")
    print("--------------------------------------------------")
    main()
