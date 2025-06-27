import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv
import os
from pathlib import Path
from datetime import datetime
import asyncio
import threading

from config import ConfigManager
from character_manager import CharacterManager
from audio_manager import VoiceEngineManager, AudioPlayer
from google import genai # AI応答生成用
from google.genai import types as genai_types

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AIChatWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("AIチャット")
        self.root.geometry("950x700")

        self.config = ConfigManager()
        self.character_manager = CharacterManager(self.config)
        self.voice_manager = VoiceEngineManager()
        self.audio_player = AudioPlayer(config_manager=self.config)

        self.ai_chat_history_folder = Path(self.config.config_file).parent / "ai_chat_history"
        try:
            self.ai_chat_history_folder.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"AIチャット履歴フォルダの作成失敗: {e}")
            messagebox.showerror("フォルダ作成エラー", f"AIチャット履歴フォルダ作成失敗: {e}", parent=self.root)

        self.current_ai_chat_file_path = None # 現在アクティブなチャットファイルパス(Pathオブジェクト)

        # Geminiモデルリスト (AITuberMainGUIからコピー・調整)
        self.available_gemini_models = [
            "gemini-1.5-flash", "gemini-1.5-flash-latest",
            "gemini-1.5-pro", "gemini-1.5-pro-latest",
            "gemini-2.5-flash", "gemini-2.5-pro"
        ]
        # ソートは後ほど

        self.create_widgets()
        self.populate_chat_character_dropdowns()
        self.load_chat_history_list()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.log("AIチャットウィンドウが初期化されました。")


    def log(self, message):
        logger.info(message)
        # GUIのログウィジェットがあればそこにも表示する (今回は省略)

    def on_closing(self):
        # 必要であればチャットセッションの保存などをここで行う
        self.root.destroy()

    def create_widgets(self):
        main_paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 左側: 会話履歴一覧
        history_list_frame = ttk.LabelFrame(main_paned_window, text="会話履歴", padding="5")
        main_paned_window.add(history_list_frame, weight=1)
        self.chat_history_tree = ttk.Treeview(history_list_frame, columns=('filename', 'last_updated'), show='headings')
        self.chat_history_tree.heading('filename', text='会話ログ'); self.chat_history_tree.heading('last_updated', text='最終更新日時')
        self.chat_history_tree.column('filename', width=150); self.chat_history_tree.column('last_updated', width=150)
        self.chat_history_tree.bind('<<TreeviewSelect>>', self.on_chat_history_selected_action)
        chat_history_scroll_y = ttk.Scrollbar(history_list_frame, orient=tk.VERTICAL, command=self.chat_history_tree.yview)
        self.chat_history_tree.configure(yscrollcommand=chat_history_scroll_y.set)
        chat_history_scroll_y.pack(side=tk.RIGHT, fill=tk.Y); self.chat_history_tree.pack(fill=tk.BOTH, expand=True)
        ttk.Button(history_list_frame, text="新しいチャットを開始", command=self.start_new_ai_chat_session_action).pack(side=tk.BOTTOM, fill=tk.X, pady=5)

        # 右側: 会話エリア
        chat_area_frame = ttk.Frame(main_paned_window)
        main_paned_window.add(chat_area_frame, weight=3)

        chat_config_frame = ttk.Frame(chat_area_frame); chat_config_frame.pack(fill=tk.X, pady=5)
        ttk.Label(chat_config_frame, text="AIキャラ:").grid(row=0, column=0, padx=2, pady=2, sticky=tk.W)
        self.ai_char_var = tk.StringVar()
        self.ai_char_combo = ttk.Combobox(chat_config_frame, textvariable=self.ai_char_var, state="readonly", width=15)
        self.ai_char_combo.grid(row=0, column=1, padx=2, pady=2, sticky=tk.W)
        ttk.Label(chat_config_frame, text="ユーザーキャラ:").grid(row=0, column=2, padx=2, pady=2, sticky=tk.W)
        self.user_char_var = tk.StringVar()
        self.user_char_combo = ttk.Combobox(chat_config_frame, textvariable=self.user_char_var, state="readonly", width=15)
        self.user_char_combo.grid(row=0, column=3, padx=2, pady=2, sticky=tk.W)
        self.play_user_speech_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(chat_config_frame, text="ユーザー発話再生", variable=self.play_user_speech_var).grid(row=0, column=4, padx=5, pady=2, sticky=tk.W)

        chat_display_container = ttk.LabelFrame(chat_area_frame, text="会話内容", padding="5")
        chat_display_container.pack(fill=tk.BOTH, expand=True, pady=5)
        self.chat_content_tree = ttk.Treeview(chat_display_container, columns=('line', 'talker', 'words'), show='headings')
        self.chat_content_tree.heading('line', text='行'); self.chat_content_tree.heading('talker', text='話者'); self.chat_content_tree.heading('words', text='発言内容')
        self.chat_content_tree.column('line', width=40, anchor=tk.CENTER); self.chat_content_tree.column('talker', width=100); self.chat_content_tree.column('words', width=350)
        chat_content_scroll_y = ttk.Scrollbar(chat_display_container, orient=tk.VERTICAL, command=self.chat_content_tree.yview)
        chat_content_scroll_x = ttk.Scrollbar(chat_display_container, orient=tk.HORIZONTAL, command=self.chat_content_tree.xview)
        self.chat_content_tree.configure(yscrollcommand=chat_content_scroll_y.set, xscrollcommand=chat_content_scroll_x.set)
        chat_content_scroll_y.pack(side=tk.RIGHT, fill=tk.Y); chat_content_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.chat_content_tree.pack(fill=tk.BOTH, expand=True)
        self.chat_content_tree.bind('<Configure>', lambda e: self._adjust_chat_words_column_width(e, self.chat_content_tree))
        self.chat_content_context_menu = tk.Menu(self.chat_content_tree, tearoff=0)
        self.chat_content_context_menu.add_command(label="選択行を削除", command=self.delete_selected_chat_message_action)
        self.chat_content_tree.bind("<Button-3>", self._show_chat_content_context_menu)

        chat_input_frame = ttk.Frame(chat_area_frame); chat_input_frame.pack(fill=tk.X, pady=5)
        self.chat_message_entry = ttk.Entry(chat_input_frame, width=60)
        self.chat_message_entry.bind("<Return>", self.send_ai_chat_message_action)
        self.chat_message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(chat_input_frame, text="送信", command=self.send_ai_chat_message_action).pack(side=tk.LEFT)


    def _adjust_chat_words_column_width(self, event, treeview_widget):
        # Treeviewの幅変更時に 'words' 列の幅を調整
        new_width = event.width - treeview_widget.column('line')['width'] - treeview_widget.column('talker')['width'] - 25 # スクロールバー等考慮
        if new_width > 100: treeview_widget.column('words', width=new_width)

    def _show_chat_content_context_menu(self, event):
        item_id = self.chat_content_tree.identify_row(event.y)
        if item_id:
            self.chat_content_tree.selection_set(item_id) # 右クリックした行を選択状態に
            self.chat_content_context_menu.post(event.x_root, event.y_root)


    def populate_chat_character_dropdowns(self):
        all_chars_data = self.character_manager.get_all_characters()
        char_names = [data.get('name', 'Unknown') for data in all_chars_data.values()]
        self.ai_char_combo['values'] = char_names
        self.user_char_combo['values'] = char_names
        if char_names:
            # 以前の選択を復元するロジック (configから読み込むなど)
            saved_ai_char = self.config.get_system_setting("ai_chat_default_ai_char_name")
            saved_user_char = self.config.get_system_setting("ai_chat_default_user_char_name")

            if saved_ai_char and saved_ai_char in char_names: self.ai_char_var.set(saved_ai_char)
            else: self.ai_char_var.set(char_names[0])

            if saved_user_char and saved_user_char in char_names: self.user_char_var.set(saved_user_char)
            elif len(char_names) > 1 : self.user_char_var.set(char_names[1] if self.ai_char_var.get() == char_names[0] else char_names[0])
            elif char_names : self.user_char_var.set(char_names[0])
        self.log("AIチャット: キャラクタープルダウン更新")


    def load_chat_history_list(self):
        self.chat_history_tree.delete(*self.chat_history_tree.get_children())
        if not self.ai_chat_history_folder.exists(): return
        history_files_data = []
        for item_path in self.ai_chat_history_folder.iterdir():
            if item_path.is_file() and item_path.suffix.lower() == '.csv':
                try:
                    last_mod_dt = datetime.fromtimestamp(item_path.stat().st_mtime)
                    history_files_data.append({"path": item_path, "name": item_path.name, "dt": last_mod_dt, "dt_str": last_mod_dt.strftime('%Y-%m-%d %H:%M:%S')})
                except Exception as e_stat: self.log(f"履歴ファイル情報取得エラー {item_path.name}: {e_stat}")
        history_files_data.sort(key=lambda x: x["dt"], reverse=True) # 新しいものが上
        for entry in history_files_data:
            self.chat_history_tree.insert('', 'end', values=(entry["name"], entry["dt_str"]), iid=str(entry["path"]))
        self.log(f"AIチャット: 会話履歴一覧更新 ({len(history_files_data)}件)")


    def start_new_ai_chat_session_action(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_filename = f"chat_{timestamp}.csv"
        new_filepath = self.ai_chat_history_folder / new_filename
        try:
            with open(new_filepath, 'w', newline='', encoding='utf-8') as csvfile:
                csv.writer(csvfile).writerow(['action', 'talker', 'words']) # ヘッダー
            self.log(f"新規チャットセッションファイル作成: {new_filepath}")
            self.current_ai_chat_file_path = new_filepath # アクティブファイルを設定
            self.chat_content_tree.delete(*self.chat_content_tree.get_children()) # 表示クリア
            self.load_chat_history_list() # リスト更新
            # 新規作成されたファイルを選択状態にする
            if self.chat_history_tree.exists(str(new_filepath)):
                self.chat_history_tree.selection_set(str(new_filepath))
                self.chat_history_tree.focus(str(new_filepath)); self.chat_history_tree.see(str(new_filepath))
            messagebox.showinfo("新しいチャット", f"新しいチャット '{new_filename}' を開始しました。", parent=self.root)
            self.chat_message_entry.focus_set()
        except Exception as e:
            self.log(f"新規チャットファイル作成エラー: {e}")
            messagebox.showerror("作成エラー", f"新規チャット作成失敗: {e}", parent=self.root)
            self.current_ai_chat_file_path = None


    def on_chat_history_selected_action(self, event=None):
        selected_items = self.chat_history_tree.selection()
        if not selected_items: self.current_ai_chat_file_path = None; return
        selected_file_path_str = selected_items[0] # iid はファイルパス文字列
        self.current_ai_chat_file_path = Path(selected_file_path_str)
        self.chat_content_tree.delete(*self.chat_content_tree.get_children())
        if not self.current_ai_chat_file_path.exists():
            messagebox.showwarning("ファイルエラー", "選択された履歴ファイルが見つかりません。", parent=self.root)
            self.current_ai_chat_file_path = None; self.load_chat_history_list(); return # リスト再読込
        try:
            with open(self.current_ai_chat_file_path, 'r', encoding='utf-8', newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                if reader.fieldnames != ['action', 'talker', 'words']:
                    messagebox.showerror("形式エラー", "CSVヘッダーが不正です。", parent=self.root); return
                for i, row in enumerate(reader):
                    if row.get('action') == 'talk':
                        self.chat_content_tree.insert('', 'end', values=(i + 1, row['talker'], row['words']), iid=str(i+1))
            if self.chat_content_tree.get_children():
                self.chat_content_tree.see(self.chat_content_tree.get_children()[-1]) # 最終行へスクロール
            self.log(f"チャット履歴読み込み: {self.current_ai_chat_file_path.name}")
        except Exception as e:
            messagebox.showerror("読み込みエラー", f"履歴読み込み失敗: {e}", parent=self.root)
            self.log(f"チャット履歴読み込みエラー: {e}")


    def _append_to_current_chat_csv(self, action, talker, words):
        if not self.current_ai_chat_file_path or not self.current_ai_chat_file_path.exists(): return
        try:
            with open(self.current_ai_chat_file_path, 'a', newline='', encoding='utf-8') as csvfile:
                csv.writer(csvfile).writerow([action, talker, words])
        except Exception as e: self.log(f"チャットCSV追記エラー: {e}")

    def _add_message_to_chat_display_tree(self, talker_display_name, message_content):
        # talker_display_name は "👤 ユーザー" や "🤖 AI"
        line_num = len(self.chat_content_tree.get_children()) + 1
        actual_talker = talker_display_name[2:] if talker_display_name.startswith(("👤 ", "🤖 ")) else talker_display_name
        item_id = self.chat_content_tree.insert('', 'end', values=(line_num, actual_talker, message_content), iid=str(line_num))
        self.chat_content_tree.see(item_id)


    def send_ai_chat_message_action(self, event=None):
        user_input = self.chat_message_entry.get().strip()
        if not user_input: return
        if not self.current_ai_chat_file_path or not self.current_ai_chat_file_path.exists():
            if messagebox.askyesno("チャット未開始", "チャットセッションがありません。新規作成しますか？", parent=self.root):
                self.start_new_ai_chat_session_action()
                if not self.current_ai_chat_file_path: return # 作成失敗時
            else: return

        ai_char_name_selected = self.ai_char_var.get()
        user_char_name_selected = self.user_char_var.get()
        if not ai_char_name_selected or not user_char_name_selected:
            messagebox.showwarning("キャラ未選択", "AIキャラとユーザーキャラを選択してください。", parent=self.root); return

        self._add_message_to_chat_display_tree(f"👤 {user_char_name_selected}", user_input)
        self._append_to_current_chat_csv('talk', user_char_name_selected, user_input)
        self.chat_message_entry.delete(0, tk.END)

        processing_mode = self.config.get_system_setting("ai_chat_processing_mode", "sequential")
        if processing_mode == "sequential" and self.play_user_speech_var.get():
            threading.Thread(target=self._play_user_speech_then_ai_response,
                             args=(user_char_name_selected, user_input, ai_char_name_selected), daemon=True).start()
        else: # parallel または sequentialでユーザー音声再生なし
            if self.play_user_speech_var.get(): # parallelでユーザー音声再生あり
                 threading.Thread(target=self._play_character_speech_async, args=(user_char_name_selected, user_input), daemon=True).start()
            # AI応答は常に別スレッドで
            threading.Thread(target=self._generate_and_handle_ai_response, args=(user_input, ai_char_name_selected, user_char_name_selected), daemon=True).start()


    def _play_user_speech_then_ai_response(self, user_char_name, user_text, ai_char_name_for_next):
        # ユーザー音声を再生し、完了後にAI応答生成をトリガー
        self._play_character_speech_async(user_char_name, user_text, block=True) # block=Trueで再生完了を待つ
        self._generate_and_handle_ai_response(user_text, ai_char_name_for_next, user_char_name)


    def _generate_and_handle_ai_response(self, user_input_text, ai_char_name, user_char_name_for_history):
        # AI応答を生成し、表示・保存・再生
        # このメソッドはスレッドで実行される
        ai_char_id = self.character_manager.get_character_id_by_name(ai_char_name)
        if not ai_char_id: self.log(f"AIキャラ '{ai_char_name}' ID見つからず"); return
        ai_char_data = self.character_manager.get_character(ai_char_id)
        if not ai_char_data: self.log(f"AIキャラ '{ai_char_name}' データ見つからず"); return

        try:
            api_key = self.config.get_system_setting("google_ai_api_key")
            if not api_key: self.root.after(0, self._add_message_to_chat_display_tree, f"🤖 {ai_char_name}", "Google APIキー未設定"); return

            client = genai.Client(api_key=api_key)
            ai_prompt = self.character_manager.get_character_prompt(ai_char_id)

            chat_history_for_prompt = [] # CSVから会話履歴を読み込む
            if self.current_ai_chat_file_path and self.current_ai_chat_file_path.exists():
                with open(self.current_ai_chat_file_path, 'r', encoding='utf-8') as f_hist:
                    reader = csv.DictReader(f_hist)
                    for row in reader:
                        if row.get('action') == 'talk':
                            speaker, msg = row.get('talker'), row.get('words')
                            prefix = "あなた" if speaker == ai_char_name else user_char_name_for_history
                            chat_history_for_prompt.append(f"{prefix}: {msg}")
            history_str = "\n".join(chat_history_for_prompt[-10:]) # 直近10件程度

            full_prompt = f"{ai_prompt}\n\n以下はこれまでの会話です:\n{history_str}\n\n{user_char_name_for_history}: {user_input_text}\n\nあなた ({ai_char_name}):"

            text_gen_model = self.config.get_system_setting("text_generation_model", "gemini-1.5-flash")
            ai_response_text = "エラー：応答取得失敗"

            if text_gen_model == "local_lm_studio":
                local_llm_url = self.config.get_system_setting("local_llm_endpoint_url")
                if not local_llm_url: ai_response_text = "ローカルLLMエンドポイントURL未設定"
                else: # 非同期で呼び出す
                    loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
                    try: ai_response_text = loop.run_until_complete(self._generate_response_local_llm_chat(full_prompt, local_llm_url, ai_char_name))
                    finally: loop.close()
            else:
                gemini_response = client.models.generate_content(model=text_gen_model, contents=full_prompt,
                                                               generation_config=genai_types.GenerateContentConfig(temperature=0.8, max_output_tokens=200))
                ai_response_text = gemini_response.text.strip() if gemini_response.text else "うーん、ちょっとうまく答えられないみたいです。"

            self.root.after(0, self._add_message_to_chat_display_tree, f"🤖 {ai_char_name}", ai_response_text)
            self._append_to_current_chat_csv('talk', ai_char_name, ai_response_text)
            self._play_character_speech_async(ai_char_name, ai_response_text)

        except genai_types.BlockedPromptException:
            self.root.after(0, self._add_message_to_chat_display_tree, f"🤖 {ai_char_name}", "その内容についてはお答えできません。")
        except Exception as e_gen:
            self.log(f"AI応答生成エラー: {e_gen}")
            self.root.after(0, self._add_message_to_chat_display_tree, f"🤖 {ai_char_name}", "ごめんなさい、ちょっと調子が悪いです。")


    async def _generate_response_local_llm_chat(self, prompt_text: str, endpoint_url: str, char_name: str) -> str:
        # debug_window.pyのものをベースに、aiohttpをこのファイルでimport
        try:
            import aiohttp
            payload = {"model": "local-model", "messages": [{"role": "user", "content": prompt_text}], "temperature": 0.7, "max_tokens": 200}
            async with aiohttp.ClientSession() as session:
                async with session.post(endpoint_url, json=payload, headers={"Content-Type": "application/json"}, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                    resp_text = await resp.text()
                    resp.raise_for_status()
                    data = json.loads(resp_text)
                    if data.get("choices") and data["choices"][0].get("message"):
                        return data["choices"][0]["message"].get("content", "").strip()
            return "ローカルLLM応答形式エラー(詳細不明)"
        except Exception as e_llm:
            self.log(f"ローカルLLM呼び出しエラー ({char_name}, {endpoint_url}): {e_llm}")
            return f"ローカルLLM呼び出しエラー: {e_llm}"


    def _play_character_speech_async(self, char_name, text, block=False):
        # 指定キャラの音声設定でテキストを再生 (非同期スレッドで)
        char_id = self.character_manager.get_character_id_by_name(char_name)
        if not char_id: self.log(f"音声再生エラー: キャラ '{char_name}' IDなし"); return
        char_data = self.character_manager.get_character(char_id)
        if not char_data: self.log(f"音声再生エラー: キャラ '{char_name}' データなし"); return

        voice_settings = char_data.get('voice_settings', {})
        engine = voice_settings.get('engine', self.config.get_system_setting("voice_engine"))
        model = voice_settings.get('model')
        speed = voice_settings.get('speed', 1.0)
        api_key = self.config.get_system_setting("google_ai_api_key") if "google_ai_studio" in engine else None

        def run_synthesis_and_play():
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            try:
                audio_files = loop.run_until_complete(
                    self.voice_manager.synthesize_with_fallback(text, model, speed, preferred_engine=engine, api_key=api_key)
                )
                if audio_files:
                    loop.run_until_complete(self.audio_player.play_audio_files(audio_files))
                else: self.log(f"音声合成失敗 ({char_name}: '{text[:20]}...')")
            except Exception as e_play: self.log(f"音声再生処理エラー ({char_name}): {e_play}")
            finally: loop.close()

        if block: # 同期的に実行（再生完了まで待つ）
            run_synthesis_and_play()
        else: # 非同期スレッドで実行
            threading.Thread(target=run_synthesis_and_play, daemon=True).start()


    def delete_selected_chat_message_action(self):
        selected_items = self.chat_content_tree.selection()
        if not selected_items: messagebox.showwarning("削除エラー", "削除する行を選択してください。", parent=self.root); return
        selected_tree_iid = selected_items[0] # TreeViewのiid (1始まりの行番号文字列)
        try:
            line_num_in_tree = int(selected_tree_iid)
            values = self.chat_content_tree.item(selected_tree_iid, 'values')
            talker_preview, words_preview = values[1], values[2][:20]
            if not messagebox.askyesno("削除確認", f"行 {line_num_in_tree} ({talker_preview}: \"{words_preview}...\") を削除しますか？\nファイルからも削除され元に戻せません。", parent=self.root): return

            if not self.current_ai_chat_file_path or not self.current_ai_chat_file_path.exists():
                messagebox.showerror("ファイルエラー", "チャット履歴ファイルが見つかりません。", parent=self.root); return

            temp_lines = []
            deleted_from_csv = False
            # CSVファイルから該当行を削除 (ヘッダーを考慮し、'talk'アクションの行だけをカウント)
            talk_action_count = 0
            with open(self.current_ai_chat_file_path, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                header = next(reader); temp_lines.append(header)
                for row_idx, row_content in enumerate(reader):
                    is_target_row_in_csv = False
                    if row_content and len(row_content) >=1 and row_content[0] == 'talk':
                        talk_action_count +=1
                        if talk_action_count == line_num_in_tree:
                            is_target_row_in_csv = True
                    if not is_target_row_in_csv: temp_lines.append(row_content)
                    else: deleted_from_csv = True

            if deleted_from_csv:
                with open(self.current_ai_chat_file_path, 'w', newline='', encoding='utf-8') as csvfile:
                    csv.writer(csvfile).writerows(temp_lines)
                self.log(f"チャット行削除: ファイル {self.current_ai_chat_file_path.name} から TreeView行 {line_num_in_tree} に対応するデータを削除")
                # TreeViewから削除し再描画 (on_chat_history_selected_action を呼ぶのが簡単)
                self.on_chat_history_selected_action() # これでTreeviewが更新される
                messagebox.showinfo("削除完了", "選択行を削除しました。", parent=self.root)
            else:
                messagebox.showerror("削除エラー", "CSVファイル内で対応する行が見つかりませんでした。", parent=self.root)
        except ValueError: messagebox.showerror("削除エラー", "行番号が無効です。", parent=self.root)
        except Exception as e_del:
            self.log(f"チャット行削除エラー: {e_del}")
            messagebox.showerror("削除エラー", f"予期せぬエラー: {e_del}", parent=self.root)


def main():
    root = tk.Tk()
    app = AIChatWindow(root)
    root.mainloop()

if __name__ == "__main__":
    main()
