import customtkinter
import tkinter as tk # 基本的な型 (StringVarなど) と標準ダイアログのため
from tkinter import messagebox # 標準ダイアログはそのまま使用 (filedialogは未使用)
import asyncio
import threading
from datetime import datetime
import time
import sys # フォント選択のため

from config import ConfigManager
from character_manager import CharacterManager
from audio_manager import VoiceEngineManager, AudioPlayer
from streaming import AITuberStreamingSystem
# from i18n_setup import _, init_i18n # モジュールレベルのインポートから変更
import i18n_setup # モジュールとしてインポート

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class YouTubeLiveWindow:
    def __init__(self, root: customtkinter.CTk):
        i18n_setup.init_i18n() # 強制的にi18nを再初期化
        self._ = i18n_setup.get_translator() # 最新の翻訳関数を取得

        self.root = root
        # self._ = i18n_setup.get_translator() # インスタンス化時に最新の翻訳関数を取得 <- 移動
        # init_i18n() # Ensure i18n is initialized, though it should be by main.py
        self.root.title(self._("youtube_live.title"))
        self.root.geometry("950x750") # 先にウィンドウサイズを設定

        # 仮のローディング表示
        self.loading_label = customtkinter.CTkLabel(self.root, text=self._("youtube_live.loading"), font=("Yu Gothic UI", 18))
        self.loading_label.pack(expand=True, fill="both")
        self.root.update_idletasks() # ウィンドウとラベルを即時描画

        # 時間のかかる処理を after で遅延させる
        self.root.after(50, self._initialize_components) # 50ms 遅延

    def _initialize_components(self):
        # ローディング表示を削除
        if hasattr(self, 'loading_label') and self.loading_label.winfo_exists():
            self.loading_label.pack_forget()
            self.loading_label.destroy()

        # self._ が __init__ で設定されていることを確認 (通常は不要だが念のため)
        if not hasattr(self, '_') or not callable(self._):
            self._ = i18n_setup.get_translator()


        # 本来の初期化処理
        # Ensure i18n is initialized, might be redundant if main.py handles it robustly
        # init_i18n() # Redundant if called in __init__ or if main.py calls it.
        # If settings window can change lang, this window might need a refresh mechanism.

        self.config = ConfigManager()
        self.character_manager = CharacterManager(self.config)
        self.voice_manager = VoiceEngineManager()
        self.audio_player = AudioPlayer(config_manager=self.config)

        self.is_streaming = False
        self.current_character_id = ""
        self.aituber_task = None

        # フォント設定
        self.default_font = ("Yu Gothic UI", 12)
        if sys.platform == "darwin": self.default_font = ("Hiragino Sans", 14)
        elif sys.platform.startswith("linux"): self.default_font = ("Noto Sans CJK JP", 12)
        self.label_font = (self.default_font[0], self.default_font[1] + 1, "bold")

        self.create_widgets()
        self.load_settings_for_youtube_live()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.log("youtube_live.log_init_complete", is_translation_key=True) # is_translation_key を明示

    def log(self, message_key_or_text, to_widget=True, is_translation_key=False, **kwargs):
        # self._ が利用可能か確認し、なければフォールバック（通常は不要）
        translate_func = getattr(self, '_', i18n_setup.get_translator())

        timestamp = datetime.now().strftime("%H:%M:%S")
        if is_translation_key:
            log_message_content = translate_func(message_key_or_text, **kwargs)
        else:
            log_message_content = message_key_or_text
        log_message = f"[{timestamp}] {log_message_content}\n"
        logger.info(log_message_content) # loggerには翻訳後のメッセージのみ
        if to_widget and hasattr(self, 'log_text_widget') and self.log_text_widget:
            try:
                self.log_text_widget.configure(state="normal")
                self.log_text_widget.insert("end", log_message)
                self.log_text_widget.see("end")
                self.log_text_widget.configure(state="disabled")
            except tk.TclError: # ウィジェットが破棄された後などに発生する可能性
                pass

    def load_settings_for_youtube_live(self):
        self.refresh_character_dropdown()
        # log_message = f"[{timestamp}] {message}\n" # この部分は重複しており、意味がないので削除
        # logger.info(message)
        # if to_widget and hasattr(self, 'log_text_widget') and self.log_text_widget:
        #     try:
        #         self.log_text_widget.configure(state="normal")
        #         self.log_text_widget.insert("end", log_message)
        #         self.log_text_widget.see("end")
        #         self.log_text_widget.configure(state="disabled")
        #     except tk.TclError:
        #         pass

    # def load_settings_for_youtube_live(self): # この関数は上記と重複しているので、どちらかが正しい実装。下を採用。
    #     self.refresh_character_dropdown()
        saved_char_id = self.config.config.get("streaming_settings", {}).get("current_character_for_youtube_live")
        if saved_char_id:
            all_chars = self.character_manager.get_all_characters()
            if saved_char_id in all_chars:
                char_name = all_chars[saved_char_id].get('name', 'Unknown')
                display_text = f"{char_name} ({saved_char_id})"
                if display_text in self.character_combo.cget("values"):
                    self.character_var.set(display_text)
                    self.on_character_selected(None) # event引数なしで呼び出し

        self.live_id_var.set(self.config.config.get("streaming_settings", {}).get("live_id", ""))
        self.response_interval_var.set(self.config.config.get("streaming_settings", {}).get("youtube_response_interval", 5.0))
        # CTkSliderの値を更新
        if hasattr(self, 'response_interval_slider'):
             self.response_interval_slider.set(self.response_interval_var.get())
             self._update_interval_label(self.response_interval_var.get())

        self.auto_response_var.set(self.config.config.get("streaming_settings", {}).get("youtube_auto_response", True))
        self.log("youtube_live.log_settings_loaded", is_translation_key=True)

    def save_settings_for_youtube_live(self):
        if "streaming_settings" not in self.config.config:
            self.config.config["streaming_settings"] = {}
        self.config.config["streaming_settings"]["live_id"] = self.live_id_var.get()
        self.config.config["streaming_settings"]["current_character_for_youtube_live"] = self.current_character_id
        self.config.config["streaming_settings"]["youtube_response_interval"] = self.response_interval_var.get()
        self.config.config["streaming_settings"]["youtube_auto_response"] = self.auto_response_var.get()
        self.config.save_config()
        self.log("youtube_live.log_settings_saved", is_translation_key=True)


    def create_widgets(self):
        # self._ を確実に使用するために、ウィジェット作成前に再取得・確認
        self._ = getattr(self, '_', i18n_setup.get_translator())

        main_frame = customtkinter.CTkFrame(self.root) # paddingはFrame自体に
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # キャラクター選択
        char_outer_frame = customtkinter.CTkFrame(main_frame)
        char_outer_frame.pack(fill="x", padx=5, pady=5)
        customtkinter.CTkLabel(char_outer_frame, text=self._("youtube_live.label.character_selection"), font=self.label_font).pack(anchor="w", padx=10, pady=(5,0))
        char_frame = customtkinter.CTkFrame(char_outer_frame)
        char_frame.pack(fill="x", padx=5, pady=5)

        char_control_frame = customtkinter.CTkFrame(char_frame, fg_color="transparent")
        char_control_frame.pack(fill="x")
        customtkinter.CTkLabel(char_control_frame, text=self._("youtube_live.label.active_character"), font=self.default_font).pack(side="left", padx=(0,5))
        self.character_var = tk.StringVar()
        self.character_combo = customtkinter.CTkComboBox(char_control_frame, variable=self.character_var, state="readonly", width=250, font=self.default_font, command=self.on_character_selected)
        self.character_combo.pack(side="left", padx=5)
        customtkinter.CTkButton(char_control_frame, text=self._("youtube_live.button.refresh_characters"), command=self.refresh_character_dropdown, font=self.default_font, width=80).pack(side="left", padx=5)

        # 配信制御
        stream_outer_frame = customtkinter.CTkFrame(main_frame)
        stream_outer_frame.pack(fill="x", padx=5, pady=5)
        customtkinter.CTkLabel(stream_outer_frame, text=self._("youtube_live.label.stream_control"), font=self.label_font).pack(anchor="w", padx=10, pady=(5,0))
        stream_frame = customtkinter.CTkFrame(stream_outer_frame)
        stream_frame.pack(fill="x", padx=5, pady=5)

        youtube_frame = customtkinter.CTkFrame(stream_frame, fg_color="transparent")
        youtube_frame.pack(fill="x", pady=2)
        customtkinter.CTkLabel(youtube_frame, text=self._("youtube_live.label.youtube_live_id"), font=self.default_font).grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.live_id_var = tk.StringVar()
        customtkinter.CTkEntry(youtube_frame, textvariable=self.live_id_var, width=300, font=self.default_font).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.start_button = customtkinter.CTkButton(youtube_frame, text=self._("youtube_live.button.start_streaming"), command=self.toggle_streaming_action, font=self.default_font)
        self.start_button.grid(row=0, column=2, padx=10, pady=5)
        youtube_frame.grid_columnconfigure(1, weight=1)

        stream_settings_frame = customtkinter.CTkFrame(stream_frame, fg_color="transparent")
        stream_settings_frame.pack(fill="x", pady=5)
        customtkinter.CTkLabel(stream_settings_frame, text=self._("youtube_live.label.response_interval"), font=self.default_font).grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.response_interval_var = tk.DoubleVar(value=5.0)
        self.response_interval_slider = customtkinter.CTkSlider(stream_settings_frame, from_=1.0, to=20.0, variable=self.response_interval_var, width=200, command=self._update_interval_label)
        self.response_interval_slider.grid(row=0, column=1, padx=5, pady=5)
        self.response_interval_label = customtkinter.CTkLabel(stream_settings_frame, text=f"{self.response_interval_var.get():.1f}", font=self.default_font, width=30)
        self.response_interval_label.grid(row=0, column=2, padx=5, pady=5)
        customtkinter.CTkLabel(stream_settings_frame, text=self._("youtube_live.label.auto_response"), font=self.default_font).grid(row=0, column=3, sticky="w", padx=(20,0), pady=5)
        self.auto_response_var = tk.BooleanVar(value=True)
        customtkinter.CTkCheckBox(stream_settings_frame, variable=self.auto_response_var, text="", font=self.default_font).grid(row=0, column=4, padx=5, pady=5)

        # ログ表示
        log_outer_frame = customtkinter.CTkFrame(main_frame)
        log_outer_frame.pack(fill="both", expand=True, padx=5, pady=5)
        customtkinter.CTkLabel(log_outer_frame, text=self._("youtube_live.label.system_log"), font=self.label_font).pack(anchor="w", padx=10, pady=(5,0))
        log_frame = customtkinter.CTkFrame(log_outer_frame)
        log_frame.pack(fill="both", expand=True, padx=5, pady=5)

        log_control_frame = customtkinter.CTkFrame(log_frame, fg_color="transparent")
        log_control_frame.pack(fill="x", pady=(0,5))
        customtkinter.CTkButton(log_control_frame, text=self._("youtube_live.button.clear_log"), command=self.clear_log_widget, font=self.default_font).pack(side="left", padx=5)

        self.log_text_widget = customtkinter.CTkTextbox(log_frame, wrap="word", state="disabled", font=self.default_font) # CTkTextbox
        self.log_text_widget.pack(fill="both", expand=True)

        # ステータスバー
        self.status_bar_label = customtkinter.CTkLabel(main_frame, text=self._("youtube_live.status.ready"), anchor="w", font=self.default_font)
        self.status_bar_label.pack(fill="x", padx=5, pady=(5,0), side="bottom")

    def _update_interval_label(self, value): # CTkSliderのcommandは値を直接渡す
        try:
            f_value = float(value)
            self.response_interval_label.configure(text=f"{f_value:.1f}")
        except ValueError:
            pass

    def refresh_character_dropdown(self):
        self._ = getattr(self, '_', i18n_setup.get_translator()) # Ensure self._ is available
        characters = self.character_manager.get_all_characters()
        char_options = [f"{data.get('name', 'Unknown')} ({char_id})" for char_id, data in characters.items()]
        self.character_combo.configure(values=char_options if char_options else [self._("youtube_live.dropdown.no_characters")])
        if char_options:
            current_selection = self.character_var.get()
            if current_selection in char_options: self.character_var.set(current_selection)
            else: self.character_var.set(char_options[0])
            self.on_character_selected(None) # event引数なしで呼び出し
        else:
            self.character_var.set(self._("youtube_live.dropdown.no_characters"))
            self.current_character_id = ""
            if hasattr(self, 'status_bar_label'): self.status_bar_label.configure(text=self._("youtube_live.status.no_character_selected"))
        self.log("youtube_live.log_char_dropdown_updated", to_widget=False, is_translation_key=True)

    def on_character_selected(self, choice=None): # CTkComboBoxのcommandは選択値を渡す
        self._ = getattr(self, '_', i18n_setup.get_translator()) # Ensure self._ is available
        selection = self.character_var.get()
        if selection and '(' in selection and ')' in selection and selection != self._("youtube_live.dropdown.no_characters"):
            self.current_character_id = selection.split('(')[-1].replace(')', '')
            char_name = selection.split(' (')[0]
            self.log("youtube_live.log_char_selected", to_widget=False, is_translation_key=True, character_name=char_name, character_id=self.current_character_id)
            if hasattr(self, 'status_bar_label'): self.status_bar_label.configure(text=self._("youtube_live.status.character_selected").format(character_name=char_name))
        else:
            self.current_character_id = ""
            if hasattr(self, 'status_bar_label'): self.status_bar_label.configure(text=self._("youtube_live.status.no_character_selected"))


    def toggle_streaming_action(self):
        if not self.is_streaming:
            self.start_streaming_action()
        else:
            self.stop_streaming_action()

    def start_streaming_action(self):
        self._ = getattr(self, '_', i18n_setup.get_translator()) # Ensure self._ is available
        if not self.current_character_id:
            messagebox.showwarning(self._("youtube_live.messagebox.error.title"), self._("youtube_live.messagebox.error.no_character_selected"), parent=self.root)
            return
        live_id = self.live_id_var.get()
        if not live_id:
            messagebox.showwarning(self._("youtube_live.messagebox.error.title"), self._("youtube_live.messagebox.error.no_live_id"), parent=self.root)
            return
        if not self.config.get_system_setting("google_ai_api_key"):
            messagebox.showwarning(self._("youtube_live.messagebox.error.title"), self._("youtube_live.messagebox.error.no_google_api_key"), parent=self.root)
            return
        if not self.config.get_system_setting("youtube_api_key"):
            messagebox.showwarning(self._("youtube_live.messagebox.error.title"), self._("youtube_live.messagebox.error.no_youtube_api_key"), parent=self.root)
            return

        self.is_streaming = True
        self.start_button.configure(text=self._("youtube_live.button.stop_streaming"))
        if hasattr(self, 'status_bar_label'): self.status_bar_label.configure(text=self._("youtube_live.status.streaming"))
        self.log("youtube_live.log_stream_starting", is_translation_key=True)

        # AITuberStreamingSystem のインスタンス化と実行
        # 必要な設定を渡す
        self.aituber_system_instance = AITuberStreamingSystem(
            config=self.config, # ConfigManagerインスタンス
            character_id=self.current_character_id,
            character_manager=self.character_manager,
            voice_manager=self.voice_manager,
            audio_player=self.audio_player,
            log_callback=self.log, # GUIのログメソッドを渡す
            # GUIからの追加設定
            youtube_live_id=live_id,
            response_interval=self.response_interval_var.get(),
            auto_response_enabled=self.auto_response_var.get()
        )
        # 別スレッドで実行
        self.aituber_task = threading.Thread(target=self._run_streaming_loop, daemon=True)
        self.aituber_task.start()


    def _run_streaming_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # AITuberStreamingSystem の run_streaming (またはそれに類するメソッド) を呼び出す
            # このメソッドは self.is_streaming フラグを見てループ制御する想定
            loop.run_until_complete(self.aituber_system_instance.run_youtube_live_loop(lambda: self.is_streaming))
        except Exception as e:
            self.log("youtube_live.log_stream_loop_error", is_translation_key=True, error=str(e))
            # エラー発生時もUIの状態を更新
            self.root.after(0, self.handle_streaming_error) # メインスレッドでUI更新
        finally:
            loop.close()
            # is_streaming フラグに基づいてUIを最終調整
            if not self.is_streaming : # 正常終了または手動停止の場合
                 self.root.after(0, self.update_ui_after_stream_stop)


    def handle_streaming_error(self):
        self._ = getattr(self, '_', i18n_setup.get_translator()) # Ensure self._ is available
        # 配信がエラーで止まった場合のUI更新
        self.is_streaming = False
        self.start_button.configure(text=self._("youtube_live.button.start_streaming"))
        if hasattr(self, 'status_bar_label'): self.status_bar_label.configure(text=self._("youtube_live.status.error"))
        messagebox.showerror(self._("youtube_live.messagebox.error.title"), self._("youtube_live.messagebox.error.generic_stream_error"), parent=self.root)

    def update_ui_after_stream_stop(self):
        self._ = getattr(self, '_', i18n_setup.get_translator()) # Ensure self._ is available
        # 配信が正常に（または手動で）停止した後のUI更新
        self.start_button.configure(text=self._("youtube_live.button.start_streaming"))
        if hasattr(self, 'status_bar_label'): self.status_bar_label.configure(text=self._("youtube_live.status.ready"))
        self.log("youtube_live.log_stream_stopped", is_translation_key=True)


    def stop_streaming_action(self):
        self._ = getattr(self, '_', i18n_setup.get_translator()) # Ensure self._ is available
        if self.is_streaming:
            self.log("youtube_live.log_stream_stopping", is_translation_key=True)
            self.is_streaming = False # これでaituber_system_instance内のループが止まるはず
            # aituber_task の終了を待つか、joinタイムアウトを設定することも検討
            # ここでは、フラグ変更でループが自然終了するのを期待
            # UIの更新は _run_streaming_loop の finally や、必要ならここでも行う
            self.start_button.configure(text=self._("youtube_live.button.start_streaming"))
            if hasattr(self, 'status_bar_label'): self.status_bar_label.configure(text=self._("youtube_live.status.ready"))


    def clear_log_widget(self):
        self._ = getattr(self, '_', i18n_setup.get_translator()) # Ensure self._ is available
        if hasattr(self, 'log_text_widget') and self.log_text_widget:
            self.log_text_widget.config(state=tk.NORMAL)
            self.log_text_widget.delete(1.0, tk.END)
            self.log_text_widget.config(state=tk.DISABLED)
            self.log("youtube_live.log_cleared", to_widget=False, is_translation_key=True)


    def on_closing(self):
        self._ = getattr(self, '_', i18n_setup.get_translator()) # Ensure self._ is available
        if self.is_streaming:
            if messagebox.askokcancel(self._("youtube_live.messagebox.confirm_exit.title"), self._("youtube_live.messagebox.confirm_exit.message"), parent=self.root):
                self.stop_streaming_action()
                # ストリーミングスレッドの終了を少し待つ
                if self.aituber_task and self.aituber_task.is_alive():
                    self.log("youtube_live.log_waiting_for_thread", to_widget=False, is_translation_key=True)
                    self.aituber_task.join(timeout=2.0) # 最大2秒待つ
                self.save_settings_for_youtube_live() # 終了前に設定保存
                self.root.destroy()
        else:
            self.save_settings_for_youtube_live() # 終了前に設定保存
            self.root.destroy()


def main():
    root = tk.Tk()
    app = YouTubeLiveWindow(root)
    root.mainloop()

if __name__ == "__main__":
    main()
