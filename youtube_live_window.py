import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import asyncio
import threading
from datetime import datetime
import time # emergency_stopで使用

from config import ConfigManager
from character_manager import CharacterManager
from audio_manager import VoiceEngineManager, AudioPlayer
from streaming import AITuberStreamingSystem # ストリーミングシステム本体

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class YouTubeLiveWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Live 配信")
        self.root.geometry("900x700") # 元のメインタブより少し小さく

        self.config = ConfigManager()
        self.character_manager = CharacterManager(self.config)
        self.voice_manager = VoiceEngineManager()
        self.audio_player = AudioPlayer(config_manager=self.config)

        self.is_streaming = False
        self.current_character_id = "" # このウィンドウでのアクティブキャラクターID
        self.aituber_task = None

        self.create_widgets()
        self.load_settings_for_youtube_live()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)


    def log(self, message, to_widget=True):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        logger.info(message) # コンソール/ファイルログ
        if to_widget and hasattr(self, 'log_text_widget') and self.log_text_widget:
            try:
                self.log_text_widget.config(state=tk.NORMAL)
                self.log_text_widget.insert(tk.END, log_message)
                self.log_text_widget.see(tk.END)
                self.log_text_widget.config(state=tk.DISABLED)
            except tk.TclError: # ウィジェットが破棄された後など
                pass


    def load_settings_for_youtube_live(self):
        # キャラクタードロップダウンの初期化・選択
        self.refresh_character_dropdown()
        # 以前選択されていたキャラクターIDを復元しようと試みる (configから)
        saved_char_id = self.config.config.get("streaming_settings", {}).get("current_character_for_youtube_live") # 新しいキー名
        if saved_char_id:
            all_chars = self.character_manager.get_all_characters()
            if saved_char_id in all_chars:
                char_name = all_chars[saved_char_id].get('name', 'Unknown')
                display_text = f"{char_name} ({saved_char_id})"
                if display_text in self.character_combo['values']:
                    self.character_var.set(display_text)
                    self.on_character_selected() # IDを設定しステータスバー更新

        # ライブIDの読み込み
        self.live_id_var.set(self.config.config.get("streaming_settings", {}).get("live_id", ""))
        # 応答間隔と自動応答 (ConfigManager経由で取得する方が良いが、簡単のため直接)
        self.response_interval_var.set(self.config.config.get("streaming_settings", {}).get("youtube_response_interval", 5.0))
        self.auto_response_var.set(self.config.config.get("streaming_settings", {}).get("youtube_auto_response", True))

        self.log("YouTube Live ウィンドウ: 設定を読み込みました。")


    def save_settings_for_youtube_live(self):
        # このウィンドウに特化した設定を保存
        if "streaming_settings" not in self.config.config:
            self.config.config["streaming_settings"] = {}
        self.config.config["streaming_settings"]["live_id"] = self.live_id_var.get()
        self.config.config["streaming_settings"]["current_character_for_youtube_live"] = self.current_character_id
        self.config.config["streaming_settings"]["youtube_response_interval"] = self.response_interval_var.get()
        self.config.config["streaming_settings"]["youtube_auto_response"] = self.auto_response_var.get()
        self.config.save_config()
        self.log("YouTube Live ウィンドウ: 設定を保存しました。")


    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- gui.py の create_main_tab を参考にUI要素を配置 ---
        # キャラクター選択
        char_frame = ttk.LabelFrame(main_frame, text="キャラクター選択", padding="10")
        char_frame.pack(fill=tk.X, padx=5, pady=5)
        char_control_frame = ttk.Frame(char_frame)
        char_control_frame.pack(fill=tk.X)
        ttk.Label(char_control_frame, text="アクティブキャラクター:").pack(side=tk.LEFT)
        self.character_var = tk.StringVar()
        self.character_combo = ttk.Combobox(char_control_frame, textvariable=self.character_var, state="readonly", width=35)
        self.character_combo.pack(side=tk.LEFT, padx=10)
        self.character_combo.bind('<<ComboboxSelected>>', self.on_character_selected)
        ttk.Button(char_control_frame, text="🔄 更新", command=self.refresh_character_dropdown).pack(side=tk.LEFT, padx=5)
        # ttk.Button(char_control_frame, text="⚙️ 設定", command=self.open_selected_character_editor_from_youtube_live).pack(side=tk.LEFT, padx=5) # 別途実装要

        # 配信制御
        stream_frame = ttk.LabelFrame(main_frame, text="配信制御", padding="10")
        stream_frame.pack(fill=tk.X, padx=5, pady=5)
        youtube_frame = ttk.Frame(stream_frame)
        youtube_frame.pack(fill=tk.X, pady=2)
        ttk.Label(youtube_frame, text="YouTube ライブID:").grid(row=0, column=0, sticky=tk.W)
        self.live_id_var = tk.StringVar()
        ttk.Entry(youtube_frame, textvariable=self.live_id_var, width=45).grid(row=0, column=1, padx=10, sticky=tk.W)
        self.start_button = ttk.Button(youtube_frame, text="配信開始", command=self.toggle_streaming_action)
        self.start_button.grid(row=0, column=2, padx=10)

        stream_settings_frame = ttk.Frame(stream_frame)
        stream_settings_frame.pack(fill=tk.X, pady=5)
        ttk.Label(stream_settings_frame, text="応答間隔 (秒):").grid(row=0, column=0, sticky=tk.W)
        self.response_interval_var = tk.DoubleVar(value=5.0)
        self.response_interval_scale = ttk.Scale(stream_settings_frame, from_=1.0, to=20.0, variable=self.response_interval_var, orient=tk.HORIZONTAL, length=150, command=self._update_interval_label)
        self.response_interval_scale.grid(row=0, column=1, padx=5)
        self.response_interval_label = ttk.Label(stream_settings_frame, text=f"{self.response_interval_var.get():.1f}")
        self.response_interval_label.grid(row=0, column=2)
        ttk.Label(stream_settings_frame, text="自動応答:").grid(row=0, column=3, sticky=tk.W, padx=(20,0))
        self.auto_response_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(stream_settings_frame, variable=self.auto_response_var).grid(row=0, column=4, padx=5)

        # ログ表示
        log_frame = ttk.LabelFrame(main_frame, text="システムログ (YouTube Live)", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        log_control_frame = ttk.Frame(log_frame)
        log_control_frame.pack(fill=tk.X, pady=(0,5))
        ttk.Button(log_control_frame, text="📄 ログクリア", command=self.clear_log_widget).pack(side=tk.LEFT, padx=5)
        # ttk.Button(log_control_frame, text="💾 ログ保存", command=self.save_log_from_widget).pack(side=tk.LEFT, padx=5) # オプション

        log_display_area = ttk.Frame(log_frame)
        log_display_area.pack(fill=tk.BOTH, expand=True)
        self.log_text_widget = tk.Text(log_display_area, height=18, wrap=tk.WORD, state=tk.DISABLED)
        scrollbar = ttk.Scrollbar(log_display_area, orient=tk.VERTICAL, command=self.log_text_widget.yview)
        self.log_text_widget.configure(yscrollcommand=scrollbar.set)
        self.log_text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # ステータスバー的なもの
        self.status_bar_label = ttk.Label(main_frame, text="準備完了", anchor=tk.W)
        self.status_bar_label.pack(fill=tk.X, padx=5, pady=(5,0))


    def _update_interval_label(self, value_str):
        try:
            value = float(value_str)
            self.response_interval_label.config(text=f"{value:.1f}")
        except ValueError:
            pass


    def refresh_character_dropdown(self):
        characters = self.character_manager.get_all_characters()
        char_options = [f"{data.get('name', 'Unknown')} ({char_id})" for char_id, data in characters.items()]
        self.character_combo['values'] = char_options
        if char_options:
            current_selection = self.character_var.get()
            if current_selection in char_options:
                self.character_var.set(current_selection) # 維持
            else:
                self.character_var.set(char_options[0]) # なければ最初のもの
            self.on_character_selected() # IDも更新
        else:
            self.character_var.set("")
            self.current_character_id = ""
            if hasattr(self, 'status_bar_label'): self.status_bar_label.config(text="キャラクター未選択")
        self.log("YouTube Live: キャラクタードロップダウン更新", to_widget=False)


    def on_character_selected(self, event=None):
        selection = self.character_var.get()
        if selection and '(' in selection and ')' in selection:
            self.current_character_id = selection.split('(')[-1].replace(')', '')
            char_name = selection.split(' (')[0]
            self.log(f"YouTube Live: キャラクター '{char_name}' (ID: {self.current_character_id}) を選択。", to_widget=False)
            if hasattr(self, 'status_bar_label'): self.status_bar_label.config(text=f"キャラクター: {char_name}")
        else:
            self.current_character_id = ""
            if hasattr(self, 'status_bar_label'): self.status_bar_label.config(text="キャラクター未選択")


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
        self.start_button.config(text="配信停止")
        if hasattr(self, 'status_bar_label'): self.status_bar_label.config(text="🔴 配信中...")
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
            loop.run_until_complete(self.aituber_system_instance.run_youtube_live_loop(lambda: self.is_streaming))
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
        self.start_button.config(text="配信開始")
        if hasattr(self, 'status_bar_label'): self.status_bar_label.config(text="⚠️ 配信エラー発生")
        messagebox.showerror("配信エラー", "配信中にエラーが発生しました。詳細はログを確認してください。", parent=self.root)

    def update_ui_after_stream_stop(self):
        # 配信が正常に（または手動で）停止した後のUI更新
        self.start_button.config(text="配信開始")
        if hasattr(self, 'status_bar_label'): self.status_bar_label.config(text="準備完了")
        self.log("⏹️ AITuber配信が停止しました。")


    def stop_streaming_action(self):
        if self.is_streaming:
            self.log("⏹️ AITuber配信の停止を試みます...")
            self.is_streaming = False # これでaituber_system_instance内のループが止まるはず
            # aituber_task の終了を待つか、joinタイムアウトを設定することも検討
            # ここでは、フラグ変更でループが自然終了するのを期待
            # UIの更新は _run_streaming_loop の finally や、必要ならここでも行う
            self.start_button.config(text="配信開始")
            if hasattr(self, 'status_bar_label'): self.status_bar_label.config(text="準備完了")


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
