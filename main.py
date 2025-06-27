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
from tkinter import messagebox
from gui import AITuberMainGUI

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


# main.py の内容

import tkinter as tk
from tkinter import messagebox
from gui import AITuberMainGUI

def main():
    """アプリケーションのエントリーポイント"""
    try:
        app = AITuberMainGUI()
        app.run()
    except Exception as e:
        print(f"❌ アプリケーション起動エラー: {e}")
        # GUIが初期化される前のエラーはコンソールにしか表示されない可能性がある
        # 起動プロセスの早い段階で発生するエラーを考慮
        try:
            # Tkinterのrootウィンドウが作成される前にエラーが発生した場合、
            # messageboxは表示できないため、基本的なエラーウィンドウを作成する試み
            root = tk.Tk()
            root.withdraw() # メインウィンドウは表示しない
            messagebox.showerror("起動エラー", f"アプリケーションの起動に失敗しました:\n{e}")
        except tk.TclError:
            # Tkinterが利用不可能な環境の場合
            pass # コンソール出力のみ

if __name__ == "__main__":
    main()

# AITuberStreamingSystem クラス定義後の main() と if __name__ == "__main__": は削除。
# ファイル末尾のものが正。

# def main():
#     """アプリケーションのエントリーポイント"""
#     try:
#         app = AITuberMainGUI()
#         app.run()
#     except Exception as e:
#         print(f"❌ アプリケーション起動エラー: {e}")
#         messagebox.showerror("起動エラー", f"アプリケーションの起動に失敗しました:\n{e}")

# if __name__ == "__main__":
#     main()
