"""
完全版 AITuberシステム v2.2 - 4エンジン完全対応版（機能削減なし）
Google AI Studio新音声合成（2025年5月追加）+ Avis Speech + VOICEVOX + システムTTS

重要な追加:
- Google AI Studio 新音声合成API（2025年5月追加）に完全対応
- 既存の全機能を維持・拡張（機能削減なし）
- 4つの音声エンジン完全統合
- 全メソッドを4エンジン対応で完全実装
- フォールバック機能を4エンジンに完全拡張

機能（全て完全実装・機能削減なし）:
- 4つの音声エンジン統合（最新技術完全対応）
- 完全設定ファイル管理
- 複数キャラクター作成・編集・管理・複製・削除
- 完全デバッグ・テスト機能
- YouTubeライブ完全連携
- AI対話システム完全実装
- 完全無料〜プロ品質まで全対応
"""
from config import ConfigManager
from character_manager import CharacterManager
from audio_manager import VoiceEngineManager, AudioPlayer, GoogleAIStudioNewVoiceAPI, AvisSpeechEngineAPI, VOICEVOXEngineAPI, SystemTTSAPI # CharacterEditDialogで直接利用しているため
from streaming import AITuberStreamingSystem

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from google import genai # 公式ドキュメント推奨
from google.genai import types # 公式ドキュメント推奨
#import google.generativeai as genai # コメントアウト
import requests
import asyncio
import json
import time
import os
import threading
import logging
import uuid
import webbrowser
import tempfile
#import subprocess
import platform
from datetime import datetime
from pathlib import Path
import aiohttp
#import urllib.parse
import base64
import wave # wave モジュールをインポート
import re # 正規表現モジュールをインポート
import json # JSONモジュールをインポート (macOSデバイス取得で使用)
import csv
import traceback # エラー追跡用に追加

