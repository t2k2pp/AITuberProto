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
#from google import genai # 公式ドキュメント推奨
#from google.genai import types # 公式ドキュメント推奨
import google.generativeai as genai
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


# ロギング設定
logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.INFO) # main.py などで設定される想定


# 設定管理クラス（完全版）
class ConfigManager:
    """
    統一設定管理システム v2.2 - 完全版
    4エンジン対応・全ての設定をJSONファイルで管理
    MCP設定機能追加
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
                    # 互換性対応: 既存の設定ファイルに mcp_settings がない場合に追加
                    if "mcp_settings" not in config_data:
                        config_data["mcp_settings"] = self.create_default_config()["mcp_settings"]
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
            logger.error(f"設定読み込みエラー: {e}")
            # エラー時もデフォルト設定を返す前に、mcp_settings と local_llm_endpoint_url を確認・追加する
            config_data = self.create_default_config()
            if "mcp_settings" not in config_data: #念のため
                 config_data["mcp_settings"] = self.create_default_config()["mcp_settings"]
            if "system_settings" in config_data and \
               "local_llm_endpoint_url" not in config_data["system_settings"]:
                 config_data["system_settings"]["local_llm_endpoint_url"] = ""
            return config_data

    def create_default_config(self):
        """デフォルト設定を作成（v2.2完全版 + MCP）"""
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
            ],
            "mcp_settings": { # MCP設定セクション
                "servers": {
                    "filesystem": { # このキーを一時的にEchoサーバーのテストに使う
                        "enabled": True,
                        "command": "mcp", # SDKのCLIランナーを使用
                        "args": ["run", "./mcp_servers/echo_server_mcp.py"], # 新しいechoサーバーを指定
                        "env": {"PYTHONUNBUFFERED": "1"}, # 必要に応じてPYTHONPATHなどもここに設定できる
                        "description": "一時的なEchoテストサーバー (本来はfilesystem)"
                    }
                    # 例: "another_server": { "enabled": False, "command": "node", "args": ["./mcp_servers/another_server.js"] }
                },
                "client_options": {
                    "default_timeout": 30 # 秒: ツール呼び出しなどのタイムアウト
                }
            }
        }

    def save_config(self):
        """設定をファイルに保存"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            # logger.info("設定が保存されました。") # 保存成功時のログは任意
            return True
        except Exception as e:
            logger.error(f"設定保存エラー: {e}")
            return False

    def get_system_setting(self, key, default=None):
        """システム設定を取得"""
        return self.config.get("system_settings", {}).get(key, default)

    def set_system_setting(self, key, value):
        """システム設定を更新"""
        if "system_settings" not in self.config:
            self.config["system_settings"] = {}
        self.config["system_settings"][key] = value
        if self.config.get("system_settings", {}).get("auto_save", True):
            self.save_config()

    def get_character(self, char_id):
        """キャラクター設定を取得"""
        return self.config.get("characters", {}).get(char_id)

    def save_character(self, char_id, char_data):
        """キャラクター設定を保存"""
        if "characters" not in self.config:
            self.config["characters"] = {}
        self.config["characters"][char_id] = char_data
        if self.get_system_setting("auto_save", True): # auto_saveを尊重
            self.save_config()

    def delete_character(self, char_id):
        """キャラクターを削除"""
        if char_id in self.config.get("characters", {}):
            del self.config["characters"][char_id]
            if self.get_system_setting("auto_save", True): # auto_saveを尊重
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
        if self.get_system_setting("auto_save", True):
            self.save_config()
        logger.info("システム設定がデフォルトにリセットされました。")

    def get_all_system_settings(self):
        """現在のシステム設定全体を返す"""
        return self.config.get("system_settings", {}).copy() # コピーを返して内部辞書を保護

    def set_all_system_settings(self, new_settings_dict):
        """システム設定全体を指定された辞書で更新する"""
        if not isinstance(new_settings_dict, dict):
            logger.error("エラー: set_all_system_settings には辞書を指定してください。")
            return

        self.config["system_settings"] = new_settings_dict.copy()

        if self.config.get("system_settings", {}).get("auto_save", True):
            self.save_config()
        logger.info("システム設定が更新されました。")

    def get_language(self):
        """現在の言語設定を取得"""
        return self.config.get("ui_settings", {}).get("language", "ja")

    def set_language(self, language_code):
        """言語設定を更新"""
        if "ui_settings" not in self.config:
            self.config["ui_settings"] = {}
        self.config["ui_settings"]["language"] = language_code
        if self.get_system_setting("auto_save", True):
            self.save_config()

    # --- MCP設定関連メソッド ---
    def get_mcp_settings(self) -> dict:
        """MCP関連の設定全体を取得する"""
        return self.config.get("mcp_settings", self.create_default_config()["mcp_settings"]).copy()

    def get_mcp_servers(self) -> dict:
        """MCPサーバーの設定を取得する"""
        mcp_settings = self.get_mcp_settings()
        return mcp_settings.get("servers", {})

    def get_mcp_server_config(self, server_name: str) -> dict | None:
        """指定されたMCPサーバーの設定を取得する"""
        servers = self.get_mcp_servers()
        return servers.get(server_name)

    def save_mcp_server_config(self, server_name: str, config: dict) -> bool:
        """指定されたMCPサーバーの設定を保存する"""
        if "mcp_settings" not in self.config:
            self.config["mcp_settings"] = self.create_default_config()["mcp_settings"]
        if "servers" not in self.config["mcp_settings"]:
            self.config["mcp_settings"]["servers"] = {}

        self.config["mcp_settings"]["servers"][server_name] = config
        logger.info(f"MCPサーバー '{server_name}' の設定を更新しました。")
        if self.get_system_setting("auto_save", True):
            return self.save_config()
        return True # 保存はスキップされたが、設定はメモリ上更新された

    def delete_mcp_server_config(self, server_name: str) -> bool:
        """指定されたMCPサーバーの設定を削除する"""
        if "mcp_settings" in self.config and "servers" in self.config["mcp_settings"] and \
           server_name in self.config["mcp_settings"]["servers"]:
            del self.config["mcp_settings"]["servers"][server_name]
            logger.info(f"MCPサーバー '{server_name}' の設定を削除しました。")
            if self.get_system_setting("auto_save", True):
                return self.save_config()
            return True
        logger.warning(f"削除対象のMCPサーバー '{server_name}' の設定が見つかりません。")
        return False

    def get_mcp_client_options(self) -> dict:
        """MCPクライアントのオプション設定を取得する"""
        mcp_settings = self.get_mcp_settings()
        return mcp_settings.get("client_options", {})

    def save_mcp_client_options(self, options: dict) -> bool:
        """MCPクライアントのオプション設定を保存する"""
        if "mcp_settings" not in self.config:
            self.config["mcp_settings"] = self.create_default_config()["mcp_settings"]

        self.config["mcp_settings"]["client_options"] = options
        logger.info("MCPクライアントオプションを更新しました。")
        if self.get_system_setting("auto_save", True):
            return self.save_config()
        return True

