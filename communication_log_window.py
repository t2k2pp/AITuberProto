import customtkinter
import tkinter as tk # messagebox のため
import os # ファイル存在確認のため
from communication_logger import CommunicationLogger

class CommunicationLogWindow(customtkinter.CTkToplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title("通信詳細ログ")
        self.geometry("800x600")

        self.logger = CommunicationLogger() # ロガーのインスタンスを取得

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        main_frame = customtkinter.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        button_frame = customtkinter.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(0, 10))

        self.refresh_button = customtkinter.CTkButton(button_frame, text="更新", command=self.refresh_logs)
        self.refresh_button.pack(side="left", padx=(0, 5))

        self.save_button = customtkinter.CTkButton(button_frame, text="現在の表示内容をファイルに保存 (スナップショット)", command=self.save_snapshot_logs)
        self.save_button.pack(side="left", padx=5)

        self.clear_memory_button = customtkinter.CTkButton(button_frame, text="メモリ上のログをクリア", command=self.clear_memory_logs)
        self.clear_memory_button.pack(side="left", padx=5)

        # セッションログファイルパス表示ラベル
        self.session_file_label = customtkinter.CTkLabel(button_frame, text="セッションログ: 未定", font=("Yu Gothic UI", 10), anchor="w")
        self.session_file_label.pack(side="left", padx=10, fill="x", expand=True)


        self.log_display_textbox = customtkinter.CTkTextbox(main_frame, wrap="word", state="disabled", font=("Yu Gothic UI", 12))
        self.log_display_textbox.pack(fill="both", expand=True)

        self.refresh_logs() # 初期表示

    def refresh_logs(self):
        """セッションログファイルからログを読み込み表示を更新する"""
        self.log_display_textbox.configure(state="normal")
        self.log_display_textbox.delete("1.0", "end")

        session_log_path = self.logger.get_session_log_filepath()

        if session_log_path and os.path.exists(session_log_path):
            try:
                # セッションログファイルパスをラベルに表示
                self.session_file_label.configure(text=f"記録中: {os.path.basename(session_log_path)}")
                with open(session_log_path, "r", encoding="utf-8") as f:
                    log_content = f.read()
                if log_content:
                    # 新しいログが上に来るようにファイルの内容を逆順にするのは大変なので、
                    # ファイルに記録された順（古いものが上）で表示する。
                    # もし逆順表示が必要なら、CommunicationLogger側でファイル書き込み順を工夫するか、
                    # ここで読み込んだ後に行ごとに処理して逆順にする必要がある。
                    # シンプルにするため、ここではファイル通りの順で表示する。
                    self.log_display_textbox.insert("end", log_content)
                else:
                    self.log_display_textbox.insert("end", f"セッションログファイル '{os.path.basename(session_log_path)}' は空です。\n")
            except Exception as e:
                self.log_display_textbox.insert("end", f"セッションログファイル '{os.path.basename(session_log_path)}' の読み込みエラー: {e}\n")
                tk.messagebox.showerror("読込エラー", f"ログファイルの読み込みに失敗しました:\n{session_log_path}\nエラー: {e}", parent=self)
        else:
            no_log_message = "セッションログファイルが見つかりません。"
            if session_log_path:
                 no_log_message = f"セッションログファイル '{os.path.basename(session_log_path)}' が見つかりません。\nアプリケーションがログを記録し始めると作成されます。"
                 self.session_file_label.configure(text=f"記録待機中: {os.path.basename(session_log_path)}")
            else:
                 self.session_file_label.configure(text="セッションログ: パス未設定")

            self.log_display_textbox.insert("end", no_log_message + "\n")

        self.log_display_textbox.configure(state="disabled")

    def save_snapshot_logs(self):
        """現在メモリに読み込まれているログのスナップショットをファイルに保存する"""
        # CommunicationLoggerのsave_logs_to_fileはメモリ上のログを保存する
        # refresh_logsはファイルから読み込むので、メモリ上のログと表示が一致しない可能性がある。
        # ここでは「表示されている内容」ではなく「現在のメモリ上のログ」を保存する。
        # もし「表示されている内容」を保存したいなら、テキストボックスの内容を取得して保存する。
        # プランでは save_logs_to_file を呼び出すことになっているので、メモリログを保存する。
        self.logger.save_logs_to_file(parent_window=self)

    def clear_memory_logs(self):
        """メモリ上のログのみをクリアする。表示は次の「更新」まで変わらない。"""
        # ボタンのテキストを「メモリ上のログをクリア」に変更したため、確認ダイアログの文言も調整
        dialog = customtkinter.CTkInputDialog(
            text="メモリ上の通信ログのみをクリアしますか？\n記録中のセッションログファイルには影響しません。\nスナップショット保存の対象がクリアされます。\nよろしければ「はい」と入力してください。",
            title="メモリログクリア確認"
        )
        user_input = dialog.get_input()

        if user_input and user_input.lower() == "はい":
            self.logger.clear_logs() # メモリ上のログをクリア
            # self.refresh_logs() # プランでは表示更新だが、ここではクリアしたことを明確にするため更新しない。
            # 更新ボタンでユーザーが明示的にファイルから再読み込みする。
            # または、クリアした旨をメッセージで表示する。
            tk.messagebox.showinfo("クリア完了", "メモリ上のログはクリアされました。\n表示を更新するには「更新」ボタンを押してください。\nセッションログファイルは影響を受けていません。", parent=self)
            # 表示されている内容は古いままなので、ユーザーに混乱を与えないように
            # テキストボックスを一時的に「メモリはクリアされました」などにしても良いが、
            # 次の更新で元に戻る。
        elif user_input is not None:
            tk.messagebox.showwarning("クリア中止", "入力が「はい」と一致しなかったため、メモリ上のログはクリアされませんでした。", parent=self)

    def on_closing(self):
        self.destroy()

if __name__ == '__main__':
    app = customtkinter.CTk()
    customtkinter.set_appearance_mode("System")
    customtkinter.set_default_color_theme("blue")
    app.title("Test App for Communication Log")
    # app.geometry("400x300") # Window自体のサイズはWindowクラスで設定

    # テスト用のログディレクトリとファイルを作成
    test_log_dir = "test_comm_log_window_logs"
    if not os.path.exists(test_log_dir):
        os.makedirs(test_log_dir)

    # CommunicationLogger のインスタンスを作成し、テスト用ディレクトリを指定
    # これにより、セッションログファイルが test_log_dir 内に作成される
    logger_instance = CommunicationLogger(log_dir=test_log_dir)

    # ダミーログを追加 (これによりセッションログファイルにも書き込まれる)
    logger_instance.add_log("sent", "test_init", "初期化テスト用の送信プロンプト。")
    logger_instance.add_log("received", "test_init", "初期化テスト用のAIレスポンス。")


    def open_log_window():
        new_log_win = CommunicationLogWindow(app)
        # new_log_win.grab_set()

    open_button = customtkinter.CTkButton(app, text="ログウィンドウを開く", command=open_log_window)
    open_button.pack(pady=20, padx=20)

    # テスト終了後にテストディレクトリを削除するための処理
    def cleanup_test_dir():
        import shutil
        if os.path.exists(test_log_dir):
            try:
                shutil.rmtree(test_log_dir)
                print(f"Cleaned up test directory: {test_log_dir}")
            except Exception as e:
                print(f"Error cleaning up test directory {test_log_dir}: {e}")
        app.destroy() # アプリケーション終了

    app.protocol("WM_DELETE_WINDOW", cleanup_test_dir)
    app.mainloop()
