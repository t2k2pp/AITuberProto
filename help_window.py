import customtkinter
import tkinter as tk # 基本的な型 (StringVarなど) と標準ダイアログのため
import webbrowser
import sys # フォント選択のため
import json # JSON読み込み用
from PIL import Image, ImageTk # アイコン表示用 (CTkImageのため)
import os # ファイルパス操作用 (将来的にアイコンなどをローカルから読む場合)
import requests # Web上の画像取得用
import io # BytesIOのため
import i18n_setup

class HelpWindow:
    def __init__(self, root: customtkinter.CTk):
        i18n_setup.init_i18n()
        self._ = i18n_setup.get_translator()
        self.root = root
        self.root.title(self._("help_window.title"))
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

        self.loading_label = customtkinter.CTkLabel(self.root, text=self._("help_window.loading"), font=("Yu Gothic UI", 18))
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
                    # MEIPASSも考慮したエラーメッセージ
                    meipass_path_info = f" or in MEIPASS path ({getattr(sys, '_MEIPASS', 'N/A')})" if hasattr(sys, '_MEIPASS') else ""
                    print(self._("help_window.error.voice_models_json_not_found").format(path1=json_path, path2=project_root_json_path, meipass_info=meipass_path_info))
                    self.voice_model_data = []
                    # エラーダイアログを出すことも検討
                    # messagebox.showerror(self._("help_window.error.title"), self._("help_window.error.voice_models_json_not_found_dialog"))
                    return

            with open(json_path, "r", encoding="utf-8") as f:
                self.voice_model_data = json.load(f)
        except FileNotFoundError: # このケースは上のexistsチェックでほぼカバーされるはずだが念のため
            print(self._("help_window.error.voice_models_json_not_found").format(path1=json_path, path2="N/A", meipass_info=""))
            self.voice_model_data = []
        except json.JSONDecodeError:
            print(self._("help_window.error.voice_models_json_parse_failed").format(path=json_path))
            self.voice_model_data = []
        except Exception as e:
            print(self._("help_window.error.voice_models_json_load_error").format(error=e))
            self.voice_model_data = []
            # TODO: ユーザーにエラーダイアログを表示することを検討 (例: messagebox.showerror)

    def populate_engine_filter(self):
        """
        読み込んだ音声モデルデータからエンジン名のリストを作成し、
        エンジンフィルター用ComboBoxの選択肢を更新する。
        """
        if not self.voice_model_data:
            self.engine_filter_combo.configure(values=[self._("help_window.voice_catalog.filter.all")]) # データがない場合でも選択肢は設定
            self.engine_filter_var.set(self._("help_window.voice_catalog.filter.all"))
            return

        engine_names = sorted(list(set(model.get("engine_name", self._("help_window.voice_catalog.data.unknown")) for model in self.voice_model_data)))
        self.engine_filter_combo.configure(values=[self._("help_window.voice_catalog.filter.all")] + engine_names)
        self.engine_filter_var.set(self._("help_window.voice_catalog.filter.all"))


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
            engine_match = (selected_engine == self._("help_window.voice_catalog.filter.all") or model.get("engine_name") == selected_engine)

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
            customtkinter.CTkLabel(self.model_list_frame, text=self._("help_window.voice_catalog.list.no_models"), font=self.text_font).pack(padx=5, pady=5)
            self._clear_details() # 詳細表示もクリア
            return

        for index, model_data in enumerate(self.filtered_voice_model_data):
            model_display_name = f"{model_data.get('model_name_jp', self._('help_window.voice_catalog.data.not_available'))} ({model_data.get('model_name_en', self._('help_window.voice_catalog.data.not_available'))})"
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
        self.detail_terms_button.configure(state="disabled", text=self._("help_window.voice_catalog.details.button.no_terms_url"))

        if hasattr(self, 'detail_icon_label') and self.detail_icon_label:
            self.detail_icon_label.configure(image=None)
            self.detail_icon_label.image = None # 参照を保持させない
        if hasattr(self, 'detail_sample_button') and self.detail_sample_button:
            self.detail_sample_button.configure(state="disabled", text=self._("help_window.voice_catalog.details.button.play_sample"))


    def _display_model_details(self, model_data: dict):
        """
        指定された音声モデルのデータを右ペインの詳細表示エリアに表示する。
        アイコンの読み込み・表示、規約URLボタン、サンプル音声ボタンの制御も行う。
        """
        self._clear_details() # 表示前に一旦クリア
        self.detail_model_name_jp_var.set(model_data.get("model_name_jp", self._("help_window.voice_catalog.data.not_available")))
        self.detail_model_name_en_var.set(model_data.get("model_name_en", self._("help_window.voice_catalog.data.not_available")))
        self.detail_engine_name_var.set(model_data.get("engine_name", self._("help_window.voice_catalog.data.not_available")))
        self.detail_features_var.set(model_data.get("features", self._("help_window.voice_catalog.data.no_information")))
        self.detail_gender_impression_var.set(model_data.get("gender_impression", self._("help_window.voice_catalog.data.no_information")))
        self.detail_commercial_use_var.set(model_data.get("commercial_use", self._("help_window.voice_catalog.data.no_information")))
        self.detail_character_info_var.set(model_data.get("character_info", self._("help_window.voice_catalog.data.no_information")))

        terms_url = model_data.get("terms_url", "")
        if terms_url and terms_url.startswith("http"):
            self.detail_terms_url_var.set(terms_url) # ボタンのtext変数ではないので直接セット
            self.detail_terms_button.configure(state="normal", text=terms_url) # ボタンテキストも更新
        else:
            self.detail_terms_url_var.set("")
            self.detail_terms_button.configure(state="disabled", text=self._("help_window.voice_catalog.details.button.no_terms_url"))

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
                        print(self._("help_window.error.icon_load_file_not_found").format(path=icon_url)) # icon_urlが相対パスの場合を想定
            except requests.exceptions.RequestException as e:
                print(self._("help_window.error.icon_load_web_error").format(url=icon_url, error=e))
            except FileNotFoundError:
                print(self._("help_window.error.icon_load_file_not_found").format(path=icon_url))
            except Exception as e:
                print(self._("help_window.error.icon_load_processing_error").format(icon_path=icon_url, error=e))

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
                print(self._("help_window.error.icon_load_ctk_error").format(icon_url=icon_url, error=e))
                self.detail_icon_label.configure(image=None, text=self._("help_window.voice_catalog.details.image_load_error"))
                self.detail_icon_label.image = None
        else:
            self.detail_icon_label.configure(image=None, text=self._("help_window.voice_catalog.details.no_icon"))
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
        tab_engine_guide = tab_view.add(self._("help_window.tab.engine_guide"))
        tab_engine_description = tab_view.add(self._("help_window.tab.engine_description"))
        tab_new_voice_catalog = tab_view.add(self._("help_window.tab.voice_catalog"))
        tab_youtube_live = tab_view.add(self._("help_window.tab.youtube_live_setup"))
        tab_ai_theater = tab_view.add(self._("help_window.tab.ai_theater_setup"))
        tab_ai_chat = tab_view.add(self._("help_window.tab.ai_chat_setup"))
        tab_settings_guide = tab_view.add(self._("help_window.tab.settings_guide"))

        # --- エンジン起動ガイドタブ ---
        engine_guide_frame = customtkinter.CTkScrollableFrame(tab_engine_guide)
        engine_guide_frame.pack(fill="both", expand=True, padx=10, pady=10)

        customtkinter.CTkLabel(engine_guide_frame, text=self._("help_window.engine_guide.title"), font=self.label_font).pack(anchor="w", padx=10, pady=(5,5))

        guide_text_widget = customtkinter.CTkTextbox(engine_guide_frame, wrap="word", font=self.text_font)
        guide_text_widget.pack(fill="both", expand=True, padx=5, pady=5)
        guide_text_widget.insert("end", self._("help_window.engine_guide.content.overview_title") + "\n")
        guide_text_widget.insert("end", self._("help_window.engine_guide.content.overview_text") + "\n\n---\n\n")
        guide_text_widget.insert("end", self._("help_window.engine_guide.content.google_ai_title") + "\n")
        guide_text_widget.insert("end", self._("help_window.engine_guide.content.google_ai_text") + "\n\n")
        guide_text_widget.insert("end", self._("help_window.engine_guide.content.avis_speech_title") + "\n")
        guide_text_widget.insert("end", self._("help_window.engine_guide.content.avis_speech_text") + "\n\n")
        guide_text_widget.insert("end", self._("help_window.engine_guide.content.voicevox_title") + "\n")
        guide_text_widget.insert("end", self._("help_window.engine_guide.content.voicevox_text") + "\n\n")
        guide_text_widget.insert("end", self._("help_window.engine_guide.content.system_tts_title") + "\n")
        guide_text_widget.insert("end", self._("help_window.engine_guide.content.system_tts_text") + "\n\n")
        guide_text_widget.insert("end", self._("help_window.engine_guide.content.troubleshooting_title") + "\n")
        guide_text_widget.insert("end", self._("help_window.engine_guide.content.troubleshooting_text") + "\n")
        guide_text_widget.configure(state="disabled")

        # 外部リンクボタンフレーム (エンジン起動ガイドタブ内)
        link_frame = customtkinter.CTkFrame(engine_guide_frame, fg_color="transparent")
        link_frame.pack(pady=10)

        buttons_info = [
            (self._("help_window.engine_guide.button.vroid_studio"), "https://vroid.com/studio"),
            (self._("help_window.engine_guide.button.vseeface"), "https://www.vseeface.icu/"),
            (self._("help_window.engine_guide.button.avis_speech"), "https://github.com/Aivis-Project/AivisSpeech-Engine"),
            (self._("help_window.engine_guide.button.voicevox"), "https://voicevox.hiroshiba.jp/")
        ]

        for text, url in buttons_info:
            button = customtkinter.CTkButton(link_frame, text=text, command=lambda u=url: webbrowser.open(u), font=self.default_font)
            button.pack(side="left", padx=5, pady=5)

        # --- 音声エンジン説明タブ ---
        engine_description_frame = customtkinter.CTkScrollableFrame(tab_engine_description)
        engine_description_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Google AI Studio
        google_ai_frame = customtkinter.CTkFrame(engine_description_frame, fg_color="transparent")
        google_ai_frame.pack(fill="x", pady=(10,5), padx=5)
        customtkinter.CTkLabel(google_ai_frame, text=self._("help_window.engine_description.google_ai.title"), font=self.label_font).pack(anchor="w")
        google_ai_details = self._("help_window.engine_description.google_ai.details")
        customtkinter.CTkLabel(google_ai_frame, text=google_ai_details.strip(), font=self.text_font, justify="left", wraplength=700).pack(anchor="w", fill="x", padx=10)

        # Avis Speech Engine
        avis_speech_frame = customtkinter.CTkFrame(engine_description_frame, fg_color="transparent")
        avis_speech_frame.pack(fill="x", pady=5, padx=5)
        customtkinter.CTkLabel(avis_speech_frame, text=self._("help_window.engine_description.avis_speech.title"), font=self.label_font).pack(anchor="w")
        avis_speech_details = self._("help_window.engine_description.avis_speech.details")
        customtkinter.CTkLabel(avis_speech_frame, text=avis_speech_details.strip(), font=self.text_font, justify="left", wraplength=700).pack(anchor="w", fill="x", padx=10)

        # VOICEVOX Engine
        voicevox_frame = customtkinter.CTkFrame(engine_description_frame, fg_color="transparent")
        voicevox_frame.pack(fill="x", pady=5, padx=5)
        customtkinter.CTkLabel(voicevox_frame, text=self._("help_window.engine_description.voicevox.title"), font=self.label_font).pack(anchor="w")
        voicevox_details = self._("help_window.engine_description.voicevox.details")
        customtkinter.CTkLabel(voicevox_frame, text=voicevox_details.strip(), font=self.text_font, justify="left", wraplength=700).pack(anchor="w", fill="x", padx=10)

        # システムTTS
        system_tts_frame = customtkinter.CTkFrame(engine_description_frame, fg_color="transparent")
        system_tts_frame.pack(fill="x", pady=(5,10), padx=5)
        customtkinter.CTkLabel(system_tts_frame, text=self._("help_window.engine_description.system_tts.title"), font=self.label_font).pack(anchor="w")
        system_tts_details = self._("help_window.engine_description.system_tts.details")
        customtkinter.CTkLabel(system_tts_frame, text=system_tts_details.strip(), font=self.text_font, justify="left", wraplength=700).pack(anchor="w", fill="x", padx=10)

        # YouTube Live手順タブ
        youtube_frame = customtkinter.CTkScrollableFrame(tab_youtube_live)
        youtube_frame.pack(fill="both", expand=True, padx=10, pady=10)

        youtube_content = f"""{self._("help_window.youtube_live_setup.title")}

{self._("help_window.youtube_live_setup.content")}
"""
        youtube_textbox = customtkinter.CTkTextbox(youtube_frame, wrap="word", font=self.text_font)
        youtube_textbox.pack(fill="both", expand=True, padx=5, pady=5)
        youtube_textbox.insert("1.0", youtube_content.strip())
        youtube_textbox.configure(state="disabled")

        # AI劇場手順タブ
        theater_frame = customtkinter.CTkScrollableFrame(tab_ai_theater)
        theater_frame.pack(fill="both", expand=True, padx=10, pady=10)

        theater_content = f"""{self._("help_window.ai_theater_setup.title")}

{self._("help_window.ai_theater_setup.content")}
"""
        theater_textbox = customtkinter.CTkTextbox(theater_frame, wrap="word", font=self.text_font)
        theater_textbox.pack(fill="both", expand=True, padx=5, pady=5)
        theater_textbox.insert("1.0", theater_content.strip())
        theater_textbox.configure(state="disabled")

        # AIチャット手順タブ
        chat_frame = customtkinter.CTkScrollableFrame(tab_ai_chat)
        chat_frame.pack(fill="both", expand=True, padx=10, pady=10)

        chat_content = f"""{self._("help_window.ai_chat_setup.title")}

{self._("help_window.ai_chat_setup.content")}
"""
        chat_textbox = customtkinter.CTkTextbox(chat_frame, wrap="word", font=self.text_font)
        chat_textbox.pack(fill="both", expand=True, padx=5, pady=5)
        chat_textbox.insert("1.0", chat_content.strip())
        chat_textbox.configure(state="disabled")

        # 設定画面の説明タブ
        settings_guide_frame = customtkinter.CTkScrollableFrame(tab_settings_guide)
        settings_guide_frame.pack(fill="both", expand=True, padx=10, pady=10)

        settings_intro_text = self._("help_window.settings_guide.intro")
        customtkinter.CTkLabel(settings_guide_frame, text=settings_intro_text.strip(), font=self.text_font, justify="left", wraplength=700).pack(anchor="w", fill="x", pady=(5,10), padx=10)

        # API設定セクション
        api_settings_frame = customtkinter.CTkFrame(settings_guide_frame, fg_color="transparent")
        api_settings_frame.pack(fill="x", pady=5, padx=5)
        customtkinter.CTkLabel(api_settings_frame, text=self._("help_window.settings_guide.api.title"), font=self.label_font).pack(anchor="w")
        api_settings_details = self._("help_window.settings_guide.api.content")
        customtkinter.CTkLabel(api_settings_frame, text=api_settings_details.strip(), font=self.text_font, justify="left", wraplength=700).pack(anchor="w", fill="x", padx=10)

        # AIチャット設定セクション
        ai_chat_settings_frame = customtkinter.CTkFrame(settings_guide_frame, fg_color="transparent")
        ai_chat_settings_frame.pack(fill="x", pady=5, padx=5)
        customtkinter.CTkLabel(ai_chat_settings_frame, text=self._("help_window.settings_guide.ai_chat.title"), font=self.label_font).pack(anchor="w")
        ai_chat_settings_details = self._("help_window.settings_guide.ai_chat.content")
        customtkinter.CTkLabel(ai_chat_settings_frame, text=ai_chat_settings_details.strip(), font=self.text_font, justify="left", wraplength=700).pack(anchor="w", fill="x", padx=10)

        # 音声エンジン設定セクション
        voice_engine_settings_frame = customtkinter.CTkFrame(settings_guide_frame, fg_color="transparent")
        voice_engine_settings_frame.pack(fill="x", pady=5, padx=5)
        customtkinter.CTkLabel(voice_engine_settings_frame, text=self._("help_window.settings_guide.voice_engine.title"), font=self.label_font).pack(anchor="w")
        voice_engine_settings_details = self._("help_window.settings_guide.voice_engine.content")
        customtkinter.CTkLabel(voice_engine_settings_frame, text=voice_engine_settings_details.strip(), font=self.text_font, justify="left", wraplength=700).pack(anchor="w", fill="x", padx=10)

        # システム設定セクション
        system_settings_frame = customtkinter.CTkFrame(settings_guide_frame, fg_color="transparent")
        system_settings_frame.pack(fill="x", pady=5, padx=5)
        customtkinter.CTkLabel(system_settings_frame, text=self._("help_window.settings_guide.system.title"), font=self.label_font).pack(anchor="w")
        system_settings_details = self._("help_window.settings_guide.system.content")
        customtkinter.CTkLabel(system_settings_frame, text=system_settings_details.strip(), font=self.text_font, justify="left", wraplength=700).pack(anchor="w", fill="x", padx=10)

        # ボタン類の説明セクション
        buttons_settings_frame = customtkinter.CTkFrame(settings_guide_frame, fg_color="transparent")
        buttons_settings_frame.pack(fill="x", pady=(5,10), padx=5)
        customtkinter.CTkLabel(buttons_settings_frame, text=self._("help_window.settings_guide.buttons.title"), font=self.label_font).pack(anchor="w")
        buttons_settings_details = self._("help_window.settings_guide.buttons.content")
        customtkinter.CTkLabel(buttons_settings_frame, text=buttons_settings_details.strip(), font=self.text_font, justify="left", wraplength=700).pack(anchor="w", fill="x", padx=10)

        # 高度な機能タブの説明
        advanced_tab_frame = customtkinter.CTkFrame(settings_guide_frame, fg_color="transparent")
        advanced_tab_frame.pack(fill="x", pady=(10,10), padx=5)
        customtkinter.CTkLabel(advanced_tab_frame, text=self._("help_window.settings_guide.advanced_tab.title"), font=self.label_font).pack(anchor="w")
        advanced_tab_details = self._("help_window.settings_guide.advanced_tab.content")
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

        customtkinter.CTkLabel(filter_frame, text=self._("help_window.voice_catalog.filter.engine"), font=self.text_font).grid(row=0, column=0, padx=(5,2), pady=5, sticky="w")
        self.engine_filter_var = tk.StringVar(value=self._("help_window.voice_catalog.filter.all"))
        self.engine_filter_combo = customtkinter.CTkComboBox(filter_frame, variable=self.engine_filter_var, values=[self._("help_window.voice_catalog.filter.all")], state="readonly", font=self.text_font, command=self._update_model_list)
        self.engine_filter_combo.grid(row=0, column=1, padx=(0,5), pady=5, sticky="ew")

        customtkinter.CTkLabel(filter_frame, text=self._("help_window.voice_catalog.filter.search"), font=self.text_font).grid(row=1, column=0, padx=(5,2), pady=5, sticky="w")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._update_model_list)
        self.search_entry = customtkinter.CTkEntry(filter_frame, textvariable=self.search_var, font=self.text_font)
        self.search_entry.grid(row=1, column=1, padx=(0,5), pady=5, sticky="ew")
        filter_frame.grid_columnconfigure(1, weight=1)


        self.model_list_frame = customtkinter.CTkScrollableFrame(left_pane, label_text=self._("help_window.voice_catalog.list_label"))
        self.model_list_frame.pack(fill="both", expand=True, padx=5, pady=(0,5))
        # 初期ラベルは _update_model_list で表示される


        # 右ペイン (詳細表示)
        right_pane = customtkinter.CTkScrollableFrame(new_catalog_tab_main_frame)
        right_pane.pack(side="right", fill="both", expand=True, padx=(5, 0), pady=0)

        detail_content_frame = customtkinter.CTkFrame(right_pane, fg_color="transparent") # 内部コンテンツ用フレーム
        detail_content_frame.pack(fill="both", expand=True, padx=10, pady=10)


        customtkinter.CTkLabel(detail_content_frame, text=self._("help_window.voice_catalog.details.title"), font=self.label_font).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0,10))

        # 詳細表示用ウィジェット
        row_idx = 1
        self.detail_icon_label = customtkinter.CTkLabel(detail_content_frame, text="", width=120, height=120) # 画像表示用
        self.detail_icon_label.grid(row=row_idx, column=0, rowspan=3, padx=(0,10), pady=5, sticky="ns") # アイコンを左に

        customtkinter.CTkLabel(detail_content_frame, text=self._("help_window.voice_catalog.details.name_jp"), font=self.text_font, anchor="e").grid(row=row_idx, column=1, sticky="ne", padx=2, pady=(5,3))
        self.detail_model_name_jp_var = tk.StringVar()
        customtkinter.CTkLabel(detail_content_frame, textvariable=self.detail_model_name_jp_var, font=self.text_font, fg_color=("gray85", "gray17"), corner_radius=5, anchor="w").grid(row=row_idx, column=2, sticky="new", padx=2, pady=(5,3))
        row_idx +=1

        customtkinter.CTkLabel(detail_content_frame, text=self._("help_window.voice_catalog.details.name_en"), font=self.text_font, anchor="e").grid(row=row_idx, column=1, sticky="ne", padx=2, pady=3)
        self.detail_model_name_en_var = tk.StringVar()
        customtkinter.CTkLabel(detail_content_frame, textvariable=self.detail_model_name_en_var, font=self.text_font, fg_color=("gray85", "gray17"), corner_radius=5, anchor="w").grid(row=row_idx, column=2, sticky="new", padx=2, pady=3)
        row_idx +=1

        customtkinter.CTkLabel(detail_content_frame, text=self._("help_window.voice_catalog.details.engine"), font=self.text_font, anchor="e").grid(row=row_idx, column=1, sticky="ne", padx=2, pady=3)
        self.detail_engine_name_var = tk.StringVar()
        customtkinter.CTkLabel(detail_content_frame, textvariable=self.detail_engine_name_var, font=self.text_font, fg_color=("gray85", "gray17"), corner_radius=5, anchor="w").grid(row=row_idx, column=2, sticky="new", padx=2, pady=3)
        row_idx +=1

        customtkinter.CTkLabel(detail_content_frame, text=self._("help_window.voice_catalog.details.features"), font=self.text_font, anchor="e").grid(row=row_idx, column=0, columnspan=1, sticky="ne", padx=2, pady=3) # 特徴は左寄せラベル
        self.detail_features_var = tk.StringVar()
        features_label = customtkinter.CTkLabel(detail_content_frame, textvariable=self.detail_features_var, font=self.text_font, wraplength=500, justify="left", fg_color=("gray85", "gray17"), corner_radius=5, anchor="nw")
        features_label.grid(row=row_idx, column=1, columnspan=2, sticky="new", padx=2, pady=3)
        row_idx +=1

        customtkinter.CTkLabel(detail_content_frame, text=self._("help_window.voice_catalog.details.gender_impression"), font=self.text_font, anchor="e").grid(row=row_idx, column=0, columnspan=1, sticky="ne", padx=2, pady=3)
        self.detail_gender_impression_var = tk.StringVar()
        customtkinter.CTkLabel(detail_content_frame, textvariable=self.detail_gender_impression_var, font=self.text_font, fg_color=("gray85", "gray17"), corner_radius=5, anchor="w").grid(row=row_idx, column=1, columnspan=2, sticky="new", padx=2, pady=3)
        row_idx +=1

        customtkinter.CTkLabel(detail_content_frame, text=self._("help_window.voice_catalog.details.commercial_use"), font=self.text_font, anchor="e").grid(row=row_idx, column=0, columnspan=1, sticky="ne", padx=2, pady=3)
        self.detail_commercial_use_var = tk.StringVar()
        commercial_label = customtkinter.CTkLabel(detail_content_frame, textvariable=self.detail_commercial_use_var, font=self.text_font, wraplength=500, justify="left", fg_color=("gray85", "gray17"), corner_radius=5, anchor="nw")
        commercial_label.grid(row=row_idx, column=1, columnspan=2, sticky="new", padx=2, pady=3)
        row_idx +=1

        customtkinter.CTkLabel(detail_content_frame, text=self._("help_window.voice_catalog.details.character_info"), font=self.text_font, anchor="e").grid(row=row_idx, column=0, columnspan=1, sticky="ne", padx=2, pady=3)
        self.detail_character_info_var = tk.StringVar()
        charinfo_label = customtkinter.CTkLabel(detail_content_frame, textvariable=self.detail_character_info_var, font=self.text_font, wraplength=500, justify="left", fg_color=("gray85", "gray17"), corner_radius=5, anchor="nw")
        charinfo_label.grid(row=row_idx, column=1, columnspan=2, sticky="new", padx=2, pady=3)
        row_idx +=1

        customtkinter.CTkLabel(detail_content_frame, text=self._("help_window.voice_catalog.details.terms_url"), font=self.text_font, anchor="e").grid(row=row_idx, column=0, columnspan=1, sticky="ne", padx=2, pady=3)
        self.detail_terms_url_var = tk.StringVar() # これはボタンのテキストではない
        terms_button = customtkinter.CTkButton(detail_content_frame, text=self._("help_window.voice_catalog.details.button.open_terms"), font=self.text_font, state="disabled", command=lambda: webbrowser.open(self.detail_terms_url_var.get()))
        terms_button.grid(row=row_idx, column=1, columnspan=2, sticky="new", padx=2, pady=3)
        self.detail_terms_button = terms_button
        row_idx +=1

        self.detail_sample_button = customtkinter.CTkButton(detail_content_frame, text=self._("help_window.voice_catalog.details.button.play_sample"), state="disabled")
        self.detail_sample_button.grid(row=row_idx, column=1, columnspan=2, sticky="new", padx=2, pady=(10,5))
        row_idx +=1

        detail_content_frame.grid_columnconfigure(2, weight=1) # 値表示ラベルが伸びるように


        # 閉じるボタン (タブビューの外、ウィンドウの最下部に配置)
        close_button_frame = customtkinter.CTkFrame(self.root, fg_color="transparent") # ウィンドウに直接配置するため
        close_button_frame.pack(pady=(0,10), fill="x", side="bottom") # pack_forgetは不要

        close_button = customtkinter.CTkButton(close_button_frame, text=self._("help_window.button.close"), command=self.root.destroy, font=self.default_font)
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