# ConfigManager の簡単な使用例
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # test_config.json というテスト用の設定ファイルを使用
    test_config_path = "test_aituber_config_mcp.json"
    if os.path.exists(test_config_path):
        os.remove(test_config_path) # テスト前に古いファイルを削除

    config_manager = ConfigManager(config_file=test_config_path)

    logger.info("--- 初期設定値 ---")
    logger.info(f"システム設定: {config_manager.get_all_system_settings()}")
    logger.info(f"MCP設定: {config_manager.get_mcp_settings()}")

    logger.info("\n--- MCPサーバー設定のテスト ---")
    fs_server_conf = config_manager.get_mcp_server_config("filesystem")
    logger.info(f"Filesystemサーバー初期設定: {fs_server_conf}")

    if fs_server_conf:
        fs_server_conf["enabled"] = False # 無効化してみる
        config_manager.save_mcp_server_config("filesystem", fs_server_conf)
        logger.info(f"Filesystemサーバー変更後: {config_manager.get_mcp_server_config('filesystem')}")

    new_server_config = {
        "enabled": True,
        "command": "node",
        "args": ["./mcp_servers/custom_server.js"],
        "env": {},
        "description": "カスタムNode.jsサーバー"
    }
    config_manager.save_mcp_server_config("custom_node_server", new_server_config)
    logger.info(f"追加したカスタムサーバー設定: {config_manager.get_mcp_server_config('custom_node_server')}")
    logger.info(f"全MCPサーバー設定: {config_manager.get_mcp_servers()}")

    config_manager.delete_mcp_server_config("custom_node_server")
    logger.info(f"カスタムサーバー削除後の全MCPサーバー設定: {config_manager.get_mcp_servers()}")

    logger.info("\n--- MCPクライアントオプションのテスト ---")
    client_opts = config_manager.get_mcp_client_options()
    logger.info(f"初期クライアントオプション: {client_opts}")
    client_opts["default_timeout"] = 60
    config_manager.save_mcp_client_options(client_opts)
    logger.info(f"変更後クライアントオプション: {config_manager.get_mcp_client_options()}")

    logger.info(f"\n設定ファイル '{test_config_path}' を確認してください。")
    # os.remove(test_config_path) # テスト後にファイルを削除する場合はコメント解除
    logger.info("テスト完了。")
