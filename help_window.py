import customtkinter
import tkinter as tk # 基本的な型 (StringVarなど) と標準ダイアログのため
import webbrowser
import sys # フォント選択のため
import json # JSON読み込み用
from PIL import Image, ImageTk # アイコン表示用 (CTkImageのため)
import os # ファイルパス操作用 (将来的にアイコンなどをローカルから読む場合)
import requests # Web上の画像取得用
import io # BytesIOのため

class HelpWindow:
    def __init__(self, root: customtkinter.CTk):
        self.root = root
        self.root.title("ヘルプ")
        self.root.geometry("800x700")

        # フォント設定
        self.default_font = ("Yu Gothic UI", 12)
        if sys.platform == "darwin": self.default_font = ("Hiragino Sans", 14)
        elif sys.platform.startswith("linux"): self.default_font = ("Noto Sans CJK JP", 12)
        self.label_font = (self.default_font[0], self.default_font[1] + 1, "bold")
        self.text_font = (self.default_font[0], self.default_font[1] -1)

        self.voice_model_data: list[dict] = [] # JSONから読み込んだ音声モデルデータ全体
        self.filtered_voice_model_data: list[dict] = [] # フィルタ/検索後のデータ
        self.current_selected_model_index = None # model_list_frame内のリストでの選択インデックス

        self.loading_label = customtkinter.CTkLabel(self.root, text="読み込み中...", font=("Yu Gothic UI", 18))
        self.loading_label.pack(expand=True, fill="both")
        self.root.update_idletasks()

        self.root.after(50, self._initialize_components)

    def _initialize_components(self):
        if hasattr(self, 'loading_label') and self.loading_label.winfo_exists():
            self.loading_label.pack_forget()
            self.loading_label.destroy()

        self.load_voice_models_data() # JSONデータ読み込み
        self.create_widgets()
        self.populate_engine_filter()
        self._update_model_list()
        # HelpWindow には log メソッドがないため、ここでログ出力はなし

    def load_voice_models_data(self):
        """
        voice_models.json ファイルから音声モデルデータを読み込み、self.voice_model_data に格納する。
        ファイルパスはスクリプトの場所、PyInstallerバンドル内、プロジェクトルート直下を探索する。
        """
        try:
            # PyInstallerでバンドルされた場合、sys._MEIPASSがリソースのある一時フォルダを指す
            # 通常実行時はスクリプトのディレクトリを基準にする
            base_dir = os.path.dirname(os.path.abspath(__file__))
            json_path = os.path.join(base_dir, "voice_models.json")

            # もしリソースディレクトリが別に設定されている場合 (例: sys._MEIPASS)
            if hasattr(sys, '_MEIPASS'):
                json_path_alt = os.path.join(sys._MEIPASS, "voice_models.json")
                if os.path.exists(json_path_alt):
                    json_path = json_path_alt

            if not os.path.exists(json_path):
                 # 開発時など、プロジェクトルート直下に置いている場合も考慮
                project_root_json_path = os.path.join(os.path.dirname(base_dir), "voice_models.json")
                if os.path.exists(project_root_json_path):
                    json_path = project_root_json_path
                else:
                    print(f"Error: voice_models.json not found at {json_path}, {project_root_json_path} or in MEIPASS.")
                    self.voice_model_data = []
                    # エラーダイアログを出すことも検討
                    # messagebox.showerror("エラー", "音声モデル定義ファイル voice_models.json が見つかりません。")
                    return

            with open(json_path, "r", encoding="utf-8") as f:
                self.voice_model_data = json.load(f)
        except FileNotFoundError:
            print(f"Error: voice_models.jsonが見つかりません。Checked path: {json_path}")
            self.voice_model_data = []
        except json.JSONDecodeError:
            print(f"Error: voice_models.json の解析に失敗しました。Path: {json_path}")
            self.voice_model_data = []
        except Exception as e:
            print(f"Error loading voice_models.json: {e}")
            self.voice_model_data = []
            # TODO: ユーザーにエラーダイアログを表示することを検討 (例: messagebox.showerror)

    def populate_engine_filter(self):
        """
        読み込んだ音声モデルデータからエンジン名のリストを作成し、
        エンジンフィルター用ComboBoxの選択肢を更新する。
        """
        if not self.voice_model_data:
            self.engine_filter_combo.configure(values=["すべて"]) # データがない場合でも選択肢は設定
            self.engine_filter_var.set("すべて")
            return

        engine_names = sorted(list(set(model.get("engine_name", "不明") for model in self.voice_model_data)))
        self.engine_filter_combo.configure(values=["すべて"] + engine_names)
        self.engine_filter_var.set("すべて")


    def _update_model_list(self, event=None):
        """
        現在のフィルター条件（エンジン名、検索語）に基づいて音声モデルのリストを更新する。
        model_list_frame 内のリストアイテムを再構築し、該当がなければメッセージを表示する。
        リスト更新後、最初のアイテムが選択されるか、詳細表示がクリアされる。
        """
        # 既存のリストアイテムをクリア
        for widget in self.model_list_frame.winfo_children():
            widget.destroy()

        selected_engine = self.engine_filter_var.get()
        search_term = self.search_var.get().lower()

        self.filtered_voice_model_data = []
        for model in self.voice_model_data:
            engine_match = (selected_engine == "すべて" or model.get("engine_name") == selected_engine)

            name_jp = model.get("model_name_jp", "").lower()
            name_en = model.get("model_name_en", "").lower()
            # features や character_info も検索対象に含めるか検討
            search_match = (search_term == "" or
                            search_term in name_jp or
                            search_term in name_en or
                            search_term in model.get("features", "").lower() or
                            search_term in model.get("character_info", "").lower()
                           )

            if engine_match and search_match:
                self.filtered_voice_model_data.append(model)

        if not self.filtered_voice_model_data:
            customtkinter.CTkLabel(self.model_list_frame, text="該当するモデルはありません。", font=self.text_font).pack(padx=5, pady=5)
            self._clear_details() # 詳細表示もクリア
            return

        for index, model_data in enumerate(self.filtered_voice_model_data):
            model_display_name = f"{model_data.get('model_name_jp', 'N/A')} ({model_data.get('model_name_en', 'N/A')})"
            item_button = customtkinter.CTkButton(self.model_list_frame, text=model_display_name,
                                                 command=lambda i=index: self._on_model_selected(i),
                                                 font=self.text_font, anchor="w")
            item_button.pack(fill="x", padx=2, pady=1)

        if self.filtered_voice_model_data:
            self._on_model_selected(0) # リスト更新後、最初のアイテムを選択状態にする
        else:
            self._clear_details()


    def _on_model_selected(self, index_in_filtered_list: int):
        """
        音声モデルリストで特定のアイテムが選択されたときの処理。
        選択されたモデルの詳細を表示し、リスト内の選択状態をハイライトする。
        """
        self.current_selected_model_index = index_in_filtered_list
        if 0 <= index_in_filtered_list < len(self.filtered_voice_model_data):
            model_to_display = self.filtered_voice_model_data[index_in_filtered_list]
            self._display_model_details(model_to_display)

            # 選択されたボタンの見た目を変える
            for i, child in enumerate(self.model_list_frame.winfo_children()):
                if isinstance(child, customtkinter.CTkButton): # ラベルなどを除外
                    is_selected = (i == index_in_filtered_list)
                    current_fg_color = customtkinter.ThemeManager.theme["CTkButton"]["fg_color"]
                    hover_color = customtkinter.ThemeManager.theme["CTkButton"]["hover_color"]

                    # CTkButton の fg_color はタプル (light_color, dark_color) の場合がある
                    if isinstance(current_fg_color, tuple):
                        selected_color = hover_color[customtkinter.get_appearance_mode() == "Dark"] if isinstance(hover_color, tuple) else hover_color
                        default_color = current_fg_color[customtkinter.get_appearance_mode() == "Dark"]
                    else: # 文字列の場合
                        selected_color = hover_color
                        default_color = current_fg_color

                    child.configure(fg_color=selected_color if is_selected else default_color)
        else:
            self._clear_details()

    def _clear_details(self):
        """右ペインの詳細表示エリアの内容をすべてクリア（初期状態に）する。"""
        self.detail_model_name_jp_var.set("")
        self.detail_model_name_en_var.set("")
        self.detail_engine_name_var.set("")
        self.detail_features_var.set("")
        self.detail_gender_impression_var.set("")
        self.detail_commercial_use_var.set("")
        self.detail_character_info_var.set("")
        self.detail_terms_url_var.set("")
        self.detail_terms_button.configure(state="disabled", text="規約URLなし")

        if hasattr(self, 'detail_icon_label') and self.detail_icon_label:
            self.detail_icon_label.configure(image=None)
            self.detail_icon_label.image = None # 参照を保持させない
        if hasattr(self, 'detail_sample_button') and self.detail_sample_button:
            self.detail_sample_button.configure(state="disabled", text="サンプル音声再生")


    def _display_model_details(self, model_data: dict):
        """
        指定された音声モデルのデータを右ペインの詳細表示エリアに表示する。
        アイコンの読み込み・表示、規約URLボタン、サンプル音声ボタンの制御も行う。
        """
        self._clear_details() # 表示前に一旦クリア
        self.detail_model_name_jp_var.set(model_data.get("model_name_jp", "N/A"))
        self.detail_model_name_en_var.set(model_data.get("model_name_en", "N/A"))
        self.detail_engine_name_var.set(model_data.get("engine_name", "N/A"))
        self.detail_features_var.set(model_data.get("features", "情報なし"))
        self.detail_gender_impression_var.set(model_data.get("gender_impression", "情報なし"))
        self.detail_commercial_use_var.set(model_data.get("commercial_use", "情報なし"))
        self.detail_character_info_var.set(model_data.get("character_info", "情報なし"))

        terms_url = model_data.get("terms_url", "")
        if terms_url and terms_url.startswith("http"):
            self.detail_terms_url_var.set(terms_url) # ボタンのtext変数ではないので直接セット
            self.detail_terms_button.configure(state="normal", text=terms_url) # ボタンテキストも更新
        else:
            self.detail_terms_url_var.set("")
            self.detail_terms_button.configure(state="disabled", text="規約URLなし")

        # アイコン表示 (Pillow と CTkImage を使用)
        # 注意: requests.getはUIスレッドをブロックする可能性があります。
        # 大量の画像や遅いネットワークでは非同期処理やスレッド化を検討すべきです。
        icon_url = model_data.get("icon_url", "")
        loaded_image = None
        if icon_url:
            try:
                if icon_url.startswith("http"): # ウェブ上の画像
                    headers = {'User-Agent': 'Mozilla/5.0'} # 一部のサーバーでUAがないと403になる対策
                    response = requests.get(icon_url, stream=True, timeout=10, headers=headers)
                    response.raise_for_status() # HTTPエラーチェック
                    image_data = response.content
                    pil_image = Image.open(io.BytesIO(image_data))
                    loaded_image = pil_image
                elif os.path.isabs(icon_url) and os.path.exists(icon_url): # 絶対パスの場合
                    pil_image = Image.open(icon_url)
                    loaded_image = pil_image
                else: # 相対パス、または MEIPASS 内のリソースの可能性
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                    local_icon_path = os.path.join(base_dir, icon_url)
                    resource_path_meipass = os.path.join(getattr(sys, '_MEIPASS', base_dir), icon_url)

                    if os.path.exists(local_icon_path):
                        pil_image = Image.open(local_icon_path)
                        loaded_image = pil_image
                    elif hasattr(sys, '_MEIPASS') and os.path.exists(resource_path_meipass):
                        pil_image = Image.open(resource_path_meipass)
                        loaded_image = pil_image
                    else:
                        print(f"Local icon file not found: {icon_url}, {local_icon_path}, {resource_path_meipass}")
            except requests.exceptions.RequestException as e:
                print(f"Error fetching icon from URL {icon_url}: {e}")
            except FileNotFoundError:
                print(f"Icon file not found: {icon_url}")
            except Exception as e:
                print(f"Error processing icon {icon_url}: {e}")

        if loaded_image:
            try:
                # RGBAでない場合、背景透過がおかしくなることがあるので変換を試みる
                if loaded_image.mode != 'RGBA':
                    loaded_image = loaded_image.convert('RGBA')
                resized_image = self._resize_image_aspect_ratio(loaded_image, 120, 120) # サイズ少し大きく
                ctk_image = customtkinter.CTkImage(light_image=resized_image, dark_image=resized_image, size=(resized_image.width, resized_image.height))
                self.detail_icon_label.configure(image=ctk_image, text="")
                self.detail_icon_label.image = ctk_image
            except Exception as e:
                print(f"Error creating CTkImage for {icon_url}: {e}")
                self.detail_icon_label.configure(image=None, text="画像表示エラー")
                self.detail_icon_label.image = None
        else:
            self.detail_icon_label.configure(image=None, text="アイコンなし")
            self.detail_icon_label.image = None

        # サンプル音声再生ボタン
        sample_url = model_data.get("sample_voice_url", "")
        if sample_url and sample_url.startswith("http"):
            self.detail_sample_button.configure(state="normal", command=lambda u=sample_url: webbrowser.open(u))
        else:
            self.detail_sample_button.configure(state="disabled")

    def _resize_image_aspect_ratio(self, pil_image: Image.Image, max_width: int, max_height: int) -> Image.Image:
        """
        PILイメージを指定された最大幅・高さにアスペクト比を維持してリサイズする。
        画像が最大サイズより小さい場合はリサイズしない。
        """
        img_width, img_height = pil_image.size
        if img_width == 0 or img_height == 0:
            return pil_image

        ratio = min(max_width / img_width, max_height / img_height)
        if ratio < 1: # 画像が最大サイズを超える場合のみリサイズ
            new_width = int(img_width * ratio)
            new_height = int(img_height * ratio)
            try:
                if hasattr(Image, 'Resampling') and hasattr(Image.Resampling, 'LANCZOS'):
                    pil_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                else:
                    pil_image = pil_image.resize((new_width, new_height), Image.LANCZOS)
            except Exception as e:
                print(f"Error resizing image: {e}")
        return pil_image

    def create_widgets(self):
        # メインフレームの代わりにタブビューを使用
        tab_view = customtkinter.CTkTabview(self.root)
        tab_view.pack(padx=10, pady=10, fill="both", expand=True)

        # 各タブを作成
        tab_engine_guide = tab_view.add("エンジン起動ガイド")
        tab_engine_description = tab_view.add("音声エンジン説明")
        tab_new_voice_catalog = tab_view.add("音声カタログ") # 新しいタブ
        tab_youtube_live = tab_view.add("YouTube Live手順")
        tab_ai_theater = tab_view.add("AI劇場手順")
        tab_ai_chat = tab_view.add("AIチャット手順")
        tab_settings_guide = tab_view.add("設定画面の説明")

        # --- エンジン起動ガイドタブ ---
        engine_guide_frame = customtkinter.CTkScrollableFrame(tab_engine_guide)
        engine_guide_frame.pack(fill="both", expand=True, padx=10, pady=10) # padx, pady変更

        customtkinter.CTkLabel(engine_guide_frame, text="エンジン起動ガイド v2.2（4エンジン完全対応）", font=self.label_font).pack(anchor="w", padx=10, pady=(5,5))

        guide_content = """
【ヘルプウィンドウの構成】
このヘルプウィンドウは複数のタブで構成されています。
- **エンジン起動ガイド:** 各音声エンジンの基本的な起動方法とトラブルシューティング。 (現在のタブ)
- **音声エンジン説明:** 各音声エンジンのより詳細な説明（特徴、コスト感など）。
- **音声カタログ:** 利用可能な個別の音声モデル（キャラクターボイス等）の特徴や利用規約を検索・確認できます。JSONファイルでデータ管理されており、ユーザーによる追加・編集も可能です。
- **YouTube Live手順:** YouTube Liveでコメント読み上げを利用する際の手順。
- **AI劇場手順:** AI劇場（寸劇作成）機能の利用手順。
- **AIチャット手順:** AIとの対話機能の利用手順。
- **設定画面の説明:** アプリケーション設定画面の各項目の説明。

---

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
        guide_text_widget = customtkinter.CTkTextbox(engine_guide_frame, wrap="word", font=self.text_font)
        guide_text_widget.pack(fill="both", expand=True, padx=5, pady=5)
        guide_text_widget.insert("1.0", guide_content.strip())
        guide_text_widget.configure(state="disabled")

        # 外部リンクボタンフレーム (エンジン起動ガイドタブ内)
        link_frame = customtkinter.CTkFrame(engine_guide_frame, fg_color="transparent")
        link_frame.pack(pady=10)

        buttons_info = [
            ("🎨 VRoid Studio", "https://vroid.com/studio"),
            ("📹 VSeeFace", "https://www.vseeface.icu/"),
            ("🎙️ Avis Speech", "https://github.com/Aivis-Project/AivisSpeech-Engine"),
            ("🎤 VOICEVOX", "https://voicevox.hiroshiba.jp/")
        ]

        for text, url in buttons_info:
            button = customtkinter.CTkButton(link_frame, text=text, command=lambda u=url: webbrowser.open(u), font=self.default_font)
            button.pack(side="left", padx=5, pady=5)

        # --- 他のタブのプレースホルダー ---
        # --- 音声エンジン説明タブ --- # 名称変更
        engine_description_frame = customtkinter.CTkScrollableFrame(tab_engine_description) # 変数名変更
        engine_description_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Google AI Studio
        google_ai_frame = customtkinter.CTkFrame(engine_description_frame, fg_color="transparent") # 親フレーム変更
        google_ai_frame.pack(fill="x", pady=(10,5), padx=5)
        customtkinter.CTkLabel(google_ai_frame, text="🚀 Google AI Studio (Gemini新音声)", font=self.label_font).pack(anchor="w")
        google_ai_details = """
        特徴: 最新AI技術、多言語対応、高品質、リアルタイム性、感情表現豊か。
        モデル例: Alloy (汎用), Echo (エネルギッシュ), Fable (物語調), Onyx (深みのある声), Nova (クリア), Shimmer (明るい) など。
        性別的特徴: 各モデルにより多様（例: Alloyは男性/女性選択可能、Onyxは深みのある男性声など、具体的な割り当てはAPI仕様に依存）。
        商用利用: Google Cloud Platformの利用規約に準じます。APIキー必須、利用量に応じた課金が発生する可能性があります。クレジット表記はサービス仕様を確認してください。
        キャラクター設定: 特定のキャラクター設定はありませんが、声のバリエーションが豊富です。
        """
        customtkinter.CTkLabel(google_ai_frame, text=google_ai_details.strip(), font=self.text_font, justify="left", wraplength=700).pack(anchor="w", fill="x", padx=10)

        # Avis Speech Engine
        avis_speech_frame = customtkinter.CTkFrame(engine_description_frame, fg_color="transparent") # 親フレーム変更
        avis_speech_frame.pack(fill="x", pady=5, padx=5)
        customtkinter.CTkLabel(avis_speech_frame, text="🎙️ Avis Speech Engine", font=self.label_font).pack(anchor="w")
        avis_speech_details = """
        特徴: 高品質な日本語音声合成、VOICEVOX互換API、感情表現対応。
        モデル例: デフォルト音声（女性/男性など、エンジンバージョンにより異なる）。VOICEVOXモデルも利用可能な場合あり。
        性別的特徴: 提供されるモデルに依存（例: デフォルトで落ち着いた女性の声など）。
        商用利用: エンジンのライセンスによります。多くは個人利用無料、商用利用は要確認。VOICEVOXモデル利用時は各モデルの規約も参照。
        キャラクター設定: VOICEVOX互換のため、VOICEVOXキャラクターが利用できる場合があります。その際はキャラクターの利用規約に従ってください。
        """
        customtkinter.CTkLabel(avis_speech_frame, text=avis_speech_details.strip(), font=self.text_font, justify="left", wraplength=700).pack(anchor="w", fill="x", padx=10)

        # VOICEVOX Engine
        voicevox_frame = customtkinter.CTkFrame(engine_description_frame, fg_color="transparent") # 親フレーム変更
        voicevox_frame.pack(fill="x", pady=5, padx=5)
        customtkinter.CTkLabel(voicevox_frame, text="🎤 VOICEVOX Engine", font=self.label_font).pack(anchor="w")
        voicevox_details = """
        特徴: 多様なキャラクター音声、感情スタイル変更、アクセント調整。
        モデル例: ずんだもん (子供っぽい可愛い声), 四国めたん (クールな少女声), 春日部つむぎ (明るい少女声), 雨晴はう (優しいお姉さん声), 冥鳴ひまり (落ち着いた女性声) など多数。
        性別的特徴: 各キャラクターに設定あり（例: ずんだもんは女性的な声（設定上は妖精）、四国めたんは女性の声）。
        商用利用: VOICEVOXコアライブラリはLGPL。キャラクターごとの利用規約を必ず確認してください。多くはクレジット表記で個人・同人商用利用可。
        キャラクター設定: 各キャラクターに詳細なプロフィール、性格、背景ストーリーなどが設定されています。公式サイトや関連ドキュメントを参照してください。
        （例：ずんだもん - 東北ずん子の武器である「ずんだアロー」に変身する妖精。語尾に「〜のだ」をつけるのが特徴。）
        """
        customtkinter.CTkLabel(voicevox_frame, text=voicevox_details.strip(), font=self.text_font, justify="left", wraplength=700).pack(anchor="w", fill="x", padx=10)

        # システムTTS
        system_tts_frame = customtkinter.CTkFrame(engine_description_frame, fg_color="transparent") # 親フレーム変更
        system_tts_frame.pack(fill="x", pady=(5,10), padx=5)
        customtkinter.CTkLabel(system_tts_frame, text="💻 システムTTS (OS標準)", font=self.label_font).pack(anchor="w")
        system_tts_details = """
        特徴: OS標準機能、追加インストール不要、オフライン動作可能。
        モデル例: Windows (例: Microsoft Haruka, Ayumi), macOS (例: Kyoko, Otoya), Linux (Festival, eSpeakなどバックエンドに依存)。
        性別的特徴: OSやインストールされている音声によって異なる（例: Harukaは女性の声、Kyokoは女性の声）。
        商用利用: OSのライセンスに準じます。通常、OS上で動作するアプリケーション内での利用は許可されますが、生成音声の配布等は確認が必要。
        キャラクター設定: 通常、特定のキャラクター設定はありません。汎用的な読み上げ音声です。
        """
        customtkinter.CTkLabel(system_tts_frame, text=system_tts_details.strip(), font=self.text_font, justify="left", wraplength=700).pack(anchor="w", fill="x", padx=10)

        # YouTube Live手順タブ
        youtube_frame = customtkinter.CTkScrollableFrame(tab_youtube_live)
        youtube_frame.pack(fill="both", expand=True, padx=10, pady=10) # padx, pady変更

        youtube_content = """
        ## YouTube Liveでコメント読み上げを利用する手順

        このアプリケーションをYouTube Liveのコメント読み上げとして利用する基本的な手順です。

        **1. 必要なソフトウェア・準備:**
            - このアプリケーション（ボイスボットクライアント）
            - OBS Studio (または他の配信ソフト)
            - YouTubeアカウントとライブ配信設定
            - （推奨）仮想オーディオデバイス（例: VB-CABLE Virtual Audio Device, VoiceMeeter Banana）
                - アプリケーションの音声とマイク音声をOBSで別々に管理しやすくなります。

        **2. アプリケーション側の設定:**
            - **設定画面を開きます。**
            - **音声エンジン選択:** 使用したい音声エンジン（Google AI, VOICEVOXなど）を選択し、必要に応じてAPIキーやポートを設定します。
            - **キャラクター選択:** 読み上げに使用するキャラクターやボイスを選択します。
            - **音声出力デバイス:**
                - **直接OBSへ:** 仮想オーディオデバイスの入力側（例: CABLE Input）を選択します。
                - **PCスピーカーから確認しつつOBSへ:** VoiceMeeter等でルーティング設定をするか、一旦PCのスピーカーに出力し、OBS側でデスクトップ音声をキャプチャします（この場合、他のPC音も入るので注意）。
            - **YouTube Live連携:**
                - メイン画面または専用ウィンドウから「YouTube Live連携」機能を開きます。
                - **ライブID入力:**
                    - 配信中のYouTube Liveの動画ID（URLの `v=` の後ろの文字列、例: `https://www.youtube.com/watch?v=XXXXXXXXXXX` の `XXXXXXXXXXX` の部分）を入力します。
                    - **重要:** これはOBS等の配信ソフトに設定する「ストリームキー」とは全く異なります。「ストリームキー」は秘密の情報であり、ここには入力しないでください。
                - **公開設定の確認:** YouTube Liveの配信設定は必ず**「公開」または「限定公開」**にしてください。「非公開」設定ではコメント情報を正しく取得できません。
                - **接続開始:** 接続ボタンを押すと、コメントの取得と読み上げが開始されます。
                - （オプション）読み上げ対象（全員、メンバーのみ等）やNGワードを設定できる場合があります。

        **3. OBS側の設定:**
            - **音声入力キャプチャの追加:**
                - ソースの「+」ボタンから「音声入力キャプチャ」を選択します。
                - 「新規作成」で名前を付け（例: ボイスボット音声）、OKを押します。
                - **デバイス:** アプリケーションの音声出力先に設定した仮想オーディオデバイスの出力側（例: CABLE Output）を選択します。
                - これで、アプリケーションの読み上げ音声がOBSに取り込まれます。
            - **マイク設定:** 通常通り、マイクデバイスをOBSに追加します。
            - **音量調整:** OBSの音声ミキサーで、ボイスボットの音声、マイク音声、ゲーム音などのバランスを調整します。

        **4. テストと配信開始:**
            - YouTube Liveでテスト配信を開始します（限定公開など）。
            - 実際にコメントを投稿してみて、アプリケーションが読み上げ、OBS経由で配信に乗るか確認します。
            - 音量や読み上げ速度などを適宜調整します。
            - 問題がなければ本番の配信を開始します。

        **ポイント:**
            - **遅延:** コメント取得から読み上げまでには多少の遅延が発生します。
            - **API制限:** Google AI StudioなどAPIを利用するエンジンでは、利用量に上限がある場合があります。長時間の配信では注意が必要です。
            - **CPU負荷:** ローカルエンジン（VOICEVOX等）はPCのリソースを消費します。配信PCのスペックに注意してください。
        """
        youtube_textbox = customtkinter.CTkTextbox(youtube_frame, wrap="word", font=self.text_font)
        youtube_textbox.pack(fill="both", expand=True, padx=5, pady=5)
        youtube_textbox.insert("1.0", youtube_content.strip())
        youtube_textbox.configure(state="disabled")

        # AI劇場手順タブ
        theater_frame = customtkinter.CTkScrollableFrame(tab_ai_theater) # ScrollableFrameに変更
        theater_frame.pack(fill="both", expand=True, padx=10, pady=10) # padx, pady変更

        theater_content = """
        ## AI劇場として利用する手順

        このアプリケーションを使って、キャラクター同士の掛け合いによるAI劇場を作成・実行する基本的な手順です。

        **1. コンセプトとシナリオ作成:**
            - **テーマ決定:** どんな物語や会話劇にするかテーマを決めます（例: 日常コメディ、SF、ファンタジーの寸劇など）。
            - **登場キャラクター設定:**
                - アプリケーションのキャラクター管理機能で、登場させたいキャラクターを準備します。
                - 各キャラクターに使用する音声エンジン、ボイス、口調などを設定します。
            - **シナリオ作成:**
                - テキストエディタや専用ツールで脚本を作成します。
                - セリフの前にキャラクター名を記述する形式が一般的です（例: `キャラA: こんにちは！`）。
                - ト書き（状況説明や動作指示）も必要に応じて記述します。
                - （オプション）一部のアプリケーションでは、感情や声のトーンを制御するタグをセリフに含めることができる場合があります（例: `キャラB: (怒り)もう知らない！`）。

        **2. アプリケーション側の設定:**
            - **AI劇場ウィンドウを開きます。** (もし専用ウィンドウがあれば)
            - **キャラクター割り当て:** シナリオ上のキャラクター名と、アプリケーションに設定されたキャラクターを紐付けます。
            - **シナリオ読み込み:** 作成したシナリオファイル（.txt, .csvなど対応形式を確認）を読み込みます。
                - CSV形式の場合、列の定義（キャラクター列、セリフ列など）を確認・設定します。
            - **表示設定:**
                - キャラクターの立ち絵や背景画像を設定できる場合は、適宜設定します。
                - フォントサイズや色、表示速度などを調整します。

        **3. 実行と調整:**
            - **再生開始:** シナリオの再生を開始します。キャラクターが順番にセリフを読み上げます。
            - **タイミング調整:** セリフ間の間（ポーズ）や読み上げ速度が適切か確認します。必要であればシナリオや設定を修正します。
            - **演出確認:** 立ち絵の切り替えや背景変更が意図通りに行われるか確認します。
            - （オプション）OBS等で録画・配信する場合は、AI劇場のウィンドウをキャプチャするように設定します。

        **4. 応用:**
            - **分岐シナリオ:** 一部の高度なAI劇場ツールでは、選択肢によるシナリオ分岐や、ランダムなセリフ生成機能を持つものもあります。
            - **外部連携:** 特定のイベント（例: 配信でのコメント）に反応してセリフを再生するような連携も考えられます。

        **ポイント:**
            - **キャラクターの声の個性:** 各キャラクターの声質や口調をしっかり設定することで、劇の魅力が向上します。
            - **間の重要性:** 会話劇では「間」が非常に重要です。適切なポーズを入れることで、より自然な掛け合いになります。
            - **シナリオ形式の確認:** 使用するアプリケーションが対応しているシナリオの書式（タグの使用可否など）を事前に確認しましょう。
        """
        theater_textbox = customtkinter.CTkTextbox(theater_frame, wrap="word", font=self.text_font)
        theater_textbox.pack(fill="both", expand=True, padx=5, pady=5)
        theater_textbox.insert("1.0", theater_content.strip())
        theater_textbox.configure(state="disabled")

        # AIチャット手順タブ
        chat_frame = customtkinter.CTkScrollableFrame(tab_ai_chat) # ScrollableFrameに変更
        chat_frame.pack(fill="both", expand=True, padx=10, pady=10) # padx, pady変更

        chat_content = """
        ## AIチャットボットとして利用する手順

        このアプリケーションをAIチャットボット（対話型AI）として利用する基本的な手順です。

        **1. 利用目的の明確化:**
            - どのようなAIチャットボットとして使いたいか定義します（例: 雑談相手、特定情報の応答、ロールプレイなど）。
            - これにより、キャラクター設定や応答生成の方法が変わってきます。

        **2. アプリケーション側の設定:**
            - **AIチャットウィンドウを開きます。** (もし専用ウィンドウがあれば)
            - **キャラクター選択・設定:**
                - チャット相手となるAIキャラクターを選択します。
                - 声のエンジン、ボイス、口調（一人称、語尾など）を設定します。
                - （オプション）キャラクターの性格や背景設定を詳細に行うことで、より一貫性のある応答が期待できます（例: プロンプトエンジニアリング）。
            - **応答生成エンジンの選択:**
                - **ローカルLLM:** PC内で動作する小規模な言語モデルを利用する場合（別途セットアップが必要なことが多い）。
                - **外部API:** OpenAI (ChatGPT), Google (Gemini), Anthropic (Claude) などの大規模言語モデルAPIを利用する場合。
                    - APIキーの設定が必要です。
                    - 利用量に応じた課金が発生する場合があります。
            - **プロンプト設定（重要）:**
                - AIチャットボットの振る舞いを指示する「システムプロンプト」や「事前指示」を設定します。
                - 例: 「あなたはフレンドリーな猫のキャラクターです。一人称は『吾輩』、語尾は『〜にゃ』を付けて話してください。」
                - 応答の質や一貫性に大きく影響します。試行錯誤して調整しましょう。
            - **音声認識設定（入力）:**
                - マイクからの音声入力を有効にする場合、使用するマイクデバイスを選択します。
                - 音声認識の精度や言語を設定します。
            - **音声合成設定（出力）:**
                - AIの応答をどの声で読み上げるか（キャラクター設定で指定した音声）を確認します。

        **3. チャットの開始と操作:**
            - **入力方法:**
                - **テキスト入力:** テキストボックスにメッセージを入力して送信します。
                - **音声入力:** マイクに向かって話しかけると、音声認識されたテキストが入力されます。
            - **AIの応答:** AIが応答を生成し、設定されたキャラクターの声で読み上げられます。テキストも表示されます。
            - **会話の継続:** 上記を繰り返して会話を続けます。
            - **会話履歴:** 過去のやり取りが表示され、文脈に基づいた応答がなされます（通常）。
            - （オプション）会話履歴のクリア機能などがある場合があります。

        **4. 応用と注意点:**
            - **ロールプレイ:** 特定のキャラクターになりきって会話を楽しむことができます。
            - **情報検索:** 外部APIを利用するLLMの場合、最新情報や専門知識について質問することも可能です（ただし、情報の正確性は常に確認が必要です）。
            - **API利用料:** 外部LLM APIを利用する場合、トークン数（処理する文字数のようなもの）に応じて費用が発生します。長時間の利用や大量のテキスト処理には注意してください。
            - **ハルシネーション:** AIは事実に基づかない情報や、もっともらしい嘘を生成することがあります（ハルシネーション）。重要な情報については必ず裏付けを取りましょう。
            - **プライバシー:** 個人情報や機密情報をAIチャットボットに入力する際は、その情報がどのように扱われるか（特に外部API利用時）を理解し、注意してください。
        """
        chat_textbox = customtkinter.CTkTextbox(chat_frame, wrap="word", font=self.text_font)
        chat_textbox.pack(fill="both", expand=True, padx=5, pady=5)
        chat_textbox.insert("1.0", chat_content.strip())
        chat_textbox.configure(state="disabled")

        # 設定画面の説明タブ
        settings_guide_frame = customtkinter.CTkScrollableFrame(tab_settings_guide)
        settings_guide_frame.pack(fill="both", expand=True, padx=10, pady=10) # padx, pady変更

        settings_intro_text = """
        この画面では、アプリケーションの動作に関する様々な設定を行うことができます。
        設定変更後は、右下の「設定を保存」ボタンを押して変更を保存してください。
        """
        customtkinter.CTkLabel(settings_guide_frame, text=settings_intro_text.strip(), font=self.text_font, justify="left", wraplength=700).pack(anchor="w", fill="x", pady=(5,10), padx=10) # wraplength変更

        # API設定セクション
        api_settings_frame = customtkinter.CTkFrame(settings_guide_frame, fg_color="transparent")
        api_settings_frame.pack(fill="x", pady=5, padx=5)
        customtkinter.CTkLabel(api_settings_frame, text="⚙️ API設定", font=self.label_font).pack(anchor="w")
        api_settings_details = """
        - **Google AI Studio APIキー:** Googleの最新音声合成モデル（Gemini音声など）を利用するために必要なキーです。Google AI Studioで取得したAPIキーを入力します。「テスト」ボタンで接続と音声生成を確認できます。
        - **YouTube APIキー:** YouTube Liveのコメントを取得するために必要なキーです。Google Cloud ConsoleでYouTube Data API v3を有効にし、APIキーを取得して入力します。「テスト」ボタンでAPIキーの有効性を確認できます。
        - **テキスト生成モデル:** AIチャット機能などで使用する大規模言語モデル（LLM）を選択します。
            - `LM Studio (Local)`: ローカルPC上のLM Studioで動作させているモデルを利用します。選択するとエンドポイントURLの入力欄が表示されます。
            - `gemini- ...`: GoogleのGeminiモデルを利用します。モデルによって性能やコストが異なります。APIキーが設定されている必要があります。
        - **LM Studio エンドポイントURL:** 上記で `LM Studio (Local)` を選択した場合に、LM Studioが提供するサーバーのURL（例: `http://127.0.0.1:1234/v1/chat/completions`）を入力します。
        """
        customtkinter.CTkLabel(api_settings_frame, text=api_settings_details.strip(), font=self.text_font, justify="left", wraplength=700).pack(anchor="w", fill="x", padx=10) # wraplength変更

        # AIチャット設定セクション
        ai_chat_settings_frame = customtkinter.CTkFrame(settings_guide_frame, fg_color="transparent")
        ai_chat_settings_frame.pack(fill="x", pady=5, padx=5)
        customtkinter.CTkLabel(ai_chat_settings_frame, text="💬 AIチャット設定", font=self.label_font).pack(anchor="w")
        ai_chat_settings_details = """
        - **AIチャット処理方式:** AIチャット時のユーザーの音声入力とAIの応答処理のタイミングを選択します。
            - `sequential (推奨)`: ユーザーの音声が再生された後に、AIが応答を生成・発話します。自然な会話の流れに近い方式です。
            - `parallel`: ユーザーの音声再生とAIの応答処理を並行して行います。応答が早くなる可能性がありますが、会話が重なることがあります。
        """
        customtkinter.CTkLabel(ai_chat_settings_frame, text=ai_chat_settings_details.strip(), font=self.text_font, justify="left", wraplength=700).pack(anchor="w", fill="x", padx=10) # wraplength変更

        # 音声エンジン設定セクション
        voice_engine_settings_frame = customtkinter.CTkFrame(settings_guide_frame, fg_color="transparent")
        voice_engine_settings_frame.pack(fill="x", pady=5, padx=5)
        customtkinter.CTkLabel(voice_engine_settings_frame, text="🔊 音声エンジン設定", font=self.label_font).pack(anchor="w")
        voice_engine_settings_details = """
        - **デフォルト音声エンジン:** アプリケーション全体で標準的に使用する音声合成エンジンを選択します。キャラクターごとに個別のエンジン設定も可能です。
            - `google_ai_studio_new`: Google AI Studioの最新音声合成。高品質で多言語対応。APIキー設定とインターネット接続が必要です。
            - `avis_speech`: Avis Speech Engine。ローカルで動作。事前にエンジンを起動しておく必要があります。
            - `voicevox`: VOICEVOX Engine。ローカルで動作。多様なキャラクターボイス。事前にエンジンを起動しておく必要があります。
            - `system_tts`: OS標準のテキスト読み上げ機能。追加設定不要ですぐに使えますが、品質は上記専用エンジンに劣ることがあります。
        - **音声出力デバイス:** 音声の再生に使用するスピーカーやヘッドフォンなどのオーディオデバイスを選択します。
        - **フォールバック有効/順序:** メインの音声エンジンでエラーが発生した場合に、別のエンジンで代替処理を行うか（有効）、その際の優先順位（自動、品質優先など）を設定します。
        """
        customtkinter.CTkLabel(voice_engine_settings_frame, text=voice_engine_settings_details.strip(), font=self.text_font, justify="left", wraplength=700).pack(anchor="w", fill="x", padx=10) # wraplength変更

        # システム設定セクション
        system_settings_frame = customtkinter.CTkFrame(settings_guide_frame, fg_color="transparent")
        system_settings_frame.pack(fill="x", pady=5, padx=5)
        customtkinter.CTkLabel(system_settings_frame, text="🛠️ システム設定", font=self.label_font).pack(anchor="w")
        system_settings_details = """
        - **自動保存:** 設定変更時に自動で保存するかどうか。チェックを外すと、「設定を保存」ボタンを押すまで変更は保存されません。
        - **デバッグモード:** アプリケーションの詳細なログを出力するなど、開発者向けのデバッグ機能を有効にします。
        - **会話履歴の長さ:** AIチャットやYouTube Liveコメント読み上げ時に記憶しておく会話の履歴件数を設定します。0で履歴なし。数値を大きくすると文脈理解が向上する可能性がありますが、リソース消費も増えます。
        """
        customtkinter.CTkLabel(system_settings_frame, text=system_settings_details.strip(), font=self.text_font, justify="left", wraplength=700).pack(anchor="w", fill="x", padx=10) # wraplength変更

        # ボタン類の説明セクション
        buttons_settings_frame = customtkinter.CTkFrame(settings_guide_frame, fg_color="transparent")
        buttons_settings_frame.pack(fill="x", pady=(5,10), padx=5)
        customtkinter.CTkLabel(buttons_settings_frame, text="💾 設定の管理ボタン", font=self.label_font).pack(anchor="w")
        buttons_settings_details = """
        - **設定を保存:** 現在のGUI上の設定内容をファイルに保存します。
        - **設定をリセット:** システム設定（APIキーやエンジン選択など）を初期状態に戻します。キャラクター設定はリセットされません。
        - **設定をエクスポート:** 現在のシステム設定をJSONファイルとして書き出します。バックアップや他の環境への移行に使えます。
        - **設定をインポート:** エクスポートしたJSONファイルからシステム設定を読み込みます。
        """
        customtkinter.CTkLabel(buttons_settings_frame, text=buttons_settings_details.strip(), font=self.text_font, justify="left", wraplength=700).pack(anchor="w", fill="x", padx=10) # wraplength変更

        # 高度な機能タブの説明
        advanced_tab_frame = customtkinter.CTkFrame(settings_guide_frame, fg_color="transparent")
        advanced_tab_frame.pack(fill="x", pady=(10,10), padx=5)
        customtkinter.CTkLabel(advanced_tab_frame, text="🚀 高度な機能タブについて", font=self.label_font).pack(anchor="w")
        advanced_tab_details = """
        設定画面には「高度な機能」タブもあります。こちらでは以下の機能が提供されています（一部は実装予定）。
        - **パフォーマンス監視:** アプリケーションのCPU使用率やメモリ使用量などを監視する機能（実装予定）。
        - **バックアップ・復元:** アプリケーションの全設定（システム設定＋キャラクターデータ）を一つのファイルにバックアップしたり、そこから復元したりする機能。
        - **プラグイン管理:** 外部プラグインを追加して機能を拡張するための管理画面（実装予定）。
        """
        customtkinter.CTkLabel(advanced_tab_frame, text=advanced_tab_details.strip(), font=self.text_font, justify="left", wraplength=700).pack(anchor="w", fill="x", padx=10)

        # --- 新しい音声カタログタブのUI ---
        new_catalog_tab_main_frame = customtkinter.CTkFrame(tab_new_voice_catalog, fg_color="transparent")
        new_catalog_tab_main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # 左ペイン (フィルタとリスト)
        left_pane = customtkinter.CTkFrame(new_catalog_tab_main_frame, width=250) # 初期幅指定
        left_pane.pack(side="left", fill="y", padx=(0, 5), pady=0)
        left_pane.pack_propagate(False) # width指定を有効にするため

        filter_frame = customtkinter.CTkFrame(left_pane)
        filter_frame.pack(fill="x", padx=5, pady=5)

        customtkinter.CTkLabel(filter_frame, text="エンジン:", font=self.text_font).grid(row=0, column=0, padx=(5,2), pady=5, sticky="w")
        self.engine_filter_var = tk.StringVar(value="すべて")
        self.engine_filter_combo = customtkinter.CTkComboBox(filter_frame, variable=self.engine_filter_var, values=["すべて"], state="readonly", font=self.text_font, command=self._update_model_list)
        self.engine_filter_combo.grid(row=0, column=1, padx=(0,5), pady=5, sticky="ew")

        customtkinter.CTkLabel(filter_frame, text="検索:", font=self.text_font).grid(row=1, column=0, padx=(5,2), pady=5, sticky="w")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._update_model_list)
        self.search_entry = customtkinter.CTkEntry(filter_frame, textvariable=self.search_var, font=self.text_font)
        self.search_entry.grid(row=1, column=1, padx=(0,5), pady=5, sticky="ew")
        filter_frame.grid_columnconfigure(1, weight=1)


        self.model_list_frame = customtkinter.CTkScrollableFrame(left_pane, label_text="音声モデルリスト")
        self.model_list_frame.pack(fill="both", expand=True, padx=5, pady=(0,5))
        # 初期ラベルは _update_model_list で表示される


        # 右ペイン (詳細表示)
        right_pane = customtkinter.CTkScrollableFrame(new_catalog_tab_main_frame)
        right_pane.pack(side="right", fill="both", expand=True, padx=(5, 0), pady=0)

        detail_content_frame = customtkinter.CTkFrame(right_pane, fg_color="transparent") # 内部コンテンツ用フレーム
        detail_content_frame.pack(fill="both", expand=True, padx=10, pady=10)


        customtkinter.CTkLabel(detail_content_frame, text="音声モデル詳細", font=self.label_font).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0,10))

        # 詳細表示用ウィジェット
        row_idx = 1
        self.detail_icon_label = customtkinter.CTkLabel(detail_content_frame, text="", width=120, height=120) # 画像表示用
        self.detail_icon_label.grid(row=row_idx, column=0, rowspan=3, padx=(0,10), pady=5, sticky="ns") # アイコンを左に

        customtkinter.CTkLabel(detail_content_frame, text="和名:", font=self.text_font, anchor="e").grid(row=row_idx, column=1, sticky="ne", padx=2, pady=(5,3))
        self.detail_model_name_jp_var = tk.StringVar()
        customtkinter.CTkLabel(detail_content_frame, textvariable=self.detail_model_name_jp_var, font=self.text_font, fg_color=("gray85", "gray17"), corner_radius=5, anchor="w").grid(row=row_idx, column=2, sticky="new", padx=2, pady=(5,3))
        row_idx +=1

        customtkinter.CTkLabel(detail_content_frame, text="英名:", font=self.text_font, anchor="e").grid(row=row_idx, column=1, sticky="ne", padx=2, pady=3)
        self.detail_model_name_en_var = tk.StringVar()
        customtkinter.CTkLabel(detail_content_frame, textvariable=self.detail_model_name_en_var, font=self.text_font, fg_color=("gray85", "gray17"), corner_radius=5, anchor="w").grid(row=row_idx, column=2, sticky="new", padx=2, pady=3)
        row_idx +=1

        customtkinter.CTkLabel(detail_content_frame, text="エンジン:", font=self.text_font, anchor="e").grid(row=row_idx, column=1, sticky="ne", padx=2, pady=3)
        self.detail_engine_name_var = tk.StringVar()
        customtkinter.CTkLabel(detail_content_frame, textvariable=self.detail_engine_name_var, font=self.text_font, fg_color=("gray85", "gray17"), corner_radius=5, anchor="w").grid(row=row_idx, column=2, sticky="new", padx=2, pady=3)
        row_idx +=1

        customtkinter.CTkLabel(detail_content_frame, text="特徴:", font=self.text_font, anchor="e").grid(row=row_idx, column=0, columnspan=1, sticky="ne", padx=2, pady=3) # 特徴は左寄せラベル
        self.detail_features_var = tk.StringVar()
        features_label = customtkinter.CTkLabel(detail_content_frame, textvariable=self.detail_features_var, font=self.text_font, wraplength=500, justify="left", fg_color=("gray85", "gray17"), corner_radius=5, anchor="nw")
        features_label.grid(row=row_idx, column=1, columnspan=2, sticky="new", padx=2, pady=3)
        row_idx +=1

        customtkinter.CTkLabel(detail_content_frame, text="性別的印象:", font=self.text_font, anchor="e").grid(row=row_idx, column=0, columnspan=1, sticky="ne", padx=2, pady=3)
        self.detail_gender_impression_var = tk.StringVar()
        customtkinter.CTkLabel(detail_content_frame, textvariable=self.detail_gender_impression_var, font=self.text_font, fg_color=("gray85", "gray17"), corner_radius=5, anchor="w").grid(row=row_idx, column=1, columnspan=2, sticky="new", padx=2, pady=3)
        row_idx +=1

        customtkinter.CTkLabel(detail_content_frame, text="商用利用:", font=self.text_font, anchor="e").grid(row=row_idx, column=0, columnspan=1, sticky="ne", padx=2, pady=3)
        self.detail_commercial_use_var = tk.StringVar()
        commercial_label = customtkinter.CTkLabel(detail_content_frame, textvariable=self.detail_commercial_use_var, font=self.text_font, wraplength=500, justify="left", fg_color=("gray85", "gray17"), corner_radius=5, anchor="nw")
        commercial_label.grid(row=row_idx, column=1, columnspan=2, sticky="new", padx=2, pady=3)
        row_idx +=1

        customtkinter.CTkLabel(detail_content_frame, text="キャラ情報:", font=self.text_font, anchor="e").grid(row=row_idx, column=0, columnspan=1, sticky="ne", padx=2, pady=3)
        self.detail_character_info_var = tk.StringVar()
        charinfo_label = customtkinter.CTkLabel(detail_content_frame, textvariable=self.detail_character_info_var, font=self.text_font, wraplength=500, justify="left", fg_color=("gray85", "gray17"), corner_radius=5, anchor="nw")
        charinfo_label.grid(row=row_idx, column=1, columnspan=2, sticky="new", padx=2, pady=3)
        row_idx +=1

        customtkinter.CTkLabel(detail_content_frame, text="利用規約URL:", font=self.text_font, anchor="e").grid(row=row_idx, column=0, columnspan=1, sticky="ne", padx=2, pady=3)
        self.detail_terms_url_var = tk.StringVar() # これはボタンのテキストではない
        terms_button = customtkinter.CTkButton(detail_content_frame, text="規約を開く", font=self.text_font, state="disabled", command=lambda: webbrowser.open(self.detail_terms_url_var.get()))
        terms_button.grid(row=row_idx, column=1, columnspan=2, sticky="new", padx=2, pady=3)
        self.detail_terms_button = terms_button
        row_idx +=1

        self.detail_sample_button = customtkinter.CTkButton(detail_content_frame, text="サンプル音声再生", state="disabled")
        self.detail_sample_button.grid(row=row_idx, column=1, columnspan=2, sticky="new", padx=2, pady=(10,5))
        row_idx +=1

        detail_content_frame.grid_columnconfigure(2, weight=1) # 値表示ラベルが伸びるように


        # 閉じるボタン (タブビューの外、ウィンドウの最下部に配置)
        close_button_frame = customtkinter.CTkFrame(self.root, fg_color="transparent") # ウィンドウに直接配置するため
        close_button_frame.pack(pady=(0,10), fill="x", side="bottom") # pack_forgetは不要

        close_button = customtkinter.CTkButton(close_button_frame, text="閉じる", command=self.root.destroy, font=self.default_font)
        close_button.pack() # 中央寄せのデフォルト挙動を利用

def main():
    customtkinter.set_appearance_mode("System")
    customtkinter.set_default_color_theme("blue")
    root = customtkinter.CTk()
    app = HelpWindow(root)
    root.mainloop()

if __name__ == "__main__":
    customtkinter.set_appearance_mode("System")
    customtkinter.set_default_color_theme("blue")
    main()
