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

from i18n_setup import get_translator, change_language, init_i18n # init_i18n もインポート
_ = get_translator() # モジュールレベルで翻訳関数を取得

class SettingsWindow:
    def __init__(self, root: customtkinter.CTk): # 親ウィンドウもCTkであることを想定
        # サブプロセスとして起動された際に、自身のプロセス空間でi18nを初期化する
        init_i18n()
        # モジュールレベルの _ が i18n_setup のラッパーであるため、
        # init_i18n() によって内部の _translator_func が更新されれば、
        # このモジュール内の _ も新しい翻訳を参照するようになる。
        # ただし、より確実にするなら、ここで再度 _ を取得しても良いが、
        # i18n_setup.py の _ の設計が正しければ不要なはず。
        # global _ # 不要
        # _ = get_translator() # 理論上は不要だが、念のため再取得する形も検討の余地あり

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

        self.root.title(_("settings.title"))
        self.root.geometry("850x800") # サイズは一旦そのまま

        self.loading_label = customtkinter.CTkLabel(self.root, text=_("settings.loading"), font=("Yu Gothic UI", 18))
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

        tab_basic = tabview.add(_("settings.tab.basic"))
        tab_advanced = tabview.add(_("settings.tab.advanced"))

        self._create_actual_settings_content(tab_basic)
        self._create_advanced_features_content(tab_advanced)

    def _create_actual_settings_content(self, parent_tab_frame: customtkinter.CTkFrame):
        print("DEBUG: settings_window.py - _create_actual_settings_content START")
        print(f"DEBUG: Current _ function in settings_window: {repr(_)}")
        if hasattr(_, '__closure__') and _.__closure__: # ラッパー関数であればクロージャーを調べる
            for cell in _.__closure__:
                print(f"DEBUG: _ closure cell content: {repr(cell.cell_contents)}")
                if hasattr(cell.cell_contents, '__name__'):
                     print(f"DEBUG: _ closure cell content name: {cell.cell_contents.__name__}")

        import i18n # i18nモジュールを直接インポートして状態を確認
        print(f"DEBUG: i18n.get('locale') in settings_window: {i18n.get('locale')}")
        print(f"DEBUG: i18n.get('load_path') in settings_window: {i18n.get('load_path')}")
        # 実際にキーを翻訳しようとしてみる
        try:
            test_translation = _("settings.api.title") # 問題のキーで試す
            print(f"DEBUG: Test translation for 'settings.api.title' in settings_window: {test_translation}")
            if test_translation == "_settings.api.title_": # プレースホルダーが返ってきているか
                 print("WARNING: Test translation returned the key itself (placeholder)!")
            elif test_translation == "settings.api.title": # キーがそのまま返ってきているか (i18nが機能していない場合)
                 print("WARNING: Test translation returned the key itself (raw key)!")
        except Exception as e_test_trans:
            print(f"ERROR: Test translation in settings_window failed: {e_test_trans}")
        print("DEBUG: settings_window.py - Proceeding to create API settings frame...")
        # ラベルフレームの代わりにCTkFrameを使用し、内部にラベルを配置
        # API設定
        api_outer_frame = customtkinter.CTkFrame(parent_tab_frame)
        api_outer_frame.pack(fill="x", padx=10, pady=(10,5))
        customtkinter.CTkLabel(api_outer_frame, text=_("settings.api.title"), font=(self.default_font[0], self.default_font[1]+2, "bold")).pack(anchor="w", padx=10, pady=(5,0))
        api_frame = customtkinter.CTkFrame(api_outer_frame) # 内側のフレームでパディング
        api_frame.pack(fill="x", padx=10, pady=5)

        # Google AI
        customtkinter.CTkLabel(api_frame, text=_("settings.api.google_ai_key"), font=self.default_font).grid(row=0, column=0, sticky="w", pady=5, padx=5)
        self.google_ai_var = tk.StringVar()
        ai_entry = customtkinter.CTkEntry(api_frame, textvariable=self.google_ai_var, width=350, show="*", font=self.default_font)
        ai_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        customtkinter.CTkButton(api_frame, text=_("settings.button.test"), command=self.test_google_ai_studio, font=self.default_font, width=80).grid(row=0, column=2, padx=5, pady=5)

        # YouTube API
        customtkinter.CTkLabel(api_frame, text=_("settings.api.youtube_api_key"), font=self.default_font).grid(row=1, column=0, sticky="w", pady=5, padx=5)
        self.youtube_api_var = tk.StringVar()
        youtube_entry = customtkinter.CTkEntry(api_frame, textvariable=self.youtube_api_var, width=350, show="*", font=self.default_font)
        youtube_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        customtkinter.CTkButton(api_frame, text=_("settings.button.test"), command=self.test_youtube_api, font=self.default_font, width=80).grid(row=1, column=2, padx=5, pady=5)

        # Text Generation Model
        customtkinter.CTkLabel(api_frame, text=_("settings.api.text_generation_model"), font=self.default_font).grid(row=2, column=0, sticky="w", pady=5, padx=5)
        self.text_generation_model_var = tk.StringVar()
        self.text_generation_model_combo = customtkinter.CTkComboBox(
            api_frame, variable=self.text_generation_model_var,
            values=self._get_display_text_generation_models(), # 値は動的に生成されるので、翻訳は _get_display_text_generation_models 内で行う
            state="readonly", width=350, font=self.default_font,
            command=self._on_text_generation_model_changed # commandでコールバック
        )
        self.text_generation_model_combo.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        # LM Studio Endpoint (最初は非表示)
        self.local_llm_endpoint_label = customtkinter.CTkLabel(api_frame, text=_("settings.api.lm_studio_endpoint_url"), font=self.default_font)
        self.local_llm_endpoint_url_var = tk.StringVar()
        self.local_llm_endpoint_entry = customtkinter.CTkEntry(api_frame, textvariable=self.local_llm_endpoint_url_var, width=350, font=self.default_font)
        self.local_llm_endpoint_hint_label = customtkinter.CTkLabel(api_frame, text=_("settings.api.lm_studio_endpoint_hint"), font=(self.default_font[0], self.default_font[1]-2), text_color="gray")
        # .grid() と .grid_remove() は後で _on_text_generation_model_changed で制御

        api_frame.grid_columnconfigure(1, weight=1) # EntryとComboBoxが伸びるように

        # AIチャット設定
        ai_chat_outer_frame = customtkinter.CTkFrame(parent_tab_frame)
        ai_chat_outer_frame.pack(fill="x", padx=10, pady=5)
        customtkinter.CTkLabel(ai_chat_outer_frame, text=_("settings.ai_chat.title"), font=(self.default_font[0], self.default_font[1]+2, "bold")).pack(anchor="w", padx=10, pady=(5,0))
        ai_chat_frame = customtkinter.CTkFrame(ai_chat_outer_frame)
        ai_chat_frame.pack(fill="x", padx=10, pady=5)

        customtkinter.CTkLabel(ai_chat_frame, text=_("settings.ai_chat.processing_mode"), font=self.default_font).grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.ai_chat_processing_mode_var = tk.StringVar()
        self.ai_chat_processing_mode_combo = customtkinter.CTkComboBox(
            ai_chat_frame, variable=self.ai_chat_processing_mode_var,
            values=[_("settings.ai_chat.mode_sequential_display"), _("settings.ai_chat.mode_parallel_display")], # 表示名
            state="readonly", width=200, font=self.default_font
        )
        self.ai_chat_processing_mode_combo.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        customtkinter.CTkLabel(ai_chat_frame, text=_("settings.ai_chat.processing_mode_hint"), font=self.default_font).grid(row=0, column=2, sticky="w", padx=5, pady=5)


        # 音声エンジン設定
        voice_outer_frame = customtkinter.CTkFrame(parent_tab_frame)
        voice_outer_frame.pack(fill="x", padx=10, pady=5)
        customtkinter.CTkLabel(voice_outer_frame, text=_("settings.voice_engine.title"), font=(self.default_font[0], self.default_font[1]+2, "bold")).pack(anchor="w", padx=10, pady=(5,0))
        voice_frame = customtkinter.CTkFrame(voice_outer_frame)
        voice_frame.pack(fill="x", padx=10, pady=5)

        customtkinter.CTkLabel(voice_frame, text=_("settings.voice_engine.default_engine"), font=self.default_font).grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.voice_engine_var = tk.StringVar()
        engine_combo = customtkinter.CTkComboBox(voice_frame, variable=self.voice_engine_var,
                    values=["google_ai_studio_new", "avis_speech", "voicevox", "system_tts"], # 内部キー
                    state="readonly", width=200, font=self.default_font, command=self.on_system_engine_changed)
        engine_combo.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.system_engine_info = customtkinter.CTkLabel(voice_frame, text="", font=self.default_font, wraplength=300) # 動的に設定
        self.system_engine_info.grid(row=0, column=2, padx=5, pady=5, sticky="w")

        customtkinter.CTkLabel(voice_frame, text=_("settings.voice_engine.output_device"), font=self.default_font).grid(row=1, column=0, sticky="w", padx=5, pady=(10,5))
        self.audio_output_device_var = tk.StringVar()
        self.audio_output_device_combo = customtkinter.CTkComboBox(voice_frame, variable=self.audio_output_device_var,
                                                     state="readonly", width=300, font=self.default_font) # populateで設定
        self.audio_output_device_combo.grid(row=1, column=1, columnspan=2, padx=5, pady=(10,5), sticky="w")
        self.populate_audio_output_devices()

        fallback_frame_inner = customtkinter.CTkFrame(voice_frame, fg_color="transparent") # グループ化用
        fallback_frame_inner.grid(row=2, column=0, columnspan=3, sticky="w", pady=10, padx=5)
        customtkinter.CTkLabel(fallback_frame_inner, text=_("settings.voice_engine.fallback_enabled"), font=self.default_font).pack(side="left")
        self.fallback_enabled_var = tk.BooleanVar(value=True)
        customtkinter.CTkCheckBox(fallback_frame_inner, variable=self.fallback_enabled_var, text="", font=self.default_font).pack(side="left", padx=5)
        customtkinter.CTkLabel(fallback_frame_inner, text=_("settings.voice_engine.fallback_order"), font=self.default_font).pack(side="left", padx=(20,0))
        self.fallback_order_var = tk.StringVar() # loadで設定
        fallback_combo = customtkinter.CTkComboBox(fallback_frame_inner, variable=self.fallback_order_var,
                                     values=[
                                         _("settings.voice_engine.fallback_auto_display"),
                                         _("settings.voice_engine.fallback_quality_display"),
                                         _("settings.voice_engine.fallback_speed_display"),
                                         _("settings.voice_engine.fallback_cost_display")
                                     ], state="readonly", font=self.default_font, width=150)
        fallback_combo.pack(side="left", padx=5)

        # システム設定
        system_outer_frame = customtkinter.CTkFrame(parent_tab_frame)
        system_outer_frame.pack(fill="x", padx=10, pady=5)
        customtkinter.CTkLabel(system_outer_frame, text=_("settings.system.title"), font=(self.default_font[0], self.default_font[1]+2, "bold")).pack(anchor="w", padx=10, pady=(5,0))
        system_frame = customtkinter.CTkFrame(system_outer_frame)
        system_frame.pack(fill="x", padx=10, pady=5)

        self.auto_save_var = tk.BooleanVar(value=True)
        customtkinter.CTkCheckBox(system_frame, text=_("settings.system.auto_save"), variable=self.auto_save_var, font=self.default_font).grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.debug_mode_var = tk.BooleanVar()
        customtkinter.CTkCheckBox(system_frame, text=_("settings.system.debug_mode"), variable=self.debug_mode_var, font=self.default_font).grid(row=0, column=1, sticky="w", padx=20, pady=5)

        customtkinter.CTkLabel(system_frame, text=_("settings.system.conversation_history_length"), font=self.default_font).grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.conversation_history_length_var = tk.IntVar(value=0)
        history_entry = customtkinter.CTkEntry(system_frame, textvariable=self.conversation_history_length_var, width=60, font=self.default_font)
        history_entry.grid(row=1, column=1, sticky="w", padx=20, pady=5)
        customtkinter.CTkLabel(system_frame, text=_("settings.system.conversation_history_length_hint"), font=self.default_font).grid(row=1, column=2, sticky="w", padx=5, pady=5)

        # 設定保存ボタン類
        save_buttons_frame = customtkinter.CTkFrame(parent_tab_frame, fg_color="transparent")
        save_buttons_frame.pack(fill="x", padx=10, pady=20)
        customtkinter.CTkButton(save_buttons_frame, text=_("settings.button.save"), command=self.save_gui_settings, font=self.default_font).pack(side="left", padx=5)
        customtkinter.CTkButton(save_buttons_frame, text=_("settings.button.reset"), command=self.reset_gui_settings, font=self.default_font).pack(side="left", padx=5)
        customtkinter.CTkButton(save_buttons_frame, text=_("settings.button.export"), command=self.export_gui_settings, font=self.default_font).pack(side="left", padx=5)
        customtkinter.CTkButton(save_buttons_frame, text=_("settings.button.import"), command=self.import_gui_settings, font=self.default_font).pack(side="left", padx=5)

        # 言語選択ドロップダウン
        language_frame = customtkinter.CTkFrame(parent_tab_frame, fg_color="transparent")
        language_frame.pack(fill="x", padx=10, pady=(5,10), side="bottom", anchor="se") # 右下に配置
        customtkinter.CTkLabel(language_frame, text=_("settings.system.language"), font=self.default_font).pack(side="left", padx=(0,5))
        self.language_var = tk.StringVar(value=self.config.get_language()) # 現在の言語を設定
        language_combo = customtkinter.CTkComboBox(
            language_frame, variable=self.language_var,
            values=["ja", "en"], # 言語コード
            command=self.on_language_change, # 変更時のコールバック
            state="readonly", font=self.default_font, width=100
        )
        language_combo.pack(side="left")


    def _create_advanced_features_content(self, parent_tab_frame: customtkinter.CTkFrame):
        perf_outer_frame = customtkinter.CTkFrame(parent_tab_frame)
        perf_outer_frame.pack(fill="x", padx=10, pady=(10,5))
        customtkinter.CTkLabel(perf_outer_frame, text=_("settings.advanced.performance_monitoring.title"), font=(self.default_font[0], self.default_font[1]+2, "bold")).pack(anchor="w", padx=10, pady=(5,0))
        perf_frame = customtkinter.CTkFrame(perf_outer_frame)
        perf_frame.pack(fill="x", padx=10, pady=5)
        customtkinter.CTkLabel(perf_frame, text=_("settings.advanced.performance_monitoring.description"), font=self.default_font).pack(padx=5, pady=5)

        backup_outer_frame = customtkinter.CTkFrame(parent_tab_frame)
        backup_outer_frame.pack(fill="x", padx=10, pady=5)
        customtkinter.CTkLabel(backup_outer_frame, text=_("settings.advanced.backup_restore.title"), font=(self.default_font[0], self.default_font[1]+2, "bold")).pack(anchor="w", padx=10, pady=(5,0))
        backup_frame = customtkinter.CTkFrame(backup_outer_frame)
        backup_frame.pack(fill="x", padx=10, pady=5)
        backup_buttons = customtkinter.CTkFrame(backup_frame, fg_color="transparent")
        backup_buttons.pack(fill="x")
        customtkinter.CTkButton(backup_buttons, text=_("settings.advanced.backup_restore.button_backup"), command=self.create_full_backup, font=self.default_font).pack(side="left", padx=5, pady=5)
        customtkinter.CTkButton(backup_buttons, text=_("settings.advanced.backup_restore.button_restore"), command=self.restore_backup, font=self.default_font).pack(side="left", padx=5, pady=5)

        plugin_outer_frame = customtkinter.CTkFrame(parent_tab_frame)
        plugin_outer_frame.pack(fill="x", padx=10, pady=5)
        customtkinter.CTkLabel(plugin_outer_frame, text=_("settings.advanced.plugin_management.title"), font=(self.default_font[0], self.default_font[1]+2, "bold")).pack(anchor="w", padx=10, pady=(5,0))
        plugin_frame = customtkinter.CTkFrame(plugin_outer_frame)
        plugin_frame.pack(fill="x", padx=10, pady=5)
        customtkinter.CTkLabel(plugin_frame, text=_("settings.advanced.plugin_management.description"), font=self.default_font).pack(padx=5, pady=5)

    def on_language_change(self, language_code: str):
        """言語が変更されたときに呼び出されるコールバック"""
        print(f"DEBUG: on_language_change START - selected: {language_code}, current_var: {self.language_var.get() if hasattr(self, 'language_var') else 'N/A'}, current_config: {self.config.get_language()}")

        # 1. 設定ファイルに新しい言語を保存 (これが ConfigManager のインスタンス self.config を更新する)
        self.config.set_language(language_code)

        # 2. i18n ライブラリのロケールを更新
        # (i18n_setup.change_language は内部で新しいConfigManagerインスタンスを作って言語を読み直すので、
        # self.config の変更とは独立して動作するが、結果的に同じ言語が設定されるはず)
        change_language(language_code)

        # 3. ドロップダウンの表示を直接更新 (UI再構築前に)
        if hasattr(self, 'language_var'):
            self.language_var.set(language_code)
            print(f"DEBUG: on_language_change - Directly set language_var to: {language_code}")

        # 4. UI全体のテキストを再翻訳して更新
        self.update_ui_texts()

        print(f"DEBUG: on_language_change END - selected: {language_code}, current_var: {self.language_var.get() if hasattr(self, 'language_var') else 'N/A'}, current_config: {self.config.get_language()}")

    def update_ui_texts(self):
        """UI要素のテキストを現在の言語設定に基づいて更新する"""
        # ウィンドウ全体を再構築することで、すべてのテキストを更新する
        # 現在のタブの状態などを保存・復元する必要があるかもしれないが、まずはシンプルに再構築
        current_tab = None
        for widget in self.root.winfo_children():
            if isinstance(widget, customtkinter.CTkTabview):
                # CTkTabviewの場合、どのタブが選択されているかを取得する方法が標準ではない可能性がある。
                # get()メソッドで現在のタブ名を取得できる場合がある。
                try:
                    current_tab_name = widget.get() # 選択中のタブ名（翻訳前のキーではない）
                    # タブ名からインデックスやキーを逆引きするのは困難なため、
                    # ここでは単純に最初のタブに戻すか、状態保存は諦める。
                    # もしタブのインデックスを保存できるなら復元する。
                    # 簡単のため、ここではタブの状態保存は行わない。
                except Exception:
                    pass # get()がないか、エラーの場合
                widget.destroy()
                break

        # loading_labelがもし残っていれば消す（通常は_initialize_componentsで消えているはず）
        if hasattr(self, 'loading_label') and self.loading_label.winfo_exists():
            self.loading_label.pack_forget()
            self.loading_label.destroy()

        self.create_widgets() # ウィジェットを再作成
        self.load_settings_to_gui() # 設定値を再読み込みしてGUIに反映
        # もし上記でcurrent_tab_name (翻訳後のタブ名) が取得できていれば、
        # 再作成されたtabviewでその名前のタブを再度選択する (tabview.set(current_tab_name))
        # ただし、タブ名も翻訳されるため、キー基準での管理が望ましい。
        # 今回はシンプル化のため、タブ選択状態の復元は省略。

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

        # AIチャット処理方式の読み込み
        ai_chat_mode_internal = self.config.get_system_setting("ai_chat_processing_mode", "sequential")
        ai_chat_mode_display = _("settings.ai_chat.mode_sequential_display") if ai_chat_mode_internal == "sequential" else _("settings.ai_chat.mode_parallel_display")
        self.ai_chat_processing_mode_var.set(ai_chat_mode_display)

        self.on_system_engine_changed(None) # event引数なしで呼び出し
        self.populate_audio_output_devices() # この中で populate_audio_output_devices が呼ばれる

        self.auto_save_var.set(self.config.get_system_setting("auto_save", True))
        self.debug_mode_var.set(self.config.get_system_setting("debug_mode", False))
        self.conversation_history_length_var.set(self.config.get_system_setting("conversation_history_length", 0))
        self.fallback_enabled_var.set(self.config.get_system_setting("fallback_enabled", True))

        # フォールバック順序の読み込み
        fallback_order_internal = self.config.get_system_setting("fallback_order", "自動")
        fallback_order_map = {
            "自動": _("settings.voice_engine.fallback_auto_display"),
            "品質優先": _("settings.voice_engine.fallback_quality_display"),
            "速度優先": _("settings.voice_engine.fallback_speed_display"),
            "コスト優先": _("settings.voice_engine.fallback_cost_display")
        }
        self.fallback_order_var.set(fallback_order_map.get(fallback_order_internal, _("settings.voice_engine.fallback_auto_display")))

        self.log(_("settings.log.settings_loaded"))

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

            # AIチャット処理方式の保存
            selected_chat_mode_display = self.ai_chat_processing_mode_var.get()
            ai_chat_mode_internal = "sequential" if selected_chat_mode_display == _("settings.ai_chat.mode_sequential_display") else "parallel"
            self.config.set_system_setting("ai_chat_processing_mode", ai_chat_mode_internal)

            selected_audio_device_name = self.audio_output_device_var.get()
            devices = self.audio_player.get_available_output_devices()
            # デバイス名が翻訳されている可能性を考慮 (populate_audio_output_devices で翻訳済み名を設定している場合)
            # ここではデバイス名は翻訳しない想定で進めるが、もし翻訳するなら逆マッピングが必要
            selected_device_id = next((d["id"] for d in devices if d["name"] == selected_audio_device_name), "default")
            self.config.set_system_setting("audio_output_device", selected_device_id)

            self.config.set_system_setting("auto_save", self.auto_save_var.get())
            self.config.set_system_setting("debug_mode", self.debug_mode_var.get())
            try:
                history_len = int(self.conversation_history_length_var.get())
                self.config.set_system_setting("conversation_history_length", history_len)
            except (ValueError, tk.TclError):
                 self.config.set_system_setting("conversation_history_length", 0)

            self.config.set_system_setting("fallback_enabled", self.fallback_enabled_var.get())
            # フォールバック順序の保存
            selected_fallback_display = self.fallback_order_var.get()
            fallback_order_internal_map = {
                _("settings.voice_engine.fallback_auto_display"): "自動",
                _("settings.voice_engine.fallback_quality_display"): "品質優先",
                _("settings.voice_engine.fallback_speed_display"): "速度優先",
                _("settings.voice_engine.fallback_cost_display"): "コスト優先"
            }
            self.config.set_system_setting("fallback_order", fallback_order_internal_map.get(selected_fallback_display, "自動"))

            self.config.save_config()
            messagebox.showinfo(_("settings.messagebox.save_success_title"), _("settings.messagebox.save_success_message"), parent=self.root)
            self.log(_("settings.log.settings_saved"))
        except Exception as e:
            messagebox.showerror(_("settings.messagebox.save_error_title"), _("settings.messagebox.save_error_message", error=e), parent=self.root)
            self.log(_("settings.log.save_error", error=e))

    def _get_display_text_generation_models(self):
        # モデル名自体は翻訳せず、付加情報のみ翻訳する
        gemini_models = []
        for model_name in self.available_gemini_models:
            display_name = model_name
            if model_name == "gemini-2.5-flash": display_name += _("settings.model.preview_suffix")
            elif model_name == "gemini-2.5-pro": display_name += _("settings.model.preview_quota_suffix")
            gemini_models.append(display_name)
        return [_("settings.model.lm_studio_local")] + gemini_models

    def _get_internal_text_generation_model_name(self, display_name):
        if display_name == _("settings.model.lm_studio_local"): return "local_lm_studio"
        # サフィックスの比較も翻訳されたものを使う必要がある
        preview_suffix = _("settings.model.preview_suffix")
        preview_quota_suffix = _("settings.model.preview_quota_suffix")
        if display_name.endswith(preview_suffix):
            return display_name[:-len(preview_suffix)]
        if display_name.endswith(preview_quota_suffix):
            return display_name[:-len(preview_quota_suffix)]
        return display_name

    def _on_text_generation_model_changed(self, event_or_choice=None): # event引数または選択値を直接受け取れるように
        selected_model_display_name = self.text_generation_model_var.get()
        # 内部名で比較する方が堅牢
        internal_model_name = self._get_internal_text_generation_model_name(selected_model_display_name)
        if internal_model_name == "local_lm_studio":
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
            device_names = [device["name"] for device in devices] # デバイス名はそのまま使用（翻訳しない）

            # "利用可能なデバイスなし" と "デフォルト" の翻訳
            no_devices_text = _("settings.audio.no_devices_available")
            default_device_text = _("settings.audio.default_device")

            self.audio_output_device_combo.configure(values=device_names if device_names else [no_devices_text])

            saved_device_id = self.config.get_system_setting("audio_output_device", "default")

            selected_device_name = default_device_text # デフォルト値
            if saved_device_id == "default":
                # "default" が保存されている場合、表示名を翻訳された "デフォルト" にする
                # ただし、実際のデバイスリストに "デフォルト" という名前のデバイスがないか確認
                if not any(d["name"] == default_device_text for d in devices):
                     # 実際のデバイスリストに "デフォルト" がなければ、それを選択肢の先頭に追加するか、
                     # 別のロジックでデフォルトデバイスを選択する。
                     # ここでは、保存値が "default" なら表示も "デフォルト"（翻訳済）とする。
                     pass # selected_device_name は default_device_text のまま
                # もしデバイスリストに実際の "デフォルト" デバイスがあるならそちらを優先するかもしれないが、
                # 通常 "default" はシステムデフォルトを指すIDとして使われる。
            else:
                # IDでデバイスを探す
                found_device = next((d["name"] for d in devices if d["id"] == saved_device_id), None)
                if found_device:
                    selected_device_name = found_device
                elif not device_names: # デバイスがなく、保存されたIDも見つからない
                    selected_device_name = no_devices_text
                elif device_names : # 保存されたIDは見つからないが、他のデバイスはある
                     selected_device_name = device_names[0] # とりあえず最初のデバイスを選択

            self.audio_output_device_var.set(selected_device_name)

        except Exception as e:
            self.log(_("settings.log.audio_device_load_error", error=e))
            self.audio_output_device_combo.configure(values=[_("settings.audio.default_device")])
            self.audio_output_device_var.set(_("settings.audio.default_device"))

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
            messagebox.showwarning(_("settings.messagebox.api_key_not_set_title"), _("settings.messagebox.google_ai_api_key_not_set_message"), parent=self.root)
            return
        self.log(_("settings.log.google_ai_test_start"))
        test_text = _("settings.google_ai_test_text") # テスト用のテキストも国際化
        threading.Thread(target=self._run_google_ai_studio_test, args=(api_key, test_text, "alloy", 1.0), daemon=True).start()

    def _run_google_ai_studio_test(self, api_key, text_to_synthesize, voice_model_short="alloy", speed=1.0):
        self.log(_("settings.log.google_ai_synth_test_start", voice_model=voice_model_short, speed=speed, text=text_to_synthesize[:20]))
        loop = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            engine = GoogleAIStudioNewVoiceAPI()
            audio_files = loop.run_until_complete(
                engine.synthesize_speech(text_to_synthesize, voice_model_short, speed, api_key=api_key)
            )
            if audio_files:
                self.log(_("settings.log.audio_file_generation_success", files=audio_files))
                loop.run_until_complete(self.audio_player.play_audio_files(audio_files))
                self.log(_("settings.log.audio_playback_complete"))
                messagebox.showinfo(_("settings.messagebox.audio_test_success_title"), _("settings.messagebox.google_ai_audio_test_success_message", voice_model=voice_model_short), parent=self.root)
            else:
                self.log(_("settings.log.audio_file_generation_failed"))
                messagebox.showerror(_("settings.messagebox.audio_test_failed_title"), _("settings.messagebox.google_ai_audio_test_failed_message", voice_model=voice_model_short), parent=self.root)
        except Exception as e:
            self.log(_("settings.log.google_ai_synth_test_error", error=e))
            messagebox.showerror(_("settings.messagebox.test_error_title"), _("settings.messagebox.google_ai_synth_test_error_message", error=e), parent=self.root)
        finally:
            if loop: loop.close()

    def test_youtube_api(self):
        api_key = self.youtube_api_var.get()
        if not api_key:
            messagebox.showwarning(_("settings.messagebox.api_key_not_set_title"), _("settings.messagebox.youtube_api_key_not_set_message"), parent=self.root)
            return
        self.log(_("settings.log.youtube_api_test_start"))
        test_channel_id = "UC_x5XG1OV2P6uZZ5FSM9Ttw" # This ID seems fine to not translate
        url = f"https://www.googleapis.com/youtube/v3/channels?part=snippet&id={test_channel_id}&key={api_key}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            if 'items' in data and data['items']:
                channel_name = data['items'][0]['snippet']['title']
                self.log(_("settings.log.youtube_api_connection_success", channel_name=channel_name))
                messagebox.showinfo(_("settings.messagebox.youtube_api_test_success_title"), _("settings.messagebox.youtube_api_test_success_message", channel_name=channel_name), parent=self.root)
            else:
                messagebox.showwarning(_("settings.messagebox.youtube_api_test_warning_title"), _("settings.messagebox.youtube_api_test_warning_message_invalid_data"), parent=self.root)
        except requests.exceptions.HTTPError as http_err:
            messagebox.showerror(_("settings.messagebox.youtube_api_test_failed_title"), _("settings.messagebox.youtube_api_test_failed_http_error", status_code=http_err.response.status_code), parent=self.root)
        except requests.exceptions.RequestException as req_err:
            messagebox.showerror(_("settings.messagebox.youtube_api_test_failed_title"), _("settings.messagebox.youtube_api_test_failed_request_error", error=req_err), parent=self.root)
        except Exception as e:
            messagebox.showerror(_("settings.messagebox.youtube_api_test_error_title"), _("settings.messagebox.youtube_api_test_unexpected_error", error=e), parent=self.root)

    def reset_gui_settings(self):
        if messagebox.askyesno(_("settings.messagebox.reset_settings_title"), _("settings.messagebox.reset_settings_confirm_message"), parent=self.root):
            default_sys_settings = self.config.create_default_config().get("system_settings", {})
            for key, value in default_sys_settings.items():
                self.config.set_system_setting(key, value)
            self.config.save_config()
            self.update_ui_texts() # UIを更新
            self.log(_("settings.log.settings_reset"))
            messagebox.showinfo(_("settings.messagebox.reset_settings_complete_title"), _("settings.messagebox.reset_settings_complete_message"), parent=self.root)

    def export_gui_settings(self):
        try:
            settings = self.config.get_all_system_settings()
            file_path = filedialog.asksaveasfilename(
                defaultextension=".json", filetypes=[(_("settings.filedialog.json_files"), "*.json")],
                title=_("settings.filedialog.export_system_settings_title"), parent=self.root
            )
            if not file_path: return
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)
            messagebox.showinfo(_("settings.messagebox.export_complete_title"), _("settings.messagebox.export_complete_message", file_path=file_path), parent=self.root)
            self.log(_("settings.log.settings_exported", file_path=file_path))
        except Exception as e:
            messagebox.showerror(_("settings.messagebox.export_error_title"), _("settings.messagebox.export_error_message", error=e), parent=self.root)

    def import_gui_settings(self):
        file_path = filedialog.askopenfilename(
            title=_("settings.filedialog.import_system_settings_title"), filetypes=[(_("settings.filedialog.json_files"), "*.json")], parent=self.root
        )
        if not file_path: return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                settings = json.load(f)
            for key, value in settings.items():
                self.config.set_system_setting(key, value)
            self.config.save_config()
            self.update_ui_texts() # UIを更新
            messagebox.showinfo(_("settings.messagebox.import_complete_title"), _("settings.messagebox.import_complete_message", file_path=file_path), parent=self.root)
            self.log(_("settings.log.settings_imported", file_path=file_path))
        except Exception as e:
            messagebox.showerror(_("settings.messagebox.import_error_title"), _("settings.messagebox.import_error_message", error=e), parent=self.root)

    def create_full_backup(self):
        if messagebox.askyesno(_("settings.messagebox.full_backup_title"), _("settings.messagebox.full_backup_confirm_message"), parent=self.root):
            try:
                backup_data = self.config.config
                file_path = filedialog.asksaveasfilename(
                    defaultextension=".json", filetypes=[(_("settings.filedialog.json_files"), "*.json")],
                    title=_("settings.filedialog.save_full_backup_title"), parent=self.root
                )
                if not file_path: return
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(backup_data, f, ensure_ascii=False, indent=4)
                messagebox.showinfo(_("settings.messagebox.backup_complete_title"), _("settings.messagebox.backup_complete_message", file_path=file_path), parent=self.root)
                self.log(_("settings.log.full_backup_created", file_path=file_path))
            except Exception as e:
                messagebox.showerror(_("settings.messagebox.backup_error_title"), _("settings.messagebox.backup_error_message", error=e), parent=self.root)

    def restore_backup(self):
        file_path = filedialog.askopenfilename(
            title=_("settings.filedialog.select_backup_file_title"), filetypes=[(_("settings.filedialog.json_files"), "*.json")], parent=self.root
        )
        if not file_path: return
        if not messagebox.askyesno(_("settings.messagebox.restore_backup_title"), _("settings.messagebox.restore_backup_confirm_message"), parent=self.root):
            return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                backup_data = json.load(f)
            if "system_settings" in backup_data:
                 self.config.config["system_settings"] = backup_data["system_settings"]
            if "characters" in backup_data:
                 self.config.config["characters"] = backup_data["characters"]
            # ui_settings も復元対象に含めるか検討。言語設定などが変わる可能性がある。
            if "ui_settings" in backup_data:
                self.config.config["ui_settings"] = backup_data["ui_settings"]
                # 言語設定がバックアップから復元された場合、即座にUIに反映させる
                change_language(self.config.get_language()) # i18n_setupの関数を呼び出す

            self.config.save_config()
            self.update_ui_texts() # UIを更新
            self.log(_("settings.log.backup_restored"))
            messagebox.showinfo(_("settings.messagebox.restore_complete_title"), _("settings.messagebox.restore_complete_message"), parent=self.root)
        except Exception as e:
            messagebox.showerror(_("settings.messagebox.restore_error_title"), _("settings.messagebox.restore_error_message", error=e), parent=self.root)


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
