import customtkinter
import tkinter as tk # 基本的な型 (StringVarなど) と標準ダイアログのため
from tkinter import messagebox, simpledialog # 標準ダイアログはそのまま使用 (filedialogは未使用)
import json
import os
import asyncio
import threading
import time
import random
import requests
from pathlib import Path
import sys # フォント選択のため

from config import ConfigManager
from character_manager import CharacterManager
from audio_manager import VoiceEngineManager, AudioPlayer, GoogleAIStudioNewVoiceAPI, AvisSpeechEngineAPI, VOICEVOXEngineAPI, SystemTTSAPI
from google import genai
from google.genai import types as genai_types

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DebugWindow:
    def __init__(self, root: customtkinter.CTk):
        self.root = root
        self.root.title("デバッグ・テスト画面")
        self.root.geometry("950x800")

        self.loading_label = customtkinter.CTkLabel(self.root, text="読み込み中...", font=("Yu Gothic UI", 18))
        self.loading_label.pack(expand=True, fill="both")
        self.root.update_idletasks()

        self.root.after(50, self._initialize_components)

    def _initialize_components(self):
        if hasattr(self, 'loading_label') and self.loading_label.winfo_exists():
            self.loading_label.pack_forget()
            self.loading_label.destroy()

        self.config = ConfigManager()
        self.character_manager = CharacterManager(self.config)
        self.voice_manager = VoiceEngineManager()
        self.audio_player = AudioPlayer(config_manager=self.config)

        self.current_test_character_id = None
        self.debug_chat_history = []

        # フォント設定
        self.default_font = ("Yu Gothic UI", 12)
        if sys.platform == "darwin": self.default_font = ("Hiragino Sans", 14)
        elif sys.platform.startswith("linux"): self.default_font = ("Noto Sans CJK JP", 12)
        self.label_font = (self.default_font[0], self.default_font[1] + 1, "bold")

        self.available_gemini_models = [
            "gemini-1.5-flash", "gemini-1.5-flash-latest",
            "gemini-1.5-pro", "gemini-1.5-pro-latest",
            "gemini-2.5-flash", "gemini-2.5-pro"
        ]
        self.load_settings_for_debug_window() # ここでソートも行われる
        self.create_widgets()
        self.log("デバッグウィンドウが初期化されました。")


    def log(self, message):
        logger.info(message)
        if hasattr(self, 'debug_chat_display_text') and self.debug_chat_display_text:
            try: # 起動時にまだウィジェットがない場合があるため
                self.debug_chat_display_text.configure(state="normal")
                self.debug_chat_display_text.insert("end", f"[LOG] {message}\n")
                self.debug_chat_display_text.see("end")
                self.debug_chat_display_text.configure(state="disabled")
            except tk.TclError: # ウィンドウ破棄後など
                pass
            except AttributeError: # ウィジェットがまだない場合
                 logger.warning(f"Log widget not available for: {message}")
            except Exception: # その他の予期せぬエラー
                pass


    def load_settings_for_debug_window(self):
        if hasattr(self, 'test_char_combo'): # ウィジェット作成後か確認
            self.refresh_test_character_dropdown()
        if hasattr(self, 'engine_test_combo'):
            self.update_test_engine_voices()

        def sort_key_gemini(model_name):
            parts = model_name.split('-')
            version_str = parts[1]; version_major = float(version_str) if len(parts) > 1 and version_str.replace('.', '', 1).isdigit() else 0.0
            precision_order = {"lite": 0, "flash": 1, "pro": 2}
            precision_val = precision_order.get(parts[2] if len(parts) > 2 else (parts[0] if parts[0] in precision_order else "flash"), 1)
            is_latest = "latest" in model_name
            return (version_major, precision_val, is_latest)
        self.available_gemini_models.sort(key=sort_key_gemini)

    def create_widgets(self):
        main_scroll_frame = customtkinter.CTkScrollableFrame(self.root)
        main_scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # 音声エンジンテスト
        engine_test_outer_frame = customtkinter.CTkFrame(main_scroll_frame)
        engine_test_outer_frame.pack(fill="x", padx=5, pady=5)
        customtkinter.CTkLabel(engine_test_outer_frame, text="音声エンジンテスト", font=self.label_font).pack(anchor="w", padx=10, pady=(5,0))
        engine_test_frame = customtkinter.CTkFrame(engine_test_outer_frame)
        engine_test_frame.pack(fill="x", padx=5, pady=5)
        self._create_engine_test_widgets(engine_test_frame)

        # API接続テスト
        api_test_outer_frame = customtkinter.CTkFrame(main_scroll_frame)
        api_test_outer_frame.pack(fill="x", padx=5, pady=5)
        customtkinter.CTkLabel(api_test_outer_frame, text="API接続テスト", font=self.label_font).pack(anchor="w", padx=10, pady=(5,0))
        api_test_frame = customtkinter.CTkFrame(api_test_outer_frame)
        api_test_frame.pack(fill="x", padx=5, pady=5)
        self._create_api_test_widgets(api_test_frame)

        # AI対話テスト
        chat_test_outer_frame = customtkinter.CTkFrame(main_scroll_frame)
        chat_test_outer_frame.pack(fill="both", expand=True, padx=5, pady=5)
        customtkinter.CTkLabel(chat_test_outer_frame, text="AI対話テスト", font=self.label_font).pack(anchor="w", padx=10, pady=(5,0))
        chat_test_frame = customtkinter.CTkFrame(chat_test_outer_frame)
        chat_test_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self._create_chat_test_widgets(chat_test_frame)

    def _create_engine_test_widgets(self, parent_frame: customtkinter.CTkFrame):
        engine_select_frame = customtkinter.CTkFrame(parent_frame, fg_color="transparent")
        engine_select_frame.pack(fill="x", pady=5)
        customtkinter.CTkLabel(engine_select_frame, text="テストエンジン:", font=self.default_font).pack(side="left")
        self.test_engine_var = tk.StringVar(value="google_ai_studio_new")
        self.engine_test_combo = customtkinter.CTkComboBox(engine_select_frame, variable=self.test_engine_var,
                                        values=["google_ai_studio_new", "avis_speech", "voicevox", "system_tts"],
                                        state="readonly", width=200, font=self.default_font, command=self.update_test_engine_voices)
        self.engine_test_combo.pack(side="left", padx=5)

        customtkinter.CTkLabel(engine_select_frame, text="音声モデル:", font=self.default_font).pack(side="left", padx=(10,0))
        self.test_voice_model_var = tk.StringVar()
        self.voice_model_test_combo = customtkinter.CTkComboBox(engine_select_frame, variable=self.test_voice_model_var,
                                       state="readonly", width=220, font=self.default_font)
        self.voice_model_test_combo.pack(side="left", padx=5)
        
        characters = self.character_manager.get_all_characters()
        char_options = [f"{data.get('name', 'Unknown')} ({char_id})" for char_id, data in characters.items()]
        self.voice_model_test_combo.configure(values=char_options if char_options else ["キャラクターなし"])
        if char_options:
            current_selection_text = self.test_voice_model_var.get()
            if current_selection_text in char_options: self.test_voice_model_var.set(current_selection_text)
            else: self.test_voice_model_var.set(char_options[0])
            #self.on_test_character_selected()
        else:
            self.test_voice_model_var.set("キャラクターなし")
            self.current_test_character_id = None
        self.log("デバッグ用キャラクタードロップダウンを更新。")

        text_frame = customtkinter.CTkFrame(parent_frame, fg_color="transparent")
        text_frame.pack(fill="x", pady=5)
        customtkinter.CTkLabel(text_frame, text="テストテキスト:", font=self.default_font).pack(anchor="w")
        self.test_text_var = tk.StringVar(value="これは音声エンジンのテストメッセージです。")
        customtkinter.CTkEntry(text_frame, textvariable=self.test_text_var, width=600, font=self.default_font).pack(fill="x", pady=2)

        test_buttons = customtkinter.CTkFrame(parent_frame, fg_color="transparent")
        test_buttons.pack(fill="x", pady=5)
        customtkinter.CTkButton(test_buttons, text="🎤 選択エンジンでテスト", command=self.run_selected_engine_test, font=self.default_font).pack(side="left", padx=2)
        customtkinter.CTkButton(test_buttons, text="🔄 全エンジン比較", command=self.run_all_engines_comparison, font=self.default_font).pack(side="left", padx=2)
        customtkinter.CTkButton(test_buttons, text="📊 エンジン状態確認", command=self.check_all_engines_status, font=self.default_font).pack(side="left", padx=2)

    def _create_api_test_widgets(self, parent_frame: customtkinter.CTkFrame):
        api_buttons = customtkinter.CTkFrame(parent_frame, fg_color="transparent")
        api_buttons.pack(fill="x", pady=5)
        customtkinter.CTkButton(api_buttons, text="🤖 Google AI Studio (音声/文章)", command=self.test_google_ai_studio_api, font=self.default_font).pack(side="left", padx=5, pady=5)
        customtkinter.CTkButton(api_buttons, text="📺 YouTube API", command=self.test_youtube_api_connection, font=self.default_font).pack(side="left", padx=5, pady=5)
        customtkinter.CTkButton(api_buttons, text="🎙️ Avis Speech (接続)", command=self.test_avis_speech_connection, font=self.default_font).pack(side="left", padx=5, pady=5)
        customtkinter.CTkButton(api_buttons, text="🎤 VOICEVOX (接続)", command=self.test_voicevox_connection, font=self.default_font).pack(side="left", padx=5, pady=5)

    def _create_chat_test_widgets(self, parent_frame: customtkinter.CTkFrame):
        char_select_frame = customtkinter.CTkFrame(parent_frame, fg_color="transparent")
        char_select_frame.pack(fill="x", pady=5)
        customtkinter.CTkLabel(char_select_frame, text="テスト用キャラクター:", font=self.default_font).pack(side="left")

        self.test_char_var = tk.StringVar()
        self.test_char_combo = customtkinter.CTkComboBox(char_select_frame, variable=self.test_char_var, state="readonly", width=250, font=self.default_font, command=self.on_test_character_selected)
        self.test_char_combo.pack(side="left", padx=5)
        customtkinter.CTkButton(char_select_frame, text="🔄 更新", command=self.refresh_test_character_dropdown, font=self.default_font, width=60).pack(side="left", padx=2)


        characters = self.character_manager.get_all_characters()
        char_options = [f"{data.get('name', 'Unknown')} ({char_id})" for char_id, data in characters.items()]
        self.test_char_combo.configure(values=char_options if char_options else ["キャラクターなし"])
        if char_options:
            current_selection_text = self.test_char_var.get()
            if current_selection_text in char_options: self.test_char_var.set(current_selection_text)
            else: self.test_char_var.set(char_options[0])
            self.on_test_character_selected()
        else:
            self.test_char_var.set("キャラクターなし")
            self.current_test_character_id = None
        self.log("デバッグ用キャラクタードロップダウンを更新。")



        chat_control_frame = customtkinter.CTkFrame(parent_frame, fg_color="transparent")
        chat_control_frame.pack(fill="x", pady=(0,5))
        customtkinter.CTkButton(chat_control_frame, text="🗑️ チャットクリア", command=self.clear_debug_chat_display, font=self.default_font).pack(side="right", padx=5)

        self.debug_chat_display_text = customtkinter.CTkTextbox(parent_frame, height=200, wrap="word", state="disabled", font=self.default_font) # CTkTextbox
        self.debug_chat_display_text.pack(fill="both", expand=True, padx=5, pady=5)

        input_frame = customtkinter.CTkFrame(parent_frame, fg_color="transparent")
        input_frame.pack(fill="x", pady=5)
        customtkinter.CTkLabel(input_frame, text="メッセージ:", font=self.default_font).pack(side="left")
        self.debug_chat_input_var = tk.StringVar()
        chat_entry = customtkinter.CTkEntry(input_frame, textvariable=self.debug_chat_input_var, width=400, font=self.default_font, placeholder_text="テストメッセージを入力...")
        chat_entry.pack(side="left", fill="x", expand=True, padx=5)
        chat_entry.bind('<Return>', self.send_debug_message_action)
        customtkinter.CTkButton(input_frame, text="送信", command=self.send_debug_message_action, font=self.default_font, width=80).pack(side="right", padx=5)
        customtkinter.CTkButton(input_frame, text="🎲 ランダム", command=self.send_random_debug_message, font=self.default_font, width=80).pack(side="right", padx=2)

    def refresh_test_character_dropdown(self):
        characters = self.character_manager.get_all_characters()
        char_options = [f"{data.get('name', 'Unknown')} ({char_id})" for char_id, data in characters.items()]
        self.test_char_combo.configure(values=char_options if char_options else ["キャラクターなし"])
        if char_options:
            current_selection_text = self.test_char_var.get()
            if current_selection_text in char_options: self.test_char_var.set(current_selection_text)
            else: self.test_char_var.set(char_options[0])
            self.on_test_character_selected()
        else:
            self.test_char_var.set("キャラクターなし")
            self.current_test_character_id = None
        self.log("デバッグ用キャラクタードロップダウンを更新。")

    def on_test_character_selected(self, choice=None): # CTkComboBoxのcommandは選択値を渡す
        selection = self.test_char_var.get()
        if selection and '(' in selection and ')' in selection and selection != "キャラクターなし":
            self.current_test_character_id = selection.split('(')[-1].replace(')', '')
            self.log(f"デバッグ用キャラクターとして '{selection}' (ID: {self.current_test_character_id}) を選択。")
        else:
            self.current_test_character_id = None
            self.log("デバッグ用キャラクターの選択が解除されました。")

    def update_test_engine_voices(self, choice=None): # CTkComboBoxのcommandは選択値を渡す
        engine_choice = self.test_engine_var.get()
        voices = []
        default_voice = ""
        engine_instance = self.voice_manager.get_engine_instance(engine_choice)
        if engine_instance:
            try:
                if asyncio.iscoroutinefunction(getattr(engine_instance, 'check_availability', None)):
                    loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
                    try: loop.run_until_complete(engine_instance.check_availability())
                    finally: loop.close()
                elif hasattr(engine_instance, 'check_availability'): engine_instance.check_availability()
                voices = engine_instance.get_available_voices()
                default_voice = voices[0] if voices else ""
            except Exception as e:
                self.log(f"テストエンジン {engine_choice} の音声リスト取得エラー: {e}")
                voices = ["エラー"]; default_voice = "エラー"
        else: voices = ["N/A"]; default_voice = "N/A"
        self.voice_model_test_combo.configure(values=voices if voices else ["選択肢なし"])
        self.test_voice_model_var.set(default_voice if voices else ("選択肢なし" if not voices else ""))

    def run_selected_engine_test(self):
        engine = self.test_engine_var.get()
        model = self.test_voice_model_var.get()
        text = self.test_text_var.get()
        if not text: messagebox.showwarning("入力エラー", "テストテキストを入力してください。", parent=self.root); return
        if not model or model == "エラー" or model == "N/A" or model == "選択肢なし":
            messagebox.showwarning("モデルエラー", "有効な音声モデルが選択されていません。", parent=self.root); return
        self.log(f"🎤 音声テスト開始: エンジン={engine}, モデル={model}, テキスト='{text[:20]}...'")
        api_key_google = self.config.get_system_setting("google_ai_api_key")
        def run_async():
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            try:
                audio_files = loop.run_until_complete(
                    self.voice_manager.synthesize_with_fallback(text, model, 1.0, preferred_engine=engine, api_key=api_key_google)
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
            finally: loop.close()
        threading.Thread(target=run_async, daemon=True).start()

    def run_all_engines_comparison(self):
        text = self.test_text_var.get()
        if not text: messagebox.showwarning("入力エラー", "比較テスト用のテキストを入力してください。", parent=self.root); return
        self.log("🔄 全音声エンジン比較テスト開始...")
        api_key_google = self.config.get_system_setting("google_ai_api_key")
        def run_async():
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            try:
                engines_to_test = ["google_ai_studio_new", "avis_speech", "voicevox", "system_tts"]
                for i, engine_name in enumerate(engines_to_test):
                    engine_instance = self.voice_manager.get_engine_instance(engine_name)
                    if not engine_instance: continue
                    if asyncio.iscoroutinefunction(getattr(engine_instance, 'check_availability', None)):
                        loop.run_until_complete(engine_instance.check_availability())
                    elif hasattr(engine_instance, 'check_availability'): engine_instance.check_availability()
                    voices = engine_instance.get_available_voices()
                    model_to_use = voices[0] if voices else None
                    if not model_to_use: self.log(f"エンジン {engine_name} の利用可能音声なし、スキップ。"); continue
                    self.log(f"🎵 比較中 ({i+1}/{len(engines_to_test)}): {engine_name} (モデル: {model_to_use})")
                    current_test_text = f"エンジン{i+1}番、{engine_name}。{text}"
                    audio_files = loop.run_until_complete(
                        self.voice_manager.synthesize_with_fallback(current_test_text, model_to_use, 1.0, preferred_engine=engine_name, api_key=api_key_google)
                    )
                    if audio_files:
                        loop.run_until_complete(self.audio_player.play_audio_files(audio_files))
                        self.log(f"✅ {engine_name} 比較再生完了。")
                    else: self.log(f"❌ {engine_name} 比較再生失敗。")
                    time.sleep(0.5)
                self.log("🎉 全エンジン比較完了。")
            except Exception as e:
                self.log(f"❌ 全エンジン比較エラー: {e}")
                messagebox.showerror("比較エラー", f"エラー: {e}", parent=self.root)
            finally: loop.close()
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
            finally: loop.close()
        threading.Thread(target=run_async, daemon=True).start()

    def test_google_ai_studio_api(self):
        api_key = self.config.get_system_setting("google_ai_api_key")
        if not api_key: messagebox.showwarning("APIキー未設定", "Google AI Studio APIキーが設定されていません。", parent=self.root); return
        self.log("🧪 Google AI Studio API テスト開始 (音声合成 & 簡単な文章生成)")
        test_text_speech = "Google AI Studioの新しい音声合成APIのテストです。"
        test_prompt_text = "「こんにちは」と返事してください。"
        def run_async():
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            try:
                engine_speech = GoogleAIStudioNewVoiceAPI()
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
            time.sleep(0.5)
            try:
                client = genai.Client(api_key=api_key)
                text_gen_model_name = self.config.get_system_setting("text_generation_model", "gemini-1.5-flash")
                if "local" in text_gen_model_name: self.log("ℹ️ Google AI Studio 文章生成テスト: テキスト生成モデルがローカルLLMのためスキップ。"); return
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
            finally: loop.close()
        threading.Thread(target=run_async, daemon=True).start()

    def test_youtube_api_connection(self):
        api_key = self.config.get_system_setting("youtube_api_key")
        if not api_key: messagebox.showwarning("APIキー未設定", "YouTube APIキーが設定されていません。", parent=self.root); return
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
            else: messagebox.showwarning("YouTube APIテスト警告", "接続成功しましたがデータ形式が不正です。", parent=self.root)
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
            finally: loop.close()
        threading.Thread(target=run_async, daemon=True).start()

    def test_avis_speech_connection(self): self._test_local_engine_connection("Avis Speech Engine", AvisSpeechEngineAPI)
    def test_voicevox_connection(self): self._test_local_engine_connection("VOICEVOX Engine", VOICEVOXEngineAPI)

    def _add_to_debug_chat_display(self, message):
        self.debug_chat_display_text.configure(state="normal")
        self.debug_chat_display_text.insert("end", message + "\n")
        self.debug_chat_display_text.see("end")
        self.debug_chat_display_text.configure(state="disabled")

    def clear_debug_chat_display(self):
        self.debug_chat_display_text.configure(state="normal")
        self.debug_chat_display_text.delete("1.0", "end")
        self.debug_chat_display_text.configure(state="disabled")
        self.debug_chat_history.clear()
        self.log("💬 デバッグチャット表示をクリアしました。")

    def send_debug_message_action(self, event=None):
        user_message = self.debug_chat_input_var.get()
        if not user_message: return
        if not self.current_test_character_id or self.test_char_var.get() == "キャラクターなし":
            self._add_to_debug_chat_display("❌ システム: AI対話テスト用のキャラクターを選択してください。"); return
        self._add_to_debug_chat_display(f"👤 あなた: {user_message}")
        self.debug_chat_input_var.set("")
        threading.Thread(target=self._generate_debug_ai_response, args=(user_message,), daemon=True).start()

    def _generate_debug_ai_response(self, user_message):
        try:
            api_key = self.config.get_system_setting("google_ai_api_key")
            if not api_key: self.root.after(0, self._add_to_debug_chat_display, "❌ AI: Google AI APIキーが未設定です。"); return
            char_data = self.character_manager.get_character(self.current_test_character_id)
            if not char_data: self.root.after(0, self._add_to_debug_chat_display, "❌ AI: キャラクターデータが見つかりません。"); return
            char_name = char_data.get('name', 'AI')
            char_prompt = self.character_manager.get_character_prompt(self.current_test_character_id)
            history_len = self.config.get_system_setting("conversation_history_length", 5)
            current_conversation_history = [f"{'ユーザー' if i%2==0 else char_name}: {entry['user' if i%2==0 else 'ai']}" for i, entry in enumerate(self.debug_chat_history[-history_len:])] # より簡潔に
            history_str = "\n".join(current_conversation_history)
            full_prompt = f"{char_prompt}\n\nこれまでの会話:\n{history_str}\n\nユーザー: {user_message}\n\n{char_name}:"
            client = genai.Client(api_key=api_key)
            text_gen_model_name = self.config.get_system_setting("text_generation_model", "gemini-1.5-flash")
            ai_response_text = "エラー：応答生成に失敗"
            if "local_lm_studio" == text_gen_model_name:
                local_llm_url = self.config.get_system_setting("local_llm_endpoint_url")
                if not local_llm_url: ai_response_text = "ローカルLLMエンドポイントURLが未設定です。"
                else:
                    loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
                    try: ai_response_text = loop.run_until_complete(self._generate_response_local_llm(full_prompt, local_llm_url, char_name))
                    finally: loop.close()
            else:
                response = client.models.generate_content(model=text_gen_model_name, contents=full_prompt, generation_config=genai_types.GenerateContentConfig(temperature=0.8, max_output_tokens=150))
                ai_response_text = response.text.strip() if response.text else "うーん、ちょっとうまく思いつかないや。"
            self.root.after(0, self._add_to_debug_chat_display, f"🤖 {char_name}: {ai_response_text}")
            self.debug_chat_history.append({"user": user_message, "ai": ai_response_text})
            if len(self.debug_chat_history) > 20: self.debug_chat_history.pop(0)
            voice_settings = char_data.get('voice_settings', {})
            preferred_engine = voice_settings.get('engine', self.config.get_system_setting('voice_engine'))
            model = voice_settings.get('model'); speed = voice_settings.get('speed', 1.0)
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            try:
                audio_files = loop.run_until_complete(self.voice_manager.synthesize_with_fallback(ai_response_text, model, speed, preferred_engine=preferred_engine, api_key=api_key))
                if audio_files: loop.run_until_complete(self.audio_player.play_audio_files(audio_files))
            finally: loop.close()
        except genai_types.BlockedPromptException: self.root.after(0, self._add_to_debug_chat_display, f"🤖 {char_name}: その内容についてはお答えできません。")
        except Exception as e:
            self.log(f"❌ AI対話テストエラー: {e}")
            self.root.after(0, self._add_to_debug_chat_display, f"🤖 {char_name}: ごめんなさい、ちょっと調子が悪いみたいです。")

    async def _generate_response_local_llm(self, prompt_text: str, endpoint_url: str, char_name_for_log: str = "LocalLLM") -> str:
        self.log(f"🤖 {char_name_for_log}: ローカルLLM ({endpoint_url}) にリクエスト送信中...")
        payload = {"model": "local-model", "messages": [{"role": "user", "content": prompt_text}], "temperature": 0.7, "max_tokens": 200}
        headers = {"Content-Type": "application/json"}
        try:
            import aiohttp
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
        if not self.current_test_character_id or self.test_char_var.get() == "キャラクターなし":
            self._add_to_debug_chat_display("❌ システム: AI対話テスト用のキャラクターを選択してください。"); return
        messages = ["今日の天気は？", "好きな食べ物は何？", "趣味は何ですか？", "最近あった面白い話をして。", "おすすめの曲を教えて。"]
        self.debug_chat_input_var.set(random.choice(messages))
        self.send_debug_message_action()

def main():
    customtkinter.set_appearance_mode("System")
    customtkinter.set_default_color_theme("blue")
    root = customtkinter.CTk()
    app = DebugWindow(root)
    root.mainloop()

if __name__ == "__main__":
    customtkinter.set_appearance_mode("System")
    customtkinter.set_default_color_theme("blue")
    main()
