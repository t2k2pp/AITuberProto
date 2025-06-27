import customtkinter
from launcher import LauncherWindow # gui.py から launcher.py に変更
import sys # Pythonのバージョンチェック用
from tkinter import messagebox # エラー表示用
import tkinter as tk # TkVersionのため、およびcheck_python_version内のtk.Tk()のため

def check_python_version():
    """Pythonのバージョンが3.7以上であることを確認する"""
    if sys.version_info < (3, 7):
        # customtkinterウィンドウを表示する前にエラーを出すため、ここは標準Tkinterのまま
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
        customtkinter.set_appearance_mode("System")  # Modes: "System" (default), "Dark", "Light"
        customtkinter.set_default_color_theme("blue")  # Themes: "blue" (default), "green", "dark-blue"

        root = customtkinter.CTk()
        app = LauncherWindow(root) # AITuberMainGUI から LauncherWindow に変更
        root.mainloop()
    except Exception as e:
        # 起動時の予期せぬエラーをキャッチして表示
        # customtkinterウィンドウを表示する前にエラーを出すため、ここは標準Tkinterのまま
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
    # tk.TkVersion を customtkinter でどう取得するか、または表示しないか検討。
    # customtkinter自体がTkinterをラップしているので、tk.TkVersionで問題ない可能性が高い。
    # ただし、customtkinter.CTk()インスタンス化前に呼び出す必要があるため、
    # tkをインポートしておく。
    try:
        # Create a temporary root to get TkVersion if customtkinter is not yet initialized
        # or if we need it before the main CTk() instance.
        temp_root = tk.Tk()
        tk_version = temp_root.tk.call('info', 'patchlevel')
        temp_root.destroy()
        print(f"Tkinter Version: {tk_version}")
    except Exception:
        print("Tkinter Version: (Could not retrieve)")
    print(f"Operating System: {sys.platform}")
    print("--------------------------------------------------")
    main()
