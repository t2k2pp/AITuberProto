import customtkinter
import tkinter as tk # 基本的な型 (StringVarなど) と標準ダイアログのため
from tkinter import ttk, messagebox, filedialog, simpledialog # Treeviewと標準ダイアログはそのまま使用
import csv
import os
import sys # フォント選択のため
from pathlib import Path
import asyncio
import threading
import time
import wave
import shutil

from config import ConfigManager
from character_manager import CharacterManager
from audio_manager import VoiceEngineManager, AudioPlayer

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AITheaterWindow:
    def __init__(self, root: customtkinter.CTk):
        self.root = root
        self.root.title("AI劇場")
        self.root.geometry("1050x850")

        self.loading_label = customtkinter.CTkLabel(self.root, text="読み込み中...", font=("Yu Gothic UI", 18))
        self.loading_label.pack(expand=True, fill="both")
        self.root.update_idletasks()

        self.root.after(50, self._initialize_components)

    def _initialize_components(self):
        if hasattr(self, 'loading_label') and self.loading_label.winfo_exists():
            self.loading_label.pack_forget()
            self.loading_label.destroy()

        self.config_manager = ConfigManager()
        self.character_manager = CharacterManager(self.config_manager)
        self.voice_manager = VoiceEngineManager()
        self.audio_player = AudioPlayer(config_manager=self.config_manager)

        self.current_script_path = None
        self.script_data = []
        self.audio_output_folder = None
        self.is_playing_script = False
        self.stop_requested = False

        # 現在のキャラクターIDを取得
        self.current_character_id = self.config_manager.config.get("streaming_settings", {}).get("current_character")
        if not self.current_character_id:
            self.log("AI劇場: 初期化時にアクティブなキャラクターIDが設定されていません。")
            # 必要であれば、デフォルトのキャラクターIDを設定するなどのフォールバック処理をここに追加できます。

        # フォント設定
        self.default_font = ("Yu Gothic UI", 12)
        if sys.platform == "darwin": self.default_font = ("Hiragino Sans", 14)
        elif sys.platform.startswith("linux"): self.default_font = ("Noto Sans CJK JP", 12)
        self.label_font = (self.default_font[0], self.default_font[1] + 1, "bold")
        self.treeview_font = (self.default_font[0], self.default_font[1] -1)

        self.create_widgets()
        self.populate_talker_dropdown()
        self.log("AI劇場ウィンドウが初期化されました。")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def log(self, message):
        # AITheaterWindow の log メソッドはUIウィジェットに書き込まないため、
        # 呼び出しタイミングに特に注意は不要。
        logger.info(message)

    def on_closing(self):
        if self.is_playing_script:
            if messagebox.askokcancel("終了確認", "AI劇場の連続再生中です。終了しますか？", parent=self.root):
                self.stop_sequential_play_action()
        self.root.destroy()

    def create_widgets(self):
        main_frame = customtkinter.CTkFrame(self.root) # paddingはFrame自体に
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        top_frame = customtkinter.CTkFrame(main_frame, fg_color="transparent")
        top_frame.pack(fill="x", padx=5, pady=5)
        customtkinter.CTkButton(top_frame, text="📜 CSV台本読み込み", command=self.load_csv_script_action, font=self.default_font).pack(side="left", padx=5)
        customtkinter.CTkButton(top_frame, text="📜 TXT台本読み込み", command=self.load_text_script , font=self.default_font).pack(side="left", padx=5)
        customtkinter.CTkButton(top_frame, text="✨ 新規CSV台本作成", command=self.create_new_csv_script_action, font=self.default_font).pack(side="left", padx=5)
        self.loaded_csv_label = customtkinter.CTkLabel(top_frame, text="CSVファイル: 未読み込み", font=self.default_font)
        self.loaded_csv_label.pack(side="left", padx=10)

        script_display_outer_frame = customtkinter.CTkFrame(main_frame)
        script_display_outer_frame.pack(fill="both", expand=True, padx=5, pady=5)
        customtkinter.CTkLabel(script_display_outer_frame, text="台本プレビュー", font=self.label_font).pack(anchor="w", padx=10, pady=(5,0))
        script_display_frame = customtkinter.CTkFrame(script_display_outer_frame)
        script_display_frame.pack(fill="both", expand=True, padx=5, pady=5)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview.Heading", font=(self.treeview_font[0], self.treeview_font[1], "bold"))
        style.configure("Treeview", font=self.treeview_font, rowheight=int(self.treeview_font[1]*2.0))

        self.script_tree = ttk.Treeview(script_display_frame, columns=('line', 'action', 'talker', 'words', 'status'), show='headings', style="Treeview")
        for col, text, width in [('line','行',50), ('action','アクション',80), ('talker','話者',120), ('words','台詞/内容',450), ('status','音声状態',100)]: # words幅調整
            self.script_tree.heading(col, text=text)
            self.script_tree.column(col, width=width, anchor="w" if col=='words' else "center", stretch=tk.YES if col=='words' else tk.NO)

        script_tree_scroll_y = ttk.Scrollbar(script_display_frame, orient="vertical", command=self.script_tree.yview)
        script_tree_scroll_x = ttk.Scrollbar(script_display_frame, orient="horizontal", command=self.script_tree.xview)
        self.script_tree.configure(yscrollcommand=script_tree_scroll_y.set, xscrollcommand=script_tree_scroll_x.set)
        script_tree_scroll_y.pack(side="right", fill="y"); script_tree_scroll_x.pack(side="bottom", fill="x")
        self.script_tree.pack(fill="both", expand=True)
        self.script_tree.bind('<<TreeviewSelect>>', self.on_script_line_selected_action)

        edit_area_outer_frame = customtkinter.CTkFrame(main_frame)
        edit_area_outer_frame.pack(fill="x", padx=5, pady=5)
        customtkinter.CTkLabel(edit_area_outer_frame, text="行追加・更新", font=self.label_font).pack(anchor="w", padx=10, pady=(5,0))
        edit_area_frame = customtkinter.CTkFrame(edit_area_outer_frame)
        edit_area_frame.pack(fill="x", padx=5, pady=5)

        edit_area_grid = customtkinter.CTkFrame(edit_area_frame, fg_color="transparent"); edit_area_grid.pack(fill="x")
        customtkinter.CTkLabel(edit_area_grid, text="アクション:", font=self.default_font).grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.script_action_var = tk.StringVar(value="talk")
        self.script_action_combo = customtkinter.CTkComboBox(edit_area_grid, variable=self.script_action_var, values=["talk", "narration", "wait"], state="readonly", width=150, font=self.default_font, command=self.on_script_action_selected_ui_update)
        self.script_action_combo.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        customtkinter.CTkLabel(edit_area_grid, text="話者:", font=self.default_font).grid(row=0, column=2, sticky="w", padx=5, pady=2)
        self.script_talker_var = tk.StringVar()
        self.script_talker_combo = customtkinter.CTkComboBox(edit_area_grid, variable=self.script_talker_var, state="readonly", width=180, font=self.default_font)
        self.script_talker_combo.grid(row=0, column=3, sticky="w", padx=5, pady=2)

        customtkinter.CTkLabel(edit_area_grid, text="台詞/内容:", font=self.default_font).grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.script_words_entry = customtkinter.CTkEntry(edit_area_grid, width=400, font=self.default_font) # width調整
        self.script_words_entry.grid(row=1, column=1, columnspan=3, sticky="ew", padx=5, pady=2)
        edit_area_grid.columnconfigure(1, weight=1) # Entryが伸びるように

        edit_buttons_frame = customtkinter.CTkFrame(edit_area_frame, fg_color="transparent"); edit_buttons_frame.pack(fill="x", pady=5)
        customtkinter.CTkButton(edit_buttons_frame, text="⏪生成&追加", command=self.add_and_generate_script_line_action, font=self.default_font).pack(side="left", padx=2)
        customtkinter.CTkButton(edit_buttons_frame, text="➕追加", command=self.add_script_line_to_preview_action, font=self.default_font).pack(side="left", padx=2)
        customtkinter.CTkButton(edit_buttons_frame, text="🔄更新", command=self.update_selected_script_line_action, font=self.default_font).pack(side="left", padx=2)
        customtkinter.CTkButton(edit_buttons_frame, text="✨クリア", command=self.clear_script_input_area_action, font=self.default_font).pack(side="left", padx=2)

        script_action_buttons_frame = customtkinter.CTkFrame(main_frame, fg_color="transparent")
        script_action_buttons_frame.pack(fill="x", padx=5, pady=5)

        audio_ops_frame = customtkinter.CTkFrame(script_action_buttons_frame, fg_color="transparent"); audio_ops_frame.pack(side="left")
        customtkinter.CTkButton(audio_ops_frame, text="🔊選択行 音声生成", command=self.generate_selected_line_audio_action, font=self.default_font).pack(side="left", padx=2)
        customtkinter.CTkButton(audio_ops_frame, text="▶️選択行 音声再生", command=self.play_selected_line_audio_action, font=self.default_font).pack(side="left", padx=2)
        customtkinter.CTkButton(audio_ops_frame, text="🔊全行 音声生成", command=self.generate_all_lines_audio_action, font=self.default_font).pack(side="left", padx=2)
        customtkinter.CTkButton(audio_ops_frame, text="▶️連続再生", command=self.play_script_sequentially_action, font=self.default_font).pack(side="left", padx=2)
        customtkinter.CTkButton(audio_ops_frame, text="⏹️再生停止", command=self.stop_sequential_play_action, font=self.default_font).pack(side="left", padx=2)

        line_ops_frame = customtkinter.CTkFrame(script_action_buttons_frame, fg_color="transparent"); line_ops_frame.pack(side="left", padx=10)
        customtkinter.CTkButton(line_ops_frame, text="🔼上へ", command=self.move_script_line_up_action, font=self.default_font).pack(side="left", padx=2)
        customtkinter.CTkButton(line_ops_frame, text="🔽下へ", command=self.move_script_line_down_action, font=self.default_font).pack(side="left", padx=2)
        customtkinter.CTkButton(line_ops_frame, text="🗑️行削除", command=self.delete_selected_script_line_action, font=self.default_font).pack(side="left", padx=2)

        file_ops_frame = customtkinter.CTkFrame(script_action_buttons_frame, fg_color="transparent"); file_ops_frame.pack(side="right")
        customtkinter.CTkButton(file_ops_frame, text="💾CSV保存", command=self.export_script_to_csv_action, font=self.default_font).pack(side="right", padx=2)
        customtkinter.CTkButton(file_ops_frame, text="🗑️音声全削除", command=self.delete_all_audio_files_action, font=self.default_font).pack(side="right", padx=2)

        self.on_script_action_selected_ui_update()

    def populate_talker_dropdown(self):
        all_chars = self.character_manager.get_all_characters()
        char_names = [data.get('name', 'Unknown') for data in all_chars.values()]
        talker_options = ["ナレーター"] + [name for name in char_names if name != "ナレーター"]
        self.script_talker_combo.configure(values=talker_options if talker_options else ["話者なし"])
        if talker_options and not self.script_talker_var.get():
            self.script_talker_var.set(talker_options[0])
        elif not talker_options:
             self.script_talker_var.set("話者なし")
        self.log("AI劇場: 話者プルダウン更新")

    def on_script_action_selected_ui_update(self, choice=None): # CTkComboBoxのcommandは選択値を渡す
        action = self.script_action_var.get()
        if action == "wait":
            self.script_talker_combo.set("")
            self.script_talker_combo.configure(state="disabled")
        else:
            self.script_talker_combo.configure(state="readonly")
            if not self.script_talker_var.get() and self.script_talker_combo.cget("values"): # cgetで取得
                self.script_talker_var.set(self.script_talker_combo.cget("values")[0])

    def load_csv_script_action(self, filepath_to_load=None):
        if filepath_to_load is None:
            filepath = filedialog.askopenfilename(title="CSV台本ファイルを選択", filetypes=[("CSVファイル", "*.csv")], parent=self.root)
            if not filepath: return
        else: filepath = filepath_to_load

        self.current_script_path = Path(filepath)
        self.script_data.clear()
        self.audio_output_folder = self.current_script_path.parent / f"{self.current_script_path.stem}_audio"
        try: self.audio_output_folder.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            messagebox.showerror("フォルダ作成エラー", f"音声保存フォルダの作成失敗: {e}", parent=self.root)
            self.current_script_path = None; self.audio_output_folder = None; return

        self.loaded_csv_label.configure(text=f"CSV: {self.current_script_path.name}")
        self.script_tree.delete(*self.script_tree.get_children())
        try:
            with open(self.current_script_path, 'r', encoding='utf-8', newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                if reader.fieldnames != ['action', 'talker', 'words']:
                    messagebox.showerror("CSVフォーマットエラー", "ヘッダーが不正です (action,talker,words)", parent=self.root)
                    self.current_script_path = None; self.audio_output_folder = None; return
                for i, row in enumerate(reader):
                    line_num = i + 1; status = "未生成"
                    audio_file_for_line = self.audio_output_folder / f"{line_num:06d}.wav"
                    if audio_file_for_line.exists(): status = "成功"
                    self.script_data.append({'line': line_num, **row, 'status': status})
                    self.script_tree.insert('', 'end', values=(line_num, row['action'], row['talker'], row['words'], status))
            self.log(f"CSV読み込み完了: {self.current_script_path} ({len(self.script_data)}行)")
        except Exception as e:
            messagebox.showerror("CSV読み込みエラー", f"エラー: {e}", parent=self.root)
            self.current_script_path = None; self.audio_output_folder = None

    def load_text_script(self):
        """テキスト台本ファイルを読み込み、内容をパースしてUIに表示する。"""
        filepath = filedialog.askopenfilename(
            title="テキスト台本ファイルを選択",
            filetypes=(("テキストファイル", "*.txt"), ("すべてのファイル", "*.*"))
        )
        if not filepath:
            self.log("AI劇場: テキスト台本ファイルの選択がキャンセルされました。")
            return

        self.current_script_path = filepath
        self.script_data = []

        # 音声保存フォルダの作成 (例: script_name_audio)
        script_filename = Path(filepath).stem
        self.audio_output_folder = Path(filepath).parent / f"{script_filename}_audio"
        try:
            self.audio_output_folder.mkdir(parents=True, exist_ok=True)
            self.log(f"AI劇場: 音声保存フォルダを作成/確認しました: {self.audio_output_folder}")
        except Exception as e:
            self.log(f"AI劇場: 音声保存フォルダの作成に失敗しました: {e}")
            messagebox.showerror("エラー", f"音声保存フォルダの作成に失敗しました: {e}")
            self.current_script_path = None
            self.audio_output_folder = None
            return

        self.loaded_csv_label.configure(text=f"ファイル: {Path(filepath).name}")
        self.script_tree.delete(*self.script_tree.get_children()) # 古い内容をクリア

        try:
            with open(filepath, 'r', encoding='utf-8') as f_in:
                lines = f_in.readlines()

            line_num = 1
            active_character_name = "ナレーター" # デフォルト話者
            if self.current_character_id:
                # config_manager を使用するように修正
                char_data = self.config_manager.get_character(self.current_character_id)
                if char_data and char_data.get('name'):
                    active_character_name = char_data.get('name')
                else:
                    self.log(f"AI劇場: current_character_id '{self.current_character_id}' に対応するキャラクターデータが見つかりませんでした。")
            else:
                self.log("AI劇場: current_character_idが設定されていません。デフォルト話者 'ナレーター' を使用します。")


            self.log(f"AI劇場: テキスト読み込み時のデフォルト話者: {active_character_name}")

            i = 0
            while i < len(lines):
                line_content = lines[i].strip()
                if not line_content: # 空行の場合
                    empty_line_count = 0
                    # 連続する空行をカウント
                    while i < len(lines) and not lines[i].strip():
                        empty_line_count += 1
                        i += 1

                    wait_time = empty_line_count * 0.5
                    self.script_data.append({
                        'line': line_num,
                        'action': "wait",
                        'talker': "",
                        'words': str(wait_time),
                        'status': '未生成'
                    })
                    self.script_tree.insert('', 'end', values=(
                        line_num, "wait", "", str(wait_time), '未生成'
                    ))
                    line_num += 1
                    # i は既に次の非空行またはファイル終端を指しているので、ここではインクリメントしない
                else: # 空行でない場合
                    self.script_data.append({
                        'line': line_num,
                        'action': "talk",
                        'talker': active_character_name,
                        'words': line_content,
                        'status': '未生成'
                    })
                    self.script_tree.insert('', 'end', values=(
                        line_num, "talk", active_character_name, line_content, '未生成'
                    ))
                    line_num += 1
                    i += 1

            self.log(f"AI劇場: テキストファイル '{filepath}' を読み込みました。全{len(self.script_data)}行。")
            if not self.script_data:
                messagebox.showinfo("情報", "読み込んだテキストファイルは空、または処理できる内容がありませんでした。")

        except FileNotFoundError:
            messagebox.showerror("エラー", f"ファイルが見つかりません: {filepath}")
            self.log(f"AI劇場: ファイルが見つかりません: {filepath}")
            self.current_script_path = None
            self.audio_output_folder = None
            self.loaded_csv_label.configure(text="ファイル: 未読み込み")
        except Exception as e:
            messagebox.showerror("テキスト読み込みエラー", f"テキストファイルの読み込み中にエラーが発生しました: {e}")
            self.log(f"AI劇場: テキスト読み込みエラー: {e}")
            self.current_script_path = None
            self.audio_output_folder = None
            self.loaded_csv_label.configure(text="ファイル: 未読み込み")

    def create_new_csv_script_action(self):
        filepath = filedialog.asksaveasfilename(title="新規CSV台本を保存", defaultextension=".csv", filetypes=[("CSVファイル", "*.csv")], parent=self.root)
        if not filepath: return
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                csv.writer(csvfile).writerow(['action', 'talker', 'words'])
            self.log(f"新規CSV作成: {filepath}")
            self.load_csv_script_action(filepath)
            messagebox.showinfo("新規作成完了", f"新規CSV台本ファイル '{Path(filepath).name}' を作成しました。", parent=self.root)
        except Exception as e: messagebox.showerror("新規作成エラー", f"エラー: {e}", parent=self.root)

    def on_script_line_selected_action(self, event=None):
        selected_items = self.script_tree.selection()
        if not selected_items: return
        item_id = selected_items[0]
        values = self.script_tree.item(item_id, 'values')
        try:
            action, talker, words = values[1], values[2], values[3]
            self.script_action_var.set(action)
            self.script_talker_var.set(talker if action != "wait" else "")
            self.script_words_entry.delete(0, "end"); self.script_words_entry.insert(0, words) # CTkEntry
            self.on_script_action_selected_ui_update()
        except (IndexError, ValueError) as e: self.log(f"行選択処理エラー: {e}")

    def add_script_line_to_preview_action(self, and_generate=False):
        action = self.script_action_var.get()
        talker = self.script_talker_var.get() if action != "wait" else ""
        words = self.script_words_entry.get()
        if not self._validate_script_line_input(action, talker, words): return
        new_line_num = (max(item['line'] for item in self.script_data) + 1) if self.script_data else 1
        new_line_data = {'line': new_line_num, 'action': action, 'talker': talker, 'words': words, 'status': '未生成'}
        self.script_data.append(new_line_data)
        item_id = self.script_tree.insert('', 'end', values=(new_line_num, action, talker, words, '未生成'))
        self.script_tree.see(item_id)
        self.log(f"行追加: L{new_line_num} - {action}, {talker}, '{words[:20]}...'")
        if and_generate:
            self.current_line_to_generate_after_add = new_line_num
            self.root.after(100, self._generate_specific_line_audio_after_add)
        self.clear_script_input_area_action()

    def _generate_specific_line_audio_after_add(self):
        if hasattr(self, 'current_line_to_generate_after_add'):
            line_num = self.current_line_to_generate_after_add
            line_data = next((item for item in self.script_data if item['line'] == line_num), None)
            if line_data: self._start_audio_generation_for_line(line_data)
            del self.current_line_to_generate_after_add

    def add_and_generate_script_line_action(self): self.add_script_line_to_preview_action(and_generate=True)

    def update_selected_script_line_action(self):
        selected_items = self.script_tree.selection()
        if not selected_items: messagebox.showwarning("選択なし", "更新する行を選択してください。", parent=self.root); return
        item_id = selected_items[0]
        try: line_num_to_update = int(self.script_tree.item(item_id, 'values')[0])
        except (IndexError, ValueError): return
        new_action = self.script_action_var.get()
        new_talker = self.script_talker_var.get() if new_action != "wait" else ""
        new_words = self.script_words_entry.get()
        if not self._validate_script_line_input(new_action, new_talker, new_words): return
        for i, data_item in enumerate(self.script_data):
            if data_item['line'] == line_num_to_update:
                old_words = data_item['words']
                data_item.update({'action': new_action, 'talker': new_talker, 'words': new_words, 'status': '未生成'})
                self.script_tree.item(item_id, values=(line_num_to_update, new_action, new_talker, new_words, '未生成'))
                if old_words != new_words or data_item['action'] != new_action or data_item['talker'] != new_talker :
                    self._delete_audio_file_for_line(line_num_to_update)
                self.log(f"行更新: L{line_num_to_update}"); break

    def clear_script_input_area_action(self):
        self.script_action_var.set("talk")
        # CTkComboBoxのvaluesは .cget("values") で取得
        self.script_talker_var.set(self.script_talker_combo.cget("values")[0] if self.script_talker_combo.cget("values") else "")
        self.script_words_entry.delete(0, "end") # CTkEntry
        self.on_script_action_selected_ui_update()
        if self.script_tree.selection(): self.script_tree.selection_remove(self.script_tree.selection())

    def _validate_script_line_input(self, action, talker, words):
        if not action: messagebox.showwarning("入力エラー", "アクションを選択。", parent=self.root); return False
        if action != "wait" and not talker: messagebox.showwarning("入力エラー", "話者を選択。", parent=self.root); return False
        if not words and (action == "talk" or action == "narration"): messagebox.showwarning("入力エラー", "台詞/内容を入力。", parent=self.root); return False
        if action == "wait" and not words.strip().replace('.', '', 1).isdigit(): messagebox.showwarning("入力エラー", "待機時間を数値で入力。", parent=self.root); return False
        return True

    def _start_audio_generation_for_line(self, line_data):
        if not self.audio_output_folder: messagebox.showerror("エラー", "音声保存フォルダが設定されていません。", parent=self.root); return
        self._update_line_status_in_tree(line_data['line'], "生成中...")
        threading.Thread(target=self._synthesize_single_line_audio_thread, args=(line_data,), daemon=True).start()

    def _synthesize_single_line_audio_thread(self, line_data):
        loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
        success = False
        try: success = loop.run_until_complete(self._synthesize_script_line_logic(line_data))
        except Exception as e: self.log(f"音声合成スレッドエラー (L{line_data['line']}): {e}")
        finally:
            loop.close(); final_status = "成功" if success else "失敗"
            self.root.after(0, self._update_line_status_in_tree, line_data['line'], final_status)
            if not success: self.root.after(0, messagebox.showerror, "音声生成失敗", f"行 {line_data['line']} の音声生成に失敗しました。", parent=self.root if self.root.winfo_exists() else None)

    async def _synthesize_script_line_logic(self, line_data: dict) -> bool:
        line_num, action, talker, words = line_data['line'], line_data['action'], line_data['talker'], line_data['words']
        output_wav_path = self.audio_output_folder / f"{line_num:06d}.wav"
        self.log(f"音声生成開始 - L{line_num}, アクション: {action}, 話者: {talker}, 内容: '{words[:20]}...'")
        if action == "talk" or action == "narration":
            char_id_to_use = self._get_char_id_for_talker(talker)
            if not char_id_to_use: self.log(f"話者 '{talker}' (L{line_num}) のキャラ設定が見つからずスキップ。"); return False
            char_settings = self.config_manager.get_character(char_id_to_use)
            if not char_settings: return False
            voice_settings = char_settings.get('voice_settings', {})
            engine = voice_settings.get('engine', self.config_manager.get_system_setting("voice_engine"))
            model = voice_settings.get('model'); speed = voice_settings.get('speed', 1.0)
            api_key = self.config_manager.get_system_setting("google_ai_api_key") if "google_ai_studio" in engine else None
            audio_files = await self.voice_manager.synthesize_with_fallback(words, model, speed, preferred_engine=engine, api_key=api_key)
            if audio_files and Path(audio_files[0]).exists():
                try:
                    if output_wav_path.exists(): output_wav_path.unlink()
                    shutil.move(audio_files[0], output_wav_path)
                    self.log(f"音声ファイル生成成功: {output_wav_path}"); return True
                except Exception as e_move:
                    self.log(f"音声ファイル移動エラー (L{line_num}): {e_move}")
                    if Path(audio_files[0]).exists(): Path(audio_files[0]).unlink(missing_ok=True)
                    return False
            return False
        elif action == "wait":
            try:
                duration = float(words); framerate=24000; channels=1; sampwidth=2
                num_frames = int(framerate * duration); silence = b'\x00\x00' * num_frames
                with wave.open(str(output_wav_path), 'wb') as wf:
                    wf.setnchannels(channels); wf.setsampwidth(sampwidth); wf.setframerate(framerate); wf.writeframes(silence)
                self.log(f"無音ファイル作成成功 ({duration}秒): {output_wav_path}"); return True
            except Exception as e_wave: self.log(f"無音ファイル作成エラー (L{line_num}): {e_wave}"); return False
        return False

    def _get_char_id_for_talker(self, talker_name):
        all_chars = self.character_manager.get_all_characters()
        for char_id, data in all_chars.items():
            if data.get('name') == talker_name: return char_id
        self.log(f"話者 '{talker_name}' に対応するキャラクターが見つかりません。"); return None

    def _update_line_status_in_tree(self, line_num: int, status: str):
        for item_id in self.script_tree.get_children():
            if int(self.script_tree.item(item_id, 'values')[0]) == line_num:
                current_values = list(self.script_tree.item(item_id, 'values')); current_values[4] = status
                self.script_tree.item(item_id, values=tuple(current_values))
                for data_item in self.script_data:
                    if data_item['line'] == line_num: data_item['status'] = status; break
                break

    def _delete_audio_file_for_line(self, line_num):
        if not self.audio_output_folder: return
        audio_file = self.audio_output_folder / f"{line_num:06d}.wav"
        if audio_file.exists():
            try: audio_file.unlink(); self.log(f"音声ファイル削除: {audio_file}")
            except Exception as e: self.log(f"音声ファイル削除エラー {audio_file}: {e}")

    def generate_selected_line_audio_action(self):
        selected_items = self.script_tree.selection()
        if not selected_items: messagebox.showwarning("選択なし", "音声生成する行を選択。", parent=self.root); return
        item_id = selected_items[0]; line_num = int(self.script_tree.item(item_id, 'values')[0])
        line_data = next((item for item in self.script_data if item['line'] == line_num), None)
        if line_data: self._start_audio_generation_for_line(line_data)

    def generate_all_lines_audio_action(self):
        if not self.script_data: messagebox.showinfo("情報", "台本が空です。", parent=self.root); return
        if not self.audio_output_folder: messagebox.showerror("エラー", "音声保存フォルダ未設定。", parent=self.root); return
        if not messagebox.askyesno("一括音声生成", f"全{len(self.script_data)}行の音声を生成しますか？", parent=self.root): return
        self.log("全行音声生成開始...")
        threading.Thread(target=self._generate_all_lines_audio_thread, daemon=True).start()

    def _generate_all_lines_audio_thread(self):
        # CTkProgressbarを使う場合は、Toplevelではなくメインウィンドウに配置するか、
        # CTkToplevel内で完結させる。ここでは標準Toplevelでttk.Progressbarを使用。
        progress_root = tk.Toplevel(self.root); progress_root.title("音声生成中..."); progress_root.geometry("300x100")
        progress_root.transient(self.root); progress_root.grab_set()
        ttk.Label(progress_root, text="音声ファイルを生成しています...").pack(pady=10) # 標準Label
        progress_var = tk.DoubleVar(); progressbar = ttk.Progressbar(progress_root, variable=progress_var, maximum=len(self.script_data), length=280)
        progressbar.pack(pady=10)
        loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
        success_count = 0; fail_count = 0
        try:
            for i, line_data in enumerate(self.script_data):
                if self.stop_requested: break
                self.root.after(0, self._update_line_status_in_tree, line_data['line'], "生成中...")
                success = loop.run_until_complete(self._synthesize_script_line_logic(line_data))
                final_status = "成功" if success else "失敗"
                self.root.after(0, self._update_line_status_in_tree, line_data['line'], final_status)
                if success: success_count +=1
                else: fail_count +=1
                progress_var.set(i + 1); progress_root.update_idletasks()
            self.log(f"全行音声生成完了。成功: {success_count}, 失敗: {fail_count}")
            if fail_count > 0: messagebox.showwarning("一部失敗", f"一部音声生成失敗。成功{success_count}, 失敗{fail_count}", parent=self.root if self.root.winfo_exists() else None)
            else: messagebox.showinfo("生成完了", f"全{success_count}行の音声生成完了。", parent=self.root if self.root.winfo_exists() else None)
        except Exception as e:
            self.log(f"全行音声生成エラー: {e}")
            messagebox.showerror("一括生成エラー", f"エラー: {e}", parent=self.root if self.root.winfo_exists() else None)
        finally:
            loop.close()
            if progress_root.winfo_exists(): progress_root.destroy()

    def play_selected_line_audio_action(self):
        selected_items = self.script_tree.selection()
        if not selected_items: messagebox.showwarning("選択なし", "再生する行を選択。", parent=self.root); return
        item_id = selected_items[0]; line_num = int(self.script_tree.item(item_id, 'values')[0])
        audio_file = self.audio_output_folder / f"{line_num:06d}.wav" if self.audio_output_folder else None
        if audio_file and audio_file.exists():
            self.log(f"音声再生: {audio_file}")
            def play_async():
                loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
                try: loop.run_until_complete(self.audio_player.play_audio_file(str(audio_file)))
                except Exception as e: self.log(f"音声再生エラー: {e}")
                finally: loop.close()
            threading.Thread(target=play_async, daemon=True).start()
        else: messagebox.showinfo("ファイルなし", "音声ファイル未生成か見つかりません。", parent=self.root)

    def play_script_sequentially_action(self):
        if not self.script_data: messagebox.showinfo("情報", "台本が空です。", parent=self.root); return
        if self.is_playing_script: messagebox.showwarning("再生中", "既に連続再生中です。", parent=self.root); return
        self.is_playing_script = True; self.stop_requested = False
        self.log("連続再生開始...")
        threading.Thread(target=self._play_script_sequentially_thread, daemon=True).start()

    def _play_script_sequentially_thread(self):
        loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
        try:
            for line_data in self.script_data:
                if self.stop_requested: self.log("連続再生 ユーザー停止"); break
                line_num = line_data['line']
                self.root.after(0, self._update_line_status_in_tree, line_num, "再生準備")
                audio_file = self.audio_output_folder / f"{line_num:06d}.wav"
                if not audio_file.exists():
                    self.root.after(0, self._update_line_status_in_tree, line_num, "生成中...")
                    if not loop.run_until_complete(self._synthesize_script_line_logic(line_data)):
                        self.root.after(0, self._update_line_status_in_tree, line_num, "生成失敗"); continue
                    self.root.after(0, self._update_line_status_in_tree, line_num, "生成完了")
                if audio_file.exists():
                    self.root.after(0, self._update_line_status_in_tree, line_num, "再生中...")
                    loop.run_until_complete(self.audio_player.play_audio_file(str(audio_file)))
                    self.root.after(0, self._update_line_status_in_tree, line_num, "再生済")
                else: self.root.after(0, self._update_line_status_in_tree, line_num, "ファイルなし")
                time.sleep(0.1)
            if not self.stop_requested: self.log("連続再生完了。")
            if self.root.winfo_exists() and not self.stop_requested : messagebox.showinfo("再生完了", "連続再生が完了しました。", parent=self.root)
        except Exception as e:
            self.log(f"連続再生エラー: {e}")
            if self.root.winfo_exists(): messagebox.showerror("再生エラー", f"エラー: {e}", parent=self.root)
        finally: self.is_playing_script = False; self.stop_requested = False; loop.close()

    def stop_sequential_play_action(self):
        if self.is_playing_script: self.stop_requested = True; self.log("連続再生停止リクエスト。")
        else: messagebox.showinfo("情報", "連続再生は実行されていません。", parent=self.root)

    def _remap_lines_and_ui_after_edit(self, select_new_line_num=None):
        if not self.audio_output_folder: return
        temp_audio_map = {}; new_script_data_temp = []
        for new_idx, old_line_item in enumerate(self.script_data):
            old_line_num = old_line_item['line']; new_line_num = new_idx + 1
            new_item = {**old_line_item, 'line': new_line_num}; new_script_data_temp.append(new_item)
            if old_line_num != new_line_num:
                old_audio_path = self.audio_output_folder / f"{old_line_num:06d}.wav"
                new_audio_path = self.audio_output_folder / f"{new_line_num:06d}.wav"
                if old_audio_path.exists(): temp_audio_map[str(old_audio_path)] = str(new_audio_path)
        self.script_data = new_script_data_temp
        intermediate_rename_paths = {}
        try:
            for old_p_str, new_p_str in temp_audio_map.items():
                if Path(old_p_str).exists():
                    temp_inter_p = Path(old_p_str + ".tmp_rename_theater")
                    Path(old_p_str).rename(temp_inter_p)
                    intermediate_rename_paths[str(temp_inter_p)] = new_p_str
            for temp_p_str, final_p_str in intermediate_rename_paths.items():
                if Path(temp_p_str).exists():
                    if Path(final_p_str).exists(): Path(final_p_str).unlink()
                    Path(temp_p_str).rename(final_p_str)
        except Exception as e_rename: self.log(f"音声ファイルリネーム中エラー: {e_rename}")
        self.script_tree.delete(*self.script_tree.get_children())
        newly_selected_item_tree_id = None
        for item_d in self.script_data:
            tid = self.script_tree.insert('', 'end', values=(item_d['line'], item_d['action'], item_d['talker'], item_d['words'], item_d['status']))
            if select_new_line_num is not None and item_d['line'] == select_new_line_num: newly_selected_item_tree_id = tid
        if newly_selected_item_tree_id:
            self.script_tree.selection_set(newly_selected_item_tree_id)
            self.script_tree.focus(newly_selected_item_tree_id)
            self.script_tree.see(newly_selected_item_tree_id)
        self.log("行編集後 UI再マッピング完了。")

    def move_script_line_up_action(self):
        selected_items = self.script_tree.selection()
        if not selected_items: return
        selected_item_id = selected_items[0]; current_tree_idx = self.script_tree.index(selected_item_id)
        if current_tree_idx == 0: return
        current_line_num = int(self.script_tree.item(selected_item_id, 'values')[0])
        current_data_idx = next((i for i, item in enumerate(self.script_data) if item['line'] == current_line_num), -1)
        if current_data_idx > 0 :
            item_to_move = self.script_data.pop(current_data_idx)
            self.script_data.insert(current_data_idx - 1, item_to_move)
            self._remap_lines_and_ui_after_edit(select_new_line_num=current_line_num -1 if current_line_num >1 else 1)

    def move_script_line_down_action(self):
        selected_items = self.script_tree.selection()
        if not selected_items: return
        selected_item_id = selected_items[0]; current_tree_idx = self.script_tree.index(selected_item_id)
        if current_tree_idx == len(self.script_tree.get_children()) -1 : return
        current_line_num = int(self.script_tree.item(selected_item_id, 'values')[0])
        current_data_idx = next((i for i, item in enumerate(self.script_data) if item['line'] == current_line_num), -1)
        if 0 <= current_data_idx < len(self.script_data) -1:
            item_to_move = self.script_data.pop(current_data_idx)
            self.script_data.insert(current_data_idx + 1, item_to_move)
            self._remap_lines_and_ui_after_edit(select_new_line_num=current_line_num + 1)

    def delete_selected_script_line_action(self):
        selected_items = self.script_tree.selection()
        if not selected_items: return
        item_id = selected_items[0]; line_num_to_delete = int(self.script_tree.item(item_id, 'values')[0])
        words_preview = self.script_tree.item(item_id, 'values')[3][:20]
        if not messagebox.askyesno("削除確認", f"行 {line_num_to_delete} ({words_preview}...) を削除しますか？\n関連音声ファイルも削除されます。", parent=self.root): return
        original_len = len(self.script_data)
        self.script_data = [item for item in self.script_data if item['line'] != line_num_to_delete]
        if len(self.script_data) < original_len:
            self._delete_audio_file_for_line(line_num_to_delete)
            self._remap_lines_and_ui_after_edit()
            self.log(f"行削除: L{line_num_to_delete}")

    def export_script_to_csv_action(self):
        if not self.script_data: messagebox.showinfo("情報", "エクスポートするデータがありません。", parent=self.root); return
        filepath = filedialog.asksaveasfilename(title="CSV台本を保存", defaultextension=".csv", filetypes=[("CSVファイル", "*.csv")], parent=self.root, initialfile=self.current_script_path.name if self.current_script_path else "script.csv")
        if not filepath: return
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=['action', 'talker', 'words'])
                writer.writeheader()
                for line_data in self.script_data: writer.writerow({'action': line_data['action'], 'talker': line_data['talker'], 'words': line_data['words']})
            self.log(f"CSVエクスポート完了: {filepath}")
            messagebox.showinfo("エクスポート完了", f"台本を '{Path(filepath).name}' に保存しました。", parent=self.root)
        except Exception as e: messagebox.showerror("エクスポートエラー", f"エラー: {e}", parent=self.root)

    def delete_all_audio_files_action(self):
        if not self.audio_output_folder or not self.audio_output_folder.exists(): messagebox.showinfo("情報", "音声フォルダが見つからないか未設定です。", parent=self.root); return
        if not messagebox.askyesno("音声全削除確認", f"フォルダ '{self.audio_output_folder.name}' 内の全音声ファイル(.wav)を削除しますか？", parent=self.root): return
        deleted_count = 0; failed_count = 0
        for item in self.audio_output_folder.iterdir():
            if item.is_file() and item.suffix.lower() == '.wav':
                try: item.unlink(); deleted_count +=1
                except Exception as e: self.log(f"ファイル削除エラー {item}: {e}"); failed_count +=1
        self.log(f"音声全削除完了。削除: {deleted_count}, 失敗: {failed_count}")
        messagebox.showinfo("削除完了", f"{deleted_count}個の音声ファイルを削除しました。" + (f"\n{failed_count}個失敗。" if failed_count else ""), parent=self.root)
        for item_id in self.script_tree.get_children():
            line_num = int(self.script_tree.item(item_id, 'values')[0])
            self._update_line_status_in_tree(line_num, "未生成")

def main():
    customtkinter.set_appearance_mode("System")
    customtkinter.set_default_color_theme("blue")
    root = customtkinter.CTk()
    app = AITheaterWindow(root)
    root.mainloop()

if __name__ == "__main__":
    customtkinter.set_appearance_mode("System")
    customtkinter.set_default_color_theme("blue")
    main()
