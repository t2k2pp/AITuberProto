import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import json
import os
import uuid
from datetime import datetime
import asyncio # CharacterEditDialog内のテスト音声再生等で必要
import threading # CharacterEditDialog内のテスト音声再生等で必要
import time # CharacterEditDialog内のエンジン比較テストで必要

# 外部依存クラス (実際のプロジェクトでは適切にimport)
from config import ConfigManager
from character_manager import CharacterManager # 本体
from audio_manager import VoiceEngineManager, AudioPlayer, GoogleAIStudioNewVoiceAPI, AvisSpeechEngineAPI, VOICEVOXEngineAPI, SystemTTSAPI # CharacterEditDialogで直接利用

# loggingについては、このファイル単体で動作させる場合に設定
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# --- CharacterEditDialogクラス (gui.pyから移植・調整) ---
class CharacterEditDialog:
    def __init__(self, parent, character_manager, char_id=None, char_data=None, config_manager=None): # config_manager を追加
        self.parent = parent # メインウィンドウを保持
        self.character_manager = character_manager
        self.char_id = char_id
        self.char_data = char_data
        self.result = None
        self.is_edit_mode = char_id is not None
        self.config_manager = config_manager # ConfigManagerのインスタンスを保持

        self.dialog = tk.Toplevel(parent)
        title = "キャラクター編集" if self.is_edit_mode else "キャラクター作成"
        self.dialog.title(title + " - 4エンジン対応版")
        self.dialog.geometry("650x800")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.create_widgets()

        if self.is_edit_mode and self.char_data:
            self.load_existing_data()

        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (650 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (800 // 2)
        self.dialog.geometry(f"650x800+{x}+{y}")
        self.dialog.wait_window()

    def create_widgets(self):
        # キャラクター名
        ttk.Label(self.dialog, text="キャラクター名:").pack(anchor=tk.W, padx=10, pady=5)
        self.name_var = tk.StringVar()
        ttk.Entry(self.dialog, textvariable=self.name_var, width=40).pack(padx=10, pady=5)

        if not self.is_edit_mode:
            template_frame = ttk.LabelFrame(self.dialog, text="テンプレート選択（4エンジン対応）", padding="10")
            template_frame.pack(fill=tk.X, padx=10, pady=10)
            self.template_var = tk.StringVar(value="最新AI系")
            templates = ["最新AI系", "元気系", "知的系", "癒し系", "ずんだもん系", "キャラクター系", "プロ品質系", "多言語対応系", "カスタム"]
            template_grid = ttk.Frame(template_frame)
            template_grid.pack(fill=tk.X)
            for i, template in enumerate(templates):
                row, col = divmod(i, 2)
                rb = ttk.Radiobutton(template_grid, text=template, variable=self.template_var, value=template, command=self.on_template_changed)
                rb.grid(row=row, column=col, sticky=tk.W, padx=10)

        personality_frame = ttk.LabelFrame(self.dialog, text="性格設定（詳細）", padding="10")
        personality_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(personality_frame, text="基本的な性格:").pack(anchor=tk.W)
        self.base_tone_var = tk.StringVar()
        ttk.Entry(personality_frame, textvariable=self.base_tone_var, width=60).pack(fill=tk.X, pady=2)
        ttk.Label(personality_frame, text="話し方・口調:").pack(anchor=tk.W, pady=(10,0))
        self.speech_style_var = tk.StringVar()
        ttk.Entry(personality_frame, textvariable=self.speech_style_var, width=60).pack(fill=tk.X, pady=2)
        ttk.Label(personality_frame, text="キャラクターの特徴 (1行1項目):").pack(anchor=tk.W, pady=(10,0))
        self.traits_text = tk.Text(personality_frame, height=4, width=60)
        self.traits_text.pack(fill=tk.X, pady=2)
        ttk.Label(personality_frame, text="好きな話題 (1行1項目):").pack(anchor=tk.W, pady=(10,0))
        self.topics_text = tk.Text(personality_frame, height=4, width=60)
        self.topics_text.pack(fill=tk.X, pady=2)

        voice_frame = ttk.LabelFrame(self.dialog, text="音声設定（4エンジン完全対応）", padding="10")
        voice_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(voice_frame, text="音声エンジン:").pack(anchor=tk.W)
        self.voice_engine_var = tk.StringVar(value="google_ai_studio_new")
        engine_combo = ttk.Combobox(voice_frame, textvariable=self.voice_engine_var,
                                   values=["google_ai_studio_new", "avis_speech", "voicevox", "system_tts"],
                                   state="readonly", width=50)
        engine_combo.pack(fill=tk.X, pady=2)
        engine_combo.bind('<<ComboboxSelected>>', self.on_engine_changed)
        self.engine_info_label = ttk.Label(voice_frame, text="", foreground="gray", wraplength=500)
        self.engine_info_label.pack(anchor=tk.W, pady=2)
        ttk.Label(voice_frame, text="音声モデル:").pack(anchor=tk.W, pady=(10,0))
        self.voice_var = tk.StringVar() # 初期値はupdate_voice_modelsで設定
        self.voice_combo = ttk.Combobox(voice_frame, textvariable=self.voice_var, state="readonly", width=50)
        self.voice_combo.pack(fill=tk.X, pady=2)

        speed_frame = ttk.Frame(voice_frame); speed_frame.pack(fill=tk.X, pady=(10,0))
        ttk.Label(speed_frame, text="音声速度:").pack(side=tk.LEFT)
        self.speed_var = tk.DoubleVar(value=1.0)
        speed_scale = ttk.Scale(speed_frame, from_=0.5, to=2.0, variable=self.speed_var, orient=tk.HORIZONTAL, length=300)
        speed_scale.pack(side=tk.LEFT, padx=10)
        self.speed_label = ttk.Label(speed_frame, text="1.0")
        self.speed_label.pack(side=tk.LEFT, padx=5)
        self.speed_var.trace('w', lambda *args: self.speed_label.config(text=f"{self.speed_var.get():.1f}"))

        quality_frame = ttk.Frame(voice_frame); quality_frame.pack(fill=tk.X, pady=5)
        ttk.Label(quality_frame, text="音声品質:").pack(side=tk.LEFT) # (Google AI Studio New で使用)
        self.quality_var = tk.StringVar(value="標準") # Google AI Studio New での品質設定用
        quality_combo = ttk.Combobox(quality_frame, textvariable=self.quality_var,
                                    values=["標準", "高品質"], state="readonly", width=15) # Google AI Studio New は2段階
        quality_combo.pack(side=tk.LEFT, padx=10)


        self.update_voice_models() # 初期音声リスト設定

        response_frame = ttk.LabelFrame(self.dialog, text="応答設定", padding="10")
        response_frame.pack(fill=tk.X, padx=10, pady=10)
        resp_grid = ttk.Frame(response_frame); resp_grid.pack(fill=tk.X)
        ttk.Label(resp_grid, text="応答長さ:").grid(row=0, column=0, sticky=tk.W)
        self.response_length_var = tk.StringVar(value="1-2文程度")
        length_combo = ttk.Combobox(resp_grid, textvariable=self.response_length_var,
                                   values=["1文程度", "1-2文程度", "2-3文程度", "3-4文程度"], state="readonly")
        length_combo.grid(row=0, column=1, padx=10, sticky=tk.W)
        ttk.Label(resp_grid, text="絵文字使用:").grid(row=0, column=2, sticky=tk.W, padx=(20,0))
        self.emoji_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(resp_grid, variable=self.emoji_var).grid(row=0, column=3, padx=5)
        ttk.Label(resp_grid, text="感情レベル:").grid(row=1, column=0, sticky=tk.W)
        self.emotion_var = tk.StringVar(value="普通")
        emotion_combo = ttk.Combobox(resp_grid, textvariable=self.emotion_var,
                                    values=["控えめ", "普通", "高め", "超高め"], state="readonly")
        emotion_combo.grid(row=1, column=1, padx=10, sticky=tk.W)

        button_frame = ttk.Frame(self.dialog); button_frame.pack(fill=tk.X, padx=10, pady=20)
        button_text = "更新" if self.is_edit_mode else "作成"
        ttk.Button(button_frame, text=button_text, command=self.save_character).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="キャンセル", command=self.dialog.destroy).pack(side=tk.RIGHT, padx=5)
        test_frame = ttk.Frame(button_frame); test_frame.pack(side=tk.LEFT)
        ttk.Button(test_frame, text="🎤 音声テスト", command=self.test_voice).pack(side=tk.LEFT, padx=5)
        ttk.Button(test_frame, text="🔄 エンジン比較", command=self.compare_voice_engines).pack(side=tk.LEFT, padx=5)


    def load_existing_data(self):
        if not self.char_data: return
        self.name_var.set(self.char_data.get('name', ''))
        personality = self.char_data.get('personality', {})
        self.base_tone_var.set(personality.get('base_tone', ''))
        self.speech_style_var.set(personality.get('speech_style', ''))
        self.traits_text.insert(1.0, '\n'.join(personality.get('character_traits', [])))
        self.topics_text.insert(1.0, '\n'.join(personality.get('favorite_topics', [])))

        voice_settings = self.char_data.get('voice_settings', {})
        self.voice_engine_var.set(voice_settings.get('engine', 'google_ai_studio_new'))
        self.update_voice_models() # エンジン変更後にモデルリストを更新
        # 保存されたモデル名が新しいリストに存在するか確認して設定
        saved_model = voice_settings.get('model', '')
        if saved_model and saved_model in self.voice_combo['values']:
            self.voice_var.set(saved_model)
        elif self.voice_combo['values']: # なければリストの最初のものを
             self.voice_var.set(self.voice_combo['values'][0])

        self.speed_var.set(voice_settings.get('speed', 1.0))
        self.quality_var.set(voice_settings.get('quality', '標準'))


        response_settings = self.char_data.get('response_settings', {})
        self.response_length_var.set(response_settings.get('max_length', '1-2文程度'))
        self.emoji_var.set(response_settings.get('use_emojis', True))
        self.emotion_var.set(response_settings.get('emotion_level', '普通'))


    def on_template_changed(self, event=None):
        selected_template_name = self.template_var.get()
        if selected_template_name == "カスタム":
            self.base_tone_var.set(""); self.speech_style_var.set("")
            self.traits_text.delete(1.0, tk.END); self.topics_text.delete(1.0, tk.END)
            self.voice_engine_var.set("google_ai_studio_new"); self.update_voice_models()
            self.speed_var.set(1.0); self.quality_var.set("標準")
            self.response_length_var.set("1-2文程度"); self.emoji_var.set(True); self.emotion_var.set("普通")
            return

        template_data = self.character_manager.character_templates.get(selected_template_name)
        if not template_data: return

        personality = template_data.get("personality", {})
        self.base_tone_var.set(personality.get("base_tone", ""))
        self.speech_style_var.set(personality.get("speech_style", ""))
        self.traits_text.delete(1.0, tk.END); self.traits_text.insert(1.0, "\n".join(personality.get("character_traits", [])))
        self.topics_text.delete(1.0, tk.END); self.topics_text.insert(1.0, "\n".join(personality.get("favorite_topics", [])))

        voice_settings = template_data.get("voice_settings", {})
        self.voice_engine_var.set(voice_settings.get("engine", "google_ai_studio_new"))
        self.update_voice_models()
        selected_model = voice_settings.get("model", "")
        if selected_model and selected_model in self.voice_combo['values']: self.voice_var.set(selected_model)
        elif self.voice_combo['values']: self.voice_var.set(self.voice_combo['values'][0])
        self.speed_var.set(voice_settings.get("speed", 1.0))
        self.quality_var.set(voice_settings.get("quality", "標準"))


        response_settings = template_data.get("response_settings", {})
        self.response_length_var.set(response_settings.get("max_length", "1-2文程度"))
        self.emoji_var.set(response_settings.get("use_emojis", True))
        self.emotion_var.set(response_settings.get("emotion_level", "普通"))

    def on_engine_changed(self, event=None):
        self.update_voice_models()

    def update_voice_models(self):
        engine_choice = self.voice_engine_var.get()
        voices = []
        default_voice = ""
        info_text = ""
        api_instance = None

        if engine_choice == "google_ai_studio_new":
            api_instance = GoogleAIStudioNewVoiceAPI()
            info_text = "🚀 最新SDK・リアルタイム・多言語"
        elif engine_choice == "avis_speech":
            api_instance = AvisSpeechEngineAPI()
            info_text = "🎙️ ローカル・高品質・VOICEVOX互換"
        elif engine_choice == "voicevox":
            api_instance = VOICEVOXEngineAPI()
            # VOICEVOXEngineAPI.get_available_voices() は同期的に動作する想定
            # もし非同期の場合は、ここで asyncio.run() するか、CharacterManager経由で取得済みのリストを使う
            info_text = "🎤 定番キャラ・ずんだもん等"
        elif engine_choice == "system_tts":
            api_instance = SystemTTSAPI()
            info_text = "💻 OS標準TTS・無料・オフライン"

        if api_instance:
            try:
                # get_available_voices が非同期の場合の対応 (VOICEVOX, AvisSpeech)
                if asyncio.iscoroutinefunction(getattr(api_instance, 'check_availability', None)):
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(api_instance.check_availability())
                    finally:
                        loop.close()
                elif hasattr(api_instance, 'check_availability'): # 同期的な check_availability
                    api_instance.check_availability()

                voices = api_instance.get_available_voices()
                default_voice = voices[0] if voices else ""
            except Exception as e:
                logger.error(f"Error getting voices for {engine_choice}: {e}")
                voices = ["エラー"]
                default_voice = "エラー"
                info_text += " (リスト取得エラー)"
        else: # フォールバック
            voices = ["N/A"]
            default_voice = "N/A"

        self.voice_combo['values'] = voices
        if voices:
            # 現在の選択がリストにあれば維持、なければデフォルトを設定
            current_selection = self.voice_var.get()
            if current_selection and current_selection in voices:
                self.voice_var.set(current_selection)
            else:
                self.voice_var.set(default_voice)
        else: # voicesが空リストの場合
            self.voice_var.set("")


        self.engine_info_label.config(text=info_text)


    def _get_api_key(self, key_name):
        # CharacterEditDialog が ConfigManager を持つように変更
        if self.config_manager:
            return self.config_manager.get_system_setting(key_name, "")
        # フォールバックとして、親ウィンドウ (CharacterManagementWindow) 経由で取得する試み
        # ただし、この方法は推奨されない。ダイアログは必要な情報を直接渡されるべき。
        elif hasattr(self.parent, 'config') and hasattr(self.parent.config, 'get_system_setting'):
            return self.parent.config.get_system_setting(key_name, "")
        logger.warning(f"APIキー '{key_name}' の取得に失敗しました。ConfigManagerが設定されていません。")
        return ""

    def test_voice(self):
        text = f"こんにちは！私は{self.name_var.get() or 'テスト'}です。音声テスト中です。"
        voice_engine_choice = self.voice_engine_var.get()
        voice_model_choice = self.voice_var.get()
        speed_choice = self.speed_var.get()
        api_key_google = self._get_api_key("google_ai_api_key")

        def run_test_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                audio_player = AudioPlayer(config_manager=self.config_manager) # config_managerを渡す
                # VoiceEngineManagerもここでインスタンス化するか、渡される必要がある
                voice_manager_local = VoiceEngineManager() # このダイアログ専用

                # synthesize_with_fallback を使う方が適切
                audio_files = loop.run_until_complete(
                    voice_manager_local.synthesize_with_fallback(
                        text, voice_model_choice, speed_choice,
                        preferred_engine=voice_engine_choice,
                        api_key=api_key_google # Google AI Studio New と Google Cloud TTS で使用
                    )
                )
                if audio_files:
                    loop.run_until_complete(audio_player.play_audio_files(audio_files))
                    logger.info(f"Voice test successful: {voice_engine_choice}/{voice_model_choice}")
                else:
                    logger.error(f"Voice test failed: {voice_engine_choice}/{voice_model_choice}")
                    messagebox.showerror("音声テスト失敗", "音声ファイルの生成に失敗しました。", parent=self.dialog)
            except Exception as e:
                logger.error(f"Voice test error: {e}", exc_info=True)
                messagebox.showerror("音声テストエラー", f"エラーが発生しました: {e}", parent=self.dialog)
            finally:
                loop.close()
        threading.Thread(target=run_test_async, daemon=True).start()


    def compare_voice_engines(self):
        text = f"私は{self.name_var.get() or 'テスト'}です。各エンジンの音質を比較します。"
        api_key_google = self._get_api_key("google_ai_api_key")

        def run_comparison_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                audio_player = AudioPlayer(config_manager=self.config_manager)
                voice_manager_local = VoiceEngineManager()
                engines_to_test_config = [
                    {"engine": "google_ai_studio_new", "model_prefix": "models/gemini-2.5-flash-preview-tts-", "default_model": "alloy"}, # 短い名前でOKのはず
                    {"engine": "avis_speech", "default_model": "Anneli(ノーマル)"},
                    {"engine": "voicevox", "default_model": "ずんだもん(ノーマル)"},
                    {"engine": "system_tts", "default_model": None} # SystemTTSはモデル指定方法が異なる場合あり
                ]

                for i, config in enumerate(engines_to_test_config, 1):
                    engine_name = config["engine"]
                    engine_instance = voice_manager_local.get_engine_instance(engine_name)
                    if not engine_instance:
                        logger.warning(f"Engine {engine_name} not found for comparison.")
                        continue

                    available_voices = engine_instance.get_available_voices()
                    model_to_use = config["default_model"]
                    if engine_name == "system_tts" and available_voices: # SystemTTSは最初の利用可能な音声
                        model_to_use = available_voices[0]
                    elif not model_to_use and available_voices : # 他エンジンでデフォルトが指定されてない場合
                         model_to_use = available_voices[0]
                    elif model_to_use and model_to_use not in available_voices and available_voices : # 指定モデルがない場合
                        logger.warning(f"Model {model_to_use} not in available voices for {engine_name}, using {available_voices[0]}")
                        model_to_use = available_voices[0]
                    elif not available_voices :
                        logger.warning(f"No available voices for {engine_name}")
                        continue


                    logger.info(f"Comparing engine {i}: {engine_name} with model {model_to_use}")
                    test_text_engine = f"エンジン{i}番、{engine_name}、モデル{model_to_use}による音声です。{text}"

                    # synthesize_with_fallback を使う
                    audio_files = loop.run_until_complete(
                        voice_manager_local.synthesize_with_fallback(
                            test_text_engine, model_to_use, 1.0,
                            preferred_engine=engine_name,
                            api_key=api_key_google
                        )
                    )
                    if audio_files:
                        loop.run_until_complete(audio_player.play_audio_files(audio_files))
                        logger.info(f"Comparison for {engine_name} successful.")
                    else:
                        logger.error(f"Comparison for {engine_name} failed.")
                    time.sleep(1) # 各エンジンの間に少し待機
                logger.info("Voice engine comparison finished.")
            except Exception as e:
                logger.error(f"Voice engine comparison error: {e}", exc_info=True)
                messagebox.showerror("比較テストエラー", f"エラーが発生しました: {e}", parent=self.dialog)
            finally:
                loop.close()
        threading.Thread(target=run_comparison_async, daemon=True).start()


    def save_character(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("エラー", "キャラクター名を入力してください", parent=self.dialog)
            return

        try:
            char_data = {
                "name": name,
                "personality": {
                    "base_tone": self.base_tone_var.get(),
                    "speech_style": self.speech_style_var.get(),
                    "character_traits": [t.strip() for t in self.traits_text.get(1.0, tk.END).strip().split('\n') if t.strip()],
                    "favorite_topics": [t.strip() for t in self.topics_text.get(1.0, tk.END).strip().split('\n') if t.strip()]
                },
                "voice_settings": {
                    "engine": self.voice_engine_var.get(),
                    "model": self.voice_var.get(),
                    "speed": self.speed_var.get(),
                    "quality": self.quality_var.get(), # 品質設定を追加
                    "volume": 1.0 # デフォルトボリューム (gui.pyにはあったが、CharacterEditDialogにはなかったので追加)
                },
                "response_settings": {
                    "max_length": self.response_length_var.get(),
                    "use_emojis": self.emoji_var.get(),
                    "emotion_level": self.emotion_var.get()
                }
            }

            if self.is_edit_mode:
                char_data["char_id"] = self.char_id
                char_data["created_at"] = self.char_data.get("created_at", datetime.now().isoformat())
                char_data["updated_at"] = datetime.now().isoformat()
                self.character_manager.config.save_character(self.char_id, char_data)
                self.result = {"char_id": self.char_id, "name": name, "action": "edited"}
            else:
                template_name_val = getattr(self, 'template_var', tk.StringVar(value="カスタム")).get()
                char_id_new = self.character_manager.create_character(
                    name=name,
                    template_name=template_name_val if template_name_val != "カスタム" else None,
                    custom_settings=char_data
                )
                self.result = {"char_id": char_id_new, "name": name, "action": "created"}

            self.dialog.destroy()
        except Exception as e:
            action_str = "編集" if self.is_edit_mode else "作成"
            logger.error(f"Character {action_str} failed: {e}", exc_info=True)
            messagebox.showerror("エラー", f"キャラクターの{action_str}に失敗: {e}", parent=self.dialog)

# --- CharacterManagementWindowクラス ---
class CharacterManagementWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("キャラクター管理")
        self.root.geometry("900x700")

        self.config_manager = ConfigManager() # このウィンドウ専用のConfigManager
        self.character_manager = CharacterManager(self.config_manager) # CharacterManagerも初期化
        # VoiceEngineManager と AudioPlayer は CharacterEditDialog で必要に応じてインスタンス化される

        self.create_widgets()
        self.refresh_character_list_display()


    def log(self, message): # 簡易ログ
        logger.info(message)

    def create_widgets(self):
        # キャラクターリスト表示フレーム
        list_frame = ttk.LabelFrame(self.root, text="キャラクター一覧", padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.char_tree = ttk.Treeview(list_frame, columns=('name', 'type', 'voice', 'engine', 'created'), show='headings')
        self.char_tree.heading('name', text='キャラクター名')
        self.char_tree.heading('type', text='タイプ') # 推定
        self.char_tree.heading('voice', text='音声モデル')
        self.char_tree.heading('engine', text='音声エンジン')
        self.char_tree.heading('created', text='作成日時')
        self.char_tree.column('name', width=150); self.char_tree.column('type', width=100)
        self.char_tree.column('voice', width=150); self.char_tree.column('engine', width=120)
        self.char_tree.column('created', width=150)
        char_tree_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.char_tree.yview)
        self.char_tree.configure(yscrollcommand=char_tree_scroll.set)
        self.char_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        char_tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.char_tree.bind('<Double-1>', lambda e: self.edit_selected_character())

        # 操作ボタンフレーム
        char_buttons_frame = ttk.Frame(self.root, padding="5") # rootに直接配置
        char_buttons_frame.pack(fill=tk.X, padx=10, pady=(0,10))

        # 1行目ボタン
        buttons_row1 = ttk.Frame(char_buttons_frame)
        buttons_row1.pack(fill=tk.X, pady=2)
        ttk.Button(buttons_row1, text="📝 新規作成", command=self.create_new_character_action).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_row1, text="✏️ 編集", command=self.edit_selected_character).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_row1, text="📋 複製", command=self.duplicate_selected_character).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_row1, text="🗑️ 削除", command=self.delete_selected_character).pack(side=tk.LEFT, padx=5)

        # 2行目ボタン
        buttons_row2 = ttk.Frame(char_buttons_frame)
        buttons_row2.pack(fill=tk.X, pady=2)
        ttk.Button(buttons_row2, text="📤 エクスポート", command=self.export_selected_character).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_row2, text="📥 インポート", command=self.import_character_action).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_row2, text="🎤 音声テスト(選択中)", command=self.test_selected_character_voice).pack(side=tk.LEFT, padx=5)
        # ttk.Button(buttons_row2, text="📊 性能測定", command=self.measure_character_performance_action).pack(side=tk.LEFT, padx=5) # 未実装なのでコメントアウト

        # テンプレート情報表示 (gui.pyからコピー)
        template_display_frame = ttk.LabelFrame(self.root, text="テンプレート一覧 v2.2（4エンジン完全対応）", padding="10")
        template_display_frame.pack(fill=tk.X, padx=10, pady=5)
        template_info_text = tk.Text(template_display_frame, height=8, width=100, wrap=tk.WORD, state=tk.DISABLED)
        template_info_scroll = ttk.Scrollbar(template_display_frame, orient=tk.VERTICAL, command=template_info_text.yview)
        template_info_text.configure(yscrollcommand=template_info_scroll.set)
        template_info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        template_info_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        template_content = """
🚀 最新AI系: 未来的・知的・革新的思考・グローバル視点 【Google AI Studio新音声: alloy】
🌟 元気系: 関西弁・超ポジティブ・リアクション大・エネルギッシュ 【Avis Speech: Anneli(ノーマル)】
🎓 知的系: 丁寧語・論理的・先生タイプ・博学 【Avis Speech: Anneli(クール)】
🌸 癒し系: ふんわり・穏やか・聞き上手・母性的 【Avis Speech: Anneli(ささやき)】
🎭 ずんだもん系: 「〜のだ」語尾・親しみやすい・東北弁・愛されキャラ 【VOICEVOX: ずんだもん(ノーマル)】
🎪 キャラクター系: アニメ調・個性的・エンターテイナー・表現豊か 【VOICEVOX: 四国めたん(ノーマル)】
⭐ プロ品質系: プロフェッショナル・上品・洗練・エレガント 【Google AI Studio新音声: puck】
🌍 多言語対応系: 国際的・グローバル・多文化理解・文化架け橋 【Google AI Studio新音声: nova】
🛠️ カスタム: 自由設定・完全カスタマイズ・オリジナル
        """
        template_info_text.config(state=tk.NORMAL)
        template_info_text.insert(1.0, template_content.strip())
        template_info_text.config(state=tk.DISABLED)


    def refresh_character_list_display(self):
        self.char_tree.delete(*self.char_tree.get_children())
        characters = self.character_manager.get_all_characters()
        for char_id, data in characters.items():
            self.char_tree.insert('', 'end', iid=char_id, values=(
                data.get('name', 'Unknown'),
                self._estimate_character_type(data), # 推定タイプ
                data.get('voice_settings', {}).get('model', 'N/A'),
                data.get('voice_settings', {}).get('engine', 'N/A'),
                data.get('created_at', 'N/A')
            ))
        self.log(f"キャラクターリスト表示を更新 ({len(characters)}件)")

    def _estimate_character_type(self, char_data):
        # gui.pyのものを参考に簡易実装
        tone = char_data.get('personality', {}).get('base_tone', '').lower()
        if '元気' in tone or '明るい' in tone: return '🌟 元気系'
        if '知的' in tone or '落ち着いた' in tone: return '🎓 知的系'
        if '癒し' in tone or '穏やか' in tone: return '🌸 癒し系'
        if 'ずんだもん' in char_data.get('name','').lower() : return '🎭 ずんだもん系'
        return '⚙️ カスタム'

    def create_new_character_action(self):
        # CharacterEditDialog に config_manager を渡す
        dialog = CharacterEditDialog(self.root, self.character_manager, config_manager=self.config_manager)
        if dialog.result and dialog.result.get("action") == "created":
            self.refresh_character_list_display()
            self.log(f"✅ 新キャラクター '{dialog.result['name']}' を作成")

    def edit_selected_character(self):
        selection = self.char_tree.selection()
        if not selection:
            messagebox.showwarning("選択エラー", "編集するキャラクターを選択してください", parent=self.root)
            return
        char_id = selection[0]
        char_data = self.character_manager.get_character(char_id)
        if not char_data:
            messagebox.showerror("エラー", "キャラクターデータが見つかりません", parent=self.root)
            return
        # CharacterEditDialog に config_manager を渡す
        dialog = CharacterEditDialog(self.root, self.character_manager, char_id, char_data, config_manager=self.config_manager)
        if dialog.result and dialog.result.get("action") == "edited":
            self.refresh_character_list_display()
            self.log(f"✏️ キャラクター '{dialog.result['name']}' を編集")

    def duplicate_selected_character(self):
        selection = self.char_tree.selection()
        if not selection:
            messagebox.showwarning("選択エラー", "複製するキャラクターを選択してください", parent=self.root)
            return
        source_char_id = selection[0]
        source_char_data = self.character_manager.get_character(source_char_id)
        if not source_char_data:
            messagebox.showerror("エラー", "複製元キャラクターデータが見つかりません", parent=self.root)
            return

        new_name = simpledialog.askstring("キャラクター複製", "新しいキャラクター名:", initialvalue=f"{source_char_data.get('name','Unknown')}のコピー", parent=self.root)
        if new_name:
            try:
                # CharacterManagerに複製機能があればそれを使う。なければ手動で。
                # ここでは手動で模倣
                new_char_data = json.loads(json.dumps(source_char_data)) # Deep copy
                new_char_data['name'] = new_name
                # char_id, created_at, updated_at は CharacterManager.create_character で自動生成されるので削除
                if 'char_id' in new_char_data: del new_char_data['char_id']
                if 'created_at' in new_char_data: del new_char_data['created_at']
                if 'updated_at' in new_char_data: del new_char_data['updated_at']

                new_id = self.character_manager.create_character(name=new_name, custom_settings=new_char_data)
                self.refresh_character_list_display()
                self.log(f"📋 キャラクター '{new_name}' (ID: {new_id}) を複製")
            except Exception as e:
                messagebox.showerror("複製エラー", f"複製に失敗: {e}", parent=self.root)
                self.log(f"❌ 複製エラー: {e}")


    def delete_selected_character(self):
        selection = self.char_tree.selection()
        if not selection:
            messagebox.showwarning("選択エラー", "削除するキャラクターを選択してください", parent=self.root)
            return
        char_id = selection[0]
        char_name = self.char_tree.item(char_id, 'values')[0]
        if messagebox.askyesno("削除確認", f"キャラクター '{char_name}' を削除しますか？\nこの操作は取り消せません。", parent=self.root):
            if self.character_manager.delete_character(char_id):
                self.refresh_character_list_display()
                self.log(f"🗑️ キャラクター '{char_name}' を削除")
            else:
                messagebox.showerror("削除エラー", "キャラクターの削除に失敗しました。", parent=self.root)

    def export_selected_character(self):
        selection = self.char_tree.selection()
        if not selection:
            messagebox.showwarning("選択エラー", "エクスポートするキャラクターを選択してください", parent=self.root)
            return
        char_id = selection[0]
        char_data = self.character_manager.get_character(char_id)
        if not char_data:
            messagebox.showerror("エラー", "キャラクターデータが見つかりません", parent=self.root)
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSONキャラクターファイル", "*.json")],
            initialfile=f"{char_data.get('name', 'character').replace(' ', '_')}.json",
            title="キャラクターをエクスポート",
            parent=self.root
        )
        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(char_data, f, ensure_ascii=False, indent=4)
                messagebox.showinfo("エクスポート完了", f"キャラクターを '{filepath}' に保存しました。", parent=self.root)
                self.log(f"📤 キャラクター '{char_data.get('name')}' をエクスポート: {filepath}")
            except Exception as e:
                messagebox.showerror("エクスポートエラー", f"エクスポート失敗: {e}", parent=self.root)

    def import_character_action(self):
        filepath = filedialog.askopenfilename(
            title="キャラクターJSONファイルを選択",
            filetypes=[("JSONファイル", "*.json")],
            parent=self.root
        )
        if not filepath: return
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                imported_data = json.load(f)

            # 必須キーのチェック (簡易的)
            if not all(k in imported_data for k in ["name", "personality", "voice_settings"]):
                messagebox.showerror("インポートエラー", "ファイル形式が正しくありません。必須キーが不足しています。", parent=self.root)
                return

            # IDは新規発行するので、既存のIDは削除
            if 'char_id' in imported_data: del imported_data['char_id']
            if 'created_at' in imported_data: del imported_data['created_at']
            if 'updated_at' in imported_data: del imported_data['updated_at']


            new_id = self.character_manager.create_character(
                name=imported_data.get('name', 'インポートされたキャラ'),
                custom_settings=imported_data # name以外はcustom_settingsで渡す
            )
            self.refresh_character_list_display()
            self.log(f"📥 キャラクター '{imported_data.get('name')}' (ID: {new_id}) をインポート")
            messagebox.showinfo("インポート完了", f"キャラクター '{imported_data.get('name')}' をインポートしました。", parent=self.root)
        except json.JSONDecodeError:
             messagebox.showerror("インポートエラー", "JSONファイルの解析に失敗しました。", parent=self.root)
        except Exception as e:
            messagebox.showerror("インポートエラー", f"インポート失敗: {e}", parent=self.root)
            self.log(f"❌ インポートエラー: {e}")


    def test_selected_character_voice(self):
        selection = self.char_tree.selection()
        if not selection:
            messagebox.showwarning("選択なし", "音声テストするキャラクターを選択してください。", parent=self.root)
            return
        char_id = selection[0]
        char_data = self.character_manager.get_character(char_id)
        if not char_data:
            messagebox.showerror("エラー", "キャラクターデータが見つかりません。", parent=self.root)
            return

        test_text = simpledialog.askstring("音声テスト", "テストするテキストを入力してください:", initialvalue="こんにちは、これは音声テストです。", parent=self.root)
        if not test_text: return

        self.log(f"🎤 キャラクター '{char_data['name']}' の音声テスト開始...")

        # CharacterEditDialogのtest_voiceロジックを参考に、この場で実行
        voice_settings = char_data.get('voice_settings', {})
        engine_choice = voice_settings.get('engine', self.config_manager.get_system_setting('voice_engine'))
        model_choice = voice_settings.get('model')
        speed_choice = voice_settings.get('speed', 1.0)
        api_key_google = self.config_manager.get_system_setting("google_ai_api_key")


        def run_test_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # このウィンドウ専用のAudioPlayerとVoiceEngineManager
                audio_player = AudioPlayer(config_manager=self.config_manager)
                voice_manager_local = VoiceEngineManager()

                audio_files = loop.run_until_complete(
                    voice_manager_local.synthesize_with_fallback(
                        test_text, model_choice, speed_choice,
                        preferred_engine=engine_choice,
                        api_key=api_key_google
                    )
                )
                if audio_files:
                    loop.run_until_complete(audio_player.play_audio_files(audio_files))
                    self.log(f"✅ '{char_data['name']}' 音声テスト成功。")
                else:
                    self.log(f"❌ '{char_data['name']}' 音声テスト失敗。")
                    messagebox.showerror("音声テスト失敗", "音声ファイルの生成に失敗しました。", parent=self.root)
            except Exception as e:
                self.log(f"❌ 音声テストエラー: {e}")
                messagebox.showerror("音声テストエラー", f"エラー発生: {e}", parent=self.root)
            finally:
                loop.close()
        threading.Thread(target=run_test_async, daemon=True).start()


def main():
    root = tk.Tk()
    app = CharacterManagementWindow(root)
    root.mainloop()

if __name__ == "__main__":
    main()
