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
import i18n_setup # 国際化対応
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CharacterEditDialog:
    def __init__(self, parent, character_manager, char_id=None, char_data=None, config_manager=None):
        i18n_setup.init_i18n() # 国際化設定の強制再初期化
        self._ = i18n_setup.get_translator() # 最新翻訳関数の取得

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
        title_key = "character_edit_dialog.title.edit" if self.is_edit_mode else "character_edit_dialog.title.create"
        self.dialog.title(self._(title_key)) #  + self._("character_edit_dialog.title.suffix_ctk") - CTk版サフィックスは削除
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
        customtkinter.CTkLabel(dialog_frame, text=self._("character_edit_dialog.label.name"), font=self.label_font).pack(anchor="w", padx=10, pady=(10,2))
        self.name_var = tk.StringVar()
        customtkinter.CTkEntry(dialog_frame, textvariable=self.name_var, width=300, font=self.default_font).pack(anchor="w", padx=10, pady=(0,10))

        if not self.is_edit_mode:
            template_outer_frame = customtkinter.CTkFrame(dialog_frame)
            template_outer_frame.pack(fill="x", padx=10, pady=10)
            customtkinter.CTkLabel(template_outer_frame, text=self._("character_edit_dialog.label.template_selection"), font=self.label_font).pack(anchor="w", padx=10, pady=(5,0))
            template_frame = customtkinter.CTkFrame(template_outer_frame)
            template_frame.pack(fill="x", padx=10, pady=5)

            # テンプレートの表示名は翻訳し、valueは元の日本語を維持（on_template_changedでの比較のため）
            self.template_var = tk.StringVar(value="最新AI系") # 初期値は日本語のまま
            templates_display = {
                "最新AI系": self._("character_edit_dialog.template.latest_ai"),
                "元気系": self._("character_edit_dialog.template.energetic"),
                "知的系": self._("character_edit_dialog.template.intelligent"),
                "癒し系": self._("character_edit_dialog.template.healing"),
                "ずんだもん系": self._("character_edit_dialog.template.zundamon"),
                "キャラクター系": self._("character_edit_dialog.template.character_type"),
                "プロ品質系": self._("character_edit_dialog.template.pro_quality"),
                "多言語対応系": self._("character_edit_dialog.template.multilingual"),
                "カスタム": self._("character_edit_dialog.template.custom")
            }
            template_values = list(templates_display.keys()) # valueは日本語キー

            template_grid = customtkinter.CTkFrame(template_frame, fg_color="transparent")
            template_grid.pack(fill="x")
            for i, template_key in enumerate(template_values):
                row, col = divmod(i, 2)
                rb = customtkinter.CTkRadioButton(template_grid, text=templates_display[template_key], variable=self.template_var, value=template_key, command=self.on_template_changed, font=self.default_font)
                rb.grid(row=row, column=col, sticky="w", padx=10, pady=3)

        personality_outer_frame = customtkinter.CTkFrame(dialog_frame)
        personality_outer_frame.pack(fill="x", padx=10, pady=10)
        customtkinter.CTkLabel(personality_outer_frame, text=self._("character_edit_dialog.label.personality_settings"), font=self.label_font).pack(anchor="w", padx=10, pady=(5,0))
        personality_frame = customtkinter.CTkFrame(personality_outer_frame)
        personality_frame.pack(fill="x", padx=10, pady=5)

        customtkinter.CTkLabel(personality_frame, text=self._("character_edit_dialog.label.base_tone"), font=self.default_font).pack(anchor="w", pady=(5,0))
        self.base_tone_var = tk.StringVar()
        customtkinter.CTkEntry(personality_frame, textvariable=self.base_tone_var, width=580, font=self.default_font).pack(fill="x", pady=2)
        customtkinter.CTkLabel(personality_frame, text=self._("character_edit_dialog.label.speech_style"), font=self.default_font).pack(anchor="w", pady=(10,0))
        self.speech_style_var = tk.StringVar()
        customtkinter.CTkEntry(personality_frame, textvariable=self.speech_style_var, width=580, font=self.default_font).pack(fill="x", pady=2)

        customtkinter.CTkLabel(personality_frame, text=self._("character_edit_dialog.label.character_traits"), font=self.default_font).pack(anchor="w", pady=(10,0))
        self.traits_text = customtkinter.CTkTextbox(personality_frame, height=100, width=580, font=self.default_font) # CTkTextbox
        self.traits_text.pack(fill="x", pady=2)
        customtkinter.CTkLabel(personality_frame, text=self._("character_edit_dialog.label.favorite_topics"), font=self.default_font).pack(anchor="w", pady=(10,0))
        self.topics_text = customtkinter.CTkTextbox(personality_frame, height=100, width=580, font=self.default_font) # CTkTextbox
        self.topics_text.pack(fill="x", pady=2)

        voice_outer_frame = customtkinter.CTkFrame(dialog_frame)
        voice_outer_frame.pack(fill="x", padx=10, pady=10)
        customtkinter.CTkLabel(voice_outer_frame, text=self._("character_edit_dialog.label.voice_settings"), font=self.label_font).pack(anchor="w", padx=10, pady=(5,0))
        voice_frame = customtkinter.CTkFrame(voice_outer_frame)
        voice_frame.pack(fill="x", padx=10, pady=5)

        customtkinter.CTkLabel(voice_frame, text=self._("character_edit_dialog.label.voice_engine"), font=self.default_font).pack(anchor="w")
        self.voice_engine_var = tk.StringVar(value="google_ai_studio_new") # valueは内部キーなのでそのまま
        engine_combo = customtkinter.CTkComboBox(voice_frame, variable=self.voice_engine_var,
                                   values=["google_ai_studio_new", "avis_speech", "voicevox", "system_tts"], # valueは内部キー
                                   state="readonly", width=580, font=self.default_font, command=self.on_engine_changed)
        engine_combo.pack(fill="x", pady=2)
        self.engine_info_label = customtkinter.CTkLabel(voice_frame, text="", text_color="gray", wraplength=500, font=self.default_font) # on_engine_changedで更新
        self.engine_info_label.pack(anchor="w", pady=2)

        customtkinter.CTkLabel(voice_frame, text=self._("character_edit_dialog.label.voice_model"), font=self.default_font).pack(anchor="w", pady=(10,0))
        self.voice_var = tk.StringVar()
        self.voice_combo = customtkinter.CTkComboBox(voice_frame, variable=self.voice_var, state="readonly", width=580, font=self.default_font) # update_voice_modelsで更新
        self.voice_combo.pack(fill="x", pady=2)

        speed_frame_inner = customtkinter.CTkFrame(voice_frame, fg_color="transparent")
        speed_frame_inner.pack(fill="x", pady=(10,0))
        customtkinter.CTkLabel(speed_frame_inner, text=self._("character_edit_dialog.label.speech_speed"), font=self.default_font).pack(side="left", padx=(0,10))
        self.speed_var = tk.DoubleVar(value=1.0)
        speed_slider = customtkinter.CTkSlider(speed_frame_inner, from_=0.5, to=2.0, variable=self.speed_var, width=300, command=lambda val: self.speed_label.configure(text=f"{val:.1f}"))
        speed_slider.pack(side="left", padx=10)
        self.speed_label = customtkinter.CTkLabel(speed_frame_inner, text="1.0", font=self.default_font)
        self.speed_label.pack(side="left", padx=5)

        quality_frame_inner = customtkinter.CTkFrame(voice_frame, fg_color="transparent")
        quality_frame_inner.pack(fill="x", pady=5)
        customtkinter.CTkLabel(quality_frame_inner, text=self._("character_edit_dialog.label.speech_quality"), font=self.default_font).pack(side="left", padx=(0,10))
        self.quality_var = tk.StringVar(value="標準") # valueは内部キーなのでそのまま
        quality_values_map = {"標準": self._("character_edit_dialog.quality.standard"), "高品質": self._("character_edit_dialog.quality.high")}
        # quality_combo = customtkinter.CTkComboBox(quality_frame_inner, variable=self.quality_var,
        #                             values=list(quality_values_map.values()), # 表示は翻訳後
        #                             state="readonly", width=150, font=self.default_font)
        # quality_varとComboBoxのvalueが異なるため、選択時に内部キーに変換する処理が必要になるが、今回はStringVarの値をそのまま使う
        # そのため、valuesも内部キーのままにして、表示は別途更新するか、StringVarに翻訳後の値をセットする必要がある。
        # ここではStringVarの値を内部キーとして扱い、表示は翻訳しない方針で一度進め、問題あれば修正する。
        # → やはり表示と内部値を分ける。StringVarには内部キー、ComboBoxのvaluesには表示名。
        # ただし、CTkComboBoxはvaluesを直接変更できないため、set_quality_optionsのようなメソッドを作るか、
        # __init__時に翻訳したリストを渡す必要がある。
        # 今回は元の実装に合わせて、StringVarには内部的な値 "標準" "高品質" を保持し、
        # ComboBoxのvaluesには翻訳されたものを表示するが、選択された値の取得はStringVarから行う。
        # そのため、ComboBoxのvaluesは表示用であり、選択された実際の値はStringVarが持つ内部値となる。
        # これにより、load_existing_dataでのセットやsave_characterでの保存は変更不要。
        # ただし、ComboBoxの初期表示とStringVarの初期値が一致している必要がある。
        # self.quality_var.set(self._("character_edit_dialog.quality.standard")) のように初期値を翻訳後のものにするか、
        # ComboBoxのvaluesに内部キーを渡し、textに翻訳関数を適用するような仕組みがあれば良いが、CTkにはない。
        # 簡潔にするため、valuesには内部キーを保持し、UI表示は英語圏ユーザーには英語の内部キーが見える形とするか、
        # __init__で翻訳したリストを生成して渡す。後者を採用。
        self.translated_quality_values = [self._("character_edit_dialog.quality.standard"), self._("character_edit_dialog.quality.high")]
        self.internal_quality_keys = ["標準", "高品質"] # 内部的なキー

        # quality_var の初期値は内部キー
        self.quality_var = tk.StringVar(value=self.internal_quality_keys[0]) # "標準"

        # ComboBoxの表示は翻訳された値、選択時にStringVarに内部キーをセットするコマンド
        def on_quality_select(choice):
            try:
                selected_index = self.translated_quality_values.index(choice)
                self.quality_var.set(self.internal_quality_keys[selected_index])
            except ValueError:
                pass # 翻訳された値が見つからない場合は何もしない

        quality_combo = customtkinter.CTkComboBox(quality_frame_inner,
                                    values=self.translated_quality_values, # 表示は翻訳後
                                    state="readonly", width=150, font=self.default_font,
                                    variable=tk.StringVar(value=self.translated_quality_values[self.internal_quality_keys.index(self.quality_var.get())]), # 初期表示
                                    command=on_quality_select)
        self.quality_combo_widget = quality_combo # インスタンス変数として保存
        self.quality_combo_widget.pack(side="left", padx=10)
        self.update_voice_models() # ここでエンジン情報ラベルも更新される

        response_outer_frame = customtkinter.CTkFrame(dialog_frame)
        response_outer_frame.pack(fill="x", padx=10, pady=10)
        customtkinter.CTkLabel(response_outer_frame, text=self._("character_edit_dialog.label.response_settings"), font=self.label_font).pack(anchor="w", padx=10, pady=(5,0))
        response_frame = customtkinter.CTkFrame(response_outer_frame)
        response_frame.pack(fill="x", padx=10, pady=5)

        resp_grid = customtkinter.CTkFrame(response_frame, fg_color="transparent")
        resp_grid.pack(fill="x")
        customtkinter.CTkLabel(resp_grid, text=self._("character_edit_dialog.label.response_length"), font=self.default_font).grid(row=0, column=0, sticky="w", padx=5, pady=5)
        # 応答長さも品質と同様の対応
        self.internal_response_length_keys = ["1文程度", "1-2文程度", "2-3文程度", "3-4文程度"]
        self.translated_response_length_values = [
            self._("character_edit_dialog.response_length.one_sentence"),
            self._("character_edit_dialog.response_length.one_to_two_sentences"),
            self._("character_edit_dialog.response_length.two_to_three_sentences"),
            self._("character_edit_dialog.response_length.three_to_four_sentences")
        ]
        self.response_length_var = tk.StringVar(value=self.internal_response_length_keys[1]) # "1-2文程度"

        def on_length_select(choice):
            try:
                selected_index = self.translated_response_length_values.index(choice)
                self.response_length_var.set(self.internal_response_length_keys[selected_index])
            except ValueError:
                pass

        length_combo = customtkinter.CTkComboBox(resp_grid,
                                   values=self.translated_response_length_values, state="readonly", font=self.default_font, width=150,
                                   variable=tk.StringVar(value=self.translated_response_length_values[self.internal_response_length_keys.index(self.response_length_var.get())]),
                                   command=on_length_select)
        self.length_combo_widget = length_combo # インスタンス変数として保存
        self.length_combo_widget.grid(row=0, column=1, padx=10, pady=5, sticky="w")

        customtkinter.CTkLabel(resp_grid, text=self._("character_edit_dialog.label.use_emojis"), font=self.default_font).grid(row=0, column=2, sticky="w", padx=(20,0), pady=5)
        self.emoji_var = tk.BooleanVar(value=True)
        customtkinter.CTkCheckBox(resp_grid, variable=self.emoji_var, text="", font=self.default_font).grid(row=0, column=3, padx=5, pady=5)

        customtkinter.CTkLabel(resp_grid, text=self._("character_edit_dialog.label.emotion_level"), font=self.default_font).grid(row=1, column=0, sticky="w", padx=5, pady=5)
        # 感情レベルも同様の対応
        self.internal_emotion_level_keys = ["控えめ", "普通", "高め", "超高め"]
        self.translated_emotion_level_values = [
            self._("character_edit_dialog.emotion_level.subtle"),
            self._("character_edit_dialog.emotion_level.normal"),
            self._("character_edit_dialog.emotion_level.high"),
            self._("character_edit_dialog.emotion_level.very_high")
        ]
        self.emotion_var = tk.StringVar(value=self.internal_emotion_level_keys[1]) # "普通"

        def on_emotion_select(choice):
            try:
                selected_index = self.translated_emotion_level_values.index(choice)
                self.emotion_var.set(self.internal_emotion_level_keys[selected_index])
            except ValueError:
                pass

        emotion_combo = customtkinter.CTkComboBox(resp_grid,
                                    values=self.translated_emotion_level_values, state="readonly", font=self.default_font, width=150,
                                    variable=tk.StringVar(value=self.translated_emotion_level_values[self.internal_emotion_level_keys.index(self.emotion_var.get())]),
                                    command=on_emotion_select)
        self.emotion_combo_widget = emotion_combo # インスタンス変数として保存
        self.emotion_combo_widget.grid(row=1, column=1, padx=10, pady=5, sticky="w")

        button_frame_bottom = customtkinter.CTkFrame(dialog_frame, fg_color="transparent")
        button_frame_bottom.pack(fill="x", padx=10, pady=20)
        button_text_key = "character_edit_dialog.button.update" if self.is_edit_mode else "character_edit_dialog.button.create"

        action_buttons_frame = customtkinter.CTkFrame(button_frame_bottom, fg_color="transparent")
        action_buttons_frame.pack(side="right")
        customtkinter.CTkButton(action_buttons_frame, text=self._(button_text_key), command=self.save_character, font=self.default_font).pack(side="left", padx=5)
        customtkinter.CTkButton(action_buttons_frame, text=self._("character_edit_dialog.button.cancel"), command=self.dialog.destroy, font=self.default_font).pack(side="left", padx=5)

        test_buttons_frame = customtkinter.CTkFrame(button_frame_bottom, fg_color="transparent")
        test_buttons_frame.pack(side="left")
        customtkinter.CTkButton(test_buttons_frame, text=self._("character_edit_dialog.button.test_voice"), command=self.test_voice, font=self.default_font).pack(side="left", padx=5)
        customtkinter.CTkButton(test_buttons_frame, text=self._("character_edit_dialog.button.compare_engines"), command=self.compare_voice_engines, font=self.default_font).pack(side="left", padx=5)

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

        # 品質設定の読み込み
        saved_quality_key = voice_settings.get('quality', self.internal_quality_keys[0])
        self.quality_var.set(saved_quality_key)
        if hasattr(self, 'quality_combo_widget') and saved_quality_key in self.internal_quality_keys:
             self.quality_combo_widget.set(self.translated_quality_values[self.internal_quality_keys.index(saved_quality_key)])

        response_settings = self.char_data.get('response_settings', {})
        # 応答長さ設定の読み込み
        saved_length_key = response_settings.get('max_length', self.internal_response_length_keys[1])
        self.response_length_var.set(saved_length_key)
        if hasattr(self, 'length_combo_widget') and saved_length_key in self.internal_response_length_keys:
            self.length_combo_widget.set(self.translated_response_length_values[self.internal_response_length_keys.index(saved_length_key)])

        self.emoji_var.set(response_settings.get('use_emojis', True))

        # 感情レベル設定の読み込み
        saved_emotion_key = response_settings.get('emotion_level', self.internal_emotion_level_keys[1])
        self.emotion_var.set(saved_emotion_key)
        if hasattr(self, 'emotion_combo_widget') and saved_emotion_key in self.internal_emotion_level_keys:
            self.emotion_combo_widget.set(self.translated_emotion_level_values[self.internal_emotion_level_keys.index(saved_emotion_key)])

    # _find_widget_by_class は不要になったので削除

    def on_template_changed(self, event=None): # CTkRadioButtonのcommandはeventを渡さない
        selected_template_name = self.template_var.get() # ここは内部キー(日本語)のまま
        if selected_template_name == "カスタム": # 内部キーで比較
            self.base_tone_var.set(""); self.speech_style_var.set("")
            self.traits_text.delete("1.0", "end"); self.topics_text.delete("1.0", "end")
            self.voice_engine_var.set("google_ai_studio_new"); self.update_voice_models()
            self.speed_var.set(1.0)

            self.quality_var.set(self.internal_quality_keys[0]) # "標準"
            if hasattr(self, 'quality_combo_widget'): self.quality_combo_widget.set(self.translated_quality_values[0])

            self.response_length_var.set(self.internal_response_length_keys[1]) # "1-2文程度"
            if hasattr(self, 'length_combo_widget'): self.length_combo_widget.set(self.translated_response_length_values[1])

            self.emoji_var.set(True)
            self.emotion_var.set(self.internal_emotion_level_keys[1]) # "普通"
            if hasattr(self, 'emotion_combo_widget'): self.emotion_combo_widget.set(self.translated_emotion_level_values[1])
            return

        template_data = self.character_manager.character_templates.get(selected_template_name)
        if not template_data: return

        # テンプレート適用時も同様に StringVar と ComboBox表示を更新
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

        template_quality_key = voice_settings.get("quality", self.internal_quality_keys[0])
        self.quality_var.set(template_quality_key)
        if hasattr(self, 'quality_combo_widget') and template_quality_key in self.internal_quality_keys:
             self.quality_combo_widget.set(self.translated_quality_values[self.internal_quality_keys.index(template_quality_key)])

        response_settings = template_data.get("response_settings", {})
        template_length_key = response_settings.get("max_length", self.internal_response_length_keys[1])
        self.response_length_var.set(template_length_key)
        if hasattr(self, 'length_combo_widget') and template_length_key in self.internal_response_length_keys:
            self.length_combo_widget.set(self.translated_response_length_values[self.internal_response_length_keys.index(template_length_key)])

        self.emoji_var.set(response_settings.get("use_emojis", True))
        template_emotion_key = response_settings.get("emotion_level", self.internal_emotion_level_keys[1])
        self.emotion_var.set(template_emotion_key)
        if hasattr(self, 'emotion_combo_widget') and template_emotion_key in self.internal_emotion_level_keys:
            self.emotion_combo_widget.set(self.translated_emotion_level_values[self.internal_emotion_level_keys.index(template_emotion_key)])

    def on_engine_changed(self, choice=None): # CTkComboBoxのcommandは選択値を渡す
        self.update_voice_models()

    def update_voice_models(self):
        engine_choice = self.voice_engine_var.get()
        voices = []
        default_voice = ""
        # エンジン情報の翻訳キーをここで設定
        engine_info_key_map = {
            "google_ai_studio_new": "character_edit_dialog.engine_info.google_ai_studio_new",
            "avis_speech": "character_edit_dialog.engine_info.avis_speech",
            "voicevox": "character_edit_dialog.engine_info.voicevox",
            "system_tts": "character_edit_dialog.engine_info.system_tts"
        }
        info_text = self._(engine_info_key_map.get(engine_choice, "")) # 見つからない場合は空文字

        api_instance = None

        if engine_choice == "google_ai_studio_new": api_instance = GoogleAIStudioNewVoiceAPI()
        elif engine_choice == "avis_speech": api_instance = AvisSpeechEngineAPI()
        elif engine_choice == "voicevox": api_instance = VOICEVOXEngineAPI()
        elif engine_choice == "system_tts": api_instance = SystemTTSAPI()

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
                voices = [self._("character_edit_dialog.voice_model.error")]; default_voice = self._("character_edit_dialog.voice_model.error")
                info_text += self._("character_edit_dialog.engine_info.list_error_suffix")
        else:
            voices = [self._("character_edit_dialog.voice_model.na")]
            default_voice = self._("character_edit_dialog.voice_model.na")

        self.voice_combo.configure(values=voices if voices else [self._("character_edit_dialog.voice_model.no_options")]) # .configureで更新
        if voices:
            current_selection = self.voice_var.get()
            if current_selection and current_selection in voices: self.voice_var.set(current_selection)
            else: self.voice_var.set(default_voice)
        else:
            self.voice_var.set(self._("character_edit_dialog.voice_model.no_options") if not voices else "")
        self.engine_info_label.configure(text=info_text) # .configureで更新

    def _get_api_key(self, key_name):
        if self.config_manager: return self.config_manager.get_system_setting(key_name, "")
        elif hasattr(self.parent, 'config') and hasattr(self.parent.config, 'get_system_setting'): # parentはCTkインスタンスのはず
             # CharacterManagementWindowがself.configを持つ想定
            if hasattr(self.parent, 'config_manager_instance'): # 仮の属性名
                return self.parent.config_manager_instance.get_system_setting(key_name, "")
        logger.warning(self._("character_edit_dialog.log.api_key_fetch_failed", key_name=key_name))
        return ""

    def test_voice(self):
        name_or_test = self.name_var.get() or self._("character_edit_dialog.voice_test.default_name_for_test") # "テスト"部分も翻訳対象にする場合
        text = self._("character_edit_dialog.voice_test.text", name_or_test=name_or_test)
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
                    # logger.info(f"Voice test successful: {voice_engine_choice}/{voice_model_choice}") # 英語ログはそのまま
                else:
                    # logger.error(f"Voice test failed: {voice_engine_choice}/{voice_model_choice}") # 英語ログはそのまま
                    messagebox.showerror(self._("character_edit_dialog.messagebox.voice_test_failed.title"),
                                         self._("character_edit_dialog.messagebox.voice_test_failed.message_generation"), parent=self.dialog)
            except Exception as e:
                # logger.error(f"Voice test error: {e}", exc_info=True) # 英語ログはそのまま
                messagebox.showerror(self._("character_edit_dialog.messagebox.voice_test_error.title"),
                                     self._("character_edit_dialog.messagebox.voice_test_error.message_generic", error=e), parent=self.dialog)
            finally: loop.close()
        threading.Thread(target=run_test_async, daemon=True).start()

    def compare_voice_engines(self):
        name_or_test = self.name_var.get() or self._("character_edit_dialog.voice_test.default_name_for_test") # "テスト"部分
        base_text = self._("character_edit_dialog.engine_comparison.text", name_or_test=name_or_test)
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

                    # logger.info(f"Comparing engine {i}: {engine_name} with model {model_to_use}") # 英語ログ
                    test_text_engine = self._("character_edit_dialog.engine_comparison.text_per_engine",
                                              i=i, engine_name=engine_name, model_to_use=model_to_use, text=base_text)
                    audio_files = loop.run_until_complete(
                        voice_manager_local.synthesize_with_fallback(
                            test_text_engine, model_to_use, 1.0, preferred_engine=engine_name, api_key=api_key_google
                        )
                    )
                    if audio_files:
                        loop.run_until_complete(audio_player.play_audio_files(audio_files))
                        # logger.info(f"Comparison for {engine_name} successful.") # 英語ログ
                    # else: logger.error(f"Comparison for {engine_name} failed.") # 英語ログ
                    time.sleep(1)
                # logger.info("Voice engine comparison finished.") # 英語ログ
            except Exception as e:
                # logger.error(f"Voice engine comparison error: {e}", exc_info=True) # 英語ログ
                messagebox.showerror(self._("character_edit_dialog.messagebox.comparison_error.title"),
                                     self._("character_edit_dialog.messagebox.comparison_error.message_generic", error=e), parent=self.dialog)
            finally: loop.close()
        threading.Thread(target=run_comparison_async, daemon=True).start()

    def save_character(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning(self._("character_edit_dialog.messagebox.error.title"),
                                 self._("character_edit_dialog.messagebox.error.name_required"), parent=self.dialog)
            return
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
            action_key = "character_edit_dialog.action.edit" if self.is_edit_mode else "character_edit_dialog.action.create"
            action_str_translated = self._(action_key)
            # logger.error(f"Character {action_str_translated} failed: {e}", exc_info=True) # ログは英語のままか、別途翻訳キーを用意
            messagebox.showerror(self._("character_edit_dialog.messagebox.error.title"),
                                 self._("character_edit_dialog.messagebox.error.save_failed", action=action_str_translated, error=e),
                                 parent=self.dialog)

class CharacterManagementWindow:
    def __init__(self, root: customtkinter.CTk):
        i18n_setup.init_i18n()
        self._ = i18n_setup.get_translator()

        self.root = root
        self.root.title(self._("character_manager.title"))
        self.root.geometry("950x750")

        self.loading_label = customtkinter.CTkLabel(self.root, text=self._("character_manager.loading"), font=("Yu Gothic UI", 18))
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
        self.log(self._("character_manager.log.initialized"))


    def log(self, message):
        # CharacterManagementWindow の log メソッドはUIウィジェットに書き込まない
        logger.info(message) # ログ出力は翻訳しないことが多いが、必要なら self._() を使う

    def create_widgets(self):
        # メインフレーム
        main_frame = customtkinter.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # キャラクターリスト表示フレーム (CTkFrame + CTkLabel)
        list_outer_frame = customtkinter.CTkFrame(main_frame)
        list_outer_frame.pack(fill="both", expand=True, padx=5, pady=5)
        customtkinter.CTkLabel(list_outer_frame, text=self._("character_manager.label.character_list"), font=self.label_font).pack(anchor="w", padx=10, pady=(5,0))
        list_frame = customtkinter.CTkFrame(list_outer_frame)
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # ttk.Treeview はそのまま使用、スタイル調整
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview.Heading", font=(self.treeview_font[0], self.treeview_font[1], "bold"))
        style.configure("Treeview", font=self.treeview_font, rowheight=int(self.treeview_font[1]*2.0))

        self.char_tree = ttk.Treeview(list_frame, columns=('name', 'type', 'voice', 'engine', 'created'), show='headings', style="Treeview")
        self.char_tree.heading('name', text=self._("character_manager.tree.header.name"))
        self.char_tree.heading('type', text=self._("character_manager.tree.header.type"))
        self.char_tree.heading('voice', text=self._("character_manager.tree.header.voice_model"))
        self.char_tree.heading('engine', text=self._("character_manager.tree.header.voice_engine"))
        self.char_tree.heading('created', text=self._("character_manager.tree.header.created_at"))
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
        customtkinter.CTkButton(buttons_row1, text=self._("character_manager.button.create_new"), command=self.create_new_character_action, font=self.default_font).pack(side="left", padx=5)
        customtkinter.CTkButton(buttons_row1, text=self._("character_manager.button.edit"), command=self.edit_selected_character, font=self.default_font).pack(side="left", padx=5)
        customtkinter.CTkButton(buttons_row1, text=self._("character_manager.button.duplicate"), command=self.duplicate_selected_character, font=self.default_font).pack(side="left", padx=5)
        customtkinter.CTkButton(buttons_row1, text=self._("character_manager.button.delete"), command=self.delete_selected_character, font=self.default_font).pack(side="left", padx=5)

        buttons_row2 = customtkinter.CTkFrame(char_buttons_frame, fg_color="transparent")
        buttons_row2.pack(fill="x", pady=2)
        customtkinter.CTkButton(buttons_row2, text=self._("character_manager.button.export"), command=self.export_selected_character, font=self.default_font).pack(side="left", padx=5)
        customtkinter.CTkButton(buttons_row2, text=self._("character_manager.button.import"), command=self.import_character_action, font=self.default_font).pack(side="left", padx=5)
        customtkinter.CTkButton(buttons_row2, text=self._("character_manager.button.test_voice_selected"), command=self.test_selected_character_voice, font=self.default_font).pack(side="left", padx=5)

        # テンプレート情報表示 (CTkTextboxを使用)
        template_outer_frame = customtkinter.CTkFrame(main_frame)
        template_outer_frame.pack(fill="x", padx=5, pady=5)
        customtkinter.CTkLabel(template_outer_frame, text=self._("character_manager.label.template_list_v2_2"), font=self.label_font).pack(anchor="w", padx=10, pady=(5,0))
        template_display_frame = customtkinter.CTkFrame(template_outer_frame)
        template_display_frame.pack(fill="x", padx=5, pady=5)

        template_info_text = customtkinter.CTkTextbox(template_display_frame, height=180, width=100, wrap="word", font=self.default_font) # CTkTextbox
        template_info_text.pack(fill="both", expand=True, padx=5, pady=5)

        # テンプレート内容は翻訳されたものを挿入
        template_info_text.insert("1.0", self._("character_manager.template_info.content").strip())
        template_info_text.configure(state="disabled") # 編集不可に

    def refresh_character_list_display(self):
        self.char_tree.delete(*self.char_tree.get_children())
        characters = self.character_manager.get_all_characters()
        for char_id, data in characters.items():
            self.char_tree.insert('', 'end', iid=char_id, values=(
                data.get('name', self._("character_manager.unknown_char_name_fallback")),
                self._estimate_character_type(data), # _estimate_character_type で翻訳
                data.get('voice_settings', {}).get('model', 'N/A'),
                data.get('voice_settings', {}).get('engine', 'N/A'),
                data.get('created_at', 'N/A')
            ))
        self.log(self._("character_manager.log.list_refreshed", count=len(characters)))

    def _estimate_character_type(self, char_data):
        # 内部的な比較は元の日本語で行い、表示する文字列のみ翻訳する
        tone = char_data.get('personality', {}).get('base_tone', '').lower()
        name_lower = char_data.get('name','').lower()
        if '元気' in tone or '明るい' in tone: return self._('character_manager.type.energetic')
        if '知的' in tone or '落ち着いた' in tone: return self._('character_manager.type.intelligent')
        if '癒し' in tone or '穏やか' in tone: return self._('character_manager.type.healing')
        if 'ずんだもん' in name_lower : return self._('character_manager.type.zundamon')
        return self._('character_manager.type.custom')

    def create_new_character_action(self):
        dialog = CharacterEditDialog(self.root, self.character_manager, config_manager=self.config_manager)
        if dialog.result and dialog.result.get("action") == "created":
            self.refresh_character_list_display()
            self.log(self._("character_manager.log.character_created", name=dialog.result['name']))

    def edit_selected_character(self):
        selection = self.char_tree.selection()
        if not selection:
            messagebox.showwarning(self._("character_manager.messagebox.selection_error.title"),
                                 self._("character_manager.messagebox.selection_error.message_edit"), parent=self.root)
            return
        char_id = selection[0]
        char_data = self.character_manager.config.get_character(char_id)
        if not char_data:
            messagebox.showerror(self._("character_manager.messagebox.error.title"),
                                 self._("character_manager.messagebox.error.char_data_not_found"), parent=self.root)
            return
        dialog = CharacterEditDialog(self.root, self.character_manager, char_id, char_data, config_manager=self.config_manager)
        if dialog.result and dialog.result.get("action") == "edited":
            self.refresh_character_list_display()
            self.log(self._("character_manager.log.character_edited", name=dialog.result['name']))

    def duplicate_selected_character(self):
        selection = self.char_tree.selection()
        if not selection:
            messagebox.showwarning(self._("character_manager.messagebox.selection_error.title"),
                                 self._("character_manager.messagebox.selection_error.message_duplicate"), parent=self.root)
            return
        source_char_id = selection[0]
        source_char_data = self.character_manager.config.get_character(source_char_id)
        if not source_char_data:
            messagebox.showerror(self._("character_manager.messagebox.error.title"),
                                 self._("character_manager.messagebox.error.source_char_data_not_found"), parent=self.root)
            return

        dialog = customtkinter.CTkInputDialog(text=self._("character_manager.input_dialog.duplicate_character.text"),
                                            title=self._("character_manager.input_dialog.duplicate_character.title"))
        new_name = dialog.get_input()

        if new_name:
            try:
                new_char_data = json.loads(json.dumps(source_char_data))
                new_char_data['name'] = new_name
                if 'char_id' in new_char_data: del new_char_data['char_id']
                if 'created_at' in new_char_data: del new_char_data['created_at']
                if 'updated_at' in new_char_data: del new_char_data['updated_at']
                new_id = self.character_manager.create_character(name=new_name, custom_settings=new_char_data)
                self.refresh_character_list_display()
                self.log(self._("character_manager.log.character_duplicated", name=new_name, id=new_id))
            except Exception as e:
                messagebox.showerror(self._("character_manager.messagebox.duplicate_error.title"),
                                     self._("character_manager.messagebox.duplicate_error.message", error=e), parent=self.root)
                self.log(self._("character_manager.log.duplicate_error", error=e))

    def delete_selected_character(self):
        selection = self.char_tree.selection()
        if not selection:
            messagebox.showwarning(self._("character_manager.messagebox.selection_error.title"),
                                 self._("character_manager.messagebox.selection_error.message_delete"), parent=self.root)
            return
        char_id = selection[0]
        char_name = self.char_tree.item(char_id, 'values')[0]
        if messagebox.askyesno(self._("character_manager.messagebox.delete_confirm.title"),
                               self._("character_manager.messagebox.delete_confirm.message", char_name=char_name), parent=self.root):
            if self.character_manager.delete_character(char_id):
                self.refresh_character_list_display()
                self.log(self._("character_manager.log.character_deleted", char_name=char_name))
            else:
                messagebox.showerror(self._("character_manager.messagebox.delete_error.title"),
                                     self._("character_manager.messagebox.delete_error.message"), parent=self.root)

    def export_selected_character(self):
        selection = self.char_tree.selection()
        if not selection:
            messagebox.showwarning(self._("character_manager.messagebox.selection_error.title"),
                                 self._("character_manager.messagebox.selection_error.message_export"), parent=self.root)
            return
        char_id = selection[0]
        char_data = self.character_manager.config.get_character(char_id)
        if not char_data:
            messagebox.showerror(self._("character_manager.messagebox.error.title"),
                                 self._("character_manager.messagebox.error.char_data_not_found"), parent=self.root)
            return
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[(self._("character_manager.filedialog.export_character.filetype"), "*.json")],
            initialfile=f"{char_data.get('name', self._('character_manager.default_export_char_filename')).replace(' ', '_')}.json",
            title=self._("character_manager.filedialog.export_character.title"), parent=self.root
        )
        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f: json.dump(char_data, f, ensure_ascii=False, indent=4)
                messagebox.showinfo(self._("character_manager.messagebox.export_complete.title"),
                                    self._("character_manager.messagebox.export_complete.message", filepath=filepath), parent=self.root)
                self.log(self._("character_manager.log.character_exported", name=char_data.get('name'), filepath=filepath))
            except Exception as e:
                messagebox.showerror(self._("character_manager.messagebox.export_error.title"),
                                     self._("character_manager.messagebox.export_error.message", error=e), parent=self.root)

    def import_character_action(self):
        filepath = filedialog.askopenfilename(
            title=self._("character_manager.filedialog.import_character.title"),
            filetypes=[(self._("character_manager.filedialog.import_character.filetype"), "*.json")], parent=self.root # settingsと共通化も検討
        )
        if not filepath: return
        try:
            with open(filepath, "r", encoding="utf-8") as f: imported_data = json.load(f)
            if not all(k in imported_data for k in ["name", "personality", "voice_settings"]):
                messagebox.showerror(self._("character_manager.messagebox.import_error.title"),
                                     self._("character_manager.messagebox.import_error.message_format"), parent=self.root)
                return
            if 'char_id' in imported_data: del imported_data['char_id']
            if 'created_at' in imported_data: del imported_data['created_at']
            if 'updated_at' in imported_data: del imported_data['updated_at']
            new_id = self.character_manager.create_character(
                name=imported_data.get('name', self._("character_manager.default_imported_char_name", default="Imported Character")), # デフォルト名も翻訳
                custom_settings=imported_data
            )
            self.refresh_character_list_display()
            self.log(self._("character_manager.log.character_imported", name=imported_data.get('name'), id=new_id))
            messagebox.showinfo(self._("character_manager.messagebox.import_complete.title"),
                                self._("character_manager.messagebox.import_complete.message", name=imported_data.get('name')), parent=self.root)
        except json.JSONDecodeError:
            messagebox.showerror(self._("character_manager.messagebox.import_error.title"),
                                 self._("character_manager.messagebox.import_error.message_json_decode"), parent=self.root)
        except Exception as e:
            messagebox.showerror(self._("character_manager.messagebox.import_error.title"),
                                 self._("character_manager.messagebox.import_error.message_generic", error=e), parent=self.root)
            self.log(self._("character_manager.log.import_error", error=e))

    def test_selected_character_voice(self):
        selection = self.char_tree.selection()
        if not selection:
            messagebox.showwarning(self._("character_manager.messagebox.no_selection.title"),
                                 self._("character_manager.messagebox.no_selection.message_test_voice"), parent=self.root)
            return
        char_id = selection[0]
        char_data = self.character_manager.config.get_character(char_id)
        if not char_data:
            messagebox.showerror(self._("character_manager.messagebox.error.title"),
                                 self._("character_manager.messagebox.error.char_data_not_found"), parent=self.root)
            return

        dialog = customtkinter.CTkInputDialog(text=self._("character_manager.input_dialog.voice_test.text"),
                                            title=self._("character_manager.input_dialog.voice_test.title"))
        test_text = dialog.get_input()
        if not test_text: return

        self.log(self._("character_manager.log.voice_test_start", name=char_data['name']))
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
                    self.log(self._("character_manager.log.voice_test_success", name=char_data['name']))
                else:
                    self.log(self._("character_manager.log.voice_test_failed", name=char_data['name']))
                    messagebox.showerror(self._("character_manager.messagebox.voice_test_failed.title"),
                                         self._("character_manager.messagebox.voice_test_failed.message_generation"), parent=self.root)
            except Exception as e:
                self.log(self._("character_manager.log.voice_test_error", error=e))
                messagebox.showerror(self._("character_manager.messagebox.voice_test_error.title"),
                                     self._("character_manager.messagebox.voice_test_error.message_generic", error=e), parent=self.root)
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
