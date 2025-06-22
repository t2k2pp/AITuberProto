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

# 設定管理クラス（完全版）
class ConfigManager:
    """
    統一設定管理システム v2.2 - 完全版
    4エンジン対応・全ての設定をJSONファイルで管理
    """
    
    def __init__(self, config_file="aituber_config_v22.json"):
        self.config_file = config_file
        self.config = self.load_config()
    
    def load_config(self):
        """設定ファイルから読み込み"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return self.create_default_config()
        except Exception as e:
            print(f"設定読み込みエラー: {e}")
            return self.create_default_config()
    
    def create_default_config(self):
        """デフォルト設定を作成（v2.2完全版）"""
        return {
            "system_settings": {
                "google_ai_api_key": "",           # 文章生成＋新音声合成
                "youtube_api_key": "",
                "voice_engine": "google_ai_studio_new",  # デフォルトは最新
                "auto_save": True,
                "debug_mode": False,
                "audio_device": "default",
                "cost_mode": "free"
            },
            "characters": {},
            "streaming_settings": {
                "current_character": "",
                "live_id": "",
                "chat_monitor_interval": 5,
                "response_delay": 1.0,
                "auto_response": True
            },
            "ui_settings": {
                "window_size": "1000x900",
                "theme": "default",
                "log_level": "INFO"
            },
            "voice_engine_priority": [
                "google_ai_studio_new",    # 最新・2025年5月追加
                "avis_speech",             # 高品質・無料・ローカル
                "voicevox",                # 定番キャラ・無料・ローカル
                "system_tts"               # フォールバック
            ]
        }
    
    def save_config(self):
        """設定をファイルに保存"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"設定保存エラー: {e}")
            return False
    
    def get_system_setting(self, key, default=None):
        """システム設定を取得"""
        return self.config.get("system_settings", {}).get(key, default)
    
    def set_system_setting(self, key, value):
        """システム設定を更新"""
        if "system_settings" not in self.config:
            self.config["system_settings"] = {}
        self.config["system_settings"][key] = value
        if self.config["system_settings"].get("auto_save", True):
            self.save_config()
    
    def get_character(self, char_id):
        """キャラクター設定を取得"""
        return self.config.get("characters", {}).get(char_id)
    
    def save_character(self, char_id, char_data):
        """キャラクター設定を保存"""
        if "characters" not in self.config:
            self.config["characters"] = {}
        self.config["characters"][char_id] = char_data
        self.save_config()
    
    def delete_character(self, char_id):
        """キャラクターを削除"""
        if char_id in self.config.get("characters", {}):
            del self.config["characters"][char_id]
            self.save_config()
            return True
        return False
    
    def get_all_characters(self):
        """全キャラクターのリストを取得"""
        return self.config.get("characters", {})

    def reset_system_settings(self):
        """システム設定をデフォルトに戻す"""
        default_config = self.create_default_config()
        self.config["system_settings"] = default_config.get("system_settings", {})
        self.save_config()
        print("システム設定がデフォルトにリセットされました。")

    def get_all_system_settings(self):
        """現在のシステム設定全体を返す"""
        return self.config.get("system_settings", {}).copy() # コピーを返して内部辞書を保護

    def set_all_system_settings(self, new_settings_dict):
        """システム設定全体を指定された辞書で更新する"""
        if not isinstance(new_settings_dict, dict):
            print("エラー: set_all_system_settings には辞書を指定してください。")
            return

        # 既存の system_settings を完全に置き換えるか、キーごとに更新するかを選択できます。
        # ここでは、完全に置き換える実装とします。
        # 必要であれば、キーの検証や部分的な更新を行うことも可能です。
        self.config["system_settings"] = new_settings_dict.copy() # 安全のためコピーを保存

        if self.config.get("system_settings", {}).get("auto_save", True): # auto_save設定を尊重
            self.save_config()
        print("システム設定が更新されました。")

# 音声エンジン基底クラス（完全版）
class VoiceEngineBase:
    """音声エンジンの基底クラス - 完全版"""
    
    def get_available_voices(self):
        raise NotImplementedError
    
    async def synthesize_speech(self, text, voice_model, speed=1.0, **kwargs):
        raise NotImplementedError
    
    def get_max_text_length(self):
        raise NotImplementedError
    
    def get_engine_info(self):
        """エンジン情報を取得"""
        return {
            "name": "Base Engine",
            "cost": "Unknown",
            "quality": "Unknown",
            "description": "Base voice engine"
        }

