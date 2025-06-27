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
        self.chat_history = [] # 会話履歴を保存するリスト
        # self.available_gemini_models の定義とソート処理は AITuberMainGUI にあるべきものなので、ここからは完全に削除。

    async def _generate_response_local_llm_streaming(self, prompt_text: str, endpoint_url: str, char_name_for_log: str = "LocalLLMStream") -> str:
        """ローカルLLM（LM Studio想定）から応答を生成する非同期メソッド (ストリーミングシステム用)"""
        self.log(f"🤖 {char_name_for_log}: ローカルLLM ({endpoint_url}) にリクエスト送信中...")
        
        payload = {
            "model": "local-model", 
            "messages": [{"role": "user", "content": prompt_text}],
            "temperature": 0.7,
            "max_tokens": 100 # ストリーミング用途なので短め
        }
        headers = {"Content-Type": "application/json"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(endpoint_url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=60)) as response: # タイムアウトを60秒に
                    response_text_for_error = await response.text() # エラーログ用に先読み
                    response.raise_for_status()
                    
                    response_data = json.loads(response_text_for_error)
                    
                    if response_data.get("choices") and isinstance(response_data["choices"], list) and len(response_data["choices"]) > 0:
                        message = response_data["choices"][0].get("message")
                        if message and isinstance(message, dict) and "content" in message:
                            generated_text = message["content"].strip()
                            self.log(f"🤖 {char_name_for_log}: ローカルLLMからの応答取得成功。")
                            return generated_text
                    
                    self.log(f"❌ {char_name_for_log}: ローカルLLM応答形式エラー。Response: {response_data}")
                    return "ローカルLLM応答形式エラーです。"

        except aiohttp.ClientConnectorError as e:
            self.log(f"❌ {char_name_for_log}: ローカルLLM接続エラー ({endpoint_url}): {e}")
            return f"ローカルLLM ({endpoint_url}) に接続できませんでした。"
        except aiohttp.ClientResponseError as e:
            self.log(f"❌ {char_name_for_log}: ローカルLLM APIエラー ({endpoint_url}) - Status: {e.status}, Message: {e.message}, Response: {response_text_for_error}")
            return f"ローカルLLM APIエラー (ステータス: {e.status})。"
        except asyncio.TimeoutError: # aiohttp.ClientTimeout は asyncio.TimeoutError を発生させる
            self.log(f"❌ {char_name_for_log}: ローカルLLM応答タイムアウト ({endpoint_url})。")
            return "ローカルLLM応答タイムアウトしました。"
        except json.JSONDecodeError as e_json: # json.loads() が失敗した場合
            self.log(f"❌ {char_name_for_log}: ローカルLLM応答のJSONデコードエラー ({endpoint_url}): {e_json}. Response Text: {response_text_for_error}")
            return "ローカルLLM応答をJSON解析できませんでした。"
        except Exception as e_generic:
            self.log(f"❌ {char_name_for_log}: ローカルLLM呼び出し中に予期せぬエラー ({endpoint_url}): {e_generic}\n{traceback.format_exc()}")
            return "ローカルLLM呼び出し中に予期せぬエラー。"
    
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

                                # 会話履歴の記録と管理
                                history_length = self.config.get_system_setting("conversation_history_length", 0)
                                if history_length > 0:
                                    # 現在のやり取りを履歴に追加
                                    self.chat_history.append({"user": author_name, "comment": comment_text, "response": response})
                                    # 履歴が設定された長さを超えた場合、最も古いものから削除
                                    if len(self.chat_history) > history_length:
                                        self.chat_history.pop(0)
                            
                            self.previous_comment = comment_text
                    
                    # 監視間隔
                    await asyncio.sleep(self.config.get_system_setting("chat_monitor_interval", 5)) # 設定から取得
                    
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
            
            # 会話履歴の長さを設定から取得
            history_length = self.config.get_system_setting("conversation_history_length", 0)

            # プロンプトに会話履歴を組み込む
            history_prompt_parts = []
            if history_length > 0 and self.chat_history:
                # 直近の履歴を取得 (最大 history_length 件)
                relevant_history = self.chat_history[-history_length:]
                for entry in relevant_history:
                    # 履歴の各エントリをプロンプトに追加
                    history_prompt_parts.append(f"視聴者 {entry['user']}: {entry['comment']}")
                    history_prompt_parts.append(f"あなた: {entry['response']}") # AI自身の過去の発言として

            history_str = "\n".join(history_prompt_parts)
            # 最終的なプロンプト: キャラクター設定 + 会話履歴 + 最新のコメント
            full_prompt = f"{char_prompt}\n\n{history_str}\n\n視聴者 {author_name}: {comment_text}\n\n親しみやすく自然な返答をしてください。"
            
            # AI応答生成（文章生成のみ）
            selected_model_internal_name = self.config.get_system_setting("text_generation_model", "gemini-1.5-flash")
            local_llm_url = self.config.get_system_setting("local_llm_endpoint_url", "")
            char_name = self.config.get_character(self.character_id).get('name', 'AIちゃん') # ログ用

            if selected_model_internal_name == "local_lm_studio":
                if not local_llm_url:
                    self.log(f"❌ LocalLLM (Streaming - {char_name}): エンドポイントURLが設定されていません。")
                    return "ローカルLLMのエンドポイントURLが未設定です。"
                # _generate_response_local_llm_streaming は await 可能
                return await self._generate_response_local_llm_streaming(full_prompt, local_llm_url, char_name)
            else:
                # Google AI Studio (Gemini) を使用
                text_response = await asyncio.to_thread(
                    self.client.models.generate_content, # client を使用
                    model=selected_model_internal_name,  # 設定から読み込んだモデルを使用
                    contents=full_prompt,
                    config=genai.types.GenerateContentConfig( 
                        temperature=0.9,
                        max_output_tokens=100, # ストリーミングなので短めに
                        top_p=0.8
                    )
                )
                if text_response.text is None:
                    self.log(f"⚠️ AI応答がNoneでした (モデル: {selected_model_internal_name})。")
                    return "ごめんなさい、うまく言葉が出てきませんでした。"
                return text_response.text.strip()
            
        except genai.types.generation_types.BlockedPromptException as bpe:
            self.log(f"❌ 応答生成エラー: プロンプトがブロックされました。{bpe}")
            return "ごめんなさい、その内容についてはお答えできません。"
        except requests.exceptions.HTTPError as http_err:
            if http_err.response.status_code == 429:
                self.log(f"❌ 応答生成エラー: API利用上限に達した可能性があります (429)。{http_err}")
                return "APIの利用上限に達したみたいです。少し時間をおいて試してみてくださいね。"
            else:
                self.log(f"❌ 応答生成エラー: HTTPエラーが発生しました。{http_err}")
                return "ごめんなさい、サーバーとの通信でエラーが起きたみたいです。"
        except Exception as e:
            self.log(f"❌ 応答生成エラー: 予期せぬエラーが発生しました。{e}")
            import traceback
            self.log(f"詳細トレース: {traceback.format_exc()}")
            return "ちょっと調子が悪いみたいです。ごめんなさいね。"
    
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
