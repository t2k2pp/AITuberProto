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
import re # 正規表現モジュールをインポート
import json # JSONモジュールをインポート (macOSデバイス取得で使用)
import csv
import traceback # エラー追跡用に追加


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
            # 既存の speaker 情報をクリアして、常に最新の情報を取得する
            self.speakers = []
            self.is_available = False
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/speakers", timeout=3) as response:
                    if response.status == 200:
                        self.speakers = await response.json()
                        if self.speakers: # speakersが空でないことを確認
                            self.is_available = True
                            print(f"VOICEVOX Engine接続成功。話者情報取得: {len(self.speakers)}名")
                            return True
                        else:
                            print("VOICEVOX Engine接続成功。しかし話者情報が空です。")
                            return False # 話者情報がなければ利用不可とみなす
                    else:
                        print(f"VOICEVOX Engine接続エラー: Status {response.status}")
                        return False
        except Exception as e:
            print(f"VOICEVOX Engine接続エラー: {e}")
            self.is_available = False
            return False
    
    def get_available_voices(self):
        """利用可能な音声一覧を取得"""
        # check_availability が呼び出され、self.speakers が更新されていることを期待
        # もし self.speakers が空、または check_availability が失敗していたらフォールバック
        if not self.is_available or not self.speakers:
            print("VOICEVOX Engineから話者情報を取得できなかったため、ハードコードされたリストを使用します。")
            # フォールバック用のハードコードリスト (最新の状況に合わせて拡充)
            return [
                "ずんだもん(ノーマル)", "ずんだもん(あまあま)", "ずんだもん(ツンツン)", "ずんだもん(セクシー)", "ずんだもん(ささやき)", "ずんだもん(ヒソヒソ)", "ずんだもん(ヘロヘロ)", "ずんだもん(なみだめ)",
                "四国めたん(ノーマル)", "四国めたん(あまあま)", "四国めたん(ツンツン)", "四国めたん(セクシー)", "四国めたん(ささやき)", "四国めたん(ヒソヒソ)",
                "春日部つむぎ(ノーマル)",
                "雨晴はう(ノーマル)",
                "波音リツ(ノーマル)", "波音リツ(クイーン)",
                "玄野武宏(ノーマル)", "玄野武宏(喜び)", "玄野武宏(ツンギレ)", "玄野武宏(悲しみ)",
                "白上虎太郎(ふつう)", "白上虎太郎(わーい)", "白上虎太郎(おこ)", "白上虎太郎(びくびく)", "白上虎太郎(びえーん)",
                "青山龍星(ノーマル)", "青山龍星(熱血)", "青山龍星(不機嫌)", "青山龍星(喜び)", "青山龍星(しっとり)", "青山龍星(かなしみ)", "青山龍星(囁き)",
                "冥鳴ひまり(ノーマル)",
                "九州そら(ノーマル)", "九州そら(あまあま)", "九州そら(ツンツン)", "九州そら(セクシー)", "九州そら(ささやき)",
                "もち子さん(ノーマル)", "もち子さん(セクシー／あん子)", "もち子さん(泣き)", "もち子さん(怒り)", "もち子さん(喜び)", "もち子さん(のんびり)",
                "剣崎雌雄(ノーマル)",
                "WhiteCUL(ノーマル)", "WhiteCUL(たのしい)", "WhiteCUL(かなしい)", "WhiteCUL(びえーん)",
                "後鬼(人間ver.)", "後鬼(ぬいぐるみver.)", "後鬼(人間（怒り）ver.)", "後鬼(鬼ver.)",
                "No.7(ノーマル)", "No.7(アナウンス)", "No.7(読み聞かせ)",
                "ちび式じい(ノーマル)",
                "櫻歌ミコ(ノーマル)", "櫻歌ミコ(第二形態)", "櫻歌ミコ(ロリ)",
                "小夜/SAYO(ノーマル)",
                "ナースロボ＿タイプＴ(ノーマル)", "ナースロボ＿タイプＴ(楽々)", "ナースロボ＿タイプＴ(恐怖)", "ナースロボ＿タイプＴ(内緒話)",
                "†聖騎士 紅桜†(ノーマル)",
                "雀松朱司(ノーマル)",
                "麒ヶ島宗麟(ノーマル)",
                "春歌ナナ(ノーマル)",
                "猫使アル(ノーマル)", "猫使アル(おちつき)", "猫使アル(うきうき)",
                "猫使ビィ(ノーマル)", "猫使ビィ(おちつき)", "猫使ビィ(人見知り)",
                "中国うさぎ(ノーマル)", "中国うさぎ(おどろき)", "中国うさぎ(こわがり)", "中国うさぎ(へろへろ)",
                "栗田まろん(ノーマル)",
                "あいえるたん(ノーマル)",
                "満別花丸(ノーマル)", "満別花丸(元気)", "満別花丸(ささやき)", "満別花丸(ぶりっ子)", "満別花丸(ボーイ)",
                "琴詠ニア(ノーマル)",
                "Voidoll(ノーマル)",
                "ぞん子(ノーマル)", "ぞん子(低血圧)", "ぞん子(覚醒)", "ぞん子(実況風)",
                "中部つるぎ(ノーマル)", "中部つるぎ(怒り)", "中部つるぎ(ヒソヒソ)", "中部つるぎ(おどおど)", "中部つるぎ(絶望と敗北)",
                "離途(ノーマル)",
                "黒沢冴白(ノーマル)"
            ]

        voice_list = []
        if self.speakers: # self.speakers が Engine から取得した情報で埋まっている場合
            for speaker_info in self.speakers:
                speaker_name = speaker_info.get('name')
                styles = speaker_info.get('styles', [])
                if speaker_name and styles:
                    for style_info in styles:
                        style_name = style_info.get('name')
                        if style_name:
                            voice_list.append(f"{speaker_name}({style_name})")

        if not voice_list: # Engine から取得できなかった、または空だった場合の最終フォールバック
            print("VOICEVOX Engineからの話者情報が取得できなかったため、ハードコードされたリスト(再フォールバック)を使用します。")
            return ["ずんだもん(ノーマル)", "四国めたん(ノーマル)"] # 最低限のリスト

        return sorted(list(set(voice_list))) # 重複を除きソートして返す

    def get_max_text_length(self):
        return self.max_length

    def get_engine_info(self):
        return {
            "name": "VOICEVOX Engine",
            "cost": "完全無料",
            "quality": "★★★☆☆",
            "description": "定番キャラクター・ずんだもん等・安定動作"
        }

    def _parse_voice_name(self, voice_name_input):
        """音声名からスピーカーIDを取得"""
        try:
            parsed_speaker_name = ""
            parsed_style_name = ""

            if '(' in voice_name_input and ')' in voice_name_input:
                parsed_speaker_name = voice_name_input.split('(')[0]
                parsed_style_name = voice_name_input.split('(')[1].replace(')', '')
            else:
                # スタイル名が省略されている場合は、デフォルトのスタイル名を探すか、エラーとする
                # ここでは、まずEngineからの情報で完全一致を探すことを優先
                parsed_speaker_name = voice_name_input
                # スタイル名が不明な場合、Engine情報でその話者の最初のスタイルIDを使うなどの戦略も可能
                # print(f"VOICEVOX _parse_voice_name: スタイル名が指定されていません: {voice_name_input}")

            # 1. Engineから取得した情報 (self.speakers) を優先して検索
            if self.speakers:
                for speaker_info in self.speakers:
                    if speaker_info.get('name') == parsed_speaker_name:
                        for style_info in speaker_info.get('styles', []):
                            if parsed_style_name == "" or style_info.get('name') == parsed_style_name:
                                print(f"VOICEVOX _parse_voice_name (dynamic): Found ID {style_info['id']} for {voice_name_input}")
                                return style_info['id']
            
            # 2. Engine情報で見つからなかった場合、ハードコードされたマッピングでフォールバック
            #    このマッピングは主要なキャラクターのみ、または最新情報に更新する
            print(f"VOICEVOX _parse_voice_name: Engine情報に '{voice_name_input}' が見つかりません。ハードコードマッピングを試みます。")
            character_mapping_fallback = {
                "ずんだもん": {"ノーマル": 3, "あまあま": 1, "ツンツン": 7, "セクシー": 26, "ささやき":22, "ヒソヒソ":38, "ヘロヘロ":42, "なみだめ":46}, # VOICEVOX 0.14.x 以前のIDと混在しないように注意
                "四国めたん": {"ノーマル": 2, "あまあま": 0, "ツンツン": 6, "セクシー": 4, "ささやき":36, "ヒソヒソ":37},
                "春日部つむぎ": {"ノーマル": 8},
                "雨晴はう": {"ノーマル": 10},
                "波音リツ": {"ノーマル": 9, "クイーン":53},
                "玄野武宏": {"ノーマル": 11, "喜び":47, "ツンギレ":48, "悲しみ":49},
                "白上虎太郎": {"ふつう": 12, "わーい":50, "おこ":51, "びくびく":52, "びえーん":53}, # スタイル名が「ふつう」
                "青山龍星": {"ノーマル": 13, "熱血":58, "不機嫌":59, "喜び":60, "しっとり":61, "かなしみ":62, "囁き":63},
                "冥鳴ひまり": {"ノーマル": 14},
                "九州そら": {"ノーマル": 16, "あまあま":17, "ツンツン":18, "セクシー":19, "ささやき":20},
                # 以下、必要に応じて他のキャラクターも追加
                # "もち子さん": {"ノーマル": 21, "セクシー／あん子": ..., "泣き": ..., "怒り": ..., "喜び": ..., "のんびり": ...},
                # "剣崎雌雄": {"ノーマル": 23},
                # "WhiteCUL": {"ノーマル": 24, "たのしい": ..., "かなしい": ..., "びえーん": ...},
            }
            
            if parsed_speaker_name in character_mapping_fallback:
                styles = character_mapping_fallback[parsed_speaker_name]
                # スタイル名が指定されていない場合、そのキャラクターの最初のスタイルID（多くは"ノーマル"）を返す
                if parsed_style_name == "" and styles:
                     # "ノーマル" があればそれを、なければリストの最初のものを返す
                    found_id = styles.get("ノーマル", next(iter(styles.values())))
                    print(f"VOICEVOX _parse_voice_name (fallback, no style): Using ID {found_id} for {parsed_speaker_name}")
                    return found_id
                elif parsed_style_name in styles:
                    found_id = styles[parsed_style_name]
                    print(f"VOICEVOX _parse_voice_name (fallback): Found ID {found_id} for {voice_name_input}")
                    return found_id
            
            # それでも見つからない場合は、アプリケーションのデフォルト話者ID (例: ずんだもんノーマル)
            print(f"VOICEVOX _parse_voice_name: ハードコードマッピングでも '{voice_name_input}' が見つかりません。デフォルトID 3 を使用します。")
            return 3 # ずんだもん(ノーマル)のID
            
        except Exception as e:
            print(f"VOICEVOX 音声名パースエラー: {e}, voice_name: {voice_name_input}. デフォルトID 3 を使用します。")
            return 3 # エラー時もデフォルトID
    
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
                "Haruka (SAPI5)",
                "Zira (SAPI5)",
                "Ayumi (OneCore)",
                "Ichiro (OneCore)",
                "Haruka (OneCore)",
                "Sayaka (OneCore)",
                "Zira (OneCore)",
                "David (OneCore)",
                "Mark (OneCore)",
                "Jenny (OneCore)",
                "Guy (OneCore)",
                # Keep other existing non-SAPI5/non-OneCore desktop voices if any were intended to be kept
                # For now, assuming the request implies these are the primary voices to be listed for Windows System TTS
            ]
            self.default_voice = "Haruka (SAPI5)" # Default remains Haruka SAPI5
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
        """Windows用TTS実装 v2.2（SAPI5/OneCore対応）"""
        try:
            ps_voice_name = voice_model # Initialize with the input voice_model

            if "(SAPI5)" in voice_model:
                base_name = voice_model.replace(" (SAPI5)", "").strip()
                sapi5_mapping = {
                    "Haruka": "Microsoft Haruka Desktop",
                    "Zira": "Microsoft Zira Desktop",
                }
                ps_voice_name = sapi5_mapping.get(base_name, f"Microsoft {base_name} Desktop")
            elif "(OneCore)" in voice_model:
                base_name = voice_model.replace(" (OneCore)", "").strip()
                onecore_mapping = {
                    "Ayumi": "Microsoft Ayumi OneCore",
                    "Ichiro": "Microsoft Ichiro OneCore",
                    "Haruka": "Microsoft Haruka OneCore",
                    "Sayaka": "Microsoft Sayaka OneCore",
                    "Zira": "Microsoft Zira OneCore",
                    "David": "Microsoft David OneCore",
                    "Mark": "Microsoft Mark OneCore",
                    "Jenny": "Microsoft Jenny OneCore",
                    "Guy": "Microsoft Guy OneCore",
                }
                ps_voice_name = onecore_mapping.get(base_name, f"Microsoft {base_name} OneCore")
            elif "Desktop" not in voice_model and "Microsoft" not in voice_model:
                # This block is for existing short names if they don't have SAPI5/OneCore suffix
                # and are not already full names.
                default_desktop_mapping = {
                    "Ayumi": "Microsoft Ayumi Desktop", # Should be Ayumi (OneCore) or Ayumi (SAPI5) if used
                    "Ichiro": "Microsoft Ichiro Desktop",# Should be Ichiro (OneCore) or Ichiro (SAPI5) if used
                    "David": "Microsoft David Desktop",  # Should be David (OneCore) or David (SAPI5) if used
                    "Hazel": "Microsoft Hazel Desktop",
                    # Haruka and Zira are primarily handled by (SAPI5) or (OneCore) suffixed versions
                }
                # Only apply this mapping if voice_model is a simple name like "Ayumi"
                # and not something already processed or a full name.
                if voice_model in default_desktop_mapping:
                     ps_voice_name = default_desktop_mapping.get(voice_model)
            # If voice_model was already a full name like "Microsoft Haruka Desktop",
            # it would have passed through the above conditions and ps_voice_name remains voice_model.
            # voice_name_for_ps = ps_voice_name # This line is removed. ps_voice_name is used directly.
            
            rate_value = max(-10, min(10, int((speed - 1.0) * 5)))
            
            ps_script = f'''
Add-Type -AssemblyName System.speech
$speak = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {{
    $voices = $speak.GetInstalledVoices()
    # Write-Host "Attempting to select voice with ps_voice_name: {ps_voice_name}" # Debug line removed
    $targetVoice = $voices | Where-Object {{ $_.VoiceInfo.Name -eq "{ps_voice_name}" }}
    if ($targetVoice) {{
        $speak.SelectVoice("{ps_voice_name}")
        # Write-Host "Successfully selected voice: {ps_voice_name}" # Debug line removed
    }} else {{
        # Write-Host "Exact match for '{ps_voice_name}' not found. Trying fallback mechanisms..." # Debug line removed
        $baseNameToSearch = ""
        if ("{ps_voice_name}".Contains("Microsoft") -and "{ps_voice_name}".Split(" ").Length -gt 1) {{
             $baseNameToSearch = "{ps_voice_name}".Split(" ")[1]
        }} else {{
             $baseNameToSearch = "{ps_voice_name}".Split(" (")[0]
        }}

        if ($baseNameToSearch -ne "") {{
            # Write-Host "Attempting partial match with base name: $baseNameToSearch" # Debug line removed
            $partialMatch = $voices | Where-Object {{ $_.VoiceInfo.Name -like "*$baseNameToSearch*" }} | Select-Object -First 1
            if ($partialMatch) {{
                $speak.SelectVoice($partialMatch.VoiceInfo.Name)
                # Write-Host "Fallback: Successfully selected voice by partial match: $($partialMatch.VoiceInfo.Name)" # Debug line removed
            }} else {{
                # Write-Host "Fallback: No partial match found for '$baseNameToSearch'. System will use its default voice." # Debug line removed
            }}
        }} else {{
            # Write-Host "Could not determine a base name for search from '{ps_voice_name}'. System will use its default voice." # Debug line removed
        }}
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
    
    def __init__(self, config_manager=None): # config_manager を追加
        self.current_process = None
        self.system = platform.system()
        self.config_manager = config_manager

    def get_available_output_devices(self):
        """利用可能な音声出力デバイスの一覧を取得する"""
        devices = [{"name": "デフォルト", "id": "default"}] # デフォルトデバイスオプション
        try:
            if self.system == "Windows":
                # PowerShellコマンドで音声デバイスを取得
                # Get-AudioDevice -List は AudioDeviceCmdlets モジュールが必要な場合がある
                # より標準的な方法を試みる
                import subprocess
                cmd = 'powershell "Get-CimInstance -Namespace root\\cimv2 -ClassName Win32_SoundDevice | Select-Object -Property Name, DeviceID"'
                result = subprocess.run(cmd, capture_output=True, text=True, shell=True, encoding='utf-8')
                if result.returncode == 0:
                    for line in result.stdout.splitlines():
                        if "Name" in line and "DeviceID" in line: # ヘッダーをスキップ
                            continue
                        if "----" in line: # 区切り線をスキップ
                            continue
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            name = " ".join(parts[:-1]).strip()
                            device_id = parts[-1].strip()
                            if name and device_id: # 空の行を避ける
                                devices.append({"name": name, "id": device_id})
                else:
                    print(f"Windows: Get-CimInstance を使用したデバイス取得に失敗しました: {result.stderr}")
                    #代替手段 (より基本的なコマンド)
                    cmd_alt = 'powershell "Get-WmiObject -Class Win32_SoundDevice | Select-Object -Property Name, DeviceID"'
                    result_alt = subprocess.run(cmd_alt, capture_output=True, text=True, shell=True, encoding='utf-8')
                    if result_alt.returncode == 0:
                        for line in result_alt.stdout.splitlines():
                            if "Name" in line and "DeviceID" in line: continue
                            if "----" in line: continue
                            parts = line.strip().split()
                            if len(parts) >= 2:
                                name = " ".join(parts[:-1]).strip()
                                device_id = parts[-1].strip()
                                if name and device_id:
                                     devices.append({"name": name, "id": device_id})
                    else:
                        print(f"Windows: Get-WmiObject を使用したデバイス取得にも失敗しました: {result_alt.stderr}")


            elif self.system == "Darwin": # macOS
                import subprocess
                # system_profiler SPAudioDataType は詳細すぎる場合がある。よりシンプルなコマンドを検討。
                # 'audiodevice' コマンドは標準ではないため、 'switchaudio-osx' (https://github.com/deweller/switchaudio-osx) のような
                # 外部ツールをユーザーにインストールしてもらうか、より基本的な方法を探す。
                # ここでは system_profiler を使い、出力デバイスのみをフィルタリングする。
                cmd = "system_profiler SPAudioDataType -json"
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, shell=True, check=True)
                    data = json.loads(result.stdout)
                    audio_data = data.get("SPAudioDataType", [])
                    for item in audio_data:
                        # 'items' の中に実際のデバイス情報が含まれることがある
                        # 'coreaudio_output_source' などでフィルタリング
                        # 'coreaudio_default_audio_output_device' や 'coreaudio_device_name' を参考にする
                        # 簡略化のため、ここでは出力デバイスと思われるものをリストアップ
                        # より正確なフィルタリングが必要
                        # print(f"macOS device item: {item}") # デバッグ用
                        # 'items' 配下の 'coreaudio_device_name' を探す
                        for sub_item in item.get("_items", []):
                            if sub_item.get("coreaudio_device_transport") == "coreaudio_device_type_builtin_output" or \
                               sub_item.get("coreaudio_device_transport") == "coreaudio_device_type_external_output" or \
                               "output" in sub_item.get("coreaudio_device_name","").lower() or \
                               "speaker" in sub_item.get("coreaudio_device_name","").lower(): # 簡易的な出力デバイス判定

                                device_name = sub_item.get("coreaudio_device_name")
                                # macOSでは一意のIDが簡単には取れない場合があるので、名前をIDとして使う
                                if device_name and not any(d['name'] == device_name for d in devices):
                                    devices.append({"name": device_name, "id": device_name})
                except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError) as e:
                    print(f"macOS: デバイス取得エラー: {e}")
                    # 代替として、基本的な 'audiodevice' のようなコマンドがあれば使う (ただし標準ではない)

            elif self.system == "Linux":
                import subprocess
                cmd = "aplay -L"
                result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
                if result.returncode == 0:
                    current_device_name = None
                    for line in result.stdout.splitlines():
                        line = line.strip()
                        if not line:
                            continue
                        # 'default' や 'null' などの特殊なデバイス名も含まれることがある
                        # ユーザーが選択しやすいように、より具体的な名前を優先する
                        # 'sysdefault', 'front', 'surround40' など、カード名とデバイス番号の組み合わせもよく使われる
                        if line.startswith("CARD=") or line.startswith("DEV="): # 詳細情報はスキップ
                            continue
                        if re.match(r"^[a-zA-Z0-9_-]+:\d+,\d+$", line): # "hw:0,0" のような形式
                            device_id = line
                            # より人間可読な名前を探す (次の行にあることが多い)
                            # この実装では hw:0,0 のようなIDをそのまま使う
                            # devices.append({"name": f"Hardware Device ({device_id})", "id": device_id})
                            # aplay -L の出力は複雑なので、ここでは簡略化して、行全体をID兼名前とする
                            # ただし、これだとユーザーフレンドリーではない。
                            # 実際のデバイス名 (例: "HDA Intel PCH, ALC255 Analog") を抽出する必要がある
                            if line.count(',') == 0 and not line.startswith(" "): # 'default' や 'plughw:CARD=PCH,DEV=0' など
                                 # 'null', 'pulse', 'default', 'dmix'などを除外するか検討
                                if line not in ["null", "pulse", "default", "dmix", "dsnoop"]:
                                    devices.append({"name": line, "id": line})
                        elif not line.startswith(" ") and ":" not in line and "," not in line: # 比較的シンプルな名前
                             if line not in ["null", "pulse", "default", "dmix", "dsnoop"]:
                                devices.append({"name": line, "id": line})


                else:
                    print(f"Linux: aplay -L を使用したデバイス取得に失敗しました: {result.stderr}")
                    # 代替: pacmd list-sinks (PulseAudioの場合)
                    cmd_pa = "pacmd list-sinks"
                    result_pa = subprocess.run(cmd_pa, capture_output=True, text=True, shell=True)
                    if result_pa.returncode == 0:
                        name_pattern = re.compile(r"name: <(.*?)>")
                        desc_pattern = re.compile(r"device.description = \"(.*?)\"")
                        current_name = None
                        for line in result_pa.stdout.splitlines():
                            name_match = name_pattern.search(line)
                            if name_match:
                                current_name = name_match.group(1)
                            desc_match = desc_pattern.search(line)
                            if desc_match and current_name:
                                devices.append({"name": desc_match.group(1), "id": current_name})
                                current_name = None # Reset for next sink
                    else:
                        print(f"Linux: pacmd list-sinks を使用したデバイス取得にも失敗しました: {result_pa.stderr}")


        except Exception as e:
            print(f"音声出力デバイスの取得中にエラーが発生しました: {e}")
            # エラーが発生した場合でもデフォルトデバイスは常に利用可能とする

        # 重複排除 (特に default のような汎用名が複数追加されるのを防ぐ)
        final_devices = []
        seen_ids = set()
        for device in devices:
            if device["id"] not in seen_ids:
                final_devices.append(device)
                seen_ids.add(device["id"])
        return final_devices

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
        """Windows用音声再生（デバイス指定対応）"""
        try:
            device_id = "default"
            if self.config_manager:
                device_id = self.config_manager.get_system_setting("audio_output_device", "default")

            # PowerShellスクリプトで再生。デバイス指定は難しいので、winsoundを優先的に試す。
            # winsound はデフォルトデバイスでしか再生できないため、デバイス指定が必要な場合は
            # より高度なライブラリ (例: sounddevice, pygame.mixer) の利用を検討する必要がある。
            # ここでは、まず winsound で試行し、失敗した場合に PowerShell の MediaPlayer を使う。
            # デバイス指定は現状、PowerShellのMediaPlayerでは直接的でないため、
            # 指定された device_id が 'default' でない場合は警告を出す。

            if device_id != "default":
                print(f"⚠️ Windows: 指定された音声出力デバイス '{device_id}' での再生は現在サポートされていません。デフォルトデバイスを使用します。")
                # TODO: 将来的に、AudioDeviceCmdlets (外部) や他のライブラリでデバイス指定再生を実装する。
                # (例: Set-AudioDevice -ID $deviceId; $mediaPlayer.Play() )
                # ただし、Set-AudioDevice は永続的な変更なので、再生前後で元に戻す処理が必要。

            try:
                import winsound
                # winsound.PlaySoundは非同期ではないため、スレッドで実行してブロッキングを防ぐ
                # SND_ASYNC は他のサウンドと競合する可能性があるので、ここでは同期的に再生し、
                # play_audio_files での asyncio.sleep でカバーする。
                # await asyncio.to_thread(winsound.PlaySound, audio_file, winsound.SND_FILENAME | winsound.SND_ASYNC)
                await asyncio.to_thread(winsound.PlaySound, audio_file, winsound.SND_FILENAME)
                print(f"✅ AudioPlayer: winsound.PlaySound ({audio_file}) で再生しました。")
                return # winsound で成功したらここで終了
            except Exception as winsound_e:
                print(f"🐍 AudioPlayer: winsound.PlaySound でエラーが発生しました: {winsound_e}。PowerShell MediaPlayerにフォールバックします。")

            # winsound が失敗した場合、またはデバイス指定が必要な場合のフォールバック (現状デバイス指定なし)
            ps_script = f'''
