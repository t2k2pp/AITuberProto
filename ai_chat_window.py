import customtkinter
import tkinter as tk # 基本的な型 (StringVarなど) と標準ダイアログのため
from tkinter import ttk, messagebox, filedialog # Treeviewと標準ダイアログはそのまま使用
import csv
import os
import sys # フォント選択のため
from pathlib import Path
from datetime import datetime
import asyncio
import threading
import json # _generate_response_local_llm_chat で使用

from config import ConfigManager
from character_manager import CharacterManager
from audio_manager import VoiceEngineManager, AudioPlayer
from google import genai
from google.genai import types as genai_types
from communication_logger import CommunicationLogger # 追加

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AIChatWindow:
    def __init__(self, root: customtkinter.CTk):
        self.root = root
        self.root.title("AIチャット")
        self.root.geometry("1000x750") # サイズ調整

        self.config = ConfigManager()
        self.character_manager = CharacterManager(self.config)
        self.voice_manager = VoiceEngineManager()
        self.audio_player = AudioPlayer(config_manager=self.config)
        self.communication_logger = CommunicationLogger() # 追加

        self.ai_chat_history_folder = Path(self.config.config_file).parent / "ai_chat_history"
        try:
            self.ai_chat_history_folder.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"AIチャット履歴フォルダの作成失敗: {e}")
            messagebox.showerror("フォルダ作成エラー", f"AIチャット履歴フォルダ作成失敗: {e}", parent=self.root)

        self.current_ai_chat_file_path = None

        # フォント設定
        self.default_font = ("Yu Gothic UI", 12)
        if sys.platform == "darwin": self.default_font = ("Hiragino Sans", 14)
        elif sys.platform.startswith("linux"): self.default_font = ("Noto Sans CJK JP", 12)
        self.treeview_font = (self.default_font[0], self.default_font[1] -1) # Treeviewは少し小さめ

        self.create_widgets()
        self.populate_chat_character_dropdowns()
        self.load_chat_history_list()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.log("AIチャットウィンドウが初期化されました。")

    def log(self, message):
        logger.info(message)

    def on_closing(self):
        self.root.destroy()

    def create_widgets(self):
        # ttk.PanedWindow の代替として、2つのCTkFrameを配置し、中間に手動でリサイズ機能を追加するか、
        # もしくは固定比率で分割する。ここでは固定比率で分割するアプローチを採る。
        # 左側のフレーム (会話履歴)
        history_panel = customtkinter.CTkFrame(self.root, width=300) # 幅を指定
        history_panel.pack(side="left", fill="y", padx=(10,5), pady=10)
        history_panel.pack_propagate(False) # widthが効くように

        # 右側のフレーム (会話エリア)
        chat_panel = customtkinter.CTkFrame(self.root)
        chat_panel.pack(side="left", fill="both", expand=True, padx=(5,10), pady=10)

        # --- 左側: 会話履歴一覧 ---
        customtkinter.CTkLabel(history_panel, text="会話履歴", font=(self.default_font[0], self.default_font[1]+2, "bold")).pack(pady=5)

        tree_frame = customtkinter.CTkFrame(history_panel) # TreeviewとScrollbarをまとめるフレーム
        tree_frame.pack(fill="both", expand=True, padx=5, pady=(0,5))

        # ttk.Treeview はそのまま使用。スタイル調整を試みる。
        style = ttk.Style()
        # Treeviewの見た目をCustomTkinterに合わせるための設定 (限定的)
        # 'clam', 'alt', 'default', 'classic' など試す。'clam' が比較的フラット。
        style.theme_use('clam')
        style.configure("Treeview.Heading", font=(self.treeview_font[0], self.treeview_font[1], "bold"))
        style.configure("Treeview", font=self.treeview_font, rowheight=int(self.treeview_font[1]*2.0)) # 行の高さを調整
        # Treeviewの背景色や文字色をCustomTkinterのテーマから取得して設定することも検討できるが複雑になる。
        # ここでは基本的なフォントとテーマの適用に留める。

        self.chat_history_tree = ttk.Treeview(tree_frame, columns=('filename', 'last_updated'), show='headings', style="Treeview")
        self.chat_history_tree.heading('filename', text='会話ログ')
        self.chat_history_tree.heading('last_updated', text='最終更新日時')
        self.chat_history_tree.column('filename', width=120, stretch=tk.YES)
        self.chat_history_tree.column('last_updated', width=120, stretch=tk.YES)
        self.chat_history_tree.bind('<<TreeviewSelect>>', self.on_chat_history_selected_action)

        # CTkScrollbar を ttk.Treeview に適用
        # Treeviewはcustomtkinterウィジェットではないため、CTkScrollbarを直接commandに設定できない。
        # ttk.Scrollbar を使用する。
        chat_history_scroll_y = ttk.Scrollbar(tree_frame, orient="vertical", command=self.chat_history_tree.yview)
        self.chat_history_tree.configure(yscrollcommand=chat_history_scroll_y.set)

        chat_history_scroll_y.pack(side="right", fill="y")
        self.chat_history_tree.pack(side="left", fill="both", expand=True)

        customtkinter.CTkButton(history_panel, text="新しいチャットを開始", command=self.start_new_ai_chat_session_action, font=self.default_font).pack(side="bottom", fill="x", padx=5, pady=5)

        # --- 右側: 会話エリア ---
        chat_config_frame = customtkinter.CTkFrame(chat_panel, fg_color="transparent")
        chat_config_frame.pack(fill="x", pady=5, padx=5)

        customtkinter.CTkLabel(chat_config_frame, text="AIキャラ:", font=self.default_font).grid(row=0, column=0, padx=2, pady=2, sticky="w")
        self.ai_char_var = tk.StringVar()
        self.ai_char_combo = customtkinter.CTkComboBox(chat_config_frame, variable=self.ai_char_var, state="readonly", width=150, font=self.default_font)
        self.ai_char_combo.grid(row=0, column=1, padx=2, pady=2, sticky="w")

        customtkinter.CTkLabel(chat_config_frame, text="ユーザーキャラ:", font=self.default_font).grid(row=0, column=2, padx=(10,2), pady=2, sticky="w")
        self.user_char_var = tk.StringVar()
        self.user_char_combo = customtkinter.CTkComboBox(chat_config_frame, variable=self.user_char_var, state="readonly", width=150, font=self.default_font)
        self.user_char_combo.grid(row=0, column=3, padx=2, pady=2, sticky="w")

        self.play_user_speech_var = tk.BooleanVar(value=True)
        customtkinter.CTkCheckBox(chat_config_frame, text="ユーザー発話再生", variable=self.play_user_speech_var, font=self.default_font).grid(row=0, column=4, padx=10, pady=2, sticky="w")

        # 会話内容表示 (LabelFrame -> CTkFrame + CTkLabel)
        chat_display_outer_frame = customtkinter.CTkFrame(chat_panel)
        chat_display_outer_frame.pack(fill="both", expand=True, pady=5, padx=5)
        customtkinter.CTkLabel(chat_display_outer_frame, text="会話内容", font=(self.default_font[0], self.default_font[1]+1, "bold")).pack(anchor="w", padx=10, pady=(5,0))
        chat_display_container = customtkinter.CTkFrame(chat_display_outer_frame)
        chat_display_container.pack(fill="both", expand=True, padx=5, pady=5)

        # ttk.Treeview for chat content
        self.chat_content_tree = ttk.Treeview(chat_display_container, columns=('line', 'talker', 'words'), show='headings', style="Treeview")
        self.chat_content_tree.heading('line', text='行')
        self.chat_content_tree.heading('talker', text='話者')
        self.chat_content_tree.heading('words', text='発言内容')
        self.chat_content_tree.column('line', width=40, anchor="center", stretch=tk.NO)
        self.chat_content_tree.column('talker', width=100, stretch=tk.NO)
        self.chat_content_tree.column('words', width=350, stretch=tk.YES) # words列が拡張

        chat_content_scroll_y = ttk.Scrollbar(chat_display_container, orient="vertical", command=self.chat_content_tree.yview)
        chat_content_scroll_x = ttk.Scrollbar(chat_display_container, orient="horizontal", command=self.chat_content_tree.xview)
        self.chat_content_tree.configure(yscrollcommand=chat_content_scroll_y.set, xscrollcommand=chat_content_scroll_x.set)

        chat_content_scroll_y.pack(side="right", fill="y")
        chat_content_scroll_x.pack(side="bottom", fill="x")
        self.chat_content_tree.pack(side="left", fill="both", expand=True)

        # Treeviewの幅変更で列幅を調整する機能はそのまま
        self.chat_content_tree.bind('<Configure>', lambda e: self._adjust_chat_words_column_width(e, self.chat_content_tree))

        # Context Menu (tk.Menuはそのまま使用)
        self.chat_content_context_menu = tk.Menu(self.chat_content_tree, tearoff=0)
        self.chat_content_context_menu.add_command(label="選択行を削除", command=self.delete_selected_chat_message_action)
        self.chat_content_tree.bind("<Button-3>", self._show_chat_content_context_menu)

        # 入力エリア
        chat_input_frame = customtkinter.CTkFrame(chat_panel, fg_color="transparent")
        chat_input_frame.pack(fill="x", pady=5, padx=5)
        self.chat_message_entry = customtkinter.CTkEntry(chat_input_frame, placeholder_text="メッセージを入力...", width=300, font=self.default_font)
        self.chat_message_entry.bind("<Return>", self.send_ai_chat_message_action)
        self.chat_message_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        customtkinter.CTkButton(chat_input_frame, text="送信", command=self.send_ai_chat_message_action, font=self.default_font, width=80).pack(side="left")

    def _adjust_chat_words_column_width(self, event, treeview_widget):
        other_cols_width = treeview_widget.column('line')['width'] + treeview_widget.column('talker')['width']
        # スクロールバーの幅を考慮 (おおよそ)
        scrollbar_width_approx = 20 if treeview_widget.winfo_exists() and treeview_widget.yview() != ('0.0', '1.0') else 0
        new_width = event.width - other_cols_width - scrollbar_width_approx - 5 # 微調整用
        if new_width > 100: treeview_widget.column('words', width=new_width)

    def _show_chat_content_context_menu(self, event):
        item_id = self.chat_content_tree.identify_row(event.y)
        if item_id:
            self.chat_content_tree.selection_set(item_id)
            self.chat_content_context_menu.post(event.x_root, event.y_root)

    def populate_chat_character_dropdowns(self):
        all_chars_data = self.character_manager.get_all_characters()
        char_names = [data.get('name', 'Unknown') for data in all_chars_data.values()]

        self.ai_char_combo.configure(values=char_names if char_names else ["キャラクターなし"])
        self.user_char_combo.configure(values=char_names if char_names else ["キャラクターなし"])

        if char_names:
            saved_ai_char = self.config.get_system_setting("ai_chat_default_ai_char_name")
            saved_user_char = self.config.get_system_setting("ai_chat_default_user_char_name")

            if saved_ai_char and saved_ai_char in char_names: self.ai_char_var.set(saved_ai_char)
            else: self.ai_char_var.set(char_names[0])

            if saved_user_char and saved_user_char in char_names: self.user_char_var.set(saved_user_char)
            elif len(char_names) > 1 : self.user_char_var.set(char_names[1] if self.ai_char_var.get() == char_names[0] else char_names[0])
            elif char_names : self.user_char_var.set(char_names[0])
        else:
            self.ai_char_var.set("キャラクターなし")
            self.user_char_var.set("キャラクターなし")
        self.log("AIチャット: キャラクタープルダウン更新")

    def load_chat_history_list(self):
        self.chat_history_tree.delete(*self.chat_history_tree.get_children())
        if not self.ai_chat_history_folder.exists(): return
        history_files_data = []
        for item_path in self.ai_chat_history_folder.iterdir():
            if item_path.is_file() and item_path.suffix.lower() == '.csv':
                try:
                    last_mod_dt = datetime.fromtimestamp(item_path.stat().st_mtime)
                    history_files_data.append({"path": item_path, "name": item_path.name, "dt": last_mod_dt, "dt_str": last_mod_dt.strftime('%Y-%m-%d %H:%M')}) # 秒を削除
                except Exception as e_stat: self.log(f"履歴ファイル情報取得エラー {item_path.name}: {e_stat}")
        history_files_data.sort(key=lambda x: x["dt"], reverse=True)
        for entry in history_files_data:
            self.chat_history_tree.insert('', 'end', values=(entry["name"], entry["dt_str"]), iid=str(entry["path"]))
        self.log(f"AIチャット: 会話履歴一覧更新 ({len(history_files_data)}件)")

    def start_new_ai_chat_session_action(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_filename = f"chat_{timestamp}.csv"
        new_filepath = self.ai_chat_history_folder / new_filename
        try:
            with open(new_filepath, 'w', newline='', encoding='utf-8') as csvfile:
                csv.writer(csvfile).writerow(['action', 'talker', 'words'])
            self.log(f"新規チャットセッションファイル作成: {new_filepath}")
            self.current_ai_chat_file_path = new_filepath
            self.chat_content_tree.delete(*self.chat_content_tree.get_children())
            self.load_chat_history_list()
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
        if not selected_items:
            self.current_ai_chat_file_path = None
            return
        selected_file_path_str = selected_items[0]
        self.current_ai_chat_file_path = Path(selected_file_path_str)
        self.chat_content_tree.delete(*self.chat_content_tree.get_children())
        if not self.current_ai_chat_file_path.exists():
            messagebox.showwarning("ファイルエラー", "選択された履歴ファイルが見つかりません。", parent=self.root)
            self.current_ai_chat_file_path = None
            self.load_chat_history_list()
            return
        try:
            with open(self.current_ai_chat_file_path, 'r', encoding='utf-8', newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                if reader.fieldnames != ['action', 'talker', 'words']:
                    messagebox.showerror("形式エラー", "CSVヘッダーが不正です。", parent=self.root)
                    return
                for i, row in enumerate(reader):
                    if row.get('action') == 'talk':
                        self.chat_content_tree.insert('', 'end', values=(i + 1, row['talker'], row['words']), iid=str(i+1))
            if self.chat_content_tree.get_children():
                self.chat_content_tree.see(self.chat_content_tree.get_children()[-1])
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
                if not self.current_ai_chat_file_path: return
            else: return

        ai_char_name_selected = self.ai_char_var.get()
        user_char_name_selected = self.user_char_var.get()
        if not ai_char_name_selected or not user_char_name_selected or "キャラクターなし" in [ai_char_name_selected, user_char_name_selected]:
            messagebox.showwarning("キャラ未選択", "AIキャラとユーザーキャラを選択してください。", parent=self.root); return

        self._add_message_to_chat_display_tree(f"👤 {user_char_name_selected}", user_input)
        self._append_to_current_chat_csv('talk', user_char_name_selected, user_input)
        self.chat_message_entry.delete(0, "end") # tk.END -> "end" for CTkEntry

        processing_mode = self.config.get_system_setting("ai_chat_processing_mode", "sequential")
        if processing_mode == "sequential" and self.play_user_speech_var.get():
            threading.Thread(target=self._play_user_speech_then_ai_response,
                             args=(user_char_name_selected, user_input, ai_char_name_selected), daemon=True).start()
        else:
            if self.play_user_speech_var.get():
                 threading.Thread(target=self._play_character_speech_async, args=(user_char_name_selected, user_input), daemon=True).start()
            threading.Thread(target=self._generate_and_handle_ai_response, args=(user_input, ai_char_name_selected, user_char_name_selected), daemon=True).start()

    def _play_user_speech_then_ai_response(self, user_char_name, user_text, ai_char_name_for_next):
        self._play_character_speech_async(user_char_name, user_text, block=True)
        self._generate_and_handle_ai_response(user_text, ai_char_name_for_next, user_char_name)

    def _generate_and_handle_ai_response(self, user_input_text, ai_char_name, user_char_name_for_history):
        ai_char_id = self.character_manager.get_character_id_by_name(ai_char_name)
        if not ai_char_id: self.log(f"AIキャラ '{ai_char_name}' ID見つからず"); return
        ai_char_data = self.character_manager.get_character(ai_char_id)
        if not ai_char_data: self.log(f"AIキャラ '{ai_char_name}' データ見つからず"); return

        try:
            api_key = self.config.get_system_setting("google_ai_api_key")
            if not api_key:
                self.root.after(0, self._add_message_to_chat_display_tree, f"🤖 {ai_char_name}", "Google APIキー未設定")
                return

            client = genai.Client(api_key=api_key)
            ai_prompt = self.character_manager.get_character_prompt(ai_char_id)
            chat_history_for_prompt = []
            if self.current_ai_chat_file_path and self.current_ai_chat_file_path.exists():
                with open(self.current_ai_chat_file_path, 'r', encoding='utf-8') as f_hist:
                    reader = csv.DictReader(f_hist)
                    for row in reader:
                        if row.get('action') == 'talk':
                            speaker, msg = row.get('talker'), row.get('words')
                            prefix = "あなた" if speaker == ai_char_name else user_char_name_for_history
                            chat_history_for_prompt.append(f"{prefix}: {msg}")
            history_str = "\n".join(chat_history_for_prompt[-10:])
            full_prompt = f"{ai_prompt}\n\n以下はこれまでの会話です:\n{history_str}\n\n{user_char_name_for_history}: {user_input_text}\n\nあなた ({ai_char_name}):"
            text_gen_model = self.config.get_system_setting("text_generation_model", "gemini-1.5-flash")
            ai_response_text = "エラー：応答取得失敗" # デフォルトのエラーメッセージ

            # ログ記録: AIへのリクエスト
            self.communication_logger.add_log("sent", "text_generation", f"[AI Chat to {ai_char_name} (Model: {text_gen_model})]\n{full_prompt}")

            if text_gen_model == "local_lm_studio":
                local_llm_url = self.config.get_system_setting("local_llm_endpoint_url")
                if not local_llm_url:
                    ai_response_text = "ローカルLLMエンドポイントURL未設定"
                else:
                    loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
                    try:
                        ai_response_text = loop.run_until_complete(self._generate_response_local_llm_chat(full_prompt, local_llm_url, ai_char_name))
                    finally:
                        loop.close()
            else:
                gemini_response = client.models.generate_content(model=text_gen_model, contents=full_prompt,
                                                               generation_config=genai_types.GenerateContentConfig(temperature=0.8, max_output_tokens=200))
                ai_response_text = gemini_response.text.strip() if gemini_response.text else "うーん、ちょっとうまく答えられないみたいです。"

            # ログ記録: AIからのレスポンス
            self.communication_logger.add_log("received", "text_generation", f"[AI Chat from {ai_char_name} (Model: {text_gen_model})]\n{ai_response_text}")

            self.root.after(0, self._add_message_to_chat_display_tree, f"🤖 {ai_char_name}", ai_response_text)
            self._append_to_current_chat_csv('talk', ai_char_name, ai_response_text)
            self._play_character_speech_async(ai_char_name, ai_response_text) # この中で音声合成ログが記録される

        except genai_types.BlockedPromptException as e_block:
            ai_response_text = "その内容についてはお答えできません。"
            self.communication_logger.add_log("received", "text_generation", f"[AI Chat from {ai_char_name} (Model: {text_gen_model}) - Blocked]\n{str(e_block)}")
            self.root.after(0, self._add_message_to_chat_display_tree, f"🤖 {ai_char_name}", ai_response_text)
        except Exception as e_gen:
            ai_response_text = "ごめんなさい、ちょっと調子が悪いです。" # エラー時のレスポンスを更新
            self.log(f"AI応答生成エラー: {e_gen}")
            self.communication_logger.add_log("received", "text_generation", f"[AI Chat from {ai_char_name} (Model: {text_gen_model}) - Error]\n{str(e_gen)}")
            self.root.after(0, self._add_message_to_chat_display_tree, f"🤖 {ai_char_name}", ai_response_text)


    async def _generate_response_local_llm_chat(self, prompt_text: str, endpoint_url: str, char_name: str) -> str:
        # このメソッド内での個別ロギングは呼び出し元に任せる
        try:
            import aiohttp # aiohttpのimportを確認
            payload = {"model": "local-model", "messages": [{"role": "user", "content": prompt_text}], "temperature": 0.7, "max_tokens": 200}
            async with aiohttp.ClientSession() as session:
                async with session.post(endpoint_url, json=payload, headers={"Content-Type": "application/json"}, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                    resp_text = await resp.text()
                    resp.raise_for_status()
                    data = json.loads(resp_text) # jsonをインポート
                    if data.get("choices") and data["choices"][0].get("message"):
                        return data["choices"][0]["message"].get("content", "").strip()
            return "ローカルLLM応答形式エラー(詳細不明)"
        except Exception as e_llm:
            self.log(f"ローカルLLM呼び出しエラー ({char_name}, {endpoint_url}): {e_llm}")
            return f"ローカルLLM呼び出しエラー: {e_llm}"

    def _play_character_speech_async(self, char_name, text, block=False):
        char_id = self.character_manager.get_character_id_by_name(char_name)
        if not char_id: self.log(f"音声再生エラー: キャラ '{char_name}' IDなし"); return
        char_data = self.character_manager.get_character(char_id)
        if not char_data: self.log(f"音声再生エラー: キャラ '{char_name}' データなし"); return

        voice_settings = char_data.get('voice_settings', {})
        engine = voice_settings.get('engine', self.config.get_system_setting("voice_engine"))
        model = voice_settings.get('model')
        speed = voice_settings.get('speed', 1.0)
        api_key = self.config.get_system_setting("google_ai_api_key") if "google_ai_studio" in engine else None

        # ログ記録: 音声合成リクエスト
        self.communication_logger.add_log("sent", "voice_synthesis", f"[AI Chat Voice for {char_name} (Engine: {engine}, Model: {model})]\n{text}")

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

        if block:
            run_synthesis_and_play()
        else:
            threading.Thread(target=run_synthesis_and_play, daemon=True).start()

    def delete_selected_chat_message_action(self):
        selected_items = self.chat_content_tree.selection()
        if not selected_items: messagebox.showwarning("削除エラー", "削除する行を選択してください。", parent=self.root); return
        selected_tree_iid = selected_items[0]
        try:
            line_num_in_tree = int(selected_tree_iid)
            values = self.chat_content_tree.item(selected_tree_iid, 'values')
            talker_preview, words_preview = values[1], values[2][:20]
            if not messagebox.askyesno("削除確認", f"行 {line_num_in_tree} ({talker_preview}: \"{words_preview}...\") を削除しますか？\nファイルからも削除され元に戻せません。", parent=self.root): return

            if not self.current_ai_chat_file_path or not self.current_ai_chat_file_path.exists():
                messagebox.showerror("ファイルエラー", "チャット履歴ファイルが見つかりません。", parent=self.root); return

            temp_lines = []
            deleted_from_csv = False
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
                self.on_chat_history_selected_action()
                messagebox.showinfo("削除完了", "選択行を削除しました。", parent=self.root)
            else:
                messagebox.showerror("削除エラー", "CSVファイル内で対応する行が見つかりませんでした。", parent=self.root)
        except ValueError: messagebox.showerror("削除エラー", "行番号が無効です。", parent=self.root)
        except Exception as e_del:
            self.log(f"チャット行削除エラー: {e_del}")
            messagebox.showerror("削除エラー", f"予期せぬエラー: {e_del}", parent=self.root)

def main():
    # customtkinterの初期設定
    customtkinter.set_appearance_mode("System")
    customtkinter.set_default_color_theme("blue")

    root = customtkinter.CTk() # ルートウィンドウをCTkで作成
    app = AIChatWindow(root)
    root.mainloop()

if __name__ == "__main__":
    # このファイルが直接実行された場合の処理
    customtkinter.set_appearance_mode("System")
    customtkinter.set_default_color_theme("blue")
    main()
