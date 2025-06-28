import customtkinter
import tkinter as tk # messagebox, filedialog, simpledialog, StringVar など基本的な型のため
from tkinter import messagebox, filedialog, simpledialog # 標準ダイアログはそのまま使用
import sys # プラットフォーム判定やフォント設定のため
import json
import os
import webbrowser
import asyncio
import requests
from pathlib import Path
from datetime import datetime # logメソッドで使用

from config import ConfigManager
from audio_manager import VoiceEngineManager, AudioPlayer, GoogleAIStudioNewVoiceAPI, AvisSpeechEngineAPI, VOICEVOXEngineAPI

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SettingsWindow:
    def __init__(self, root: customtkinter.CTk): # 親ウィンドウもCTkであることを想定
        self.root = root # CTkToplevelの親になる
        # SettingsWindow自体がメインウィンドウになる場合 (単体テストなど)
        # if not isinstance(root, customtkinter.CTk) and not isinstance(root, customtkinter.CTkToplevel):
        #     self.app_root = customtkinter.CTk()
        # else:
        #     self.app_root = root

        # このウィンドウはToplevelとして作成する想定がより自然かもしれないが、
        # launcher.py から起動される各ウィンドウは独立したプロセスでtk.Tk()をルートとしていた。
        # その構造を踏襲し、このSettingsWindowも独自のルートを持つようにする。
        # ただし、customtkinterでは通常、メインのCTkインスタンスは一つ。
        # ここでは、渡されたroot (main.pyで作成されたCTkインスタンス) の上に
        # 直接ウィジェットを配置するのではなく、もしSettingsWindowが
        # Toplevelとして開かれるべきなら、呼び出し側でCTkToplevelを作成し、
        # そのインスタンスをこのクラスのコンストラクタに渡す形になる。
        # 今回は、各ウィンドウが独自のメインループを持つ元の構造を維持しつつ、
        # customtkinter化するため、self.rootをそのまま使う。
        # launcherから呼び出されるので、self.rootは実質的に新しいCTk()インスタンスとなる。

        self.root.title("設定画面")
        self.root.geometry("850x800")

        self.loading_label = customtkinter.CTkLabel(self.root, text="読み込み中...", font=("Yu Gothic UI", 18))
        self.loading_label.pack(expand=True, fill="both")
        self.root.update_idletasks()

        self.root.after(50, self._initialize_components)

    def _initialize_components(self):
        if hasattr(self, 'loading_label') and self.loading_label.winfo_exists():
            self.loading_label.pack_forget()
            self.loading_label.destroy()

        self.config = ConfigManager()
        self.voice_manager = VoiceEngineManager()
        self.audio_player = AudioPlayer(config_manager=self.config)
        self.log_text_widget = None # オプション

        self.available_gemini_models = [
            "gemini-1.5-flash", "gemini-1.5-flash-latest",
            "gemini-1.5-pro", "gemini-1.5-pro-latest",
            "gemini-2.5-flash", "gemini-2.5-pro"
        ]
        def sort_key_gemini(model_name):
            parts = model_name.split('-')
            version_str = parts[1]
            try: version_major = float(version_str)
            except ValueError: version_major = 0
            precision_order = {"lite": 0, "flash": 1, "pro": 2}
            precision_val = precision_order.get(parts[2] if len(parts) > 2 else (parts[0] if parts[0] in precision_order else "flash"), 1)
            is_latest = "latest" in model_name
            return (version_major, precision_val, is_latest)
        self.available_gemini_models.sort(key=sort_key_gemini)

        # フォント定義 (例)
        self.default_font = ("Yu Gothic UI", 12)
        if sys.platform == "darwin": self.default_font = ("Hiragino Sans", 14)
        elif sys.platform.startswith("linux"): self.default_font = ("Noto Sans CJK JP", 12)

        self.create_widgets()
        self.load_settings_to_gui()
        # self.log("設定ウィンドウが初期化されました。") # load_settings_to_gui の最後に移動済み

    def log(self, message):
        logger.info(message)
        # SettingsWindow の log メソッドは self.log_text_widget を使用するが、
        # このウィジェットは _create_advanced_features_content の中で作成される（またはされない）。
        # 現状のコードでは log_text_widget はオプション扱いなので、
        # _initialize_components の最後でログを出すようにする。
        # ただし、load_settings_to_gui の最後にログがあるので、ここでは不要。
        if self.log_text_widget and isinstance(self.log_text_widget, customtkinter.CTkTextbox):
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_message = f"[{timestamp}] {message}\n"
            try:
                self.log_text_widget.insert("end", log_message) # tk.END -> "end"
                self.log_text_widget.see("end") # tk.END -> "end"
            except tk.TclError: # ウィンドウ破棄後など
                pass
            except AttributeError: # ウィジェットがまだない場合
                 logger.warning(f"Log widget not available for: {message}")

    def create_widgets(self):
        # ttk.Notebook -> CTkTabview
        tabview = customtkinter.CTkTabview(self.root, width=800, height=700)
        tabview.pack(fill="both", expand=True, padx=10, pady=10)

        tab_basic = tabview.add("⚙️ 基本設定")
        tab_advanced = tabview.add("🚀 高度な機能")

        self._create_actual_settings_content(tab_basic)
        self._create_advanced_features_content(tab_advanced)

    def _create_actual_settings_content(self, parent_tab_frame: customtkinter.CTkFrame):
        # ラベルフレームの代わりにCTkFrameを使用し、内部にラベルを配置
        # API設定
        api_outer_frame = customtkinter.CTkFrame(parent_tab_frame)
        api_outer_frame.pack(fill="x", padx=10, pady=(10,5))
        customtkinter.CTkLabel(api_outer_frame, text="API設定 v2.2（4エンジン完全対応）", font=(self.default_font[0], self.default_font[1]+2, "bold")).pack(anchor="w", padx=10, pady=(5,0))
        api_frame = customtkinter.CTkFrame(api_outer_frame) # 内側のフレームでパディング
        api_frame.pack(fill="x", padx=10, pady=5)

        # Google AI
        customtkinter.CTkLabel(api_frame, text="Google AI Studio APIキー:", font=self.default_font).grid(row=0, column=0, sticky="w", pady=5, padx=5)
        self.google_ai_var = tk.StringVar()
        ai_entry = customtkinter.CTkEntry(api_frame, textvariable=self.google_ai_var, width=350, show="*", font=self.default_font)
        ai_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        customtkinter.CTkButton(api_frame, text="テスト", command=self.test_google_ai_studio, font=self.default_font, width=80).grid(row=0, column=2, padx=5, pady=5)

        # YouTube API
        customtkinter.CTkLabel(api_frame, text="YouTube APIキー:", font=self.default_font).grid(row=1, column=0, sticky="w", pady=5, padx=5)
        self.youtube_api_var = tk.StringVar()
        youtube_entry = customtkinter.CTkEntry(api_frame, textvariable=self.youtube_api_var, width=350, show="*", font=self.default_font)
        youtube_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        customtkinter.CTkButton(api_frame, text="テスト", command=self.test_youtube_api, font=self.default_font, width=80).grid(row=1, column=2, padx=5, pady=5)

        # Text Generation Model
        customtkinter.CTkLabel(api_frame, text="テキスト生成モデル:", font=self.default_font).grid(row=2, column=0, sticky="w", pady=5, padx=5)
        self.text_generation_model_var = tk.StringVar()
        self.text_generation_model_combo = customtkinter.CTkComboBox(
            api_frame, variable=self.text_generation_model_var,
            values=self._get_display_text_generation_models(),
            state="readonly", width=350, font=self.default_font,
            command=self._on_text_generation_model_changed # commandでコールバック
        )
        self.text_generation_model_combo.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        # LM Studio Endpoint (最初は非表示)
        self.local_llm_endpoint_label = customtkinter.CTkLabel(api_frame, text="LM Studio エンドポイントURL:", font=self.default_font)
        self.local_llm_endpoint_url_var = tk.StringVar()
        self.local_llm_endpoint_entry = customtkinter.CTkEntry(api_frame, textvariable=self.local_llm_endpoint_url_var, width=350, font=self.default_font)
        self.local_llm_endpoint_hint_label = customtkinter.CTkLabel(api_frame, text="例: http://127.0.0.1:1234/v1/chat/completions", font=(self.default_font[0], self.default_font[1]-2), text_color="gray")
        # .grid() と .grid_remove() は後で _on_text_generation_model_changed で制御

        api_frame.grid_columnconfigure(1, weight=1) # EntryとComboBoxが伸びるように

        # AIチャット設定
        ai_chat_outer_frame = customtkinter.CTkFrame(parent_tab_frame)
        ai_chat_outer_frame.pack(fill="x", padx=10, pady=5)
        customtkinter.CTkLabel(ai_chat_outer_frame, text="AIチャット設定", font=(self.default_font[0], self.default_font[1]+2, "bold")).pack(anchor="w", padx=10, pady=(5,0))
        ai_chat_frame = customtkinter.CTkFrame(ai_chat_outer_frame)
        ai_chat_frame.pack(fill="x", padx=10, pady=5)

        customtkinter.CTkLabel(ai_chat_frame, text="AIチャット処理方式:", font=self.default_font).grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.ai_chat_processing_mode_var = tk.StringVar()
        self.ai_chat_processing_mode_combo = customtkinter.CTkComboBox(
            ai_chat_frame, variable=self.ai_chat_processing_mode_var,
            values=["sequential (推奨)", "parallel"], state="readonly", width=200, font=self.default_font
        )
        self.ai_chat_processing_mode_combo.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        customtkinter.CTkLabel(ai_chat_frame, text="sequential: ユーザー音声再生後にAI応答 / parallel: 並行処理", font=self.default_font).grid(row=0, column=2, sticky="w", padx=5, pady=5)


        # 音声エンジン設定
        voice_outer_frame = customtkinter.CTkFrame(parent_tab_frame)
        voice_outer_frame.pack(fill="x", padx=10, pady=5)
        customtkinter.CTkLabel(voice_outer_frame, text="音声エンジン設定（4エンジン完全対応）", font=(self.default_font[0], self.default_font[1]+2, "bold")).pack(anchor="w", padx=10, pady=(5,0))
        voice_frame = customtkinter.CTkFrame(voice_outer_frame)
        voice_frame.pack(fill="x", padx=10, pady=5)

        customtkinter.CTkLabel(voice_frame, text="デフォルト音声エンジン:", font=self.default_font).grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.voice_engine_var = tk.StringVar()
        engine_combo = customtkinter.CTkComboBox(voice_frame, variable=self.voice_engine_var,
                    values=["google_ai_studio_new", "avis_speech", "voicevox", "system_tts"],
                    state="readonly", width=200, font=self.default_font, command=self.on_system_engine_changed)
        engine_combo.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.system_engine_info = customtkinter.CTkLabel(voice_frame, text="", font=self.default_font, wraplength=300)
        self.system_engine_info.grid(row=0, column=2, padx=5, pady=5, sticky="w")

        customtkinter.CTkLabel(voice_frame, text="音声出力デバイス:", font=self.default_font).grid(row=1, column=0, sticky="w", padx=5, pady=(10,5))
        self.audio_output_device_var = tk.StringVar()
        self.audio_output_device_combo = customtkinter.CTkComboBox(voice_frame, variable=self.audio_output_device_var,
                                                     state="readonly", width=300, font=self.default_font)
        self.audio_output_device_combo.grid(row=1, column=1, columnspan=2, padx=5, pady=(10,5), sticky="w")
        self.populate_audio_output_devices()

        fallback_frame_inner = customtkinter.CTkFrame(voice_frame, fg_color="transparent") # グループ化用
        fallback_frame_inner.grid(row=2, column=0, columnspan=3, sticky="w", pady=10, padx=5)
        customtkinter.CTkLabel(fallback_frame_inner, text="フォールバック有効:", font=self.default_font).pack(side="left")
        self.fallback_enabled_var = tk.BooleanVar(value=True)
        customtkinter.CTkCheckBox(fallback_frame_inner, variable=self.fallback_enabled_var, text="", font=self.default_font).pack(side="left", padx=5) # text="" for CTkCheckBox
        customtkinter.CTkLabel(fallback_frame_inner, text="フォールバック順序:", font=self.default_font).pack(side="left", padx=(20,0))
        self.fallback_order_var = tk.StringVar(value="自動")
        fallback_combo = customtkinter.CTkComboBox(fallback_frame_inner, variable=self.fallback_order_var,
                                     values=["自動", "品質優先", "速度優先", "コスト優先"], state="readonly", font=self.default_font, width=150)
        fallback_combo.pack(side="left", padx=5)

        # システム設定
        system_outer_frame = customtkinter.CTkFrame(parent_tab_frame)
        system_outer_frame.pack(fill="x", padx=10, pady=5)
        customtkinter.CTkLabel(system_outer_frame, text="システム設定", font=(self.default_font[0], self.default_font[1]+2, "bold")).pack(anchor="w", padx=10, pady=(5,0))
        system_frame = customtkinter.CTkFrame(system_outer_frame)
        system_frame.pack(fill="x", padx=10, pady=5)

        self.auto_save_var = tk.BooleanVar(value=True)
        customtkinter.CTkCheckBox(system_frame, text="自動保存", variable=self.auto_save_var, font=self.default_font).grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.debug_mode_var = tk.BooleanVar()
        customtkinter.CTkCheckBox(system_frame, text="デバッグモード", variable=self.debug_mode_var, font=self.default_font).grid(row=0, column=1, sticky="w", padx=20, pady=5)

        customtkinter.CTkLabel(system_frame, text="会話履歴の長さ:", font=self.default_font).grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.conversation_history_length_var = tk.IntVar(value=0)
        # Spinboxの代替としてCTkEntryを使用し、入力制限やバリデーションは別途必要に応じて実装
        history_entry = customtkinter.CTkEntry(system_frame, textvariable=self.conversation_history_length_var, width=60, font=self.default_font)
        history_entry.grid(row=1, column=1, sticky="w", padx=20, pady=5)
        customtkinter.CTkLabel(system_frame, text="(0で履歴なし、最大100件。YouTubeライブとデバッグタブのチャットに適用)", font=self.default_font).grid(row=1, column=2, sticky="w", padx=5, pady=5)

        # 設定保存ボタン類
        save_buttons_frame = customtkinter.CTkFrame(parent_tab_frame, fg_color="transparent")
        save_buttons_frame.pack(fill="x", padx=10, pady=20)
        customtkinter.CTkButton(save_buttons_frame, text="💾 設定を保存", command=self.save_gui_settings, font=self.default_font).pack(side="left", padx=5)
        customtkinter.CTkButton(save_buttons_frame, text="🔄 設定をリセット", command=self.reset_gui_settings, font=self.default_font).pack(side="left", padx=5)
        customtkinter.CTkButton(save_buttons_frame, text="📤 設定をエクスポート", command=self.export_gui_settings, font=self.default_font).pack(side="left", padx=5)
        customtkinter.CTkButton(save_buttons_frame, text="📥 設定をインポート", command=self.import_gui_settings, font=self.default_font).pack(side="left", padx=5)


    def _create_advanced_features_content(self, parent_tab_frame: customtkinter.CTkFrame):
        perf_outer_frame = customtkinter.CTkFrame(parent_tab_frame)
        perf_outer_frame.pack(fill="x", padx=10, pady=(10,5))
        customtkinter.CTkLabel(perf_outer_frame, text="パフォーマンス監視", font=(self.default_font[0], self.default_font[1]+2, "bold")).pack(anchor="w", padx=10, pady=(5,0))
        perf_frame = customtkinter.CTkFrame(perf_outer_frame)
        perf_frame.pack(fill="x", padx=10, pady=5)
        customtkinter.CTkLabel(perf_frame, text="パフォーマンス監視機能（実装予定）", font=self.default_font).pack(padx=5, pady=5)

        backup_outer_frame = customtkinter.CTkFrame(parent_tab_frame)
        backup_outer_frame.pack(fill="x", padx=10, pady=5)
        customtkinter.CTkLabel(backup_outer_frame, text="バックアップ・復元", font=(self.default_font[0], self.default_font[1]+2, "bold")).pack(anchor="w", padx=10, pady=(5,0))
        backup_frame = customtkinter.CTkFrame(backup_outer_frame)
        backup_frame.pack(fill="x", padx=10, pady=5)
        backup_buttons = customtkinter.CTkFrame(backup_frame, fg_color="transparent")
        backup_buttons.pack(fill="x")
        customtkinter.CTkButton(backup_buttons, text="💾 完全バックアップ", command=self.create_full_backup, font=self.default_font).pack(side="left", padx=5, pady=5)
        customtkinter.CTkButton(backup_buttons, text="📥 バックアップ復元", command=self.restore_backup, font=self.default_font).pack(side="left", padx=5, pady=5)

        plugin_outer_frame = customtkinter.CTkFrame(parent_tab_frame)
        plugin_outer_frame.pack(fill="x", padx=10, pady=5)
        customtkinter.CTkLabel(plugin_outer_frame, text="プラグイン管理", font=(self.default_font[0], self.default_font[1]+2, "bold")).pack(anchor="w", padx=10, pady=(5,0))
        plugin_frame = customtkinter.CTkFrame(plugin_outer_frame)
        plugin_frame.pack(fill="x", padx=10, pady=5)
        customtkinter.CTkLabel(plugin_frame, text="プラグイン管理機能（実装予定）", font=self.default_font).pack(padx=5, pady=5)


    def load_settings_to_gui(self):
        self.google_ai_var.set(self.config.get_system_setting("google_ai_api_key", ""))
        self.youtube_api_var.set(self.config.get_system_setting("youtube_api_key", ""))
        self.voice_engine_var.set(self.config.get_system_setting("voice_engine", "google_ai_studio_new"))

        internal_model_name = self.config.get_system_setting("text_generation_model", "gemini-1.5-flash-latest")
        display_name_to_set = ""
        for dn in self._get_display_text_generation_models():
            if self._get_internal_text_generation_model_name(dn) == internal_model_name:
                display_name_to_set = dn
                break
        self.text_generation_model_var.set(display_name_to_set if display_name_to_set else self._get_display_text_generation_models()[0])
        self.local_llm_endpoint_url_var.set(self.config.get_system_setting("local_llm_endpoint_url", ""))
        self._on_text_generation_model_changed()

        ai_chat_mode = self.config.get_system_setting("ai_chat_processing_mode", "sequential")
        self.ai_chat_processing_mode_var.set("sequential (推奨)" if ai_chat_mode == "sequential" else "parallel")

        self.on_system_engine_changed(None) # event引数なしで呼び出し
        self.populate_audio_output_devices()

        self.auto_save_var.set(self.config.get_system_setting("auto_save", True))
        self.debug_mode_var.set(self.config.get_system_setting("debug_mode", False))
        self.conversation_history_length_var.set(self.config.get_system_setting("conversation_history_length", 0))
        self.fallback_enabled_var.set(self.config.get_system_setting("fallback_enabled", True))
        self.fallback_order_var.set(self.config.get_system_setting("fallback_order", "自動"))
        self.log("⚙️ 設定画面: 設定をGUIに読み込みました。")

    def save_gui_settings(self):
        try:
            self.config.set_system_setting("google_ai_api_key", self.google_ai_var.get())
            self.config.set_system_setting("youtube_api_key", self.youtube_api_var.get())
            self.config.set_system_setting("voice_engine", self.voice_engine_var.get())

            selected_display_name = self.text_generation_model_var.get()
            internal_model_name = self._get_internal_text_generation_model_name(selected_display_name)
            self.config.set_system_setting("text_generation_model", internal_model_name)
            if internal_model_name == "local_lm_studio":
                self.config.set_system_setting("local_llm_endpoint_url", self.local_llm_endpoint_url_var.get())
            else:
                self.config.set_system_setting("local_llm_endpoint_url", "")

            selected_chat_mode_display = self.ai_chat_processing_mode_var.get()
            self.config.set_system_setting("ai_chat_processing_mode", "sequential" if selected_chat_mode_display == "sequential (推奨)" else "parallel")

            selected_audio_device_name = self.audio_output_device_var.get()
            devices = self.audio_player.get_available_output_devices()
            selected_device_id = next((d["id"] for d in devices if d["name"] == selected_audio_device_name), "default")
            self.config.set_system_setting("audio_output_device", selected_device_id)

            self.config.set_system_setting("auto_save", self.auto_save_var.get())
            self.config.set_system_setting("debug_mode", self.debug_mode_var.get())
            try: # IntVarが空文字列などでエラーになる可能性への対処
                history_len = int(self.conversation_history_length_var.get())
                self.config.set_system_setting("conversation_history_length", history_len)
            except (ValueError, tk.TclError):
                 self.config.set_system_setting("conversation_history_length", 0) # エラー時は0にフォールバック

            self.config.set_system_setting("fallback_enabled", self.fallback_enabled_var.get())
            self.config.set_system_setting("fallback_order", self.fallback_order_var.get())

            self.config.save_config()
            messagebox.showinfo("設定保存", "設定を保存しました", parent=self.root)
            self.log("💾 設定画面: 設定を保存しました。")
        except Exception as e:
            messagebox.showerror("設定保存エラー", f"設定の保存に失敗しました: {e}", parent=self.root)
            self.log(f"❌ 設定画面: 設定保存エラー: {e}")

    def _get_display_text_generation_models(self):
        gemini_models = []
        for model_name in self.available_gemini_models:
            display_name = model_name
            if model_name == "gemini-2.5-flash": display_name += " (プレビュー)"
            elif model_name == "gemini-2.5-pro": display_name += " (プレビュー - クォータ注意)"
            gemini_models.append(display_name)
        return ["LM Studio (Local)"] + gemini_models

    def _get_internal_text_generation_model_name(self, display_name):
        if display_name == "LM Studio (Local)": return "local_lm_studio"
        if display_name.endswith(" (プレビュー)"): return display_name.replace(" (プレビュー)", "")
        if display_name.endswith(" (プレビュー - クォータ注意)"): return display_name.replace(" (プレビュー - クォータ注意)", "")
        return display_name

    def _on_text_generation_model_changed(self, event_or_choice=None): # event引数または選択値を直接受け取れるように
        selected_model_display_name = self.text_generation_model_var.get()
        if selected_model_display_name == "LM Studio (Local)":
            self.local_llm_endpoint_label.grid(row=3, column=0, sticky="w", pady=5, padx=5)
            self.local_llm_endpoint_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")
            self.local_llm_endpoint_hint_label.grid(row=4, column=1, sticky="w", padx=5, pady=(0,5))
        else:
            self.local_llm_endpoint_label.grid_remove()
            self.local_llm_endpoint_entry.grid_remove()
            self.local_llm_endpoint_hint_label.grid_remove()

    def populate_audio_output_devices(self):
        try:
            devices = self.audio_player.get_available_output_devices()
            device_names = [device["name"] for device in devices]
            # CTkComboBoxのvaluesを更新するには .configure(values=...) を使う
            self.audio_output_device_combo.configure(values=device_names if device_names else ["利用可能なデバイスなし"])
            saved_device_id = self.config.get_system_setting("audio_output_device", "default")
            selected_device_name = next((d["name"] for d in devices if d["id"] == saved_device_id), "デフォルト" if "デフォルト" in device_names else (device_names[0] if device_names else "利用可能なデバイスなし"))
            self.audio_output_device_var.set(selected_device_name)
        except Exception as e:
            self.log(f"❌ 音声出力デバイスの読み込みに失敗: {e}")
            self.audio_output_device_combo.configure(values=["デフォルト"])
            self.audio_output_device_var.set("デフォルト")

    def on_system_engine_changed(self, choice=None): # CTkComboBoxのcommandは選択値を渡す
        engine = self.voice_engine_var.get()
        info = self.voice_manager.get_engine_info(engine)
        if info:
            self.system_engine_info.configure(text=f"{info['description']} - {info['cost']}")
        else:
            self.system_engine_info.configure(text="エンジン情報不明")

    def test_google_ai_studio(self):
        api_key = self.google_ai_var.get()
        if not api_key:
            messagebox.showwarning("APIキー未設定", "Google AI Studio APIキーを入力してください", parent=self.root)
            return
        self.log("🧪 Google AI Studio 接続テスト開始...")
        test_text = "これはGoogle AI Studioの新しい音声合成APIのテストです。"
        threading.Thread(target=self._run_google_ai_studio_test, args=(api_key, test_text, "alloy", 1.0), daemon=True).start()

    def _run_google_ai_studio_test(self, api_key, text_to_synthesize, voice_model_short="alloy", speed=1.0):
        self.log(f"🧪 Google AI Studio 新音声合成テスト開始: Voice: {voice_model_short}, Speed: {speed}, Text: '{text_to_synthesize[:20]}...'")
        loop = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            engine = GoogleAIStudioNewVoiceAPI()
            audio_files = loop.run_until_complete(
                engine.synthesize_speech(text_to_synthesize, voice_model_short, speed, api_key=api_key)
            )
            if audio_files:
                self.log(f"✅ 音声ファイル生成成功: {audio_files}")
                loop.run_until_complete(self.audio_player.play_audio_files(audio_files))
                self.log("🎧 音声再生完了")
                messagebox.showinfo("音声テスト成功", f"Google AI Studio 新音声合成 ({voice_model_short}) のテスト再生が完了しました。", parent=self.root)
            else:
                self.log("❌ 音声ファイルの生成に失敗しました。")
                messagebox.showerror("音声テスト失敗", f"Google AI Studio 新音声合成 ({voice_model_short}) で音声ファイルの生成に失敗しました。", parent=self.root)
        except Exception as e:
            self.log(f"❌ Google AI Studio 新音声合成テスト中にエラー: {e}")
            messagebox.showerror("テストエラー", f"Google AI Studio 新音声合成テスト中にエラー: {e}", parent=self.root)
        finally:
            if loop: loop.close()

    def test_youtube_api(self):
        api_key = self.youtube_api_var.get()
        if not api_key:
            messagebox.showwarning("APIキー未設定", "YouTube APIキーを入力してください", parent=self.root)
            return
        self.log("🧪 YouTube API 接続テスト開始...")
        test_channel_id = "UC_x5XG1OV2P6uZZ5FSM9Ttw"
        url = f"https://www.googleapis.com/youtube/v3/channels?part=snippet&id={test_channel_id}&key={api_key}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            if 'items' in data and data['items']:
                channel_name = data['items'][0]['snippet']['title']
                self.log(f"✅ YouTube API 接続成功。テストチャンネル名: {channel_name}")
                messagebox.showinfo("YouTube APIテスト成功", f"接続成功。チャンネル名: {channel_name}", parent=self.root)
            else:
                messagebox.showwarning("YouTube APIテスト警告", "接続成功しましたがデータ形式が不正です。", parent=self.root)
        except requests.exceptions.HTTPError as http_err:
            messagebox.showerror("YouTube APIテスト失敗", f"HTTPエラー: {http_err.response.status_code}", parent=self.root)
        except requests.exceptions.RequestException as req_err:
            messagebox.showerror("YouTube APIテスト失敗", f"リクエストエラー: {req_err}", parent=self.root)
        except Exception as e:
            messagebox.showerror("YouTube APIテストエラー", f"予期せぬエラー: {e}", parent=self.root)

    def reset_gui_settings(self):
        if messagebox.askyesno("設定リセット", "本当にシステム設定を初期状態にリセットしますか？", parent=self.root):
            default_sys_settings = self.config.create_default_config().get("system_settings", {})
            for key, value in default_sys_settings.items():
                self.config.set_system_setting(key, value)
            self.config.save_config()
            self.load_settings_to_gui()
            self.log("🔄 設定画面: システム設定を初期状態にリセットしました。")
            messagebox.showinfo("設定リセット完了", "システム設定が初期状態にリセットされました。", parent=self.root)

    def export_gui_settings(self):
        try:
            settings = self.config.get_all_system_settings()
            file_path = filedialog.asksaveasfilename(
                defaultextension=".json", filetypes=[("JSONファイル", "*.json")],
                title="システム設定を保存", parent=self.root
            )
            if not file_path: return
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)
            messagebox.showinfo("保存完了", f"システム設定を '{file_path}' に保存しました", parent=self.root)
            self.log(f"📤 設定画面: システム設定をエクスポートしました: {file_path}")
        except Exception as e:
            messagebox.showerror("エクスポートエラー", f"システム設定のエクスポートに失敗: {e}", parent=self.root)

    def import_gui_settings(self):
        file_path = filedialog.askopenfilename(
            title="システム設定JSONファイルを選択", filetypes=[("JSONファイル", "*.json")], parent=self.root
        )
        if not file_path: return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                settings = json.load(f)
            for key, value in settings.items():
                self.config.set_system_setting(key, value)
            self.config.save_config()
            self.load_settings_to_gui()
            messagebox.showinfo("インポート完了", f"システム設定を '{file_path}' からインポートしました", parent=self.root)
            self.log(f"📥 設定画面: システム設定をインポートしました: {file_path}")
        except Exception as e:
            messagebox.showerror("インポートエラー", f"システム設定のインポートに失敗: {e}", parent=self.root)

    def create_full_backup(self):
        if messagebox.askyesno("完全バックアップ", "設定ファイル全体とキャラクターデータをバックアップしますか？", parent=self.root):
            try:
                backup_data = self.config.config
                file_path = filedialog.asksaveasfilename(
                    defaultextension=".json", filetypes=[("JSONファイル", "*.json")],
                    title="完全バックアップを保存", parent=self.root
                )
                if not file_path: return
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(backup_data, f, ensure_ascii=False, indent=4)
                messagebox.showinfo("バックアップ完了", f"完全バックアップを '{file_path}' に保存しました", parent=self.root)
                self.log(f"📦 設定画面: 完全バックアップを作成しました: {file_path}")
            except Exception as e:
                messagebox.showerror("バックアップエラー", f"完全バックアップに失敗: {e}", parent=self.root)

    def restore_backup(self):
        file_path = filedialog.askopenfilename(
            title="バックアップJSONファイルを選択", filetypes=[("JSONファイル", "*.json")], parent=self.root
        )
        if not file_path: return
        if not messagebox.askyesno("バックアップ復元", "本当にバックアップから設定を復元しますか？\n現在の設定は上書きされます。", parent=self.root):
            return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                backup_data = json.load(f)
            if "system_settings" in backup_data:
                 self.config.config["system_settings"] = backup_data["system_settings"]
            if "characters" in backup_data:
                 self.config.config["characters"] = backup_data["characters"]
            self.config.save_config()
            self.load_settings_to_gui()
            self.log("🔄 設定画面: バックアップを復元しました。")
            messagebox.showinfo("復元完了", "バックアップを復元しました。", parent=self.root)
        except Exception as e:
            messagebox.showerror("復元エラー", f"バックアップの復元に失敗: {e}", parent=self.root)


def main():
    # このファイルが直接実行された場合の処理 (テスト用)
    # main.py側で設定されることを期待するが、単体テスト用にここにも記述しておく
    customtkinter.set_appearance_mode("System") # or "Light", "Dark"
    customtkinter.set_default_color_theme("blue") # or "green", "dark-blue"

    app_root = customtkinter.CTk() # SettingsWindow のためのルートウィンドウ
    app = SettingsWindow(app_root)
    app_root.mainloop()

if __name__ == "__main__":
    # launcher.py から起動されることを想定しているため、
    # このファイルが直接実行された場合は、customtkinterの初期設定を行う。
    customtkinter.set_appearance_mode("System")
    customtkinter.set_default_color_theme("blue")

    # SettingsWindowは通常、他のウィンドウから呼び出されるか、
    # もしくはメインアプリケーションの一部として組み込まれる。
    # 単体で実行する場合、独自のCTkルートを持つ。
    root = customtkinter.CTk()
    app = SettingsWindow(root)
    root.mainloop()