# Google AI Studio 新音声合成API（2025年5月追加・完全版）
class GoogleAIStudioNewVoiceAPI(VoiceEngineBase):
    """
    Google AI Studio 新音声合成API（2025年5月追加・完全版）
    Gemini 2.5 Flash 新音声機能・Multimodal Live API完全対応
    """
    
    def __init__(self):
        self.max_length = 2000 # 一般的なTTSの上限として維持、SDKでは具体的に言及なし
        # Google AI Studio TTS (gemini-2.5-flash-preview-tts) で利用可能な音声名。
        # APIエラーメッセージから取得したサポートされている音声名リスト (2025-06-21時点)
        # 'Voice name Alloy is not supported. Allowed voice names are: achernar, achird, algenib, algieba, alnilam, aoede, autonoe, callirrhoe, charon, despina, enceladus, erinome, fenrir, gacrux, iapetus, kore, laomedeia, leda, orus, puck, pulcherrima, rasalgethi, sadachbia, sadaltager, schedar, sulafat, umbriel, vindemiatrix, zephyr, zubenelgenubi'
        supported_voice_names_from_api = [
            "achernar", "achird", "algenib", "algieba", "alnilam", "aoede", "autonoe",
            "callirrhoe", "charon", "despina", "enceladus", "erinome", "fenrir",
            "gacrux", "iapetus", "kore", "laomedeia", "leda", "orus", "puck",
            "pulcherrima", "rasalgethi", "sadachbia", "sadaltager", "schedar",
            "sulafat", "umbriel", "vindemiatrix", "zephyr", "zubenelgenubi"
        ]

        # voice_models はAPIがサポートする短い名前のリストとする
        self.voice_models = sorted(list(set(supported_voice_names_from_api)))

        # self.api_endpoint = "https://generativelanguage.googleapis.com/v1beta" # SDK利用のため不要
        self.client = None # synthesize_speech でAPIキーと共に初期化
    
    def _initialize_client(self, api_key=None):
        if self.client is None:
            if api_key:
                self.client = genai.Client(api_key=api_key)
            else:
                # 環境変数などから自動で設定されることを期待
                self.client = genai.Client()
        elif api_key: # 既にクライアントがあるが、新しいAPIキーが指定された場合
             self.client = genai.Client(api_key=api_key)


    def get_available_voices(self):
        """
        利用可能な音声モデル名（短い形式、例: "Kore", "Alloy"）のリストを返す。
        これはUIのドロップダウンに表示され、SDK呼び出し時の `voice_name` として使用される。
        """
        return self.voice_models
    
    def get_max_text_length(self):
        return self.max_length
    
    def get_engine_info(self):
        return {
            "name": "Google AI Studio 新音声",
            "cost": "無料枠",
            "quality": "★★★★★",
            "description": "2025年5月新追加・最新技術・リアルタイム対応・感情表現"
        }
    
    async def synthesize_speech(self, text, voice_model="puck", speed=1.0, api_key=None, **kwargs): # 修正: デフォルト引数を短い形式に
        """
        Google AI Studio 新音声合成 (SDK版 v202506)
        使用モデル: gemini-2.5-flash-preview-tts (または gemini-2.5-pro-preview-tts)
        音声指定: `PrebuiltVoiceConfig` の `voice_name` に短い音声名 (例: "Kore", "Alloy") を指定。
        API呼び出し: `client.models.generate_content` を使用。
        ドキュメント: https://ai.google.dev/gemini-api/docs/speech-generation
        """
        try:
            # APIキーの取り扱い:
            # クラスインスタンスのクライアントを初期化/更新
            self._initialize_client(api_key)
            # - 引数 `api_key` が指定されていれば、それを使用して genai.Client を初期化。
            # - 指定されていなければ、事前に `genai.configure(api_key=...)` が呼び出されているか、
            #   環境変数 `GOOGLE_API_KEY` が設定されていることを期待して `genai.Client()` を使用。
            # if api_key: # _initialize_client で処理
            #     client = genai.Client(api_key=api_key)
            # else:
            #     client = genai.Client()



    #response = model.generate_content('Teach me about how an LLM works')


            # `voice_model` には "Kore", "Alloy" のような短い音声名が渡されることを期待。
            # `speed` パラメータは現状のSDKでは直接サポートされていない。
            # プロンプトによるスタイル制御 (例: "Speak slowly: ...") は可能だが、ここでは実装しない。
            print(f"ℹ️ GoogleAIStudioNewVoiceAPI: synthesize_speech - Text: {text[:50]}...")
            print(f"ℹ️ GoogleAIStudioNewVoiceAPI: synthesize_speech - Voice Name for SDK: {voice_model}")

            tts_model_name = "gemini-2.5-flash-preview-tts" # TTS専用モデル

            # 音声合成のための設定オブジェクトを作成
            generation_config = genai.types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=genai.types.SpeechConfig(
                    voice_config=genai.types.VoiceConfig(
                        prebuilt_voice_config=genai.types.PrebuiltVoiceConfig(
                            voice_name=voice_model # 例: "Kore", "Alloy"
                        )
                    )
                ),
            )

            # 音声合成のためのツール設定
            # ドキュメント (https://ai.google.dev/gemini-api/docs/speech-generation#sample_code) を参照
            # `Tool` と `SpeechGenerationConfig` を使用する

            # `GeminiVoiceChatApp` のサンプルコードに基づき、`config` パラメータを使用する方式に変更
            # TTS専用モデル名は tts_model_name ("gemini-2.5-flash-preview-tts") を使用
            # contents は text (合成するテキスト)
            # voice_model はSDKで指定する短い音声名 (例: "Alloy", "Puck")

            # 音声合成のための設定オブジェクトを作成 (genai.types を使用)
            generation_and_speech_config = genai.types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=genai.types.SpeechConfig(
                    voice_config=genai.types.VoiceConfig(
                        prebuilt_voice_config=genai.types.PrebuiltVoiceConfig(
                            voice_name=voice_model # 例: "Alloy", "Puck"
                        )
                    )
                )
            )

            # `client.models.generate_content` を使用 (サンプルコードに合わせる)
            # あるいは、`genai.GenerativeModel(model_name=tts_model_name).generate_content(...)` も考えられるが、
            # サンプルでは client インスタンスの models 経由で呼び出している。
            # aituber_system_proto.py の client は genai.Client() で初期化されている。

            response = await asyncio.to_thread(
                self.client.models.generate_content, # client インスタンスを使用 (GeminiVoiceChatAppと同様)
                model=tts_model_name,                # TTS専用モデル名
                contents=text,                       # 合成するテキスト (サンプルでは f"Say...: {text}" となっているが、ここでは元のtextをそのまま使用)
                config=generation_and_speech_config  # ここで GenerateContentConfig を渡す
            )

            # レスポンスから音声データを抽出 (サンプルコードの構造に合わせる)
            # ドキュメントのレスポンス構造に基づき修正
            if response and response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                # ツール呼び出しの結果は parts の中に function_call ではなく、直接 inline_data として返ってくる場合がある
                # または、ToolConfig で指定した modality (AUDIO) に基づいて parts の中に音声データが含まれる
                audio_part = None
                for part in response.candidates[0].content.parts:
                    if part.inline_data and part.inline_data.mime_type.startswith("audio/"):
                        audio_part = part
                        break

                if audio_part and audio_part.inline_data and audio_part.inline_data.data:
                    audio_data = audio_part.inline_data.data

                    # 音声データを一時ファイルに保存 (waveモジュール使用)
                    # 標準的なPCMフォーマットを想定: 24kHz, 1チャンネル, 16bit
                    # APIが実際に返す形式に合わせて調整が必要な場合がある
                    temp_wav_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                    temp_filename = temp_wav_file.name
                    temp_wav_file.close() # ファイル名を確保するために一度閉じる

                    try:
                        with wave.open(temp_filename, "wb") as wf:
                            wf.setnchannels(1)  # モノラル
                            wf.setsampwidth(2)  # 16ビット (2バイト)
                            wf.setframerate(24000)  # 24kHz サンプリングレート
                            wf.writeframes(audio_data)
                        print(f"✅ Google AI Studio新音声合成成功 (SDK v2, wave_module): Voice: {voice_model}, File: {temp_filename}")
                        return [temp_filename]
                    except Exception as wave_write_error:
                        print(f"❌ Google AI Studio新音声 (SDK v2): WAVファイル書き込みエラー: {wave_write_error}")
                        if os.path.exists(temp_filename):
                            os.unlink(temp_filename) # エラー時はファイルを削除
                        return []
                else:
                    print(f"❌ Google AI Studio新音声 (SDK v2): レスポンスに音声データ (inline_data.data with audio MIME type) が含まれていません。Parts: {response.candidates[0].content.parts}")
                    return []
            else:
                error_message = "APIから期待される形式のレスポンスが得られませんでした。"
                if response and response.prompt_feedback:
                    error_message += f" Prompt Feedback: {response.prompt_feedback}"
                print(f"❌ Google AI Studio新音声 (SDK v2): {error_message} Response: {response}")
                return []

        except Exception as e:
            print(f"❌ Google AI Studio新音声エラー (SDK Main v2): {e}")
            import traceback
            print(f"詳細トレース: {traceback.format_exc()}")
            return []

