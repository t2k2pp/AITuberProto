import customtkinter
import tkinter as tk # messagebox のため
import os # ファイル存在確認のため
from communication_logger import CommunicationLogger
from i18n_setup import _ # 国際化対応

class CommunicationLogWindow(customtkinter.CTkToplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self._ = _ # 翻訳関数をインスタンス変数として保持
        self.title(self._("communication_log.title"))
        self.geometry("800x600")

        self.logger = CommunicationLogger() # ロガーのインスタンスを取得

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        main_frame = customtkinter.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        button_frame = customtkinter.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(0, 10))

        self.refresh_button = customtkinter.CTkButton(button_frame, text=self._("communication_log.button.refresh"), command=self.refresh_logs)
        self.refresh_button.pack(side="left", padx=(0, 5))

        self.save_button = customtkinter.CTkButton(button_frame, text=self._("communication_log.button.save_snapshot"), command=self.save_snapshot_logs)
        self.save_button.pack(side="left", padx=5)

        self.clear_memory_button = customtkinter.CTkButton(button_frame, text=self._("communication_log.button.clear_memory"), command=self.clear_memory_logs)
        self.clear_memory_button.pack(side="left", padx=5)

        # セッションログファイルパス表示ラベル
        self.session_file_label = customtkinter.CTkLabel(button_frame, text=self._("communication_log.session_file_label.default"), font=("Yu Gothic UI", 10), anchor="w")
        self.session_file_label.pack(side="left", padx=10, fill="x", expand=True)


        self.log_display_textbox = customtkinter.CTkTextbox(main_frame, wrap="word", state="disabled", font=("Yu Gothic UI", 12))
        self.log_display_textbox.pack(fill="both", expand=True)

        self.refresh_logs() # 初期表示

    def refresh_logs(self):
        """セッションログファイルからログを読み込み表示を更新する"""
        self.log_display_textbox.configure(state="normal")
        self.log_display_textbox.delete("1.0", "end")

        session_log_path = self.logger.get_session_log_filepath()
        base_filename = os.path.basename(session_log_path) if session_log_path else ""

        if session_log_path and os.path.exists(session_log_path):
            try:
                # セッションログファイルパスをラベルに表示
                self.session_file_label.configure(text=self._("communication_log.session_file_label.recording", filename=base_filename))
                with open(session_log_path, "r", encoding="utf-8") as f:
                    log_content = f.read()
                if log_content:
                    self.log_display_textbox.insert("end", log_content)
                else:
                    self.log_display_textbox.insert("end", self._("communication_log.log_empty", filename=base_filename))
            except Exception as e:
                self.log_display_textbox.insert("end", self._("communication_log.log_read_error", filename=base_filename, error=str(e)))
                tk.messagebox.showerror(
                    self._("communication_log.messagebox.read_error.title"),
                    self._("communication_log.messagebox.read_error.message", filepath=session_log_path, error=str(e)),
                    parent=self
                )
        else:
            if session_log_path:
                 no_log_message = self._("communication_log.log_not_found_specific", filename=base_filename)
                 self.session_file_label.configure(text=self._("communication_log.session_file_label.waiting", filename=base_filename))
            else:
                 no_log_message = self._("communication_log.log_not_found_default")
                 self.session_file_label.configure(text=self._("communication_log.session_file_label.path_not_set"))

            self.log_display_textbox.insert("end", no_log_message + "\n")

        self.log_display_textbox.configure(state="disabled")

    def save_snapshot_logs(self):
        """現在メモリに読み込まれているログのスナップショットをファイルに保存する"""
        self.logger.save_logs_to_file(parent_window=self)

    def clear_memory_logs(self):
        """メモリ上のログのみをクリアする。表示は次の「更新」まで変わらない。"""
        dialog = customtkinter.CTkInputDialog(
            text=self._("communication_log.input_dialog.clear_memory.text"),
            title=self._("communication_log.input_dialog.clear_memory.title")
        )
        user_input = dialog.get_input()

        # 「はい」の比較は言語に依存しないようにするべきだが、今回は現状維持
        # 英語環境の場合は "yes" と比較する必要がある。
        # より良い方法は、翻訳キー "common.yes" のようなものを用意し、それと比較すること。
        # ここでは、日本語環境でのみ正しく動作する可能性がある。
        # 修正案：user_input.lower() == self._("common.yes").lower() のような形
        # common.yes を locales ファイルに追加したため、以下のように修正。
        confirm_word = self._("common.yes").lower()

        if user_input and user_input.lower() == confirm_word:
            self.logger.clear_logs()
            tk.messagebox.showinfo(
                self._("communication_log.messagebox.clear_success.title"),
                self._("communication_log.messagebox.clear_success.message"),
                parent=self
            )
        elif user_input is not None: # キャンセルではなく、何か入力したが一致しなかった場合
            tk.messagebox.showwarning(
                self._("communication_log.messagebox.clear_canceled.title"),
                self._("communication_log.messagebox.clear_canceled.message"), # メッセージに「'はい'または'yes'と～」のように修正も検討
                parent=self
            )

    def on_closing(self):
        pass
