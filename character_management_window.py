import customtkinter
import tkinter as tk # 基本的な型 (StringVarなど) と標準ダイアログのため
from tkinter import ttk, messagebox, filedialog, simpledialog # Treeviewと標準ダイアログはそのまま使用
import json
import os
import uuid # CharacterEditDialogでは使われていないが、将来的にもし使うなら
import sys # フォント選択のため
from datetime import datetime
import asyncio
import threading
import time

from config import ConfigManager
from character_manager import CharacterManager
from audio_manager import VoiceEngineManager, AudioPlayer, GoogleAIStudioNewVoiceAPI, AvisSpeechEngineAPI, VOICEVOXEngineAPI, SystemTTSAPI

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CharacterEditDialog:
    def __init__(self, parent, character_manager, char_id=None, char_data=None, config_manager=None):
        self.parent = parent
        self.character_manager = character_manager
        self.char_id = char_id
        self.char_data = char_data
        self.result = None
        self.is_edit_mode = char_id is not None
        self.config_manager = config_manager

        # フォント設定をダイアログにも適用
        self.default_font = ("Yu Gothic UI", 12)
        if sys.platform == "darwin": self.default_font = ("Hiragino Sans", 14)
        elif sys.platform.startswith("linux"): self.default_font = ("Noto Sans CJK JP", 12)
        self.label_font = (self.default_font[0], self.default_font[1], "bold")


        # tk.Toplevel -> customtkinter.CTkToplevel
        self.dialog = customtkinter.CTkToplevel(parent)
        title = "キャラクター編集" if self.is_edit_mode else "キャラクター作成"
        self.dialog.title(title + " - CTk版")
        self.dialog.geometry("700x850") # 少し大きめに
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # CTkToplevelはpackなどで内部コンテナが必要な場合がある
        # ここではメインフレームを作成して、その中にウィジェットを配置
        self.main_dialog_frame = customtkinter.CTkScrollableFrame(self.dialog) # スクロール可能に
        self.main_dialog_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.create_widgets(self.main_dialog_frame) # メインフレームを渡す

        if self.is_edit_mode and self.char_data:
            self.load_existing_data()

        # CTkToplevelはmainloopを呼ばない
        # self.dialog.wait_window() はそのまま
        self.dialog.wait_window()


    def create_widgets(self, dialog_frame: customtkinter.CTkFrame): # 引数に親フレームを受け取る
        # CharacterEditDialog のウィジェット作成は変更なし
        # キャラクター名
        customtkinter.CTkLabel(dialog_frame, text="キャラクター名:", font=self.label_font).pack(anchor="w", padx=10, pady=(10,2))
        self.name_var = tk.StringVar()
        customtkinter.CTkEntry(dialog_frame, textvariable=self.name_var, width=300, font=self.default_font).pack(anchor="w", padx=10, pady=(0,10))

        if not self.is_edit_mode:
            template_outer_frame = customtkinter.CTkFrame(dialog_frame)
            template_outer_frame.pack(fill="x", padx=10, pady=10)
            customtkinter.CTkLabel(template_outer_frame, text="テンプレート選択（4エンジン対応）", font=self.label_font).pack(anchor="w", padx=10, pady=(5,0))
            template_frame = customtkinter.CTkFrame(template_outer_frame)
            template_frame.pack(fill="x", padx=10, pady=5)

            self.template_var = tk.StringVar(value="最新AI系")
            templates = ["最新AI系", "元気系", "知的系", "癒し系", "ずんだもん系", "キャラクター系", "プロ品質系", "多言語対応系", "カスタム"]
            template_grid = customtkinter.CTkFrame(template_frame, fg_color="transparent")
            template_grid.pack(fill="x")
            for i, template in enumerate(templates):
                row, col = divmod(i, 2)
                rb = customtkinter.CTkRadioButton(template_grid, text=template, variable=self.template_var, value=template, command=self.on_template_changed, font=self.default_font)
                rb.grid(row=row, column=col, sticky="w", padx=10, pady=3)

        personality_outer_frame = customtkinter.CTkFrame(dialog_frame)
        personality_outer_frame.pack(fill="x", padx=10, pady=10)
        customtkinter.CTkLabel(personality_outer_frame, text="性格設定（詳細）", font=self.label_font).pack(anchor="w", padx=10, pady=(5,0))
        personality_frame = customtkinter.CTkFrame(personality_outer_frame)
        personality_frame.pack(fill="x", padx=10, pady=5)

        customtkinter.CTkLabel(personality_frame, text="基本的な性格:", font=self.default_font).pack(anchor="w", pady=(5,0))
        self.base_tone_var = tk.StringVar()
        customtkinter.CTkEntry(personality_frame, textvariable=self.base_tone_var, width=580, font=self.default_font).pack(fill="x", pady=2)
        customtkinter.CTkLabel(personality_frame, text="話し方・口調:", font=self.default_font).pack(anchor="w", pady=(10,0))
        self.speech_style_var = tk.StringVar()
        customtkinter.CTkEntry(personality_frame, textvariable=self.speech_style_var, width=580, font=self.default_font).pack(fill="x", pady=2)

        customtkinter.CTkLabel(personality_frame, text="キャラクターの特徴 (1行1項目):", font=self.default_font).pack(anchor="w", pady=(10,0))
        self.traits_text = customtkinter.CTkTextbox(personality_frame, height=100, width=580, font=self.default_font) # CTkTextbox
        self.traits_text.pack(fill="x", pady=2)
        customtkinter.CTkLabel(personality_frame, text="好きな話題 (1行1項目):", font=self.default_font).pack(anchor="w", pady=(10,0))
        self.topics_text = customtkinter.CTkTextbox(personality_frame, height=100, width=580, font=self.default_font) # CTkTextbox
        self.topics_text.pack(fill="x", pady=2)

        voice_outer_frame = customtkinter.CTkFrame(dialog_frame)
        voice_outer_frame.pack(fill="x", padx=10, pady=10)
        customtkinter.CTkLabel(voice_outer_frame, text="音声設定（4エンジン完全対応）", font=self.label_font).pack(anchor="w", padx=10, pady=(5,0))
        voice_frame = customtkinter.CTkFrame(voice_outer_frame)
        voice_frame.pack(fill="x", padx=10, pady=5)

        customtkinter.CTkLabel(voice_frame, text="音声エンジン:", font=self.default_font).pack(anchor="w")
        self.voice_engine_var = tk.StringVar(value="google_ai_studio_new")
        engine_combo = customtkinter.CTkComboBox(voice_frame, variable=self.voice_engine_var,
                                   values=["google_ai_studio_new", "avis_speech", "voicevox", "system_tts"],
                                   state="readonly", width=580, font=self.default_font, command=self.on_engine_changed) # commandでコールバック
        engine_combo.pack(fill="x", pady=2)
        self.engine_info_label = customtkinter.CTkLabel(voice_frame, text="", text_color="gray", wraplength=500, font=self.default_font)
        self.engine_info_label.pack(anchor="w", pady=2)

        customtkinter.CTkLabel(voice_frame, text="音声モデル:", font=self.default_font).pack(anchor="w", pady=(10,0))
        self.voice_var = tk.StringVar()
        self.voice_combo = customtkinter.CTkComboBox(voice_frame, variable=self.voice_var, state="readonly", width=580, font=self.default_font)
        self.voice_combo.pack(fill="x", pady=2)

        speed_frame_inner = customtkinter.CTkFrame(voice_frame, fg_color="transparent")
        speed_frame_inner.pack(fill="x", pady=(10,0))
        customtkinter.CTkLabel(speed_frame_inner, text="音声速度:", font=self.default_font).pack(side="left", padx=(0,10))
        self.speed_var = tk.DoubleVar(value=1.0)
        # ttk.Scale -> customtkinter.CTkSlider
        speed_slider = customtkinter.CTkSlider(speed_frame_inner, from_=0.5, to=2.0, variable=self.speed_var, width=300, command=lambda val: self.speed_label.configure(text=f"{val:.1f}"))
        speed_slider.pack(side="left", padx=10)
        self.speed_label = customtkinter.CTkLabel(speed_frame_inner, text="1.0", font=self.default_font)
        self.speed_label.pack(side="left", padx=5)
        # CTkSliderのcommandでラベル更新するのでtraceは不要に

        quality_frame_inner = customtkinter.CTkFrame(voice_frame, fg_color="transparent")
        quality_frame_inner.pack(fill="x", pady=5)
        customtkinter.CTkLabel(quality_frame_inner, text="音声品質:", font=self.default_font).pack(side="left", padx=(0,10))
        self.quality_var = tk.StringVar(value="標準")
        quality_combo = customtkinter.CTkComboBox(quality_frame_inner, variable=self.quality_var,
                                    values=["標準", "高品質"], state="readonly", width=150, font=self.default_font)
        quality_combo.pack(side="left", padx=10)
        self.update_voice_models()

        response_outer_frame = customtkinter.CTkFrame(dialog_frame)
        response_outer_frame.pack(fill="x", padx=10, pady=10)
        customtkinter.CTkLabel(response_outer_frame, text="応答設定", font=self.label_font).pack(anchor="w", padx=10, pady=(5,0))
        response_frame = customtkinter.CTkFrame(response_outer_frame)
        response_frame.pack(fill="x", padx=10, pady=5)

        resp_grid = customtkinter.CTkFrame(response_frame, fg_color="transparent")
        resp_grid.pack(fill="x")
        customtkinter.CTkLabel(resp_grid, text="応答長さ:", font=self.default_font).grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.response_length_var = tk.StringVar(value="1-2文程度")
        length_combo = customtkinter.CTkComboBox(resp_grid, variable=self.response_length_var,
                                   values=["1文程度", "1-2文程度", "2-3文程度", "3-4文程度"], state="readonly", font=self.default_font, width=150)
        length_combo.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        customtkinter.CTkLabel(resp_grid, text="絵文字使用:", font=self.default_font).grid(row=0, column=2, sticky="w", padx=(20,0), pady=5)
        self.emoji_var = tk.BooleanVar(value=True)
        customtkinter.CTkCheckBox(resp_grid, variable=self.emoji_var, text="", font=self.default_font).grid(row=0, column=3, padx=5, pady=5) # text=""

        customtkinter.CTkLabel(resp_grid, text="感情レベル:", font=self.default_font).grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.emotion_var = tk.StringVar(value="普通")
        emotion_combo = customtkinter.CTkComboBox(resp_grid, variable=self.emotion_var,
                                    values=["控えめ", "普通", "高め", "超高め"], state="readonly", font=self.default_font, width=150)
        emotion_combo.grid(row=1, column=1, padx=10, pady=5, sticky="w")

        button_frame_bottom = customtkinter.CTkFrame(dialog_frame, fg_color="transparent")
        button_frame_bottom.pack(fill="x", padx=10, pady=20)
        button_text = "更新" if self.is_edit_mode else "作成"

        # ボタンを右寄せにするために新しいフレームを作る
        action_buttons_frame = customtkinter.CTkFrame(button_frame_bottom, fg_color="transparent")
        action_buttons_frame.pack(side="right")
        customtkinter.CTkButton(action_buttons_frame, text=button_text, command=self.save_character, font=self.default_font).pack(side="left", padx=5)
        customtkinter.CTkButton(action_buttons_frame, text="キャンセル", command=self.dialog.destroy, font=self.default_font).pack(side="left", padx=5)

        test_buttons_frame = customtkinter.CTkFrame(button_frame_bottom, fg_color="transparent")
        test_buttons_frame.pack(side="left")
        customtkinter.CTkButton(test_buttons_frame, text="🎤 音声テスト", command=self.test_voice, font=self.default_font).pack(side="left", padx=5)
        customtkinter.CTkButton(test_buttons_frame, text="🔄 エンジン比較", command=self.compare_voice_engines, font=self.default_font).pack(side="left", padx=5)

    def load_existing_data(self):
        if not self.char_data: return
        self.name_var.set(self.char_data.get('name', ''))
        personality = self.char_data.get('personality', {})
        self.base_tone_var.set(personality.get('base_tone', ''))
        self.speech_style_var.set(personality.get('speech_style', ''))
        self.traits_text.delete("1.0", "end") # CTkTextbox
        self.traits_text.insert("1.0", '\n'.join(personality.get('character_traits', [])))
        self.topics_text.delete("1.0", "end") # CTkTextbox
        self.topics_text.insert("1.0", '\n'.join(personality.get('favorite_topics', [])))

        voice_settings = self.char_data.get('voice_settings', {})
        self.voice_engine_var.set(voice_settings.get('engine', 'google_ai_studio_new'))
        self.update_voice_models()
        saved_model = voice_settings.get('model', '')
        if saved_model and saved_model in self.voice_combo.cget("values"): # CTkComboBoxは .cget("values")
            self.voice_var.set(saved_model)
        elif self.voice_combo.cget("values"):
             self.voice_var.set(self.voice_combo.cget("values")[0])
        self.speed_var.set(voice_settings.get('speed', 1.0))
        self.quality_var.set(voice_settings.get('quality', '標準'))

        response_settings = self.char_data.get('response_settings', {})
        self.response_length_var.set(response_settings.get('max_length', '1-2文程度'))
        self.emoji_var.set(response_settings.get('use_emojis', True))
        self.emotion_var.set(response_settings.get('emotion_level', '普通'))

    def on_template_changed(self, event=None): # CTkRadioButtonのcommandはeventを渡さない
        selected_template_name = self.template_var.get()
        if selected_template_name == "カスタム":
            self.base_tone_var.set(""); self.speech_style_var.set("")
            self.traits_text.delete("1.0", "end"); self.topics_text.delete("1.0", "end")
            self.voice_engine_var.set("google_ai_studio_new"); self.update_voice_models()
            self.speed_var.set(1.0); self.quality_var.set("標準")
            self.response_length_var.set("1-2文程度"); self.emoji_var.set(True); self.emotion_var.set("普通")
            return

        template_data = self.character_manager.character_templates.get(selected_template_name)
        if not template_data: return

        personality = template_data.get("personality", {})
        self.base_tone_var.set(personality.get("base_tone", ""))
        self.speech_style_var.set(personality.get("speech_style", ""))
        self.traits_text.delete("1.0", "end"); self.traits_text.insert("1.0", "\n".join(personality.get("character_traits", [])))
        self.topics_text.delete("1.0", "end"); self.topics_text.insert("1.0", "\n".join(personality.get("favorite_topics", [])))

        voice_settings = template_data.get("voice_settings", {})
        self.voice_engine_var.set(voice_settings.get("engine", "google_ai_studio_new"))
        self.update_voice_models()
        selected_model = voice_settings.get("model", "")
        if selected_model and selected_model in self.voice_combo.cget("values"): self.voice_var.set(selected_model)
        elif self.voice_combo.cget("values"): self.voice_var.set(self.voice_combo.cget("values")[0])
        self.speed_var.set(voice_settings.get("speed", 1.0))
        self.quality_var.set(voice_settings.get("quality", "標準"))

        response_settings = template_data.get("response_settings", {})
        self.response_length_var.set(response_settings.get("max_length", "1-2文程度"))
        self.emoji_var.set(response_settings.get("use_emojis", True))
        self.emotion_var.set(response_settings.get("emotion_level", "普通"))

    def on_engine_changed(self, choice=None): # CTkComboBoxのcommandは選択値を渡す
        self.update_voice_models()

    def update_voice_models(self):
        engine_choice = self.voice_engine_var.get()
        voices = []
        default_voice = ""
        info_text = ""
        api_instance = None

        if engine_choice == "google_ai_studio_new": api_instance = GoogleAIStudioNewVoiceAPI(); info_text = "🚀 最新SDK・リアルタイム・多言語"
        elif engine_choice == "avis_speech": api_instance = AvisSpeechEngineAPI(); info_text = "🎙️ ローカル・高品質・VOICEVOX互換"
        elif engine_choice == "voicevox": api_instance = VOICEVOXEngineAPI(); info_text = "🎤 定番キャラ・ずんだもん等"
        elif engine_choice == "system_tts": api_instance = SystemTTSAPI(); info_text = "💻 OS標準TTS・無料・オフライン"

        if api_instance:
            try:
                if asyncio.iscoroutinefunction(getattr(api_instance, 'check_availability', None)):
                    loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
                    try: loop.run_until_complete(api_instance.check_availability())
                    finally: loop.close()
                elif hasattr(api_instance, 'check_availability'): api_instance.check_availability()
                voices = api_instance.get_available_voices()
                default_voice = voices[0] if voices else ""
            except Exception as e:
                logger.error(f"Error getting voices for {engine_choice}: {e}")
                voices = ["エラー"]; default_voice = "エラー"; info_text += " (リスト取得エラー)"
        else: voices = ["N/A"]; default_voice = "N/A"

        self.voice_combo.configure(values=voices if voices else ["選択肢なし"]) # .configureで更新
        if voices:
            current_selection = self.voice_var.get()
            if current_selection and current_selection in voices: self.voice_var.set(current_selection)
            else: self.voice_var.set(default_voice)
        else: self.voice_var.set("選択肢なし" if not voices else "")
        self.engine_info_label.configure(text=info_text) # .configureで更新

    def _get_api_key(self, key_name):
        if self.config_manager: return self.config_manager.get_system_setting(key_name, "")
        elif hasattr(self.parent, 'config') and hasattr(self.parent.config, 'get_system_setting'): # parentはCTkインスタンスのはず
             # CharacterManagementWindowがself.configを持つ想定
            if hasattr(self.parent, 'config_manager_instance'): # 仮の属性名
                return self.parent.config_manager_instance.get_system_setting(key_name, "")
        logger.warning(f"APIキー '{key_name}' の取得に失敗しました。ConfigManagerが設定されていません。")
        return ""

    def test_voice(self):
        text = f"こんにちは！私は{self.name_var.get() or 'テスト'}です。音声テスト中です。"
        voice_engine_choice = self.voice_engine_var.get()
        voice_model_choice = self.voice_var.get()
        speed_choice = self.speed_var.get()
        api_key_google = self._get_api_key("google_ai_api_key")

        def run_test_async():
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            try:
                audio_player = AudioPlayer(config_manager=self.config_manager)
                voice_manager_local = VoiceEngineManager()
                audio_files = loop.run_until_complete(
                    voice_manager_local.synthesize_with_fallback(
                        text, voice_model_choice, speed_choice,
                        preferred_engine=voice_engine_choice, api_key=api_key_google
                    )
                )
                if audio_files:
                    loop.run_until_complete(audio_player.play_audio_files(audio_files))
                    logger.info(f"Voice test successful: {voice_engine_choice}/{voice_model_choice}")
                else:
                    logger.error(f"Voice test failed: {voice_engine_choice}/{voice_model_choice}")
                    messagebox.showerror("音声テスト失敗", "音声ファイルの生成に失敗しました。", parent=self.dialog) # parentはCTkToplevel
            except Exception as e:
                logger.error(f"Voice test error: {e}", exc_info=True)
                messagebox.showerror("音声テストエラー", f"エラーが発生しました: {e}", parent=self.dialog)
            finally: loop.close()
        threading.Thread(target=run_test_async, daemon=True).start()

    def compare_voice_engines(self):
        text = f"私は{self.name_var.get() or 'テスト'}です。各エンジンの音質を比較します。"
        api_key_google = self._get_api_key("google_ai_api_key")

        def run_comparison_async():
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            try:
                audio_player = AudioPlayer(config_manager=self.config_manager)
                voice_manager_local = VoiceEngineManager()
                engines_to_test_config = [
                    {"engine": "google_ai_studio_new", "default_model": "alloy"},
                    {"engine": "avis_speech", "default_model": "Anneli(ノーマル)"},
                    {"engine": "voicevox", "default_model": "ずんだもん(ノーマル)"},
                    {"engine": "system_tts", "default_model": None}
                ]
                for i, config in enumerate(engines_to_test_config, 1):
                    engine_name = config["engine"]
                    engine_instance = voice_manager_local.get_engine_instance(engine_name)
                    if not engine_instance: logger.warning(f"Engine {engine_name} not found."); continue
                    available_voices = engine_instance.get_available_voices()
                    model_to_use = config["default_model"]
                    if engine_name == "system_tts" and available_voices: model_to_use = available_voices[0]
                    elif not model_to_use and available_voices: model_to_use = available_voices[0]
                    elif model_to_use and model_to_use not in available_voices and available_voices:
                        logger.warning(f"Model {model_to_use} not in available for {engine_name}, using {available_voices[0]}")
                        model_to_use = available_voices[0]
                    elif not available_voices: logger.warning(f"No voices for {engine_name}"); continue

                    logger.info(f"Comparing engine {i}: {engine_name} with model {model_to_use}")
                    test_text_engine = f"エンジン{i}番、{engine_name}、モデル{model_to_use}による音声です。{text}"
                    audio_files = loop.run_until_complete(
                        voice_manager_local.synthesize_with_fallback(
                            test_text_engine, model_to_use, 1.0, preferred_engine=engine_name, api_key=api_key_google
                        )
                    )
                    if audio_files:
                        loop.run_until_complete(audio_player.play_audio_files(audio_files))
                        logger.info(f"Comparison for {engine_name} successful.")
                    else: logger.error(f"Comparison for {engine_name} failed.")
                    time.sleep(1)
                logger.info("Voice engine comparison finished.")
            except Exception as e:
                logger.error(f"Voice engine comparison error: {e}", exc_info=True)
                messagebox.showerror("比較テストエラー", f"エラーが発生しました: {e}", parent=self.dialog)
            finally: loop.close()
        threading.Thread(target=run_comparison_async, daemon=True).start()

    def save_character(self):
        name = self.name_var.get().strip()
        if not name: messagebox.showwarning("エラー", "キャラクター名を入力してください", parent=self.dialog); return
        try:
            char_data = {
                "name": name,
                "personality": {
                    "base_tone": self.base_tone_var.get(), "speech_style": self.speech_style_var.get(),
                    "character_traits": [t.strip() for t in self.traits_text.get("1.0", "end-1c").strip().split('\n') if t.strip()], # CTkTextbox
                    "favorite_topics": [t.strip() for t in self.topics_text.get("1.0", "end-1c").strip().split('\n') if t.strip()]  # CTkTextbox
                },
                "voice_settings": {
                    "engine": self.voice_engine_var.get(), "model": self.voice_var.get(),
                    "speed": self.speed_var.get(), "quality": self.quality_var.get(), "volume": 1.0
                },
                "response_settings": {
                    "max_length": self.response_length_var.get(), "use_emojis": self.emoji_var.get(),
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
                    name=name, template_name=template_name_val if template_name_val != "カスタム" else None,
                    custom_settings=char_data
                )
                self.result = {"char_id": char_id_new, "name": name, "action": "created"}
            self.dialog.destroy()
        except Exception as e:
            action_str = "編集" if self.is_edit_mode else "作成"
            logger.error(f"Character {action_str} failed: {e}", exc_info=True)
            messagebox.showerror("エラー", f"キャラクターの{action_str}に失敗: {e}", parent=self.dialog)

class CharacterManagementWindow:
    def __init__(self, root: customtkinter.CTk):
        self.root = root
        self.root.title("キャラクター管理")
        self.root.geometry("950x750")

        self.loading_label = customtkinter.CTkLabel(self.root, text="読み込み中...", font=("Yu Gothic UI", 18))
        self.loading_label.pack(expand=True, fill="both")
        self.root.update_idletasks()

        self.root.after(50, self._initialize_components)

    def _initialize_components(self):
        if hasattr(self, 'loading_label') and self.loading_label.winfo_exists():
            self.loading_label.pack_forget()
            self.loading_label.destroy()

        self.config_manager = ConfigManager()
        self.character_manager = CharacterManager(self.config_manager)

        # フォント設定
        self.default_font = ("Yu Gothic UI", 12)
        if sys.platform == "darwin": self.default_font = ("Hiragino Sans", 14)
        elif sys.platform.startswith("linux"): self.default_font = ("Noto Sans CJK JP", 12)
        self.label_font = (self.default_font[0], self.default_font[1] + 1, "bold")
        self.treeview_font = (self.default_font[0], self.default_font[1] -1)

        self.create_widgets()
        self.refresh_character_list_display()
        self.log("キャラクター管理ウィンドウが初期化されました。")


    def log(self, message):
        # CharacterManagementWindow の log メソッドはUIウィジェットに書き込まない
        logger.info(message)

    def create_widgets(self):
        # メインフレーム
        main_frame = customtkinter.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # キャラクターリスト表示フレーム (CTkFrame + CTkLabel)
        list_outer_frame = customtkinter.CTkFrame(main_frame)
        list_outer_frame.pack(fill="both", expand=True, padx=5, pady=5)
        customtkinter.CTkLabel(list_outer_frame, text="キャラクター一覧", font=self.label_font).pack(anchor="w", padx=10, pady=(5,0))
        list_frame = customtkinter.CTkFrame(list_outer_frame)
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # ttk.Treeview はそのまま使用、スタイル調整
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview.Heading", font=(self.treeview_font[0], self.treeview_font[1], "bold"))
        style.configure("Treeview", font=self.treeview_font, rowheight=int(self.treeview_font[1]*2.0))

        self.char_tree = ttk.Treeview(list_frame, columns=('name', 'type', 'voice', 'engine', 'created'), show='headings', style="Treeview")
        self.char_tree.heading('name', text='キャラクター名')
        self.char_tree.heading('type', text='タイプ')
        self.char_tree.heading('voice', text='音声モデル')
        self.char_tree.heading('engine', text='音声エンジン')
        self.char_tree.heading('created', text='作成日時')
        self.char_tree.column('name', width=150, stretch=tk.YES); self.char_tree.column('type', width=100, stretch=tk.YES)
        self.char_tree.column('voice', width=150, stretch=tk.YES); self.char_tree.column('engine', width=120, stretch=tk.YES)
        self.char_tree.column('created', width=150, stretch=tk.YES)

        char_tree_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.char_tree.yview) # ttk.Scrollbar
        self.char_tree.configure(yscrollcommand=char_tree_scroll.set)
        char_tree_scroll.pack(side="right", fill="y")
        self.char_tree.pack(side="left", fill="both", expand=True)
        self.char_tree.bind('<Double-1>', lambda e: self.edit_selected_character())

        # 操作ボタンフレーム
        char_buttons_frame = customtkinter.CTkFrame(main_frame, fg_color="transparent")
        char_buttons_frame.pack(fill="x", padx=5, pady=(5,10))

        buttons_row1 = customtkinter.CTkFrame(char_buttons_frame, fg_color="transparent")
        buttons_row1.pack(fill="x", pady=2)
        customtkinter.CTkButton(buttons_row1, text="📝 新規作成", command=self.create_new_character_action, font=self.default_font).pack(side="left", padx=5)
        customtkinter.CTkButton(buttons_row1, text="✏️ 編集", command=self.edit_selected_character, font=self.default_font).pack(side="left", padx=5)
        customtkinter.CTkButton(buttons_row1, text="📋 複製", command=self.duplicate_selected_character, font=self.default_font).pack(side="left", padx=5)
        customtkinter.CTkButton(buttons_row1, text="🗑️ 削除", command=self.delete_selected_character, font=self.default_font).pack(side="left", padx=5)

        buttons_row2 = customtkinter.CTkFrame(char_buttons_frame, fg_color="transparent")
        buttons_row2.pack(fill="x", pady=2)
        customtkinter.CTkButton(buttons_row2, text="📤 エクスポート", command=self.export_selected_character, font=self.default_font).pack(side="left", padx=5)
        customtkinter.CTkButton(buttons_row2, text="📥 インポート", command=self.import_character_action, font=self.default_font).pack(side="left", padx=5)
        customtkinter.CTkButton(buttons_row2, text="🎤 音声テスト(選択中)", command=self.test_selected_character_voice, font=self.default_font).pack(side="left", padx=5)

        # テンプレート情報表示 (CTkTextboxを使用)
        template_outer_frame = customtkinter.CTkFrame(main_frame)
        template_outer_frame.pack(fill="x", padx=5, pady=5)
        customtkinter.CTkLabel(template_outer_frame, text="テンプレート一覧 v2.2（4エンジン完全対応）", font=self.label_font).pack(anchor="w", padx=10, pady=(5,0))
        template_display_frame = customtkinter.CTkFrame(template_outer_frame)
        template_display_frame.pack(fill="x", padx=5, pady=5)

        template_info_text = customtkinter.CTkTextbox(template_display_frame, height=180, width=100, wrap="word", font=self.default_font) # CTkTextbox
        template_info_text.pack(fill="both", expand=True, padx=5, pady=5)

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
        template_info_text.insert("1.0", template_content.strip())
        template_info_text.configure(state="disabled") # 編集不可に

    def refresh_character_list_display(self):
        self.char_tree.delete(*self.char_tree.get_children())
        characters = self.character_manager.get_all_characters()
        for char_id, data in characters.items():
            self.char_tree.insert('', 'end', iid=char_id, values=(
                data.get('name', 'Unknown'), self._estimate_character_type(data),
                data.get('voice_settings', {}).get('model', 'N/A'),
                data.get('voice_settings', {}).get('engine', 'N/A'),
                data.get('created_at', 'N/A')
            ))
        self.log(f"キャラクターリスト表示を更新 ({len(characters)}件)")

    def _estimate_character_type(self, char_data):
        tone = char_data.get('personality', {}).get('base_tone', '').lower()
        if '元気' in tone or '明るい' in tone: return '🌟 元気系'
        if '知的' in tone or '落ち着いた' in tone: return '🎓 知的系'
        if '癒し' in tone or '穏やか' in tone: return '🌸 癒し系'
        if 'ずんだもん' in char_data.get('name','').lower() : return '🎭 ずんだもん系'
        return '⚙️ カスタム'

    def create_new_character_action(self):
        dialog = CharacterEditDialog(self.root, self.character_manager, config_manager=self.config_manager)
        if dialog.result and dialog.result.get("action") == "created":
            self.refresh_character_list_display()
            self.log(f"✅ 新キャラクター '{dialog.result['name']}' を作成")

    def edit_selected_character(self):
        selection = self.char_tree.selection()
        if not selection: messagebox.showwarning("選択エラー", "編集するキャラクターを選択してください", parent=self.root); return
        char_id = selection[0]
        char_data = self.character_manager.config.get_character(char_id) # 修正
        if not char_data: messagebox.showerror("エラー", "キャラクターデータが見つかりません", parent=self.root); return
        dialog = CharacterEditDialog(self.root, self.character_manager, char_id, char_data, config_manager=self.config_manager)
        if dialog.result and dialog.result.get("action") == "edited":
            self.refresh_character_list_display()
            self.log(f"✏️ キャラクター '{dialog.result['name']}' を編集")

    def duplicate_selected_character(self):
        selection = self.char_tree.selection()
        if not selection: messagebox.showwarning("選択エラー", "複製するキャラクターを選択してください", parent=self.root); return
        source_char_id = selection[0]
        source_char_data = self.character_manager.config.get_character(source_char_id) # 修正
        if not source_char_data: messagebox.showerror("エラー", "複製元キャラクターデータが見つかりません", parent=self.root); return

        # CTkInputDialog を使用
        dialog = customtkinter.CTkInputDialog(text="新しいキャラクター名:", title="キャラクター複製")
        new_name = dialog.get_input() # .get_input()で値を取得

        if new_name: # Noneや空文字列でないことを確認
            try:
                new_char_data = json.loads(json.dumps(source_char_data))
                new_char_data['name'] = new_name
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
        if not selection: messagebox.showwarning("選択エラー", "削除するキャラクターを選択してください", parent=self.root); return
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
        if not selection: messagebox.showwarning("選択エラー", "エクスポートするキャラクターを選択してください", parent=self.root); return
        char_id = selection[0]
        char_data = self.character_manager.config.get_character(char_id) # 修正
        if not char_data: messagebox.showerror("エラー", "キャラクターデータが見つかりません", parent=self.root); return
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("JSONキャラクターファイル", "*.json")],
            initialfile=f"{char_data.get('name', 'character').replace(' ', '_')}.json",
            title="キャラクターをエクスポート", parent=self.root
        )
        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f: json.dump(char_data, f, ensure_ascii=False, indent=4)
                messagebox.showinfo("エクスポート完了", f"キャラクターを '{filepath}' に保存しました。", parent=self.root)
                self.log(f"📤 キャラクター '{char_data.get('name')}' をエクスポート: {filepath}")
            except Exception as e:
                messagebox.showerror("エクスポートエラー", f"エクスポート失敗: {e}", parent=self.root)

    def import_character_action(self):
        filepath = filedialog.askopenfilename(
            title="キャラクターJSONファイルを選択", filetypes=[("JSONファイル", "*.json")], parent=self.root
        )
        if not filepath: return
        try:
            with open(filepath, "r", encoding="utf-8") as f: imported_data = json.load(f)
            if not all(k in imported_data for k in ["name", "personality", "voice_settings"]):
                messagebox.showerror("インポートエラー", "ファイル形式が正しくありません。必須キーが不足しています。", parent=self.root); return
            if 'char_id' in imported_data: del imported_data['char_id']
            if 'created_at' in imported_data: del imported_data['created_at']
            if 'updated_at' in imported_data: del imported_data['updated_at']
            new_id = self.character_manager.create_character(
                name=imported_data.get('name', 'インポートされたキャラ'), custom_settings=imported_data
            )
            self.refresh_character_list_display()
            self.log(f"📥 キャラクター '{imported_data.get('name')}' (ID: {new_id}) をインポート")
            messagebox.showinfo("インポート完了", f"キャラクター '{imported_data.get('name')}' をインポートしました。", parent=self.root)
        except json.JSONDecodeError: messagebox.showerror("インポートエラー", "JSONファイルの解析に失敗しました。", parent=self.root)
        except Exception as e:
            messagebox.showerror("インポートエラー", f"インポート失敗: {e}", parent=self.root)
            self.log(f"❌ インポートエラー: {e}")

    def test_selected_character_voice(self):
        selection = self.char_tree.selection()
        if not selection: messagebox.showwarning("選択なし", "音声テストするキャラクターを選択してください。", parent=self.root); return
        char_id = selection[0]
        char_data = self.character_manager.config.get_character(char_id) # 修正
        if not char_data: messagebox.showerror("エラー", "キャラクターデータが見つかりません。", parent=self.root); return

        # CTkInputDialog を使用
        dialog = customtkinter.CTkInputDialog(text="テストするテキストを入力してください:", title="音声テスト")
        test_text = dialog.get_input()
        if not test_text: return

        self.log(f"🎤 キャラクター '{char_data['name']}' の音声テスト開始...")
        voice_settings = char_data.get('voice_settings', {})
        engine_choice = voice_settings.get('engine', self.config_manager.get_system_setting('voice_engine'))
        model_choice = voice_settings.get('model')
        speed_choice = voice_settings.get('speed', 1.0)
        api_key_google = self.config_manager.get_system_setting("google_ai_api_key")

        def run_test_async():
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            try:
                audio_player = AudioPlayer(config_manager=self.config_manager)
                voice_manager_local = VoiceEngineManager()
                audio_files = loop.run_until_complete(
                    voice_manager_local.synthesize_with_fallback(
                        test_text, model_choice, speed_choice, preferred_engine=engine_choice, api_key=api_key_google
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
            finally: loop.close()
        threading.Thread(target=run_test_async, daemon=True).start()

def main():
    customtkinter.set_appearance_mode("System")
    customtkinter.set_default_color_theme("blue")
    root = customtkinter.CTk()
    app = CharacterManagementWindow(root)
    root.mainloop()

if __name__ == "__main__":
    customtkinter.set_appearance_mode("System")
    customtkinter.set_default_color_theme("blue")
    main()
