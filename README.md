# 完全版 AITuber 制作システム設計書 v2.0 - 実用・無料版

## システム概要

**完全無料で動作する**プロレベルのAITuber制作システムです。Google AI Studio（文章生成） + Avis Speech（音声合成） + システムTTS を統合し、**この設計書通りに進めれば、確実に無料で動作するシステムが構築できます。**

### 主な機能
- **完全GUI操作**: プログラミング知識不要の直感的インターフェース
- **3つの音声エンジン**: Avis Speech・システムTTS・Google Cloud TTS（オプション）
- **キャラクター管理**: 複数キャラクターの作成・切り替え・管理
- **リアルタイム配信**: YouTubeライブとの完全連携
- **完全無料動作**: 基本機能は追加費用なし
- **会話履歴保持機能**: 設定した回数分の直近の会話を記憶し、AIの応答に活用します。(New!)

## 💰 コスト構造（重要な変更点）

### ✅ 完全無料構成（推奨）
- **Google AI Studio**: 月60リクエスト/分（無料枠・文章生成専用）
- **Avis Speech Engine**: 完全無料・ローカル実行・制限なし
- **VOICEVOX Engine**: 完全無料・ローカル実行・制限なし
- **システムTTS**: OS標準機能・完全無料
- **YouTube API**: 1日10,000ユニット（無料枠）

### 💡 高品質オプション構成
- **Google Cloud TTS**: 月100万文字まで無料、以降は有料
- **Azure Cognitive Services**: 月50万文字まで無料

**推奨**: まずは完全無料構成から開始し、必要に応じて高品質オプションを追加

## 📋 事前準備チェックリスト

### ✅ Step 1: Python環境構築

**Python 3.8以上が必要です**

```bash
# Pythonバージョン確認
python --version

# 必要なライブラリをすべてインストール
pip install google-generativeai requests asyncio tkinter pathlib uuid webbrowser tempfile subprocess platform datetime threading logging json time os aiohttp pydub
```

**重要なライブラリ詳細:**
- `google-generativeai`: Google AI Studio API用（文章生成のみ）
- `requests` / `aiohttp`: HTTP通信用（YouTube API、Avis Speech API）
- `pydub`: 音声ファイル処理用
- `tkinter`: GUI（Python標準ライブラリ）

### ✅ Step 2: APIキー取得

#### 2.1 Google AI Studio APIキー（必須・文章生成用）
1. **Google AI Studio**（https://aistudio.google.com/）にアクセス
2. Googleアカウントでログイン
3. **「Get API key」**をクリック
4. **「Create API key in new project」**を選択
5. APIキーをコピー・保存

**制限事項:**
- 無料枠: 月60リクエスト/分、1日1500リクエスト
- 用途: **文章生成のみ**（音声合成は使用しない）

#### 2.2 YouTube Data API v3キー（配信時必須）
1. **Google Cloud Console**（https://console.cloud.google.com/）にアクセス
2. 新規プロジェクト作成または既存選択
3. **「APIとサービス」→「ライブラリ」**
4. **「YouTube Data API v3」**を検索・有効化
5. **「認証情報」→「認証情報を作成」→「APIキー」**
6. APIキーをコピー・保存

#### 2.3 Avis Speech Engine（高品質音声・完全無料）

**Avis Speech Engineのセットアップ:**

**方法1: デスクトップアプリ版（推奨・簡単）**
1. **Avis Speech公式サイト**（https://aivis-project.com/）にアクセス
2. **「AivisSpeechをダウンロード」**をクリック
3. Windows/macOS版をダウンロード・インストール
4. アプリを起動すると自動でHTTP APIサーバーが立ち上がる（ポート10101）

**方法2: Engine単体版（上級者向け）**
1. **GitHub**（https://github.com/Aivis-Project/AivisSpeech-Engine）から取得
2. releases から実行ファイルをダウンロード
3. 解凍して実行

**方法3: Docker版（Linux・サーバー用）**
```bash
# GPU使用の場合
docker run --rm --gpus all -p '10101:10101' \
  -v ~/.local/share/AivisSpeech-Engine:/home/user/.local/share/AivisSpeech-Engine-Dev \
  ghcr.io/aivis-project/aivisspeech-engine:nvidia-latest

# CPU使用の場合
docker run --rm -p '10101:10101' \
  -v ~/.local/share/AivisSpeech-Engine:/home/user/.local/share/AivisSpeech-Engine-Dev \
  ghcr.io/aivis-project/aivisspeech-engine:cpu-latest
```

#### 2.4 VOICEVOX Engine（定番音声・完全無料・オプション）

**VOICEVOX Engineのセットアップ（オプション）:**

