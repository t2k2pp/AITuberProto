import customtkinter
import tkinter as tk # messagebox のため
import os # ファイル存在確認のため
from communication_logger import CommunicationLogger
import i18n_setup # 追加

class CommunicationLogWindow(customtkinter.CTkToplevel):
    def __init__(self, master=None):
        super().__init__(master)
        i18n_setup.init_i18n() # 強制再初期化
        self._ = i18n_setup.get_translator()

        self.title(self._("comm_log.title"))
        self.geometry("800x600")

        self.logger = CommunicationLogger() # ロガーのインスタンスを取得

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        main_frame = customtkinter.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        button_frame = customtkinter.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(0, 10))

        self.refresh_button = customtkinter.CTkButton(button_frame, text=self._("comm_log.button.refresh"), command=self.refresh_logs)
        self.refresh_button.pack(side="left", padx=(0, 5))

        self.save_button = customtkinter.CTkButton(button_frame, text=self._("comm_log.button.save_snapshot"), command=self.save_snapshot_logs)
        self.save_button.pack(side="left", padx=5)

        self.clear_memory_button = customtkinter.CTkButton(button_frame, text=self._("comm_log.button.clear_memory"), command=self.clear_memory_logs)
        self.clear_memory_button.pack(side="left", padx=5)

        # セッションログファイルパス表示ラベル
        self.session_file_label = customtkinter.CTkLabel(button_frame, text=self._("comm_log.label.session_log_status_default"), font=("Yu Gothic UI", 10), anchor="w")
        self.session_file_label.pack(side="left", padx=10, fill="x", expand=True)


        self.log_display_textbox = customtkinter.CTkTextbox(main_frame, wrap="word", state="disabled", font=("Yu Gothic UI", 12))
        self.log_display_textbox.pack(fill="both", expand=True)

        self.refresh_logs() # 初期表示

    def refresh_logs(self):
        """セッションログファイルからログを読み込み表示を更新する"""
        self.log_display_textbox.configure(state="normal")
        self.log_display_textbox.delete("1.0", "end")

        session_log_path = self.logger.get_session_log_filepath()
        filename_display = os.path.basename(session_log_path) if session_log_path else "N/A"

        if session_log_path and os.path.exists(session_log_path):
            try:
                self.session_file_label.configure(text=self._("comm_log.label.session_log_status_recording", filename=filename_display))
                with open(session_log_path, "r", encoding="utf-8") as f:
                    log_content = f.read()
                if log_content:
                    self.log_display_textbox.insert("end", log_content)
                else:
                    self.log_display_textbox.insert("end", self._("comm_log.message.file_empty", filename=filename_display))
            except Exception as e:
                self.log_display_textbox.insert("end", self._("comm_log.message.file_read_error", filename=filename_display, error=e))
                tk.messagebox.showerror(self._("comm_log.messagebox.read_error.title"), self._("comm_log.messagebox.read_error.message", filepath=session_log_path, error=e), parent=self)
        else:
            no_log_message = self._("comm_log.message.file_not_found_generic")
            if session_log_path:
                 no_log_message = self._("comm_log.message.file_not_found_specific", filename=filename_display)
                 self.session_file_label.configure(text=self._("comm_log.label.session_log_status_waiting", filename=filename_display))
            else:
                 self.session_file_label.configure(text=self._("comm_log.label.session_log_status_path_unset"))

            self.log_display_textbox.insert("end", no_log_message + "\n")

        self.log_display_textbox.configure(state="disabled")

    def save_snapshot_logs(self):
        """現在メモリに読み込まれているログのスナップショットをファイルに保存する"""
        self.logger.save_logs_to_file(parent_window=self)

    def clear_memory_logs(self):
        """メモリ上のログのみをクリアする。表示は次の「更新」まで変わらない。"""
        # CTkInputDialogのtextパラメータは翻訳された文字列を期待する
        # "はい" の部分は英語の場合 "yes" などになるため、比較もそれに応じて行う必要がある。
        # ここでは簡単のため、確認文字列自体は翻訳せず、メッセージのみ翻訳する。
        # または、より堅牢な確認方法（専用の確認ダイアログなど）を検討する。
        # 今回は、入力プロンプトの指示に従う形で、"yes" (英語の場合) または "はい" (日本語の場合) を期待する。
        # 翻訳キーで期待する入力文字列も定義できるようにする。
        # comm_log.input_dialog.clear_memory.confirm_input_text = "yes" (en.json) / "はい" (ja.json) のようなキーを作る。
        # ただし、CTkInputDialogはシンプルな入力なので、ここではメッセージのみ翻訳。
        # ユーザーには "yes" と入力するよう促す (英語の場合)。
        # 日本語環境では "はい" と入力するよう促す。
        # これを簡単にするため、ダイアログのメッセージに期待する文字列を埋め込む。
        expected_confirmation_text = self._("comm_log.input_dialog.clear_memory.confirm_input_text_value") # "yes" or "はい"

        dialog = customtkinter.CTkInputDialog(
            text=self._("comm_log.input_dialog.clear_memory.text", confirm_value=expected_confirmation_text),
            title=self._("comm_log.input_dialog.clear_memory.title")
        )
        user_input = dialog.get_input()

        if user_input and user_input.lower() == expected_confirmation_text.lower():
            self.logger.clear_logs()
            tk.messagebox.showinfo(self._("comm_log.messagebox.clear_complete.title"), self._("comm_log.messagebox.clear_complete.message"), parent=self)
        elif user_input is not None: # ユーザーが何か入力したが、期待する文字列ではなかった場合
            tk.messagebox.showwarning(self._("comm_log.messagebox.clear_aborted.title"), self._("comm_log.messagebox.clear_aborted.message", confirm_value=expected_confirmation_text), parent=self)
        # user_input is None の場合はキャンセルされたので何もしない

    def on_closing(self):
        pass
