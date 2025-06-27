import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import json
import os
import asyncio
import threading
import time
import random # send_random_message で使用
import requests # test_youtube_api で使用
from pathlib import Path # save_chat で使用 (オプション)

from config import ConfigManager
from character_manager import CharacterManager
from audio_manager import VoiceEngineManager, AudioPlayer, GoogleAIStudioNewVoiceAPI, AvisSpeechEngineAPI, VOICEVOXEngineAPI, SystemTTSAPI
from google import genai # AI対話テストで使用
from google.genai import types as genai_types # AI対話テストで使用

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DebugWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("デバッグ・テスト画面")
        self.root.geometry("900x750")

        self.config = ConfigManager()
        self.character_manager = CharacterManager(self.config)
        self.voice_manager = VoiceEngineManager()
        self.audio_player = AudioPlayer(config_manager=self.config)

        # AI対話テスト用の状態
        self.current_test_character_id = None # デバッグタブ専用のキャラクターID
        self.debug_chat_history = []

        # Geminiモデルリスト (AITuberMainGUIからコピー)
        self.available_gemini_models = [
            "gemini-1.5-flash", "gemini-1.5-flash-latest",
            "gemini-1.5-pro", "gemini-1.5-pro-latest",
            "gemini-2.5-flash", "gemini-2.5-pro"
        ] # ソートは load_settings で行う

        self.create_widgets()
        self.load_settings_for_debug_window() # デバッグウィンドウ用の設定読み込み

    def log(self, message):
        logger.info(message)
        # 必要であればGUIのログ表示ウィジェットにも出力

    def load_settings_for_debug_window(self):
        # キャラクタードロップダウンの初期化
        self.refresh_test_character_dropdown()
        # テストエンジンの音声モデルリスト初期化
        self.update_test_engine_voices()
        # Geminiモデルソート
        def sort_key_gemini(model_name):
            parts = model_name.split('-')
            version_str = parts[1]; version_major = float(version_str) if version_str else 0
            precision_order = {"lite": 0, "flash": 1, "pro": 2}
            precision_val = precision_order.get(parts[2] if len(parts) > 2 else (parts[0] if parts[0] in precision_order else "flash"), 1)
            is_latest = "latest" in model_name
            return (version_major, precision_val, is_latest)
        self.available_gemini_models.sort(key=sort_key_gemini)


    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 音声エンジンテスト
        engine_test_frame = ttk.LabelFrame(main_frame, text="音声エンジンテスト", padding="10")
        engine_test_frame.pack(fill=tk.X, padx=5, pady=5)
        self._create_engine_test_widgets(engine_test_frame)

        # API接続テスト
        api_test_frame = ttk.LabelFrame(main_frame, text="API接続テスト", padding="10")
        api_test_frame.pack(fill=tk.X, padx=5, pady=5)
        self._create_api_test_widgets(api_test_frame)

        # AI対話テスト
        chat_test_frame = ttk.LabelFrame(main_frame, text="AI対話テスト", padding="10")
        chat_test_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self._create_chat_test_widgets(chat_test_frame)


    def _create_engine_test_widgets(self, parent_frame):
        engine_select_frame = ttk.Frame(parent_frame)
        engine_select_frame.pack(fill=tk.X, pady=5)
        ttk.Label(engine_select_frame, text="テストエンジン:").pack(side=tk.LEFT)
        self.test_engine_var = tk.StringVar(value="google_ai_studio_new")
        self.engine_test_combo = ttk.Combobox(engine_select_frame, textvariable=self.test_engine_var,
                                        values=["google_ai_studio_new", "avis_speech", "voicevox", "system_tts"],
                                        state="readonly", width=20)
        self.engine_test_combo.pack(side=tk.LEFT, padx=5)
        self.engine_test_combo.bind('<<ComboboxSelected>>', self.update_test_engine_voices)

        ttk.Label(engine_select_frame, text="音声モデル:").pack(side=tk.LEFT, padx=(10,0))
        self.test_voice_model_var = tk.StringVar()
        self.voice_model_test_combo = ttk.Combobox(engine_select_frame, textvariable=self.test_voice_model_var,
                                       state="readonly", width=25)
        self.voice_model_test_combo.pack(side=tk.LEFT, padx=5)

        text_frame = ttk.Frame(parent_frame)
        text_frame.pack(fill=tk.X, pady=5)
        ttk.Label(text_frame, text="テストテキスト:").pack(anchor=tk.W)
        self.test_text_var = tk.StringVar(value="これは音声エンジンのテストメッセージです。")
        ttk.Entry(text_frame, textvariable=self.test_text_var, width=80).pack(fill=tk.X, pady=2)

        test_buttons = ttk.Frame(parent_frame)
        test_buttons.pack(fill=tk.X, pady=5)
        ttk.Button(test_buttons, text="🎤 選択エンジンでテスト", command=self.run_selected_engine_test).pack(side=tk.LEFT, padx=2)
        ttk.Button(test_buttons, text="🔄 全エンジン比較", command=self.run_all_engines_comparison).pack(side=tk.LEFT, padx=2)
        ttk.Button(test_buttons, text="📊 エンジン状態確認", command=self.check_all_engines_status).pack(side=tk.LEFT, padx=2)
        # ttk.Button(test_buttons, text="⚡ 性能ベンチマーク", command=self.run_engine_performance_benchmark).pack(side=tk.LEFT, padx=2) # 必要なら


    def _create_api_test_widgets(self, parent_frame):
        api_buttons = ttk.Frame(parent_frame)
        api_buttons.pack(fill=tk.X, pady=5)
        ttk.Button(api_buttons, text="🤖 Google AI Studio (音声/文章)", command=self.test_google_ai_studio_api).pack(side=tk.LEFT, padx=5)
        ttk.Button(api_buttons, text="📺 YouTube API", command=self.test_youtube_api_connection).pack(side=tk.LEFT, padx=5)
        ttk.Button(api_buttons, text="🎙️ Avis Speech (接続)", command=self.test_avis_speech_connection).pack(side=tk.LEFT, padx=5)
        ttk.Button(api_buttons, text="🎤 VOICEVOX (接続)", command=self.test_voicevox_connection).pack(side=tk.LEFT, padx=5)


    def _create_chat_test_widgets(self, parent_frame):
        # キャラクター選択
        char_select_frame = ttk.Frame(parent_frame)
        char_select_frame.pack(fill=tk.X, pady=5)
        ttk.Label(char_select_frame, text="テスト用キャラクター:").pack(side=tk.LEFT)
        self.test_char_var = tk.StringVar()
        self.test_char_combo = ttk.Combobox(char_select_frame, textvariable=self.test_char_var, state="readonly", width=30)
        self.test_char_combo.pack(side=tk.LEFT, padx=5)
        self.test_char_combo.bind('<<ComboboxSelected>>', self.on_test_character_selected)
        ttk.Button(char_select_frame, text="🔄 更新", command=self.refresh_test_character_dropdown).pack(side=tk.LEFT, padx=2)


        chat_control_frame = ttk.Frame(parent_frame)
        chat_control_frame.pack(fill=tk.X, pady=(0,5))
        ttk.Button(chat_control_frame, text="🗑️ チャットクリア", command=self.clear_debug_chat_display).pack(side=tk.RIGHT, padx=5)
        # ttk.Button(chat_control_frame, text="💾 チャット保存", command=self.save_debug_chat_log).pack(side=tk.RIGHT, padx=5) # オプション

        chat_display_frame = ttk.Frame(parent_frame)
        chat_display_frame.pack(fill=tk.BOTH, expand=True)
        self.debug_chat_display_text = tk.Text(chat_display_frame, height=15, wrap=tk.WORD, state=tk.DISABLED)
        chat_scroll = ttk.Scrollbar(chat_display_frame, orient=tk.VERTICAL, command=self.debug_chat_display_text.yview)
        self.debug_chat_display_text.configure(yscrollcommand=chat_scroll.set)
        self.debug_chat_display_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        chat_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        input_frame = ttk.Frame(parent_frame) # main_frameではなく、chat_test_frame の中が適切
        input_frame.pack(fill=tk.X, pady=5)
        ttk.Label(input_frame, text="メッセージ:").pack(side=tk.LEFT)
        self.debug_chat_input_var = tk.StringVar()
        chat_entry = ttk.Entry(input_frame, textvariable=self.debug_chat_input_var, width=60)
        chat_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        chat_entry.bind('<Return>', self.send_debug_message_action)
        ttk.Button(input_frame, text="送信", command=self.send_debug_message_action).pack(side=tk.RIGHT, padx=5)
        ttk.Button(input_frame, text="🎲 ランダム", command=self.send_random_debug_message).pack(side=tk.RIGHT, padx=2)

    def refresh_test_character_dropdown(self):
        characters = self.character_manager.get_all_characters()
        char_options = [f"{data.get('name', 'Unknown')} ({char_id})" for char_id, data in characters.items()]
        self.test_char_combo['values'] = char_options
        if char_options:
            # 以前の選択を維持しようと試みる
            current_selection_text = self.test_char_var.get()
            if current_selection_text in char_options:
                self.test_char_var.set(current_selection_text) # そのまま
            else: # なければ最初のものを選択
                self.test_char_var.set(char_options[0])
            self.on_test_character_selected() # 選択処理を呼び出しIDを更新
        else:
            self.test_char_var.set("")
            self.current_test_character_id = None
        self.log("デバッグ用キャラクタードロップダウンを更新。")


    def on_test_character_selected(self, event=None):
        selection = self.test_char_var.get()
        if selection and '(' in selection and ')' in selection:
            self.current_test_character_id = selection.split('(')[-1].replace(')', '')
            self.log(f"デバッグ用キャラクターとして '{selection}' (ID: {self.current_test_character_id}) を選択。")
        else:
            self.current_test_character_id = None
            self.log("デバッグ用キャラクターの選択が解除されました。")


    def update_test_engine_voices(self, event=None):
        engine_choice = self.test_engine_var.get()
        voices = []
        default_voice = ""
        engine_instance = self.voice_manager.get_engine_instance(engine_choice)

        if engine_instance:
            try:
                # check_availability を呼び出す (必要な場合)
                if asyncio.iscoroutinefunction(getattr(engine_instance, 'check_availability', None)):
                    loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
                    try: loop.run_until_complete(engine_instance.check_availability())
                    finally: loop.close()
                elif hasattr(engine_instance, 'check_availability'):
                    engine_instance.check_availability()

                voices = engine_instance.get_available_voices()
                default_voice = voices[0] if voices else ""
            except Exception as e:
                self.log(f"テストエンジン {engine_choice} の音声リスト取得エラー: {e}")
                voices = ["エラー"]
                default_voice = "エラー"
        else:
            voices = ["N/A"]; default_voice = "N/A"

        self.voice_model_test_combo['values'] = voices
        self.test_voice_model_var.set(default_voice if voices else "")


    def run_selected_engine_test(self):
        engine = self.test_engine_var.get()
        model = self.test_voice_model_var.get()
        text = self.test_text_var.get()
        if not text:
            messagebox.showwarning("入力エラー", "テストテキストを入力してください。", parent=self.root)
            return
        if not model or model == "エラー" or model == "N/A":
            messagebox.showwarning("モデルエラー", "有効な音声モデルが選択されていません。", parent=self.root)
            return

        self.log(f"🎤 音声テスト開始: エンジン={engine}, モデル={model}, テキスト='{text[:20]}...'")
        api_key_google = self.config.get_system_setting("google_ai_api_key")

        def run_async():
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            try:
                # VoiceEngineManager を通じて合成と再生
                audio_files = loop.run_until_complete(
                    self.voice_manager.synthesize_with_fallback(
                        text, model, 1.0, preferred_engine=engine, api_key=api_key_google
                    )
                )
                if audio_files:
                    loop.run_until_complete(self.audio_player.play_audio_files(audio_files))
                    self.log("✅ 音声テスト（選択エンジン）完了。")
                else:
                    self.log("❌ 音声テスト（選択エンジン）失敗: 音声ファイル生成できず。")
                    messagebox.showerror("テスト失敗", "音声ファイルの生成に失敗しました。", parent=self.root)
            except Exception as e:
                self.log(f"❌ 音声テスト（選択エンジン）エラー: {e}")
                messagebox.showerror("テストエラー", f"エラー: {e}", parent=self.root)
            finally:
                loop.close()
        threading.Thread(target=run_async, daemon=True).start()


    def run_all_engines_comparison(self):
        text = self.test_text_var.get()
        if not text:
            messagebox.showwarning("入力エラー", "比較テスト用のテキストを入力してください。", parent=self.root)
            return
        self.log("🔄 全音声エンジン比較テスト開始...")
        api_key_google = self.config.get_system_setting("google_ai_api_key")

        def run_async():
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            try:
                engines_to_test = ["google_ai_studio_new", "avis_speech", "voicevox", "system_tts"]
                for i, engine_name in enumerate(engines_to_test):
                    engine_instance = self.voice_manager.get_engine_instance(engine_name)
                    if not engine_instance: continue
                    # check_availability
                    if asyncio.iscoroutinefunction(getattr(engine_instance, 'check_availability', None)):
                        loop.run_until_complete(engine_instance.check_availability())
                    elif hasattr(engine_instance, 'check_availability'): engine_instance.check_availability()

                    voices = engine_instance.get_available_voices()
                    model_to_use = voices[0] if voices else None
                    if not model_to_use:
                        self.log(f"エンジン {engine_name} の利用可能音声なし、スキップ。")
                        continue

                    self.log(f"🎵 比較中 ({i+1}/{len(engines_to_test)}): {engine_name} (モデル: {model_to_use})")
                    current_test_text = f"エンジン{i+1}番、{engine_name}。{text}"
                    audio_files = loop.run_until_complete(
                        self.voice_manager.synthesize_with_fallback(
                            current_test_text, model_to_use, 1.0, preferred_engine=engine_name, api_key=api_key_google
                        )
                    )
                    if audio_files:
                        loop.run_until_complete(self.audio_player.play_audio_files(audio_files))
                        self.log(f"✅ {engine_name} 比較再生完了。")
                    else:
                        self.log(f"❌ {engine_name} 比較再生失敗。")
                    time.sleep(0.5) # 間隔
                self.log("🎉 全エンジン比較完了。")
            except Exception as e:
                self.log(f"❌ 全エンジン比較エラー: {e}")
                messagebox.showerror("比較エラー", f"エラー: {e}", parent=self.root)
            finally:
                loop.close()
        threading.Thread(target=run_async, daemon=True).start()


    def check_all_engines_status(self):
        self.log("📊 全音声エンジン状態確認開始...")
        def run_async():
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            try:
                availability = loop.run_until_complete(self.voice_manager.check_engines_availability())
                status_message = "エンジン状態:\n"
                for engine, is_available in availability.items():
                    status_message += f"- {engine}: {'✅ 利用可能' if is_available else '❌ 利用不可'}\n"
                self.log(status_message)
                messagebox.showinfo("エンジン状態", status_message, parent=self.root)
            except Exception as e:
                self.log(f"❌ エンジン状態確認エラー: {e}")
                messagebox.showerror("状態確認エラー", f"エラー: {e}", parent=self.root)
            finally:
                loop.close()
        threading.Thread(target=run_async, daemon=True).start()


    def test_google_ai_studio_api(self):
        api_key = self.config.get_system_setting("google_ai_api_key")
        if not api_key:
            messagebox.showwarning("APIキー未設定", "Google AI Studio APIキーが設定されていません。", parent=self.root)
            return
        self.log("🧪 Google AI Studio API テスト開始 (音声合成 & 簡単な文章生成)")
        test_text_speech = "Google AI Studioの新しい音声合成APIのテストです。"
        test_prompt_text = "「こんにちは」と返事してください。"

        def run_async():
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            # 音声合成テスト
            try:
                engine_speech = GoogleAIStudioNewVoiceAPI()
                # 利用可能な最初の音声モデルを使用 (例: alloy)
                available_voices = engine_speech.get_available_voices()
                model_speech = available_voices[0] if available_voices else "alloy"

                audio_files = loop.run_until_complete(engine_speech.synthesize_speech(test_text_speech, model_speech, 1.0, api_key=api_key))
                if audio_files:
                    loop.run_until_complete(self.audio_player.play_audio_files(audio_files))
                    self.log(f"✅ Google AI Studio 音声合成テスト成功 (モデル: {model_speech})。")
                    messagebox.showinfo("Google AI 音声テスト", "音声合成テスト成功！", parent=self.root)
                else:
                    self.log("❌ Google AI Studio 音声合成テスト失敗。")
                    messagebox.showerror("Google AI 音声テスト", "音声合成テスト失敗。", parent=self.root)
            except Exception as e_speech:
                self.log(f"❌ Google AI Studio 音声合成テストエラー: {e_speech}")
                messagebox.showerror("Google AI 音声テストエラー", f"音声合成エラー: {e_speech}", parent=self.root)

            time.sleep(0.5) # 少し待つ

            # 文章生成テスト
            try:
                client = genai.Client(api_key=api_key)
                # 設定からテキスト生成モデルを取得、なければデフォルト
                text_gen_model_name = self.config.get_system_setting("text_generation_model", "gemini-1.5-flash")
                if "local" in text_gen_model_name: # ローカルモデルはこのテストでは対象外
                     self.log("ℹ️ Google AI Studio 文章生成テスト: テキスト生成モデルがローカルLLMのためスキップ。")
                     return

                response = client.models.generate_content(model=text_gen_model_name, contents=test_prompt_text)
                if response.text:
                    self.log(f"✅ Google AI Studio 文章生成テスト成功。応答: {response.text.strip()}")
                    messagebox.showinfo("Google AI 文章テスト", f"文章生成テスト成功！\n応答: {response.text.strip()}", parent=self.root)
                else:
                    self.log("❌ Google AI Studio 文章生成テスト失敗。応答なし。")
                    messagebox.showerror("Google AI 文章テスト", "文章生成テスト失敗。応答がありませんでした。", parent=self.root)
            except Exception as e_text:
                self.log(f"❌ Google AI Studio 文章生成テストエラー: {e_text}")
                messagebox.showerror("Google AI 文章テストエラー", f"文章生成エラー: {e_text}", parent=self.root)
            finally:
                loop.close()
        threading.Thread(target=run_async, daemon=True).start()


    def test_youtube_api_connection(self):
        # settings_window.py の test_youtube_api とほぼ同じロジック
        api_key = self.config.get_system_setting("youtube_api_key")
        if not api_key:
            messagebox.showwarning("APIキー未設定", "YouTube APIキーが設定されていません。", parent=self.root)
            return
        self.log("🧪 YouTube API 接続テスト開始...")
        test_channel_id = "UC_x5XG1OV2P6uZZ5FSM9Ttw" # Google Developers
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
            self.log(f"❌ YouTube API HTTPエラー: {http_err.response.status_code} - {http_err.response.text}")
            messagebox.showerror("YouTube APIテスト失敗", f"HTTPエラー: {http_err.response.status_code}", parent=self.root)
        except requests.exceptions.RequestException as req_err:
             self.log(f"❌ YouTube API リクエストエラー: {req_err}")
             messagebox.showerror("YouTube APIテスト失敗", f"リクエストエラー: {req_err}", parent=self.root)
        except Exception as e:
            self.log(f"❌ YouTube API テスト中に予期せぬエラー: {e}")
            messagebox.showerror("YouTube APIテストエラー", f"予期せぬエラー: {e}", parent=self.root)


    def _test_local_engine_connection(self, engine_name, engine_class):
        self.log(f"🧪 {engine_name} 接続テスト開始...")
        def run_async():
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            try:
                engine = engine_class()
                is_available = loop.run_until_complete(engine.check_availability())
                if is_available:
                    voices = engine.get_available_voices()
                    voices_str = ", ".join(voices[:3]) + ("..." if len(voices) > 3 else "")
                    self.log(f"✅ {engine_name} 接続成功。利用可能音声(一部): {voices_str}")
                    messagebox.showinfo(f"{engine_name}テスト成功", f"接続成功。\n音声(一部): {voices_str}", parent=self.root)
                else:
                    self.log(f"❌ {engine_name} 接続失敗。エンジンが起動しているか確認してください。")
                    messagebox.showerror(f"{engine_name}テスト失敗", "接続失敗。エンジンが起動しているか確認してください。", parent=self.root)
            except Exception as e:
                self.log(f"❌ {engine_name} テストエラー: {e}")
                messagebox.showerror(f"{engine_name}テストエラー", f"エラー: {e}", parent=self.root)
            finally:
                loop.close()
        threading.Thread(target=run_async, daemon=True).start()

    def test_avis_speech_connection(self):
        self._test_local_engine_connection("Avis Speech Engine", AvisSpeechEngineAPI)

    def test_voicevox_connection(self):
        self._test_local_engine_connection("VOICEVOX Engine", VOICEVOXEngineAPI)

    def _add_to_debug_chat_display(self, message):
        self.debug_chat_display_text.config(state=tk.NORMAL)
        self.debug_chat_display_text.insert(tk.END, message + "\n")
        self.debug_chat_display_text.see(tk.END)
        self.debug_chat_display_text.config(state=tk.DISABLED)

    def clear_debug_chat_display(self):
        self.debug_chat_display_text.config(state=tk.NORMAL)
        self.debug_chat_display_text.delete(1.0, tk.END)
        self.debug_chat_display_text.config(state=tk.DISABLED)
        self.debug_chat_history.clear()
        self.log("💬 デバッグチャット表示をクリアしました。")

    def send_debug_message_action(self, event=None):
        user_message = self.debug_chat_input_var.get()
        if not user_message: return
        if not self.current_test_character_id:
            self._add_to_debug_chat_display("❌ システム: AI対話テスト用のキャラクターを選択してください。")
            return

        self._add_to_debug_chat_display(f"👤 あなた: {user_message}")
        self.debug_chat_input_var.set("")

        threading.Thread(target=self._generate_debug_ai_response, args=(user_message,), daemon=True).start()

    def _generate_debug_ai_response(self, user_message):
        try:
            api_key = self.config.get_system_setting("google_ai_api_key")
            if not api_key:
                self.root.after(0, self._add_to_debug_chat_display, "❌ AI: Google AI APIキーが未設定です。")
                return

            char_data = self.character_manager.get_character(self.current_test_character_id)
            if not char_data:
                self.root.after(0, self._add_to_debug_chat_display, "❌ AI: キャラクターデータが見つかりません。")
                return

            char_name = char_data.get('name', 'AI')
            char_prompt = self.character_manager.get_character_prompt(self.current_test_character_id)
            history_len = self.config.get_system_setting("conversation_history_length", 5) # デフォルト5件

            current_conversation_history = []
            for entry in self.debug_chat_history[-history_len:]: # 直近の履歴
                 current_conversation_history.append(f"ユーザー: {entry['user']}")
                 current_conversation_history.append(f"{char_name}: {entry['ai']}")
            history_str = "\n".join(current_conversation_history)

            full_prompt = f"{char_prompt}\n\nこれまでの会話:\n{history_str}\n\nユーザー: {user_message}\n\n{char_name}:"

            client = genai.Client(api_key=api_key)
            text_gen_model_name = self.config.get_system_setting("text_generation_model", "gemini-1.5-flash")
            ai_response_text = "エラー：応答生成に失敗"

            if "local_lm_studio" == text_gen_model_name:
                local_llm_url = self.config.get_system_setting("local_llm_endpoint_url")
                if not local_llm_url:
                    ai_response_text = "ローカルLLMエンドポイントURLが未設定です。"
                else: # 非同期呼び出し
                    loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
                    try: ai_response_text = loop.run_until_complete(self._generate_response_local_llm(full_prompt, local_llm_url, char_name))
                    finally: loop.close()
            else:
                response = client.models.generate_content(model=text_gen_model_name, contents=full_prompt,
                                                       generation_config=genai_types.GenerateContentConfig(temperature=0.8, max_output_tokens=150))
                ai_response_text = response.text.strip() if response.text else "うーん、ちょっとうまく思いつかないや。"

            self.root.after(0, self._add_to_debug_chat_display, f"🤖 {char_name}: {ai_response_text}")
            self.debug_chat_history.append({"user": user_message, "ai": ai_response_text})
            if len(self.debug_chat_history) > 20: self.debug_chat_history.pop(0) # 最大20件保持

            # 音声再生
            voice_settings = char_data.get('voice_settings', {})
            preferred_engine = voice_settings.get('engine', self.config.get_system_setting('voice_engine'))
            model = voice_settings.get('model')
            speed = voice_settings.get('speed', 1.0)

            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            try:
                audio_files = loop.run_until_complete(
                    self.voice_manager.synthesize_with_fallback(
                        ai_response_text, model, speed, preferred_engine=preferred_engine, api_key=api_key
                    )
                )
                if audio_files:
                    loop.run_until_complete(self.audio_player.play_audio_files(audio_files))
            finally:
                loop.close()

        except genai_types.BlockedPromptException:
            self.root.after(0, self._add_to_debug_chat_display, f"🤖 {char_name}: その内容についてはお答えできません。")
        except Exception as e:
            self.log(f"❌ AI対話テストエラー: {e}")
            self.root.after(0, self._add_to_debug_chat_display, f"🤖 {char_name}: ごめんなさい、ちょっと調子が悪いみたいです。")


    async def _generate_response_local_llm(self, prompt_text: str, endpoint_url: str, char_name_for_log: str = "LocalLLM") -> str:
        # gui.pyから移植 (aiohttpが必要)
        self.log(f"🤖 {char_name_for_log}: ローカルLLM ({endpoint_url}) にリクエスト送信中...")
        payload = {"model": "local-model", "messages": [{"role": "user", "content": prompt_text}], "temperature": 0.7, "max_tokens": 200}
        headers = {"Content-Type": "application/json"}
        try:
            import aiohttp # ここでimport
            async with aiohttp.ClientSession() as session:
                async with session.post(endpoint_url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=120)) as response:
                    response_text_for_error = await response.text()
                    response.raise_for_status()
                    response_data = json.loads(response_text_for_error)
                    if response_data.get("choices") and response_data["choices"][0].get("message"):
                        return response_data["choices"][0]["message"].get("content", "").strip()
                    return "ローカルLLM応答形式エラー (message.contentなし)"
        except Exception as e:
            self.log(f"❌ ローカルLLM呼び出しエラー ({endpoint_url}): {e}")
            return f"ローカルLLM呼び出しエラー: {e}"


    def send_random_debug_message(self):
        if not self.current_test_character_id:
            self._add_to_debug_chat_display("❌ システム: AI対話テスト用のキャラクターを選択してください。")
            return
        messages = [
            "今日の天気は？", "好きな食べ物は何？", "趣味は何ですか？",
            "最近あった面白い話をして。", "おすすめの曲を教えて。"
        ]
        self.debug_chat_input_var.set(random.choice(messages))
        self.send_debug_message_action()


def main():
    root = tk.Tk()
    app = DebugWindow(root)
    root.mainloop()

if __name__ == "__main__":
    main()
