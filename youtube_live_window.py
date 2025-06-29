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

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class YouTubeLiveWindow:
    def __init__(self, root: customtkinter.CTk):
        self.root = root
        self.root.title("YouTube Live 配信")
        self.root.geometry("950x750") # 先にウィンドウサイズを設定

        # 仮のローディング表示
        self.loading_label = customtkinter.CTkLabel(self.root, text="読み込み中...", font=("Yu Gothic UI", 18))
        self.loading_label.pack(expand=True, fill="both")
        self.root.update_idletasks() # ウィンドウとラベルを即時描画

        # 時間のかかる処理を after で遅延させる
        self.root.after(50, self._initialize_components) # 50ms 遅延

    def _initialize_components(self):
        # ローディング表示を削除
        if hasattr(self, 'loading_label') and self.loading_label.winfo_exists():
            self.loading_label.pack_forget()
            self.loading_label.destroy()

        # 本来の初期化処理
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
        self.log("YouTube Live ウィンドウ: 初期化完了。")

    def log(self, message, to_widget=True):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        logger.info(message)
        if to_widget and hasattr(self, 'log_text_widget') and self.log_text_widget:
            try:
                self.log_text_widget.configure(state="normal")
                self.log_text_widget.insert("end", log_message)
                self.log_text_widget.see("end")
                self.log_text_widget.configure(state="disabled")
            except tk.TclError:
                pass

    def load_settings_for_youtube_live(self):
        self.refresh_character_dropdown()
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
        self.log("YouTube Live ウィンドウ: 設定を読み込みました。")

    def save_settings_for_youtube_live(self):
        if "streaming_settings" not in self.config.config:
            self.config.config["streaming_settings"] = {}
        self.config.config["streaming_settings"]["live_id"] = self.live_id_var.get()
        self.config.config["streaming_settings"]["current_character_for_youtube_live"] = self.current_character_id
        self.config.config["streaming_settings"]["youtube_response_interval"] = self.response_interval_var.get()
        self.config.config["streaming_settings"]["youtube_auto_response"] = self.auto_response_var.get()
        self.config.save_config()
        self.log("YouTube Live ウィンドウ: 設定を保存しました。")


    def create_widgets(self):
        main_frame = customtkinter.CTkFrame(self.root) # paddingはFrame自体に
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # キャラクター選択
        char_outer_frame = customtkinter.CTkFrame(main_frame)
        char_outer_frame.pack(fill="x", padx=5, pady=5)
        customtkinter.CTkLabel(char_outer_frame, text="キャラクター選択", font=self.label_font).pack(anchor="w", padx=10, pady=(5,0))
        char_frame = customtkinter.CTkFrame(char_outer_frame)
        char_frame.pack(fill="x", padx=5, pady=5)

        char_control_frame = customtkinter.CTkFrame(char_frame, fg_color="transparent")
        char_control_frame.pack(fill="x")
        customtkinter.CTkLabel(char_control_frame, text="アクティブキャラクター:", font=self.default_font).pack(side="left", padx=(0,5))
        self.character_var = tk.StringVar()
        self.character_combo = customtkinter.CTkComboBox(char_control_frame, variable=self.character_var, state="readonly", width=250, font=self.default_font, command=self.on_character_selected)
        self.character_combo.pack(side="left", padx=5)
        customtkinter.CTkButton(char_control_frame, text="🔄 更新", command=self.refresh_character_dropdown, font=self.default_font, width=80).pack(side="left", padx=5)

        # 配信制御
        stream_outer_frame = customtkinter.CTkFrame(main_frame)
        stream_outer_frame.pack(fill="x", padx=5, pady=5)
        customtkinter.CTkLabel(stream_outer_frame, text="配信制御", font=self.label_font).pack(anchor="w", padx=10, pady=(5,0))
        stream_frame = customtkinter.CTkFrame(stream_outer_frame)
        stream_frame.pack(fill="x", padx=5, pady=5)

        youtube_frame = customtkinter.CTkFrame(stream_frame, fg_color="transparent")
        youtube_frame.pack(fill="x", pady=2)
        customtkinter.CTkLabel(youtube_frame, text="YouTube ライブID:", font=self.default_font).grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.live_id_var = tk.StringVar()
        customtkinter.CTkEntry(youtube_frame, textvariable=self.live_id_var, width=300, font=self.default_font).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.start_button = customtkinter.CTkButton(youtube_frame, text="配信開始", command=self.toggle_streaming_action, font=self.default_font)
        self.start_button.grid(row=0, column=2, padx=10, pady=5)
        youtube_frame.grid_columnconfigure(1, weight=1)

        stream_settings_frame = customtkinter.CTkFrame(stream_frame, fg_color="transparent")
        stream_settings_frame.pack(fill="x", pady=5)
        customtkinter.CTkLabel(stream_settings_frame, text="応答間隔 (秒):", font=self.default_font).grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.response_interval_var = tk.DoubleVar(value=5.0)
        self.response_interval_slider = customtkinter.CTkSlider(stream_settings_frame, from_=1.0, to=20.0, variable=self.response_interval_var, width=200, command=self._update_interval_label)
        self.response_interval_slider.grid(row=0, column=1, padx=5, pady=5)
        self.response_interval_label = customtkinter.CTkLabel(stream_settings_frame, text=f"{self.response_interval_var.get():.1f}", font=self.default_font, width=30)
        self.response_interval_label.grid(row=0, column=2, padx=5, pady=5)
        customtkinter.CTkLabel(stream_settings_frame, text="自動応答:", font=self.default_font).grid(row=0, column=3, sticky="w", padx=(20,0), pady=5)
        self.auto_response_var = tk.BooleanVar(value=True)
        customtkinter.CTkCheckBox(stream_settings_frame, variable=self.auto_response_var, text="", font=self.default_font).grid(row=0, column=4, padx=5, pady=5)

        # ログ表示
        log_outer_frame = customtkinter.CTkFrame(main_frame)
        log_outer_frame.pack(fill="both", expand=True, padx=5, pady=5)
        customtkinter.CTkLabel(log_outer_frame, text="システムログ (YouTube Live)", font=self.label_font).pack(anchor="w", padx=10, pady=(5,0))
        log_frame = customtkinter.CTkFrame(log_outer_frame)
        log_frame.pack(fill="both", expand=True, padx=5, pady=5)

        log_control_frame = customtkinter.CTkFrame(log_frame, fg_color="transparent")
        log_control_frame.pack(fill="x", pady=(0,5))
        customtkinter.CTkButton(log_control_frame, text="📄 ログクリア", command=self.clear_log_widget, font=self.default_font).pack(side="left", padx=5)

        self.log_text_widget = customtkinter.CTkTextbox(log_frame, wrap="word", state="disabled", font=self.default_font) # CTkTextbox
        self.log_text_widget.pack(fill="both", expand=True)

        # ステータスバー
        self.status_bar_label = customtkinter.CTkLabel(main_frame, text="準備完了", anchor="w", font=self.default_font)
        self.status_bar_label.pack(fill="x", padx=5, pady=(5,0), side="bottom")

    def _update_interval_label(self, value): # CTkSliderのcommandは値を直接渡す
        try:
            f_value = float(value)
            self.response_interval_label.configure(text=f"{f_value:.1f}")
        except ValueError:
            pass

    def refresh_character_dropdown(self):
        characters = self.character_manager.get_all_characters()
        char_options = [f"{data.get('name', 'Unknown')} ({char_id})" for char_id, data in characters.items()]
        self.character_combo.configure(values=char_options if char_options else ["キャラクターなし"])
        if char_options:
            current_selection = self.character_var.get()
            if current_selection in char_options: self.character_var.set(current_selection)
            else: self.character_var.set(char_options[0])
            self.on_character_selected(None) # event引数なしで呼び出し
        else:
            self.character_var.set("キャラクターなし")
            self.current_character_id = ""
            if hasattr(self, 'status_bar_label'): self.status_bar_label.configure(text="キャラクター未選択") # 修正
        self.log("YouTube Live: キャラクタードロップダウン更新", to_widget=False)

    def on_character_selected(self, choice=None): # CTkComboBoxのcommandは選択値を渡す
        selection = self.character_var.get()
        if selection and '(' in selection and ')' in selection and selection != "キャラクターなし":
            self.current_character_id = selection.split('(')[-1].replace(')', '')
            char_name = selection.split(' (')[0]
            self.log(f"YouTube Live: キャラクター '{char_name}' (ID: {self.current_character_id}) を選択。", to_widget=False)
            if hasattr(self, 'status_bar_label'): self.status_bar_label.configure(text=f"キャラクター: {char_name}") # 修正
        else:
            self.current_character_id = ""
            if hasattr(self, 'status_bar_label'): self.status_bar_label.configure(text="キャラクター未選択") # 修正


    def toggle_streaming_action(self):
        if not self.is_streaming:
            self.start_streaming_action()
        else:
            self.stop_streaming_action()

    def start_streaming_action(self):
        if not self.current_character_id:
            messagebox.showwarning("エラー", "配信キャラクターを選択してください。", parent=self.root)
            return
        live_id = self.live_id_var.get()
        if not live_id:
            messagebox.showwarning("エラー", "YouTube ライブIDを入力してください。", parent=self.root)
            return
        if not self.config.get_system_setting("google_ai_api_key"):
            messagebox.showwarning("エラー", "Google AI Studio APIキーが設定されていません（設定画面を確認）。", parent=self.root)
            return
        if not self.config.get_system_setting("youtube_api_key"):
            messagebox.showwarning("エラー", "YouTube APIキーが設定されていません（設定画面を確認）。", parent=self.root)
            return

        self.is_streaming = True
        self.start_button.configure(text="配信停止") # 修正
        if hasattr(self, 'status_bar_label'): self.status_bar_label.configure(text="🔴 配信中...") # 修正
        self.log("🎬 AITuber配信を開始します...")

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
            loop.run_until_complete(self.aituber_system_instance.run_streaming()) # 引数なしで呼び出し、メソッド名を修正
        except Exception as e:
            self.log(f"❌ 配信ループ中にエラー: {e}")
            # エラー発生時もUIの状態を更新
            self.root.after(0, self.handle_streaming_error) # メインスレッドでUI更新
        finally:
            loop.close()
            # is_streaming フラグに基づいてUIを最終調整
            if not self.is_streaming : # 正常終了または手動停止の場合
                 self.root.after(0, self.update_ui_after_stream_stop)


    def handle_streaming_error(self):
        # 配信がエラーで止まった場合のUI更新
        self.is_streaming = False
        self.start_button.configure(text="配信開始") # 修正
        if hasattr(self, 'status_bar_label'): self.status_bar_label.configure(text="⚠️ 配信エラー発生") # 修正
        messagebox.showerror("配信エラー", "配信中にエラーが発生しました。詳細はログを確認してください。", parent=self.root)

    def update_ui_after_stream_stop(self):
        # 配信が正常に（または手動で）停止した後のUI更新
        self.start_button.configure(text="配信開始") # 修正
        if hasattr(self, 'status_bar_label'): self.status_bar_label.configure(text="準備完了") # 修正
        self.log("⏹️ AITuber配信が停止しました。")


    def stop_streaming_action(self):
        if self.is_streaming:
            self.log("⏹️ AITuber配信の停止を試みます...")
            self.is_streaming = False # これでaituber_system_instance内のループが止まるはず
            # aituber_task の終了を待つか、joinタイムアウトを設定することも検討
            # ここでは、フラグ変更でループが自然終了するのを期待
            # UIの更新は _run_streaming_loop の finally や、必要ならここでも行う
            self.start_button.configure(text="配信開始") # 修正
            if hasattr(self, 'status_bar_label'): self.status_bar_label.configure(text="準備完了") # 修正


    def clear_log_widget(self):
        if hasattr(self, 'log_text_widget') and self.log_text_widget:
            self.log_text_widget.config(state=tk.NORMAL)
            self.log_text_widget.delete(1.0, tk.END)
            self.log_text_widget.config(state=tk.DISABLED)
            self.log("YouTube Live: ログ表示をクリアしました。", to_widget=False)


    def on_closing(self):
        if self.is_streaming:
            if messagebox.askokcancel("終了確認", "配信中です。本当に終了しますか？", parent=self.root):
                self.stop_streaming_action()
                # ストリーミングスレッドの終了を少し待つ
                if self.aituber_task and self.aituber_task.is_alive():
                    self.log("終了前にストリーミングスレッドの完了を待機中...", to_widget=False)
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