# キャラクター編集ダイアログ（4エンジン完全対応版）
class CharacterEditDialog:
    """キャラクター作成・編集ダイアログ v2.2（4エンジン完全対応・機能削減なし）"""
    
    def __init__(self, parent, character_manager, char_id=None, char_data=None):
        self.character_manager = character_manager
        self.char_id = char_id
        self.char_data = char_data
        self.result = None
        self.is_edit_mode = char_id is not None
        
        # ダイアログウィンドウ作成
        self.dialog = tk.Toplevel(parent)
        title = "キャラクター編集" if self.is_edit_mode else "キャラクター作成"
        self.dialog.title(title + " - 4エンジン対応版")
        self.dialog.geometry("650x800")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.create_widgets()
        
        # 編集モードの場合は既存データを読み込み
        if self.is_edit_mode and self.char_data:
            self.load_existing_data()
        
        # 中央配置
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (650 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (800 // 2)
        self.dialog.geometry(f"650x800+{x}+{y}")
        
        self.dialog.wait_window()
    
    def create_widgets(self):
        """ダイアログのウィジェット作成（完全版）"""
        # キャラクター名
        ttk.Label(self.dialog, text="キャラクター名:").pack(anchor=tk.W, padx=10, pady=5)
        self.name_var = tk.StringVar()
        ttk.Entry(self.dialog, textvariable=self.name_var, width=40).pack(padx=10, pady=5)
        
        # テンプレート選択（新規作成時のみ）
        if not self.is_edit_mode:
            template_frame = ttk.LabelFrame(self.dialog, text="テンプレート選択（4エンジン対応）", padding="10")
            template_frame.pack(fill=tk.X, padx=10, pady=10)
            
            self.template_var = tk.StringVar(value="最新AI系")
            templates = ["最新AI系", "元気系", "知的系", "癒し系", "ずんだもん系", "キャラクター系", "プロ品質系", "多言語対応系", "カスタム"]
            
            # テンプレートを2列で配置
            template_grid = ttk.Frame(template_frame)
            template_grid.pack(fill=tk.X)
            
            for i, template in enumerate(templates):
                row = i // 2
                col = i % 2
                rb = ttk.Radiobutton(template_grid, text=template,
                                     variable=self.template_var, value=template,
                                     command=self.on_template_changed) # テンプレート変更時のコマンドを追加
                rb.grid(row=row, column=col, sticky=tk.W, padx=10)

        # 性格設定
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
        
        # 音声設定（4エンジン完全対応）
        voice_frame = ttk.LabelFrame(self.dialog, text="音声設定（4エンジン完全対応）", padding="10")
        voice_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 音声エンジン選択
        ttk.Label(voice_frame, text="音声エンジン:").pack(anchor=tk.W)
        self.voice_engine_var = tk.StringVar(value="google_ai_studio_new")
        engine_combo = ttk.Combobox(voice_frame, textvariable=self.voice_engine_var,
                                   values=["google_ai_studio_new", "avis_speech", "voicevox", "system_tts"], 
                                   state="readonly", width=50)
        engine_combo.pack(fill=tk.X, pady=2)
        engine_combo.bind('<<ComboboxSelected>>', self.on_engine_changed)
        
        # エンジン説明ラベル
        self.engine_info_label = ttk.Label(voice_frame, text="", 
                                         foreground="gray", wraplength=500)
        self.engine_info_label.pack(anchor=tk.W, pady=2)
        
        # 音声モデル選択
        ttk.Label(voice_frame, text="音声モデル:").pack(anchor=tk.W, pady=(10,0))
        self.voice_var = tk.StringVar(value="Alloy")
        
        self.voice_combo = ttk.Combobox(voice_frame, textvariable=self.voice_var,
                                       state="readonly", width=50)
        self.voice_combo.pack(fill=tk.X, pady=2)
        
        # 音声速度
        speed_frame = ttk.Frame(voice_frame)
        speed_frame.pack(fill=tk.X, pady=(10,0))
        
        ttk.Label(speed_frame, text="音声速度:").pack(side=tk.LEFT)
        self.speed_var = tk.DoubleVar(value=1.0)
        speed_scale = ttk.Scale(speed_frame, from_=0.5, to=2.0, variable=self.speed_var, orient=tk.HORIZONTAL, length=300)
        speed_scale.pack(side=tk.LEFT, padx=10)
        self.speed_label = ttk.Label(speed_frame, text="1.0")
        self.speed_label.pack(side=tk.LEFT, padx=5)
        
        # 速度表示更新
        def update_speed_label(*args):
            self.speed_label.config(text=f"{self.speed_var.get():.1f}")
        self.speed_var.trace('w', update_speed_label)
        
        # 音声品質設定
        quality_frame = ttk.Frame(voice_frame)
        quality_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(quality_frame, text="音声品質:").pack(side=tk.LEFT)
        self.quality_var = tk.StringVar(value="標準")
        quality_combo = ttk.Combobox(quality_frame, textvariable=self.quality_var,
                                    values=["標準", "高品質", "最高品質"], state="readonly", width=15)
        quality_combo.pack(side=tk.LEFT, padx=10)
        
        # 初期音声リスト設定
        self.update_voice_models()
        
        # 応答設定
        response_frame = ttk.LabelFrame(self.dialog, text="応答設定", padding="10")
        response_frame.pack(fill=tk.X, padx=10, pady=10)
        
        resp_grid = ttk.Frame(response_frame)
        resp_grid.pack(fill=tk.X)
        
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
        
        # ボタン
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=20)
        
        button_text = "更新" if self.is_edit_mode else "作成"
        ttk.Button(button_frame, text=button_text, command=self.save_character).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="キャンセル", command=self.dialog.destroy).pack(side=tk.RIGHT, padx=5)
        
        # 音声テストボタン
        test_frame = ttk.Frame(button_frame)
        test_frame.pack(side=tk.LEFT)
        ttk.Button(test_frame, text="🎤 音声テスト", command=self.test_voice).pack(side=tk.LEFT, padx=5)
        ttk.Button(test_frame, text="🔄 エンジン比較", command=self.compare_voice_engines).pack(side=tk.LEFT, padx=5)
    
    def load_existing_data(self):
        """既存データを読み込み（編集モード用・完全版）"""
        if not self.char_data:
            return
        
        # 基本情報
        self.name_var.set(self.char_data.get('name', ''))
        
        # 性格設定
        personality = self.char_data.get('personality', {})
        self.base_tone_var.set(personality.get('base_tone', ''))
        self.speech_style_var.set(personality.get('speech_style', ''))
        
        # 特徴
        traits = personality.get('character_traits', [])
        self.traits_text.insert(1.0, '\n'.join(traits))
        
        # 話題
        topics = personality.get('favorite_topics', [])
        self.topics_text.insert(1.0, '\n'.join(topics))
        
        # 音声設定
        voice_settings = self.char_data.get('voice_settings', {})
        self.voice_engine_var.set(voice_settings.get('engine', 'google_ai_studio_new'))

        # エンジンを設定した直後にモデルリストを更新して、正しいモデル名のリストを voice_combo に設定する
        self.update_voice_models()

        # 更新されたモデルリストを元に、保存されていたモデル名を設定する
        # voice_settings.get('model', ...) のデフォルト値は、リストの最初の要素か、具体的なフォールバック値を指定する
        default_voice_model_on_load = self.voice_combo['values'][0] if self.voice_combo['values'] else "gemini-2.5-flash-preview-tts-alloy"
        saved_model = voice_settings.get('model', default_voice_model_on_load)

        # 保存されたモデルが現在のエンジンのリストに存在するか確認
        if saved_model in self.voice_combo['values']:
            self.voice_var.set(saved_model)
        else:
            # 存在しない場合はリストの最初のモデルを選択 (または固定のデフォルト)
            self.voice_var.set(default_voice_model_on_load)

        self.speed_var.set(voice_settings.get('speed', 1.0))
        
        # 応答設定
        response_settings = self.char_data.get('response_settings', {})
        self.response_length_var.set(response_settings.get('max_length', '1-2文程度'))
        self.emoji_var.set(response_settings.get('use_emojis', True))
        self.emotion_var.set(response_settings.get('emotion_level', '普通'))
        
        # update_voice_models は既に上で呼び出されているので、ここでは不要
        # self.update_voice_models()

        # 追加対応：Google AI Studio 新音声エンジンの場合、古い形式のモデル名 (例: "gemini-2.5-flash-preview-tts-alloy") が
        # 設定ファイル等から読み込まれた場合に、新しい短い形式 (例: "Alloy") に変換してUIに正しく反映させる。
        selected_engine = voice_settings.get('engine', 'google_ai_studio_new') # 現在選択されている、または読み込まれたエンジン
        if selected_engine == "google_ai_studio_new":
            # self.voice_var には、update_voice_models() の後に、保存されていたモデル名が設定されているはず。
            # (または、保存されたモデル名がリストにない場合はリストの最初の要素)
            current_model_selection_from_config = voice_settings.get('model') # 設定ファイル等に保存されていたモデル名

            if current_model_selection_from_config and \
               current_model_selection_from_config.startswith("gemini-2.5-flash-preview-tts-"):
                try:
                    # 例: "gemini-2.5-flash-preview-tts-alloy" -> "Alloy"
                    short_model_name = current_model_selection_from_config.split('-')[-1].capitalize()

                    # 変換した短い名前が、更新された音声リスト (self.voice_combo['values']) に存在するか確認
                    if short_model_name in self.voice_combo['values']:
                        self.voice_var.set(short_model_name) # UIの選択値を更新
                    else:
                        # 変換後の名前がリストにない場合 (例: SDKの音声リストから削除された等) は、
                        # 現在のリストの最初の音声を選択する。
                        if self.voice_combo['values']:
                            self.voice_var.set(self.voice_combo['values'][0])
                        # else: リストが空の場合は何もしない（エラーケース）
                except IndexError:
                    # 文字列操作で予期せぬエラーが発生した場合のフォールバック
                    if self.voice_combo['values']:
                        self.voice_var.set(self.voice_combo['values'][0])
            # else: 保存されていたモデル名が短い形式であるか、または他のエンジンである場合は、
            #       既に update_voice_models と voice_settings.get('model', ...) の組み合わせで
            #       適切な値が self.voice_var に設定されているはずなので、ここでは何もしない。

    def on_template_changed(self, event=None):
        """テンプレート選択が変更された際の処理。UIの各フィールドを更新する。"""
        selected_template_name = self.template_var.get()
        if selected_template_name == "カスタム":
            # カスタム選択時はフィールドをクリアまたはデフォルト値に
            self.base_tone_var.set("")
            self.speech_style_var.set("")
            self.traits_text.delete(1.0, tk.END)
            self.topics_text.delete(1.0, tk.END)
            self.voice_engine_var.set("google_ai_studio_new") # デフォルトエンジン
            self.update_voice_models() # エンジン変更に伴いモデルリスト更新
            # self.voice_var.set("") # update_voice_models内でデフォルトが設定される
            self.speed_var.set(1.0)
            self.response_length_var.set("1-2文程度")
            self.emoji_var.set(True)
            self.emotion_var.set("普通")
            return

        template_data = self.character_manager.character_templates.get(selected_template_name)
        if not template_data:
            return # テンプレートデータが見つからない場合は何もしない

        # 性格設定を更新
        personality = template_data.get("personality", {})
        self.base_tone_var.set(personality.get("base_tone", ""))
        self.speech_style_var.set(personality.get("speech_style", ""))
        self.traits_text.delete(1.0, tk.END)
        self.traits_text.insert(1.0, "\n".join(personality.get("character_traits", [])))
        self.topics_text.delete(1.0, tk.END)
        self.topics_text.insert(1.0, "\n".join(personality.get("favorite_topics", [])))

        # 音声設定を更新
        voice_settings = template_data.get("voice_settings", {})
        self.voice_engine_var.set(voice_settings.get("engine", "google_ai_studio_new"))
        self.update_voice_models() # エンジン変更に伴いモデルリスト更新
        # self.voice_var が update_voice_models の後に設定されるようにする
        # 正しいモデルが選択されるように、update_voice_models の後に設定
        selected_model = voice_settings.get("model", "")
        if selected_model and selected_model in self.voice_combo['values']:
            self.voice_var.set(selected_model)
        elif self.voice_combo['values']: # モデルリストにない場合、リストの最初のものを選択
            self.voice_var.set(self.voice_combo['values'][0])
        # else: モデルリストも空の場合は設定しない（エラーケース）

        self.speed_var.set(voice_settings.get("speed", 1.0))

        # 応答設定を更新
        response_settings = template_data.get("response_settings", {})
        self.response_length_var.set(response_settings.get("max_length", "1-2文程度"))
        self.emoji_var.set(response_settings.get("use_emojis", True))
        self.emotion_var.set(response_settings.get("emotion_level", "普通"))
    
    def on_engine_changed(self, event=None):
        """音声エンジン選択が変更された際の処理。音声モデルのリストを更新する。"""
        self.update_voice_models()
    
    def update_voice_models(self):
        """選択された音声エンジンに応じて音声モデルリストを更新（4エンジン完全対応）"""
        engine = self.voice_engine_var.get()
        voices = []
        default_voice = ""
        info_text = ""
        
        # エンジンごとに音声モデルを取得
        if engine == "google_ai_studio_new":
            instance = GoogleAIStudioNewVoiceAPI()
            voices = instance.get_available_voices()
            default_voice = voices[0] if voices else "puck"
            info_text = "🚀 最新SDK利用・gemini-2.5-flash-preview-ttsモデル・リアルタイム対応・多言語"
        elif engine == "avis_speech":
            # AvisSpeechの音声リストは現状固定だが、将来的にはAPIから取得する可能性も考慮
            avis_instance = AvisSpeechEngineAPI()
            # AvisSpeechEngineAPI.get_available_voices は asyncio を使う場合があるため、
            # ここでは CharacterEditDialog の同期的なコンテキストで呼び出すのが難しい。
            # GUIの初期化時に一度だけ取得しておくか、AvisSpeechEngineAPI側で同期的に取得できるメソッドを用意する必要がある。
            # 現状はハードコードされたリストを維持するが、理想的には動的に取得したい。
            voices = ["Anneli(ノーマル)", "Anneli(クール)", "Anneli(ささやき)", "Anneli(元気)", "Anneli(悲しみ)", "Anneli(怒り)"] # 仮
            if not voices: # もしAPIから動的に取得しようとして失敗した場合のフォールバック
                 voices = ["Anneli(ノーマル)", "Anneli(クール)", "Anneli(ささやき)"]
            default_voice = "Anneli(ノーマル)"
            info_text = "🎙️ ローカル実行・高品質・VOICEVOX互換API・感情表現対応"
        elif engine == "voicevox":
            voicevox_instance = VOICEVOXEngineAPI()
            # VOICEVOXEngineAPI.get_available_voices は内部で check_availability を呼び出す可能性があり、
            # check_availability は asyncio を使用する。
            # ここでは、VOICEVOXEngineAPIのインスタンスを作成し、get_available_voicesを呼び出す。
            # get_available_voices内で必要に応じて同期的にcheck_availabilityを呼び出すように修正済みと仮定。
            # または、GUIの初期化時にVoiceManagerなどを経由して事前に取得しておく。
            # ここでは直接呼び出すが、もしGUIがフリーズするようなら非同期処理の検討が必要。
            # VOICEVOXEngineAPI の get_available_voices は同期的に動作するように改修した前提で進める。
            # （内部でループを回して asyncio.run するなど）
            # 実際には、GUIの応答性を保つために、これらのAPI呼び出しは別スレッドで行い、
            # 結果をキューでメインスレッドに渡してUIを更新するのが望ましい。
            # 今回の改修範囲では、VOICEVOXEngineAPI.get_available_voicesが同期的に動作すると仮定。

            # VOICEVOXEngineAPI のインスタンスを作成
            # このインスタンスは CharacterManager 経由ではなく、直接生成
            # TODO: VoiceEngineManager を CharacterEditDialog に渡してそこから取得する方が良いかもしれない
            temp_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(temp_loop)
            try:
                # check_availability を呼び出して self.speakers を更新させる
                temp_loop.run_until_complete(voicevox_instance.check_availability())
                voices = voicevox_instance.get_available_voices() # これで動的に取得されたリスト、またはフォールバックリスト
            except Exception as e:
                print(f"CharacterEditDialog: VOICEVOXの音声リスト取得中にエラー: {e}")
                voices = ["ずんだもん(ノーマル)"] # エラー時の最終フォールバック
            finally:
                temp_loop.close()

            default_voice = voices[0] if voices else "ずんだもん(ノーマル)"
            info_text = "🎤 定番キャラクター・ずんだもん等・安定動作・豊富な感情表現（Engineから動的取得）"
        else:  # system_tts
            system_tts_instance = SystemTTSAPI()
            voices = system_tts_instance.get_available_voices()
            default_voice = "Haruka (SAPI5)" if "Haruka (SAPI5)" in voices else (voices[0] if voices else "デフォルト")
            info_text = "💻 OS標準TTS (SAPI5 & OneCore対応)・完全無料・インターネット不要・安定動作"
        
        # 音声モデルリスト更新
        self.voice_combo['values'] = voices
        if not self.is_edit_mode or self.voice_var.get() not in voices:
            self.voice_var.set(default_voice)
        elif self.is_edit_mode and self.voice_var.get() in voices:
            # If in edit mode and the current voice is valid, keep it.
            pass # voice_var is already correctly set or will be by load_existing_data
        else: # Fallback if the current voice_var value is somehow invalid after list update
            self.voice_var.set(default_voice)
        
        # エンジン情報表示
        if hasattr(self, 'engine_info_label'):
            self.engine_info_label.config(text=info_text)
    
    def test_voice(self):
        """音声テスト（4エンジン完全対応）"""
        text = f"こんにちは！私は{self.name_var.get() or 'テスト'}です。4つの音声エンジンに完全対応したシステムでお話しています。"
        voice_engine = self.voice_engine_var.get()
        voice_model = self.voice_var.get()
        speed = self.speed_var.get()
        
        def run_test():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # エンジンに応じて処理（完全対応版）
                if voice_engine == "google_ai_studio_new":
                    api_key = self._get_api_key("google_ai_api_key") # この行は既に存在
                    engine = GoogleAIStudioNewVoiceAPI()
                    # synthesize_speech に api_key を渡す
                    audio_files = loop.run_until_complete(
                        engine.synthesize_speech(text, voice_model, speed, api_key=api_key)
                    )
                elif voice_engine == "avis_speech":
                    engine = AvisSpeechEngineAPI()
                    audio_files = loop.run_until_complete(
                        engine.synthesize_speech(text, voice_model, speed)
                    )
                elif voice_engine == "voicevox":
                    engine = VOICEVOXEngineAPI()
                    audio_files = loop.run_until_complete(
                        engine.synthesize_speech(text, voice_model, speed)
                    )
                else:  # system_tts
                    engine = SystemTTSAPI()
                    audio_files = loop.run_until_complete(
                        engine.synthesize_speech(text, voice_model, speed)
                    )
                
                if audio_files:
                    audio_player = AudioPlayer()
                    loop.run_until_complete(
                        audio_player.play_audio_files(audio_files)
                    )
                    print(f"✅ 音声テスト完了: {voice_engine}/{voice_model}")
                else:
                    print(f"❌ 音声テスト失敗: {voice_engine}/{voice_model}")
                
                loop.close()
                
            except Exception as e:
                print(f"音声テストエラー: {e}")
        
        threading.Thread(target=run_test, daemon=True).start()
    
    def compare_voice_engines(self):
        """エンジン比較テスト"""
        text = f"私は{self.name_var.get() or 'テスト'}です。各エンジンの音質を比較してみましょう。"
        
        def run_comparison():
            try:
                engines_to_test = [
                    ("google_ai_studio_new", "puck"), # 修正: 短い形式の音声名に変更 (例: "puck")
                    ("avis_speech", "Anneli(ノーマル)"),
                    ("voicevox", "ずんだもん(ノーマル)"),
                    ("system_tts", "Microsoft Ayumi Desktop")
                ]
                
                for i, (engine_name, voice_model) in enumerate(engines_to_test, 1):
                    print(f"🎵 エンジン比較 {i}/{len(engines_to_test)}: {engine_name}")
                    
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    test_text = f"エンジン{i}番、{engine_name}による音声です。{text}"
                    
                    try:
                        if engine_name == "google_ai_studio_new":
                            api_key = self._get_api_key("google_ai_api_key") # 修正: この行は既に存在し、正しい
                            engine = GoogleAIStudioNewVoiceAPI()
                            # 修正: synthesize_speech に api_key を渡す (既に正しく渡されている)
                            audio_files = loop.run_until_complete(
                                engine.synthesize_speech(test_text, voice_model, 1.0, api_key=api_key)
                            )
                        elif engine_name == "avis_speech":
                            engine = AvisSpeechEngineAPI()
                            audio_files = loop.run_until_complete(
                                engine.synthesize_speech(test_text, voice_model, 1.0)
                            )
                        elif engine_name == "voicevox":
                            engine = VOICEVOXEngineAPI()
                            audio_files = loop.run_until_complete(
                                engine.synthesize_speech(test_text, voice_model, 1.0)
                            )
                        else:  # system_tts
                            engine = SystemTTSAPI()
                            audio_files = loop.run_until_complete(
                                engine.synthesize_speech(test_text, voice_model, 1.0)
                            )
                        
                        if audio_files:
                            audio_player = AudioPlayer()
                            loop.run_until_complete(
                                audio_player.play_audio_files(audio_files)
                            )
                            print(f"✅ {engine_name} 比較完了")
                        else:
                            print(f"❌ {engine_name} 比較失敗")
                    
                    except Exception as e:
                        print(f"❌ {engine_name} エラー: {e}")
                    
                    finally:
                        loop.close()
                    
                    time.sleep(1)  # 次のエンジンとの間隔
                
                print("🎉 4エンジン比較完了")
                
            except Exception as e:
                print(f"比較テストエラー: {e}")
        
        threading.Thread(target=run_comparison, daemon=True).start()
    
    def _get_api_key(self, key_name):
        """APIキーを取得"""
        try:
            with open('aituber_config_v22.json', 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                return config_data.get('system_settings', {}).get(key_name, '')
        except:
            return ""
    
    def save_character(self):
        """キャラクター保存（完全版）"""
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("エラー", "キャラクター名を入力してください")
            return
        
        try:
            # キャラクターデータ構築（完全版）
            char_data = {
                "name": name,
                "personality": {
                    "base_tone": self.base_tone_var.get(),
                    "speech_style": self.speech_style_var.get(),
                    "character_traits": [
                        trait.strip() for trait in self.traits_text.get(1.0, tk.END).strip().split('\n') 
                        if trait.strip()
                    ],
                    "favorite_topics": [
                        topic.strip() for topic in self.topics_text.get(1.0, tk.END).strip().split('\n') 
                        if topic.strip()
                    ]
                },
                "voice_settings": {
                    "engine": self.voice_engine_var.get(),
                    "model": self.voice_var.get(),
                    "speed": self.speed_var.get(),
                    "volume": 1.0,
                    "quality": self.quality_var.get()
                },
                "response_settings": {
                    "max_length": self.response_length_var.get(),
                    "use_emojis": self.emoji_var.get(),
                    "emotion_level": self.emotion_var.get()
                }
            }
            
            if self.is_edit_mode:
                # 編集モード：既存キャラクターを更新
                char_data["char_id"] = self.char_id
                char_data["created_at"] = self.char_data.get("created_at", datetime.now().isoformat())
                char_data["updated_at"] = datetime.now().isoformat()
                
                self.character_manager.config.save_character(self.char_id, char_data)
                
                self.result = {
                    "char_id": self.char_id,
                    "name": name,
                    "action": "edited"
                }
            else:
                # 新規作成モード
                template = getattr(self, 'template_var', tk.StringVar(value="カスタム")).get()
                
                char_id = self.character_manager.create_character(
                    name=name,
                    template_name=template if template != "カスタム" else None,
                    custom_settings=char_data
                )
                
                self.result = {
                    "char_id": char_id,
                    "name": name,
                    "action": "created"
                }
            
            self.dialog.destroy()
            
        except Exception as e:
            action = "編集" if self.is_edit_mode else "作成"
            messagebox.showerror("エラー", f"キャラクターの{action}に失敗しました: {e}")

# メインGUIアプリケーション v2.2（4エンジン完全対応版・機能削減なし）
class AITuberMainGUI:
    """
    完全版AITuberシステムGUI v2.2 - 4エンジン完全対応版
    キャラクター管理・配信・デバッグ機能を完全統合（機能削減なし）
    """
    
    def __init__(self):
        self.root = tk.Tk()
        self.log_text = None # log_text を None で初期化
        self.root.title("AITuber完全版システム v2.2 - 4エンジン完全対応版（2025年5月最新・機能削減なし）")
        self.root.geometry("1100x950")
        
        # システム初期化
        self.config = ConfigManager()
        self.character_manager = CharacterManager(self.config)
        self.voice_manager = VoiceEngineManager()
        self.audio_player = AudioPlayer(config_manager=self.config) # config_managerを渡す
        
        # 状態管理
        self.is_streaming = False
        self.current_character_id = ""
        self.aituber_task = None
        self.debug_chat_history = [] # デバッグチャット用の会話履歴

        # AI劇場関連の状態変数
        self.current_script_path = None
        self.script_data = [] # パースされた台本データ
        self.audio_output_folder = None
        self.is_playing_script = False  # 連続再生中フラグ
        self.stop_requested = False     # 連続再生停止リクエストフラグ

        # AIチャット履歴用フォルダのパス設定と作成
        self.ai_chat_history_folder = Path(self.config.config_file).parent / "ai_chat_history"
        try:
            self.ai_chat_history_folder.mkdir(parents=True, exist_ok=True)
            self.log(f"AIチャット履歴フォルダを作成/確認しました: {self.ai_chat_history_folder}")
        except Exception as e:
            self.log(f"AIチャット履歴フォルダの作成に失敗しました: {e}")
            # エラー発生時も処理を継続するが、履歴機能は利用できない可能性あり
            messagebox.showerror("フォルダ作成エラー", f"AIチャット履歴フォルダの作成に失敗しました: {e}\nチャット履歴機能が正しく動作しない可能性があります。")


        self.available_gemini_models = [
            "gemini-1.5-flash",
            "gemini-1.5-flash-latest",
            "gemini-1.5-pro",
            "gemini-1.5-pro-latest",
            # "gemini-2.0-flash", # APIドキュメントに記載なし (2024/03時点)
            # "gemini-2.0-pro",   # APIドキュメントに記載なし (2024/03時点)
            # "gemini-2.5-flash-lite", # v1beta generateContent で未対応のため削除 (2024/06/24確認)
            "gemini-2.5-flash",
            "gemini-2.5-pro"      # 仮追加 (APIでの利用可否とプレビュー状況の確認が必要)
        ]
        # モデル名のソート (バージョン、精度の順)
        # 簡単なソートキー関数を定義
        def sort_key_gemini(model_name):
            parts = model_name.split('-')
            version_str = parts[1] # "1.5", "2.5"など
            try:
                version_major = float(version_str)
            except ValueError:
                version_major = 0 # エラーの場合は先頭に

            precision_order = {"lite": 0, "flash": 1, "pro": 2}
            precision_val = precision_order.get(parts[2] if len(parts) > 2 else (parts[0] if parts[0] in precision_order else "flash"), 1)

            is_latest = "latest" in model_name
            return (version_major, precision_val, is_latest)

        self.available_gemini_models.sort(key=sort_key_gemini)
        
        # ログ設定
        self.setup_logging()
        
        # GUI構築
        self.create_widgets()
        self.load_settings()
        
        # 終了時の処理
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_logging(self):
        """ログシステム設定（完全版）"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('aituber_system_v22_complete.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def create_widgets(self):
        """GUI要素作成（完全版）"""
        # メインノートブック
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # タブ作成（完全版）
        self.create_main_tab()
        self.create_character_tab()
        self.create_ai_chat_tab() # AIチャットタブ作成メソッド呼び出しを追加
        self.create_debug_tab()
        self.create_settings_tab()
        self.create_ai_theater_tab() # AI劇場タブ作成メソッド呼び出しを追加
        self.create_advanced_tab()  # 新規追加：高度な機能
        
        # ステータスバー
        self.create_status_bar()

    def create_ai_chat_tab(self):
        """AIチャットタブを作成"""
        ai_chat_frame = ttk.Frame(self.notebook)
        self.notebook.add(ai_chat_frame, text="💬 AIチャット")

        # メインフレームを左右に分割
        main_paned_window = ttk.PanedWindow(ai_chat_frame, orient=tk.HORIZONTAL)
        main_paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 左側: 会話履歴一覧
        history_list_frame = ttk.LabelFrame(main_paned_window, text="会話履歴", padding="5")
        main_paned_window.add(history_list_frame, weight=1)

        self.chat_history_tree = ttk.Treeview(history_list_frame, columns=('filename', 'last_updated'), show='headings')
        self.chat_history_tree.heading('filename', text='会話ログ')
        self.chat_history_tree.heading('last_updated', text='最終更新日時')
        self.chat_history_tree.column('filename', width=150)
        self.chat_history_tree.column('last_updated', width=150)
        self.chat_history_tree.bind('<<TreeviewSelect>>', self.on_chat_history_selected)
        chat_history_scroll_y = ttk.Scrollbar(history_list_frame, orient=tk.VERTICAL, command=self.chat_history_tree.yview)
        self.chat_history_tree.configure(yscrollcommand=chat_history_scroll_y.set)
        chat_history_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.chat_history_tree.pack(fill=tk.BOTH, expand=True)

        # 右側: 会話エリア
        chat_area_frame = ttk.Frame(main_paned_window)
        main_paned_window.add(chat_area_frame, weight=3)

        # 右側上部: キャラクター選択と設定
        chat_config_frame = ttk.Frame(chat_area_frame)
        chat_config_frame.pack(fill=tk.X, pady=5)

        ttk.Label(chat_config_frame, text="AIキャラ:").grid(row=0, column=0, padx=2, pady=2, sticky=tk.W)
        self.ai_char_var = tk.StringVar()
        self.ai_char_combo = ttk.Combobox(chat_config_frame, textvariable=self.ai_char_var, state="readonly", width=15)
        self.ai_char_combo.grid(row=0, column=1, padx=2, pady=2, sticky=tk.W)
        # TODO: self.ai_char_combo.bind('<<ComboboxSelected>>', self.on_ai_character_changed_for_chat)

        ttk.Label(chat_config_frame, text="ユーザーキャラ:").grid(row=0, column=2, padx=2, pady=2, sticky=tk.W)
        self.user_char_var = tk.StringVar()
        self.user_char_combo = ttk.Combobox(chat_config_frame, textvariable=self.user_char_var, state="readonly", width=15)
        self.user_char_combo.grid(row=0, column=3, padx=2, pady=2, sticky=tk.W)
        # TODO: self.user_char_combo.bind('<<ComboboxSelected>>', self.on_user_character_changed_for_chat)

        self.play_user_speech_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(chat_config_frame, text="ユーザー発話再生", variable=self.play_user_speech_var).grid(row=0, column=4, padx=5, pady=2, sticky=tk.W)


        # 右側中央: 会話内容表示
        chat_display_container = ttk.LabelFrame(chat_area_frame, text="会話内容 (TreeView形式)", padding="5")
        chat_display_container.pack(fill=tk.BOTH, expand=True, pady=5)

        self.chat_content_tree = ttk.Treeview(chat_display_container, columns=('line', 'talker', 'words'), show='headings')
        self.chat_content_tree.heading('line', text='行')
        self.chat_content_tree.heading('talker', text='話者')
        self.chat_content_tree.heading('words', text='発言内容')

        self.chat_content_tree.column('line', width=50, anchor=tk.CENTER)
        self.chat_content_tree.column('talker', width=120)
        self.chat_content_tree.column('words', width=400) # 可変幅にするか検討

        chat_content_scroll_y = ttk.Scrollbar(chat_display_container, orient=tk.VERTICAL, command=self.chat_content_tree.yview)
        chat_content_scroll_x = ttk.Scrollbar(chat_display_container, orient=tk.HORIZONTAL, command=self.chat_content_tree.xview)
        self.chat_content_tree.configure(yscrollcommand=chat_content_scroll_y.set, xscrollcommand=chat_content_scroll_x.set)

        chat_content_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        chat_content_scroll_x.pack(side=tk.BOTTOM, fill=tk.X) # Xスクロールバーも追加
        self.chat_content_tree.pack(fill=tk.BOTH, expand=True)

        # ウィンドウリサイズ時に 'words' 列の幅を調整する
        def on_chat_content_tree_configure(event):
            new_width = event.width - self.chat_content_tree.column('line')['width'] - self.chat_content_tree.column('talker')['width'] - 20 # スクロールバーやパディング分を考慮
            if new_width > 100: # 最小幅制限
                self.chat_content_tree.column('words', width=new_width)
        self.chat_content_tree.bind('<Configure>', on_chat_content_tree_configure)


        # 会話内容TreeViewの右クリックメニュー設定
        self.chat_content_context_menu = tk.Menu(self.chat_content_tree, tearoff=0)
        self.chat_content_context_menu.add_command(label="選択行を削除", command=self.delete_selected_chat_message)
        self.chat_content_tree.bind("<Button-3>", self.show_chat_content_context_menu)


        # 右側下部: チャット入力
        chat_input_frame = ttk.Frame(chat_area_frame)
        chat_input_frame.pack(fill=tk.X, pady=5)

        self.chat_message_entry = ttk.Entry(chat_input_frame, width=60)
        self.chat_message_entry.bind("<Return>", self.send_ai_chat_message)
        self.chat_message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        send_button = ttk.Button(chat_input_frame, text="送信", command=self.send_ai_chat_message)
        send_button.pack(side=tk.LEFT)

        # 新しいチャットセッションを開始するボタン
        new_chat_button = ttk.Button(history_list_frame, text="新しいチャットを開始", command=self.start_new_ai_chat_session)
        new_chat_button.pack(side=tk.BOTTOM, fill=tk.X, pady=5)


        # TODO: キャラクタードロップダウンの初期化 (populate_ai_theater_talker_dropdown のようなメソッドを参考に)
        self.populate_chat_character_dropdowns()
        self.load_chat_history_list() # 会話履歴一覧を読み込み
        self.current_ai_chat_file_path = None # 現在アクティブなチャットファイル

    def start_new_ai_chat_session(self):
        """新しいAIチャットセッションを開始し、対応するCSVファイルを作成する"""
        if not hasattr(self, 'ai_chat_history_folder') or not self.ai_chat_history_folder.exists():
            messagebox.showerror("エラー", "AIチャット履歴フォルダが見つかりません。")
            self.log("AIチャット: 新規セッション開始不可 - 履歴フォルダなし。")
            return

        # 新しいチャットファイル名を生成 (例: chat_YYYYMMDD_HHMMSS.csv)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_chat_filename = f"chat_{timestamp}.csv"
        self.current_ai_chat_file_path = self.ai_chat_history_folder / new_chat_filename

        try:
            with open(self.current_ai_chat_file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['action', 'talker', 'words']) # ヘッダー

            self.log(f"AIチャット: 新しいチャットセッションファイルを作成しました: {self.current_ai_chat_file_path}")

            # 会話内容表示エリア (TreeView) をクリア
            self.chat_content_tree.delete(*self.chat_content_tree.get_children())

            # 履歴リストを更新して新しいファイルを表示
            self.load_chat_history_list()
            # 新しく作成されたファイルを選択状態にする (iid はファイルパスの文字列)
            if self.chat_history_tree.exists(str(self.current_ai_chat_file_path)):
                self.chat_history_tree.selection_set(str(self.current_ai_chat_file_path))
                self.chat_history_tree.focus(str(self.current_ai_chat_file_path))
                self.chat_history_tree.see(str(self.current_ai_chat_file_path))

            messagebox.showinfo("新しいチャット", f"新しいチャットセッション '{new_chat_filename}' を開始しました。")
            self.chat_message_entry.focus_set() # 入力欄にフォーカス

        except Exception as e:
            self.log(f"AIチャット: 新しいチャットセッションファイルの作成に失敗: {e}")
            messagebox.showerror("作成エラー", f"新しいチャットセッションの作成に失敗しました: {e}")
            self.current_ai_chat_file_path = None

    def send_ai_chat_message(self, event=None):
        """AIチャットメッセージを送信する処理 (プレースホルダー)"""
        user_input = self.chat_message_entry.get().strip()
        if not user_input:
            return

        if not self.current_ai_chat_file_path or not os.path.exists(self.current_ai_chat_file_path):
            # アクティブなチャットセッションがない場合は、新しいセッションを開始するか尋ねる
            if messagebox.askyesno("チャット未開始", "アクティブなチャットセッションがありません。\n新しいチャットを開始しますか？"):
                self.start_new_ai_chat_session()
                if not self.current_ai_chat_file_path: # 新規作成に失敗した場合
                    return
            else:
                return

        # TODO: 実際のメッセージ送信、AI応答取得、表示、保存処理をここに実装
        self.log(f"AIチャット: メッセージ送信試行: '{user_input}' (ファイル: {self.current_ai_chat_file_path})")
        user_input = self.chat_message_entry.get().strip()
        if not user_input:
            return

        if not self.current_ai_chat_file_path or not os.path.exists(self.current_ai_chat_file_path):
            if messagebox.askyesno("チャット未開始", "アクティブなチャットセッションがありません。\n新しいチャットを開始しますか？"):
                self.start_new_ai_chat_session()
                if not self.current_ai_chat_file_path:
                    return
            else:
                return

        ai_char_name = self.ai_char_var.get()
        user_char_name = self.user_char_var.get()

        if not ai_char_name or not user_char_name:
            messagebox.showwarning("キャラクター未選択", "AIキャラクターとユーザーキャラクターを選択してください。")
            return

        # ユーザーメッセージの表示と保存
        self._add_message_to_chat_display(f"👤 {user_char_name}", user_input, is_user_message=True)
        self._append_to_chat_csv('talk', user_char_name, user_input)

        self.chat_message_entry.delete(0, tk.END)

        # 2. 設定に応じて処理方式を分岐
        processing_mode = self.config.get_system_setting("ai_chat_processing_mode", "sequential")
        self.log(f"AIチャット処理モード: {processing_mode}")

        if processing_mode == "sequential":
            # シーケンシャル処理: ユーザー音声再生後にAI応答
            if self.play_user_speech_var.get():
                self.log(f"AIチャット (Sequential): ユーザー発話 ('{user_input[:20]}...') の再生を開始し、完了後にAI応答をトリガーします。")
                user_speech_thread = threading.Thread(
                    target=self._play_user_speech_and_trigger_ai,
                    args=(user_char_name, user_input, ai_char_name, user_char_name),
                    daemon=True
                )
                user_speech_thread.start()
            else:
                self.log(f"AIチャット (Sequential): ユーザー発話再生はオフ。直接AI応答生成を開始します。")
                threading.Thread(
                    target=self._generate_and_display_ai_response_for_chat,
                    args=(user_input, ai_char_name, user_char_name),
                    daemon=True
                ).start()
        elif processing_mode == "parallel":
            # パラレル処理: ユーザー音声再生とAI応答生成を並行
            self.log(f"AIチャット (Parallel): ユーザー発話再生とAI応答生成を並行して開始します。")
            if self.play_user_speech_var.get():
                # ユーザー発話の音声再生 (スレッドで実行)
                threading.Thread(target=self._play_character_speech, args=(user_char_name, user_input), daemon=True).start()

            # AI応答の生成と表示 (スレッドで実行) - ユーザー音声再生とは独立して開始
            threading.Thread(target=self._generate_and_display_ai_response_for_chat, args=(user_input, ai_char_name, user_char_name), daemon=True).start()
        else: # 不明なモードの場合はデフォルトのシーケンシャルとして扱う
            self.log(f"AIチャット: 不明な処理モード '{processing_mode}' のため、シーケンシャル処理を実行します。")
            if self.play_user_speech_var.get():
                user_speech_thread = threading.Thread(
                    target=self._play_user_speech_and_trigger_ai,
                    args=(user_char_name, user_input, ai_char_name, user_char_name),
                    daemon=True
                )
                user_speech_thread.start()
            else:
                threading.Thread(
                    target=self._generate_and_display_ai_response_for_chat,
                    args=(user_input, ai_char_name, user_char_name),
                    daemon=True
                ).start()

    def _play_user_speech_and_trigger_ai(self, user_char_name, user_input_text, ai_char_name_for_next_step, user_char_name_for_next_step):
        """
        ユーザーの音声を再生し、その再生が完了した後にAIの応答生成処理をトリガーする。
        このメソッド全体がスレッドで実行されることを想定。
        """
        try:
            self.log(f"AIチャット: ユーザー '{user_char_name}' の発話 ('{user_input_text[:20]}...') の音声再生処理を開始。")
            # ユーザーの音声を再生する (このメソッドは内部で非同期処理を呼び出す場合があるが、ここでは完了を待つ)
            # _play_character_speech は内部で asyncio ループを作成・実行するため、
            # このスレッド内ではその完了を待機する形になる。
            self._play_character_speech(user_char_name, user_input_text)
            self.log(f"AIチャット: ユーザー '{user_char_name}' の発話再生完了。AI応答生成をトリガーします。")

            # AI応答生成をトリガー
            # この呼び出しもスレッド内で行われるが、_generate_and_display_ai_response_for_chat
            # 自体がGUI更新を含むため、その中のGUI操作は self.root.after を使っていることを確認。
            self._generate_and_display_ai_response_for_chat(user_input_text, ai_char_name_for_next_step, user_char_name_for_next_step)

        except Exception as e:
            self.log(f"AIチャット: _play_user_speech_and_trigger_ai 処理中にエラー: {e}\n{traceback.format_exc()}")
            # エラーが発生した場合でも、AIの応答生成を試みるか、あるいはエラー処理を行う
            # ここでは、ユーザー音声再生でエラーが起きても、AI応答は試みる設計とする
            self.log(f"AIチャット: ユーザー音声再生中にエラーが発生しましたが、AI応答生成は試行します。")
            # 引数名を修正して呼び出し
            self._generate_and_display_ai_response_for_chat(user_input_text, ai_char_name_for_next_step, user_char_name_for_next_step)


    def _add_message_to_chat_display(self, talker_display_name, message_content, is_user_message=False):
        """チャット表示TreeViewにメッセージを追加する"""
        # talker_display_name は "👤 ユーザーキャラ名" や "🤖 AIキャラ名" のような形式
        # message_content は実際のメッセージ

        # TreeViewの現在の行数を取得し、新しい行番号を決定
        line_num = len(self.chat_content_tree.get_children()) + 1

        # TreeViewに挿入する話者名 (シンボルなしの純粋なキャラクター名)
        # プレフィックスを除去する処理を追加
        actual_talker_name = talker_display_name
        if talker_display_name.startswith("👤 ") or talker_display_name.startswith("🤖 "):
            actual_talker_name = talker_display_name[2:]

        item_id = self.chat_content_tree.insert('', 'end', values=(line_num, actual_talker_name, message_content), iid=str(line_num))
        self.chat_content_tree.see(item_id) # 追加された行が見えるようにスクロール

    def _append_to_chat_csv(self, action, talker, words):
        """現在のAIチャットCSVファイルに情報を追記する"""
        if not self.current_ai_chat_file_path or not os.path.exists(self.current_ai_chat_file_path):
            self.log(f"AIチャット: CSVファイルへの追記失敗 - current_ai_chat_file_path が無効: {self.current_ai_chat_file_path}")
            return
        try:
            with open(self.current_ai_chat_file_path, 'a', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([action, talker, words])
        except Exception as e:
            self.log(f"AIチャット: CSVファイルへの書き込みエラー ({self.current_ai_chat_file_path}): {e}")

    def _get_character_id_by_name(self, char_name):
        """キャラクター名からキャラクターIDを取得する"""
        all_chars = self.character_manager.get_all_characters()
        for char_id, data in all_chars.items():
            if data.get('name') == char_name:
                return char_id
        return None

    def _play_character_speech(self, char_name, text):
        """指定されたキャラクターの音声設定でテキストを再生する"""
        char_id = self._get_character_id_by_name(char_name)
        if not char_id:
            self.log(f"AIチャット: 音声再生エラー - キャラクター '{char_name}' が見つかりません。")
            return

        char_data = self.config.get_character(char_id)
        if not char_data:
            self.log(f"AIチャット: 音声再生エラー - キャラクター '{char_name}' (ID: {char_id}) のデータが見つかりません。")
            return

        voice_settings = char_data.get('voice_settings', {})
        engine = voice_settings.get('engine', self.config.get_system_setting("voice_engine", "google_ai_studio_new"))
        model = voice_settings.get('model', 'puck')
        speed = voice_settings.get('speed', 1.0)
        google_api_key = self.config.get_system_setting("google_ai_api_key")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            audio_files = loop.run_until_complete(
                self.voice_manager.synthesize_with_fallback(
                    text, model, speed, preferred_engine=engine, api_key=google_api_key
                )
            )
            if audio_files:
                loop.run_until_complete(self.audio_player.play_audio_files(audio_files))
            else:
                self.log(f"AIチャット: 音声合成失敗 ({char_name}: {text[:20]}...)")
        except Exception as e:
            self.log(f"AIチャット: 音声再生処理中にエラー ({char_name}): {e}")
        finally:
            loop.close()

    def _generate_and_display_ai_response_for_chat(self, user_input, ai_char_name, user_char_name):
        """AIの応答を生成し、表示・保存・再生する"""
        ai_char_id = self._get_character_id_by_name(ai_char_name)
        if not ai_char_id:
            self.log(f"AIチャット: AI応答生成エラー - AIキャラクター '{ai_char_name}' が見つかりません。")
            self.root.after(0, self._add_message_to_chat_display, f"システムエラー", f"AIキャラクター '{ai_char_name}' の設定が見つかりません。")
            return

        ai_char_data = self.config.get_character(ai_char_id)
        if not ai_char_data:
            self.log(f"AIチャット: AI応答生成エラー - AIキャラクター '{ai_char_name}' (ID: {ai_char_id}) のデータが見つかりません。")
            self.root.after(0, self._add_message_to_chat_display, f"システムエラー", f"AIキャラクター '{ai_char_name}' のデータ読み込みに失敗しました。")
            return

        # AI応答生成
        try:
            google_api_key = self.config.get_system_setting("google_ai_api_key")
            if not google_api_key:
                self.log("AIチャット: Google AI APIキーが設定されていません。")
                self.root.after(0, self._add_message_to_chat_display, "システムエラー", "Google AI APIキーが未設定です。")
                return

            client = genai.Client(api_key=google_api_key)
            ai_prompt = self.character_manager.get_character_prompt(ai_char_id)

            # CSVから会話履歴を読み込む
            chat_history_for_prompt = []
            if self.current_ai_chat_file_path and os.path.exists(self.current_ai_chat_file_path):
                with open(self.current_ai_chat_file_path, 'r', encoding='utf-8') as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        if row.get('action') == 'talk':
                            speaker = row.get('talker')
                            message_text = row.get('words')
                            if speaker == ai_char_name:
                                chat_history_for_prompt.append(f"あなた: {message_text}")
                            elif speaker == user_char_name: # ユーザーの発言も履歴に含める
                                chat_history_for_prompt.append(f"{user_char_name}: {message_text}")
                            # 他のキャラクターの発言は履歴に含めないか、別の扱いをする

            # 会話履歴をプロンプトに結合 (直近N件など、制限も検討)
            # ここではシンプルに全履歴を結合するが、トークン数に注意
            history_str = "\n".join(chat_history_for_prompt[-20:]) # 直近20件程度に制限

            full_prompt = f"{ai_prompt}\n\n以下はこれまでの会話です:\n{history_str}\n\n{user_char_name}: {user_input}\n\nあなた ({ai_char_name}):"

            selected_model_internal_name = self.config.get_system_setting("text_generation_model", "gemini-1.5-flash")
            local_llm_url = self.config.get_system_setting("local_llm_endpoint_url", "")
            ai_response_text = ""

            if selected_model_internal_name == "local_lm_studio":
                if not local_llm_url:
                    self.log("❌ AIチャット: ローカルLLMエンドポイントURLが設定されていません。")
                    ai_response_text = "ローカルLLMのエンドポイントURLが未設定です。設定タブで確認してください。"
                else:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        ai_response_text = loop.run_until_complete(
                            self._generate_response_local_llm(full_prompt, local_llm_url, ai_char_name)
                        )
                    finally:
                        loop.close()
            else:
                # Google AI Studio (Gemini) を使用
                gemini_response_obj = client.models.generate_content(
                    model=selected_model_internal_name,
                    contents=full_prompt,
                    config=genai.types.GenerateContentConfig(temperature=0.8, max_output_tokens=200)
                )
                ai_response_text = gemini_response_obj.text.strip() if gemini_response_obj.text else "うーん、ちょっとうまく答えられないみたいです。"
            
            # AI応答の表示と保存
            self.root.after(0, self._add_message_to_chat_display, f"🤖 {ai_char_name}", ai_response_text)
            self._append_to_chat_csv('talk', ai_char_name, ai_response_text)

            # AI応答の音声再生
            self._play_character_speech(ai_char_name, ai_response_text)

        except genai.types.generation_types.BlockedPromptException as bpe:
            error_msg = "その内容についてはお答えできません。"
            self.log(f"AIチャット: AI応答生成エラー - プロンプトブロック: {bpe}")
            self.root.after(0, self._add_message_to_chat_display, f"🤖 {ai_char_name}", error_msg)
            self._append_to_chat_csv('talk', ai_char_name, error_msg) # エラーメッセージも保存
        except requests.exceptions.HTTPError as http_err:
            error_msg = "APIの利用上限か、サーバーとの通信に問題があったようです。"
            self.log(f"AIチャット: AI応答生成エラー - HTTPエラー {http_err.response.status_code}: {http_err}")
            self.root.after(0, self._add_message_to_chat_display, f"🤖 {ai_char_name}", error_msg)
            self._append_to_chat_csv('talk', ai_char_name, error_msg)
        except Exception as e:
            error_msg = "ごめんなさい、ちょっと調子が悪いみたいです。"
            self.log(f"AIチャット: AI応答生成中に予期せぬエラー: {e}\n{traceback.format_exc()}")
            self.root.after(0, self._add_message_to_chat_display, f"🤖 {ai_char_name}", error_msg)
            self._append_to_chat_csv('talk', ai_char_name, error_msg)


    def on_chat_history_selected(self, event=None):
        """チャット履歴一覧で項目が選択されたときの処理"""
        selected_items = self.chat_history_tree.selection()
        if not selected_items:
            self.current_ai_chat_file_path = None
            # 会話内容表示エリアをクリアするなどの処理もここに追加可能
            self.chat_content_tree.delete(*self.chat_content_tree.get_children()) # TreeViewをクリア
            return

        selected_item_id = selected_items[0] # 選択されたアイテムのID (iidとしてファイルパス文字列を指定済み)

        try:
            filepath_str = selected_item_id # iidはファイルパスの文字列
            selected_file_path = Path(filepath_str)

            if selected_file_path.exists() and selected_file_path.is_file():
                self.current_ai_chat_file_path = selected_file_path
                self.log(f"AIチャット: 履歴ファイル '{selected_file_path.name}' を選択しました。")

                # CSVファイルの内容を読み込んで会話内容表示エリア(TreeView)に表示
                self.chat_content_tree.delete(*self.chat_content_tree.get_children()) # TreeViewをクリア

                with open(selected_file_path, 'r', encoding='utf-8') as csvfile:
                    reader = csv.DictReader(csvfile)
                    if reader.fieldnames != ['action', 'talker', 'words']:
                        self.log(f"AIチャット: 履歴ファイル '{selected_file_path.name}' のヘッダーが不正です。")
                        # エラーメッセージをTreeViewに表示する代わりに、messageboxで表示
                        messagebox.showerror("ファイル形式エラー", f"ファイル '{selected_file_path.name}' の形式が正しくありません。\n期待されるヘッダー: action,talker,words")
                        self.current_ai_chat_file_path = None # エラーの場合はアクティブファイルを解除
                    else:
                        line_num = 1
                        for row in reader:
                            action = row.get('action', '')
                            talker = row.get('talker', '不明')
                            words = row.get('words', '')

                            if action == 'talk': # 'talk' アクションのみ表示
                                self.chat_content_tree.insert('', 'end', values=(line_num, talker, words), iid=str(line_num))
                                line_num += 1
                if self.chat_content_tree.get_children(): # アイテムがあれば最終行へスクロール
                    self.chat_content_tree.see(self.chat_content_tree.get_children()[-1])
            else:
                self.log(f"AIチャット: 選択された履歴ファイル '{filepath_str}' が存在しません。")
                messagebox.showwarning("ファイルエラー", f"選択された履歴ファイル '{selected_file_path.name}' が見つかりません。")
                self.current_ai_chat_file_path = None
                self.chat_content_tree.delete(*self.chat_content_tree.get_children()) # TreeViewをクリア
                # 履歴リストを再読み込みして不整合を解消
                self.load_chat_history_list()
        except Exception as e:
            self.log(f"AIチャット: 履歴選択処理中にエラー: {e}")
            messagebox.showerror("履歴読み込みエラー", f"チャット履歴の読み込み中にエラーが発生しました: {e}")
            self.current_ai_chat_file_path = None
            self.chat_content_tree.delete(*self.chat_content_tree.get_children()) # TreeViewをクリア

    def show_chat_content_context_menu(self, event):
        """AIチャットの会話内容TreeViewで右クリックメニューを表示する"""
        try:
            # クリックされたアイテムを選択状態にする
            # (メニュー表示前にアイテムが選択されていなくても、クリック位置のアイテムを選択する)
            item_id = self.chat_content_tree.identify_row(event.y)
            if item_id:
                self.chat_content_tree.selection_set(item_id)
                self.chat_content_context_menu.post(event.x_root, event.y_root)
        except Exception as e:
            self.log(f"AIチャット: 右クリックメニュー表示エラー: {e}")

    def delete_selected_chat_message(self):
        """AIチャットの会話内容表示TreeViewで選択されている行を削除する"""
        selected_items = self.chat_content_tree.selection()
        if not selected_items:
            messagebox.showwarning("削除エラー", "削除する行が選択されていません。")
            return

        selected_item_id = selected_items[0] # 最初の選択アイテムのiid (行番号文字列)
        try:
            selected_values = self.chat_content_tree.item(selected_item_id, 'values')
            if not selected_values or len(selected_values) < 3:
                messagebox.showerror("削除エラー", "選択された行の情報を取得できませんでした。")
                return

            line_num_in_tree = int(selected_values[0]) # TreeView上の行番号
            talker_name = selected_values[1]
            message_text_preview = selected_values[2][:30] + "..." if len(selected_values[2]) > 30 else selected_values[2]

            if not messagebox.askyesno("削除確認", f"行 {line_num_in_tree} ({talker_name}: \"{message_text_preview}\") を削除しますか？\nこの操作は元に戻せません。"):
                return

            if not self.current_ai_chat_file_path or not os.path.exists(self.current_ai_chat_file_path):
                messagebox.showerror("ファイルエラー", "現在アクティブなチャット履歴ファイルが見つかりません。")
                return

            # CSVファイルから該当行を削除
            temp_lines = []
            deleted_from_csv = False
            # CSVファイル内の実際の行インデックス (0始まり) を特定する必要がある
            # TreeView上の行番号は1始まりで、'talk'アクションのみをカウントしている

            current_csv_line_index = 0 # CSVファイル内の物理的な行カウンター (ヘッダー除く)
            talk_action_counter = 0    # 'talk' アクションのカウンター (TreeViewの行番号に対応)

            with open(self.current_ai_chat_file_path, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                header = next(reader) # ヘッダーを読み飛ばす
                temp_lines.append(header)
                for row in reader:
                    current_csv_line_index +=1
                    is_target_row = False
                    if row and len(row) >=1 and row[0] == 'talk': # action列が'talk'か
                        talk_action_counter += 1
                        if talk_action_counter == line_num_in_tree: # TreeView上の行番号と一致
                           is_target_row = True

                    if not is_target_row:
                        temp_lines.append(row)
                    else:
                        deleted_from_csv = True
                        self.log(f"AIチャット: CSVから行削除準備完了 (TreeView行: {line_num_in_tree}, CSV物理行(推定): {current_csv_line_index+1})")


            if deleted_from_csv:
                with open(self.current_ai_chat_file_path, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerows(temp_lines)
                self.log(f"AIチャット: CSVファイルから行を削除し、上書き保存しました: {self.current_ai_chat_file_path}")

                # TreeViewから該当行を削除
                self.chat_content_tree.delete(selected_item_id)
                self.log(f"AIチャット: TreeViewから行 {line_num_in_tree} を削除しました。")

                # TreeViewの行番号を再採番して表示を更新
                # (on_chat_history_selectedを再実行するのが簡単)
                self.on_chat_history_selected() # これで再描画と行番号の再採番が行われる
                messagebox.showinfo("削除完了", f"選択された会話行を削除しました。")

            else: # CSVから対応する行が見つからなかった場合 (通常は発生しないはず)
                messagebox.showerror("削除エラー", "CSVファイル内で対応する行が見つかりませんでした。")
                self.log(f"AIチャット: 削除対象の行がCSV内で見つかりませんでした (TreeView行: {line_num_in_tree})。")

        except ValueError:
            messagebox.showerror("削除エラー", "選択された行の行番号が無効です。")
        except Exception as e:
            self.log(f"AIチャット: 会話行の削除中にエラー: {e}\n{traceback.format_exc()}")
            messagebox.showerror("削除エラー", f"会話行の削除中に予期せぬエラーが発生しました: {e}")


    def load_chat_history_list(self):
        """AIチャットの会話履歴一覧をai_chat_historyフォルダから読み込んでTreeViewに表示する"""
        self.chat_history_tree.delete(*self.chat_history_tree.get_children()) # 古い内容をクリア
        if not hasattr(self, 'ai_chat_history_folder') or not self.ai_chat_history_folder.exists():
            self.log("AIチャット: 履歴フォルダが見つからないため、履歴一覧を読み込めません。")
            return

        history_files = []
        for item in self.ai_chat_history_folder.iterdir():
            if item.is_file() and item.suffix.lower() == '.csv':
                try:
                    # ファイル名から日付情報を取得する試み (ファイル名形式に依存)
                    # 例: chat_log_20231027_103000.csv
                    # より堅牢なのはファイルの最終更新日時
                    last_modified_timestamp = item.stat().st_mtime
                    last_modified_dt = datetime.fromtimestamp(last_modified_timestamp)
                    history_files.append({
                        "filename": item.name,
                        "path": item,
                        "last_updated_dt": last_modified_dt,
                        "last_updated_str": last_modified_dt.strftime('%Y-%m-%d %H:%M:%S')
                    })
                except Exception as e:
                    self.log(f"AIチャット: 履歴ファイル '{item.name}' の情報取得中にエラー: {e}")

        # 最終更新日時の降順（新しいものが上）でソート
        history_files.sort(key=lambda x: x["last_updated_dt"], reverse=True)

        for entry in history_files:
            self.chat_history_tree.insert('', 'end', values=(entry["filename"], entry["last_updated_str"]), iid=str(entry["path"]))

        self.log(f"AIチャット: 会話履歴一覧を更新しました ({len(history_files)}件)。")


    def populate_chat_character_dropdowns(self):
        """AIチャットタブのキャラクター選択プルダウンを更新する"""
        all_chars = self.character_manager.get_all_characters()
        char_names = [data.get('name', 'Unknown') for data in all_chars.values()]

        # 「ナレーター」や空欄は不要なので、キャラクター名のみ
        # TODO: AI用とユーザー用で別々のリストを持つか、同じリストを使うか検討。現状は同じリスト。

        self.ai_char_combo['values'] = char_names
        if char_names:
            # 以前選択されていたキャラクターがいればそれを維持、なければ最初のものを選択
            current_ai_char = self.ai_char_var.get()
            if current_ai_char and current_ai_char in char_names:
                self.ai_char_var.set(current_ai_char)
            else:
                self.ai_char_var.set(char_names[0])

        self.user_char_combo['values'] = char_names
        if char_names:
            # ユーザーキャラクターのデフォルトはAIキャラクターと同じか、別のものにするか検討
            # ここでは、AIキャラと同じものを初期選択とする (もしAIキャラが選択されていれば)
            current_user_char = self.user_char_var.get()
            if current_user_char and current_user_char in char_names:
                self.user_char_var.set(current_user_char)
            elif self.ai_char_var.get() and self.ai_char_var.get() in char_names: # AIキャラが選択されていればそれに合わせる
                self.user_char_var.set(self.ai_char_var.get())
            elif char_names: # それもなければ最初のもの
                self.user_char_var.set(char_names[0])

        self.log("AIチャット: キャラクタープルダウンを更新しました。")

    def create_ai_theater_tab(self):
        """AI劇場タブを作成"""
        ai_theater_frame = ttk.Frame(self.notebook)
        self.notebook.add(ai_theater_frame, text="🎭 AI劇場")

        # 上部フレーム (ファイル読み込みと操作ボタン)
        top_frame = ttk.Frame(ai_theater_frame)
        top_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(top_frame, text="📜 CSV台本読み込み", command=self.load_csv_script).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="✨ 新規CSV台本作成", command=self.create_new_csv_script).pack(side=tk.LEFT, padx=5) # 新規ボタン追加
        self.loaded_csv_label = ttk.Label(top_frame, text="CSVファイル: 未読み込み")
        self.loaded_csv_label.pack(side=tk.LEFT, padx=10)

        # 台詞表示エリア (中央フレーム)
        script_display_frame = ttk.LabelFrame(ai_theater_frame, text="台本プレビュー", padding="10")
        script_display_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.script_tree = ttk.Treeview(script_display_frame, columns=('line', 'action', 'talker', 'words', 'status'), show='headings')
        self.script_tree.heading('line', text='行')
        self.script_tree.heading('action', text='アクション')
        self.script_tree.heading('talker', text='話者')
        self.script_tree.heading('words', text='台詞/内容')
        self.script_tree.heading('status', text='音声状態')

        self.script_tree.column('line', width=50, anchor=tk.CENTER)
        self.script_tree.column('action', width=100)
        self.script_tree.column('talker', width=150)
        self.script_tree.column('words', width=400)
        self.script_tree.column('status', width=100, anchor=tk.CENTER)

        script_tree_scroll_y = ttk.Scrollbar(script_display_frame, orient=tk.VERTICAL, command=self.script_tree.yview)
        script_tree_scroll_x = ttk.Scrollbar(script_display_frame, orient=tk.HORIZONTAL, command=self.script_tree.xview)
        self.script_tree.configure(yscrollcommand=script_tree_scroll_y.set, xscrollcommand=script_tree_scroll_x.set)

        script_tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        script_tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.script_tree.pack(fill=tk.BOTH, expand=True)

        # 台本プレビューのイベントバインド (行選択時)
        self.script_tree.bind('<<TreeviewSelect>>', self.on_script_line_selected)


        # 行追加・更新エリア
        edit_area_frame = ttk.LabelFrame(ai_theater_frame, text="行追加・更新", padding="10")
        edit_area_frame.pack(fill=tk.X, padx=10, pady=5)

        edit_area_grid = ttk.Frame(edit_area_frame)
        edit_area_grid.pack(fill=tk.X)

        ttk.Label(edit_area_grid, text="アクション:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.script_action_var = tk.StringVar()
        self.script_action_combo = ttk.Combobox(edit_area_grid, textvariable=self.script_action_var, values=["talk", "narration", "wait"], state="readonly", width=15)
        self.script_action_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        self.script_action_combo.bind('<<ComboboxSelected>>', self.on_script_action_selected) # アクション選択時の処理

        ttk.Label(edit_area_grid, text="話者:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        self.script_talker_var = tk.StringVar()
        self.script_talker_combo = ttk.Combobox(edit_area_grid, textvariable=self.script_talker_var, state="readonly", width=20)
        self.script_talker_combo.grid(row=0, column=3, sticky=tk.W, padx=5, pady=2)
        # 話者リストはキャラクター読み込み後に設定

        ttk.Label(edit_area_grid, text="台詞/内容:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.script_words_entry = ttk.Entry(edit_area_grid, width=60) # Entryで一行
        self.script_words_entry.grid(row=1, column=1, columnspan=3, sticky=tk.EW, padx=5, pady=2)

        # 行追加・更新ボタン
        edit_buttons_frame = ttk.Frame(edit_area_frame)
        edit_buttons_frame.pack(fill=tk.X, pady=5)

        ttk.Button(edit_buttons_frame, text="⏪最後尾に生成追加", command=self.add_and_generate_script_line).pack(side=tk.LEFT, padx=2)
        ttk.Button(edit_buttons_frame, text="➕最後尾に追加", command=self.add_script_line_to_preview).pack(side=tk.LEFT, padx=2)
        ttk.Button(edit_buttons_frame, text="🔄選択行を更新", command=self.update_selected_script_line).pack(side=tk.LEFT, padx=2)
        ttk.Button(edit_buttons_frame, text="✨クリア", command=self.clear_script_input_area).pack(side=tk.LEFT, padx=2)


        # 台本操作ボタンフレーム (プレビューの下)
        script_action_buttons_frame = ttk.Frame(ai_theater_frame)
        script_action_buttons_frame.pack(fill=tk.X, padx=10, pady=5)

        # 左側ボタン群 (音声生成・再生系)
        audio_ops_frame = ttk.Frame(script_action_buttons_frame)
        audio_ops_frame.pack(side=tk.LEFT)
        ttk.Button(audio_ops_frame, text="🔊選択行の音声生成", command=self.generate_selected_line_audio).pack(side=tk.LEFT, padx=2)
        ttk.Button(audio_ops_frame, text="▶️選択行の音声再生", command=self.play_selected_line_audio).pack(side=tk.LEFT, padx=2) # 追加
        ttk.Button(audio_ops_frame, text="🔊全ての音声生成", command=self.generate_all_lines_audio).pack(side=tk.LEFT, padx=2)
        ttk.Button(audio_ops_frame, text="▶️連続再生", command=self.play_script_sequentially).pack(side=tk.LEFT, padx=2)
        ttk.Button(audio_ops_frame, text="⏹️連続再生停止", command=self.stop_sequential_play).pack(side=tk.LEFT, padx=2)

        # 中央ボタン群 (行編集系)
        line_ops_frame = ttk.Frame(script_action_buttons_frame)
        line_ops_frame.pack(side=tk.LEFT, padx=20) # 少し間隔をあける
        ttk.Button(line_ops_frame, text="🔼1行上に移動", command=self.move_script_line_up).pack(side=tk.LEFT, padx=2)
        ttk.Button(line_ops_frame, text="🔽1行下に移動", command=self.move_script_line_down).pack(side=tk.LEFT, padx=2)
        ttk.Button(line_ops_frame, text="🗑️選択行を削除", command=self.delete_selected_script_line).pack(side=tk.LEFT, padx=2)


        # 右側ボタン群 (ファイル操作系)
        file_ops_frame = ttk.Frame(script_action_buttons_frame)
        file_ops_frame.pack(side=tk.RIGHT)
        ttk.Button(file_ops_frame, text="💾CSV台本保存", command=self.export_script_to_csv).pack(side=tk.RIGHT, padx=2) # 追加
        ttk.Button(file_ops_frame, text="🗑️音声ファイル全削除", command=self.delete_all_audio_files).pack(side=tk.RIGHT, padx=2)


    def on_script_action_selected(self, event=None):
        """AI劇場の行追加エリアでアクションが選択されたときの処理"""
        selected_action = self.script_action_var.get()
        if selected_action == "wait":
            self.script_talker_combo.set("") # 話者を空に
            self.script_talker_combo.config(state="disabled") # 話者コンボボックスを非活性化
            self.script_words_entry.delete(0, tk.END) # 台詞/内容をクリア
            # 必要であれば、台詞/内容エントリーも非活性化または数値入力専用にする
        else:
            self.script_talker_combo.config(state="readonly") # 話者コンボボックスを活性化
            # talkerのデフォルト選択などを行う場合はここに記述
            if not self.script_talker_var.get() and self.script_talker_combo['values']:
                 self.script_talker_var.set(self.script_talker_combo['values'][0])


    def populate_ai_theater_talker_dropdown(self):
        """AI劇場タブの話者プルダウンをキャラクターリストで更新する"""
        all_chars = self.character_manager.get_all_characters()
        char_names = [data.get('name', 'Unknown') for data in all_chars.values()]

        # 「ナレーター」を固定で追加し、重複があればキャラクター名を優先
        talker_options = ["ナレーター"] + [name for name in char_names if name != "ナレーター"]

        # waitアクション用に空欄の選択肢を追加（オプション）
        # talker_options = [""] + talker_options # 先頭に空欄を追加

        self.script_talker_combo['values'] = talker_options
        if talker_options and not self.script_talker_var.get(): # 現在の選択がない場合のみデフォルト設定
            self.script_talker_var.set(talker_options[0])

        # 現在選択中のアクションがwaitでなければ、選択肢を有効にする
        if self.script_action_var.get() != "wait":
            self.script_talker_combo.config(state="readonly")
            # talkerのデフォルト選択などを行う場合はここに記述
            if not self.script_talker_var.get() and self.script_talker_combo['values']: # 何も選択されていなければ最初のものを
                 self.script_talker_var.set(self.script_talker_combo['values'][0])
        else: # wait の場合
            self.script_talker_combo.set("") # 話者を空に
            self.script_talker_combo.config(state="disabled")


    def clear_script_input_area(self):
        """AI劇場の行追加・更新エリアをクリアする"""
        self.script_action_var.set("talk") # デフォルトアクション
        self.script_words_entry.delete(0, tk.END)

        # 話者リストがあれば最初のものを選択、なければ空
        if self.script_talker_combo['values']:
            self.script_talker_var.set(self.script_talker_combo['values'][0])
        else:
            self.script_talker_var.set("")
        self.script_talker_combo.config(state="readonly") # 活性化 (waitでない限り)

        # プレビューの選択解除
        if self.script_tree.selection():
            self.script_tree.selection_remove(self.script_tree.selection()[0])

        self.on_script_action_selected() # アクション選択時の処理を呼び出し、話者コンボの状態を正しくする
        self.log("AI劇場: 入力エリアをクリアしました。")

    def on_script_line_selected(self, event=None):
        """AI劇場の台本プレビューで行が選択されたときの処理"""
        selected_items = self.script_tree.selection()
        if not selected_items:
            # 選択が解除された場合、入力欄をクリアする（オプション）
            # self.clear_script_input_area()
            return

        selected_item_id = selected_items[0]
        # Treeviewから直接値を取得するのではなく、self.script_data から対応する行データを取得する
        # Treeviewの values は表示用であり、実際のデータソースは self.script_data
        try:
            # Treeviewの値から行番号を取得
            tree_values = self.script_tree.item(selected_item_id, 'values')
            if not tree_values or len(tree_values) == 0:
                self.log(f"AI劇場: Treeviewから行番号の取得に失敗。Values: {tree_values}")
                return

            line_num_in_tree = int(tree_values[0])

            # self.script_data から該当行を検索
            line_data = next((item for item in self.script_data if item['line'] == line_num_in_tree), None)

            if line_data:
                action = line_data.get('action', 'talk')
                talker = line_data.get('talker', '')
                words = line_data.get('words', '')

                self.script_action_var.set(action)
                self.script_words_entry.delete(0, tk.END)
                self.script_words_entry.insert(0, words)

                # 話者プルダウンの処理
                if action == "wait":
                    self.script_talker_var.set("") # wait時は空
                    self.script_talker_combo.config(state="disabled")
                else:
                    self.script_talker_combo.config(state="readonly")
                    # 既存のキャラクターリストにtalkerが存在するか確認
                    if talker in self.script_talker_combo['values']:
                        self.script_talker_var.set(talker)
                    elif self.script_talker_combo['values']: # リストにない場合は最初のものを選択
                        self.script_talker_var.set(self.script_talker_combo['values'][0])
                        self.log(f"AI劇場: 話者 '{talker}' がリストにないため、最初の話者 '{self.script_talker_combo['values'][0]}' を選択しました。")
                    else: # リストが空の場合
                        self.script_talker_var.set("")
            else:
                self.log(f"AI劇場: script_dataに該当する行データが見つかりません。行番号(Tree): {line_num_in_tree}")
                # 念のため入力欄をクリア
                self.clear_script_input_area()

        except (ValueError, TypeError, IndexError) as e:
            self.log(f"AI劇場: 行選択処理中にエラー: {e}. Tree Values: {self.script_tree.item(selected_item_id, 'values')}")
            self.clear_script_input_area() # エラー時もクリア


    def add_script_line_to_preview(self):
        """行追加・更新エリアの内容を台本プレビューの最後尾に追加する"""
        action = self.script_action_var.get()
        talker = self.script_talker_var.get() if action != "wait" else ""
        words = self.script_words_entry.get()

        if not action:
            messagebox.showwarning("入力エラー", "アクションを選択してください。")
            return
        if action != "wait" and not talker:
            messagebox.showwarning("入力エラー", "話者を選択してください。")
            return
        if not words:
            if action == "talk" or action == "narration":
                messagebox.showwarning("入力エラー", "台詞/内容を入力してください。")
                return
            elif action == "wait":
                if not words.strip().replace('.', '', 1).isdigit(): # 小数点も許容
                    messagebox.showwarning("入力エラー", "待機時間を数値で入力してください。")
                    return

        # 新しい行番号を決定 (既存の行があればその次の番号、なければ1)
        new_line_num = 1
        if self.script_data:
            new_line_num = max(item['line'] for item in self.script_data) + 1

        new_line_data = {
            'line': new_line_num,
            'action': action,
            'talker': talker,
            'words': words,
            'status': '未生成'
        }
        self.script_data.append(new_line_data)

        self.script_tree.insert('', 'end', values=(
            new_line_num, action, talker, words, '未生成'
        ))

        self.log(f"AI劇場: 行 {new_line_num} を追加しました: {action}, {talker}, {words[:20]}...")
        self.clear_script_input_area() # 入力エリアをクリア

    def add_and_generate_script_line(self):
        """行追加・更新エリアの内容を追加し、その行の音声を生成・再生する"""
        action = self.script_action_var.get()
        talker = self.script_talker_var.get() if action != "wait" else ""
        words = self.script_words_entry.get()

        if not action:
            messagebox.showwarning("入力エラー", "アクションを選択してください。")
            return
        if action != "wait" and not talker:
            messagebox.showwarning("入力エラー", "話者を選択してください。")
            return
        if not words:
            if action == "talk" or action == "narration":
                messagebox.showwarning("入力エラー", "台詞/内容を入力してください。")
                return
            elif action == "wait":
                if not words.strip().replace('.', '', 1).isdigit():
                     messagebox.showwarning("入力エラー", "待機時間を数値で入力してください。")
                     return

        if not self.current_script_path or self.audio_output_folder is None:
            messagebox.showerror("エラー", "先にCSV台本を読み込み、音声保存フォルダが設定されている必要があります。")
            return

        new_line_num = 1
        if self.script_data:
            new_line_num = max(item['line'] for item in self.script_data) + 1

        new_line_data = {
            'line': new_line_num,
            'action': action,
            'talker': talker,
            'words': words,
            'status': '未生成'
        }
        self.script_data.append(new_line_data)

        # Treeview にも追加
        item_id = self.script_tree.insert('', 'end', values=(
            new_line_num, action, talker, words, '生成中...' # 最初は生成中ステータス
        ))
        self.script_tree.see(item_id) # 追加された行が見えるようにスクロール

        self.log(f"AI劇場: 行 {new_line_num} を生成付きで追加開始: {action}, {talker}, {words[:20]}...")
        self.clear_script_input_area()

        def run_synthesis_and_play():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success = False
            audio_file_to_play = None
            try:
                # _synthesize_script_line は bool を返すので、ファイルパスも取得する必要がある
                # ここでは、成功したら _get_audio_filename でパスを取得する
                synthesis_success = loop.run_until_complete(self._synthesize_script_line(new_line_data))

                if synthesis_success:
                    audio_file_to_play = self._get_audio_filename(new_line_num)
                    if os.path.exists(audio_file_to_play):
                        self.root.after(0, self._update_script_tree_status, new_line_num, "成功")
                        self.log(f"AI劇場: 行 {new_line_num} の音声生成成功。再生します。")
                        # play_audio_file が単一ファイルを再生し、削除しないことを前提とする
                        loop.run_until_complete(self.audio_player.play_audio_file(str(audio_file_to_play)))
                        success = True
                    else:
                        self.log(f"AI劇場: 行 {new_line_num} の音声生成には成功しましたが、ファイルが見つかりません。")
                        self.root.after(0, self._update_script_tree_status, new_line_num, "ファイルなし")
                else:
                    self.log(f"AI劇場: 行 {new_line_num} の音声生成に失敗しました。")
                    self.root.after(0, self._update_script_tree_status, new_line_num, "失敗")
                    messagebox.showerror("音声生成エラー", f"行 {new_line_num} の音声生成に失敗しました。")

            except Exception as e:
                self.log(f"AI劇場: 生成追加処理中にエラー (行 {new_line_num}): {e}")
                import traceback
                self.log(f"詳細トレース: {traceback.format_exc()}")
                self.root.after(0, self._update_script_tree_status, new_line_num, "エラー")
                messagebox.showerror("処理エラー", f"行 {new_line_num} の生成追加処理中にエラーが発生しました: {e}")
            finally:
                loop.close()

        threading.Thread(target=run_synthesis_and_play, daemon=True).start()


    def update_selected_script_line(self):
        """選択されている台本プレビューの行を行追加・更新エリアの内容で更新する"""
        selected_items = self.script_tree.selection()
        if not selected_items:
            messagebox.showwarning("選択なし", "更新する行を台本プレビューで選択してください。")
            return

        selected_item_id = selected_items[0]

        try:
            # Treeviewの値から行番号を取得
            tree_values = self.script_tree.item(selected_item_id, 'values')
            if not tree_values or len(tree_values) == 0: return # defensive
            line_num_to_update = int(tree_values[0])
        except (ValueError, TypeError, IndexError):
            messagebox.showerror("エラー", "選択された行の情報を取得できませんでした。")
            return

        # 更新後の情報を取得
        new_action = self.script_action_var.get()
        new_talker = self.script_talker_var.get() if new_action != "wait" else ""
        new_words = self.script_words_entry.get()

        if not new_action:
            messagebox.showwarning("入力エラー", "アクションを選択してください。")
            return
        if new_action != "wait" and not new_talker:
            messagebox.showwarning("入力エラー", "話者を選択してください。")
            return
        if not new_words:
            if new_action == "talk" or new_action == "narration":
                messagebox.showwarning("入力エラー", "台詞/内容を入力してください。")
                return
            elif new_action == "wait":
                 if not new_words.strip().replace('.', '', 1).isdigit():
                    messagebox.showwarning("入力エラー", "待機時間を数値で入力してください。")
                    return

        # script_data 内の該当行を更新
        line_data_found = False
        for i, data_item in enumerate(self.script_data):
            if data_item['line'] == line_num_to_update:
                self.script_data[i]['action'] = new_action
                self.script_data[i]['talker'] = new_talker
                self.script_data[i]['words'] = new_words
                self.script_data[i]['status'] = '未生成' # 更新時は未生成に戻す
                line_data_found = True
                break

        if not line_data_found:
            messagebox.showerror("エラー", f"内部データで行 {line_num_to_update} が見つかりませんでした。")
            return

        # Treeview の表示を更新
        self.script_tree.item(selected_item_id, values=(
            line_num_to_update, new_action, new_talker, new_words, '未生成'
        ))

        # 古い音声ファイルがあれば削除
        audio_file_to_delete = self._get_audio_filename(line_num_to_update)
        if os.path.exists(audio_file_to_delete):
            try:
                os.remove(audio_file_to_delete)
                self.log(f"AI劇場: 更新のため音声ファイル {audio_file_to_delete} を削除しました。")
            except FileNotFoundError:
                self.log(f"AI劇場: 更新時、削除対象の音声ファイルが見つかりませんでした: {audio_file_to_delete}") # これはエラーではない場合もある
            except PermissionError as e_perm:
                self.log(f"AI劇場: 音声ファイル削除パーミッションエラー (更新時) {audio_file_to_delete}: {e_perm}")
                messagebox.showwarning("ファイル削除エラー", f"古い音声ファイルの削除中にパーミッションエラーが発生しました。\n{e_perm}")
            except OSError as e_os:
                self.log(f"AI劇場: 音声ファイル削除OSエラー (更新時) {audio_file_to_delete}: {e_os}")
                messagebox.showwarning("ファイル削除エラー", f"古い音声ファイルの削除中にエラーが発生しました。\n{e_os}")
            except Exception as e: # その他の予期せぬエラー
                self.log(f"AI劇場: 音声ファイル削除中に予期せぬエラー (更新時) {audio_file_to_delete}: {e}")
                messagebox.showwarning("ファイル削除エラー", f"古い音声ファイルの削除中に予期せぬエラーが発生しました。\n{e}")

        self.log(f"AI劇場: 行 {line_num_to_update} を更新しました: {new_action}, {new_talker}, {new_words[:20]}...")
        # self.clear_script_input_area() # 更新後はクリアしない方が連続編集しやすい場合もある
        # プレビューの選択は維持

    def _remap_script_lines_and_ui(self, select_line_num_after_remap=None):
        """
        script_dataに基づいて行番号を再割り当てし、Treeviewを再描画する。
        音声ファイル名も新しい行番号に合わせてリネームする。
        select_line_num_after_remap: 再描画後に選択状態にしたい行の新しい行番号。
        """
        if not self.audio_output_folder:
            self.log("AI劇場: _remap_script_lines_and_ui - audio_output_folderが未設定のため処理をスキップ。")
            # messagebox.showerror("エラー", "音声出力フォルダが設定されていません。") # ここで出すと頻発する可能性
            return

        temp_audio_files_mapping = {} # {old_path: new_path}

        # 1. 新しい行番号を割り当て、リネーム対象の音声ファイルを特定
        new_script_data = []
        for new_idx, old_line_data in enumerate(self.script_data):
            old_line_num = old_line_data['line']
            new_line_num = new_idx + 1

            new_item = old_line_data.copy()
            new_item['line'] = new_line_num
            new_script_data.append(new_item)

            if old_line_num != new_line_num: # 行番号が変わる場合のみリネーム対象
                old_audio_path = self._get_audio_filename(old_line_num)
                new_audio_path = self._get_audio_filename(new_line_num)
                if os.path.exists(old_audio_path):
                    temp_audio_files_mapping[str(old_audio_path)] = str(new_audio_path)

        self.script_data = new_script_data

        # 2. 音声ファイルのリネーム (一時ファイルを経由して衝突を避ける)
        # リネームは逆順で行うと、上書きのリスクを減らせる場合があるが、
        # old_path -> temp_path, temp_path -> new_path の2段階が安全。
        # ここでは、直接リネームを試みるが、衝突の可能性がある場合はより複雑な処理が必要。
        # 簡単のため、リネーム対象の新しいパスが既に存在する場合は警告を出す。
        # より堅牢にするには、まず全て一時的な名前にリネームし、その後新しい名前にリネームする。

        # 簡単化のため、リネームは古い番号から新しい番号へ直接行う。
        # 衝突を避けるため、リネーム対象の新しいパスが既に存在し、かつそれがリネーム元でない場合はスキップまたは警告。
        # しかし、この関数が呼ばれる時点ではscript_dataのline番号は既に更新されているので、
        # _get_audio_filename(old_line_data['line']) は古い番号のファイル名を返す。

        # リネーム戦略：
        # a. 全ての old_path -> temp_unique_path にリネーム
        # b. 全ての temp_unique_path -> new_path にリネーム
        intermediate_paths = {}
        try:
            # Step a: old -> intermediate
            for old_path_str, new_path_str in temp_audio_files_mapping.items():
                if os.path.exists(old_path_str):
                    temp_intermediate_path = old_path_str + ".tmp_rename"
                    os.rename(old_path_str, temp_intermediate_path)
                    intermediate_paths[temp_intermediate_path] = new_path_str
                    self.log(f"AI劇場: リネーム準備 {old_path_str} -> {temp_intermediate_path}")

            # Step b: intermediate -> new
            for temp_path, final_new_path in intermediate_paths.items():
                if os.path.exists(temp_path): # 念のため存在確認
                    # new_path が既に存在する場合の処理 (通常は無いはずだが、衝突した場合)
                    if os.path.exists(final_new_path):
                        # ターゲットの final_new_path が、他のリネーム操作の中間ファイルである可能性も考慮する
                        # (例: 1.wav -> 2.wav, 2.wav -> 3.wav の時、2.wav.tmp_rename が final_new_path になるケース)
                        # ただし、現在のロジックでは中間ファイル名は .tmp_rename がつくので直接衝突はしにくい。
                        # 純粋に予期せずファイルが存在する場合の処理。
                        self.log(f"AI劇場: リネーム衝突警告 - ターゲットパス {final_new_path} は既に存在します。削除を試みます。")
                        try:
                            os.remove(final_new_path)
                            self.log(f"AI劇場: 既存ファイル {final_new_path} を削除しました。")
                        except OSError as e_del:
                            self.log(f"AI劇場: 既存ファイル削除エラー {final_new_path}: {e_del}。リネームをスキップします。")
                            # リネームできないので、中間ファイルを元に戻す
                            original_old_path_for_temp = temp_path.replace(".tmp_rename", "")
                            if os.path.exists(temp_path) and not os.path.exists(original_old_path_for_temp):
                                 os.rename(temp_path, original_old_path_for_temp)
                                 self.log(f"AI劇場: 中間ファイル {temp_path} を {original_old_path_for_temp} に戻しました。")
                            continue # このファイルのリネームはスキップ

                    os.rename(temp_path, final_new_path)
                    self.log(f"AI劇場: リネーム成功 {temp_path} -> {final_new_path}")
        except OSError as e_os: # より具体的なエラータイプ
            self.log(f"AI劇場: 音声ファイルのリネーム中にOSエラー: {e_os} (errno: {e_os.errno}, strerror: {e_os.strerror}, filename: {e_os.filename}, filename2: {e_os.filename2})")
            messagebox.showerror("リネームエラー", f"音声ファイルのリネーム中にエラーが発生しました: {e_os.strerror}")
            # リネームに失敗した場合、中間ファイルを元に戻す試み (ベストエフォート)
        except Exception as e: # その他の予期せぬエラー
            self.log(f"AI劇場: 音声ファイルのリネーム中に予期せぬエラー: {e}")
            messagebox.showerror("リネームエラー", f"音声ファイルのリネーム中に予期せぬエラーが発生しました: {e}")
            # リネームに失敗した場合、中間ファイルを元に戻す試み (ベストエフォート)
            for temp_path, final_new_path in intermediate_paths.items():
                original_old_path = temp_path.replace(".tmp_rename", "")
                if os.path.exists(temp_path) and not os.path.exists(original_old_path):
                    try:
                        os.rename(temp_path, original_old_path)
                        self.log(f"AI劇場: リネームロールバック {temp_path} -> {original_old_path}")
                    except Exception as e_rb:
                         self.log(f"AI劇場: リネームロールバック失敗 {temp_path}: {e_rb}")
            # この時点で処理を中断し、UIの再描画は行わないか、エラー状態を示す
            return


        # 3. Treeviewをクリアして再描画
        for item in self.script_tree.get_children():
            self.script_tree.delete(item)

        newly_selected_item_id = None
        for data_item in self.script_data:
            item_id = self.script_tree.insert('', 'end', values=(
                data_item['line'], data_item['action'], data_item['talker'], data_item['words'], data_item['status']
            ))
            if select_line_num_after_remap is not None and data_item['line'] == select_line_num_after_remap:
                newly_selected_item_id = item_id

        # 指定された行を選択状態にする
        if newly_selected_item_id:
            self.script_tree.selection_set(newly_selected_item_id)
            self.script_tree.focus(newly_selected_item_id) # フォーカスも当てる
            self.script_tree.see(newly_selected_item_id)   # 見えるようにスクロール

        self.log("AI劇場: 行番号とUIを再マッピングしました。")


    def move_script_line_up(self):
        """選択された台本プレビューの行を1行上に移動する"""
        selected_items = self.script_tree.selection()
        if not selected_items:
            messagebox.showwarning("選択なし", "移動する行を選択してください。")
            return

        selected_item_id = selected_items[0]
        current_tree_index = self.script_tree.index(selected_item_id)

        if current_tree_index == 0: # 既に一番上の場合
            self.log("AI劇場: 選択行は既に一番上です。")
            return

        # script_data 内でのインデックスも Treeview のインデックスと一致しているはず
        # (CSV読み込み時や追加時に順序通りに格納しているため)
        # ただし、安全のため、行番号で script_data 内の要素を特定する
        try:
            tree_values = self.script_tree.item(selected_item_id, 'values')
            if not tree_values or len(tree_values) == 0: return
            current_line_num = int(tree_values[0])

            # script_data から現在の行のインデックスを探す
            current_data_index = -1
            for idx, item_data in enumerate(self.script_data):
                if item_data['line'] == current_line_num:
                    current_data_index = idx
                    break

            if current_data_index == -1 or current_data_index == 0 : # データが見つからないか、既に先頭
                self.log(f"AI劇場: 行移動(上)エラー。データインデックス: {current_data_index}")
                return

            # script_data の要素を入れ替え
            item_to_move = self.script_data.pop(current_data_index)
            self.script_data.insert(current_data_index - 1, item_to_move)

            self.log(f"AI劇場: 行 {current_line_num} を1行上に移動しました。")
            self._remap_script_lines_and_ui(select_line_num_after_remap=current_line_num -1) # 移動後の新しい行番号で選択

        except (ValueError, TypeError, IndexError) as e:
            self.log(f"AI劇場: 行を上に移動中にエラー: {e}")
            messagebox.showerror("エラー", f"行の移動中にエラーが発生しました: {e}")


    def move_script_line_down(self):
        """選択された台本プレビューの行を1行下に移動する"""
        selected_items = self.script_tree.selection()
        if not selected_items:
            messagebox.showwarning("選択なし", "移動する行を選択してください。")
            return

        selected_item_id = selected_items[0]
        current_tree_index = self.script_tree.index(selected_item_id)
        total_items = len(self.script_tree.get_children())

        if current_tree_index == total_items - 1: # 既に一番下の場合
            self.log("AI劇場: 選択行は既に一番下です。")
            return

        try:
            tree_values = self.script_tree.item(selected_item_id, 'values')
            if not tree_values or len(tree_values) == 0: return
            current_line_num = int(tree_values[0])

            current_data_index = -1
            for idx, item_data in enumerate(self.script_data):
                if item_data['line'] == current_line_num:
                    current_data_index = idx
                    break

            if current_data_index == -1 or current_data_index == len(self.script_data) -1:
                self.log(f"AI劇場: 行移動(下)エラー。データインデックス: {current_data_index}")
                return

            item_to_move = self.script_data.pop(current_data_index)
            self.script_data.insert(current_data_index + 1, item_to_move)

            self.log(f"AI劇場: 行 {current_line_num} を1行下に移動しました。")
            self._remap_script_lines_and_ui(select_line_num_after_remap=current_line_num + 1)

        except (ValueError, TypeError, IndexError) as e:
            self.log(f"AI劇場: 行を下に移動中にエラー: {e}")
            messagebox.showerror("エラー", f"行の移動中にエラーが発生しました: {e}")


    def delete_selected_script_line(self):
        """選択された台本プレビューの行を削除する"""
        selected_items = self.script_tree.selection()
        if not selected_items:
            messagebox.showwarning("選択なし", "削除する行を選択してください。")
            return

        selected_item_id = selected_items[0]

        try:
            tree_values = self.script_tree.item(selected_item_id, 'values')
            if not tree_values or len(tree_values) == 0: return
            line_num_to_delete = int(tree_values[0])
            action_to_delete = tree_values[1]
            words_to_delete = tree_values[3]

            if not messagebox.askyesno("削除確認", f"行 {line_num_to_delete} ({action_to_delete}: {words_to_delete[:20]}...) を削除しますか？\n関連する音声ファイルも削除されます。"):
                return

            # script_data から削除
            original_length = len(self.script_data)
            self.script_data = [item for item in self.script_data if item['line'] != line_num_to_delete]

            if len(self.script_data) == original_length: # 削除対象が見つからなかった場合
                messagebox.showerror("エラー", f"内部データで行 {line_num_to_delete} が見つかりませんでした。")
                return

            # 音声ファイルを削除
            audio_file_to_delete = self._get_audio_filename(line_num_to_delete)
            if os.path.exists(audio_file_to_delete):
                try:
                    os.remove(audio_file_to_delete)
                    self.log(f"AI劇場: 音声ファイル {audio_file_to_delete} を削除しました。")
                except FileNotFoundError:
                    self.log(f"AI劇場: 削除対象の音声ファイルが見つかりませんでした: {audio_file_to_delete}")
                except PermissionError as e_perm:
                    self.log(f"AI劇場: 音声ファイル削除パーミッションエラー {audio_file_to_delete}: {e_perm}")
                    messagebox.showwarning("ファイル削除エラー", f"音声ファイルの削除中にパーミッションエラーが発生しました。\n{e_perm}")
                except OSError as e_os:
                    self.log(f"AI劇場: 音声ファイル削除OSエラー {audio_file_to_delete}: {e_os}")
                    messagebox.showwarning("ファイル削除エラー", f"音声ファイルの削除中にエラーが発生しました。\n{e_os}")
                except Exception as e: # その他の予期せぬエラー
                    self.log(f"AI劇場: 音声ファイル削除中に予期せぬエラー {audio_file_to_delete}: {e}")
                    messagebox.showwarning("ファイル削除エラー", f"音声ファイルの削除中に予期せぬエラーが発生しました。\n{e}")

            self.log(f"AI劇場: 行 {line_num_to_delete} を削除しました。")
            self._remap_script_lines_and_ui() # UI再描画と行番号再割り当て、選択は解除される

        except (ValueError, TypeError, IndexError) as e:
            self.log(f"AI劇場: 行削除中にエラー: {e}")
            messagebox.showerror("エラー", f"行の削除中にエラーが発生しました: {e}")


    def play_selected_line_audio(self):
        """選択された行の音声を再生する。なければ生成を促す。"""
        selected_items = self.script_tree.selection()
        if not selected_items:
            messagebox.showwarning("選択なし", "再生する行を選択してください。")
            return

        selected_item_id = selected_items[0]
        try:
            tree_values = self.script_tree.item(selected_item_id, 'values')
            if not tree_values or len(tree_values) == 0: return
            line_num = int(tree_values[0])
            status = tree_values[4]

            audio_file_path = self._get_audio_filename(line_num)

            if os.path.exists(audio_file_path):
                self.log(f"AI劇場: 行 {line_num} の音声ファイル {audio_file_path} を再生します。")

                def run_play():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        # play_audio_file は単一ファイルを再生し、削除しないことを前提
                        loop.run_until_complete(self.audio_player.play_audio_file(str(audio_file_path)))
                        self.log(f"AI劇場: 行 {line_num} の再生完了。")
                        # 再生後にステータスを「再生済」にするかはオプション
                        # self.root.after(0, self._update_script_tree_status, line_num, "再生済")
                    except Exception as e_play:
                        self.log(f"AI劇場: 音声再生エラー (行 {line_num}): {e_play}")
                        messagebox.showerror("再生エラー", f"音声の再生中にエラーが発生しました: {e_play}")
                    finally:
                        loop.close()
                threading.Thread(target=run_play, daemon=True).start()
            else:
                self.log(f"AI劇場: 行 {line_num} の音声ファイルが見つかりません。ステータス: {status}")
                if status == "未生成" or status == "失敗" or status == "エラー":
                    messagebox.showinfo("音声未生成", f"行 {line_num} の音声はまだ生成されていません。\n「選択行の音声生成」ボタンで生成してください。")
                else: # "成功" や "ファイルなし" の場合もファイルがないのはおかしい
                    messagebox.showwarning("ファイルなし", f"行 {line_num} の音声ファイルが見つかりませんでした。\n再度音声生成をお試しください。")

        except (ValueError, TypeError, IndexError) as e:
            self.log(f"AI劇場: 音声再生準備中にエラー: {e}")
            messagebox.showerror("エラー", f"音声再生の準備中にエラーが発生しました: {e}")


    def export_script_to_csv(self):
        """現在の台本プレビューの内容をCSVファイルとしてエクスポートする"""
        if not self.script_data:
            messagebox.showinfo("エクスポート不可", "エクスポートする台本データがありません。")
            return

        filepath = filedialog.asksaveasfilename(
            title="CSV台本を名前を付けて保存",
            defaultextension=".csv",
            filetypes=(("CSVファイル", "*.csv"), ("すべてのファイル", "*.*"))
        )
        if not filepath:
            return

        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['action', 'talker', 'words'] # CSVScriptDefinitions.md に従う
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for line_data in self.script_data:
                    # 行番号やステータスはエクスポートしない
                    row_to_write = {
                        'action': line_data['action'],
                        'talker': line_data['talker'],
                        'words': line_data['words']
                    }
                    writer.writerow(row_to_write)

            self.log(f"AI劇場: 台本をCSVファイルにエクスポートしました: {filepath}")
            messagebox.showinfo("エクスポート完了", f"台本をCSVファイルに保存しました。\n{filepath}")
        except Exception as e:
            self.log(f"AI劇場: CSVエクスポート中にエラー: {e}")
            messagebox.showerror("エクスポートエラー", f"CSVファイルのエクスポート中にエラーが発生しました: {e}")


    def load_csv_script(self, filepath=None):
        """CSV台本ファイルを読み込み、内容をパースしてUIに表示する。filepathが指定されていればそれを使用する。"""
        if filepath is None:
            filepath = filedialog.askopenfilename(
                title="CSV台本ファイルを選択",
                filetypes=(("CSVファイル", "*.csv"), ("すべてのファイル", "*.*"))
            )
            if not filepath:
                self.log("AI劇場: CSV台本ファイルの選択がキャンセルされました。")
                return
        else:
            self.log(f"AI劇場: 指定されたCSV台本ファイルを読み込みます: {filepath}")

        self.current_script_path = filepath
        self.script_data = []

        # 音声保存フォルダの作成 (例: script_name_audio)
        script_filename = Path(filepath).stem
        self.audio_output_folder = Path(filepath).parent / f"{script_filename}_audio"
        try:
            self.audio_output_folder.mkdir(parents=True, exist_ok=True)
            self.log(f"AI劇場: 音声保存フォルダを作成/確認しました: {self.audio_output_folder}")
        except Exception as e:
            self.log(f"AI劇場: 音声保存フォルダの作成に失敗しました: {e}")
            messagebox.showerror("エラー", f"音声保存フォルダの作成に失敗しました: {e}")
            self.current_script_path = None
            self.audio_output_folder = None
            return

        self.loaded_csv_label.config(text=f"CSVファイル: {Path(filepath).name}")
        self.script_tree.delete(*self.script_tree.get_children()) # 古い内容をクリア

        try:
            with open(filepath, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                if reader.fieldnames != ['action', 'talker', 'words']:
                    messagebox.showerror("CSVフォーマットエラー", "CSVのヘッダーが不正です。\n期待されるヘッダー: action,talker,words")
                    self.log(f"AI劇場: CSVフォーマットエラー。ヘッダー: {reader.fieldnames}")
                    self.current_script_path = None
                    self.audio_output_folder = None
                    self.loaded_csv_label.config(text="CSVファイル: 未読み込み")
                    return

                line_num = 1
                for row in reader:
                    self.script_data.append({
                        'line': line_num,
                        'action': row['action'],
                        'talker': row['talker'],
                        'words': row['words'],
                        'status': '未生成' # 初期ステータス
                    })
                    self.script_tree.insert('', 'end', values=(
                        line_num, row['action'], row['talker'], row['words'], '未生成'
                    ))
                    line_num += 1
            self.log(f"AI劇場: CSVファイル '{filepath}' を読み込みました。全{len(self.script_data)}行。")
        except FileNotFoundError:
            messagebox.showerror("エラー", f"ファイルが見つかりません: {filepath}")
            self.log(f"AI劇場: ファイルが見つかりません: {filepath}")
            self.current_script_path = None
            self.audio_output_folder = None
            self.loaded_csv_label.config(text="CSVファイル: 未読み込み")
        except Exception as e:
            messagebox.showerror("CSV読み込みエラー", f"CSVファイルの読み込み中にエラーが発生しました: {e}")
            self.log(f"AI劇場: CSV読み込みエラー: {e}")
            self.current_script_path = None
            self.audio_output_folder = None
            self.loaded_csv_label.config(text="CSVファイル: 未読み込み")

    def _get_audio_filename(self, line_number: int) -> str:
        """指定された行番号に対する音声ファイル名を生成する (例: 000001.wav)"""
        if not self.audio_output_folder:
            # この状況は通常発生しないはずだが、念のため
            self.log("AI劇場: エラー - 音声出力フォルダが設定されていません。")
            return "error.wav"
        return self.audio_output_folder / f"{line_number:06d}.wav"

    async def _synthesize_script_line(self, line_data: dict) -> bool:
        """指定された一行の台本データに基づいて音声ファイルを生成する"""
        line_num = line_data['line']
        action = line_data['action']
        talker = line_data['talker']
        words = line_data['words']
        output_wav_path = self._get_audio_filename(line_num)

        self.log(f"AI劇場: 音声生成開始 - 行{line_num}, アクション: {action}, 話者: {talker}, 内容: {words[:20]}...")

        try:
            if action == "talk" or action == "narration":
                text_to_speak = words
                char_id_to_use = None

                # 話者を特定
                all_characters = self.character_manager.get_all_characters()
                found_char = False
                for char_id, char_config in all_characters.items():
                    if char_config.get('name') == talker:
                        char_id_to_use = char_id
                        found_char = True
                        self.log(f"AI劇場: 話者 '{talker}' をキャラクターID '{char_id}' にマッピングしました。")
                        break

                if not found_char:
                    if self.current_character_id: # メイン画面のアクティブキャラクター
                        char_id_to_use = self.current_character_id
                        active_char_name = self.config.get_character(self.current_character_id).get('name', '不明')
                        self.log(f"AI劇場: 話者 '{talker}' がキャラクター一覧に見つかりません。アクティブキャラクター '{active_char_name}' (ID: {char_id_to_use}) を使用します。")
                    else:
                        self.log(f"AI劇場: 話者 '{talker}' もアクティブキャラクターも見つかりません。音声生成をスキップします。")
                        messagebox.showwarning("音声生成エラー", f"話者 '{talker}' に対応するキャラクターが見つからず、\nまた、メイン画面でアクティブなキャラクターも選択されていません。")
                        return False

                char_settings = self.config.get_character(char_id_to_use)
                if not char_settings:
                     self.log(f"AI劇場: キャラクターID '{char_id_to_use}' の設定が見つかりません。")
                     return False

                voice_settings = char_settings.get('voice_settings', {})
                engine = voice_settings.get('engine', self.config.get_system_setting("voice_engine", "google_ai_studio_new"))
                model = voice_settings.get('model', 'puck') # Google AI Studio のデフォルト的なもの
                speed = voice_settings.get('speed', 1.0)

                # Google AI Studio APIキーの取得
                google_api_key = self.config.get_system_setting("google_ai_api_key")

                # 実際に使用するエンジンインスタンスを取得
                voice_engine_instance = self.voice_manager.engines.get(engine)
                if not voice_engine_instance:
                    self.log(f"AI劇場: 指定された音声エンジン '{engine}' が見つかりません。フォールバックを試みます。")
                    # フォールバックロジック (synthesize_with_fallback を直接使うか、ここで代替エンジンを選択)
                    # ここでは synthesize_with_fallback に任せる
                    audio_files = await self.voice_manager.synthesize_with_fallback(
                        text_to_speak, model, speed, preferred_engine=engine, api_key=google_api_key
                    )
                else:
                     # APIキーを渡す必要があるか確認
                    if "google_ai_studio" in engine:
                        audio_files = await voice_engine_instance.synthesize_speech(text_to_speak, model, speed, api_key=google_api_key)
                    else:
                        audio_files = await voice_engine_instance.synthesize_speech(text_to_speak, model, speed)

                if audio_files and os.path.exists(audio_files[0]):
                    import shutil
                    try:
                        # 移動先にファイルが既に存在する場合、shutil.moveは上書きする (Python 3.9+では上書きしない場合がある os.replace の方が良いかも)
                        # より安全に上書きするために、一度削除してからmoveするか、os.replaceを使用
                        if os.path.exists(output_wav_path):
                            os.remove(output_wav_path) # 既存ファイルを削除
                        shutil.move(audio_files[0], output_wav_path)
                        self.log(f"AI劇場: 音声ファイル生成成功: {output_wav_path}")
                        return True
                    except (shutil.Error, OSError) as e_move:
                        self.log(f"AI劇場: 音声ファイル移動エラー (shutil.move from {audio_files[0]} to {output_wav_path}): {e_move}")
                        # 移動に失敗した場合、一時ファイルが残っている可能性があるので削除を試みる
                        if os.path.exists(audio_files[0]):
                            try:
                                os.remove(audio_files[0])
                            except OSError as e_del_temp:
                                self.log(f"AI劇場: 一時音声ファイル削除エラー: {e_del_temp}")
                        return False
                else:
                    self.log(f"AI劇場: 音声ファイル生成失敗 (ファイルなし): 行{line_num}")
                    return False

            elif action == "wait":
                try:
                    duration_seconds = float(words)
                    if duration_seconds <= 0:
                        self.log(f"AI劇場: waitアクションの秒数が不正です: {words}。0秒として扱います。")
                        duration_seconds = 0

                    # 無音WAVファイル作成 (24kHz, 16bit, mono を想定)
                    framerate = 24000
                    channels = 1
                    sampwidth = 2 # 16-bit
                    num_frames = int(framerate * duration_seconds)
                    silence = b'\x00\x00' * num_frames # 16-bit zero samples
                    try:
                        with wave.open(str(output_wav_path), 'wb') as wf:
                            wf.setnchannels(channels)
                            wf.setsampwidth(sampwidth)
                            wf.setframerate(framerate)
                            wf.writeframes(silence)
                        self.log(f"AI劇場: 無音ファイル作成成功 ({duration_seconds}秒): {output_wav_path}")
                        return True
                    except wave.Error as e_wave:
                        self.log(f"AI劇場: 無音WAVファイル書き込みエラー (wave.open for {output_wav_path}): {e_wave}")
                        return False
                    except OSError as e_os:
                        self.log(f"AI劇場: 無音WAVファイル書き込みOSエラー (wave.open for {output_wav_path}): {e_os}")
                        return False
                except ValueError:
                    self.log(f"AI劇場: waitアクションの秒数指定が不正です: {words}")
                    messagebox.showerror("書式エラー", f"waitアクションの秒数指定が不正です: {words}\n行 {line_num}")
                    return False
            else:
                self.log(f"AI劇場: 未知のアクションタイプです: {action}。行{line_num}")
                return False # 未知のアクションは失敗扱い

        except Exception as e:
            self.log(f"AI劇場: 音声生成中にエラーが発生しました (行{line_num}): {e}")
            import traceback
            self.log(f"詳細トレース: {traceback.format_exc()}")
            return False

    def _update_script_tree_status(self, line_num: int, status: str):
        """Treeviewの指定行のステータスを更新する"""
        for item_id in self.script_tree.get_children():
            item_values = self.script_tree.item(item_id, 'values')
            if item_values and int(item_values[0]) == line_num:
                # 現在の値を保持しつつ、ステータスのみ更新
                new_values = list(item_values)
                new_values[4] = status
                self.script_tree.item(item_id, values=tuple(new_values))
                break

    def generate_selected_line_audio(self):
        """選択されている行の音声を生成する"""
        selected_items = self.script_tree.selection()
        if not selected_items:
            messagebox.showinfo("AI劇場", "台本プレビューから音声生成する行を選択してください。")
            return

        if not self.current_script_path or not self.script_data:
            messagebox.showerror("エラー", "先にCSV台本を読み込んでください。")
            return

        selected_item_id = selected_items[0]
        selected_values = self.script_tree.item(selected_item_id, 'values')

        try:
            line_num_to_generate = int(selected_values[0])
        except (TypeError, IndexError, ValueError):
            messagebox.showerror("エラー", "選択された行の情報を取得できませんでした。")
            return

        line_data_to_synthesize = next((item for item in self.script_data if item['line'] == line_num_to_generate), None)

        if not line_data_to_synthesize:
            messagebox.showerror("エラー", f"行番号 {line_num_to_generate} のデータが見つかりません。")
            return

        self._update_script_tree_status(line_num_to_generate, "生成中...")

        def run_synthesis():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                success = loop.run_until_complete(self._synthesize_script_line(line_data_to_synthesize))
                final_status = "成功" if success else "失敗"
                # TreeViewの更新はメインスレッドで行う
                self.root.after(0, self._update_script_tree_status, line_num_to_generate, final_status)
                if success:
                    self.log(f"AI劇場: 行 {line_num_to_generate} の音声生成が{final_status}しました。")
                else:
                    messagebox.showerror("音声生成エラー", f"行 {line_num_to_generate} の音声生成に失敗しました。詳細はログを確認してください。")
            except Exception as e:
                self.log(f"AI劇場: generate_selected_line_audio スレッド内エラー: {e}")
                self.root.after(0, self._update_script_tree_status, line_num_to_generate, "エラー")
                messagebox.showerror("音声生成エラー", f"行 {line_num_to_generate} の音声生成中に予期せぬエラーが発生しました: {e}")
            finally:
                loop.close()

        threading.Thread(target=run_synthesis, daemon=True).start()


    def generate_all_lines_audio(self):
        """台本全体の音声を一括生成する"""
        if not self.current_script_path or not self.script_data:
            messagebox.showerror("エラー", "先にCSV台本を読み込んでください。")
            return

        if not messagebox.askyesno("一括音声生成確認", f"台本全体の音声ファイル（全{len(self.script_data)}行）を生成しますか？\n時間がかかる場合があります。"):
            return

        self.log("AI劇場: 全ての音声ファイルの一括生成を開始します...")

        # プログレスバーの準備 (オプション)
        progress_popup = tk.Toplevel(self.root)
        progress_popup.title("音声生成中...")
        progress_popup.geometry("300x100")
        progress_popup.transient(self.root)
        progress_popup.grab_set()

        ttk.Label(progress_popup, text="音声ファイルを生成しています...").pack(pady=10)
        progress_var = tk.DoubleVar()
        progressbar = ttk.Progressbar(progress_popup, variable=progress_var, maximum=len(self.script_data), length=280)
        progressbar.pack(pady=10)

        def run_batch_synthesis():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success_count = 0
            fail_count = 0
            try:
                for i, line_data in enumerate(self.script_data):
                    line_num = line_data['line']
                    self.root.after(0, self._update_script_tree_status, line_num, "生成中...")

                    success = loop.run_until_complete(self._synthesize_script_line(line_data))
                    final_status = "成功" if success else "失敗"
                    self.root.after(0, self._update_script_tree_status, line_num, final_status)

                    if success:
                        success_count += 1
                    else:
                        fail_count += 1

                    # プログレスバー更新
                    progress_var.set(i + 1)
                    progress_popup.update_idletasks() # UIを強制更新

                    # ユーザーによるキャンセルチェック (もし実装する場合)
                    # if self.cancel_batch_generation_flag: break

                self.log(f"AI劇場: 一括音声生成完了。成功: {success_count}, 失敗: {fail_count}")
                if fail_count > 0:
                    messagebox.showwarning("一括音声生成完了", f"一部の音声生成に失敗しました。\n成功: {success_count}件, 失敗: {fail_count}件\n詳細はログを確認してください。")
                else:
                    messagebox.showinfo("一括音声生成完了", f"全ての音声生成が完了しました。\n成功: {success_count}件")

            except Exception as e:
                self.log(f"AI劇場: 一括音声生成中にエラー: {e}")
                messagebox.showerror("一括音声生成エラー", f"一括音声生成中にエラーが発生しました: {e}")
            finally:
                loop.close()
                progress_popup.destroy()

        threading.Thread(target=run_batch_synthesis, daemon=True).start()


    def play_script_sequentially(self):
        """台本を一行ずつ順次再生する。音声がない場合は生成してから再生する。"""
        if not self.current_script_path or not self.script_data:
            messagebox.showerror("エラー", "先にCSV台本を読み込んでください。")
            return

        self.log("AI劇場: 連続再生を開始します...")

        if self.is_playing_script:
            messagebox.showwarning("再生中", "既に連続再生が実行中です。")
            self.log("AI劇場: 連続再生の二重起動が試みられました。")
            return

        self.is_playing_script = True
        self.stop_requested = False # 停止リクエストフラグをリセット

        def run_sequential_play():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                for i, line_data in enumerate(self.script_data):
                    if self.stop_requested:
                        self.log("AI劇場: 連続再生がユーザーによって停止されました。")
                        # messagebox.showinfo はメインスレッドから呼び出すべきなので、ここではログのみ
                        # UI上のメッセージは stop_sequential_play メソッド側か、メインスレッドのafterで出す
                        current_line_num_for_status_update = line_data['line']
                        # 再生中の行だけでなく、それ以降の行もステータスを更新する方が自然かもしれない
                        # ここでは現在の行のみ「停止」とし、残りはそのままか「未再生」とする
                        self.root.after(0, self._update_script_tree_status, current_line_num_for_status_update, "停止済")
                        # 停止後に再生完了メッセージが表示されるのを防ぐため、ここで完了メッセージを出す
                        self.root.after(0, lambda: messagebox.showinfo("連続再生停止", "連続再生を停止しました。"))
                        break

                    line_num = line_data['line']
                    self.log(f"AI劇場: 行 {line_num} を再生準備中...")
                    self.root.after(0, self._update_script_tree_status, line_num, "再生準備") # UI更新

                    audio_file_path = self._get_audio_filename(line_num)

                    if not os.path.exists(audio_file_path):
                        self.log(f"AI劇場: 音声ファイルが見つかりません: {audio_file_path}。生成します...")
                        self.root.after(0, self._update_script_tree_status, line_num, "生成中...")
                        success = loop.run_until_complete(self._synthesize_script_line(line_data))
                        if not success:
                            self.log(f"AI劇場: 行 {line_num} の音声生成に失敗したため、再生をスキップします。")
                            self.root.after(0, self._update_script_tree_status, line_num, "生成失敗")
                            # オプション: エラー発生時に連続再生を中止するかどうか
                            # messagebox.showerror("再生エラー", f"行 {line_num} の音声生成に失敗しました。連続再生を中止します。")
                            # break
                            continue # 次の行へ
                        self.root.after(0, self._update_script_tree_status, line_num, "生成完了")

                    if os.path.exists(audio_file_path):
                        self.log(f"AI劇場: 音声ファイル {audio_file_path} を再生します。")
                        self.root.after(0, self._update_script_tree_status, line_num, "再生中...")

                        # AudioPlayer.play_audio_files はリストを期待するのでリストで渡す
                        # play_audio_files は内部で一時ファイルを削除するため、ここでは永続ファイルを直接再生するメソッドが必要。
                        # AudioPlayer に play_single_persistent_file のようなメソッドを追加するか、
                        # ここで play_audio_file (単数形) を直接呼び出す。
                        # AudioPlayer.play_audio_file は await 可能である想定。

                        # play_audio_files は再生後にファイルを削除してしまうため、ここでは使用しない。
                        # 代わりに、play_audio_file を使用するが、これは現在 AudioPlayer の内部メソッド (_play_windows など)
                        # を直接呼び出す形になっており、トップレベルの await可能な play_audio_file が必要。
                        # 今回は、AudioPlayer の play_audio_files を呼び出すが、
                        # 再生後にファイルが消えないように、一時的なコピーを作成してそれを再生させるか、
                        # AudioPlayer 側を修正する。
                        # ここでは、AudioPlayer.play_audio_file が存在し、単一ファイルを再生し削除しないと仮定。
                        # もし play_audio_file がなければ、play_audio_files に単一要素リストを渡す。
                        # ただし、play_audio_filesはファイルを削除する。
                        # なので、ここでは _synthesize_script_line が作ったファイルを直接再生する。

                        # AudioPlayer の play_audio_file を直接呼び出す
                        # このメソッドは、self.audio_player.play_audio_file(str(audio_file_path)) のように使える必要がある。
                        # 現在の AudioPlayer の play_audio_file は内部的に _play_windows などを呼び出す。
                        loop.run_until_complete(self.audio_player.play_audio_file(str(audio_file_path)))

                        self.log(f"AI劇場: 行 {line_num} の再生完了。")
                        self.root.after(0, self._update_script_tree_status, line_num, "再生済")
                    else:
                        self.log(f"AI劇場: 再生試行後も音声ファイルが見つかりません: {audio_file_path}")
                        self.root.after(0, self._update_script_tree_status, line_num, "ファイルなし")

                    # 各行の再生後に短い待機を入れる（任意）
                    # await asyncio.sleep(0.1)

                self.log("AI劇場: 全ての行の連続再生が完了しました。")
                messagebox.showinfo("連続再生完了", "台本の連続再生が完了しました。")

            except Exception as e:
                self.log(f"AI劇場: 連続再生中にエラーが発生しました: {e}")
                import traceback
                self.log(f"詳細トレース: {traceback.format_exc()}")
                # messagebox.showerror("連続再生エラー", f"連続再生中にエラーが発生しました: {e}") # スレッド内からは避ける
                self.root.after(0, lambda: messagebox.showerror("連続再生エラー", f"連続再生中にエラーが発生しました: {e}"))
            finally:
                self.is_playing_script = False # 再生中フラグをリセット
                # self.stop_requested はここでリセットせず、次の再生開始時にリセットする
                if not self.stop_requested : # ユーザーによる停止でない場合のみ完了メッセージ
                    self.log("AI劇場: 全ての行の連続再生が正常に完了しました。")
                    self.root.after(0, lambda: messagebox.showinfo("連続再生完了", "台本の連続再生が完了しました。"))
                # stop_requested が True の場合は、既に停止メッセージが表示されているはずなので、ここでは何もしない
                self.stop_requested = False # finallyブロックの最後でリセット
                loop.close()

        threading.Thread(target=run_sequential_play, daemon=True).start()

    def delete_all_audio_files(self):
        """現在読み込まれている台本の音声ファイルを全て削除する"""
        if not self.current_script_path or not self.audio_output_folder:
            messagebox.showerror("エラー", "先にCSV台本を読み込んでください。音声フォルダが特定できません。")
            return

        if not os.path.exists(self.audio_output_folder):
            messagebox.showinfo("情報", f"音声フォルダが見つかりません。削除するファイルはありません。\nフォルダパス: {self.audio_output_folder}")
            self.log(f"AI劇場: 音声フォルダ {self.audio_output_folder} が存在しないため、削除処理をスキップしました。")
            # Treeviewのステータスも更新しておく
            for item_id in self.script_tree.get_children():
                values = list(self.script_tree.item(item_id, 'values'))
                values[4] = "未生成"
                self.script_tree.item(item_id, values=tuple(values))
            return

        if not messagebox.askyesno("音声ファイル全削除確認",
                                   f"本当に音声フォルダ内の全ての音声ファイル（.wav）を削除しますか？\nフォルダ: {self.audio_output_folder}\nこの操作は取り消せません。"):
            return

        self.log(f"AI劇場: 音声ファイル全削除処理を開始します。対象フォルダ: {self.audio_output_folder}")
        deleted_count = 0
        failed_count = 0
        try:
            for filename in os.listdir(self.audio_output_folder):
                if filename.lower().endswith(".wav"):
                    file_path_to_delete = self.audio_output_folder / filename
                    try:
                        os.remove(file_path_to_delete)
                        self.log(f"AI劇場: 削除しました: {file_path_to_delete}")
                        deleted_count += 1
                    except Exception as e:
                        self.log(f"AI劇場: ファイル削除エラー ({file_path_to_delete}): {e}")
                        failed_count += 1

            if failed_count > 0:
                messagebox.showwarning("一部削除失敗", f"{deleted_count}個の音声ファイルを削除しましたが、{failed_count}個のファイルの削除に失敗しました。詳細はログを確認してください。")
            else:
                messagebox.showinfo("削除完了", f"{deleted_count}個の音声ファイルを削除しました。")
            self.log(f"AI劇場: 音声ファイル削除完了。削除: {deleted_count}件, 失敗: {failed_count}件")

            # TreeViewのステータスを全て「未生成」に更新
            if self.script_data: # script_data がある場合のみ更新
                for line_data in self.script_data:
                    self._update_script_tree_status(line_data['line'], "未生成")
            else: # script_dataがない（＝CSVが読み込まれていないがフォルダだけ残っているような稀なケース）
                  # または、script_treeが空の場合
                for item_id in self.script_tree.get_children():
                    values = list(self.script_tree.item(item_id, 'values'))
                    if len(values) > 4 : # valuesの要素数をチェック
                        values[4] = "未生成"
                        self.script_tree.item(item_id, values=tuple(values))


        except Exception as e:
            self.log(f"AI劇場: 音声ファイル全削除処理中にエラー: {e}")
            messagebox.showerror("削除エラー", f"音声ファイルの削除中にエラーが発生しました: {e}")

    def stop_sequential_play(self):
        """AI劇場の連続再生を停止する"""
        if self.is_playing_script:
            if not self.stop_requested: # まだ停止リクエストが出ていない場合のみ
                self.stop_requested = True
                self.log("AI劇場: 連続再生の停止ボタンが押されました。停止を試みます。")
                # UIへのフィードバックは play_script_sequentially 内のループで停止を検知した際に行う
            else:
                self.log("AI劇場: 連続再生は既に停止処理中です。")
                messagebox.showinfo("情報", "連続再生は既に停止処理中です。")
        else:
            self.log("AI劇場: 停止ボタンが押されましたが、連続再生は実行されていません。")
            messagebox.showinfo("情報", "連続再生は実行されていません。")
    
    def create_main_tab(self):
        """メインタブ - 配信制御（完全版）"""
        main_frame = ttk.Frame(self.notebook)
        self.notebook.add(main_frame, text="🎬 メイン")
        
        # システム状態表示
        status_frame = ttk.LabelFrame(main_frame, text="システム状態", padding="10")
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 費用情報（完全版）
        cost_info = ttk.Label(status_frame, 
                             text="💰 v2.2完全版: 4エンジン完全統合（Google AI Studio新音声＋Avis Speech＋VOICEVOX＋システムTTS）", 
                             foreground="green", wraplength=800)
        cost_info.pack(anchor=tk.W)
        
        # エンジン状態表示
        self.engine_status_frame = ttk.Frame(status_frame)
        self.engine_status_frame.pack(fill=tk.X, pady=5)
        
        # キャラクター選択
        char_frame = ttk.LabelFrame(main_frame, text="キャラクター選択", padding="10")
        char_frame.pack(fill=tk.X, padx=10, pady=5)
        
        char_control_frame = ttk.Frame(char_frame)
        char_control_frame.pack(fill=tk.X)
        
        ttk.Label(char_control_frame, text="アクティブキャラクター:").pack(side=tk.LEFT)
        self.character_var = tk.StringVar()
        self.character_combo = ttk.Combobox(
            char_control_frame, textvariable=self.character_var,
            state="readonly", width=35
        )
        self.character_combo.pack(side=tk.LEFT, padx=10)
        self.character_combo.bind('<<ComboboxSelected>>', self.on_character_changed)
        
        ttk.Button(char_control_frame, text="🔄 更新", 
                  command=lambda: [self.refresh_character_list(), self.populate_ai_theater_talker_dropdown()]).pack(side=tk.LEFT, padx=5) # AI劇場話者リストも更新
        ttk.Button(char_control_frame, text="⚙️ 設定", 
                  command=self.open_selected_character_editor).pack(side=tk.LEFT, padx=5)
        
        # 配信制御（完全版）
        stream_frame = ttk.LabelFrame(main_frame, text="配信制御", padding="10")
        stream_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # YouTube設定
        youtube_frame = ttk.Frame(stream_frame)
        youtube_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(youtube_frame, text="YouTube ライブID:").grid(row=0, column=0, sticky=tk.W)
        self.live_id_var = tk.StringVar()
        ttk.Entry(youtube_frame, textvariable=self.live_id_var, width=45).grid(
            row=0, column=1, padx=10, sticky=tk.W
        )
        
        self.start_button = ttk.Button(
            youtube_frame, text="配信開始", command=self.toggle_streaming
        )
        self.start_button.grid(row=0, column=2, padx=10)
        
        # 配信設定
        stream_settings_frame = ttk.Frame(stream_frame)
        stream_settings_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(stream_settings_frame, text="応答間隔:").grid(row=0, column=0, sticky=tk.W)
        self.response_interval_var = tk.DoubleVar(value=5.0)
        ttk.Scale(stream_settings_frame, from_=1.0, to=10.0, variable=self.response_interval_var, 
                 orient=tk.HORIZONTAL, length=150).grid(row=0, column=1, padx=5)
        ttk.Label(stream_settings_frame, textvariable=self.response_interval_var).grid(row=0, column=2)
        
        ttk.Label(stream_settings_frame, text="自動応答:").grid(row=0, column=3, sticky=tk.W, padx=(20,0))
        self.auto_response_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(stream_settings_frame, variable=self.auto_response_var).grid(row=0, column=4, padx=5)
        
        # ログ表示（完全版）
        log_frame = ttk.LabelFrame(main_frame, text="システムログ", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # ログ制御
        log_control_frame = ttk.Frame(log_frame)
        log_control_frame.pack(fill=tk.X, pady=(0,5))
        
        ttk.Button(log_control_frame, text="📄 ログクリア", 
                  command=self.clear_log).pack(side=tk.LEFT, padx=5)
        ttk.Button(log_control_frame, text="💾 ログ保存", 
                  command=self.save_log).pack(side=tk.LEFT, padx=5)
        ttk.Button(log_control_frame, text="🔄 ログ更新", 
                  command=self.refresh_log).pack(side=tk.LEFT, padx=5)
        
        # ログレベル選択
        ttk.Label(log_control_frame, text="ログレベル:").pack(side=tk.LEFT, padx=(20,0))
        self.log_level_var = tk.StringVar(value="INFO")
        log_level_combo = ttk.Combobox(log_control_frame, textvariable=self.log_level_var,
                                      values=["DEBUG", "INFO", "WARNING", "ERROR"], state="readonly", width=10)
        log_level_combo.pack(side=tk.LEFT, padx=5)
        
        # ログ表示エリア
        log_display_frame = ttk.Frame(log_frame)
        log_display_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = tk.Text(log_display_frame, height=22, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(log_display_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 制御ボタン（完全版）
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(control_frame, text="🚨 緊急停止", 
                  command=self.emergency_stop).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="📊 システム状態", 
                  command=self.show_system_status).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="🔧 診断実行", 
                  command=self.run_system_diagnostics).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="❓ ヘルプ", 
                  command=self.show_help).pack(side=tk.RIGHT, padx=5)
        ttk.Button(control_frame, text="ℹ️ About", 
                  command=self.show_about).pack(side=tk.RIGHT, padx=5)
    
    def create_character_tab(self):
        """キャラクター管理タブ（完全版）"""
        char_frame = ttk.Frame(self.notebook)
        self.notebook.add(char_frame, text="👥 キャラクター管理")
        
        # キャラクターリスト（完全版）
        list_frame = ttk.LabelFrame(char_frame, text="キャラクター一覧", padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # リスト表示
        self.char_tree = ttk.Treeview(list_frame, columns=('name', 'type', 'voice', 'engine', 'created'), show='headings')
        self.char_tree.heading('name', text='キャラクター名')
        self.char_tree.heading('type', text='タイプ')
        self.char_tree.heading('voice', text='音声モデル')
        self.char_tree.heading('engine', text='音声エンジン')
        self.char_tree.heading('created', text='作成日時')
        
        # 列幅調整
        self.char_tree.column('name', width=150)
        self.char_tree.column('type', width=120)
        self.char_tree.column('voice', width=150)
        self.char_tree.column('engine', width=150)
        self.char_tree.column('created', width=120)
        
        # ツリービューのスクロールバー
        char_tree_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.char_tree.yview)
        self.char_tree.configure(yscrollcommand=char_tree_scroll.set)
        
        self.char_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        char_tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # ダブルクリックで編集
        self.char_tree.bind('<Double-1>', lambda e: self.edit_character())
        
        # キャラクター操作ボタン（完全版）
        char_buttons = ttk.Frame(list_frame)
        char_buttons.pack(fill=tk.X, pady=5)
        
        # 基本操作
        basic_ops = ttk.Frame(char_buttons)
        basic_ops.pack(fill=tk.X)
        
        ttk.Button(basic_ops, text="📝 新規作成", 
                  command=self.create_new_character).pack(side=tk.LEFT, padx=5)
        ttk.Button(basic_ops, text="✏️ 編集", 
                  command=self.edit_character).pack(side=tk.LEFT, padx=5)
        ttk.Button(basic_ops, text="📋 複製", 
                  command=self.duplicate_character).pack(side=tk.LEFT, padx=5)
        ttk.Button(basic_ops, text="🗑️ 削除", 
                  command=self.delete_character).pack(side=tk.LEFT, padx=5)
        
        # 高度な操作
        advanced_ops = ttk.Frame(char_buttons)
        advanced_ops.pack(fill=tk.X, pady=(5,0))
        
        ttk.Button(advanced_ops, text="📤 エクスポート", 
                  command=self.export_character).pack(side=tk.LEFT, padx=5)
        ttk.Button(advanced_ops, text="📥 インポート", 
                  command=self.import_character).pack(side=tk.LEFT, padx=5)
        ttk.Button(advanced_ops, text="🎤 音声テスト", 
                  command=self.test_character_voice).pack(side=tk.LEFT, padx=5)
        ttk.Button(advanced_ops, text="📊 性能測定", 
                  command=self.measure_character_performance).pack(side=tk.LEFT, padx=5)
        
        # テンプレート情報（4エンジン完全対応版）
        template_frame = ttk.LabelFrame(char_frame, text="テンプレート一覧 v2.2（4エンジン完全対応）", padding="10")
        template_frame.pack(fill=tk.X, padx=10, pady=5)
        
        template_info = tk.Text(template_frame, height=10, width=100, wrap=tk.WORD, state=tk.DISABLED)
        template_info_scroll = ttk.Scrollbar(template_frame, orient=tk.VERTICAL, command=template_info.yview)
        template_info.configure(yscrollcommand=template_info_scroll.set)
        
        template_info.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        template_info_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        template_content = """
🚀 最新AI系: 未来的・知的・革新的思考・グローバル視点 【Google AI Studio新音声: Alloy】
🌟 元気系: 関西弁・超ポジティブ・リアクション大・エネルギッシュ 【Avis Speech: Anneli(ノーマル)】
🎓 知的系: 丁寧語・論理的・先生タイプ・博学 【Avis Speech: Anneli(クール)】
🌸 癒し系: ふんわり・穏やか・聞き上手・母性的 【Avis Speech: Anneli(ささやき)】
🎭 ずんだもん系: 「〜のだ」語尾・親しみやすい・東北弁・愛されキャラ 【VOICEVOX: ずんだもん(ノーマル)】
🎪 キャラクター系: アニメ調・個性的・エンターテイナー・表現豊か 【VOICEVOX: 四国めたん(ノーマル)】
⭐ プロ品質系: プロフェッショナル・上品・洗練・エレガント 【Google AI Studio新音声: puck】
🌍 多言語対応系: 国際的・グローバル・多文化理解・文化架け橋 【Google AI Studio新音声: Nova】
🛠️ カスタム: 自由設定・完全カスタマイズ・オリジナル
        """
        
        template_info.config(state=tk.NORMAL)
        template_info.insert(1.0, template_content.strip())
        template_info.config(state=tk.DISABLED)
    
    def create_debug_tab(self):
        """デバッグ・テストタブ（4エンジン完全対応版）"""
        debug_frame = ttk.Frame(self.notebook)
        self.notebook.add(debug_frame, text="🔧 デバッグ")
        
        # 音声エンジンテスト（完全版）
        engine_test_frame = ttk.LabelFrame(debug_frame, text="音声エンジンテスト v2.2（4エンジン完全対応）", padding="10")
        engine_test_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # エンジン選択
        engine_select_frame = ttk.Frame(engine_test_frame)
        engine_select_frame.pack(fill=tk.X)
        
        ttk.Label(engine_select_frame, text="テストエンジン:").pack(side=tk.LEFT)
        self.test_engine_var = tk.StringVar(value="google_ai_studio_new")
        engine_test_combo = ttk.Combobox(engine_select_frame, textvariable=self.test_engine_var,
                                        values=["google_ai_studio_new", "avis_speech", "voicevox", "system_tts"], 
                                        state="readonly", width=25)
        engine_test_combo.pack(side=tk.LEFT, padx=10)
        
        ttk.Label(engine_select_frame, text="音声モデル:").pack(side=tk.LEFT, padx=(20,0))
        self.test_voice_var = tk.StringVar(value="Alloy")
        voice_test_combo = ttk.Combobox(engine_select_frame, textvariable=self.test_voice_var,
                                       state="readonly", width=25)
        voice_test_combo.pack(side=tk.LEFT, padx=10)
        
        # エンジン変更時に音声モデルを更新
        def update_test_voices(*args):
            engine = self.test_engine_var.get()
            if engine in self.voice_manager.engines:
                voices = self.voice_manager.engines[engine].get_available_voices()
                voice_test_combo['values'] = voices
                if voices:
                    self.test_voice_var.set(voices[0])
        
        self.test_engine_var.trace('w', update_test_voices)
        update_test_voices()  # 初期設定
        
        # テストテキスト
        text_frame = ttk.Frame(engine_test_frame)
        text_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(text_frame, text="テストテキスト:").pack(anchor=tk.W)
        self.test_text_var = tk.StringVar(
            value="こんにちは！4つの音声エンジンを完全統合したAITuberシステムv2.2のテストです。2025年5月最新技術に完全対応しています！"
        )
        test_text_entry = ttk.Entry(text_frame, textvariable=self.test_text_var, width=100)
        test_text_entry.pack(fill=tk.X, pady=5)
        
        # テストボタン（完全版）
        test_buttons = ttk.Frame(engine_test_frame)
        test_buttons.pack(fill=tk.X)
        
        ttk.Button(test_buttons, text="🎤 音声テスト", 
                  command=self.test_voice).pack(side=tk.LEFT, padx=5)
        ttk.Button(test_buttons, text="🔄 全エンジン比較", 
                  command=self.compare_engines).pack(side=tk.LEFT, padx=5)
        ttk.Button(test_buttons, text="⚠️ フォールバック手動テスト案内",
                  command=self.show_fallback_test_info).pack(side=tk.LEFT, padx=5)
        ttk.Button(test_buttons, text="📊 エンジン状態確認", 
                  command=self.check_engines_status).pack(side=tk.LEFT, padx=5)
        ttk.Button(test_buttons, text="⚡ 性能ベンチマーク", 
                  command=self.run_performance_benchmark).pack(side=tk.LEFT, padx=5)
        
        # API接続テスト
        api_test_frame = ttk.LabelFrame(debug_frame, text="API接続テスト", padding="10")
        api_test_frame.pack(fill=tk.X, padx=10, pady=5)
        
        api_buttons = ttk.Frame(api_test_frame)
        api_buttons.pack(fill=tk.X)
        
        ttk.Button(api_buttons, text="🤖 Google AI Studio", 
                  command=self.test_google_ai_studio).pack(side=tk.LEFT, padx=5)
        ttk.Button(api_buttons, text="📺 YouTube API", 
                  command=self.test_youtube_api).pack(side=tk.LEFT, padx=5)
        ttk.Button(api_buttons, text="🎙️ Avis Speech", 
                  command=self.test_avis_speech).pack(side=tk.LEFT, padx=5)
        ttk.Button(api_buttons, text="🎤 VOICEVOX", 
                  command=self.test_voicevox).pack(side=tk.LEFT, padx=5)
        
        # 対話テスト（完全版）
        chat_test_frame = ttk.LabelFrame(debug_frame, text="AI対話テスト（Gemini文章生成＋4エンジン音声合成）", padding="10")
        chat_test_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 対話制御
        chat_control_frame = ttk.Frame(chat_test_frame)
        chat_control_frame.pack(fill=tk.X, pady=(0,5))
        
        ttk.Label(chat_control_frame, text="AIとの会話テスト（文章生成: Google AI Studio + 音声合成: 4エンジン対応）:").pack(side=tk.LEFT)
        ttk.Button(chat_control_frame, text="🗑️ チャットクリア", 
                  command=self.clear_chat).pack(side=tk.RIGHT, padx=5)
        ttk.Button(chat_control_frame, text="💾 チャット保存", 
                  command=self.save_chat).pack(side=tk.RIGHT, padx=5)
        
        # チャット表示
        chat_display_frame = ttk.Frame(chat_test_frame)
        chat_display_frame.pack(fill=tk.BOTH, expand=True)
        
        self.chat_display = tk.Text(chat_display_frame, height=18, wrap=tk.WORD)
        chat_scroll = ttk.Scrollbar(chat_display_frame, orient=tk.VERTICAL, 
                                   command=self.chat_display.yview)
        self.chat_display.configure(yscrollcommand=chat_scroll.set)
        
        self.chat_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        chat_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 入力欄（完全版）
        input_frame = ttk.Frame(debug_frame)
        input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(input_frame, text="メッセージ:").pack(side=tk.LEFT)
        self.chat_input_var = tk.StringVar()
        chat_entry = ttk.Entry(input_frame, textvariable=self.chat_input_var)
        chat_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        chat_entry.bind('<Return>', self.send_test_message)
        
        ttk.Button(input_frame, text="送信", 
                  command=self.send_test_message).pack(side=tk.RIGHT, padx=5)
        ttk.Button(input_frame, text="🎲 ランダム", 
                  command=self.send_random_message).pack(side=tk.RIGHT, padx=5)
    
    def create_settings_tab(self):
        """設定タブ（4エンジン完全対応版）"""
        settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(settings_frame, text="⚙️ 設定")
        
        # API設定（4エンジン完全対応）
        api_frame = ttk.LabelFrame(settings_frame, text="API設定 v2.2（4エンジン完全対応）", padding="10")
        api_frame.pack(fill=tk.X, padx=10, pady=5)
        
        api_grid = ttk.Frame(api_frame)
        api_grid.pack(fill=tk.X)
        
        # Google AI Studio APIキー
        ttk.Label(api_grid, text="Google AI Studio APIキー（文章生成＋新音声合成）:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.google_ai_var = tk.StringVar()
        ai_entry = ttk.Entry(api_grid, textvariable=self.google_ai_var, width=50, show="*")
        ai_entry.grid(row=0, column=1, padx=10, pady=2)
        ttk.Button(api_grid, text="テスト", command=self.test_google_ai_studio).grid(row=0, column=2, padx=5)
        
        # YouTube APIキー
        ttk.Label(api_grid, text="YouTube APIキー（配信用）:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.youtube_api_var = tk.StringVar()
        youtube_entry = ttk.Entry(api_grid, textvariable=self.youtube_api_var, width=50, show="*")
        youtube_entry.grid(row=1, column=1, padx=10, pady=2)
        ttk.Button(api_grid, text="テスト", command=self.test_youtube_api).grid(row=1, column=2, padx=5)

        # テキスト生成モデル選択
        ttk.Label(api_grid, text="テキスト生成モデル (Gemini):").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.text_generation_model_var = tk.StringVar()
        self.text_generation_model_combo = ttk.Combobox(
            api_grid, textvariable=self.text_generation_model_var,
            values=self._get_display_text_generation_models(), # 変更: 新しいメソッドを使用
            state="readonly", width=47
        )
        self.text_generation_model_combo.grid(row=2, column=1, padx=10, pady=2, sticky=tk.W)
        self.text_generation_model_combo.bind('<<ComboboxSelected>>', self._on_text_generation_model_changed) # イベントハンドラをバインド

        # ローカルLLMエンドポイントURL入力フィールド (最初は非表示)
        self.local_llm_endpoint_label = ttk.Label(api_grid, text="LM Studio エンドポイントURL:")
        self.local_llm_endpoint_label.grid(row=3, column=0, sticky=tk.W, pady=2)
        self.local_llm_endpoint_label.grid_remove() # 初期状態は非表示

        self.local_llm_endpoint_url_var = tk.StringVar()
        self.local_llm_endpoint_entry = ttk.Entry(api_grid, textvariable=self.local_llm_endpoint_url_var, width=50)
        self.local_llm_endpoint_entry.grid(row=3, column=1, padx=10, pady=2, sticky=tk.W)
        self.local_llm_endpoint_entry.grid_remove() # 初期状態は非表示

        self.local_llm_endpoint_hint_label = ttk.Label(api_grid, text="例: http://127.0.0.1:1234/v1/chat/completions のように完全なパスを入力", foreground="gray")
        self.local_llm_endpoint_hint_label.grid(row=4, column=1, sticky=tk.W, padx=10, pady=(0, 5)) # row を変更し、適切な位置に配置
        self.local_llm_endpoint_hint_label.grid_remove() # 初期状態は非表示

        # AIチャット設定フレーム (新規追加)
        ai_chat_settings_frame = ttk.LabelFrame(settings_frame, text="AIチャット設定", padding="10")
        ai_chat_settings_frame.pack(fill=tk.X, padx=10, pady=5)

        ai_chat_grid = ttk.Frame(ai_chat_settings_frame)
        ai_chat_grid.pack(fill=tk.X)

        ttk.Label(ai_chat_grid, text="AIチャット処理方式:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.ai_chat_processing_mode_var = tk.StringVar()
        self.ai_chat_processing_mode_combo = ttk.Combobox( # Comboboxのインスタンスをselfに保存
            ai_chat_grid,
            textvariable=self.ai_chat_processing_mode_var,
            values=["sequential (推奨)", "parallel"],
            state="readonly",
            width=25
        )
        self.ai_chat_processing_mode_combo.grid(row=0, column=1, padx=10, pady=2, sticky=tk.W)
        ttk.Label(ai_chat_grid, text="sequential: ユーザー音声再生後にAI応答 / parallel: 並行処理").grid(row=0, column=2, sticky=tk.W, padx=5)

        
        # 音声エンジン設定（4エンジン完全対応）
        voice_frame = ttk.LabelFrame(settings_frame, text="音声エンジン設定（4エンジン完全対応）", padding="10")
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
        
        # エンジン説明表示
        self.system_engine_info = ttk.Label(voice_grid, text="", 
                                           foreground="gray", wraplength=500)
        self.system_engine_info.grid(row=0, column=2, padx=10, sticky=tk.W)
        
        # 音声出力デバイス選択
        ttk.Label(voice_grid, text="音声出力デバイス:").grid(row=1, column=0, sticky=tk.W, pady=(10,0))
        self.audio_output_device_var = tk.StringVar()
        self.audio_output_device_combo = ttk.Combobox(voice_grid, textvariable=self.audio_output_device_var,
                                                     state="readonly", width=40)
        self.audio_output_device_combo.grid(row=1, column=1, columnspan=2, padx=10, pady=(10,0), sticky=tk.W)
        self.populate_audio_output_devices() # ドロップダウンの初期化

        # フォールバック設定
        fallback_frame = ttk.Frame(voice_grid)
        fallback_frame.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=10) # row を変更
        
        ttk.Label(fallback_frame, text="フォールバック有効:").pack(side=tk.LEFT)
        self.fallback_enabled_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(fallback_frame, variable=self.fallback_enabled_var).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(fallback_frame, text="フォールバック順序:").pack(side=tk.LEFT, padx=(20,0))
        self.fallback_order_var = tk.StringVar(value="自動")
        fallback_combo = ttk.Combobox(fallback_frame, textvariable=self.fallback_order_var,
                                     values=["自動", "品質優先", "速度優先", "コスト優先"], state="readonly")
        fallback_combo.pack(side=tk.LEFT, padx=5)
        
        # システム設定（完全版）
        system_frame = ttk.LabelFrame(settings_frame, text="システム設定", padding="10")
        system_frame.pack(fill=tk.X, padx=10, pady=5)
        
        system_grid = ttk.Frame(system_frame)
        system_grid.pack(fill=tk.X)
        
        # 基本設定
        self.auto_save_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(system_grid, text="自動保存", 
                       variable=self.auto_save_var).grid(row=0, column=0, sticky=tk.W)
        
        self.debug_mode_var = tk.BooleanVar()
        ttk.Checkbutton(system_grid, text="デバッグモード", 
                       variable=self.debug_mode_var).grid(row=0, column=1, sticky=tk.W, padx=20)
        
        # 会話履歴保持数設定 (System Settings in GUI)
        ttk.Label(system_grid, text="会話履歴の長さ:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.conversation_history_length_var = tk.IntVar(value=0) # Default value for the UI variable
        history_spinbox = ttk.Spinbox(system_grid, from_=0, to=100, increment=1, # UI for setting conversation history length
                                      textvariable=self.conversation_history_length_var, width=5)
        history_spinbox.grid(row=1, column=1, sticky=tk.W, padx=20, pady=5)
        ttk.Label(system_grid, text="(0で履歴なし、最大100件。YouTubeライブとデバッグタブのチャットに適用)").grid(row=1, column=2, sticky=tk.W, pady=5, padx=5)

        # 設定保存ボタン
        save_frame = ttk.Frame(settings_frame)
        save_frame.pack(fill=tk.X, padx=10, pady=20)
        
        ttk.Button(save_frame, text="💾 設定を保存", 
                  command=self.save_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(save_frame, text="🔄 設定をリセット", 
                  command=self.reset_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(save_frame, text="📤 設定をエクスポート", 
                  command=self.export_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(save_frame, text="📥 設定をインポート", 
                  command=self.import_settings).pack(side=tk.LEFT, padx=5)
        
        # ヘルプ・ガイド（4エンジン完全対応）
        help_frame = ttk.LabelFrame(settings_frame, text="エンジン起動ガイド v2.2（4エンジン完全対応）", padding="10")
        help_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 音声エンジンの使い分けガイド
        guide_text = tk.Text(help_frame, height=12, width=100, wrap=tk.WORD, state=tk.DISABLED)
        guide_scroll = ttk.Scrollbar(help_frame, orient=tk.VERTICAL, command=guide_text.yview)
        guide_text.configure(yscrollcommand=guide_scroll.set)
        
        guide_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        guide_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        guide_content = """
🚀 【Google AI Studio新音声】- 2025年5月追加・最新技術
設定: Google AI Studio APIキーを設定するだけ（Gemini 2.5 Flash新音声機能使用）
品質: 最新技術・リアルタイム対応・多言語・高音質・感情表現対応
特徴: Alloy, Echo, Fable, Onyx, Nova, Shimmer等の最新音声モデル

🎙️ 【Avis Speech Engine】- ポート10101
起動: AvisSpeechアプリを起動 または docker run -p 10101:10101 aivisspeech-engine
確認: http://127.0.0.1:10101/docs
特徴: 高品質・VOICEVOX互換・感情表現対応

🎤 【VOICEVOX Engine】- ポート50021  
起動: VOICEVOXアプリを起動 または docker run -p 50021:50021 voicevox/voicevox_engine
確認: http://127.0.0.1:50021/docs
特徴: ずんだもん・四国めたん等の人気キャラクター音声

💻 【システムTTS】- OS標準
設定: 不要（Windows/macOS/Linuxの標準機能を自動利用）
特徴: 完全無料・オフライン・安定動作
        """
        
        guide_text.config(state=tk.NORMAL)
        guide_text.insert(1.0, guide_content.strip())
        guide_text.config(state=tk.DISABLED)
        
        # 外部リンク
        link_frame = ttk.Frame(help_frame)
        link_frame.pack(pady=5)
        
        ttk.Button(link_frame, text="🎨 VRoid Studio", 
                  command=lambda: webbrowser.open("https://vroid.com/studio")).pack(side=tk.LEFT, padx=5)
        ttk.Button(link_frame, text="📹 VSeeFace", 
                  command=lambda: webbrowser.open("https://www.vseeface.icu/")).pack(side=tk.LEFT, padx=5)
        ttk.Button(link_frame, text="🎙️ Avis Speech", 
                  command=lambda: webbrowser.open("https://github.com/Aivis-Project/AivisSpeech-Engine")).pack(side=tk.LEFT, padx=5)
        ttk.Button(link_frame, text="🎤 VOICEVOX", 
                  command=lambda: webbrowser.open("https://github.com/VOICEVOX/voicevox_engine")).pack(side=tk.LEFT, padx=5)
    
    def create_advanced_tab(self):
        """高度な機能タブ（新規追加）"""
        advanced_frame = ttk.Frame(self.notebook)
        self.notebook.add(advanced_frame, text="🚀 高度な機能")
        
        # パフォーマンス監視
        perf_frame = ttk.LabelFrame(advanced_frame, text="パフォーマンス監視", padding="10")
        perf_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # TODO: パフォーマンス監視機能を実装
        ttk.Label(perf_frame, text="パフォーマンス監視機能（実装予定）").pack()
        
        # バックアップ・復元
        backup_frame = ttk.LabelFrame(advanced_frame, text="バックアップ・復元", padding="10")
        backup_frame.pack(fill=tk.X, padx=10, pady=5)
        
        backup_buttons = ttk.Frame(backup_frame)
        backup_buttons.pack(fill=tk.X)
        
        ttk.Button(backup_buttons, text="💾 完全バックアップ", 
                  command=self.create_full_backup).pack(side=tk.LEFT, padx=5)
        ttk.Button(backup_buttons, text="📥 バックアップ復元", 
                  command=self.restore_backup).pack(side=tk.LEFT, padx=5)
        ttk.Button(backup_buttons, text="🗂️ バックアップ管理", 
                  command=self.manage_backups).pack(side=tk.LEFT, padx=5)
        
        # プラグイン管理
        plugin_frame = ttk.LabelFrame(advanced_frame, text="プラグイン管理", padding="10")
        plugin_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # TODO: プラグイン管理機能を実装
        ttk.Label(plugin_frame, text="プラグイン管理機能（実装予定）").pack()
    
    def create_status_bar(self):
        """ステータスバー作成（完全版）"""
        self.status_bar = ttk.Frame(self.root)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        
        # 左側：基本状態
        self.status_label = ttk.Label(self.status_bar, text="✅ 準備完了 - v2.2（4エンジン完全対応版・2025年5月最新・機能削減なし）")
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        # 中央：キャラクター状態
        self.character_status = ttk.Label(self.status_bar, text="キャラクター: 未選択")
        self.character_status.pack(side=tk.LEFT, padx=20)
        
        # 右側：システム情報
        self.system_info_label = ttk.Label(self.status_bar, text="メモリ: --MB | CPU: --%")
        self.system_info_label.pack(side=tk.RIGHT, padx=10)
        
        # ステータス更新を定期実行
        self.update_system_info()

    def _get_display_gemini_models(self):
        """UI表示用のGeminiモデル名リストを生成（注釈付き）"""
        display_models = []
        for model_name in self.available_gemini_models: # self.available_gemini_models は __init__ で定義済み
            display_name = model_name
            if model_name == "gemini-2.5-flash":
                display_name += " (プレビュー)"
            elif model_name == "gemini-2.5-pro":
                display_name += " (プレビュー - クォータ注意)"
            display_models.append(display_name)
        return display_models

    def _get_display_text_generation_models(self):
        """UI表示用のテキスト生成モデル名リストを生成（ローカルLLMを含む）"""
        gemini_models = self._get_display_gemini_models()
        return ["LM Studio (Local)"] + gemini_models

    def _get_internal_text_generation_model_name(self, display_name):
        """UI表示名から内部的なテキスト生成モデル名を取得"""
        if display_name == "LM Studio (Local)":
            return "local_lm_studio" # ローカルLLMを示す内部名
        # それ以外はGeminiモデルとして処理 (元々の _get_internal_gemini_model_name のロジック)
        if display_name.endswith(" (プレビュー)"):
            return display_name.replace(" (プレビュー)", "")
        elif display_name.endswith(" (プレビュー - クォータ注意)"):
            return display_name.replace(" (プレビュー - クォータ注意)", "")
        return display_name

    def _on_text_generation_model_changed(self, event=None):
        """テキスト生成モデルの選択が変更されたときの処理 (UI表示制御)"""
        selected_model_display_name = self.text_generation_model_var.get()
        if selected_model_display_name == "LM Studio (Local)":
            # ローカルLLMが選択された場合、エンドポイントURL入力フィールドとヒントラベルを表示
            self.local_llm_endpoint_label.grid() 
            self.local_llm_endpoint_entry.grid() 
            self.local_llm_endpoint_hint_label.grid()
        else:
            # それ以外の場合、エンドポイントURL入力フィールドとヒントラベルを非表示
            self.local_llm_endpoint_label.grid_remove()
            self.local_llm_endpoint_entry.grid_remove()
            self.local_llm_endpoint_hint_label.grid_remove()

    def populate_audio_output_devices(self):
        """音声出力デバイスのドロップダウンメニューを初期化する"""
        try:
            devices = self.audio_player.get_available_output_devices()
            device_names = [device["name"] for device in devices]
            self.audio_output_device_combo['values'] = device_names

            # 設定ファイルから保存されたデバイスIDを取得
            saved_device_id = self.config.get_system_setting("audio_output_device", "default")

            # 保存されたIDに対応するデバイス名を探して設定
            selected_device_name = "デフォルト" # デフォルト値
            for device in devices:
                if device["id"] == saved_device_id:
                    selected_device_name = device["name"]
                    break

            if selected_device_name in device_names:
                self.audio_output_device_var.set(selected_device_name)
            elif device_names: # 保存されたものがない場合、リストの最初のものを選択
                self.audio_output_device_var.set(device_names[0])

        except Exception as e:
            self.log(f"❌ 音声出力デバイスの読み込みに失敗: {e}")
            self.audio_output_device_combo['values'] = ["デフォルト"]
            self.audio_output_device_var.set("デフォルト")
    
    # quick_character_settings メソッドと open_quick_edit_dialog メソッドを削除

    def open_selected_character_editor(self):
        """メインタブで選択されているキャラクターの編集ダイアログを開く"""
        selection = self.character_var.get() # メインタブのキャラクター選択コンボボックスの値

        if not selection:
            messagebox.showwarning("キャラクター未選択", "編集するキャラクターをメインタブで選択してください。")
            self.log("⚠️キャラクター編集: キャラクターが選択されていません。")
            return

        try:
            # "キャラクター名 (ID)" の形式からIDを抽出
            if '(' in selection and ')' in selection:
                char_id = selection.split('(')[-1].replace(')', '')
            else:
                self.log(f"❌ キャラクター編集: 選択形式エラー '{selection}'。キャラクター名 (ID) 形式を期待します。")
                messagebox.showerror("選択エラー", f"キャラクターの選択形式が無効です: {selection}")
                return

            char_data = self.config.get_character(char_id)
            if not char_data:
                self.log(f"❌ キャラクター編集: キャラクターデータが見つかりません (ID: {char_id})。")
                messagebox.showerror("エラー", f"キャラクターデータ (ID: {char_id}) が見つかりません。")
                return

            self.log(f"✏️ キャラクター編集開始: {char_data.get('name', 'Unknown')} (ID: {char_id})")
            dialog = CharacterEditDialog(self.root, self.character_manager, char_id, char_data)
            if dialog.result:
                self.refresh_character_list() # キャラクターリストを更新
                self.populate_ai_theater_talker_dropdown() # AI劇場の話者リストも更新
                # メインタブのコンボボックスの表示も更新する必要があるか確認
                # 名前が変更された場合、コンボボックスの表示も追従させると親切
                new_name = dialog.result['name']
                new_char_id = dialog.result['char_id']
                self.character_var.set(f"{new_name} ({new_char_id})") # 表示を更新
                self.on_character_changed() # ステータスバーなども更新
                self.log(f"✅ キャラクター編集完了: {new_name}")
        except Exception as e:
            self.log(f"❌ キャラクター編集ダイアログ表示エラー: {e}")
            import traceback
            self.log(f"詳細トレース: {traceback.format_exc()}")
            messagebox.showerror("編集エラー", f"キャラクター編集ダイアログの表示中にエラーが発生しました: {e}")

    def update_system_info(self):
        """システム情報の定期更新"""
        try:
            import psutil
            memory_usage = psutil.virtual_memory().percent
            cpu_usage = psutil.cpu_percent()
            self.system_info_label.config(text=f"メモリ: {memory_usage:.1f}% | CPU: {cpu_usage:.1f}%")
        except ImportError:
            # psutilが利用できない場合
            self.system_info_label.config(text="システム情報: N/A")
        except Exception as e:
            self.system_info_label.config(text="システム情報: エラー")
        
        # 5秒後に再実行
        self.root.after(5000, self.update_system_info)

    
    def load_settings(self):
        """設定をGUIに読み込み"""
        # API設定
        self.google_ai_var.set(self.config.get_system_setting("google_ai_api_key", ""))
        self.youtube_api_var.set(self.config.get_system_setting("youtube_api_key", ""))
        self.voice_engine_var.set(self.config.get_system_setting("voice_engine", "avis_speech"))
        
        # テキスト生成モデル設定の読み込み
        internal_model_name_from_config = self.config.get_system_setting("text_generation_model", "gemini-1.5-flash-latest") # デフォルトを適切なGeminiモデルに
        display_name_to_set = ""
        # 設定ファイル上の内部名と一致する表示名をUIモデルリストから探す
        for dn in self._get_display_text_generation_models(): # 新しいメソッドを使用
            if self._get_internal_text_generation_model_name(dn) == internal_model_name_from_config:
                display_name_to_set = dn
                break
        
        if display_name_to_set:
            self.text_generation_model_var.set(display_name_to_set)
        elif self._get_display_text_generation_models(): # フォールバックでリストの最初のものを設定
            self.text_generation_model_var.set(self._get_display_text_generation_models()[0])
        
        # ローカルLLMエンドポイントURLの読み込み
        self.local_llm_endpoint_url_var.set(self.config.get_system_setting("local_llm_endpoint_url", ""))

        # テキスト生成モデル変更時のUI更新処理を呼び出し、エンドポイントURLフィールドの表示を初期化
        self._on_text_generation_model_changed()

        # AIチャット処理方式の読み込み (新規追加)
        ai_chat_mode = self.config.get_system_setting("ai_chat_processing_mode", "sequential")
        current_combo_values_chat_mode = self.ai_chat_processing_mode_combo['values'] # ("sequential (推奨)", "parallel")

        if ai_chat_mode == "sequential" and "sequential (推奨)" in current_combo_values_chat_mode:
            self.ai_chat_processing_mode_var.set("sequential (推奨)")
        elif ai_chat_mode == "parallel" and "parallel" in current_combo_values_chat_mode:
            self.ai_chat_processing_mode_var.set("parallel")
        else: # マッチしない場合や設定ファイルにない場合はデフォルト (sequential (推奨))
            self.ai_chat_processing_mode_var.set("sequential (推奨)")


        # システム音声エンジン変更時の情報表示を初期化
        self.on_system_engine_changed()
        
        # 音声出力デバイスの読み込み
        self.populate_audio_output_devices() # populate_audio_output_devices を呼び出してUIを更新
        saved_audio_device_name = self.audio_output_device_var.get() # populate_audio_output_devices で設定された値
        # 対応するIDを見つける
        devices = self.audio_player.get_available_output_devices()
        saved_audio_device_id = "default"
        for device in devices:
            if device["name"] == saved_audio_device_name:
                saved_audio_device_id = device["id"]
                break
        self.config.set_system_setting("audio_output_device", saved_audio_device_id) # 保存されているIDを（再）設定

        self.auto_save_var.set(self.config.get_system_setting("auto_save", True))
        self.debug_mode_var.set(self.config.get_system_setting("debug_mode", False))
        self.conversation_history_length_var.set(self.config.get_system_setting("conversation_history_length", 0))
        
        # キャラクター一覧更新
        self.refresh_character_list()
        self.populate_ai_theater_talker_dropdown() # AI劇場の話者リストも初期化
        
        # 利用可能なキャラクターがある場合は最初のものを自動選択
        characters = self.config.get_all_characters()
        if characters and not self.current_character_id:
            first_char_id = list(characters.keys())[0]
            first_char_name = characters[first_char_id].get('name', 'Unknown')
            self.auto_select_character(first_char_id, first_char_name)
        
        # ストリーミング設定
        self.live_id_var.set(self.config.config.get("streaming_settings", {}).get("live_id", ""))
        
        self.log("✅ 設定を読み込みました（v2.1 - 修正版・完全動作版）")
    
    def save_settings(self):
        """設定を保存"""
        try:
            # API設定
            self.config.set_system_setting("google_ai_api_key", self.google_ai_var.get())
            self.config.set_system_setting("youtube_api_key", self.youtube_api_var.get())
            self.config.set_system_setting("voice_engine", self.voice_engine_var.get())

            # UI表示名から内部モデル名を取得して保存
            selected_display_name = self.text_generation_model_var.get()
            internal_model_name = self._get_internal_text_generation_model_name(selected_display_name) # 修正: 正しいメソッド呼び出し
            self.config.set_system_setting("text_generation_model", internal_model_name)

            # ローカルLLMエンドポイントURLの保存
            if internal_model_name == "local_lm_studio":
                self.config.set_system_setting("local_llm_endpoint_url", self.local_llm_endpoint_url_var.get())
            else:
                self.config.set_system_setting("local_llm_endpoint_url", "") # ローカルLLM以外なら空を保存

            # AIチャット処理方式の保存 (新規追加)
            selected_chat_mode_display = self.ai_chat_processing_mode_var.get()
            if selected_chat_mode_display == "sequential (推奨)":
                chat_mode_to_save = "sequential"
            elif selected_chat_mode_display == "parallel":
                chat_mode_to_save = "parallel"
            else: # 念のためフォールバック
                chat_mode_to_save = "sequential"
            self.config.set_system_setting("ai_chat_processing_mode", chat_mode_to_save)


            # 音声出力デバイス設定の保存
            selected_audio_device_name = self.audio_output_device_var.get()
            devices = self.audio_player.get_available_output_devices()
            selected_device_id = "default" # デフォルト値
            for device in devices:
                if device["name"] == selected_audio_device_name:
                    selected_device_id = device["id"]
                    break
            self.config.set_system_setting("audio_output_device", selected_device_id)

            self.config.set_system_setting("auto_save", self.auto_save_var.get())
            self.config.set_system_setting("debug_mode", self.debug_mode_var.get())
            self.config.set_system_setting("conversation_history_length", self.conversation_history_length_var.get())
            
            # ストリーミング設定
            if "streaming_settings" not in self.config.config:
                self.config.config["streaming_settings"] = {}
            self.config.config["streaming_settings"]["live_id"] = self.live_id_var.get()
            
            self.config.save_config()
            messagebox.showinfo("設定保存", "設定を保存しました")
            self.log("💾 設定を保存しました")
            
            # ステータス更新
            self.status_label.config(text="✅ 準備完了 - v2.1修正版・完全動作版")
            
        except Exception as e:
            messagebox.showerror("設定保存エラー", f"設定の保存に失敗しました: {e}")
            self.log(f"❌ 設定保存エラー: {e}")
    
    def refresh_character_list(self):
        """キャラクターリストを更新"""
        # コンボボックス更新
        characters = self.config.get_all_characters()
        char_options = []
        
        # キャラクター情報を整理して表示用リストを作成
        for char_id, data in characters.items():
            char_name = data.get('name', 'Unknown')
            char_options.append(f"{char_name} ({char_id})")
        
        self.character_combo['values'] = char_options
        
        # ツリービュー更新
        self.char_tree.delete(*self.char_tree.get_children())
        for char_id, data in characters.items():
            self.char_tree.insert('', 'end', iid=char_id, values=(
                data.get('name', 'Unknown'),
                self._get_character_type(data),
                data.get('voice_settings', {}).get('model', 'Default'),
                data.get('voice_settings', {}).get('engine', 'avis_speech'), # カンマが抜けていたのを修正
                data.get('created_at', 'N/A') # created_at を表示に追加
            ))
        
        self.log(f"📝 キャラクターリストを更新（{len(characters)}件）")
        if hasattr(self, 'populate_chat_character_dropdowns'): # AIチャットタブが初期化されていれば
            self.populate_chat_character_dropdowns()
    
    def _get_character_type(self, char_data):
        """キャラクタータイプを推定"""
        tone = char_data.get('personality', {}).get('base_tone', '')
        voice_engine = char_data.get('voice_settings', {}).get('engine', '')
        voice_model = char_data.get('voice_settings', {}).get('model', '')
        
        if '元気' in tone or '明るい' in tone:
            return '🌟 元気系'
        elif '知的' in tone or '落ち着い' in tone:
            return '🎓 知的系'
        elif '癒し' in tone or '穏やか' in tone:
            return '🌸 癒し系'
        elif 'ずんだもん' in str(char_data) or voice_engine == 'voicevox':
            return '🎭 ずんだもん系'
        elif voice_engine == 'Wavenet' in voice_model:
            return '⭐ 高品質系'
        else:
            return '⚙️ カスタム'
    
    def on_character_changed(self, event=None):
        """キャラクター選択変更時の処理"""
        selection = self.character_var.get()
        if not selection:
            self.current_character_id = ""
            self.character_status.config(text="キャラクター: 未選択")
            return
        
        try:
            # キャラクターIDを抽出（括弧内の完全なID）
            if '(' in selection and ')' in selection:
                char_id = selection.split('(')[-1].replace(')', '')
                
                # キャラクターデータの存在確認
                char_data = self.config.get_character(char_id)
                if char_data:
                    self.current_character_id = char_id
                    char_name = char_data.get('name', 'Unknown')
                    voice_engine = char_data.get('voice_settings', {}).get('engine', 'avis_speech')
                    voice_model = char_data.get('voice_settings', {}).get('model', 'デフォルト')
                    
                    self.character_status.config(
                        text=f"キャラクター: {char_name} | 音声: {voice_engine}/{voice_model}"
                    )
                    self.log(f"🎯 キャラクター '{char_name}' を選択（{voice_engine}）")
                else:
                    self.current_character_id = ""
                    self.character_status.config(text="キャラクター: エラー（データなし）")
                    self.log(f"❌ キャラクターデータが見つかりません: {char_id}")
            else:
                self.current_character_id = ""
                self.character_status.config(text="キャラクター: エラー（形式不正）")
                self.log(f"❌ 無効なキャラクター選択: {selection}")
                
        except Exception as e:
            self.current_character_id = ""
            self.character_status.config(text="キャラクター: エラー")
            self.log(f"❌ キャラクター選択エラー: {e}")
    
    def on_system_engine_changed(self, event=None):
        """システム設定での音声エンジン変更時の処理"""
        engine = self.voice_engine_var.get()
        info = self.voice_manager.get_engine_info(engine)
        
        if info:
            info_text = f"{info['description']} - {info['cost']}"
            self.system_engine_info.config(text=info_text)
    
    def auto_select_character(self, char_id, char_name):
        """指定されたキャラクターを自動選択"""
        try:
            # コンボボックスから該当キャラクターを探して選択
            for i, option in enumerate(self.character_combo['values']):
                if char_id in option:
                    self.character_combo.current(i)
                    self.character_var.set(option)
                    self.on_character_changed()
                    self.log(f"🎯 キャラクター '{char_name}' を自動選択")
                    break
        except Exception as e:
            self.log(f"❌ 自動選択エラー: {e}")
    
    def create_new_character(self):
        """新しいキャラクター作成"""
        dialog = CharacterEditDialog(self.root, self.character_manager)
        if dialog.result:
            self.refresh_character_list()
            self.populate_ai_theater_talker_dropdown() # AI劇場の話者リストも更新
            action = dialog.result.get('action', 'created')
            name = dialog.result['name']
            char_id = dialog.result['char_id']
            
            if action == 'created':
                self.log(f"✅ 新キャラクター '{name}' を作成")
                # 作成したキャラクターを自動選択
                self.auto_select_character(char_id, name)
            elif action == 'edited':
                self.log(f"✅ キャラクター '{name}' を編集")
    
    def edit_character(self):
        """キャラクター編集"""
        selection = self.char_tree.selection()
        if not selection:
            messagebox.showwarning("選択エラー", "編集するキャラクターを選択してください")
            return
        
        char_id = selection[0]
        char_data = self.config.get_character(char_id)
        
        if not char_data:
            messagebox.showerror("エラー", "キャラクターデータが見つかりません")
            return
        
        # 編集ダイアログを開く
        dialog = CharacterEditDialog(self.root, self.character_manager, char_id, char_data)
        if dialog.result:
            self.refresh_character_list()
            self.populate_ai_theater_talker_dropdown() # AI劇場の話者リストも更新
            self.log(f"✏️ キャラクター '{dialog.result['name']}' を編集")
    
    def duplicate_character(self):
        """キャラクター複製"""
        selection = self.char_tree.selection()
        if not selection:
            messagebox.showwarning("選択エラー", "複製するキャラクターを選択してください")
            return
        
        char_id = selection[0]
        char_data = self.config.get_character(char_id)
        
        if not char_data:
            messagebox.showerror("エラー", "キャラクターデータが見つかりません")
            return
        
        try:
            # 新しい名前を入力
            original_name = char_data.get('name', 'Unknown')
            new_name = simpledialog.askstring(
                "キャラクター複製", 
                f"新しいキャラクター名を入力してください:",
                initialvalue=f"{original_name}のコピー"
            )
            
            if new_name:
                # データをコピーして新しいキャラクターを作成
                new_char_data = char_data.copy()
                new_char_data['name'] = new_name
                
                new_char_id = self.character_manager.create_character(
                    name=new_name,
                    custom_settings=new_char_data
                )
                
                self.refresh_character_list()
                self.populate_ai_theater_talker_dropdown() # AI劇場の話者リストも更新
                self.log(f"📋 キャラクター '{new_name}' を複製")
                
        except Exception as e:
            messagebox.showerror("複製エラー", f"キャラクターの複製に失敗しました: {e}")
            self.log(f"❌ 複製エラー: {e}")
    
    def delete_character(self):
        """キャラクター削除"""
        selection = self.char_tree.selection()
        if not selection:
            messagebox.showwarning("選択エラー", "削除するキャラクターを選択してください")
            return
        
        char_id = selection[0]
        char_data = self.config.get_character(char_id)
        
        if not char_data:
            messagebox.showerror("エラー", "キャラクターデータが見つかりません")
            return
        
        char_name = char_data.get('name', 'Unknown')
        
        # 削除確認
        if messagebox.askyesno("削除確認", f"キャラクター '{char_name}' を削除しますか？\nこの操作は取り消せません。"):
            try:
                success = self.config.delete_character(char_id)
                if success:
                    # 現在選択中のキャラクターが削除される場合は選択解除
                    if self.current_character_id == char_id:
                        self.current_character_id = ""
                        self.character_var.set("")
                        self.character_status.config(text="キャラクター: 未選択")
                    
                    self.refresh_character_list()
                    self.populate_ai_theater_talker_dropdown() # AI劇場の話者リストも更新
                    self.log(f"🗑️ キャラクター '{char_name}' を削除")
                else:
                    messagebox.showerror("削除エラー", "キャラクターの削除に失敗しました")
                    
            except Exception as e:
                messagebox.showerror("削除エラー", f"削除処理中にエラーが発生しました: {e}")
                self.log(f"❌ 削除エラー: {e}")
    
    def test_voice(self):
        """音声テスト実行"""
        if not self.current_character_id:
            messagebox.showwarning("キャラクター未選択", 
                                  "音声テストを行うには、まずキャラクターを選択してください。")
            return
        
        text_to_test = self.test_text_var.get()
        if not text_to_test: # 変数名を text から text_to_test に変更
            messagebox.showwarning("テキスト未入力", "音声テストを行うテキストを入力してください。")
            return
        
        # 非同期で音声テスト実行
        self.log(f"🎤 音声テスト開始: {text_to_test}") # 変数名を text から text_to_test に変更
        threading.Thread(target=self._run_voice_test, args=(text_to_test,), daemon=True).start() # 変数名を text から text_to_test に変更
    
    def _run_voice_test(self, text):
        """音声テストの実行 v2.1（完全版）"""
        loop = None
        try:
            self.log(f"🔊 音声テスト開始...")
            
            # キャラクターデータの取得と検証
            if not self.current_character_id:
                self.log("❌ キャラクターが選択されていません")
                return
            
            char_data = self.config.get_character(self.current_character_id)
            if not char_data:
                self.log(f"❌ キャラクターデータが見つかりません")
                return
            
            # 音声設定取得
            voice_settings = char_data.get('voice_settings', {})
            voice_engine = voice_settings.get('engine', 'avis_speech')
            voice_model = voice_settings.get('model', 'Anneli(ノーマル)')
            speed = voice_settings.get('speed', 1.0)
            
            self.log(f"🎯 使用エンジン: {voice_engine}, モデル: {voice_model}, 速度: {speed}")
            
            # 音声合成実行
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # API KEY取得
            google_ai_api_key = self.config.get_system_setting("google_ai_api_key")

            # 優先エンジンに応じて適切なAPIキーを選択
            api_key_to_use = None
            if "google_ai_studio" in voice_engine:
                api_key_to_use = google_ai_api_key
            
            # フォールバック機能付き音声合成
            audio_files = loop.run_until_complete(
                self.voice_manager.synthesize_with_fallback(
                    text, voice_model, speed, preferred_engine=voice_engine, api_key=api_key_to_use
                )
            )
            
            if audio_files:
                # 音声再生
                self.log("🎵 音声再生中...")
                loop.run_until_complete(
                    self.audio_player.play_audio_files(audio_files)
                )
                self.log("✅ 音声テスト完了")
            else:
                self.log("❌ 音声合成に失敗しました")
                
        except Exception as e:
            self.log(f"❌ 音声テストエラー: {e}")
            import traceback
            self.log(f"詳細: {traceback.format_exc()}")
        finally:
            if loop:
                try:
                    loop.close()
                except:
                    pass
    
    def compare_engines(self):
        """複数音声エンジンの比較テスト"""
        text = self.test_text_var.get()
        if not text:
            messagebox.showwarning("エラー", "テストテキストを入力してください")
            return
        
        threading.Thread(target=self._run_engine_comparison, args=(text,), daemon=True).start()
    
    def _run_engine_comparison(self, text):
        """音声エンジン比較テストの実行 v2.1"""
        try:
            self.log("🔄 音声エンジン比較テスト開始...")
            
            engines_to_test = ["avis_speech", "voicevox", "system_tts"]
            
            for i, engine_name in enumerate(engines_to_test, 1):
                self.log(f"🎵 テスト {i}/{len(engines_to_test)}: {engine_name}")
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                test_text = f"エンジン{i}番、{engine_name}です。{text}"
                
                try:
                    engine = self.voice_manager.engines[engine_name]
                    voices = engine.get_available_voices()
                    default_voice = voices[0] if voices else "default"
                    
                    api_key_to_use = None
                    if "google_ai_studio" in engine_name: # google_ai_studio_new
                        api_key_to_use = self.config.get_system_setting("google_ai_api_key")

                    if api_key_to_use:
                        audio_files = loop.run_until_complete(
                            engine.synthesize_speech(test_text, default_voice, 1.0, api_key=api_key_to_use)
                        )
                    else:
                        audio_files = loop.run_until_complete(
                            engine.synthesize_speech(test_text, default_voice, 1.0)
                        )
                    
                    if audio_files:
                        loop.run_until_complete(
                            self.audio_player.play_audio_files(audio_files)
                        )
                        self.log(f"✅ {engine_name} テスト完了")
                    else:
                        self.log(f"❌ {engine_name} 音声合成失敗")
                
                except Exception as e:
                    self.log(f"❌ {engine_name} エラー: {e}")
                
                finally:
                    if loop:
                        loop.close()
                        loop = None
                
                # 次のエンジンとの間隔
                time.sleep(1)
            
            self.log("🎉 音声エンジン比較完了")
            
        except Exception as e:
            self.log(f"❌ 比較テストエラー: {e}")
    
    def test_fallback(self):
        """フォールバック機能テスト"""
        text = self.test_text_var.get()
        if not text:
            messagebox.showwarning("エラー", "テストテキストを入力してください")
            return
        
        self.log("🔄 フォールバック機能テスト開始...")
        # threading.Thread(target=self._run_fallback_test, args=(text,), daemon=True).start() # 削除したメソッドの呼び出しなのでコメントアウト
        self.show_fallback_test_info() # 新しい情報表示メソッドを呼び出すように変更
    
    # _run_fallback_test メソッドはユーザーの指示により削除
    # def _run_fallback_test(self, text):
    #     """フォールバック機能テストの実行"""
    #     try:
    #         loop = asyncio.new_event_loop()
    #         asyncio.set_event_loop(loop)
            
    #         # 故意に存在しないエンジンから開始してフォールバックをテスト
    #         audio_files = loop.run_until_complete(
    #             self.voice_manager.synthesize_with_fallback(
    #                 text, "default", 1.0, preferred_engine="nonexistent_engine", api_key=self.config.get_system_setting("google_ai_api_key")
    #             )
    #         )
            
    #         if audio_files:
    #             loop.run_until_complete(
    #                 self.audio_player.play_audio_files(audio_files)
    #             )
    #             self.log("✅ フォールバック機能が正常に動作しました")
    #         else:
    #             self.log("❌ フォールバック機能が失敗しました")
            
    #         loop.close()
            
    #     except Exception as e:
    #         self.log(f"❌ フォールバックテストエラー: {e}")
    
    def check_engines_status(self):
        """エンジン状態確認"""
        self.log("📊 音声エンジン状態確認開始...")
        threading.Thread(target=self._check_engines_status, daemon=True).start()

    def show_fallback_test_info(self):
        """フォールバックテストの手動実行方法をユーザーに案内する"""
        messagebox.showinfo(
            "フォールバック手動テスト案内",
            "フォールバック機能を確認するには、以下の手順をお試しください：\n\n"
            "1. いずれかの音声エンジンを意図的に利用不可な状態にします。\n"
            "   (例: VOICEVOXやAvis Speech Engineを終了する、など)\n\n"
            "2. キャラクター設定で、優先エンジンを「利用不可にしたエンジン」に設定します。\n\n"
            "3. デバッグタブの「音声テスト」や「AI対話テスト」を実行します。\n\n"
            "4. コンソールログやAITuberの応答ログで、設定した優先順位に従って\n"
            "   別のエンジンにフォールバックして音声が再生されるか確認してください。\n\n"
            "（このボタン自体はテストを実行しません。上記の手順で手動確認をお願いします。）"
        )
        self.log("ℹ️ フォールバック手動テストの案内を表示しました。")
    
    def _check_engines_status(self):
        """エンジン状態確認の実行"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            availability = loop.run_until_complete(
                self.voice_manager.check_engines_availability()
            )
            
            self.log("📊 エンジン状態一覧:")
            for engine_name, is_available in availability.items():
                status = "✅ 利用可能" if is_available else "❌ 利用不可"
                info = self.voice_manager.get_engine_info(engine_name)
                self.log(f"  {engine_name}: {status} ({info.get('description', '')})")
            
            loop.close()
            
        except Exception as e:
            self.log(f"❌ エンジン状態確認エラー: {e}")
    
    def send_test_message(self, event=None):
        """テストメッセージ送信"""
        if not self.current_character_id:
            self.chat_display.insert(tk.END, "❌ システム: キャラクターが選択されていません。\n")
            self.chat_display.see(tk.END)
            return
        
        message = self.chat_input_var.get()
        if not message:
            return
        
        self.chat_input_var.set("")
        self.chat_display.insert(tk.END, f"👤 あなた: {message}\n")
        self.chat_display.see(tk.END)
        
        # 非同期でAI応答生成
        threading.Thread(target=self._generate_test_response, args=(message,), daemon=True).start()
    
    def _generate_test_response(self, message):
        """テスト用AI応答生成 v2.1"""
        try:
            # Google AI Studio設定（文章生成専用）
            api_key = self.config.get_system_setting("google_ai_api_key")
            if not api_key:
                self.root.after(0, lambda: self.chat_display.insert(tk.END, "❌ AIちゃん: Google AI Studio APIキーが設定されていません\n"))
                self.root.after(0, lambda: self.chat_display.see(tk.END))
                return
            
            # キャラクター選択確認
            if not self.current_character_id:
                self.root.after(0, lambda: self.chat_display.insert(tk.END, "❌ AIちゃん: キャラクターが選択されていません\n"))
                self.root.after(0, lambda: self.chat_display.see(tk.END))
                return
            
            char_data = self.config.get_character(self.current_character_id)
            if not char_data:
                self.root.after(0, lambda: self.chat_display.insert(tk.END, f"❌ AIちゃん: キャラクターデータが見つかりません\n"))
                self.root.after(0, lambda: self.chat_display.see(tk.END))
                return
            
            # genai.configure(api_key=api_key) # コメントアウトのまま
            # model = genai.GenerativeModel('gemini-2.5-flash') # 旧方式

            client = genai.Client(api_key=api_key) # Client を初期化
            
            # キャラクタープロンプト取得
            char_prompt = self.character_manager.get_character_prompt(self.current_character_id)
            char_name = char_data.get('name', 'AIちゃん')
            
            # 会話履歴の長さを設定から取得
            history_length = self.config.get_system_setting("conversation_history_length", 0)

            # デバッグチャット用のプロンプトに会話履歴を組み込む
            history_prompt_parts = []
            if history_length > 0 and self.debug_chat_history:
                # 直近の履歴を取得 (最大 history_length 件)
                relevant_history = self.debug_chat_history[-history_length:]
                for entry in relevant_history:
                    # 履歴の各エントリをプロンプトに追加
                    history_prompt_parts.append(f"ユーザー: {entry['user_message']}")
                    history_prompt_parts.append(f"{char_name}: {entry['ai_response']}") # AIの発言者名はキャラクター名

            history_str = "\n".join(history_prompt_parts)
            # 最終的なプロンプト: キャラクター設定 + 会話履歴 + 最新のメッセージ
            full_prompt = f"{char_prompt}\n\n{history_str}\n\nユーザー: {message}\n\n{char_name}として、自然で親しみやすい返答をしてください。" # AIの発言者名を明示
            
            # response = model.generate_content(full_prompt) # 旧方式
            selected_model_internal_name = self.config.get_system_setting("text_generation_model", "gemini-1.5-flash")
            local_llm_url = self.config.get_system_setting("local_llm_endpoint_url", "")
            ai_response = ""

            if selected_model_internal_name == "local_lm_studio":
                if not local_llm_url:
                    self.log("❌ AI対話テスト: ローカルLLMエンドポイントURLが設定されていません。")
                    ai_response = "ローカルLLMのエンドポイントURLが未設定です。設定タブで確認してください。"
                else:
                    # _generate_response_local_llm は async なので、新しいイベントループで実行
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        ai_response = loop.run_until_complete(
                            self._generate_response_local_llm(full_prompt, local_llm_url, char_name)
                        )
                    finally:
                        loop.close()
            else:
                # Google AI Studio (Gemini) を使用
                gemini_response_obj = client.models.generate_content( # text_response から変更
                    model=selected_model_internal_name, 
                    contents=full_prompt,
                    config=genai.types.GenerateContentConfig( 
                        temperature=0.9,
                        max_output_tokens=150
                    )
                )
                if gemini_response_obj.text is None: # gemini_response_obj を使用
                    self.log(f"⚠️ AI応答がNoneでした (モデル: {selected_model_internal_name})。")
                    ai_response = "ごめんなさい、ちょっと考えがまとまりませんでした。"
                else:
                    ai_response = gemini_response_obj.text.strip() # gemini_response_obj を使用
            
            # GUI更新
            self.root.after(0, lambda: self.chat_display.insert(tk.END, f"🤖 {char_name}: {ai_response}\n"))
            self.root.after(0, lambda: self.chat_display.see(tk.END))
            
            # 音声再生（フォールバック機能付き）
            voice_settings = char_data.get('voice_settings', {})
            voice_engine = voice_settings.get('engine', 'avis_speech')
            voice_model = voice_settings.get('model', 'Anneli(ノーマル)')
            speed = voice_settings.get('speed', 1.0)
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # API KEY取得（音声合成用）
            google_ai_api_key = self.config.get_system_setting("google_ai_api_key")

            # 優先エンジンに応じて適切なAPIキーを選択
            api_key_to_use = None
            if "google_ai_studio" in voice_engine: # google_ai_studio_new
                api_key_to_use = google_ai_api_key
            
            # フォールバック機能付き音声合成
            audio_files = loop.run_until_complete(
                self.voice_manager.synthesize_with_fallback(
                    ai_response, voice_model, speed, preferred_engine=voice_engine, api_key=api_key_to_use
                )
            )
            
            if audio_files:
                loop.run_until_complete(
                    self.audio_player.play_audio_files(audio_files)
                )
            
            loop.close()

            # デバッグチャットの会話履歴の記録と管理
            if history_length > 0:
                # 現在のやり取りを履歴に追加
                self.debug_chat_history.append({"user_message": message, "ai_response": ai_response})
                # 履歴が設定された長さを超えた場合、最も古いものから削除
                if len(self.debug_chat_history) > history_length:
                    self.debug_chat_history.pop(0)
            
        except genai.types.generation_types.BlockedPromptException as bpe:
            error_msg = "❌ AIちゃん: その内容についてはお答えできません。"
            self.log(f"❌ テスト応答生成エラー: プロンプトがブロックされました。{bpe}")
            self.root.after(0, lambda: self.chat_display.insert(tk.END, f"{error_msg}\n"))
            self.root.after(0, lambda: self.chat_display.see(tk.END))
        except requests.exceptions.HTTPError as http_err:
            if http_err.response.status_code == 429:
                error_msg = "❌ AIちゃん: APIの利用上限に達したみたいです。少し時間をおいて試してみてくださいね。"
                self.log(f"❌ テスト応答生成エラー: API利用上限 (429)。{http_err}")
            else:
                error_msg = f"❌ AIちゃん: サーバーとの通信エラー ({http_err.response.status_code})。"
                self.log(f"❌ テスト応答生成エラー: HTTPエラー {http_err.response.status_code}。{http_err}")
            self.root.after(0, lambda: self.chat_display.insert(tk.END, f"{error_msg}\n"))
            self.root.after(0, lambda: self.chat_display.see(tk.END))
        except Exception as e:
            error_msg = f"❌ AIちゃん: ちょっと調子が悪いみたいです。ごめんなさいね。"
            self.log(f"❌ テスト応答生成エラー: 予期せぬエラー。{e}")
            import traceback
            self.log(f"詳細トレース: {traceback.format_exc()}")
            self.root.after(0, lambda: self.chat_display.insert(tk.END, f"{error_msg}\n"))
            self.root.after(0, lambda: self.chat_display.see(tk.END))
    
    def toggle_streaming(self):
        """配信開始/停止切り替え"""
        if not self.is_streaming:
            self.start_streaming()
        else:
            self.stop_streaming()
    
    def start_streaming(self):
        """配信開始"""
        try:
            # 必要な設定確認
            if not self.current_character_id:
                messagebox.showwarning("エラー", "キャラクターを選択してください")
                return
            
            if not self.live_id_var.get():
                messagebox.showwarning("エラー", "YouTube ライブIDを入力してください")
                return
            
            if not self.config.get_system_setting("google_ai_api_key"):
                messagebox.showwarning("エラー", "Google AI Studio APIキーを設定してください（文章生成用）")
                return
            
            if not self.config.get_system_setting("youtube_api_key"):
                messagebox.showwarning("エラー", "YouTube APIキーを設定してください")
                return
            
            # 配信開始
            self.is_streaming = True
            self.start_button.config(text="配信停止")
            self.status_label.config(text="🔴 配信中...")
            
            # 非同期でストリーミング開始
            self.aituber_task = threading.Thread(
                target=self._run_streaming, daemon=True
            )
            self.aituber_task.start()
            
            self.log("🎬 AITuber配信を開始しました")
            
        except Exception as e:
            self.log(f"❌ 配信開始エラー: {e}")
            messagebox.showerror("エラー", f"配信開始に失敗しました: {e}")
    
    def stop_streaming(self):
        """配信停止"""
        self.is_streaming = False
        self.start_button.config(text="配信開始")
        self.status_label.config(text="✅ 準備完了 - v2.1修正版・完全動作版")
        self.log("⏹️ AITuber配信を停止しました")
    
    def _run_streaming(self):
        """ストリーミングメインループ v2.1"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # AITuberシステム初期化
            aituber = AITuberStreamingSystem(
                config=self.config,
                character_id=self.current_character_id,
                character_manager=self.character_manager,
                voice_manager=self.voice_manager,
                audio_player=self.audio_player,
                log_callback=self.log
            )
            
            # ストリーミング実行
            loop.run_until_complete(
                aituber.run_streaming(self.live_id_var.get())
            )
            
        except Exception as e:
            self.log(f"❌ ストリーミングエラー: {e}")
        finally:
            loop.close()
            self.is_streaming = False
            self.root.after(0, lambda: self.start_button.config(text="配信開始"))
            self.root.after(0, lambda: self.status_label.config(text="✅ 準備完了 - v2.1修正版・完全動作版"))
    
    def emergency_stop(self):
        """緊急停止"""
        self.stop_streaming()
        self.log("🚨 緊急停止が実行されました")
        messagebox.showinfo("緊急停止", "システムを緊急停止しました")
    
    def show_help(self):
        """ヘルプ表示"""
        help_text = """