# Avis Speech Engine API実装（完全版・変更なし）
class AvisSpeechEngineAPI(VoiceEngineBase):
    """
    Avis Speech Engine HTTP API統合（完全版）
    ローカルで動作する高品質日本語音声合成エンジン
    """
    
    def __init__(self):
        self.base_url = "http://127.0.0.1:10101"
        self.max_length = 1000
        self.speakers = []
        self.is_available = False
    
    async def check_availability(self):
        """エンジンの可用性をチェック"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/speakers", timeout=3) as response:
                    if response.status == 200:
                        self.speakers = await response.json()
                        self.is_available = True
                        return True
        except Exception as e:
            print(f"Avis Speech Engine接続エラー: {e}")
            self.is_available = False
            return False
    
    def get_available_voices(self):
        """利用可能な音声一覧を取得"""
        if not self.speakers:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.check_availability())
            except:
                pass
            finally:
                loop.close()
        
        voice_list = []
        for speaker in self.speakers:
            for style in speaker.get('styles', []):
                voice_name = f"{speaker['name']}({style['name']})"
                voice_list.append(voice_name)
        
        return voice_list if voice_list else ["Anneli(ノーマル)"]
    
    def get_max_text_length(self):
        return self.max_length
    
    def get_engine_info(self):
        return {
            "name": "Avis Speech Engine",
            "cost": "完全無料",
            "quality": "★★★★☆",
            "description": "ローカル実行・高品質・VOICEVOX互換API"
        }
    
    def _parse_voice_name(self, voice_name):
        """音声名からスピーカーIDとスタイルIDを取得"""
        try:
            if '(' in voice_name and ')' in voice_name:
                speaker_name = voice_name.split('(')[0]
                style_name = voice_name.split('(')[1].replace(')', '')
            else:
                speaker_name = voice_name
                style_name = None
            
            for speaker in self.speakers:
                if speaker['name'] == speaker_name:
                    for style in speaker.get('styles', []):
                        if style_name is None or style['name'] == style_name:
                            return style['id']
            
            if self.speakers:
                return self.speakers[0]['styles'][0]['id']
            return 888753760
            
        except Exception as e:
            print(f"音声名パースエラー: {e}")
            return 888753760
    
    async def synthesize_speech(self, text, voice_model="Anneli(ノーマル)", speed=1.0, **kwargs):
        """
        Avis Speech Engineを使用した音声合成（完全版）
        """
        try:
            if not await self.check_availability():
                print("❌ Avis Speech Engineが利用できません")
                return []
            
            speaker_id = self._parse_voice_name(voice_model)
            
            async with aiohttp.ClientSession() as session:
                # Step 1: AudioQuery作成
                audio_query_params = {
                    'text': text,
                    'speaker': speaker_id
                }
                
                async with session.post(
                    f"{self.base_url}/audio_query",
                    params=audio_query_params,
                    timeout=10
                ) as response:
                    if response.status != 200:
                        print(f"AudioQuery作成エラー: {response.status}")
                        return []
                    
                    audio_query = await response.json()
                
                # 速度調整
                if 'speedScale' in audio_query:
                    audio_query['speedScale'] = speed
                
                # Step 2: 音声合成
                synthesis_params = {
                    'speaker': speaker_id
                }
                
                async with session.post(
                    f"{self.base_url}/synthesis",
                    params=synthesis_params,
                    json=audio_query,
                    timeout=30
                ) as response:
                    if response.status != 200:
                        print(f"音声合成エラー: {response.status}")
                        return []
                    
                    audio_data = await response.read()
                    
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                    temp_file.write(audio_data)
                    temp_file.close()
                    
                    print(f"✅ Avis Speech Engine音声合成成功: {voice_model}")
                    return [temp_file.name]
            
        except Exception as e:
            print(f"❌ Avis Speech Engine合成エラー: {e}")
            return []

# VOICEVOX Engine API実装（完全版・変更なし）
class VOICEVOXEngineAPI(VoiceEngineBase):
    """
    VOICEVOX Engine HTTP API統合（完全版）
    ローカルで動作する定番音声合成エンジン
    """
    
    def __init__(self):
        self.base_url = "http://127.0.0.1:50021"
        self.max_length = 1000
        self.speakers = []
        self.is_available = False
    
    async def check_availability(self):
        """エンジンの可用性をチェック"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/speakers", timeout=3) as response:
                    if response.status == 200:
                        self.speakers = await response.json()
                        self.is_available = True
                        return True
        except Exception as e:
            print(f"VOICEVOX Engine接続エラー: {e}")
            self.is_available = False
            return False
    
    def get_available_voices(self):
        """利用可能な音声一覧を取得"""
        if not self.speakers:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.check_availability())
            except:
                pass
            finally:
                loop.close()
        
        voice_list = []
        for speaker in self.speakers:
            for style in speaker.get('styles', []):
                voice_name = f"{speaker['name']}({style['name']})"
                voice_list.append(voice_name)
        
        if not voice_list:
            voice_list = [
                "ずんだもん(ノーマル)", "ずんだもん(あまあま)", "ずんだもん(つよつよ)",
                "四国めたん(ノーマル)", "四国めたん(あまあま)", "四国めたん(つよつよ)",
                "春日部つむぎ(ノーマル)", "雨晴はう(ノーマル)"
            ]
        
        return voice_list
    
    def get_max_text_length(self):
        return self.max_length
    
    def get_engine_info(self):
        return {
            "name": "VOICEVOX Engine",
            "cost": "完全無料",
            "quality": "★★★☆☆",
            "description": "定番キャラクター・ずんだもん等・安定動作"
        }
    
    def _parse_voice_name(self, voice_name):
        """音声名からスピーカーIDを取得"""
        try:
            if '(' in voice_name and ')' in voice_name:
                speaker_name = voice_name.split('(')[0]
                style_name = voice_name.split('(')[1].replace(')', '')
            else:
                speaker_name = voice_name
                style_name = "ノーマル"
            
            for speaker in self.speakers:
                if speaker['name'] == speaker_name:
                    for style in speaker.get('styles', []):
                        if style['name'] == style_name:
                            return style['id']
            
            character_mapping = {
                "ずんだもん": {"ノーマル": 3, "あまあま": 1, "つよつよ": 7},
                "四国めたん": {"ノーマル": 2, "あまあま": 0, "つよつよ": 6},
                "春日部つむぎ": {"ノーマル": 8},
                "雨晴はう": {"ノーマル": 10}
            }
            
            if speaker_name in character_mapping:
                styles = character_mapping[speaker_name]
                return styles.get(style_name, list(styles.values())[0])
            
            return 3
            
        except Exception as e:
            print(f"音声名パースエラー: {e}")
            return 3
    
    async def synthesize_speech(self, text, voice_model="ずんだもん(ノーマル)", speed=1.0, **kwargs):
        """
        VOICEVOX Engineを使用した音声合成（完全版）
        """
        try:
            if not await self.check_availability():
                print("❌ VOICEVOX Engineが利用できません")
                return []
            
            speaker_id = self._parse_voice_name(voice_model)
            
            async with aiohttp.ClientSession() as session:
                # Step 1: AudioQuery作成
                audio_query_params = {
                    'text': text,
                    'speaker': speaker_id
                }
                
                async with session.post(
                    f"{self.base_url}/audio_query",
                    params=audio_query_params,
                    timeout=10
                ) as response:
                    if response.status != 200:
                        print(f"VOICEVOX AudioQuery作成エラー: {response.status}")
                        return []
                    
                    audio_query = await response.json()
                
                # 速度調整
                if 'speedScale' in audio_query:
                    audio_query['speedScale'] = speed
                
                # Step 2: 音声合成
                synthesis_params = {
                    'speaker': speaker_id
                }
                
                async with session.post(
                    f"{self.base_url}/synthesis",
                    params=synthesis_params,
                    json=audio_query,
                    timeout=30
                ) as response:
                    if response.status != 200:
                        print(f"VOICEVOX 音声合成エラー: {response.status}")
                        return []
                    
                    audio_data = await response.read()
                    
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                    temp_file.write(audio_data)
                    temp_file.close()
                    
                    print(f"✅ VOICEVOX Engine音声合成成功: {voice_model}")
                    return [temp_file.name]
            
        except Exception as e:
            print(f"❌ VOICEVOX Engine合成エラー: {e}")
            return []