**方法1: デスクトップアプリ版**
1. **VOICEVOX公式サイト**（https://voicevox.hiroshiba.jp/）にアクセス
2. **「ダウンロード」**をクリック
3. Windows/macOS/Linux版をダウンロード・インストール
4. アプリを起動すると自動でHTTP APIサーバーが立ち上がる（ポート50021）

**方法2: Engine単体版**
1. **GitHub**（https://github.com/VOICEVOX/voicevox_engine）から取得
2. releases から実行ファイルをダウンロード
3. 解凍して `run.exe` または `run` を実行

**方法3: Docker版**
```bash
docker run --rm -p 50021:50021 voicevox/voicevox_engine:latest
```

**利用可能な音声（例）:**
- ずんだもん（ID: 3）
- 四国めたん（ID: 2）
- 春日部つむぎ（ID: 8）
- 雨晴はう（ID: 10）

### ✅ Step 3: システムTTS設定（完全無料・メイン音声）

#### 3.1 Windows設定
**利用可能な音声:**
- Microsoft Ayumi Desktop（日本語女性）
- Microsoft Ichiro Desktop（日本語男性）
- Microsoft Haruka Desktop（日本語女性）
- Microsoft Zira Desktop（英語女性）

**設定方法:**
1. **「設定」→「時刻と言語」→「音声認識」**
2. **「音声」タブで利用可能な音声を確認**
3. 日本語音声がない場合は言語パックをインストール

#### 3.2 macOS設定
**利用可能な音声:**
- Kyoko（日本語女性）
- Otoya（日本語男性）
- Ava（英語女性）
- Samantha（英語女性）

**設定方法:**
1. **「システム環境設定」→「アクセシビリティ」→「音声読み上げ」**
2. **「システムの声」で利用可能な音声を確認**
3. 日本語音声をダウンロード・インストール

#### 3.3 Linux設定
```bash
# Ubuntu/Debian
sudo apt-get install espeak espeak-ng festival

# CentOS/RHEL
sudo yum install espeak espeak-ng festival

# Arch Linux
sudo pacman -S espeak espeak-ng festival
```

## 🚀 段階的セットアップ手順

### Phase 1: 最小構成での動作確認（15分）

#### 1.1 プログラムファイル準備
1. `complete_aituber_system_v2.py`をダウンロード
2. 同じフォルダに保存

#### 1.2 初回起動テスト
```bash
python complete_aituber_system_v2.py
```

**期待する結果:**
- GUI画面が表示される
- エラーなく起動する
- 「AITuber完全版システム v2.0」タイトルが表示

#### 1.3 システムTTSテスト
1. **「設定」タブ**を開く
2. **「デフォルト音声エンジン」**を**「system_tts」**に設定
3. **「設定を保存」**をクリック
4. **「キャラクター管理」タブ**で**「新規作成」**
5. 任意の名前でキャラクター作成
6. **「デバッグ」タブ**で**「音声テスト」**実行

### Phase 2: Avis Speech Engine連携（30分）

#### 2.1 Avis Speech Engine起動確認
1. **Avis Speech**アプリまたは**Avis Speech Engine**を起動
2. ブラウザで **http://127.0.0.1:10101/docs** にアクセス
3. **Swagger UI**が表示されることを確認
4. `/speakers` エンドポイントでスピーカー一覧を確認

#### 2.2 Avis Speech音声テスト
1. **「キャラクター管理」**で新しいキャラクター作成
2. **音声エンジン**を**「avis_speech」**に設定
3. **音声モデル**を選択（利用可能なスピーカーから）
4. **「デバッグ」タブ**で**「音声テスト」**実行

**期待する結果:**
- Avis Speech Engineによる高品質な音声が再生される
- ローカル実行のためインターネット不要
- エラーなく完了

#### 2.3 VOICEVOX Engine連携（オプション）
1. **VOICEVOX**アプリまたは**VOICEVOX Engine**を起動
2. ブラウザで **http://127.0.0.1:50021/docs** にアクセス
3. **Swagger UI**が表示されることを確認
4. **「キャラクター管理」**で**音声エンジン**を**「voicevox」**に設定してテスト

#### 2.4 Google AI Studio文章生成テスト
1. **「設定」タブ**でGoogle AI Studio APIキーを入力
2. **「デバッグ」タブ**の**「対話テスト」**エリア
3. メッセージを入力して送信
4. AIからの返答と音声再生を確認

**重要**: Google AI Studioは**文章生成のみ**使用します（音声合成は使用しません）

### Phase 3: YouTubeライブ配信連携（30分）

#### 3.1 YouTube配信準備
1. **YouTube Studio**（https://studio.youtube.com/）にアクセス
2. **「ライブ配信を開始」**をクリック
3. 配信タイトル・説明を入力
4. **「チャット」**を有効化
5. **配信URL**からライブID取得（「watch?v=」以降の文字列）