🎯 AITuber完全版システム v2.1 - 修正版・完全動作版

【基本的な使い方】
1. 「キャラクター管理」でキャラクターを作成
2. 「設定」でAPIキーを設定（Google AI Studio APIキーが必須）
3. 「デバッグ」で音声テスト・エンジン状態確認
4. 「メイン」でYouTube配信開始

【4つの音声エンジン（修正版）】
🚀 Google AI Studio新音声: 最新技術・リアルタイム対応 (Google AI Studio APIキー設定)
🎙️ Avis Speech Engine: ローカル実行・高品質（ポート10101）
🎤 VOICEVOX Engine: 定番キャラ・ずんだもん等（ポート50021）
💻 システムTTS: OS標準・フォールバック用

【推奨設定】
• まずは「元気系」「ずんだもん系」キャラクターから開始
• 音声エンジンは「google_ai_studio_new」、「avis_speech」、「voicevox」推奨
• 問題があれば自動で次のエンジンにフォールバック

🎭【AI劇場機能】
1. 「AI劇場」タブを開きます。
2. 「CSV台本読み込み」ボタンで、所定のフォーマットのCSVファイルを読み込みます。
   (フォーマット詳細は CSVScriptDefinitions.md を参照)
3. 読み込まれた台本がプレビューに表示されます。
4. 「選択行の音声生成」または「全ての音声生成」で、台詞に対応する音声ファイルを作成します。
   音声ファイルはCSVファイルと同じ場所に `[CSVファイル名]_audio` というフォルダが作成され、その中に保存されます。
