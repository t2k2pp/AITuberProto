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


# キャラクター管理システム v2.2（4エンジン完全対応版）
class CharacterManager:
    """キャラクター作成・編集・管理システム v2.2（4エンジン完全対応・機能削減なし）"""

    def __init__(self, config_manager):
        self.config = config_manager
        self.character_templates = self._load_templates()

    def _load_templates(self):
        """キャラクターテンプレート定義 v2.2（4エンジン完全対応）"""
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
                    "model": "puck", # GoogleAIStudioNewVoiceAPIで定義された短いモデル名
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
                    "model": "achernar", # GoogleAIStudioNewVoiceAPIで定義された短いモデル名 (puck以外で例示)
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
                    "model": "vindemiatrix", # GoogleAIStudioNewVoiceAPIで定義された短いモデル名 (puck以外で例示)
                    "speed": 1.0
                }
            }
        }

    def create_character(self, name, template_name=None, custom_settings=None):
        """新しいキャラクターを作成 v2.2（完全版）"""
        char_id = str(uuid.uuid4())

        if template_name and template_name in self.character_templates:
            char_data = self.character_templates[template_name].copy() # copy() を使用してテンプレートの変更を防ぐ
            # テンプレートからロードした場合でも、不足している可能性のあるキーをデフォルトで補完
            # 特に voice_settings は重要
            default_blank = self._create_blank_character()
            if "voice_settings" not in char_data:
                char_data["voice_settings"] = default_blank["voice_settings"].copy()
            else: # voice_settings が存在する場合でも、個別のキーが不足している可能性を考慮
                for key, value in default_blank["voice_settings"].items():
                    if key not in char_data["voice_settings"]:
                        char_data["voice_settings"][key] = value

            if "personality" not in char_data:
                char_data["personality"] = default_blank["personality"].copy()
            else:
                for key, value in default_blank["personality"].items():
                    if key not in char_data["personality"]:
                        char_data["personality"][key] = value

            if "response_settings" not in char_data:
                char_data["response_settings"] = default_blank["response_settings"].copy()
            else:
                for key, value in default_blank["response_settings"].items():
                    if key not in char_data["response_settings"]:
                        char_data["response_settings"][key] = value
        else:
            char_data = self._create_blank_character()

        char_data["name"] = name
        char_data["created_at"] = datetime.now().isoformat()
        char_data["char_id"] = char_id
        char_data["version"] = "2.2" # バージョン情報を付与

        # カスタム設定を適用（テンプレート適用後にカスタム設定で上書き）
        if custom_settings:
            # ネストされた辞書も考慮して深くマージする (ここでは単純な update を使用)
            # より複雑なマージが必要な場合は、専用のユーティリティ関数を検討
            if "personality" in custom_settings and isinstance(custom_settings["personality"], dict):
                if "personality" not in char_data: char_data["personality"] = {}
                char_data["personality"].update(custom_settings.pop("personality"))
            if "voice_settings" in custom_settings and isinstance(custom_settings["voice_settings"], dict):
                if "voice_settings" not in char_data: char_data["voice_settings"] = {}
                char_data["voice_settings"].update(custom_settings.pop("voice_settings"))
            if "response_settings" in custom_settings and isinstance(custom_settings["response_settings"], dict):
                if "response_settings" not in char_data: char_data["response_settings"] = {}
                char_data["response_settings"].update(custom_settings.pop("response_settings"))
            char_data.update(custom_settings) # 残りのトップレベルキーを更新

        self.config.save_character(char_id, char_data)
        return char_id

    def _create_blank_character(self):
        """空のキャラクタープレート v2.2（完全版）"""
        return {
            "name": "", # 名前は create_character で設定される
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
                "engine": "google_ai_studio_new", # デフォルトエンジン（最新）
                "model": "puck",                   # GoogleAIStudioNewVoiceAPIのデフォルト的な短いモデル名
                "speed": 1.0,
                "volume": 1.0 # volume は現状の音声エンジンでは直接使われていないが、将来的な拡張性のため
            }
            # char_id, created_at, version などは create_character で付与
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

    def get_character(self, char_id):
        """キャラクターIDからキャラクターデータを取得する。"""
        return self.config.get_character(char_id)

    def get_all_characters(self):
        """保存されている全てのキャラクターデータを辞書として返す。"""
        return self.config.get_all_characters()

    def get_character_id_by_name(self, char_name):
        """キャラクター名からキャラクターIDを取得する。"""
        all_chars = self.get_all_characters()
        for char_id, char_data in all_chars.items():
            if char_data.get("name") == char_name:
                return char_id
        return None

    def delete_character(self, char_id):
        """
        指定されたキャラクターIDのキャラクターを削除する。
        実際にはConfigManagerのdelete_characterメソッドを呼び出す。
        """
        try:
            if self.config.delete_character(char_id):
                # logging.info(f"キャラクター (ID: {char_id}) の削除に成功しました。") # CharacterManagerではロギングしない方針の場合
                return True
            else:
                # logging.warning(f"キャラクター (ID: {char_id}) の削除に失敗しました。IDが存在しない可能性があります。")
                return False
        except Exception as e:
            # logging.error(f"キャラクター (ID: {char_id}) の削除中にエラーが発生しました: {e}", exc_info=True)
            print(f"キャラクター (ID: {char_id}) の削除中にエラーが発生しました: {e}") # GUIがない場合はprint
            return False
