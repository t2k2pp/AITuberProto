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
from audio_manager import VoiceEngineManager, AudioPlayer
from communication_logger import CommunicationLogger # 追加

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
# import json # JSONモジュールをインポート (macOSデバイス取得で使用) # 重複インポートなのでコメントアウト
import csv
import traceback # エラー追跡用に追加



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
        self.communication_logger = CommunicationLogger() # 追加

        # Google AI Studio設定（文章生成専用）
        api_key = self.config.get_system_setting("google_ai_api_key")

        if api_key:
            try:
                self.client = genai.Client(api_key=api_key) # Client を初期化
            except Exception as e:
                self.client = None
                self.log(f"警告: Google AI Clientの初期化に失敗しました。APIキーが正しいか確認してください。エラー: {e}")
        else:
            self.client = None
            self.log("警告: Google AI APIキーが設定されていません。Google AI関連機能が動作しない可能性があります。")

        # YouTube API設定
        self.youtube_api_key = self.config.get_system_setting("youtube_api_key")
        self.youtube_base_url = "https://www.googleapis.com/youtube/v3"

        # 状態管理
        self.chat_id = None
        self.previous_comment = ""
        self.viewer_memory = {}
        self.running = False
        self.chat_history = [] # 会話履歴を保存するリスト

    async def _generate_response_local_llm_streaming(self, prompt_text: str, endpoint_url: str, char_name_for_log: str = "LocalLLMStream") -> str:
        """ローカルLLM（LM Studio想定）から応答を生成する非同期メソッド (ストリーミングシステム用)"""
        self.log(f"🤖 {char_name_for_log}: ローカルLLM ({endpoint_url}) にリクエスト送信中...")
        # リクエストとレスポンスのロギングは呼び出し元の generate_response で行う

        payload = {
            "model": "local-model",
            "messages": [{"role": "user", "content": prompt_text}],
            "temperature": 0.7,
            "max_tokens": 100
        }
        headers = {"Content-Type": "application/json"}
        generated_text = f"ローカルLLM ({endpoint_url}) 呼び出しエラー。" # デフォルトエラー

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(endpoint_url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=60)) as response:
                    response_text_for_error = await response.text()
                    response.raise_for_status()
                    response_data = json.loads(response_text_for_error)

                    if response_data.get("choices") and isinstance(response_data["choices"], list) and len(response_data["choices"]) > 0:
                        message = response_data["choices"][0].get("message")
                        if message and isinstance(message, dict) and "content" in message:
                            generated_text = message["content"].strip()
                            self.log(f"🤖 {char_name_for_log}: ローカルLLMからの応答取得成功。")
                            return generated_text

                    self.log(f"❌ {char_name_for_log}: ローカルLLM応答形式エラー。Response: {response_data}")
                    generated_text = "ローカルLLM応答形式エラーです。"
        except aiohttp.ClientConnectorError as e:
            self.log(f"❌ {char_name_for_log}: ローカルLLM接続エラー ({endpoint_url}): {e}")
            generated_text = f"ローカルLLM ({endpoint_url}) に接続できませんでした。"
        except aiohttp.ClientResponseError as e:
            self.log(f"❌ {char_name_for_log}: ローカルLLM APIエラー ({endpoint_url}) - Status: {e.status}, Message: {e.message}, Response: {response_text_for_error}")
            generated_text = f"ローカルLLM APIエラー (ステータス: {e.status})。"
        except asyncio.TimeoutError:
            self.log(f"❌ {char_name_for_log}: ローカルLLM応答タイムアウト ({endpoint_url})。")
            generated_text = "ローカルLLM応答タイムアウトしました。"
        except json.JSONDecodeError as e_json:
            self.log(f"❌ {char_name_for_log}: ローカルLLM応答のJSONデコードエラー ({endpoint_url}): {e_json}. Response Text: {response_text_for_error}")
            generated_text = "ローカルLLM応答をJSON解析できませんでした。"
        except Exception as e_generic:
            self.log(f"❌ {char_name_for_log}: ローカルLLM呼び出し中に予期せぬエラー ({endpoint_url}): {e_generic}\n{traceback.format_exc()}")
            # generated_text は既にデフォルトエラーメッセージに設定済み
        return generated_text

    async def run_streaming(self, live_id):
        """配信メインループ"""
        try:
            self.log("配信準備中...")
            self.chat_id = await self.get_chat_id(live_id)
            if not self.chat_id:
                self.log("❌ チャットIDの取得に失敗しました。配信を開始できません。")
                return

            self.log("✅ YouTube配信に接続しました")
            self.running = True
            char_data = self.config.get_character(self.character_id)
            char_name = char_data.get('name', 'AIちゃん')
            self.log(f"🌟 {char_name}が配信開始しました！")

            while self.running:
                try:
                    comments = await self.get_latest_comments()
                    if comments:
                        latest_comment = comments[-1]
                        comment_text = latest_comment['snippet']['displayMessage']
                        author_name = latest_comment['authorDetails']['displayName']

                        if comment_text != self.previous_comment:
                            self.log(f"💬 {author_name}: {comment_text}")
                            response_text = await self.generate_response(comment_text, author_name)

                            if response_text:
                                self.log(f"🤖 {char_name}: {response_text}")
                                await self.synthesize_and_play(response_text)
                                history_length = self.config.get_system_setting("conversation_history_length", 0)
                                if history_length > 0:
                                    self.chat_history.append({"user": author_name, "comment": comment_text, "response": response_text})
                                    if len(self.chat_history) > history_length:
                                        self.chat_history.pop(0)
                            self.previous_comment = comment_text
                    await asyncio.sleep(self.config.get_system_setting("chat_monitor_interval", 5))
                except Exception as loop_e: # ループ内のエラー
                    self.log(f"⚠️ 配信ループ中にエラー: {loop_e}\n{traceback.format_exc()}")
                    await asyncio.sleep(10) # 少し待って再試行
        except Exception as main_e: # メイン処理のエラー
            self.log(f"❌ 配信処理全体でエラー: {main_e}\n{traceback.format_exc()}")
        finally:
            self.log("配信を終了しました")

    async def get_chat_id(self, live_id):
        if not self.youtube_api_key:
            self.log("❌ YouTube APIキーが設定されていません。チャットIDを取得できません。")
            return None
        try:
            url = f"{self.youtube_base_url}/videos"
            params = {'part': 'liveStreamingDetails', 'id': live_id, 'key': self.youtube_api_key}
            response = await asyncio.to_thread(requests.get, url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data.get('items'):
                return data['items'][0].get('liveStreamingDetails', {}).get('activeLiveChatId')
            return None
        except Exception as e:
            self.log(f"チャットID取得エラー: {e}")
            return None

    async def get_latest_comments(self, max_results=50):
        if not self.chat_id: return []
        if not self.youtube_api_key:
            self.log("❌ YouTube APIキーが設定されていません。コメントを取得できません。")
            return []
        try:
            url = f"{self.youtube_base_url}/liveChat/messages"
            params = {'liveChatId': self.chat_id, 'part': 'snippet,authorDetails', 'maxResults': max_results, 'key': self.youtube_api_key}
            response = await asyncio.to_thread(requests.get, url, params=params, timeout=10)
            response.raise_for_status()
            return response.json().get('items', [])
        except Exception as e:
            self.log(f"コメント取得エラー: {e}")
            return []

    async def generate_response(self, comment_text, author_name):
        char_name = self.config.get_character(self.character_id).get('name', 'AIちゃん')
        selected_model = self.config.get_system_setting("text_generation_model", "gemini-1.5-flash")
        ai_response_text = "ごめんなさい、ちょっと考え中です。" # デフォルト

        try:
            char_prompt = self.character_manager.get_character_prompt(self.character_id)
            history_len = self.config.get_system_setting("conversation_history_length", 0)
            history_parts = [f"視聴者 {h['user']}: {h['comment']}\nあなた: {h['response']}" for h in self.chat_history[-history_len:]] if history_len > 0 else []
            full_prompt = f"{char_prompt}\n\n{''.join(history_parts)}\n\n視聴者 {author_name}: {comment_text}\n\n親しみやすく自然な返答をしてください。"

            self.communication_logger.add_log("sent", "text_generation", f"[Streaming to {char_name} (Model: {selected_model})]\n{full_prompt}")

            if selected_model == "local_lm_studio":
                local_llm_url = self.config.get_system_setting("local_llm_endpoint_url", "")
                if not local_llm_url:
                    ai_response_text = "ローカルLLMのエンドポイントURLが未設定です。"
                    self.log(f"❌ LocalLLM (Streaming - {char_name}): エンドポイントURL未設定。")
                else:
                    ai_response_text = await self._generate_response_local_llm_streaming(full_prompt, local_llm_url, char_name)
            else:
                if not self.client:
                    ai_response_text = "Google AIサービスに接続できません (クライアント未初期化)。"
                    self.log("❌ Google AI Clientが初期化されていません。")
                else:
                    gemini_response = await asyncio.to_thread(
                        self.client.models.generate_content,
                        model=selected_model, contents=full_prompt,
                        generation_config=genai.types.GenerateContentConfig(temperature=0.9, max_output_tokens=100, top_p=0.8)
                    )
                    ai_response_text = gemini_response.text.strip() if gemini_response.text else "うーん、うまく言葉にできませんでした。"

            self.communication_logger.add_log("received", "text_generation", f"[Streaming from {char_name} (Model: {selected_model})]\n{ai_response_text}")
            return ai_response_text

        except genai.types.BlockedPromptException as bpe:
            ai_response_text = "その内容についてはお答えできません。"
            self.log(f"❌ 応答生成エラー (Blocked): {bpe}")
            self.communication_logger.add_log("received", "text_generation", f"[Streaming from {char_name} (Model: {selected_model}) - Blocked]\n{bpe}")
        except requests.exceptions.HTTPError as http_err:
            ai_response_text = f"APIエラーが発生しました ({http_err.response.status_code})。"
            self.log(f"❌ 応答生成エラー (HTTP): {http_err}")
            self.communication_logger.add_log("received", "text_generation", f"[Streaming from {char_name} (Model: {selected_model}) - HTTP Error {http_err.response.status_code}]\n{http_err}")
        except Exception as e:
            ai_response_text = "予期せぬエラーで応答できませんでした。"
            self.log(f"❌ 応答生成エラー (Generic): {e}\n{traceback.format_exc()}")
            self.communication_logger.add_log("received", "text_generation", f"[Streaming from {char_name} (Model: {selected_model}) - Generic Error]\n{e}")
        return ai_response_text

    async def synthesize_and_play(self, text):
        try:
            char_data = self.config.get_character(self.character_id)
            char_name = char_data.get('name', 'AIちゃん')
            voice_settings = char_data.get('voice_settings', {})
            engine = voice_settings.get('engine', self.config.get_system_setting("voice_engine", "avis_speech")) # デフォルトエンジン設定
            model = voice_settings.get('model') # モデルはエンジンごとに異なるので、ここではNoneかもしれない
            speed = voice_settings.get('speed', 1.0)

            self.communication_logger.add_log("sent", "voice_synthesis", f"[Streaming Voice for {char_name} (Engine: {engine}, Model: {model or 'N/A'})]\n{text}")

            google_api_key = self.config.get_system_setting("google_ai_api_key") if "google_ai_studio" in engine else None

            audio_files = await self.voice_manager.synthesize_with_fallback(
                text, model, speed, preferred_engine=engine, api_key=google_api_key
            )

            if audio_files:
                await self.audio_player.play_audio_files(audio_files)
            else:
                self.log(f"警告: 音声合成に失敗しました ({char_name}, Text: '{text[:30]}...')")
        except Exception as e:
            self.log(f"❌ 音声処理エラー: {e}\n{traceback.format_exc()}")

    def stop(self):
        self.running = False
        self.log("配信停止処理を呼び出しました。")