#### 3.2 配信設定
1. AITuberシステムの**「設定」タブ**
2. **「YouTube APIキー」**を入力
3. **「設定を保存」**
4. **「メイン」タブ**で**「YouTube ライブID」**を入力

#### 3.3 配信テスト
1. **「配信開始」**ボタンをクリック
2. YouTube配信画面でチャットにメッセージ投稿
3. AITuberが反応することを確認

## 🛠️ デバッグとテスト

### 音声合成フォールバック機能のテスト方法

本システムには、設定された音声エンジンが利用できない場合に、別のエンジンに自動的に切り替わるフォールバック機能が搭載されています。この機能が正しく動作するかは、以下の手順で手動で確認できます。

1.  **デバッグタブの確認**:
    *   AITuberシステムのGUIの「デバッグ」タブを開きます。
    *   「⚠️ フォールバック手動テスト案内」というボタンがあります。このボタン自体はテストを実行しませんが、クリックするとテストの手順に関する簡単な案内が表示されます。

2.  **エラー状況の意図的な作成**:
    *   いずれかの音声エンジンを意図的に利用不可な状態にします。
        *   **例1（ローカルエンジン）**: VOICEVOX Engine や Avis Speech Engine を使用している場合、それらのアプリケーションを一時的に終了します。
        *   **例2（APIベースのエンジン）**: Google AI Studio 新音声などAPIを利用するエンジンの場合、設定タブで該当するAPIキーを一時的に無効な文字列に変更します（テスト後は元に戻してください）。

3.  **キャラクター設定の確認**:
    *   「キャラクター管理」タブで、テストに使用するキャラクターを選択（または作成）し、そのキャラクターの音声設定を開きます。
    *   「音声エンジン」として、上記ステップ2で利用不可にしたエンジンが優先的に使用されるように設定します（または、システムのデフォルト音声エンジン設定がそうなっていることを確認します）。
    *   音声エンジンの優先順位は `VoiceEngineManager` クラス内の `priority` リストで定義されており、通常は `["google_ai_studio_new", "avis_speech", "voicevox", "system_tts"]` の順になっています。

4.  **音声合成の実行**:
    *   デバッグタブの「音声テスト」機能で任意のテキストを合成してみるか、「AI対話テスト」でメッセージを送信してAIに発話させてみます。

5.  **結果の確認**:
    *   コンソールログ（ターミナルやコマンドプロンプトの出力）を確認します。
    *   最初に試行したエンジン（利用不可にしたエンジン）でエラーが発生し、次に優先順位の高い利用可能なエンジンにフォールバックして音声が正常に再生されれば、フォールバック機能は正しく動作しています。
    *   例えば、「🔄 音声合成試行: voicevox」→「⚠️ voicevox は利用できません」→「🔄 音声合成試行: system_tts」→「✅ 音声合成成功: system_tts」のようなログが出力されます。

**重要な注意点**:
*   このフォールバック処理（`VoiceEngineManager.synthesize_with_fallback` メソッドによる制御）は、メインの配信処理中やデバッグタブでのチャットテスト時の音声合成でも共通して使用されます。したがって、上記の手順でのテストは、実際の配信時などのフォールバック動作の確認にも繋がります。
*   テスト後は、意図的に変更した設定（APIキーやローカルエンジンの状態など）を元に戻すことを忘れないでください。

## 🎯 音声エンジン比較・選択指針

### 推奨使い分け

| エンジン | 品質 | コスト | 用途 | 制限 | ポート |
|----------|------|--------|------|------|--------|
| **Avis Speech Engine** | ★★★★☆ | 完全無料 | メイン配信・高品質 | ローカル実行 | 10101 |
| **VOICEVOX Engine** | ★★★☆☆ | 完全無料 | 定番キャラ・安定 | ローカル実行 | 50021 |
| **システムTTS** | ★★☆☆☆ | 完全無料 | テスト・フォールバック | OS依存 | - |
| **Google Cloud TTS** | ★★★★★ | 有料 | プロ品質・商用 | 月額課金 | API |

### デフォルト設定（推奨）
1. **メイン配信**: Avis Speech Engine
2. **キャラクター系**: VOICEVOX Engine（ずんだもん等）
3. **テスト・フォールバック**: システムTTS
4. **商用・プロ品質**: Google Cloud TTS（オプション）

### 音声エンジン自動フォールバック
- **第1優先**: Avis Speech Engine（ポート10101に接続試行）
- **第2優先**: VOICEVOX Engine（ポート50021に接続試行）
- **第3優先**: システムTTS（OS標準TTS）

## 🎮 キャラクター表示システム連携

### VSeeFace連携（VRM用・推奨）

