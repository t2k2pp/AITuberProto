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
                    config_data = json.load(f)
                    # local_llm_endpoint_url の互換性対応
                    if "system_settings" in config_data and \
                       "local_llm_endpoint_url" not in config_data["system_settings"]:
                        config_data["system_settings"]["local_llm_endpoint_url"] = ""
                    return config_data
            else:
                # 新規作成時もデフォルトに関わらずキーが含まれるようにする
                config_data = self.create_default_config()
                if "system_settings" in config_data and \
                   "local_llm_endpoint_url" not in config_data["system_settings"]:
                       config_data["system_settings"]["local_llm_endpoint_url"] = ""
                return config_data
        except Exception as e:
            print(f"設定読み込みエラー: {e}")
            # エラー時もデフォルト設定を返す前に、local_llm_endpoint_url を確認・追加する
            config_data = self.create_default_config()
            if "system_settings" in config_data and \
               "local_llm_endpoint_url" not in config_data["system_settings"]:
                 config_data["system_settings"]["local_llm_endpoint_url"] = ""
            return config_data
    
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
                "cost_mode": "free",
                "conversation_history_length": 0, # 会話履歴の保持数 (0は記憶なし、1以上でその回数分の直近の会話を記憶)
                "text_generation_model": "gemini-1.5-flash-latest", # デフォルトのテキスト生成モデルを更新
                "ai_chat_processing_mode": "sequential", # "sequential" または "parallel"
                "local_llm_endpoint_url": "" # LM StudioなどのローカルLLMのエンドポイントURL
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
                "log_level": "INFO",
                "language": "ja"  # デフォルト言語を日本語に設定
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

    def get_language(self):
        """現在の言語設定を取得"""
        return self.config.get("ui_settings", {}).get("language", "ja")

    def set_language(self, language_code):
        """言語設定を更新"""
        if "ui_settings" not in self.config:
            self.config["ui_settings"] = {}
        self.config["ui_settings"]["language"] = language_code
        # auto_save は system_settings の設定なので、ここでは参照しない。
        # ui_settings の変更時にも保存するのが適切か、
        # auto_save をグローバルな設定とみなすかによる。
        # ここでは、set_system_setting と同様に auto_save を確認する。
        if self.get_system_setting("auto_save", True):
            self.save_config()