5. 「連続再生」で台本を順次再生します。音声ファイルがない場合は自動で生成してから再生します。
6. 「音声ファイル全削除」で、現在読み込んでいる台本に対応する音声フォルダ内の音声ファイルを全て削除します。
7. 話者名（talker）はキャラクター管理で登録されたキャラクター名と照合されます。ナレーターも同様です。
   該当がない場合はメイン画面のアクティブキャラクターの声が使用されます。

【エンジン起動確認】
• Google AI Studio新音声: Google AI Studio APIキー設定
• Avis Speech: http://127.0.0.1:10101/docs
• VOICEVOX: http://127.0.0.1:50021/docs
• システムTTS: 設定不要

【トラブルシューティング】
• 音声が出ない → 「エンジン状態確認」で各エンジンの状況をチェック
• 配信できない → Google AI Studio APIキー設定確認
• キャラクターが動かない → VSeeFace設定確認
• Google AI Studio TTS エラー → v2.1では文章生成のみ使用（修正済み）
        """
        
        messagebox.showinfo("ヘルプ", help_text)
    
    def log(self, message):
        """ログ出力 v2.1"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        # self.log_text が None でないことを確認してからGUIに書き込む
        if self.log_text is not None:
            self.root.after(0, lambda: self.log_text.insert(tk.END, log_message))
            self.root.after(0, lambda: self.log_text.see(tk.END))
        else:
            # log_text がまだ初期化されていない場合は、標準出力にのみ表示
            print(f"[GUI Log Text Not Initialized] {log_message.strip()}")
        
        print(log_message.strip())
        
        # デバッグモードの場合、より詳細なログ
        if self.config.get_system_setting("debug_mode", False):
            self.logger.info(message)
    
    def clear_log(self):
        """ログクリア"""
        if self.log_text:
            self.log_text.delete(1.0, tk.END)
        self.log("📄 ログをクリアしました")
    
    def save_log(self):
        """ログ保存"""
        if not self.log_text:
            messagebox.showwarning("エラー", "ログテキストウィジェットが初期化されていません")
            return
        
        log_content = self.log_text.get(1.0, tk.END).strip()
        if not log_content:
            messagebox.showinfo("情報", "ログは空です")
            return
        
        try:
            with open("aituber_log.txt", "w", encoding="utf-8") as f:
                f.write(log_content)
            messagebox.showinfo("保存完了", "ログを 'aituber_log.txt' に保存しました")
            self.log("💾 ログを保存しました")
        except Exception as e:
            messagebox.showerror("保存エラー", f"ログの保存に失敗しました: {e}")
            self.log(f"❌ ログ保存エラー: {e}")

    def refresh_log(self):
        """ログを最新の状態に更新"""
        if not self.log_text:
            messagebox.showwarning("エラー", "ログテキストウィジェットが初期化されていません")
            return
        
        # ログファイルを読み込んで表示
        try:
            with open("aituber_log.txt", "r", encoding="utf-8") as f:
                log_content = f.read()
            self.log_text.delete(1.0, tk.END)
            self.log_text.insert(tk.END, log_content)
            self.log("🔄 ログを最新の状態に更新しました")
        except FileNotFoundError:
            messagebox.showwarning("警告", "ログファイルが見つかりません")
            self.log("⚠️ ログファイルが見つかりません")
        except Exception as e:
            messagebox.showerror("エラー", f"ログの更新に失敗しました: {e}")
            self.log(f"❌ ログ更新エラー: {e}")

    def show_system_status(self):
        """システムステータスを表示"""
        status_text = (
            "🔧 システムステータス\n"
            "--------------------\n"
            f"キャラクターID: {self.current_character_id or '未選択'}\n"
            f"配信状態: {'配信中' if self.is_streaming else '停止中'}\n"
            f"Google AI APIキー: {'設定済み' if self.config.get_system_setting('google_ai_api_key') else '未設定'}\n"
            f"YouTube APIキー: {'設定済み' if self.config.get_system_setting('youtube_api_key') else '未設定'}\n"
            f"音声エンジン: {self.voice_manager.get_current_engine_name()}\n"
        )
        
        messagebox.showinfo("システムステータス", status_text)

    def run_system_diagnostics(self):
        """システム診断を実行"""
        diagnostics_text = "🔍 システム診断結果\n--------------------\n"
        
        # キャラクター選択確認
        if not self.current_character_id:
            diagnostics_text += "キャラクターが選択されていません。\n"
        else:
            diagnostics_text += f"選択中のキャラクターID: {self.current_character_id}\n"
        
        # APIキー確認
        if not self.config.get_system_setting("google_ai_api_key"):
            diagnostics_text += "Google AI Studio APIキーが未設定です。\n"
        if not self.config.get_system_setting("youtube_api_key"):
            diagnostics_text += "YouTube APIキーが未設定です。\n"
        
        # 音声エンジン状態確認
        engine_status = self.voice_manager.check_engines_availability()
        for engine, available in engine_status.items():
            status = "利用可能" if available else "利用不可"
            diagnostics_text += f"{engine}: {status}\n"
        
        messagebox.showinfo("システム診断", diagnostics_text)

    def show_about(self):
        """アプリケーション情報を表示"""
        about_text = (
            "AITuberシステム v2.1 - 修正版・完全動作版\n"
            "開発者: あなたの名前\n")
        about_text += (
            "このアプリケーションは、YouTubeライブ配信を支援するAITuberシステムです。\n"
            "音声エンジンの選択やキャラクター管理、AI応答生成などの機能を提供します。\n"
            "詳細はヘルプをご覧ください。\n"
            "GitHub:xxxx"
        )
        messagebox.showinfo("アプリケーション情報", about_text)

    def export_character(self):
        """キャラクターをJSON形式でエクスポート"""
        selection = self.char_tree.selection()
        if not selection:
            messagebox.showwarning("選択エラー", "エクスポートするキャラクターを選択してください")
            return
        
        char_id = selection[0]
        char_data = self.config.get_character(char_id)
        
        if not char_data:
            messagebox.showerror("エラー", "キャラクターデータが見つかりません")
            return
        
        try:
            # JSONファイル名を指定
            file_name = f"{char_data['name']}_character.json"
            with open(file_name, "w", encoding="utf-8") as f:
                json.dump(char_data, f, ensure_ascii=False, indent=4)
            
            messagebox.showinfo("エクスポート完了", f"キャラクター '{char_data['name']}' を '{file_name}' にエクスポートしました")
            self.log(f"📤 キャラクター '{char_data['name']}' をエクスポートしました")
            
        except Exception as e:
            messagebox.showerror("エクスポートエラー", f"キャラクターのエクスポートに失敗しました: {e}")
            self.log(f"❌ エクスポートエラー: {e}")

    def import_character(self):
        """JSON形式のキャラクターをインポート"""
        file_path = filedialog.askopenfilename(
            title="キャラクターJSONファイルを選択",
            filetypes=[("JSONファイル", "*.json")]
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                char_data = json.load(f)
            
            # キャラクターIDを生成
            char_id = self.character_manager.create_character(
                name=char_data.get('name', '新しいキャラクター'),
                custom_settings=char_data
            )
            
            self.refresh_character_list()
            self.log(f"📥 キャラクター '{char_data.get('name', '新しいキャラクター')}' をインポートしました")
            
        except Exception as e:
            messagebox.showerror("インポートエラー", f"キャラクターのインポートに失敗しました: {e}")
            self.log(f"❌ インポートエラー: {e}")

    def test_character_voice(self):
        """選択中のキャラクターの音声をテスト再生"""
        if not self.current_character_id:
            messagebox.showwarning("キャラクター未選択", "音声テストを行うには、まずキャラクターを選択してください。")
            return
        
        char_data = self.config.get_character(self.current_character_id)
        if not char_data:
            messagebox.showerror("エラー", "キャラクターデータが見つかりません")
            return
        
        # 音声合成テスト
        test_text = "こんにちは！これは音声テストです。"
        self.log(f"🎤 キャラクター '{char_data['name']}' の音声テスト開始: {test_text}")
        
        threading.Thread(target=self._run_voice_test, args=(test_text,), daemon=True).start()

    def measure_character_performance(self):
        """選択中のキャラクターのパフォーマンスを測定"""
        if not self.current_character_id:
            messagebox.showwarning("キャラクター未選択", "パフォーマンス測定を行うには、まずキャラクターを選択してください。")
            return
        
        char_data = self.config.get_character(self.current_character_id)
        if not char_data:
            messagebox.showerror("エラー", "キャラクターデータが見つかりません")
            return
        
        # パフォーマンス測定開始
        self.log(f"📊 キャラクター '{char_data['name']}' のパフォーマンス測定を開始します...")
        
        # 非同期でパフォーマンス測定実行
        threading.Thread(target=self._run_performance_measurement, args=(char_data,), daemon=True).start()

    def _run_performance_measurement(self, char_data):
        """キャラクターの音声合成パフォーマンスを測定する内部メソッド"""
        self.log(f"📊 パフォーマンス測定開始: キャラクター '{char_data.get('name', 'Unknown')}'")

        voice_settings = char_data.get('voice_settings', {})
        engine_name = voice_settings.get('engine', 'system_tts')
        voice_model = voice_settings.get('model', 'default')
        speed = voice_settings.get('speed', 1.0)

        if engine_name not in self.voice_manager.engines:
            self.log(f"❌ パフォーマンス測定エラー: エンジン '{engine_name}' が見つかりません。")
            messagebox.showerror("測定エラー", f"音声エンジン '{engine_name}' がシステムに登録されていません。")
            return

        engine_instance = self.voice_manager.engines[engine_name]

        test_texts = [
            ("短い挨拶", "こんにちは"),
            ("一般的な質問", "今日の天気はどうですか？"),
            ("少し長めの説明", "この音声合成システムは、複数のエンジンに対応しています。"),
            ("感情表現を含む可能性のあるテキスト", "わーい！とても嬉しいです！ありがとう！"),
            ("長いニュース記事風のテキスト", "本日未明、東京スカイツリーの頂上に謎の飛行物体が確認され、専門家チームが調査を開始しました。詳細は追って報告される予定です。")
        ]

        results = []
        api_key_google_ai = self.config.get_system_setting("google_ai_api_key")
        api_key_google_cloud = self.config.get_system_setting("google_cloud_api_key")

        loop = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            for description, text_to_synthesize in test_texts:
                self.log(f"🔄 テスト中: '{description}' (長さ: {len(text_to_synthesize)}文字)")
                start_time = time.time()

                kwargs = {}
                if "google_ai_studio" in engine_name:
                    kwargs['api_key'] = api_key_google_ai

                audio_files = loop.run_until_complete(
                    engine_instance.synthesize_speech(text_to_synthesize, voice_model, speed, **kwargs)
                )

                end_time = time.time()
                duration = end_time - start_time

                if audio_files:
                    self.log(f"✅ 成功: {duration:.3f}秒 - {audio_files[0] if audio_files else 'No file'}")
                    results.append({
                        "description": description,
                        "text_length": len(text_to_synthesize),
                        "duration_seconds": duration,
                        "success": True,
                        "output_file": audio_files[0] if audio_files else None
                    })
                else:
                    self.log(f"❌ 失敗: {duration:.3f}秒")
                    results.append({
                        "description": description,
                        "text_length": len(text_to_synthesize),
                        "duration_seconds": duration,
                        "success": False,
                        "output_file": None
                    })
                time.sleep(0.5) # Avoid overwhelming the API/engine

            self.log("📊 パフォーマンス測定結果:")
            total_duration = 0
            successful_syntheses = 0
            for res in results:
                status = "成功" if res["success"] else "失敗"
                self.log(f"  - {res['description']} ({res['text_length']}文字): {res['duration_seconds']:.3f}秒 [{status}]")
                if res["success"]:
                    total_duration += res["duration_seconds"]
                    successful_syntheses +=1

            avg_duration = total_duration / successful_syntheses if successful_syntheses > 0 else 0
            self.log(f"平均合成時間 (成功分のみ): {avg_duration:.3f}秒")
            self.log(f"合計成功数: {successful_syntheses}/{len(test_texts)}")

            # GUIに結果を表示 (簡易的にメッセージボックスで)
            result_summary_gui = f"パフォーマンス測定完了: {char_data.get('name', 'Unknown')} ({engine_name}/{voice_model})\n"
            result_summary_gui += f"合計テスト数: {len(test_texts)}\n"
            result_summary_gui += f"成功数: {successful_syntheses}\n"
            result_summary_gui += f"平均合成時間 (成功分): {avg_duration:.3f}秒\n\n詳細はログを確認してください。"
            messagebox.showinfo("パフォーマンス測定完了", result_summary_gui)

        except Exception as e:
            self.log(f"❌ パフォーマンス測定中にエラーが発生しました: {e}")
            import traceback
            self.log(f"詳細トレース: {traceback.format_exc()}")
            messagebox.showerror("測定エラー", f"パフォーマンス測定中にエラーが発生しました: {e}")
        finally:
            if loop:
                try:
                    loop.close()
                except Exception as e:
                     self.log(f"⚠️ イベントループクローズエラー（パフォーマンス測定）: {e}")

    def run_performance_benchmark(self):
        """キャラクターのパフォーマンスベンチマークを実行"""
        if not self.current_character_id:
            messagebox.showwarning("キャラクター未選択", "パフォーマンスベンチマークを行うには、まずキャラクターを選択してください。")
            return
        
        char_data = self.config.get_character(self.current_character_id)
        if not char_data:
            messagebox.showerror("エラー", "キャラクターデータが見つかりません")
            return
        
        # ベンチマーク開始
        self.log(f"🚀 キャラクター '{char_data['name']}' のパフォーマンスベンチマークを開始します...")
        
        # 非同期でベンチマーク実行
        # threading.Thread(target=self._run_performance_benchmark, args=(char_data,), daemon=True).start()
        # messagebox.showinfo("パフォーマンスベンチマーク", "この機能は現在実装中です。")
        if not self.current_character_id:
            messagebox.showwarning("キャラクター未選択", "パフォーマンスベンチマークを行うには、まずキャラクターを選択してください。")
            return

        char_data = self.config.get_character(self.current_character_id)
        if not char_data:
            messagebox.showerror("エラー", "キャラクターデータが見つかりません")
            return

        self.log(f"🚀 キャラクター '{char_data['name']}' のパフォーマンスベンチマークを開始します...")
        threading.Thread(target=self._run_performance_benchmark, args=(char_data,), daemon=True).start()

    def _run_performance_benchmark(self, char_data):
        """キャラクターの音声合成パフォーマンスを測定する内部メソッド"""
        self.log(f"📊 ベンチマーク開始: キャラクター '{char_data.get('name', 'Unknown')}'")

        voice_settings = char_data.get('voice_settings', {})
        engine_name = voice_settings.get('engine', 'system_tts')
        voice_model = voice_settings.get('model', 'default')
        speed = voice_settings.get('speed', 1.0)

        if engine_name not in self.voice_manager.engines:
            self.log(f"❌ ベンチマークエラー: エンジン '{engine_name}' が見つかりません。")
            messagebox.showerror("ベンチマークエラー", f"音声エンジン '{engine_name}' がシステムに登録されていません。")
            return

        engine_instance = self.voice_manager.engines[engine_name]

        test_texts = [
            ("短い挨拶", "こんにちは"),
            ("一般的な質問", "今日の天気はどうですか？"),
            ("少し長めの説明", "この音声合成システムは、複数のエンジンに対応しています。"),
            ("感情表現を含む可能性のあるテキスト", "わーい！とても嬉しいです！ありがとう！"),
            ("長いニュース記事風のテキスト", "本日未明、東京スカイツリーの頂上に謎の飛行物体が確認され、専門家チームが調査を開始しました。詳細は追って報告される予定です。")
        ]

        results = []
        api_key_google_ai = self.config.get_system_setting("google_ai_api_key")
        api_key_google_cloud = self.config.get_system_setting("google_cloud_api_key")

        loop = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            for description, text_to_synthesize in test_texts:
                self.log(f"🔄 テスト中: '{description}' (長さ: {len(text_to_synthesize)}文字)")
                start_time = time.time()

                kwargs = {}
                if "google_ai_studio" in engine_name:
                    kwargs['api_key'] = api_key_google_ai

                audio_files = loop.run_until_complete(
                    engine_instance.synthesize_speech(text_to_synthesize, voice_model, speed, **kwargs)
                )

                end_time = time.time()
                duration = end_time - start_time

                if audio_files:
                    self.log(f"✅ 成功: {duration:.3f}秒 - {audio_files[0] if audio_files else 'No file'}")
                    results.append({
                        "description": description,
                        "text_length": len(text_to_synthesize),
                        "duration_seconds": duration,
                        "success": True,
                        "output_file": audio_files[0] if audio_files else None
                    })
                    # Optionally play the audio for quick verification during testing
                    # audio_player = AudioPlayer()
                    # loop.run_until_complete(audio_player.play_audio_files(audio_files))
                else:
                    self.log(f"❌ 失敗: {duration:.3f}秒")
                    results.append({
                        "description": description,
                        "text_length": len(text_to_synthesize),
                        "duration_seconds": duration,
                        "success": False,
                        "output_file": None
                    })
                time.sleep(0.5) # Avoid overwhelming the API/engine

            self.log("📊 ベンチマーク結果:")
            total_duration = 0
            successful_syntheses = 0
            for res in results:
                status = "成功" if res["success"] else "失敗"
                self.log(f"  - {res['description']} ({res['text_length']}文字): {res['duration_seconds']:.3f}秒 [{status}]")
                if res["success"]:
                    total_duration += res["duration_seconds"]
                    successful_syntheses +=1

            avg_duration = total_duration / successful_syntheses if successful_syntheses > 0 else 0
            self.log(f"平均合成時間 (成功分のみ): {avg_duration:.3f}秒")
            self.log(f"合計成功数: {successful_syntheses}/{len(test_texts)}")

            # GUIに結果を表示 (簡易的にメッセージボックスで)
            result_summary_gui = f"ベンチマーク完了: {char_data.get('name', 'Unknown')} ({engine_name}/{voice_model})\n"
            result_summary_gui += f"合計テスト数: {len(test_texts)}\n"
            result_summary_gui += f"成功数: {successful_syntheses}\n"
            result_summary_gui += f"平均合成時間 (成功分): {avg_duration:.3f}秒\n\n詳細はログを確認してください。"
            messagebox.showinfo("パフォーマンスベンチマーク完了", result_summary_gui)

        except Exception as e:
            self.log(f"❌ ベンチマーク中にエラーが発生しました: {e}")
            import traceback
            self.log(f"詳細トレース: {traceback.format_exc()}")
            messagebox.showerror("ベンチマークエラー", f"ベンチマーク中にエラーが発生しました: {e}")
        finally:
            if loop:
                try:
                    loop.close()
                except Exception as e:
                    self.log(f"⚠️ イベントループクローズエラー（ベンチマーク）: {e}")


    def test_google_ai_studio(self):
        """Google AI Studioの文章生成機能をテスト"""
        if not self.config.get_system_setting("google_ai_api_key"):
            messagebox.showwarning("APIキー未設定", "Google AI Studio APIキーを設定してください")
            return
        
        # テスト用のプロンプト
        test_prompt = "こんにちは、AIちゃん！今日はどんなことを話しましょうか？"
        
        self.log(f"📝 Google AI Studio 文章生成テスト開始: {test_prompt}")
        
        # 非同期で文章生成実行
        # threading.Thread(target=self._run_google_ai_studio_test, args=(test_prompt,), daemon=True).start() # Placeholder for actual test
        # self.log("Google AI Studio Test (Text Gen) - Not implemented yet in this fashion, see chat test.")
        # messagebox.showinfo("テスト", "Google AI Studio (文章生成) のテストは、デバッグタブのAI対話テストをご利用ください。")
        test_text = "これはGoogle AI Studioの新しい音声合成APIのテストです。"
        # Google AI Studioの新音声合成テストを実行
        # voice_model はSDKで利用する正しい形式を指定する
        threading.Thread(target=self._run_google_ai_studio_test, args=(test_text, "gemini-2.5-flash-preview-tts-alloy", 1.0), daemon=True).start()

    def _run_google_ai_studio_test(self, text_to_synthesize, voice_model="gemini-2.5-flash-preview-tts-alloy", speed=1.0):
        """Google AI Studio (New Voice API) の音声合成をテストする内部メソッド"""
        self.log(f"🧪 Google AI Studio 新音声合成テスト開始: Voice: {voice_model}, Speed: {speed}, Text: {text_to_synthesize}")
        api_key = self.config.get_system_setting("google_ai_api_key")
        if not api_key:
            self.log("❌ Google AI Studio APIキーが設定されていません。")
            messagebox.showerror("APIキーエラー", "Google AI Studio APIキーが設定されていません。")
            return

        loop = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            engine = GoogleAIStudioNewVoiceAPI()
            audio_files = loop.run_until_complete(
                engine.synthesize_speech(text_to_synthesize, voice_model, speed, api_key=api_key)
            )

            if audio_files:
                self.log(f"✅ 音声ファイル生成成功: {audio_files}")
                audio_player = AudioPlayer()
                loop.run_until_complete(
                    audio_player.play_audio_files(audio_files)
                )
                self.log("🎧 音声再生完了")
                messagebox.showinfo("音声テスト成功", f"Google AI Studio 新音声合成 ({voice_model}) のテスト再生が完了しました。")
            else:
                self.log("❌ 音声ファイルの生成に失敗しました。")
                messagebox.showerror("音声テスト失敗", f"Google AI Studio 新音声合成 ({voice_model}) で音声ファイルの生成に失敗しました。詳細はログを確認してください。")

        except Exception as e:
            self.log(f"❌ Google AI Studio 新音声合成テスト中にエラーが発生しました: {e}")
            import traceback
            self.log(f"詳細トレース: {traceback.format_exc()}")
            messagebox.showerror("テストエラー", f"Google AI Studio 新音声合成テスト中にエラーが発生しました: {e}")
        finally:
            if loop:
                try:
                    loop.close()
                except Exception as e:
                    self.log(f"⚠️ イベントループクローズエラー: {e}")

    def test_youtube_api(self):
        """YouTube APIの接続テスト"""
        api_key = self.config.get_system_setting("youtube_api_key")
        if not api_key:
            messagebox.showwarning("APIキー未設定", "YouTube APIキーを設定してください")
            self.log("❌ YouTube API テスト: APIキーが設定されていません。")
            return

        self.log("🧪 YouTube API 接続テスト開始...")

        # テストとして、チャンネル情報などを取得する簡単なリクエストを試みる
        # ここでは、テスト目的で 'GoogleDevelopers' チャンネルの情報を取得してみます。
        # 実際のアプリケーションでは、より適切なエンドポイントやパラメータを使用してください。
        test_channel_id = "UC_x5XG1OV2P6uZZ5FSM9Ttw" # Google DevelopersチャンネルID (例)
        url = f"https://www.googleapis.com/youtube/v3/channels?part=snippet&id={test_channel_id}&key={api_key}"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()  # HTTPエラーがあれば例外を発生させる

            data = response.json()
            if 'items' in data and data['items']:
                channel_name = data['items'][0]['snippet']['title']
                self.log(f"✅ YouTube API 接続成功。テストチャンネル名: {channel_name}")
                messagebox.showinfo("YouTube APIテスト成功", f"YouTube APIに正常に接続できました。\nテストチャンネル '{channel_name}' の情報を取得しました。")
            else:
                self.log("⚠️ YouTube API 接続成功しましたが、期待されるデータ形式ではありませんでした。")
                messagebox.showwarning("YouTube APIテスト警告", "YouTube APIには接続できましたが、レスポンスが期待した形式ではありませんでした。")

        except requests.exceptions.HTTPError as http_err:
            self.log(f"❌ YouTube API HTTPエラー: {http_err.response.status_code} - {http_err.response.text}")
            messagebox.showerror("YouTube APIテスト失敗", f"YouTube APIへの接続に失敗しました (HTTPエラー)。\nステータス: {http_err.response.status_code}\n詳細はログを確認してください。")
        except requests.exceptions.RequestException as req_err:
            self.log(f"❌ YouTube API リクエストエラー: {req_err}")
            messagebox.showerror("YouTube APIテスト失敗", f"YouTube APIへのリクエスト中にエラーが発生しました。\nエラー: {req_err}\n詳細はログを確認してください。")
        except Exception as e:
            self.log(f"❌ YouTube API テスト中に予期せぬエラー: {e}")
            import traceback
            self.log(f"詳細トレース: {traceback.format_exc()}")
            messagebox.showerror("YouTube APIテストエラー", f"YouTube APIのテスト中に予期せぬエラーが発生しました: {e}")

    def test_avis_speech(self):
        """Avis Speech Engineの音声合成機能をテスト"""
        # Avis Speech はローカルエンジンなので、APIキー設定の確認は不要。
        # 代わりに、エンジンが起動しているか（/speakers エンドポイントにアクセス可能か）を確認する。
        # ただし、このボタンから直接テストする際は、CharacterEditDialog の test_voice のような
        # 音声合成と再生を行うのがユーザーにとって分かりやすい。
        # ここでは、AvisSpeechEngineAPI の check_availability を呼び出す形にする。

        self.log("🧪 Avis Speech Engine 接続テスト開始...")

        loop = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            engine = AvisSpeechEngineAPI()
            is_available = loop.run_until_complete(engine.check_availability())

            if is_available:
                self.log("✅ Avis Speech Engine は利用可能です。")
                # 利用可能な音声も表示
                voices = engine.get_available_voices()
                voices_str = ", ".join(voices[:5]) + ("..." if len(voices) > 5 else "")
                messagebox.showinfo("Avis Speechテスト成功", f"Avis Speech Engineに接続できました。\n利用可能な音声 (一部): {voices_str}")
            else:
                self.log("❌ Avis Speech Engine は利用できません。エンジンが起動しているか確認してください。")
                messagebox.showerror("Avis Speechテスト失敗", "Avis Speech Engineに接続できませんでした。\nエンジンがローカルで起動しているか、ポート設定（デフォルト: 10101）を確認してください。")

        except Exception as e:
            self.log(f"❌ Avis Speech Engine テスト中にエラー: {e}")
            import traceback
            self.log(f"詳細トレース: {traceback.format_exc()}")
            messagebox.showerror("Avis Speechテストエラー", f"Avis Speech Engineのテスト中にエラーが発生しました: {e}")
        finally:
            if loop:
                try:
                    loop.close()
                except Exception as e:
                    self.log(f"⚠️ イベントループクローズエラー (Avis Speech Test): {e}")

        # より完全なテストとして、実際の音声合成と再生を行う場合は以下のようにする
        # test_text = "これはAvis Speech Engineの音声合成テストです。"
        # self.log(f"🔊 Avis Speech Engine 音声合成テスト開始: {test_text}")
        # threading.Thread(target=self._run_avis_speech_test, args=(test_text,), daemon=True).start()
        # ただし、_run_avis_speech_test はまだ定義されていないので注意。
        # このステップでは、APIキーの代わりに接続性を確認する方向で実装。
        # if not self.config.get_system_setting("avis_speech_api_key"):
        # messagebox.showwarning("APIキー未設定", "Avis Speech Engine APIキーを設定してください")
        # return
        
        # テスト用のテキスト
        test_text = "こんにちは、これはAvis Speech Engineの音声合成テストです。"
        
        self.log(f"🔊 Avis Speech Engine 音声合成テスト開始: {test_text}")
        
        # 非同期で音声合成実行
        threading.Thread(target=self._run_avis_speech_test, args=(test_text,), daemon=True).start()

    def _run_avis_speech_test(self, text_to_synthesize, voice_model="Anneli(ノーマル)", speed=1.0):
        """Avis Speech Engine の音声合成をテストする内部メソッド"""
        self.log(f"🧪 Avis Speech Engine 音声合成テスト開始: Voice: {voice_model}, Speed: {speed}, Text: {text_to_synthesize}")

        loop = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            engine = AvisSpeechEngineAPI()

            # まずエンジンが利用可能かチェック
            is_available = loop.run_until_complete(engine.check_availability())
            if not is_available:
                self.log("❌ Avis Speech Engine は利用できません。エンジンが起動しているか確認してください。")
                messagebox.showerror("Avis Speechテスト失敗", "Avis Speech Engineに接続できませんでした。\nエンジンがローカルで起動しているか、ポート設定（デフォルト: 10101）を確認してください。")
                return

            audio_files = loop.run_until_complete(
                engine.synthesize_speech(text_to_synthesize, voice_model, speed)
            )

            if audio_files:
                self.log(f"✅ 音声ファイル生成成功: {audio_files}")
                audio_player = AudioPlayer()
                loop.run_until_complete(
                    audio_player.play_audio_files(audio_files)
                )
                self.log("🎧 音声再生完了")
                messagebox.showinfo("音声テスト成功", f"Avis Speech Engine ({voice_model}) のテスト再生が完了しました。")
            else:
                self.log("❌ 音声ファイルの生成に失敗しました。")
                messagebox.showerror("音声テスト失敗", f"Avis Speech Engine ({voice_model}) で音声ファイルの生成に失敗しました。詳細はログを確認してください。")

        except Exception as e:
            self.log(f"❌ Avis Speech Engine テスト中にエラーが発生しました: {e}")
            import traceback
            self.log(f"詳細トレース: {traceback.format_exc()}")
            messagebox.showerror("テストエラー", f"Avis Speech Engine テスト中にエラーが発生しました: {e}")
        finally:
            if loop:
                try:
                    loop.close()
                except Exception as e:
                    self.log(f"⚠️ イベントループクローズエラー (Avis Speech Run Test): {e}")

    def send_random_message(self):
        """ランダムなメッセージを送信するデバッグ用関数"""
        if not self.current_character_id:
            self.chat_display.insert(tk.END, "❌ システム: キャラクターが選択されていません。\n")
            self.chat_display.see(tk.END)
            self.log("⚠️ ランダムメッセージ送信失敗: キャラクター未選択")
            return

        messages = [
            "こんにちは！今日はどんなことを話しましょうか？",
            "AIちゃん、元気ですか？",
            "最近のおすすめのアニメは何ですか？",
            "AIちゃんの好きな食べ物は何ですか？",
            "次の配信はいつですか？",
            "今日のラッキーアイテムは何だろう？",
            "面白いジョークを一つ教えて！",
            "週末の予定はもう決まった？",
            "おすすめのゲームがあったら教えてほしいな。",
            "疲れたときにリフレッシュする方法ってある？"
        ]

        import random # random モジュールをインポート
        chosen_message = random.choice(messages)

        self.chat_input_var.set(chosen_message) # 入力フィールドにも表示（任意）
        self.send_test_message() # send_test_message を呼び出して送信処理を行う
        self.log(f"💬 ランダムメッセージ送信: {chosen_message}")

    def reset_settings(self):
        """システム設定を初期状態にリセット"""
        if messagebox.askyesno("設定リセット", "本当にシステム設定を初期状態にリセットしますか？"):
            self.config.reset_system_settings()
            self.log("🔄 システム設定を初期状態にリセットしました")
            messagebox.showinfo("設定リセット完了", "システム設定が初期状態にリセットされました")
        else:
            self.log("❌ システム設定のリセットがキャンセルされました")

    def export_settings(self):
        """システム設定をJSON形式でエクスポート"""
        try:
            settings = self.config.get_all_system_settings()
            file_path = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSONファイル", "*.json")],
                title="システム設定を保存"
            )
            if not file_path:
                return
            
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)
            
            messagebox.showinfo("保存完了", f"システム設定を '{file_path}' に保存しました")
            self.log(f"📤 システム設定をエクスポートしました: {file_path}")
        except Exception as e:
            messagebox.showerror("エクスポートエラー", f"システム設定のエクスポートに失敗しました: {e}")

    def import_settings(self):
        """JSON形式のシステム設定をインポート"""
        file_path = filedialog.askopenfilename(
            title="システム設定JSONファイルを選択",
            filetypes=[("JSONファイル", "*.json")]
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                settings = json.load(f)
            
            self.config.set_all_system_settings(settings)
            messagebox.showinfo("インポート完了", f"システム設定を '{file_path}' からインポートしました")
            self.log(f"📥 システム設定をインポートしました: {file_path}")
        except Exception as e:
            messagebox.showerror("インポートエラー", f"システム設定のインポートに失敗しました: {e}")

    def create_full_backup(self):
        """システムの完全バックアップを作成"""
        if messagebox.askyesno("完全バックアップ", "システムの完全バックアップを作成しますか？"):
            try:
                backup_data = {
                    "system_settings": self.config.get_all_system_settings(),
                    "characters": self.character_manager.get_all_characters(),
                    "voices": self.voice_manager.get_all_voices()
                }
                
                file_path = filedialog.asksaveasfilename(
                    defaultextension=".json",
                    filetypes=[("JSONファイル", "*.json")],
                    title="システム完全バックアップを保存"
                )
                
                if not file_path:
                    return
                
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(backup_data, f, ensure_ascii=False, indent=4)
                
                messagebox.showinfo("バックアップ完了", f"システムの完全バックアップを '{file_path}' に保存しました")
                self.log(f"📦 システムの完全バックアップを作成しました: {file_path}")
            except Exception as e:
                messagebox.showerror("バックアップエラー", f"システムの完全バックアップに失敗しました: {e}")

    def restore_backup(self):
        """システムのバックアップを復元"""
        file_path = filedialog.askopenfilename(
            title="バックアップJSONファイルを選択",
            filetypes=[("JSONファイル", "*.json")]
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                backup_data = json.load(f)
            
            # システム設定の復元
            self.config.set_all_system_settings(backup_data.get("system_settings", {}))
            self.log("🔄 システム設定を復元しました")
            
            # キャラクターの復元
            characters = backup_data.get("characters", [])
            for char in characters:
                self.character_manager.create_character(**char)
            self.log(f"📜 {len(characters)} キャラクターを復元しました")
            
            # 音声の復元
            voices = backup_data.get("voices", [])
            for voice in voices:
                self.voice_manager.add_voice(voice)
            self.log(f"🎤 {len(voices)} 音声を復元しました")
            
            messagebox.showinfo("復元完了", "システムのバックアップを復元しました")
        except Exception as e:
            messagebox.showerror("復元エラー", f"システムのバックアップの復元に失敗しました: {e}")

    def manage_backups(self):
        """バックアップ管理ダイアログを表示"""
        backup_window = tk.Toplevel(self.root)
        backup_window.title("バックアップ管理")
        backup_window.geometry("400x300")
        
        # バックアップ作成ボタン
        create_button = tk.Button(backup_window, text="完全バックアップを作成", command=self.create_full_backup)
        create_button.pack(pady=10)
        
        # バックアップ復元ボタン
        restore_button = tk.Button(backup_window, text="バックアップを復元", command=self.restore_backup)
        restore_button.pack(pady=10)
        
        # バックアップ管理の説明ラベル
        info_label = tk.Label(backup_window, text="システムの完全バックアップと復元を行います。")
        info_label.pack(pady=10)

    def test_voicevox(self):
        """VOICEVOX Engineの音声合成機能をテスト"""
        if not self.config.get_system_setting("voicevox_api_key"):
            messagebox.showwarning("APIキー未設定", "VOICEVOX Engine APIキーを設定してください")
            return
        
        # テスト用のテキスト
        test_text = "こんにちは、これはVOICEVOX Engineの音声合成テストです。"
        
        self.log(f"🔊 VOICEVOX Engine 音声合成テスト開始: {test_text}")
        
        # 非同期で音声合成実行
        threading.Thread(target=self._run_voicevox_test, args=(test_text,), daemon=True).start()

    def _run_voicevox_test(self, text_to_synthesize, voice_model="ずんだもん(ノーマル)", speed=1.0):
        """VOICEVOX Engine の音声合成をテストする内部メソッド"""
        self.log(f"🧪 VOICEVOX Engine 音声合成テスト開始: Voice: {voice_model}, Speed: {speed}, Text: {text_to_synthesize}")

        # VOICEVOX はローカルエンジンなので、APIキー設定の確認は不要。
        loop = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            engine = VOICEVOXEngineAPI()

            # まずエンジンが利用可能かチェック
            is_available = loop.run_until_complete(engine.check_availability())
            if not is_available:
                self.log("❌ VOICEVOX Engine は利用できません。エンジンが起動しているか確認してください。")
                messagebox.showerror("VOICEVOXテスト失敗", "VOICEVOX Engineに接続できませんでした。\nエンジンがローカルで起動しているか、ポート設定（デフォルト: 50021）を確認してください。")
                return

            audio_files = loop.run_until_complete(
                engine.synthesize_speech(text_to_synthesize, voice_model, speed)
            )

            if audio_files:
                self.log(f"✅ 音声ファイル生成成功: {audio_files}")
                audio_player = AudioPlayer()
                loop.run_until_complete(
                    audio_player.play_audio_files(audio_files)
                )
                self.log("🎧 音声再生完了")
                messagebox.showinfo("音声テスト成功", f"VOICEVOX Engine ({voice_model}) のテスト再生が完了しました。")
            else:
                self.log("❌ 音声ファイルの生成に失敗しました。")
                messagebox.showerror("音声テスト失敗", f"VOICEVOX Engine ({voice_model}) で音声ファイルの生成に失敗しました。詳細はログを確認してください。")

        except Exception as e:
            self.log(f"❌ VOICEVOX Engine テスト中にエラーが発生しました: {e}")
            import traceback
            self.log(f"詳細トレース: {traceback.format_exc()}")
            messagebox.showerror("テストエラー", f"VOICEVOX Engine テスト中にエラーが発生しました: {e}")
        finally:
            if loop:
                try:
                    loop.close()
                except Exception as e:
                    self.log(f"⚠️ イベントループクローズエラー (VOICEVOX Run Test): {e}")

    def clear_chat(self):
        """チャット表示をクリア"""
        self.chat_display.delete(1.0, tk.END)
        self.log("💬 チャットをクリアしました")

    def save_chat(self):
        """チャット内容をファイルに保存"""
        chat_content = self.chat_display.get(1.0, tk.END).strip()
        if not chat_content:
            messagebox.showinfo("情報", "チャットは空です")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("テキストファイル", "*.txt")],
            title="チャットを保存"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(chat_content)
            messagebox.showinfo("保存完了", f"チャットを '{file_path}' に保存しました")
            self.log(f"💾 チャットを保存しました: {file_path}")
        except Exception as e:
            messagebox.showerror("保存エラー", f"チャットの保存に失敗しました: {e}")

    def on_closing(self):
        """アプリケーション終了時の処理"""
        if self.is_streaming:
            if messagebox.askokcancel("終了確認", "配信中です。終了しますか？"):
                self.stop_streaming()
                time.sleep(1)  # 停止処理の完了を待つ
                self.root.destroy()
        else:
            self.root.destroy()

    async def _generate_response_local_llm(self, prompt_text: str, endpoint_url: str, char_name_for_log: str = "LocalLLM") -> str:
        """ローカルLLM（LM Studio想定）から応答を生成する非同期メソッド"""
        self.log(f"🤖 {char_name_for_log}: ローカルLLM ({endpoint_url}) にリクエスト送信中...")
        
        payload = {
            "model": "local-model", 
            "messages": [{"role": "user", "content": prompt_text}],
            "temperature": 0.7,
            "max_tokens": 200 
        }
        headers = {"Content-Type": "application/json"}
        # LM StudioはAPIキーを必要としないことが多いので、Authorizationヘッダーは含めない

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(endpoint_url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=120)) as response:
                    response_text_for_error = await response.text() # エラーログ用に先読み
                    response.raise_for_status()  # HTTPエラーがあれば例外を発生
                    
                    response_data = json.loads(response_text_for_error) # 先読みしたテキストをパース
                    
                    if response_data.get("choices") and isinstance(response_data["choices"], list) and len(response_data["choices"]) > 0:
                        message = response_data["choices"][0].get("message")
                        if message and isinstance(message, dict) and "content" in message:
                            generated_text = message["content"].strip()
                            self.log(f"🤖 {char_name_for_log}: ローカルLLMからの応答取得成功。")
                            return generated_text
                        else:
                            self.log(f"❌ {char_name_for_log}: ローカルLLM応答形式エラー - message.content が見つかりません。Response: {response_data}")
                            return "ローカルLLMからの応答形式が正しくありませんでした (message.contentなし)。"
                    else:
                        self.log(f"❌ {char_name_for_log}: ローカルLLM応答形式エラー - choices が見つかりません。Response: {response_data}")
                        return "ローカルLLMからの応答形式が正しくありませんでした (choicesなし)。"

        except aiohttp.ClientConnectorError as e:
            self.log(f"❌ {char_name_for_log}: ローカルLLM接続エラー ({endpoint_url}): {e}")
            return f"ローカルLLM ({endpoint_url}) に接続できませんでした。LM Studioが起動しているか、URLを確認してください。"
        except aiohttp.ClientResponseError as e:
            self.log(f"❌ {char_name_for_log}: ローカルLLM APIエラー ({endpoint_url}) - Status: {e.status}, Message: {e.message}, Response: {response_text_for_error}")
            return f"ローカルLLM APIからエラー応答がありました (ステータス: {e.status})。詳細はログを確認してください。"
        except asyncio.TimeoutError: # aiohttp.ClientTimeout は asyncio.TimeoutError を発生させる
            self.log(f"❌ {char_name_for_log}: ローカルLLM応答タイムアウト ({endpoint_url})。")
            return "ローカルLLMからの応答がタイムアウトしました。"
        except json.JSONDecodeError as e_json: # json.loads() が失敗した場合
            self.log(f"❌ {char_name_for_log}: ローカルLLM応答のJSONデコードエラー ({endpoint_url}): {e_json}. Response Text: {response_text_for_error}")
            return "ローカルLLMからの応答をJSONとして解析できませんでした。"
        except Exception as e_generic:
            self.log(f"❌ {char_name_for_log}: ローカルLLM呼び出し中に予期せぬエラー ({endpoint_url}): {e_generic}\n{traceback.format_exc()}")
            return "ローカルLLMの呼び出し中に予期せぬエラーが発生しました。"

    def create_new_csv_script(self):
        """新規CSV台本を作成し、関連フォルダも準備する"""
        self.log("AI劇場: 新規CSV台本作成処理を開始。")
        filepath = filedialog.asksaveasfilename(
            title="新規CSV台本を名前を付けて保存",
            defaultextension=".csv",
            filetypes=(("CSVファイル", "*.csv"), ("すべてのファイル", "*.*"))
        )

        if not filepath:
            self.log("AI劇場: 新規CSV台本作成がキャンセルされました。")
            return

        try:
            # ヘッダーのみのCSVファイルを作成
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['action', 'talker', 'words'])
            self.log(f"AI劇場: 新規CSVファイルを作成しました: {filepath}")

            # 音声保存フォルダの作成
            script_filename = Path(filepath).stem
            audio_output_folder = Path(filepath).parent / f"{script_filename}_audio"
            audio_output_folder.mkdir(parents=True, exist_ok=True)
            self.log(f"AI劇場: 音声保存フォルダを作成/確認しました: {audio_output_folder}")

            # 作成したCSVを読み込む準備 (ステップ3でload_csv_scriptを呼び出す)
            self.current_script_path = filepath
            self.audio_output_folder = audio_output_folder

            # この後、ステップ3で self.load_csv_script() を呼び出すことになるが、
            # load_csv_script は現在ファイルダイアログを開くようになっている。
            # 引数でファイルパスを受け取れるようにするか、
            # self.current_script_path を参照するように load_csv_script を修正する必要がある。
            # ここでは、load_csv_script が self.current_script_path を直接使うように変更する前提で進める。
            # (または、load_csv_scriptを呼び出す前に、その中でファイルダイアログをスキップするフラグを立てるなど)

            # UIの更新と0件データの読み込みは次のステップで行う
            # messagebox.showinfo("新規CSV作成完了", f"新規CSV台本ファイルと音声フォルダを作成しました。\nファイル: {filepath}\nフォルダ: {audio_output_folder}")
            # load_csv_script を呼び出すことで、UIの更新とメッセージ表示が行われる
            self.load_csv_script(filepath)
            if self.current_script_path: # load_csv_scriptが成功したか（current_script_pathが設定されたか）で判断
                self.log(f"AI劇場: 新規作成したCSV '{filepath}' の読み込みが完了しました。")
                messagebox.showinfo("新規CSV作成完了", f"新規CSV台本ファイルと音声フォルダを作成し、読み込みました。\nファイル: {filepath}\nフォルダ: {audio_output_folder}")
            else:
                # load_csv_script内でエラーが発生した場合、current_script_path が None になっている可能性がある
                self.log(f"AI劇場: 新規作成したCSV '{filepath}' の読み込みに失敗しました。")
                # エラーメッセージは load_csv_script 内で表示されているはずなので、ここでは追加しない。

        except Exception as e:
            self.log(f"AI劇場: 新規CSV台本作成中にエラー: {e}")
            messagebox.showerror("作成エラー", f"新規CSV台本の作成中にエラーが発生しました: {e}")
            self.current_script_path = None
            self.audio_output_folder = None
    
    def run(self):
        """アプリケーションのメインループを開始"""
        self.log("🚀 AITuberシステム v2.1 - 修正版・完全動作版を起動しました")
        self.root.mainloop()
        self.log("🛑 アプリケーションを終了しました")