#### 4.1 VSeeFace設定
1. **VSeeFace公式サイト**からダウンロード・インストール
2. VRoid Studioで作成したVRMファイルを読み込み
3. **「General settings」→「OSC/VMC protocol」**を有効化

#### 4.2 音声リップシンク設定
1. **「Microphone settings」**で**「System audio」**を選択
2. **「Voice activity detection」**の感度調整
3. AITuberの音声にリアルタイムでリップシンク

### OBS Studio連携

#### 5.1 OBS設定
1. **OBS Studio**で**「ソース追加」→「ゲームキャプチャ」**
2. **「VSeeFace」**を選択
3. **「透過を許可」**にチェック
4. 背景・装飾を追加

## ⚠️ よくある問題と解決方法

### エラー1: Google AI Studio音声エラー
```
Google Gemini TTS エラー: 400 This model only supports text output.
```
**解決方法:**
- ✅ **修正済み**: v2.0ではGoogle AI Studioは文章生成のみ使用
- 音声合成はAvis Speech / システムTTSを使用

### エラー2: Avis Speech接続失敗
```
❌ Avis Speech接続エラー
```
**解決方法:**
1. インターネット接続を確認
2. Avis Speechサイトの稼働状況を確認
3. システムTTSにフォールバック

### エラー3: 音声が再生されない
**解決方法:**
1. **音声エンジン**を**「system_tts」**に変更してテスト
2. システム音量・音声出力デバイス確認
3. ファイアウォール・セキュリティソフト確認

### エラー4: キャラクターモデルが動かない
**解決方法:**
1. **VSeeFace/VTube Studio**が正常に起動しているか確認
2. **音声入力設定**でシステム音声が検出されているか確認
3. **マイク感度**を調整

## 🎉 運用のベストプラクティス

### 配信品質向上
- **解像度**: 1080p/30fps推奨
- **音声品質**: 48kHz/16bit以上
- **遅延**: エンドツーエンド3秒以内を目標

### パフォーマンス最適化
- **メモリ使用量**: 2GB以下を維持
- **CPU使用率**: 70%以下で安定動作
- **ネットワーク**: 上り1Mbps以上推奨

### コスト最適化
- **基本配信**: システムTTS + Avis Speech（完全無料）
- **高品質配信**: Google Cloud TTS追加（月額10-30ドル程度）
- **プロ配信**: 全エンジン利用（月額50-100ドル程度）

## 📈 段階的機能拡張

### Level 1: 完全無料配信
- システムTTS + Avis Speechでの基本配信
- 単一キャラクターでの雑談配信
- 月額コスト: **0円**

### Level 2: 高品質配信
- 複数キャラクターの使い分け
- VSeeFace/VTube Studioとの連携
- 月額コスト: **0円**（無料枠内）

### Level 3: プロレベル配信
- Google Cloud TTS追加
- 多言語対応
- 月額コスト: **10-30ドル**

### Level 4: 商用レベル
- 企業案件・スポンサー対応
- マルチプラットフォーム配信
- 月額コスト: **50-100ドル**

## 🛠️ 開発・カスタマイズ

### 設定ファイル構造
```json
{
  "system_settings": {
    "google_ai_api_key": "your_api_key_here",
    "youtube_api_key": "your_youtube_key_here",
    "voice_engine": "avis_speech",
    "auto_save": true,
    "conversation_history_length": 0 // 会話履歴の保持数 (0は記憶なし、1以上でその回数分の直近の会話を記憶) (New!)
  },
  "characters": {
    "character_001": {
      "name": "AIちゃん",
      "personality": {...},
      "voice_settings": {
        "engine": "avis_speech",
        "model": "female_1",
        "speed": 1.0
      }
    }
  }
}
```

### 音声エンジン優先順位設定
```python
# 推奨設定
voice_engine_priority = [
    "avis_speech",    # 高品質・無料
    "system_tts",     # 基本品質・無料
    "google_cloud"    # 最高品質・有料
]
```

## 🆓 完全無料で始める最短ルート

### 必要なもの（すべて無料）
1. **Google AI Studio APIキー**（文章生成・無料枠）
2. **YouTube APIキー**（配信・無料枠）
3. **Avis Speechアカウント**（音声合成・完全無料）
4. **VRoid Studio**（キャラクター作成・無料）
5. **VSeeFace**（キャラクター表示・無料）
6. **OBS Studio**（配信・無料）

### 30分でできる最短セットアップ
1. **5分**: Python環境構築
2. **5分**: APIキー取得
3. **10分**: システム起動・テスト
4. **10分**: キャラクター作成・音声テスト

この設計書通りに進めれば、**完全無料で本格的なAITuberシステム**が構築できます。まずは無料構成から始めて、必要に応じて高品質オプションを追加していく段階的なアプローチがおすすめです。