# システムTTS API（完全版・変更なし）
class SystemTTSAPI(VoiceEngineBase):
    """
    システム標準TTS API v2.2（完全版）
    Windows/macOS/Linux の標準音声合成機能を使用
    完全無料でオフライン動作
    """
    
    def __init__(self):
        self.max_length = 500
        self.system = platform.system()
        
        if self.system == "Windows":
            self.voice_models = [
                "Microsoft Ayumi Desktop",     # 日本語女性（標準）
                "Microsoft Ichiro Desktop",    # 日本語男性
                "Microsoft Haruka Desktop",    # 日本語女性（若い）
                "Microsoft Zira Desktop",      # 英語女性
                "Microsoft David Desktop",     # 英語男性
                "Microsoft Hazel Desktop"      # 英語女性（イギリス）
            ]
            self.default_voice = "Microsoft Ayumi Desktop"
        elif self.system == "Darwin":  # macOS
            self.voice_models = [
                "Kyoko",        # 日本語女性
                "Otoya",        # 日本語男性
                "Ava",          # 英語女性
                "Samantha",     # 英語女性
                "Alex",         # 英語男性
                "Victoria"      # 英語女性
            ]
            self.default_voice = "Kyoko"
        else:  # Linux
            self.voice_models = [
                "japanese",     # 日本語
                "english",      # 英語
                "default"       # デフォルト
            ]
            self.default_voice = "japanese"
    
    def get_available_voices(self):
        return self.voice_models
    
    def get_max_text_length(self):
        return self.max_length
    
    def get_engine_info(self):
        return {
            "name": "システムTTS",
            "cost": "完全無料",
            "quality": "★★☆☆☆",
            "description": "OS標準・オフライン・インストール不要・安定動作"
        }
    
    async def synthesize_speech(self, text, voice_model=None, speed=1.0, **kwargs):
        """
        システム標準TTSを使用した音声合成 v2.2（完全版）
        """
        try:
            if voice_model is None:
                voice_model = self.default_voice
            
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            temp_file.close()
            
            if self.system == "Windows":
                success = await self._windows_tts(text, temp_file.name, voice_model, speed)
            elif self.system == "Darwin":  # macOS
                success = await self._macos_tts(text, temp_file.name, voice_model, speed)
            else:  # Linux
                success = await self._linux_tts(text, temp_file.name, voice_model, speed)
            
            if success and os.path.exists(temp_file.name) and os.path.getsize(temp_file.name) > 0:
                return [temp_file.name]
            else:
                print(f"システムTTS: 音声ファイル生成失敗")
                try:
                    os.unlink(temp_file.name)
                except:
                    pass
                return []
            
        except Exception as e:
            print(f"システムTTS合成エラー: {e}")
            return []
    
    async def _windows_tts(self, text, output_file, voice_model, speed):
        """Windows用TTS実装 v2.2（完全版）"""
        try:
            voice_name = voice_model
            if "Desktop" not in voice_name and "Microsoft" not in voice_name:
                voice_mapping = {
                    "Ayumi": "Microsoft Ayumi Desktop",
                    "Ichiro": "Microsoft Ichiro Desktop",
                    "Haruka": "Microsoft Haruka Desktop",
                    "Zira": "Microsoft Zira Desktop"
                }
                voice_name = voice_mapping.get(voice_model, "Microsoft Ayumi Desktop")
            
            rate_value = max(-10, min(10, int((speed - 1.0) * 5)))
            
            ps_script = f'''
Add-Type -AssemblyName System.speech
$speak = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {{
    $voices = $speak.GetInstalledVoices()
    $targetVoice = $voices | Where-Object {{ $_.VoiceInfo.Name -eq "{voice_name}" }}
    if ($targetVoice) {{
        $speak.SelectVoice("{voice_name}")
    }} else {{
        Write-Host "Voice not found: {voice_name}, using default"
    }}
    $speak.Rate = {rate_value}
    $speak.SetOutputToWaveFile("{output_file}")
    $speak.Speak(@"
{text}
"@)
    $speak.Dispose()
    Write-Host "TTS completed successfully"
}} catch {{
    Write-Host "Error: $_"
    $speak.Dispose()
    exit 1
}}
'''
            
            process = await asyncio.create_subprocess_exec(
                "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            stdout_decoded = stdout.decode('utf-8', errors='ignore').strip()
            stderr_decoded = stderr.decode('utf-8', errors='ignore').strip()

            if stdout_decoded:
                print(f"SystemTTSAPI._windows_tts PowerShell STDOUT: {stdout_decoded}")
            if stderr_decoded:
                print(f"SystemTTSAPI._windows_tts PowerShell STDERR: {stderr_decoded}")

            if process.returncode == 0 and "Error:" not in stderr_decoded and "エラー:" not in stderr_decoded:
                if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                    print(f"✅ SystemTTSAPI._windows_tts: 音声ファイル生成成功 {output_file}")
                    return True
                else:
                    print(f"❌ SystemTTSAPI._windows_tts: PowerShellは成功しましたが、音声ファイルが空または存在しません: {output_file}")
                    return False
            else:
                print(f"❌ SystemTTSAPI._windows_tts: PowerShell TTS エラー (returncode={process.returncode}): {stderr_decoded}")
                return False
            
        except Exception as e:
            print(f"❌ Windows TTS実行エラー: {e}")
            return False
    
    async def _macos_tts(self, text, output_file, voice_model, speed):
        """macOS用TTS実装 v2.2（完全版）"""
        try:
            voice_name = voice_model
            if voice_name not in self.voice_models:
                voice_name = "Kyoko"
            
            rate_value = max(100, min(500, int(200 * speed)))
            
            process = await asyncio.create_subprocess_exec(
                "say", "-v", voice_name, "-r", str(rate_value), 
                "-o", output_file, "--data-format=LEI16@22050", text,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return True
            else:
                print(f"macOS TTS エラー: {stderr.decode()}")
                return False
            
        except Exception as e:
            print(f"macOS TTS実行エラー: {e}")
            return False
    
    async def _linux_tts(self, text, output_file, voice_model, speed):
        """Linux用TTS実装 v2.2（完全版）"""
        try:
            speed_value = max(80, min(300, int(160 * speed)))
            
            # espeak-ngを最初に試行
            try:
                if "japanese" in voice_model.lower():
                    voice_name = "ja"
                else:
                    voice_name = "en"
                
                process = await asyncio.create_subprocess_exec(
                    "espeak-ng", "-v", voice_name, "-s", str(speed_value),
                    "-w", output_file, text,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    return True
            except FileNotFoundError:
                pass
            
            # フォールバック: espeak
            try:
                process = await asyncio.create_subprocess_exec(
                    "espeak", "-s", str(speed_value),
                    "-w", output_file, text,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    return True
            except FileNotFoundError:
                pass
            
            print("Linux TTS: 利用可能なTTSエンジンが見つかりません")
            return False
            
        except Exception as e:
            print(f"Linux TTS実行エラー: {e}")
            return False

# 音声再生クラス v2.2（完全版・変更なし）
class AudioPlayer:
    """
    クロスプラットフォーム音声再生 v2.2（完全版）
    VSeeFace/VTube Studioのリップシンク対応
    """
    
    def __init__(self):
        self.current_process = None
        self.system = platform.system()
    
    async def play_audio_files(self, audio_files, delay_between=0.2):
        """複数音声ファイルを順次再生（完全版）"""
        try:
            for i, audio_file in enumerate(audio_files):
                if os.path.exists(audio_file):
                    print(f"🎵 音声再生 {i+1}/{len(audio_files)}: {os.path.basename(audio_file)}")
                    await self.play_audio_file(audio_file)
                    
                    if delay_between > 0 and i < len(audio_files) - 1:
                        await asyncio.sleep(delay_between)
                    
                    # 再生後にファイルを削除
                    try:
                        await asyncio.sleep(0.1)
                        os.unlink(audio_file)
                    except Exception as delete_error:
                        print(f"ファイル削除エラー: {delete_error}")
            
        except Exception as e:
            print(f"音声再生エラー: {e}")
    
    async def play_audio_file(self, audio_file):
        """単一音声ファイルを再生（完全版）"""
        try:
            if self.system == "Windows":
                await self._play_windows(audio_file)
            elif self.system == "Darwin":  # macOS
                await self._play_macos(audio_file)
            else:  # Linux
                await self._play_linux(audio_file)
                
        except Exception as e:
            print(f"音声ファイル再生エラー: {e}")
    
    async def _play_windows(self, audio_file):
        """Windows用音声再生（完全版）"""
        try:
            ps_script = f'''
Add-Type -AssemblyName presentationCore
$mediaPlayer = New-Object system.windows.media.mediaplayer
$mediaPlayer.open("{audio_file}")
$mediaPlayer.Play()
# Wait for media to open and duration to be available
$loaded = $False
for ($i = 0; $i -lt 50; $i++) {{ # Max 5 seconds wait
    if ($mediaPlayer.NaturalDuration.HasTimeSpan) {{
        $loaded = $True
        break
    }}
    Start-Sleep -Milliseconds 100
}}
if ($loaded -and $mediaPlayer.NaturalDuration.TimeSpan.TotalSeconds -gt 0) {{
    Write-Host "Media loaded. Duration: $($mediaPlayer.NaturalDuration.TimeSpan.TotalSeconds)s"
    while($mediaPlayer.Position -lt $mediaPlayer.NaturalDuration.TimeSpan) {{
        Start-Sleep -Milliseconds 100
    }}
    Write-Host "Playback finished."
}} else {{
    Write-Host "Error: MediaPlayer did not load media correctly or media has zero duration."
    # Fallback for very short sounds or if duration is not correctly reported, just wait a bit
    Start-Sleep -Seconds 2 # Wait 2 seconds as a fallback
}}
$mediaPlayer.Stop()
$mediaPlayer.Close()
'''
            
            process = await asyncio.create_subprocess_exec(
                "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            stdout_decoded = stdout.decode('utf-8', errors='ignore').strip()
            stderr_decoded = stderr.decode('utf-8', errors='ignore').strip()

            if stdout_decoded:
                print(f"AudioPlayer._play_windows PowerShell STDOUT: {stdout_decoded}")
            if stderr_decoded:
                print(f"AudioPlayer._play_windows PowerShell STDERR: {stderr_decoded}")

            if process.returncode != 0 or "エラー" in stderr_decoded.lower() or "error" in stderr_decoded.lower():
                print(f"❌ AudioPlayer._play_windows: PowerShell再生エラー (returncode={process.returncode}): {stderr_decoded}")
                print(f"🐍 AudioPlayer: PowerShellでの再生に失敗したため、winsoundにフォールバックします: {audio_file}")
                try:
                    import winsound
                    # winsound.PlaySoundは非同期ではないため、スレッドで実行してブロッキングを防ぐ
                    await asyncio.to_thread(winsound.PlaySound, audio_file, winsound.SND_FILENAME | winsound.SND_ASYNC)
                    print(f"✅ AudioPlayer: winsound.PlaySound ({audio_file}) の呼び出しを試みました (非同期)。")
                except Exception as winsound_e:
                    print(f"❌ AudioPlayer: winsound.PlaySound でもエラーが発生しました: {winsound_e}")
            else:
                print(f"✅ AudioPlayer._play_windows: PowerShellによる音声再生成功: {audio_file}")

        except Exception as e:
            print(f"❌ Windows音声再生エラー (PowerShell呼び出し前): {e}")
            print(f"🐍 AudioPlayer: PowerShell呼び出し前にエラーが発生したため、winsoundにフォールバックします: {audio_file}")
            try:
                import winsound
                await asyncio.to_thread(winsound.PlaySound, audio_file, winsound.SND_FILENAME | winsound.SND_ASYNC)
                print(f"✅ AudioPlayer: winsound.PlaySound ({audio_file}) の呼び出しを試みました (非同期)。")
            except Exception as winsound_e:
                print(f"❌ AudioPlayer: winsound.PlaySound でもエラーが発生しました: {winsound_e}")
    
    async def _play_macos(self, audio_file):
        """macOS用音声再生（完全版）"""
        try:
            process = await asyncio.create_subprocess_exec("afplay", audio_file)
            await process.wait()
        except Exception as e:
            print(f"macOS音声再生エラー: {e}")
    
    async def _play_linux(self, audio_file):
        """Linux用音声再生（完全版）"""
        try:
            players = ["aplay", "paplay", "play", "ffplay"]
            
            for player in players:
                try:
                    if player == "ffplay":
                        process = await asyncio.create_subprocess_exec(
                            player, "-nodisp", "-autoexit", audio_file,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
                    else:
                        process = await asyncio.create_subprocess_exec(
                            player, audio_file,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
                    
                    await process.wait()
                    
                    if process.returncode == 0:
                        return
                    
                except FileNotFoundError:
                    continue
            
            print("Linux: 利用可能な音声プレイヤーが見つかりません")
            
        except Exception as e:
            print(f"Linux音声再生エラー: {e}")

# 音声エンジン管理クラス v2.2（6エンジン完全対応版）
class VoiceEngineManager:
    """
    音声エンジン管理クラス v2.2 - 6エンジン完全統合版
    
    優先順位（2025年5月最新版・修正版）:
    1. Google AI Studio新音声（2025年5月追加・最新技術）
    2. Avis Speech Engine（高品質・完全無料・ローカル）
    3. VOICEVOX Engine（定番キャラ・完全無料・ローカル）
    4. システムTTS（OS標準・フォールバック）
    """
    
    def __init__(self):
        self.engines = {
            "google_ai_studio_new": GoogleAIStudioNewVoiceAPI(),
            "avis_speech": AvisSpeechEngineAPI(),
            "voicevox": VOICEVOXEngineAPI(),
            "system_tts": SystemTTSAPI()
        }
        self.current_engine = "google_ai_studio_new"  # デフォルトは最新
        self.priority = [
            "google_ai_studio_new", "avis_speech", "voicevox",
            "system_tts"
        ]
    
    def set_engine(self, engine_name):
        """使用する音声エンジンを設定"""
        if engine_name in self.engines:
            self.current_engine = engine_name
            return True
        return False
    
    def get_current_engine(self):
        """現在の音声エンジンを取得"""
        return self.engines[self.current_engine]
    
    def get_available_engines(self):
        """利用可能な音声エンジン一覧を取得"""
        return list(self.engines.keys())
    
    def get_engine_info(self, engine_name):
        """指定された音声エンジンの情報を取得"""
        if engine_name in self.engines:
            return self.engines[engine_name].get_engine_info()
        return {}
    
    async def check_engines_availability(self):
        """全エンジンの可用性をチェック（完全版）"""
        availability = {}
        for name, engine in self.engines.items():
            if hasattr(engine, 'check_availability'):
                try:
                    availability[name] = await engine.check_availability()
                except:
                    availability[name] = False
            else:
                availability[name] = True  # Google系・SystemTTSは常に利用可能とみなす
        
        return availability
    
    async def synthesize_with_fallback(self, text, voice_model, speed=1.0, preferred_engine=None, api_key=None):
        """
        フォールバック機能付き音声合成 v2.2（6エンジン完全対応版）
        指定されたエンジンが失敗した場合、自動的に次のエンジンを試行
        """
        engines_to_try = []
        
        if preferred_engine and preferred_engine in self.engines:
            engines_to_try.append(preferred_engine)
        
        # 優先順位に従って追加
        for engine_name in self.priority:
            if engine_name not in engines_to_try:
                engines_to_try.append(engine_name)
        
        for engine_name in engines_to_try:
            try:
                print(f"🔄 音声合成試行: {engine_name}")
                engine = self.engines[engine_name]
                
                # エンジンが利用可能かチェック（該当メソッドがある場合）
                if hasattr(engine, 'check_availability'):
                    if not await engine.check_availability():
                        print(f"⚠️ {engine_name} は利用できません")
                        continue
                
                # API KEYを渡す（完全対応）
                if "google_ai_studio" in engine_name or engine_name == "google_cloud_tts":
                    audio_files = await engine.synthesize_speech(text, voice_model, speed, api_key=api_key)
                else:
                    audio_files = await engine.synthesize_speech(text, voice_model, speed)
                
                if audio_files:
                    print(f"✅ 音声合成成功: {engine_name}")
                    return audio_files
                else:
                    print(f"⚠️ 音声合成失敗: {engine_name}")
                    
            except Exception as e:
                print(f"❌ 音声合成エラー {engine_name}: {e}")
                continue
        
        print("❌ 全ての音声エンジンで合成に失敗しました")
        return []

    def get_all_voices(self):
        """全てのエンジンで利用可能な音声モデルのリストを返す（エンジン名とモデルのペアのリストなど）。"""
        all_voices_map = {}
        for engine_name, engine_instance in self.engines.items():
            try:
                # get_available_voices() がリストを返すことを期待
                available_voices = engine_instance.get_available_voices()
                if available_voices: # 空リストでないことを確認
                    all_voices_map[engine_name] = available_voices
                else:
                    all_voices_map[engine_name] = ["(利用可能な音声なし)"]
            except NotImplementedError:
                all_voices_map[engine_name] = ["(未実装)"]
            except Exception as e:
                print(f"エラー: {engine_name} の音声取得中にエラーが発生しました: {e}")
                all_voices_map[engine_name] = ["(取得エラー)"]
        return all_voices_map

    def add_voice(self, voice_data):
        """
        新しい音声モデルを特定のエンジンに追加する機能。
        主に設定の復元を想定。
        現状のエンジン実装では、音声リストはエンジンクラス内で定義されているため、
        実行時に動的に追加する標準的な方法は提供されていません。
        このメソッドは将来的な拡張用、または特定のエンジンが動的追加をサポートする場合のためのプレースホルダーです。
        """
        # voice_data は {"engine_name": "some_engine", "model_name": "new_voice_model", ...} のような辞書を期待
        engine_name = voice_data.get("engine_name")
        model_name = voice_data.get("model_name")

        if not engine_name or not model_name:
            print("エラー: add_voice には engine_name と model_name が必要です。")
            return

        if engine_name in self.engines:
            # エンジンインスタンスが動的な音声追加をサポートしているか確認
            # 例えば、self.engines[engine_name].add_voice_model(model_name, ...) のようなメソッドがあれば呼び出す
            # 現状の実装ではそのようなメソッドはないため、ログ出力に留める
            print(f"情報: エンジン '{engine_name}' に音声 '{model_name}' を追加するリクエストを受け取りました。")
            print(f"注意: 現在のエンジン実装では、実行時の動的な音声モデル追加は標準サポートされていません。")
            # もし特定のエンジン（例：カスタムTTSエンジンなど）が対応している場合は、ここで分岐処理を行う
            #例:
            # if hasattr(self.engines[engine_name], "add_model"):
            #     self.engines[engine_name].add_model(model_name, voice_data.get("path_to_model_file"))
            #     print(f"'{model_name}' が '{engine_name}' に追加されました。")
            # else:
            #     print(f"エンジン '{engine_name}' は動的な音声追加をサポートしていません。")
        else:
            print(f"エラー: エンジン '{engine_name}' は登録されていません。")

    def get_current_engine_name(self):
        """現在選択されている音声エンジンの名前を返す。"""
        return self.current_engine

# キャラクター管理システム v2.2（6エンジン完全対応版）
class CharacterManager:
    """キャラクター作成・編集・管理システム v2.2（6エンジン完全対応・機能削減なし）"""
    
    def __init__(self, config_manager):
        self.config = config_manager
        self.character_templates = self._load_templates()
    
    def _load_templates(self):
        """キャラクターテンプレート定義 v2.2（6エンジン完全対応）"""
        return {
            "最新AI系": {
                "personality": {
                    "base_tone": "最新技術に詳しく、未来的で知的、革新的な思考",
                    "speech_style": "テクノロジー用語を自然に使い、革新的な視点で話す、時々英語を交える",
                    "character_traits": ["未来志向", "技術愛好家", "革新的思考", "トレンドセッター", "グローバル視点"],
                    "favorite_topics": ["AI技術", "最新ガジェット", "未来予測", "イノベーション", "テクノロジー", "宇宙開発"]
                },
                "response_settings": {
                    "max_length": "2-3文程度",
                    "use_emojis": True,
                    "emotion_level": "知的で興奮気味"
                },
                "voice_settings": {
                    "engine": "google_ai_studio_new",
                    "model": "puck", # Updated model name to a supported one
                    "speed": 1.0
                }
            },
            "元気系": {
                "personality": {
                    "base_tone": "とても明るく元気で親しみやすい、ポジティブエネルギー溢れる",
                    "speech_style": "関西弁メインの親しみやすい口調、感嘆符を多用、リアクション豊か",
                    "character_traits": ["超ポジティブ", "リアクション大きめ", "みんなの応援団", "ノリが良い", "エネルギッシュ"],
                    "favorite_topics": ["スポーツ", "音楽", "ダンス", "お祭り", "ゲーム", "アニメ", "美味しいもの"]
                },
                "response_settings": {
                    "max_length": "1-2文程度",
                    "use_emojis": True,
                    "emotion_level": "超高め"
                },
                "voice_settings": {
                    "engine": "avis_speech",
                    "model": "Anneli(ノーマル)",
                    "speed": 1.1
                }
            },
            "知的系": {
                "personality": {
                    "base_tone": "落ち着いていて知的、親しみやすい先生タイプ、論理的思考",
                    "speech_style": "丁寧語中心、時々専門用語、分かりやすい説明を心がける、教育的",
                    "character_traits": ["好奇心旺盛", "論理的思考", "優しい先生タイプ", "聞き上手", "博学"],
                    "favorite_topics": ["科学", "歴史", "読書", "学習", "技術", "哲学", "研究"]
                },
                "response_settings": {
                    "max_length": "2-3文程度",
                    "use_emojis": False,
                    "emotion_level": "控えめで上品"
                },
                "voice_settings": {
                    "engine": "avis_speech",
                    "model": "Anneli(クール)",
                    "speed": 0.9
                }
            },
            "癒し系": {
                "personality": {
                    "base_tone": "穏やかで癒し系、包容力がある、母性的な優しさ",
                    "speech_style": "ふんわりとした優しい口調、ゆったりとした話し方、共感的",
                    "character_traits": ["包容力がある", "聞き上手", "みんなの癒し", "穏やかな性格", "共感力高い"],
                    "favorite_topics": ["自然", "ガーデニング", "お茶", "瞑想", "読書", "音楽", "手作り"]
                },
                "response_settings": {
                    "max_length": "1-2文程度",
                    "use_emojis": True,
                    "emotion_level": "穏やかで温かい"
                },
                "voice_settings": {
                    "engine": "avis_speech",
                    "model": "Anneli(ささやき)",
                    "speed": 0.8
                }
            },
            "ずんだもん系": {
                "personality": {
                    "base_tone": "元気で親しみやすい、東北弁が特徴的、愛されキャラ",
                    "speech_style": "「〜のだ」「〜なのだ」語尾、親しみやすい口調、東北弁",
                    "character_traits": ["親しみやすい", "元気いっぱい", "東北弁", "みんなの人気者", "天然っぽい"],
                    "favorite_topics": ["ずんだ餅", "東北", "お祭り", "美味しいもの", "みんなとの話", "枝豆"]
                },
                "response_settings": {
                    "max_length": "1-2文程度",
                    "use_emojis": True,
                    "emotion_level": "高めで親しみやすい"
                },
                "voice_settings": {
                    "engine": "voicevox",
                    "model": "ずんだもん(ノーマル)",
                    "speed": 1.0
                }
            },
            "キャラクター系": {
                "personality": {
                    "base_tone": "アニメキャラクターのような個性的で魅力的、エンターテイナー",
                    "speech_style": "特徴的な口調、語尾に特徴、感情豊か、演技がかった表現",
                    "character_traits": ["個性的", "感情表現豊か", "ユニークな視点", "エンターテイナー", "表現力抜群"],
                    "favorite_topics": ["アニメ", "ゲーム", "マンガ", "コスプレ", "声優", "二次創作", "ライブ"]
                },
                "response_settings": {
                    "max_length": "1-2文程度",
                    "use_emojis": True,
                    "emotion_level": "超高めで表現豊か"
                },
                "voice_settings": {
                    "engine": "voicevox",
                    "model": "四国めたん(ノーマル)",
                    "speed": 1.0
                }
            },
            "プロ品質系": {
                "personality": {
                    "base_tone": "プロフェッショナルで上品、洗練された、エレガント",
                    "speech_style": "丁寧で美しい日本語、品格のある話し方、洗練された表現",
                    "character_traits": ["上品", "洗練された", "プロフェッショナル", "知性的", "エレガント"],
                    "favorite_topics": ["文化", "芸術", "ファッション", "グルメ", "旅行", "ライフスタイル", "ビジネス"]
                },
                "response_settings": {
                    "max_length": "2-3文程度",
                    "use_emojis": False,
                    "emotion_level": "上品で控えめ"
                },
                "voice_settings": {
                    "engine": "google_ai_studio_new",
                    "model": "puck", # Or another suitable model from GoogleAIStudioNewVoiceAPI
                    "speed": 1.0
                }
            },
            "多言語対応系": {
                "personality": {
                    "base_tone": "国際的で多様性に富んだ、グローバルな視点、文化理解力",
                    "speech_style": "時々英語を交える、国際的な話題に詳しい、多文化的視点",
                    "character_traits": ["国際的", "多文化理解", "語学堪能", "グローバル思考", "文化架け橋"],
                    "favorite_topics": ["国際情勢", "言語学習", "世界文化", "旅行", "国際交流", "多様性"]
                },
                "response_settings": {
                    "max_length": "2-3文程度",
                    "use_emojis": True,
                    "emotion_level": "普通で国際的"
                },
                "voice_settings": {
                    "engine": "google_ai_studio_new",
                    "model": "puck", # Updated model name to a supported one
                    "speed": 1.0
                }
            }
        }
    
    def create_character(self, name, template_name=None, custom_settings=None):
        """新しいキャラクターを作成 v2.2（完全版）"""
        char_id = str(uuid.uuid4())
        
        if template_name and template_name in self.character_templates:
            char_data = self.character_templates[template_name].copy()
        else:
            char_data = self._create_blank_character()
        
        char_data["name"] = name
        char_data["created_at"] = datetime.now().isoformat()
        char_data["char_id"] = char_id
        char_data["version"] = "2.2"
        
        # カスタム設定を適用
        if custom_settings:
            char_data.update(custom_settings)
        
        # デフォルト音声設定（v2.2・6エンジン対応）
        if "voice_settings" not in char_data:
            char_data["voice_settings"] = {
                "engine": "google_ai_studio_new",  # デフォルトエンジン（最新）
                "model": "puck", # Updated model name to a supported one
                "speed": 1.0,
                "volume": 1.0
            }
        
        self.config.save_character(char_id, char_data)
        return char_id
    
    def _create_blank_character(self):
        """空のキャラクタープレート v2.2（完全版）"""
        return {
            "personality": {
                "base_tone": "親しみやすく自然な、バランスの取れた",
                "speech_style": "丁寧語と親しい口調のバランス、自然な会話",
                "character_traits": ["フレンドリー", "聞き上手", "親しみやすい", "バランス感覚"],
                "favorite_topics": ["雑談", "趣味", "日常", "エンターテイメント"]
            },
            "response_settings": {
                "max_length": "1-2文程度",
                "use_emojis": True,
                "emotion_level": "普通"
            },
            "voice_settings": {
                "engine": "google_ai_studio_new",
                "model": "gemini-2.5-flash-preview-tts-alloy", # Updated model name
                "speed": 1.0,
                "volume": 1.0
            }
        }
    
    def get_character_prompt(self, char_id):
        """キャラクター設定からAI用プロンプトを生成 v2.2（完全版）"""
        char_data = self.config.get_character(char_id)
        if not char_data:
            return ""
        
        personality = char_data.get("personality", {})
        response_settings = char_data.get("response_settings", {})
        voice_settings = char_data.get("voice_settings", {})
        
        prompt = f"""
あなたは「{char_data.get('name', '')}」という名前のAITuberです。

性格と話し方：
- 基本的な口調: {personality.get('base_tone', '')}
- 話し方のスタイル: {personality.get('speech_style', '')}
- キャラクターの特徴: {', '.join(personality.get('character_traits', []))}
- 好きな話題: {', '.join(personality.get('favorite_topics', []))}

返答のルール：
- 文章の長さ: {response_settings.get('max_length', '1-2文程度')}
- 絵文字の使用: {'積極的に使用' if response_settings.get('use_emojis', True) else '控えめに使用'}
- 感情表現: {response_settings.get('emotion_level', '普通')}レベル

技術情報：
- 音声エンジン: {voice_settings.get('engine', 'google_ai_studio_new')}
- 音声モデル: {voice_settings.get('model', 'Alloy')}

視聴者との自然で親しみやすい会話を心がけてください。
YouTubeライブ配信での短時間の応答に適した内容にしてください。
あなたのキャラクター性を活かした魅力的な応答をしてください。
        """
        return prompt.strip()

    def get_all_characters(self):
        """保存されている全てのキャラクターデータを辞書として返す。"""
        return self.config.get_all_characters()

# キャラクター編集ダイアログ（6エンジン完全対応版）
class CharacterEditDialog:
    """キャラクター作成・編集ダイアログ v2.2（6エンジン完全対応・機能削減なし）"""
    
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
                ttk.Radiobutton(template_grid, text=template, 
                               variable=self.template_var, value=template).grid(row=row, column=col, sticky=tk.W, padx=10)
        
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
    
    def on_engine_changed(self, event=None):
        """音声エンジン選択が変更された際の処理。音声モデルのリストを更新する。"""
        self.update_voice_models()
    
    def update_voice_models(self):
        """選択された音声エンジンに応じて音声モデルリストを更新（6エンジン完全対応）"""
        engine = self.voice_engine_var.get()
        
        # エンジンごとに音声モデルを取得
        if engine == "google_ai_studio_new":
            instance = GoogleAIStudioNewVoiceAPI()
            voices = instance.get_available_voices()
            # default_voice はAPIがサポートするリストの最初のものにする
            default_voice = voices[0] if voices else "puck" # フォールバックとして "puck" (APIエラーリストより)
            info_text = "🚀 最新SDK利用・gemini-2.5-flash-preview-ttsモデル・リアルタイム対応・多言語"
        elif engine == "avis_speech":
            voices = ["Anneli(ノーマル)", "Anneli(クール)", "Anneli(ささやき)", "Anneli(元気)", "Anneli(悲しみ)", "Anneli(怒り)"]
            default_voice = "Anneli(ノーマル)"
            info_text = "🎙️ ローカル実行・高品質・VOICEVOX互換API・感情表現対応"
        elif engine == "voicevox":
            voices = [
                "ずんだもん(ノーマル)", "ずんだもん(あまあま)", "ずんだもん(つよつよ)", "ずんだもん(セクシー)",
                "四国めたん(ノーマル)", "四国めたん(あまあま)", "四国めたん(つよつよ)", "四国めたん(セクシー)",
                "春日部つむぎ(ノーマル)", "雨晴はう(ノーマル)", "波音リツ(ノーマル)", "玄野武宏(ノーマル)"
            ]
            default_voice = "ずんだもん(ノーマル)"
            info_text = "🎤 定番キャラクター・ずんだもん等・安定動作・豊富な感情表現"
        else:  # system_tts
            system_tts = SystemTTSAPI()
            voices = system_tts.get_available_voices()
            default_voice = voices[0] if voices else "デフォルト"
            info_text = "💻 OS標準TTS・完全無料・インターネット不要・安定動作"
        
        # 音声モデルリスト更新
        self.voice_combo['values'] = voices
        if not self.is_edit_mode or self.voice_var.get() not in voices:
            self.voice_var.set(default_voice)
        
        # エンジン情報表示
        if hasattr(self, 'engine_info_label'):
            self.engine_info_label.config(text=info_text)
    
    def test_voice(self):
        """音声テスト（6エンジン完全対応）"""
        text = f"こんにちは！私は{self.name_var.get() or 'テスト'}です。6つの音声エンジンに完全対応したシステムでお話しています。"
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
                
                print("🎉 6エンジン比較完了")
                
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

# メインGUIアプリケーション v2.2（6エンジン完全対応版・機能削減なし）
class AITuberMainGUI:
    """
    完全版AITuberシステムGUI v2.2 - 4エンジン完全対応版
    キャラクター管理・配信・デバッグ機能を完全統合（機能削減なし）
    """
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AITuber完全版システム v2.2 - 4エンジン完全対応版（2025年5月最新・機能削減なし）")
        self.root.geometry("1100x950")
        
        # システム初期化
        self.config = ConfigManager()
        self.character_manager = CharacterManager(self.config)
        self.voice_manager = VoiceEngineManager()
        self.audio_player = AudioPlayer()
        
        # 状態管理
        self.is_streaming = False
        self.current_character_id = ""
        self.aituber_task = None
        
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
        self.create_debug_tab()
        self.create_settings_tab()
        self.create_advanced_tab()  # 新規追加：高度な機能
        
        # ステータスバー
        self.create_status_bar()
    
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
                  command=self.refresh_character_list).pack(side=tk.LEFT, padx=5)
        ttk.Button(char_control_frame, text="⚙️ 設定", 
                  command=self.quick_character_settings).pack(side=tk.LEFT, padx=5)
        
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
        
        # テンプレート情報（6エンジン完全対応版）
        template_frame = ttk.LabelFrame(char_frame, text="テンプレート一覧 v2.2（6エンジン完全対応）", padding="10")
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
        """デバッグ・テストタブ（6エンジン完全対応版）"""
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
        ttk.Button(test_buttons, text="🎯 フォールバックテスト", 
                  command=self.test_fallback).pack(side=tk.LEFT, padx=5)
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
        
        ttk.Label(chat_control_frame, text="AIとの会話テスト（文章生成: Google AI Studio + 音声合成: 6エンジン対応）:").pack(side=tk.LEFT)
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
        
        # フォールバック設定
        fallback_frame = ttk.Frame(voice_grid)
        fallback_frame.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=10)
        
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
        
        self.performance_monitoring_var = tk.BooleanVar()
        ttk.Checkbutton(system_grid, text="パフォーマンス監視", 
                       variable=self.performance_monitoring_var).grid(row=0, column=2, sticky=tk.W, padx=20)
        
        # 高度な設定
        self.auto_update_var = tk.BooleanVar()
        ttk.Checkbutton(system_grid, text="自動アップデート", 
                       variable=self.auto_update_var).grid(row=1, column=0, sticky=tk.W)
        
        self.telemetry_var = tk.BooleanVar()
        ttk.Checkbutton(system_grid, text="使用統計の送信", 
                       variable=self.telemetry_var).grid(row=1, column=1, sticky=tk.W, padx=20)
        
        self.experimental_features_var = tk.BooleanVar()
        ttk.Checkbutton(system_grid, text="実験的機能", 
                       variable=self.experimental_features_var).grid(row=1, column=2, sticky=tk.W, padx=20)
        
        # 音声品質設定
        quality_frame = ttk.Frame(system_frame)
        quality_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(quality_frame, text="音声品質:").pack(side=tk.LEFT)
        self.audio_quality_var = tk.StringVar(value="標準")
        quality_combo = ttk.Combobox(quality_frame, textvariable=self.audio_quality_var,
                                    values=["低品質", "標準", "高品質", "最高品質"], state="readonly")
        quality_combo.pack(side=tk.LEFT, padx=10)
        
        ttk.Label(quality_frame, text="音声遅延:").pack(side=tk.LEFT, padx=(20,0))
        self.audio_latency_var = tk.DoubleVar(value=0.2)
        ttk.Scale(quality_frame, from_=0.0, to=1.0, variable=self.audio_latency_var,
                 orient=tk.HORIZONTAL, length=150).pack(side=tk.LEFT, padx=10)
        
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
    
    def quick_character_settings(self):
        """クイックキャラクター設定（完全版）"""
        quick_frame = ttk.Frame(self.notebook)
        self.notebook.add(quick_frame, text="⚡ クイック設定")
        
        # キャラクター選択
        ttk.Label(quick_frame, text="キャラクター選択:").pack(anchor=tk.W, padx=10, pady=5)
        self.character_combo = ttk.Combobox(quick_frame, state="readonly", width=50)
        self.character_combo.pack(padx=10, pady=5)
        
        # キャラクター選択時の処理
        self.character_combo.bind('<<ComboboxSelected>>', self.on_character_selected)
        
        # キャラクター情報表示
        self.char_info_label = ttk.Label(quick_frame, text="キャラクター情報: 未選択", wraplength=500)
        self.char_info_label.pack(padx=10, pady=5)
        
        # キャラクター操作ボタン
        button_frame = ttk.Frame(quick_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(button_frame, text="📝 設定変更", command=self.open_character_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="🎤 音声テスト", command=self.test_character_voice).pack(side=tk.LEFT, padx=5)


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
        
        # システム音声エンジン変更時の情報表示を初期化
        self.on_system_engine_changed()
        
        self.auto_save_var.set(self.config.get_system_setting("auto_save", True))
        self.debug_mode_var.set(self.config.get_system_setting("debug_mode", False))
        
        # キャラクター一覧更新
        self.refresh_character_list()
        
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
            self.config.set_system_setting("auto_save", self.auto_save_var.get())
            self.config.set_system_setting("debug_mode", self.debug_mode_var.get())
            
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
                data.get('voice_settings', {}).get('engine', 'avis_speech')
            ))
        
        self.log(f"📝 キャラクターリストを更新（{len(characters)}件）")
    
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
        elif voice_engine == 'google_cloud_tts' or 'Wavenet' in voice_model:
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
                    if "google_ai_studio" in engine_name: # google_ai_studio_new と google_ai_studio_legacy
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
        threading.Thread(target=self._run_fallback_test, args=(text,), daemon=True).start()
    
    def _run_fallback_test(self, text):
        """フォールバック機能テストの実行"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 故意に存在しないエンジンから開始してフォールバックをテスト
            audio_files = loop.run_until_complete(
                self.voice_manager.synthesize_with_fallback(
                    text, "default", 1.0, preferred_engine="nonexistent_engine", api_key=self.config.get_system_setting("google_ai_api_key")
                )
            )
            
            if audio_files:
                loop.run_until_complete(
                    self.audio_player.play_audio_files(audio_files)
                )
                self.log("✅ フォールバック機能が正常に動作しました")
            else:
                self.log("❌ フォールバック機能が失敗しました")
            
            loop.close()
            
        except Exception as e:
            self.log(f"❌ フォールバックテストエラー: {e}")
    
    def check_engines_status(self):
        """エンジン状態確認"""
        self.log("📊 音声エンジン状態確認開始...")
        threading.Thread(target=self._check_engines_status, daemon=True).start()
    
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
            
            # AI応答生成（文章生成のみ）
            full_prompt = f"{char_prompt}\n\nユーザー: {message}\n\n自然で親しみやすい返答をしてください。"
            
            # response = model.generate_content(full_prompt) # 旧方式
            text_response = client.models.generate_content(
                model="gemini-1.5-flash", # テキスト生成に適したモデル (gemini-2.5-flashでも可)
                contents=full_prompt,
                config=genai.types.GenerateContentConfig( # 引数名を config に修正
                    temperature=0.9,
                    max_output_tokens=150
                )
            )
            ai_response = text_response.text.strip()
            
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
            if "google_ai_studio" in voice_engine: # google_ai_studio_new または google_ai_studio_legacy
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
            
        except Exception as e:
            error_msg = f"❌ エラー: {str(e)}"
            self.root.after(0, lambda: self.chat_display.insert(tk.END, f"{error_msg}\n"))
            self.root.after(0, lambda: self.chat_display.see(tk.END))
            self.log(f"❌ テスト応答生成エラー: {e}")
    
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
        
        if self.log_text:
            self.root.after(0, lambda: self.log_text.insert(tk.END, log_message))
            self.root.after(0, lambda: self.log_text.see(tk.END))
        
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
                elif engine_name == "google_cloud_tts":
                    kwargs['api_key'] = api_key_google_cloud

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
                elif engine_name == "google_cloud_tts":
                    kwargs['api_key'] = api_key_google_cloud

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
    
    def run(self):
        """アプリケーションのメインループを開始"""
        self.log("🚀 AITuberシステム v2.1 - 修正版・完全動作版を起動しました")
        self.root.mainloop()
        self.log("🛑 アプリケーションを終了しました")



# AITuberストリーミングシステム v2.1（修正版）
class AITuberStreamingSystem:
    """YouTubeライブ配信用AITuberシステム v2.1 - 修正版"""
    
    def __init__(self, config, character_id, character_manager, voice_manager, audio_player, log_callback):
        self.config = config
        self.character_id = character_id
        self.character_manager = character_manager
        self.voice_manager = voice_manager  # 更新された音声管理システム
        self.audio_player = audio_player
        self.log = log_callback
        
        # Google AI Studio設定（文章生成専用）
        api_key = self.config.get_system_setting("google_ai_api_key")
        # genai.configure(api_key=api_key) # コメントアウトのまま
        # self.model = genai.GenerativeModel('gemini-2.5-flash') # 旧方式
        self.client = genai.Client(api_key=api_key) # Client を初期化してインスタンス変数に格納
        
        # YouTube API設定
        self.youtube_api_key = self.config.get_system_setting("youtube_api_key")
        self.youtube_base_url = "https://www.googleapis.com/youtube/v3"
        
        # 状態管理
        self.chat_id = None
        self.previous_comment = ""
        self.viewer_memory = {}
        self.running = False
    
    async def run_streaming(self, live_id):
        """配信メインループ"""
        try:
            self.log("配信準備中...")
            
            # チャットID取得
            self.chat_id = await self.get_chat_id(live_id)
            if not self.chat_id:
                self.log("❌ チャットIDの取得に失敗しました")
                return
            
            self.log("✅ YouTube配信に接続しました")
            self.running = True
            
            # キャラクター情報取得
            char_data = self.config.get_character(self.character_id)
            char_name = char_data.get('name', 'AIちゃん')
            
            self.log(f"🌟 {char_name}が配信開始しました！")
            
            while self.running:
                try:
                    # コメント取得
                    comments = await self.get_latest_comments()
                    
                    if comments:
                        latest_comment = comments[-1]
                        comment_text = latest_comment['snippet']['displayMessage']
                        author_name = latest_comment['authorDetails']['displayName']
                        
                        # 新しいコメントの場合
                        if comment_text != self.previous_comment:
                            self.log(f"💬 {author_name}: {comment_text}")
                            
                            # AI応答生成（文章生成のみ）
                            response = await self.generate_response(comment_text, author_name)
                            
                            if response:
                                self.log(f"🤖 {char_name}: {response}")
                                
                                # 音声合成・再生
                                await self.synthesize_and_play(response)
                            
                            self.previous_comment = comment_text
                    
                    # 監視間隔
                    await asyncio.sleep(5)
                    
                except Exception as e:
                    self.log(f"⚠️ エラー: {e}")
                    await asyncio.sleep(10)
            
        except Exception as e:
            self.log(f"❌ 配信エラー: {e}")
        finally:
            self.log("配信を終了しました")
    
    async def get_chat_id(self, live_id):
        """YouTubeライブのチャットID取得"""
        try:
            url = f"{self.youtube_base_url}/videos"
            params = {
                'part': 'liveStreamingDetails',
                'id': live_id,
                'key': self.youtube_api_key
            }
            
            response = await asyncio.to_thread(requests.get, url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if 'items' in data and data['items']:
                live_details = data['items'][0].get('liveStreamingDetails', {})
                return live_details.get('activeLiveChatId')
            
            return None
            
        except Exception as e:
            self.log(f"チャットID取得エラー: {e}")
            return None
    
    async def get_latest_comments(self, max_results=50):
        """最新コメント取得"""
        if not self.chat_id:
            return []
        
        try:
            url = f"{self.youtube_base_url}/liveChat/messages"
            params = {
                'liveChatId': self.chat_id,
                'part': 'snippet,authorDetails',
                'maxResults': max_results,
                'key': self.youtube_api_key
            }
            
            response = await asyncio.to_thread(requests.get, url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return data.get('items', [])
            
        except Exception as e:
            self.log(f"コメント取得エラー: {e}")
            return []
    
    async def generate_response(self, comment_text, author_name):
        """AI応答生成（文章生成専用）"""
        try:
            # キャラクタープロンプト取得
            char_prompt = self.character_manager.get_character_prompt(self.character_id)
            
            # プロンプト構築
            full_prompt = f"{char_prompt}\n\n視聴者 {author_name}: {comment_text}\n\n親しみやすく自然な返答をしてください。"
            
            # AI応答生成（文章生成のみ）
            # response = await asyncio.to_thread( # 旧方式
            #     self.model.generate_content,
            #     full_prompt,
            #     generation_config={
            #         'temperature': 0.9,
            #         'max_output_tokens': 100,
            #         'top_p': 0.8
            #     }
            # )
            text_response = await asyncio.to_thread(
                self.client.models.generate_content, # client を使用
                model="gemini-1.5-flash",  # テキスト生成に適したモデル
                contents=full_prompt,
                config=genai.types.GenerateContentConfig( # 引数名を config に修正
                    temperature=0.9,
                    max_output_tokens=100, # ストリーミングなので短めに
                    top_p=0.8
                )
            )
            
            return text_response.text.strip()
            
        except Exception as e:
            self.log(f"応答生成エラー: {e}")
            return "ちょっと聞こえへんかったわ〜😅"
    
    async def synthesize_and_play(self, text):
        """音声合成・再生 v2.1（修正版）"""
        try:
            char_data = self.config.get_character(self.character_id)
            voice_settings = char_data.get('voice_settings', {})
            voice_engine = voice_settings.get('engine', 'avis_speech')
            voice_model = voice_settings.get('model', 'Anneli(ノーマル)')
            speed = voice_settings.get('speed', 1.0)
            
            # API KEY取得（音声合成用）
            google_ai_api_key = self.config.get_system_setting("google_ai_api_key")
            
            # フォールバック機能付き音声合成
            audio_files = await self.voice_manager.synthesize_with_fallback(
                text, voice_model, speed, preferred_engine=voice_engine, api_key=google_ai_api_key
            )
            
            if audio_files:
                # 音声再生
                await self.audio_player.play_audio_files(audio_files)
            
        except Exception as e:
            self.log(f"❌ 音声処理エラー: {e}")
    
    def stop(self):
        """配信停止"""
        self.running = False

def main():
    """アプリケーションのエントリーポイント"""
    try:
        app = AITuberMainGUI()
        app.run()
    except Exception as e:
        print(f"❌ アプリケーション起動エラー: {e}")
        messagebox.showerror("起動エラー", f"アプリケーションの起動に失敗しました:\n{e}")

if __name__ == "__main__":
    main()