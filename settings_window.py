import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import json
import os
import webbrowser
import asyncio # _run_google_ai_studio_test, test_avis_speech, _run_avis_speech_test, test_voicevox, _run_voicevox_test で必要
import requests # test_youtube_api で必要
from pathlib import Path # create_full_backup で必要 (ただし、AITuberMainGUIクラスのメソッドなので、移植時に検討)

# 外部依存クラス (実際のプロジェクトでは適切にimport)
from config import ConfigManager
from audio_manager import VoiceEngineManager, AudioPlayer, GoogleAIStudioNewVoiceAPI, AvisSpeechEngineAPI, VOICEVOXEngineAPI
# from character_manager import CharacterManager # settings_window.py単体では直接使わないが、関連機能で必要になる可能性あり

# loggingについては、このファイル単体で動作させる場合に設定
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SettingsWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("設定画面")
        self.root.geometry("800x750") # 少し大きめに

        # --- AITuberMainGUIからの移植・模倣 ---
        self.config = ConfigManager()
        self.voice_manager = VoiceEngineManager() # test_google_ai_studio などで使用
        self.audio_player = AudioPlayer(config_manager=self.config) # populate_audio_output_devices などで使用
        # self.character_manager = CharacterManager(self.config) # 必要に応じて

        # ログ出力用 (AITuberMainGUIのlogメソッドを模倣)
        self.log_text_widget = None # あとで Text ウィジェットを割り当てる (オプション)

        # Geminiモデルリスト (AITuberMainGUIからコピー)
        self.available_gemini_models = [
            "gemini-1.5-flash", "gemini-1.5-flash-latest",
            "gemini-1.5-pro", "gemini-1.5-pro-latest",
            "gemini-2.5-flash", "gemini-2.5-pro"
        ]
        def sort_key_gemini(model_name):
            parts = model_name.split('-')
            version_str = parts[1]
            try:
                version_major = float(version_str)
            except ValueError: version_major = 0
            precision_order = {"lite": 0, "flash": 1, "pro": 2}
            precision_val = precision_order.get(parts[2] if len(parts) > 2 else (parts[0] if parts[0] in precision_order else "flash"), 1)
            is_latest = "latest" in model_name
            return (version_major, precision_val, is_latest)
        self.available_gemini_models.sort(key=sort_key_gemini)
        # --- ここまで AITuberMainGUIからの移植・模倣 ---

        self.create_widgets()
        self.load_settings_to_gui()

    def log(self, message):
        # print(f"LOG: {message}") # コンソールへの簡易ログ
        logger.info(message)
        if self.log_text_widget: # オプションのログ表示ウィジェットがあれば更新
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_message = f"[{timestamp}] {message}\n"
            self.log_text_widget.insert(tk.END, log_message)
            self.log_text_widget.see(tk.END)

    def create_widgets(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 「設定」タブ部分 (旧 create_settings_tab からエンジン起動ガイド部を除く)
        settings_tab_frame = ttk.Frame(notebook)
        notebook.add(settings_tab_frame, text="⚙️ 基本設定")
        self._create_actual_settings_content(settings_tab_frame) # メソッド化

        # 「高度な機能」タブ部分 (旧 create_advanced_tab から)
        advanced_tab_frame = ttk.Frame(notebook)
        notebook.add(advanced_tab_frame, text="🚀 高度な機能")
        self._create_advanced_features_content(advanced_tab_frame) # メソッド化

    def _create_actual_settings_content(self, parent_frame):
        # API設定
        api_frame = ttk.LabelFrame(parent_frame, text="API設定 v2.2（4エンジン完全対応）", padding="10")
        api_frame.pack(fill=tk.X, padx=10, pady=5)
        api_grid = ttk.Frame(api_frame)
        api_grid.pack(fill=tk.X)

        ttk.Label(api_grid, text="Google AI Studio APIキー（文章生成＋新音声合成）:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.google_ai_var = tk.StringVar()
        ai_entry = ttk.Entry(api_grid, textvariable=self.google_ai_var, width=50, show="*")
        ai_entry.grid(row=0, column=1, padx=10, pady=2)
        ttk.Button(api_grid, text="テスト", command=self.test_google_ai_studio).grid(row=0, column=2, padx=5)

        ttk.Label(api_grid, text="YouTube APIキー（配信用）:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.youtube_api_var = tk.StringVar()
        youtube_entry = ttk.Entry(api_grid, textvariable=self.youtube_api_var, width=50, show="*")
        youtube_entry.grid(row=1, column=1, padx=10, pady=2)
        ttk.Button(api_grid, text="テスト", command=self.test_youtube_api).grid(row=1, column=2, padx=5)

        ttk.Label(api_grid, text="テキスト生成モデル (Gemini/Local):").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.text_generation_model_var = tk.StringVar()
        self.text_generation_model_combo = ttk.Combobox(
            api_grid, textvariable=self.text_generation_model_var,
            values=self._get_display_text_generation_models(),
            state="readonly", width=47
        )
        self.text_generation_model_combo.grid(row=2, column=1, padx=10, pady=2, sticky=tk.W)
        self.text_generation_model_combo.bind('<<ComboboxSelected>>', self._on_text_generation_model_changed)

        self.local_llm_endpoint_label = ttk.Label(api_grid, text="LM Studio エンドポイントURL:")
        self.local_llm_endpoint_label.grid(row=3, column=0, sticky=tk.W, pady=2)
        self.local_llm_endpoint_label.grid_remove()
        self.local_llm_endpoint_url_var = tk.StringVar()
        self.local_llm_endpoint_entry = ttk.Entry(api_grid, textvariable=self.local_llm_endpoint_url_var, width=50)
        self.local_llm_endpoint_entry.grid(row=3, column=1, padx=10, pady=2, sticky=tk.W)
        self.local_llm_endpoint_entry.grid_remove()
        self.local_llm_endpoint_hint_label = ttk.Label(api_grid, text="例: http://127.0.0.1:1234/v1/chat/completions", foreground="gray")
        self.local_llm_endpoint_hint_label.grid(row=4, column=1, sticky=tk.W, padx=10, pady=(0,5))
        self.local_llm_endpoint_hint_label.grid_remove()


        # AIチャット設定
        ai_chat_settings_frame = ttk.LabelFrame(parent_frame, text="AIチャット設定", padding="10")
        ai_chat_settings_frame.pack(fill=tk.X, padx=10, pady=5)
        ai_chat_grid = ttk.Frame(ai_chat_settings_frame)
        ai_chat_grid.pack(fill=tk.X)
        ttk.Label(ai_chat_grid, text="AIチャット処理方式:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.ai_chat_processing_mode_var = tk.StringVar()
        self.ai_chat_processing_mode_combo = ttk.Combobox(
            ai_chat_grid, textvariable=self.ai_chat_processing_mode_var,
            values=["sequential (推奨)", "parallel"], state="readonly", width=25
        )
        self.ai_chat_processing_mode_combo.grid(row=0, column=1, padx=10, pady=2, sticky=tk.W)
        ttk.Label(ai_chat_grid, text="sequential: ユーザー音声再生後にAI応答 / parallel: 並行処理").grid(row=0, column=2, sticky=tk.W, padx=5)


        # 音声エンジン設定
        voice_frame = ttk.LabelFrame(parent_frame, text="音声エンジン設定（4エンジン完全対応）", padding="10")
        voice_frame.pack(fill=tk.X, padx=10, pady=5)
        voice_grid = ttk.Frame(voice_frame)
        voice_grid.pack(fill=tk.X)

        ttk.Label(voice_grid, text="デフォルト音声エンジン:").grid(row=0, column=0, sticky=tk.W)
        self.voice_engine_var = tk.StringVar()
        engine_combo = ttk.Combobox(voice_grid, textvariable=self.voice_engine_var,
                    values=["google_ai_studio_new", "avis_speech", "voicevox", "system_tts"],
                    state="readonly", width=25)
        engine_combo.grid(row=0, column=1, padx=10)
        engine_combo.bind('<<ComboboxSelected>>', self.on_system_engine_changed)
        self.system_engine_info = ttk.Label(voice_grid, text="", foreground="gray", wraplength=300)
        self.system_engine_info.grid(row=0, column=2, padx=10, sticky=tk.W)

        ttk.Label(voice_grid, text="音声出力デバイス:").grid(row=1, column=0, sticky=tk.W, pady=(10,0))
        self.audio_output_device_var = tk.StringVar()
        self.audio_output_device_combo = ttk.Combobox(voice_grid, textvariable=self.audio_output_device_var,
                                                     state="readonly", width=40)
        self.audio_output_device_combo.grid(row=1, column=1, columnspan=2, padx=10, pady=(10,0), sticky=tk.W)
        self.populate_audio_output_devices()

        fallback_frame = ttk.Frame(voice_grid)
        fallback_frame.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=10)
        ttk.Label(fallback_frame, text="フォールバック有効:").pack(side=tk.LEFT)
        self.fallback_enabled_var = tk.BooleanVar(value=True) # configから読み込むべき
        ttk.Checkbutton(fallback_frame, variable=self.fallback_enabled_var).pack(side=tk.LEFT, padx=5)
        ttk.Label(fallback_frame, text="フォールバック順序:").pack(side=tk.LEFT, padx=(20,0))
        self.fallback_order_var = tk.StringVar(value="自動") # configから読み込むべき
        fallback_combo = ttk.Combobox(fallback_frame, textvariable=self.fallback_order_var,
                                     values=["自動", "品質優先", "速度優先", "コスト優先"], state="readonly")
        fallback_combo.pack(side=tk.LEFT, padx=5)


        # システム設定
        system_frame = ttk.LabelFrame(parent_frame, text="システム設定", padding="10")
        system_frame.pack(fill=tk.X, padx=10, pady=5)
        system_grid = ttk.Frame(system_frame)
        system_grid.pack(fill=tk.X)

        self.auto_save_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(system_grid, text="自動保存", variable=self.auto_save_var).grid(row=0, column=0, sticky=tk.W)
        self.debug_mode_var = tk.BooleanVar()
        ttk.Checkbutton(system_grid, text="デバッグモード", variable=self.debug_mode_var).grid(row=0, column=1, sticky=tk.W, padx=20)
        ttk.Label(system_grid, text="会話履歴の長さ:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.conversation_history_length_var = tk.IntVar(value=0)
        history_spinbox = ttk.Spinbox(system_grid, from_=0, to=100, increment=1,
                                      textvariable=self.conversation_history_length_var, width=5)
        history_spinbox.grid(row=1, column=1, sticky=tk.W, padx=20, pady=5)
        ttk.Label(system_grid, text="(0で履歴なし、最大100件。YouTubeライブとデバッグタブのチャットに適用)").grid(row=1, column=2, sticky=tk.W, pady=5, padx=5)


        # 設定保存ボタン類
        save_buttons_frame = ttk.Frame(parent_frame) # parent_frameに直接配置
        save_buttons_frame.pack(fill=tk.X, padx=10, pady=20)
        ttk.Button(save_buttons_frame, text="💾 設定を保存", command=self.save_gui_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(save_buttons_frame, text="🔄 設定をリセット", command=self.reset_gui_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(save_buttons_frame, text="📤 設定をエクスポート", command=self.export_gui_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(save_buttons_frame, text="📥 設定をインポート", command=self.import_gui_settings).pack(side=tk.LEFT, padx=5)


    def _create_advanced_features_content(self, parent_frame):
        # パフォーマンス監視 (gui.pyでは未実装だったのでラベルのみ)
        perf_frame = ttk.LabelFrame(parent_frame, text="パフォーマンス監視", padding="10")
        perf_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(perf_frame, text="パフォーマンス監視機能（実装予定）").pack()

        # バックアップ・復元
        backup_frame = ttk.LabelFrame(parent_frame, text="バックアップ・復元", padding="10")
        backup_frame.pack(fill=tk.X, padx=10, pady=5)
        backup_buttons = ttk.Frame(backup_frame)
        backup_buttons.pack(fill=tk.X)
        ttk.Button(backup_buttons, text="💾 完全バックアップ", command=self.create_full_backup).pack(side=tk.LEFT, padx=5)
        ttk.Button(backup_buttons, text="📥 バックアップ復元", command=self.restore_backup).pack(side=tk.LEFT, padx=5)
        # ttk.Button(backup_buttons, text="🗂️ バックアップ管理", command=self.manage_backups).pack(side=tk.LEFT, padx=5) # manage_backupsはダイアログなので、ここでは不要かも

        # プラグイン管理 (gui.pyでは未実装だったのでラベルのみ)
        plugin_frame = ttk.LabelFrame(parent_frame, text="プラグイン管理", padding="10")
        plugin_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(plugin_frame, text="プラグイン管理機能（実装予定）").pack()


    # --- 以下、AITuberMainGUIから移植・改変するメソッド群 ---

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
        self._on_text_generation_model_changed() # 表示制御

        ai_chat_mode = self.config.get_system_setting("ai_chat_processing_mode", "sequential")
        self.ai_chat_processing_mode_var.set("sequential (推奨)" if ai_chat_mode == "sequential" else "parallel")

        self.on_system_engine_changed() # エンジン情報表示更新
        self.populate_audio_output_devices() # これで var も設定されるはず
        # populate_audio_output_devices内でconfigへの保存は不要、load時は読み込むだけ

        self.auto_save_var.set(self.config.get_system_setting("auto_save", True))
        self.debug_mode_var.set(self.config.get_system_setting("debug_mode", False))
        self.conversation_history_length_var.set(self.config.get_system_setting("conversation_history_length", 0))
        # フォールバック設定の読み込み
        self.fallback_enabled_var.set(self.config.get_system_setting("fallback_enabled", True)) # 仮のキー名
        self.fallback_order_var.set(self.config.get_system_setting("fallback_order", "自動")) # 仮のキー名

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
            self.config.set_system_setting("conversation_history_length", self.conversation_history_length_var.get())
            # フォールバック設定の保存
            self.config.set_system_setting("fallback_enabled", self.fallback_enabled_var.get()) # 仮のキー名
            self.config.set_system_setting("fallback_order", self.fallback_order_var.get()) # 仮のキー名


            self.config.save_config() # 明示的に保存
            messagebox.showinfo("設定保存", "設定を保存しました", parent=self.root)
            self.log("💾 設定画面: 設定を保存しました。")
        except Exception as e:
            messagebox.showerror("設定保存エラー", f"設定の保存に失敗しました: {e}", parent=self.root)
            self.log(f"❌ 設定画面: 設定保存エラー: {e}")

    def _get_display_text_generation_models(self):
        # AITuberMainGUIからコピー
        gemini_models = []
        for model_name in self.available_gemini_models:
            display_name = model_name
            if model_name == "gemini-2.5-flash": display_name += " (プレビュー)"
            elif model_name == "gemini-2.5-pro": display_name += " (プレビュー - クォータ注意)"
            gemini_models.append(display_name)
        return ["LM Studio (Local)"] + gemini_models

    def _get_internal_text_generation_model_name(self, display_name):
        # AITuberMainGUIからコピー
        if display_name == "LM Studio (Local)": return "local_lm_studio"
        if display_name.endswith(" (プレビュー)"): return display_name.replace(" (プレビュー)", "")
        if display_name.endswith(" (プレビュー - クォータ注意)"): return display_name.replace(" (プレビュー - クォータ注意)", "")
        return display_name

    def _on_text_generation_model_changed(self, event=None):
        # AITuberMainGUIからコピー
        selected_model_display_name = self.text_generation_model_var.get()
        if selected_model_display_name == "LM Studio (Local)":
            self.local_llm_endpoint_label.grid()
            self.local_llm_endpoint_entry.grid()
            self.local_llm_endpoint_hint_label.grid()
        else:
            self.local_llm_endpoint_label.grid_remove()
            self.local_llm_endpoint_entry.grid_remove()
            self.local_llm_endpoint_hint_label.grid_remove()

    def populate_audio_output_devices(self):
        # AITuberMainGUIからコピー
        try:
            devices = self.audio_player.get_available_output_devices()
            device_names = [device["name"] for device in devices]
            self.audio_output_device_combo['values'] = device_names
            saved_device_id = self.config.get_system_setting("audio_output_device", "default")
            selected_device_name = next((d["name"] for d in devices if d["id"] == saved_device_id), "デフォルト" if "デフォルト" in device_names else (device_names[0] if device_names else ""))
            self.audio_output_device_var.set(selected_device_name)
        except Exception as e:
            self.log(f"❌ 音声出力デバイスの読み込みに失敗: {e}")
            self.audio_output_device_combo['values'] = ["デフォルト"]
            self.audio_output_device_var.set("デフォルト")


    def on_system_engine_changed(self, event=None):
        # AITuberMainGUIからコピー
        engine = self.voice_engine_var.get()
        info = self.voice_manager.get_engine_info(engine)
        if info:
            self.system_engine_info.config(text=f"{info['description']} - {info['cost']}")
        else:
            self.system_engine_info.config(text="エンジン情報不明")


    def test_google_ai_studio(self):
        # AITuberMainGUIのものをベースに、このウィンドウ用に調整
        api_key = self.google_ai_var.get()
        if not api_key:
            messagebox.showwarning("APIキー未設定", "Google AI Studio APIキーを入力してください", parent=self.root)
            return
        self.log("🧪 Google AI Studio 接続テスト開始...")
        # Google AI Studioの新音声合成テストを実行
        test_text = "これはGoogle AI Studioの新しい音声合成APIのテストです。"
        # voice_model はSDKで利用する正しい形式を指定する。短い名前でも可のはず。
        threading.Thread(target=self._run_google_ai_studio_test, args=(api_key, test_text, "alloy", 1.0), daemon=True).start()


    def _run_google_ai_studio_test(self, api_key, text_to_synthesize, voice_model_short="alloy", speed=1.0):
        # AITuberMainGUIのものをベースに、APIキーを引数で受け取る
        self.log(f"🧪 Google AI Studio 新音声合成テスト開始: Voice: {voice_model_short}, Speed: {speed}, Text: '{text_to_synthesize[:20]}...'")
        loop = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            engine = GoogleAIStudioNewVoiceAPI() # インスタンス生成
            # voice_model はSDKが期待するフルネームである必要があるかもしれないので、短い名前からフルネームに変換
            # もしSDKが短い名前を直接受け付けるならこの変換は不要
            full_voice_model_name = f"models/gemini-2.5-flash-preview-tts-{voice_model_short.lower()}" # 仮
            # GoogleAIStudioNewVoiceAPIのget_available_voices()が返す短い名前をそのまま使えるようにAPI側を改修した方が良い。
            # ここでは、voice_model_short をそのまま渡してみる（API側が対応している前提）
            audio_files = loop.run_until_complete(
                engine.synthesize_speech(text_to_synthesize, voice_model_short, speed, api_key=api_key)
            )
            if audio_files:
                self.log(f"✅ 音声ファイル生成成功: {audio_files}")
                # audio_player は self.audio_player を使う
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
        # AITuberMainGUIからコピーし、parent=self.root を追加
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
                self.config.set_system_setting(key, value) # これで個別に保存される(auto_save=Trueの場合)
            self.config.save_config() # 明示的に全体を保存
            self.load_settings_to_gui() # GUIに再読み込み
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
            # 読み込んだ設定をConfigManager経由で適用
            for key, value in settings.items():
                self.config.set_system_setting(key, value) # これで個別に保存される(auto_save=Trueの場合)
            self.config.save_config() # 明示的に全体を保存
            self.load_settings_to_gui() # GUIに再読み込み
            messagebox.showinfo("インポート完了", f"システム設定を '{file_path}' からインポートしました", parent=self.root)
            self.log(f"📥 設定画面: システム設定をインポートしました: {file_path}")
        except Exception as e:
            messagebox.showerror("インポートエラー", f"システム設定のインポートに失敗: {e}", parent=self.root)

    def create_full_backup(self):
        # AITuberMainGUIから移植。CharacterManagerとVoiceManagerのデータもバックアップに含めるかは要検討。
        # このウィンドウ単体ではそれらのデータは直接持っていない。ConfigManagerが持つキャラクターデータは対象。
        if messagebox.askyesno("完全バックアップ", "設定ファイル全体とキャラクターデータをバックアップしますか？", parent=self.root):
            try:
                # ConfigManagerが持つ全設定（システム設定＋キャラクター設定）をバックアップ
                backup_data = self.config.config # ConfigManagerの内部辞書全体

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

            # ConfigManagerの内部データを直接置き換えるか、キーごとに設定するか。
            # ここでは、ConfigManagerに全データをロードさせる機能があればそれを使う。なければキーごと。
            # ConfigManager.load_config() はファイルパスから読むので、ここでは辞書を直接設定する。
            if "system_settings" in backup_data:
                 self.config.config["system_settings"] = backup_data["system_settings"]
            if "characters" in backup_data:
                 self.config.config["characters"] = backup_data["characters"]
            # 他のトップレベルキーも同様に復元
            # ...

            self.config.save_config() # 変更を保存
            self.load_settings_to_gui() # GUIに再読み込み
            self.log("🔄 設定画面: バックアップを復元しました。")
            messagebox.showinfo("復元完了", "バックアップを復元しました。", parent=self.root)
        except Exception as e:
            messagebox.showerror("復元エラー", f"バックアップの復元に失敗: {e}", parent=self.root)


def main():
    root = tk.Tk()
    app = SettingsWindow(root)
    root.mainloop()

if __name__ == "__main__":
    main()
