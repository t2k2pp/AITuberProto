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
from mcp_client import MCPClientManager # MCPクライアントマネージャーをインポート
import i18n_setup # 追加

import logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s') # main.py等で設定想定
logger = logging.getLogger(__name__)

class AIChatWindow:
    def __init__(self, root: customtkinter.CTk):
        i18n_setup.init_i18n() # 強制再初期化
        self._ = i18n_setup.get_translator()

        self.root = root
        self.root.title(self._("ai_chat.title"))
        self.root.geometry("1000x750")

        self.loading_label = customtkinter.CTkLabel(self.root, text=self._("ai_chat.loading"), font=("Yu Gothic UI", 18))
        self.loading_label.pack(expand=True, fill="both")
        self.root.update_idletasks()

        self.root.after(50, self._initialize_components)

    def _initialize_components(self):
        if hasattr(self, 'loading_label') and self.loading_label.winfo_exists():
            self.loading_label.pack_forget()
            self.loading_label.destroy()

        self.config = ConfigManager()
        self.character_manager = CharacterManager(self.config)
        self.voice_manager = VoiceEngineManager()
        self.audio_player = AudioPlayer(config_manager=self.config)
        self.communication_logger = CommunicationLogger() # 追加
        self.mcp_client_manager = MCPClientManager(config_manager=self.config) # MCPクライアントマネージャー初期化

        self.ai_chat_history_folder = Path(self.config.config_file).parent / "ai_chat_history"
        try:
            self.ai_chat_history_folder.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(self._("ai_chat.error.history_folder_creation_failed", e=e))
            # messagebox は _initialize_components 内で表示する方が安全
            # messagebox.showerror(self._("ai_chat.messagebox.folder_creation_error.title"), self._("ai_chat.error.history_folder_creation_failed", e=e), parent=self.root)

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

        # MCPサーバーの初期化を別スレッドで実行
        threading.Thread(target=self._initialize_mcp_servers_async, daemon=True).start()

        self.log(self._("ai_chat.log.init_completed"))
        # エラー発生時のメッセージボックス表示 (もしあれば)
        if not self.ai_chat_history_folder.exists():
             messagebox.showerror(self._("ai_chat.messagebox.folder_creation_error.title"), self._("ai_chat.messagebox.folder_creation_error.message", path=self.ai_chat_history_folder), parent=self.root)

    def _initialize_mcp_servers_async(self):
        """MCPサーバーの初期化を非同期で行う"""
        self.log(self._("ai_chat.log.mcp_server_init_start"))
        try:
            # MCPClientManagerのメソッドがasyncなので、新しいイベントループで実行
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.mcp_client_manager.initialize_servers_from_config())
            loop.close()
            self.log(self._("ai_chat.log.mcp_server_init_success"))
        except Exception as e:
            self.log(self._("ai_chat.log.mcp_server_init_error", error=e))
            # UIスレッドでエラーメッセージを表示する場合は self.root.after を使用
            # self.root.after(0, lambda: messagebox.showerror("MCP Error", f"MCPサーバーの初期化に失敗: {e}", parent=self.root))


    def log(self, message):
        # AIChatWindow の log メソッドはUIウィジェットに書き込まないため、
        # 呼び出しタイミングに特に注意は不要。
        # ただし、渡される message が翻訳済みであることを期待する
        logger.info(message)

    def on_closing(self):
        self.log(self._("ai_chat.log.shutting_down_mcp"))
        try:
            # MCPクライアントのシャットダウン (非同期)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.mcp_client_manager.shutdown())
            loop.close()
            self.log(self._("ai_chat.log.mcp_shutdown_complete"))
        except Exception as e:
            self.log(self._("ai_chat.log.mcp_shutdown_error", error=e))
        finally:
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
        customtkinter.CTkLabel(history_panel, text=self._("ai_chat.label.chat_history"), font=(self.default_font[0], self.default_font[1]+2, "bold")).pack(pady=5)

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
        self.chat_history_tree.heading('filename', text=self._("ai_chat.history_tree.header.filename"))
        self.chat_history_tree.heading('last_updated', text=self._("ai_chat.history_tree.header.last_updated"))
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

        customtkinter.CTkButton(history_panel, text=self._("ai_chat.button.start_new_chat"), command=self.start_new_ai_chat_session_action, font=self.default_font).pack(side="bottom", fill="x", padx=5, pady=5)

        # --- 右側: 会話エリア ---
        chat_config_frame = customtkinter.CTkFrame(chat_panel, fg_color="transparent")
        chat_config_frame.pack(fill="x", pady=5, padx=5)

        customtkinter.CTkLabel(chat_config_frame, text=self._("ai_chat.label.ai_character"), font=self.default_font).grid(row=0, column=0, padx=2, pady=2, sticky="w")
        self.ai_char_var = tk.StringVar()
        self.ai_char_combo = customtkinter.CTkComboBox(chat_config_frame, variable=self.ai_char_var, state="readonly", width=150, font=self.default_font)
        self.ai_char_combo.grid(row=0, column=1, padx=2, pady=2, sticky="w")

        customtkinter.CTkLabel(chat_config_frame, text=self._("ai_chat.label.user_character"), font=self.default_font).grid(row=0, column=2, padx=(10,2), pady=2, sticky="w")
        self.user_char_var = tk.StringVar()
        self.user_char_combo = customtkinter.CTkComboBox(chat_config_frame, variable=self.user_char_var, state="readonly", width=150, font=self.default_font)
        self.user_char_combo.grid(row=0, column=3, padx=2, pady=2, sticky="w")

        self.play_user_speech_var = tk.BooleanVar(value=True)
        customtkinter.CTkCheckBox(chat_config_frame, text=self._("ai_chat.checkbox.play_user_speech"), variable=self.play_user_speech_var, font=self.default_font).grid(row=0, column=4, padx=10, pady=2, sticky="w")

        # 会話内容表示 (LabelFrame -> CTkFrame + CTkLabel)
        chat_display_outer_frame = customtkinter.CTkFrame(chat_panel)
        chat_display_outer_frame.pack(fill="both", expand=True, pady=5, padx=5)
        customtkinter.CTkLabel(chat_display_outer_frame, text=self._("ai_chat.label.chat_content"), font=(self.default_font[0], self.default_font[1]+1, "bold")).pack(anchor="w", padx=10, pady=(5,0))
        chat_display_container = customtkinter.CTkFrame(chat_display_outer_frame)
        chat_display_container.pack(fill="both", expand=True, padx=5, pady=5)

        # ttk.Treeview for chat content
        self.chat_content_tree = ttk.Treeview(chat_display_container, columns=('line', 'talker', 'words'), show='headings', style="Treeview")
        self.chat_content_tree.heading('line', text=self._("ai_chat.content_tree.header.line"))
        self.chat_content_tree.heading('talker', text=self._("ai_chat.content_tree.header.talker"))
        self.chat_content_tree.heading('words', text=self._("ai_chat.content_tree.header.words"))
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
        self.chat_content_context_menu.add_command(label=self._("ai_chat.context_menu.delete_selected_row"), command=self.delete_selected_chat_message_action)
        self.chat_content_tree.bind("<Button-3>", self._show_chat_content_context_menu)

        # 入力エリア
        chat_input_frame = customtkinter.CTkFrame(chat_panel, fg_color="transparent")
        chat_input_frame.pack(fill="x", pady=5, padx=5)
        self.chat_message_entry = customtkinter.CTkEntry(chat_input_frame, placeholder_text=self._("ai_chat.entry.placeholder.message_input"), width=300, font=self.default_font)
        self.chat_message_entry.bind("<Return>", self.send_ai_chat_message_action)
        self.chat_message_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        customtkinter.CTkButton(chat_input_frame, text=self._("ai_chat.button.send"), command=self.send_ai_chat_message_action, font=self.default_font, width=80).pack(side="left")

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
        char_names = [data.get('name', self._("ai_chat.dropdown.unknown_character_name")) for data in all_chars_data.values()]
        no_char_text = self._("ai_chat.dropdown.no_character")

        self.ai_char_combo.configure(values=char_names if char_names else [no_char_text])
        self.user_char_combo.configure(values=char_names if char_names else [no_char_text])

        if char_names:
            saved_ai_char = self.config.get_system_setting("ai_chat_default_ai_char_name")
            saved_user_char = self.config.get_system_setting("ai_chat_default_user_char_name")

            if saved_ai_char and saved_ai_char in char_names: self.ai_char_var.set(saved_ai_char)
            else: self.ai_char_var.set(char_names[0])

            if saved_user_char and saved_user_char in char_names: self.user_char_var.set(saved_user_char)
            elif len(char_names) > 1 : self.user_char_var.set(char_names[1] if self.ai_char_var.get() == char_names[0] else char_names[0])
            elif char_names : self.user_char_var.set(char_names[0])
        else:
            self.ai_char_var.set(no_char_text)
            self.user_char_var.set(no_char_text)
        self.log(self._("ai_chat.log.character_dropdown_updated"))

    def load_chat_history_list(self):
        self.chat_history_tree.delete(*self.chat_history_tree.get_children())
        if not self.ai_chat_history_folder.exists(): return
        history_files_data = []
        for item_path in self.ai_chat_history_folder.iterdir():
            if item_path.is_file() and item_path.suffix.lower() == '.csv':
                try:
                    last_mod_dt = datetime.fromtimestamp(item_path.stat().st_mtime)
                    history_files_data.append({"path": item_path, "name": item_path.name, "dt": last_mod_dt, "dt_str": last_mod_dt.strftime('%Y-%m-%d %H:%M')}) # 秒を削除
                except Exception as e_stat: self.log(self._("ai_chat.log.history_file_stat_error", filename=item_path.name, e_stat=e_stat))
        history_files_data.sort(key=lambda x: x["dt"], reverse=True)
        for entry in history_files_data:
            self.chat_history_tree.insert('', 'end', values=(entry["name"], entry["dt_str"]), iid=str(entry["path"]))
        self.log(self._("ai_chat.log.history_list_updated", count=len(history_files_data)))

    def start_new_ai_chat_session_action(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_filename = f"chat_{timestamp}.csv"
        new_filepath = self.ai_chat_history_folder / new_filename
        try:
            with open(new_filepath, 'w', newline='', encoding='utf-8') as csvfile:
                csv.writer(csvfile).writerow(['action', 'talker', 'words'])
            self.log(self._("ai_chat.log.new_chat_session_created", filepath=new_filepath))
            self.current_ai_chat_file_path = new_filepath
            self.chat_content_tree.delete(*self.chat_content_tree.get_children())
            self.load_chat_history_list()
            if self.chat_history_tree.exists(str(new_filepath)):
                self.chat_history_tree.selection_set(str(new_filepath))
                self.chat_history_tree.focus(str(new_filepath)); self.chat_history_tree.see(str(new_filepath))
            messagebox.showinfo(self._("ai_chat.messagebox.new_chat.title"), self._("ai_chat.messagebox.new_chat.message", filename=new_filename), parent=self.root)
            self.chat_message_entry.focus_set()
        except Exception as e:
            self.log(self._("ai_chat.log.new_chat_file_creation_error", e=e))
            messagebox.showerror(self._("ai_chat.messagebox.creation_error.title"), self._("ai_chat.messagebox.new_chat_creation_failed", e=e), parent=self.root)
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
            messagebox.showwarning(self._("ai_chat.messagebox.file_error.title"), self._("ai_chat.messagebox.history_file_not_found"), parent=self.root)
            self.current_ai_chat_file_path = None
            self.load_chat_history_list()
            return
        try:
            with open(self.current_ai_chat_file_path, 'r', encoding='utf-8', newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                # ヘッダーチェックは重要なので維持する
                expected_headers = ['action', 'talker', 'words']
                if not reader.fieldnames or not all(header in reader.fieldnames for header in expected_headers):
                    # 互換性のため、古い形式のファイルも許容するか、エラーとするか。
                    # ここでは厳密にチェックし、不足していればエラーとする。
                    logger.error(f"CSV header mismatch. Expected: {expected_headers}, Got: {reader.fieldnames}")
                    messagebox.showerror(self._("ai_chat.messagebox.format_error.title"),
                                         self._("ai_chat.messagebox.csv_header_invalid") + f"\nExpected: {expected_headers}\nGot: {reader.fieldnames}",
                                         parent=self.root)
                    return

                line_display_count = 0
                for row_data in reader:
                    action = row_data.get('action')
                    talker = row_data.get('talker', '') # talkerがない場合も考慮
                    words = row_data.get('words', '')   # wordsがない場合も考慮

                    display_talker = talker
                    add_to_tree = False

                    if action == 'talk':
                        add_to_tree = True
                        # 'talk' の場合、talker はキャラクター名なのでそのまま表示
                    elif action == 'mcp_command':
                        add_to_tree = True
                        display_talker = f"User (MCP)" # talker には 'User' が入っているはずだが、表示上は固定
                    elif action == 'mcp_result':
                        add_to_tree = True
                        display_talker = f"💻 MCP ({talker})" # talker に tool_id が入る想定
                    elif action == 'mcp_error':
                        add_to_tree = True
                        display_talker = f"💻 MCP Error ({talker})" # talker に tool_id が入る想定

                    if add_to_tree:
                        line_display_count += 1
                        self.chat_content_tree.insert('', 'end', values=(line_display_count, display_talker, words), iid=str(line_display_count))

            if self.chat_content_tree.get_children():
                self.chat_content_tree.see(self.chat_content_tree.get_children()[-1])
            self.log(self._("ai_chat.log.chat_history_loaded", filename=self.current_ai_chat_file_path.name))
        except Exception as e:
            messagebox.showerror(self._("ai_chat.messagebox.load_error.title"), self._("ai_chat.messagebox.history_load_failed", e=e), parent=self.root)
            self.log(self._("ai_chat.log.chat_history_load_error", e=e))

    def _append_to_current_chat_csv(self, action, talker, words):
        self.log(f"Attempting to append to CSV: action='{action}', talker='{talker}', words='{words[:50]}...'")
        if not self.current_ai_chat_file_path:
            self.log("CSV Append Skipped: current_ai_chat_file_path is None.")
            return
        if not self.current_ai_chat_file_path.exists():
            self.log(f"CSV Append Skipped: File does not exist at path: {self.current_ai_chat_file_path}")
            return

        try:
            self.log(f"Writing to CSV: {self.current_ai_chat_file_path}")
            with open(self.current_ai_chat_file_path, 'a', newline='', encoding='utf-8') as csvfile:
                csv_writer = csv.writer(csvfile)
                csv_writer.writerow([action, talker, words])
            self.log(f"Successfully appended to CSV: action='{action}'")
        except Exception as e:
            # ログメッセージは翻訳キーを使う
            log_message = self._("ai_chat.log.csv_append_error", e=e)
            self.log(log_message)
            # 念のためコンソールにもスタックトレースを出力
            import traceback
            logger.error(f"Detailed CSV append error: {traceback.format_exc()}")


    def _add_message_to_chat_display_tree(self, talker_display_name, message_content):
        line_num = len(self.chat_content_tree.get_children()) + 1
        actual_talker = talker_display_name[2:] if talker_display_name.startswith(("👤 ", "🤖 ")) else talker_display_name
        item_id = self.chat_content_tree.insert('', 'end', values=(line_num, actual_talker, message_content), iid=str(line_num))
        self.chat_content_tree.see(item_id)

    def send_ai_chat_message_action(self, event=None):
        user_input = self.chat_message_entry.get().strip()
        if not user_input: return

        # MCPコマンドの処理
        if user_input.startswith("/mcp "):
            self.chat_message_entry.delete(0, "end")
            self._handle_mcp_command(user_input)
            return

        # 通常のチャット処理
        no_char_text = self._("ai_chat.dropdown.no_character")
        if not self.current_ai_chat_file_path or not self.current_ai_chat_file_path.exists():
            if messagebox.askyesno(self._("ai_chat.messagebox.chat_not_started.title"), self._("ai_chat.messagebox.chat_not_started.confirm"), parent=self.root):
                self.start_new_ai_chat_session_action()
                if not self.current_ai_chat_file_path: return
            else: return

        ai_char_name_selected = self.ai_char_var.get()
        user_char_name_selected = self.user_char_var.get()
        if not ai_char_name_selected or not user_char_name_selected or no_char_text in [ai_char_name_selected, user_char_name_selected]:
            messagebox.showwarning(self._("ai_chat.messagebox.character_not_selected.title"), self._("ai_chat.messagebox.character_not_selected.message"), parent=self.root); return

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

    def _handle_mcp_command(self, command_input: str):
        """MCPコマンドを処理する"""
        # チャットセッションの確認と開始
        if not self.current_ai_chat_file_path or not self.current_ai_chat_file_path.exists():
            self.log(self._("ai_chat.log.mcp_auto_new_chat_for_command"))
            # MCPコマンド実行時は確認なしで新規チャットを開始する
            # start_new_ai_chat_session_action は messagebox を表示するので、直接呼ぶのは避けるか、
            # messagebox を表示しないサイレントなバージョンを用意する必要がある。
            # ここでは、既存の start_new_ai_chat_session_action を呼び、
            # それが失敗した場合（ユーザーがキャンセルなど）は処理を中断する。
            # ただし、start_new_ai_chat_session_action はUI操作を伴うため、
            # このメソッドがどのスレッドから呼ばれるかによっては問題になる可能性がある。
            # send_ai_chat_message_action から呼ばれるのであればUIスレッドのはず。

            # ユーザーに確認を求める場合 (より安全だが、UIフローが変わる)
            # confirmed = messagebox.askyesno(
            #     self._("ai_chat.messagebox.chat_not_started.title"),
            #     self._("ai_chat.messagebox.mcp_chat_not_started.confirm"), # MCP用の確認メッセージ
            #     parent=self.root
            # )
            # if confirmed:
            #     self.start_new_ai_chat_session_action()
            #     if not self.current_ai_chat_file_path:
            #         self._add_message_to_chat_display_tree("💻 System", self._("ai_chat.mcp.error.cannot_start_chat_session"))
            #         return
            # else:
            #     self._add_message_to_chat_display_tree("💻 System", self._("ai_chat.mcp.error.chat_session_required"))
            #     return

            # 現状は、通常のチャット開始と同じ動作を期待してそのまま呼び出す
            # ただし、MCPコマンド前にチャットを開始していない場合、messageboxが出る挙動になる
            if messagebox.askyesno(self._("ai_chat.messagebox.chat_not_started.title"), self._("ai_chat.messagebox.mcp_chat_not_started.confirm"), parent=self.root):
                self.start_new_ai_chat_session_action()
                if not self.current_ai_chat_file_path:
                     self._add_message_to_chat_display_tree("💻 System", self._("ai_chat.mcp.error.cannot_start_chat_session"))
                     return
            else:
                self._add_message_to_chat_display_tree("💻 System", self._("ai_chat.mcp.error.chat_session_required"))
                return

        parts = command_input.strip().split(" ", 2) # /mcp <tool_id> <json_params>
        if len(parts) < 2:
            self._add_message_to_chat_display_tree("💻 System", self._("ai_chat.mcp.error.invalid_command_format"))
            return

        tool_id = parts[1]
        params_str = parts[2] if len(parts) > 2 else "{}"
        params: dict = {}

        try:
            params = json.loads(params_str)
            if not isinstance(params, dict):
                raise json.JSONDecodeError("パラメータはJSONオブジェクトである必要があります。", params_str, 0)
        except json.JSONDecodeError as e:
            self._add_message_to_chat_display_tree("💻 System", self._("ai_chat.mcp.error.invalid_json_params", error=e))
            return

        self._add_message_to_chat_display_tree(f"👤 User (MCP)", command_input) # MCPコマンド自体もログとして表示
        self._append_to_current_chat_csv('mcp_command', 'User', command_input) # CSVにも記録

        # MCPツール実行を別スレッドで行う
        threading.Thread(target=self._execute_mcp_tool_async, args=(tool_id, params), daemon=True).start()

    def _execute_mcp_tool_async(self, tool_id: str, params: dict):
        """MCPツールを非同期で実行し、結果をチャットに表示する"""
        self.log(self._("ai_chat.log.mcp_tool_execution_start", tool_id=tool_id, params=params))
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.mcp_client_manager.execute_tool(tool_id, params))
            loop.close()

            if result.get("success"):
                result_data_str = json.dumps(result.get("data"), ensure_ascii=False, indent=2)
                base_message_success = self._("ai_chat.mcp.success.tool_executed")
                message = base_message_success.format(tool_id=tool_id, result=result_data_str)
                self._add_message_to_chat_display_tree("💻 MCP", message)
                self._append_to_current_chat_csv('mcp_result', tool_id, result_data_str)

                # ログ用のメッセージも同様にフォーマットする
                log_message_success_base = self._("ai_chat.log.mcp_tool_execution_success")
                log_message_success = log_message_success_base.format(tool_id=tool_id, result=result_data_str)
                self.log(log_message_success)
            else:
                error_message_content = result.get("error", "Unknown error")
                base_message_failed = self._("ai_chat.mcp.error.tool_execution_failed")
                message = base_message_failed.format(tool_id=tool_id, error=error_message_content)
                self._add_message_to_chat_display_tree("💻 MCP Error", message)
                self._append_to_current_chat_csv('mcp_error', tool_id, error_message_content)

                log_message_failed_base = self._("ai_chat.log.mcp_tool_execution_error")
                log_message_failed = log_message_failed_base.format(tool_id=tool_id, error=error_message_content)
                self.log(log_message_failed)

        except Exception as e:
            error_message_exc_content = str(e)
            base_message_exception = self._("ai_chat.mcp.error.tool_execution_exception")
            message = base_message_exception.format(tool_id=tool_id, error=error_message_exc_content)
            self._add_message_to_chat_display_tree("💻 MCP Error", message)
            self._append_to_current_chat_csv('mcp_error', tool_id, error_message_exc_content)

            log_message_exception_base = self._("ai_chat.log.mcp_tool_execution_exception")
            log_message_exception = log_message_exception_base.format(tool_id=tool_id, error=error_message_exc_content)
            self.log(log_message_exception)
            # UIスレッドでエラーメッセージを表示する場合は self.root.after を使用
            # self.root.after(0, lambda: messagebox.showerror("MCP Tool Error", f"ツール '{tool_id}' の実行中に例外が発生: {e}", parent=self.root))


    def _play_user_speech_then_ai_response(self, user_char_name, user_text, ai_char_name_for_next):
        self._play_character_speech_async(user_char_name, user_text, block=True)
        self._generate_and_handle_ai_response(user_text, ai_char_name_for_next, user_char_name)

    def _generate_and_handle_ai_response(self, user_input_text, ai_char_name, user_char_name_for_history):
        ai_char_id = self.character_manager.get_character_id_by_name(ai_char_name)
        if not ai_char_id: self.log(self._("ai_chat.log.ai_char_id_not_found", char_name=ai_char_name)); return
        ai_char_data = self.character_manager.get_character(ai_char_id)
        if not ai_char_data: self.log(self._("ai_chat.log.ai_char_data_not_found", char_name=ai_char_name)); return

        try:
            api_key = self.config.get_system_setting("google_ai_api_key")
            if not api_key:
                self.root.after(0, self._add_message_to_chat_display_tree, f"🤖 {ai_char_name}", self._("ai_chat.message.google_api_key_not_set"))
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
                            prefix = self._("ai_chat.prompt.ai_self_prefix") if speaker == ai_char_name else user_char_name_for_history
                            chat_history_for_prompt.append(f"{prefix}: {msg}")
            history_str = "\n".join(chat_history_for_prompt[-10:])
            prompt_history_header = self._("ai_chat.prompt.history_header")
            prompt_ai_turn_prefix = self._("ai_chat.prompt.ai_self_prefix")
            full_prompt = f"{ai_prompt}\n\n{prompt_history_header}\n{history_str}\n\n{user_char_name_for_history}: {user_input_text}\n\n{prompt_ai_turn_prefix} ({ai_char_name}):"
            text_gen_model = self.config.get_system_setting("text_generation_model", "gemini-1.5-flash")
            ai_response_text = self._("ai_chat.message.error_getting_response") # デフォルトのエラーメッセージ

            # ログ記録: AIへのリクエスト
            self.communication_logger.add_log("sent", "text_generation", f"[AI Chat to {ai_char_name} (Model: {text_gen_model})]\n{full_prompt}")

            if text_gen_model == "local_lm_studio":
                local_llm_url = self.config.get_system_setting("local_llm_endpoint_url")
                if not local_llm_url:
                    ai_response_text = self._("ai_chat.message.local_llm_url_not_set")
                else:
                    loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
                    try:
                        ai_response_text = loop.run_until_complete(self._generate_response_local_llm_chat(full_prompt, local_llm_url, ai_char_name))
                    finally:
                        loop.close()
            else:
                gemini_response = client.models.generate_content(model=text_gen_model, contents=full_prompt,
                                                               generation_config=genai_types.GenerateContentConfig(temperature=0.8, max_output_tokens=200))
                ai_response_text = gemini_response.text.strip() if gemini_response.text else self._("ai_chat.message.ai_generic_error_response")

            # ログ記録: AIからのレスポンス
            self.communication_logger.add_log("received", "text_generation", f"[AI Chat from {ai_char_name} (Model: {text_gen_model})]\n{ai_response_text}")

            self.root.after(0, self._add_message_to_chat_display_tree, f"🤖 {ai_char_name}", ai_response_text)
            self._append_to_current_chat_csv('talk', ai_char_name, ai_response_text)
            self._play_character_speech_async(ai_char_name, ai_response_text) # この中で音声合成ログが記録される

        except genai_types.BlockedPromptException as e_block:
            ai_response_text = self._("ai_chat.message.ai_blocked_response")
            self.communication_logger.add_log("received", "text_generation", f"[AI Chat from {ai_char_name} (Model: {text_gen_model}) - Blocked]\n{str(e_block)}")
            self.root.after(0, self._add_message_to_chat_display_tree, f"🤖 {ai_char_name}", ai_response_text)
        except Exception as e_gen:
            ai_response_text = self._("ai_chat.message.ai_system_error_response") # エラー時のレスポンスを更新
            self.log(self._("ai_chat.log.ai_response_generation_error", e_gen=e_gen))
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
            return self._("ai_chat.message.local_llm_response_format_error")
        except Exception as e_llm:
            self.log(self._("ai_chat.log.local_llm_call_error", char_name=char_name, endpoint_url=endpoint_url, e_llm=e_llm))
            return self._("ai_chat.message.local_llm_call_error", e_llm=e_llm)

    def _play_character_speech_async(self, char_name, text, block=False):
        char_id = self.character_manager.get_character_id_by_name(char_name)
        if not char_id: self.log(self._("ai_chat.log.audio_play_char_id_not_found", char_name=char_name)); return
        char_data = self.character_manager.get_character(char_id)
        if not char_data: self.log(self._("ai_chat.log.audio_play_char_data_not_found", char_name=char_name)); return

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
                else: self.log(self._("ai_chat.log.audio_synthesis_failed", char_name=char_name, text_preview=text[:20]))
            except Exception as e_play: self.log(self._("ai_chat.log.audio_playback_error", char_name=char_name, e_play=e_play))
            finally: loop.close()

        if block:
            run_synthesis_and_play()
        else:
            threading.Thread(target=run_synthesis_and_play, daemon=True).start()

    def delete_selected_chat_message_action(self):
        selected_items = self.chat_content_tree.selection()
        if not selected_items: messagebox.showwarning(self._("ai_chat.messagebox.delete_error.title"), self._("ai_chat.messagebox.select_row_to_delete"), parent=self.root); return
        selected_tree_iid = selected_items[0]
        try:
            line_num_in_tree = int(selected_tree_iid)
            values = self.chat_content_tree.item(selected_tree_iid, 'values')
            talker_preview, words_preview = values[1], values[2][:20]
            if not messagebox.askyesno(
                self._("ai_chat.messagebox.delete_confirm.title"),
                self._("ai_chat.messagebox.delete_confirm.message", line_num=line_num_in_tree, talker=talker_preview, words_preview=words_preview),
                parent=self.root): return

            if not self.current_ai_chat_file_path or not self.current_ai_chat_file_path.exists():
                messagebox.showerror(self._("ai_chat.messagebox.file_error.title"), self._("ai_chat.messagebox.chat_history_file_not_found_on_delete"), parent=self.root); return

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
                self.log(self._("ai_chat.log.chat_row_deleted", filename=self.current_ai_chat_file_path.name, line_num=line_num_in_tree))
                self.on_chat_history_selected_action() # Reload and refresh display
                messagebox.showinfo(self._("ai_chat.messagebox.delete_complete.title"), self._("ai_chat.messagebox.delete_complete.message"), parent=self.root)
            else:
                messagebox.showerror(self._("ai_chat.messagebox.delete_error.title"), self._("ai_chat.messagebox.delete_row_not_found_in_csv"), parent=self.root)
        except ValueError: messagebox.showerror(self._("ai_chat.messagebox.delete_error.title"), self._("ai_chat.messagebox.invalid_row_number"), parent=self.root)
        except Exception as e_del:
            self.log(self._("ai_chat.log.chat_row_delete_error", e_del=e_del))
            messagebox.showerror(self._("ai_chat.messagebox.delete_error.title"), self._("ai_chat.messagebox.unexpected_error_on_delete", e_del=e_del), parent=self.root)

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
