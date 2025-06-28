import customtkinter
import tkinter as tk # messagebox のため
from communication_logger import CommunicationLogger

class CommunicationLogWindow(customtkinter.CTkToplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title("通信詳細ログ")
        self.geometry("800x600")

        self.logger = CommunicationLogger() # ロガーのインスタンスを取得

        # ウィンドウを閉じるときの処理
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # --- UI要素の作成 ---
        main_frame = customtkinter.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # ボタンフレーム
        button_frame = customtkinter.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(0, 10))

        self.refresh_button = customtkinter.CTkButton(button_frame, text="更新", command=self.refresh_logs)
        self.refresh_button.pack(side="left", padx=(0, 5))

        self.save_button = customtkinter.CTkButton(button_frame, text="ログをファイルに保存", command=self.save_logs)
        self.save_button.pack(side="left", padx=5)

        self.clear_button = customtkinter.CTkButton(button_frame, text="表示ログをクリア (メモリ)", command=self.clear_displayed_logs)
        self.clear_button.pack(side="left", padx=5)

        # ログ表示エリア (CTkTextboxを使用)
        self.log_display_textbox = customtkinter.CTkTextbox(main_frame, wrap="word", state="disabled", font=("Yu Gothic UI", 12)) # 適切なフォントを指定
        self.log_display_textbox.pack(fill="both", expand=True)

        self.refresh_logs() # 初期表示

    def refresh_logs(self):
        """ログ表示を更新する"""
        self.log_display_textbox.configure(state="normal") # テキストを編集可能に
        self.log_display_textbox.delete("1.0", "end") # 現在の表示をクリア

        logs = self.logger.get_logs()
        if not logs:
            self.log_display_textbox.insert("end", "ログエントリはありません。\n")
        else:
            for entry in reversed(logs): # 新しいログが上に来るように逆順で表示
                self.log_display_textbox.insert("end", f"Timestamp: {entry['timestamp']}\n")
                self.log_display_textbox.insert("end", f"Direction: {entry['direction']}\n")
                self.log_display_textbox.insert("end", f"Function Type: {entry['function_type']}\n")
                self.log_display_textbox.insert("end", f"Body:\n{entry['text_body']}\n")
                self.log_display_textbox.insert("end", "-" * 40 + "\n\n")

        self.log_display_textbox.configure(state="disabled") # テキストを読み取り専用に

    def save_logs(self):
        """ログをファイルに保存する"""
        self.logger.save_logs_to_file(parent_window=self) # CommunicationLoggerの保存メソッドを呼び出す

    def clear_displayed_logs(self):
        """表示されているログ（メモリ上のログ）をクリアする"""
        # customtkinter に標準的な Yes/No ダイアログがないため、tkinter.messagebox を使うか、
        # 自作するか、CTkInputDialog で代用する。ここではCTkInputDialogで簡易的に行う。
        dialog = customtkinter.CTkInputDialog(text="メモリ上の全ての通信ログをクリアしますか？\nこの操作は元に戻せません。\nよろしければ「はい」と入力してください。", title="ログクリア確認")
        user_input = dialog.get_input()
        if user_input and user_input.lower() == "はい":
             self.logger.clear_logs()
             self.refresh_logs()
        elif user_input is not None: # 何か入力したが「はい」ではなかった場合
            tk.messagebox.showwarning("クリア中止", "入力が「はい」と一致しなかったため、ログはクリアされませんでした。", parent=self)


    def on_closing(self):
        """ウィンドウが閉じられるときの処理"""
        # self.withdraw() # ウィンドウを隠すだけならこちら
        self.destroy() # ウィンドウを破棄する

if __name__ == '__main__':
    # このウィンドウを単体でテストするためのコード
    app = customtkinter.CTk()
    customtkinter.set_appearance_mode("System") # or "Light", "Dark"
    customtkinter.set_default_color_theme("blue") # or "green", "dark-blue"
    app.title("Test App for Communication Log")
    app.geometry("400x300")

    # ダミーログの追加 (テスト用)
    logger_instance = CommunicationLogger()
    logger_instance.add_log("sent", "text_generation", "これはテスト用の送信プロンプトです。\n複数行のテストも兼ねています。")
    logger_instance.add_log("received", "text_generation", "これはテスト用のAIレスポンスです。")
    for i in range(5): # 少し多めにログを追加
        logger_instance.add_log("sent", "voice_synthesis", f"テスト用音声合成リクエスト {i+1}。長めの文章も入れてみましょう。祇園精舎の鐘の声、諸行無常の響きあり。")
        logger_instance.add_log("received", "voice_synthesis", f"音声合成結果 {i+1} (これはダミーです。通常、音声合成のレスポンスBodyは記録しませんが、テストとして)")


    # グローバル変数やクラス変数としてウィンドウインスタンスを保持しないようにする
    # log_window_instance = None

    def open_log_window():
        # nonlocal log_window_instance # nonlocalは不要
        # if log_window_instance is None or not log_window_instance.winfo_exists():
        #     log_window_instance = CommunicationLogWindow(app)
        # else:
        #     log_window_instance.deiconify()
        #     log_window_instance.lift()
        #     log_window_instance.focus()
        #     if hasattr(log_window_instance, 'refresh_logs'):
        #         log_window_instance.refresh_logs()

        # シンプルに毎回新しいウィンドウを開くか、launcher.py と同様の管理をする
        # ここではテストなのでシンプルに毎回開く
        new_log_win = CommunicationLogWindow(app)
        # new_log_win.grab_set() # モーダルにする場合はコメント解除


    open_button = customtkinter.CTkButton(app, text="ログウィンドウを開く", command=open_log_window)
    open_button.pack(pady=20)

    app.mainloop()