Add-Type -AssemblyName presentationCore
$mediaPlayer = New-Object system.windows.media.mediaplayer
$mediaPlayer.open("{audio_file}")
$mediaPlayer.Play()
$loaded = $False
for ($i = 0; $i -lt 50; $i++) {{
    if ($mediaPlayer.NaturalDuration.HasTimeSpan) {{
        $loaded = $True
        break
    }}
    Start-Sleep -Milliseconds 100
}}
if ($loaded -and $mediaPlayer.NaturalDuration.TimeSpan.TotalSeconds -gt 0) {{
    while($mediaPlayer.Position -lt $mediaPlayer.NaturalDuration.TimeSpan) {{
        Start-Sleep -Milliseconds 100
    }}
}} else {{
    Start-Sleep -Seconds 2
}}
$mediaPlayer.Stop()
$mediaPlayer.Close()
'''
            process = await asyncio.create_subprocess_exec(
                "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if process.returncode != 0 or "エラー" in stderr.decode('utf-8', errors='ignore').lower() or "error" in stderr.decode('utf-8', errors='ignore').lower():
                print(f"❌ AudioPlayer._play_windows: PowerShell再生エラー: {stderr.decode('utf-8', errors='ignore')}")
            else:
                print(f"✅ AudioPlayer._play_windows: PowerShellによる音声再生成功: {audio_file}")

        except Exception as e:
            print(f"❌ Windows音声再生エラー: {e}")
    
    async def _play_macos(self, audio_file):
        """macOS用音声再生（デバイス指定は現状困難）"""
        try:
            device_id = "default"
            if self.config_manager:
                device_id = self.config_manager.get_system_setting("audio_output_device", "default")

            # afplay には直接的なデバイス指定オプションがない。
            # 'audiodevice' (https://github.com/sourcelair/audiodevice) のような外部コマンドラインツールを使うか、
            # Swift/Objective-C で Core Audio を操作するヘルパースクリプトを呼び出す必要がある。
            # ここでは、もし 'audiodevice' コマンドがあればそれを使用し、なければ afplay のデフォルト出力にフォールバック。
            cmd_list = []
            if device_id != "default":
                print(f"ℹ️ macOS: 指定デバイス '{device_id}' での再生を試みます。audiodeviceコマンドが必要です。")
                # audiodevice コマンドの存在確認は省略し、直接実行を試みる。エラーならafplayへ。
                # audiodevice output "{device_id}" # これでデフォルト出力デバイスを変更
                # process_set_device = await asyncio.create_subprocess_exec("audiodevice", "output", device_id)
                # await process_set_device.wait()
                # if process_set_device.returncode != 0:
                #     print(f"⚠️ macOS: audiodevice での出力デバイス設定に失敗。afplay のデフォルト出力を使用します。")
                # cmd_list.extend(["afplay", audio_file])
                #
                # より安全なのは、afplay の -d オプション (もしあれば) や、
                # OSレベルでデフォルトデバイスを切り替える方法だが、afplay にはそのオプションがない。
                # Soundflowerのような仮想オーディオデバイスとルーティングを使う手もあるが複雑。
                # 現状は、device_id が default でない場合は警告を出し、afplay のデフォルト出力で再生。
                print(f"⚠️ macOS: 指定された音声出力デバイス '{device_id}' での再生は現在 'afplay' では直接サポートされていません。デフォルトデバイスを使用します。")
                cmd_list = ["afplay", audio_file]
            else:
                cmd_list = ["afplay", audio_file]

            process = await asyncio.create_subprocess_exec(*cmd_list)
            await process.wait()
            if process.returncode != 0:
                print(f"❌ macOS: {' '.join(cmd_list)} での再生に失敗しました。")
            else:
                print(f"✅ macOS: {' '.join(cmd_list)} で再生しました。")

        except FileNotFoundError:
            print(f"❌ macOS: afplay (または audiodevice) コマンドが見つかりません。")
        except Exception as e:
            print(f"❌ macOS音声再生エラー: {e}")
    
    async def _play_linux(self, audio_file):
        """Linux用音声再生（デバイス指定対応）"""
        try:
            device_id = "default"
            if self.config_manager:
                device_id = self.config_manager.get_system_setting("audio_output_device", "default")

            players = ["aplay", "paplay", "play"] # ffplayはデバイス指定が複雑なので一旦除外
            
            for player_name in players:
                cmd_list = []
                if player_name == "aplay":
                    if device_id != "default":
                        cmd_list = [player_name, "-D", device_id, audio_file]
                    else:
                        cmd_list = [player_name, audio_file]
                elif player_name == "paplay": # PulseAudio Player
                    if device_id != "default":
                        # paplay の --device オプションはシンク名またはインデックス
                        cmd_list = [player_name, "--device", device_id, audio_file]
                    else:
                        cmd_list = [player_name, audio_file]
                elif player_name == "play": # SoX
                    # play コマンド (SoX) の場合、AUDIODEV 環境変数でデバイスを指定できる場合がある
                    # または、-d <driver>:<device> のような形式だが、汎用性に欠ける。
                    # ここでは AUDIODEV の設定は行わず、デフォルトで試す。
                    if device_id != "default":
                         print(f"⚠️ Linux: play コマンドでのデバイス '{device_id}' 指定は現在サポートされていません。デフォルトデバイスを使用します。")
                    cmd_list = [player_name, audio_file]

                if not cmd_list: continue

                try:
                    process = await asyncio.create_subprocess_exec(
                        *cmd_list,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await process.communicate()
                    
                    if process.returncode == 0:
                        print(f"✅ Linux: {' '.join(cmd_list)} で再生しました。")
                        return
                    else:
                        print(f"ℹ️ Linux: {' '.join(cmd_list)} での再生に失敗。次のプレイヤーを試します。Stderr: {stderr.decode('utf-8', errors='ignore')}")
                except FileNotFoundError:
                    print(f"ℹ️ Linux: {player_name} が見つかりません。")
                    continue
            
            print(f"❌ Linux: 利用可能な音声プレイヤーで {audio_file} の再生に失敗しました。")
            
        except Exception as e:
            print(f"❌ Linux音声再生エラー: {e}")

# 音声エンジン管理クラス v2.2（4エンジン完全対応版）
class VoiceEngineManager:
    """
    音声エンジン管理クラス v2.2 - 4エンジン完全統合版
    
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
        フォールバック機能付き音声合成 v2.2（4エンジン完全対応版）
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
                if "google_ai_studio" in engine_name :
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


