import tkinter as tk
from tkinter import ttk
import webbrowser

class HelpWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("ヘルプ - エンジン起動ガイド")
        self.root.geometry("700x550") # 少し広め

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- gui.py の create_settings_tab 内のヘルプ部分を参考にUI要素を配置 ---
        help_content_frame = ttk.LabelFrame(main_frame, text="エンジン起動ガイド v2.2（4エンジン完全対応）", padding="10")
        help_content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        guide_text_widget = tk.Text(help_content_frame, height=18, width=80, wrap=tk.WORD, state=tk.DISABLED, relief=tk.FLAT, bg=self.root.cget('bg'))
        guide_scroll = ttk.Scrollbar(help_content_frame, orient=tk.VERTICAL, command=guide_text_widget.yview)
        guide_text_widget.configure(yscrollcommand=guide_scroll.set)

        guide_text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        guide_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        guide_content = """
🚀 【Google AI Studio新音声】- 2025年5月追加・最新技術
設定: Google AI Studio APIキーを設定するだけ（Gemini 2.5 Flash新音声機能使用）
品質: 最新技術・リアルタイム対応・多言語・高音質・感情表現対応
特徴: Alloy, Echo, Fable, Onyx, Nova, Shimmer等の最新音声モデル
利点: 高度な表現力とリアルタイム性。クラウドベースで常に最新。
注意点: APIキーが必要。インターネット接続必須。利用量に応じた課金の可能性。

🎙️ 【Avis Speech Engine】- ポート10101
起動: AvisSpeechアプリを起動 または docker run -p 10101:10101 aivisspeech/aivis-speech-engine (イメージ名確認)
確認: http://127.0.0.1:10101/docs (ブラウザでアクセス)
特徴: 高品質な日本語音声合成。VOICEVOX互換API。感情表現対応。
利点: ローカル実行可能で無料。VOICEVOXキャラクターも利用可能な場合あり。
注意点: 事前にエンジンを起動しておく必要あり。PCのリソースを消費。

🎤 【VOICEVOX Engine】- ポート50021
起動: VOICEVOXアプリを起動 または docker run -p 50021:50021 voicevox/voicevox_engine
確認: http://127.0.0.1:50021/docs (ブラウザでアクセス)
特徴: ずんだもん・四国めたん等の人気キャラクター音声が豊富。
利点: ローカル実行可能で無料。多様なキャラクターとスタイル。コミュニティが活発。
注意点: 事前にエンジンを起動しておく必要あり。PCのリソースを消費。

💻 【システムTTS】- OS標準
設定: 不要（Windows/macOS/Linuxの標準TTS機能を自動利用）
特徴: 完全無料・オフライン動作可能・安定性が高い。
利点: 追加インストール不要ですぐ使える。インターネット接続不要。
注意点: 音質や表現力は上記専用エンジンに劣る場合が多い。利用できる音声はOSに依存。

【一般的なトラブルシューティング】
- 音声が出ない:
    - 各エンジンの起動状態とポート設定を確認してください。
    - 設定画面で正しい音声出力デバイスが選択されているか確認してください。
    - キャラクター設定で、選択したエンジンに対応する有効な音声モデルが選ばれているか確認してください。
- APIエラーが出る:
    - Google AI Studio APIキーが正しく設定されているか確認してください。
    - インターネット接続を確認してください。
    - APIの利用上限に達していないか確認してください。
- その他:
    - アプリケーションのログ（メイン画面やコンソール）にエラーメッセージが出ていないか確認してください。
"""
        guide_text_widget.config(state=tk.NORMAL)
        guide_text_widget.delete(1.0, tk.END) # 念のためクリア
        guide_text_widget.insert(tk.END, guide_content.strip())
        guide_text_widget.config(state=tk.DISABLED)

        # 外部リンクボタンフレーム
        link_frame = ttk.Frame(main_frame) # main_frameに配置
        link_frame.pack(pady=10)

        buttons_info = [
            ("🎨 VRoid Studio", "https://vroid.com/studio"),
            ("📹 VSeeFace", "https://www.vseeface.icu/"),
            ("🎙️ Avis Speech", "https://github.com/Aivis-Project/AivisSpeech-Engine"), # 正しいURLに修正
            ("🎤 VOICEVOX", "https://voicevox.hiroshiba.jp/") # 公式サイト
        ]

        for text, url in buttons_info:
            button = ttk.Button(link_frame, text=text, command=lambda u=url: webbrowser.open(u))
            button.pack(side=tk.LEFT, padx=5, pady=5)

        # 閉じるボタン
        close_button = ttk.Button(main_frame, text="閉じる", command=self.root.destroy)
        close_button.pack(pady=10)


def main():
    root = tk.Tk()
    app = HelpWindow(root)
    root.mainloop()

if __name__ == "__main__":
    main()
