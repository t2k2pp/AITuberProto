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
import chardet # 文字コード判別ライブラリ

from config import ConfigManager
from character_manager import CharacterManager
from audio_manager import VoiceEngineManager, AudioPlayer
import i18n_setup #国際化対応

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AITheaterWindow:
    def __init__(self, root: customtkinter.CTk):
        self.root = root
        i18n_setup.init_i18n()
        self._ = i18n_setup.get_translator()
        self.root.title(self._("ai_theater.title"))
        self.root.geometry("1050x850")

        self.loading_label = customtkinter.CTkLabel(self.root, text=self._("ai_theater.loading"), font=("Yu Gothic UI", 18))
        self.loading_label.pack(expand=True, fill="both")
        self.root.update_idletasks()

        self.root.after(50, self._initialize_components)

    def _initialize_components(self):
        if hasattr(self, 'loading_label') and self.loading_label.winfo_exists():
            self.loading_label.pack_forget()
            self.loading_label.destroy()

        i18n_setup.init_i18n() # NOTE: タイミングによっては言語設定変更が即時反映されない場合があるため、ここで再初期化
        self._ = i18n_setup.get_translator()


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
            self.log(self._("ai_theater.log.init_failed_active_char_id"))
            # 必要であれば、デフォルトのキャラクターIDを設定するなどのフォールバック処理をここに追加できます。

        # フォント設定
        self.default_font = ("Yu Gothic UI", 12)
        if sys.platform == "darwin": self.default_font = ("Hiragino Sans", 14)
        elif sys.platform.startswith("linux"): self.default_font = ("Noto Sans CJK JP", 12)
        self.label_font = (self.default_font[0], self.default_font[1] + 1, "bold")
        self.treeview_font = (self.default_font[0], self.default_font[1] -1)

        self.create_widgets()
        self.populate_talker_dropdown()
        self.log(self._("ai_theater.log.init_complete"))
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def log(self, message):
        # AITheaterWindow の log メソッドはUIウィジェットに書き込まないため、
        # 呼び出しタイミングに特に注意は不要。
        logger.info(message)

    def on_closing(self):
        if self.is_playing_script:
            if messagebox.askokcancel(self._("ai_theater.messagebox.confirm_exit.title"), self._("ai_theater.messagebox.confirm_exit.message"), parent=self.root):
                self.stop_sequential_play_action()
        self.root.destroy()

    def create_widgets(self):
        main_frame = customtkinter.CTkFrame(self.root) # paddingはFrame自体に
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        top_frame = customtkinter.CTkFrame(main_frame, fg_color="transparent")
        top_frame.pack(fill="x", padx=5, pady=5)
        customtkinter.CTkButton(top_frame, text=self._("ai_theater.button.load_csv_script"), command=self.load_csv_script_action, font=self.default_font).pack(side="left", padx=5)
        customtkinter.CTkButton(top_frame, text=self._("ai_theater.button.load_txt_script"), command=self.load_text_script , font=self.default_font).pack(side="left", padx=5)
        customtkinter.CTkButton(top_frame, text=self._("ai_theater.button.create_new_csv_script"), command=self.create_new_csv_script_action, font=self.default_font).pack(side="left", padx=5)
        self.loaded_csv_label = customtkinter.CTkLabel(top_frame, text=self._("ai_theater.label.loaded_csv_file"), font=self.default_font)
        self.loaded_csv_label.pack(side="left", padx=10)

        script_display_outer_frame = customtkinter.CTkFrame(main_frame)
        script_display_outer_frame.pack(fill="both", expand=True, padx=5, pady=5)
        customtkinter.CTkLabel(script_display_outer_frame, text=self._("ai_theater.label.script_preview"), font=self.label_font).pack(anchor="w", padx=10, pady=(5,0))
        script_display_frame = customtkinter.CTkFrame(script_display_outer_frame)
        script_display_frame.pack(fill="both", expand=True, padx=5, pady=5)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview.Heading", font=(self.treeview_font[0], self.treeview_font[1], "bold"))
        style.configure("Treeview", font=self.treeview_font, rowheight=int(self.treeview_font[1]*2.0))

        self.script_tree = ttk.Treeview(script_display_frame, columns=('line', 'action', 'talker', 'words', 'status'), show='headings', style="Treeview")

        headers = [
            ('line', self._("ai_theater.treeview.header.line"), 50),
            ('action', self._("ai_theater.treeview.header.action"), 80),
            ('talker', self._("ai_theater.treeview.header.talker"), 120),
            ('words', self._("ai_theater.treeview.header.words"), 450),
            ('status', self._("ai_theater.treeview.header.status"), 100)
        ]
        for col, text, width in headers:
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
        customtkinter.CTkLabel(edit_area_outer_frame, text=self._("ai_theater.label.add_update_line"), font=self.label_font).pack(anchor="w", padx=10, pady=(5,0))
        edit_area_frame = customtkinter.CTkFrame(edit_area_outer_frame)
        edit_area_frame.pack(fill="x", padx=5, pady=5)

        edit_area_grid = customtkinter.CTkFrame(edit_area_frame, fg_color="transparent"); edit_area_grid.pack(fill="x")
        customtkinter.CTkLabel(edit_area_grid, text=self._("ai_theater.label.action_type"), font=self.default_font).grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.script_action_var = tk.StringVar(value="talk")
        self.script_action_combo = customtkinter.CTkComboBox(edit_area_grid, variable=self.script_action_var, values=["talk", "narration", "wait"], state="readonly", width=150, font=self.default_font, command=self.on_script_action_selected_ui_update)
        self.script_action_combo.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        customtkinter.CTkLabel(edit_area_grid, text=self._("ai_theater.label.talker_name"), font=self.default_font).grid(row=0, column=2, sticky="w", padx=5, pady=2)
        self.script_talker_var = tk.StringVar()
        self.script_talker_combo = customtkinter.CTkComboBox(edit_area_grid, variable=self.script_talker_var, state="readonly", width=180, font=self.default_font)
        self.script_talker_combo.grid(row=0, column=3, sticky="w", padx=5, pady=2)

        customtkinter.CTkLabel(edit_area_grid, text=self._("ai_theater.label.script_content"), font=self.default_font).grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.script_words_entry = customtkinter.CTkEntry(edit_area_grid, width=400, font=self.default_font) # width調整
        self.script_words_entry.grid(row=1, column=1, columnspan=3, sticky="ew", padx=5, pady=2)
        edit_area_grid.columnconfigure(1, weight=1) # Entryが伸びるように

        edit_buttons_frame = customtkinter.CTkFrame(edit_area_frame, fg_color="transparent"); edit_buttons_frame.pack(fill="x", pady=5)
        customtkinter.CTkButton(edit_buttons_frame, text=self._("ai_theater.button.generate_add"), command=self.add_and_generate_script_line_action, font=self.default_font).pack(side="left", padx=2)
        customtkinter.CTkButton(edit_buttons_frame, text=self._("ai_theater.button.add"), command=self.add_script_line_to_preview_action, font=self.default_font).pack(side="left", padx=2)
        customtkinter.CTkButton(edit_buttons_frame, text=self._("ai_theater.button.update"), command=self.update_selected_script_line_action, font=self.default_font).pack(side="left", padx=2)
        customtkinter.CTkButton(edit_buttons_frame, text=self._("ai_theater.button.clear"), command=self.clear_script_input_area_action, font=self.default_font).pack(side="left", padx=2)

        script_action_buttons_frame = customtkinter.CTkFrame(main_frame, fg_color="transparent")
        script_action_buttons_frame.pack(fill="x", padx=5, pady=5)

        audio_ops_frame = customtkinter.CTkFrame(script_action_buttons_frame, fg_color="transparent"); audio_ops_frame.pack(side="left")
        customtkinter.CTkButton(audio_ops_frame, text=self._("ai_theater.button.generate_selected_audio"), command=self.generate_selected_line_audio_action, font=self.default_font).pack(side="left", padx=2)
        customtkinter.CTkButton(audio_ops_frame, text=self._("ai_theater.button.play_selected_audio"), command=self.play_selected_line_audio_action, font=self.default_font).pack(side="left", padx=2)
        customtkinter.CTkButton(audio_ops_frame, text=self._("ai_theater.button.generate_all_audio"), command=self.generate_all_lines_audio_action, font=self.default_font).pack(side="left", padx=2)
        customtkinter.CTkButton(audio_ops_frame, text=self._("ai_theater.button.play_sequentially"), command=self.play_script_sequentially_action, font=self.default_font).pack(side="left", padx=2)
        customtkinter.CTkButton(audio_ops_frame, text=self._("ai_theater.button.stop_playback"), command=self.stop_sequential_play_action, font=self.default_font).pack(side="left", padx=2)

        line_ops_frame = customtkinter.CTkFrame(script_action_buttons_frame, fg_color="transparent"); line_ops_frame.pack(side="left", padx=10)
        customtkinter.CTkButton(line_ops_frame, text=self._("ai_theater.button.move_up"), command=self.move_script_line_up_action, font=self.default_font).pack(side="left", padx=2)
        customtkinter.CTkButton(line_ops_frame, text=self._("ai_theater.button.move_down"), command=self.move_script_line_down_action, font=self.default_font).pack(side="left", padx=2)
        customtkinter.CTkButton(line_ops_frame, text=self._("ai_theater.button.delete_line"), command=self.delete_selected_script_line_action, font=self.default_font).pack(side="left", padx=2)

        file_ops_frame = customtkinter.CTkFrame(script_action_buttons_frame, fg_color="transparent"); file_ops_frame.pack(side="right")
        customtkinter.CTkButton(file_ops_frame, text=self._("ai_theater.button.save_csv"), command=self.export_script_to_csv_action, font=self.default_font).pack(side="right", padx=2)
        customtkinter.CTkButton(file_ops_frame, text=self._("ai_theater.button.delete_all_audio"), command=self.delete_all_audio_files_action, font=self.default_font).pack(side="right", padx=2)

        self.on_script_action_selected_ui_update()

    def populate_talker_dropdown(self):
        all_chars = self.character_manager.get_all_characters()
        char_names = [data.get('name', self._("ai_theater.dropdown.unknown_character_name")) for data in all_chars.values()]

        narrator_str = self._("ai_theater.dropdown.narrator")
        no_talker_str = self._("ai_theater.dropdown.no_talker")
        no_talkers_available_str = self._("ai_theater.dropdown.no_talkers_available")

        talker_options = [narrator_str] + [name for name in char_names if name != narrator_str]

        self.script_talker_combo.configure(values=talker_options if talker_options else [no_talkers_available_str])
        if talker_options and not self.script_talker_var.get():
            self.script_talker_var.set(talker_options[0])
        elif not talker_options:
             self.script_talker_var.set(no_talkers_available_str) # ここも翻訳
        self.log(self._("ai_theater.log.talker_dropdown_updated"))

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
            filepath = filedialog.askopenfilename(
                title=self._("ai_theater.filedialog.select_csv_script_title"),
                filetypes=[(self._("ai_theater.filedialog.csv_files"), "*.csv")],
                parent=self.root
            )
            if not filepath: return
        else: filepath = filepath_to_load

        self.current_script_path = Path(filepath)
        self.script_data.clear()
        self.audio_output_folder = self.current_script_path.parent / f"{self.current_script_path.stem}_audio"
        try: self.audio_output_folder.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            messagebox.showerror(
                self._("ai_theater.messagebox.error.folder_creation_failed.title"),
                self._("ai_theater.messagebox.error.folder_creation_failed.message").format(error=e),
                parent=self.root
            )
            self.current_script_path = None; self.audio_output_folder = None; return

        self.loaded_csv_label.configure(text=self._("ai_theater.label.loaded_csv_file_display").format(filename=self.current_script_path.name))
        self.script_tree.delete(*self.script_tree.get_children())
        try:
            # --- 文字コード自動判別処理 ---
            with open(self.current_script_path, 'rb') as f_raw:
                raw_data = f_raw.read()

            detected_encoding_info = chardet.detect(raw_data)
            encoding_to_try = detected_encoding_info['encoding']
            confidence = detected_encoding_info['confidence']
            self.log(self._("ai_theater.log.csv_encoding_detected").format(filepath=self.current_script_path, encoding=encoding_to_try, confidence=confidence))

            if encoding_to_try is None or confidence < 0.7:
                self.log(self._("ai_theater.log.csv_encoding_low_confidence").format(confidence=confidence))
                encodings_to_attempt = ['utf-8', 'shift_jis', 'euc_jp']
            else:
                encodings_to_attempt = [encoding_to_try, 'utf-8', 'shift_jis', 'euc_jp']

            read_data = None
            used_encoding = None
            for enc in list(dict.fromkeys(enc for enc in encodings_to_attempt if enc)): # Noneを除外
                try:
                    with open(self.current_script_path, 'r', encoding=enc, newline='') as csvfile:
                        reader = csv.DictReader(csvfile)
                        if reader.fieldnames != ['action', 'talker', 'words']:
                            self.log(self._("ai_theater.log.csv_read_attempt_encoding_header_invalid").format(encoding=enc))
                            continue
                        read_data = list(reader) # Read data inside the 'with' block
                    used_encoding = enc
                    self.log(self._("ai_theater.log.csv_read_success_encoding").format(encoding=enc))
                    break
                except UnicodeDecodeError:
                    self.log(self._("ai_theater.log.csv_read_fail_encoding").format(encoding=enc))
                    continue
                except Exception as e_csv_read:
                    self.log(self._("ai_theater.log.csv_read_error_encoding").format(encoding=enc, error=e_csv_read))
                    read_data = None
                    continue

            if read_data is None:
                messagebox.showerror(
                    self._("ai_theater.messagebox.error.csv_read_failed.title"),
                    self._("ai_theater.messagebox.error.csv_read_failed.message_format_or_encoding"),
                    parent=self.root
                )
                self.log(self._("ai_theater.log.csv_read_encoding_not_found").format(filepath=self.current_script_path))
                self.current_script_path = None; self.audio_output_folder = None; return
            # --- 文字コード自動判別処理ここまで ---

            status_not_generated = self._("ai_theater.status.not_generated")
            status_success = self._("ai_theater.status.success")

            for i, row in enumerate(read_data):
                line_num = i + 1; status = status_not_generated
                audio_file_for_line = self.audio_output_folder / f"{line_num:06d}.wav"
                if audio_file_for_line.exists(): status = status_success
                self.script_data.append({'line': line_num, **row, 'status': status})
                self.script_tree.insert('', 'end', values=(line_num, row['action'], row['talker'], row['words'], status))
            self.log(self._("ai_theater.log.csv_loaded").format(filepath=self.current_script_path, line_count=len(self.script_data), encoding=used_encoding))
        except Exception as e:
            messagebox.showerror(self._("ai_theater.messagebox.error.csv_read_failed.title"), self._("ai_theater.messagebox.error.csv_read_failed.message_generic").format(error=e), parent=self.root)
            self.current_script_path = None; self.audio_output_folder = None

    def load_text_script(self):
        """テキスト台本ファイルを読み込み、内容をパースしてUIに表示する。"""
        filepath = filedialog.askopenfilename(
            title=self._("ai_theater.filedialog.select_text_script_title"),
            filetypes=((self._("ai_theater.filedialog.text_files"), "*.txt"), (self._("ai_theater.filedialog.all_files"), "*.*")),
            parent=self.root
        )
        if not filepath:
            self.log(self._("ai_theater.log.txt_load_canceled"))
            return

        self.current_script_path = filepath
        self.script_data = []

        script_filename = Path(filepath).stem
        self.audio_output_folder = Path(filepath).parent / f"{script_filename}_audio"
        try:
            self.audio_output_folder.mkdir(parents=True, exist_ok=True)
            self.log(self._("ai_theater.log.audio_folder_created").format(folder_path=self.audio_output_folder))
        except Exception as e:
            self.log(self._("ai_theater.log.audio_folder_creation_failed").format(error=e))
            messagebox.showerror(
                self._("ai_theater.messagebox.error.folder_creation_failed.title"),
                self._("ai_theater.messagebox.error.folder_creation_failed.message").format(error=e),
                parent=self.root
            )
            self.current_script_path = None
            self.audio_output_folder = None
            return

        self.loaded_csv_label.configure(text=self._("ai_theater.label.loaded_file").format(filename=Path(filepath).name))
        self.script_tree.delete(*self.script_tree.get_children()) # 古い内容をクリア

        try:
            # --- 文字コード自動判別処理 ---
            with open(filepath, 'rb') as f_raw:
                raw_data = f_raw.read()

            detected_encoding_info = chardet.detect(raw_data)
            encoding_to_try = detected_encoding_info['encoding']
            confidence = detected_encoding_info['confidence']
            self.log(self._("ai_theater.log.txt_encoding_detected").format(filepath=filepath, encoding=encoding_to_try, confidence=confidence))

            if encoding_to_try is None or confidence < 0.7:
                self.log(self._("ai_theater.log.txt_encoding_low_confidence").format(confidence=confidence))
                encodings_to_attempt = ['utf-8', 'shift_jis', 'euc_jp']
            else:
                encodings_to_attempt = [encoding_to_try, 'utf-8', 'shift_jis', 'euc_jp']

            lines = None
            used_encoding = None
            for enc in list(dict.fromkeys(enc for enc in encodings_to_attempt if enc)): # Noneを除外
                try:
                    with open(filepath, 'r', encoding=enc) as f_in:
                        lines = f_in.readlines()
                    used_encoding = enc
                    self.log(self._("ai_theater.log.txt_read_success_encoding").format(encoding=enc))
                    break
                except UnicodeDecodeError:
                    self.log(self._("ai_theater.log.txt_read_fail_encoding").format(encoding=enc))
                    continue
                except Exception as e_open:
                    self.log(self._("ai_theater.log.txt_read_error_encoding").format(encoding=enc, error=e_open))
                    continue

            if lines is None:
                messagebox.showerror(
                    self._("ai_theater.messagebox.error.text_read_failed.title"),
                    self._("ai_theater.messagebox.error.text_read_failed.message_encoding"),
                    parent=self.root
                )
                self.log(self._("ai_theater.log.txt_read_encoding_not_found").format(filepath=filepath))
                self.current_script_path = None
                self.audio_output_folder = None
                self.loaded_csv_label.configure(text=self._("ai_theater.label.file_not_loaded"))
                return
            # --- 文字コード自動判別処理ここまで ---

            line_num = 1
            active_character_name = self._("ai_theater.dropdown.narrator") # デフォルト話者
            if self.current_character_id:
                char_data = self.config_manager.get_character(self.current_character_id)
                if char_data and char_data.get('name'):
                    active_character_name = char_data.get('name')
                else:
                    self.log(self._("ai_theater.log.txt_char_data_not_found").format(char_id=self.current_character_id))
            else:
                self.log(self._("ai_theater.log.txt_current_char_id_not_set"))

            self.log(self._("ai_theater.log.txt_default_talker").format(talker_name=active_character_name, encoding=used_encoding))

            status_not_generated = self._("ai_theater.status.not_generated")
            i = 0
            while i < len(lines):
                line_content = lines[i].strip()
                if not line_content:
                    empty_line_count = 0
                    while i < len(lines) and not lines[i].strip():
                        empty_line_count += 1
                        i += 1
                    wait_time = empty_line_count * 0.5
                    self.script_data.append({
                        'line': line_num, 'action': "wait", 'talker': "",
                        'words': str(wait_time), 'status': status_not_generated
                    })
                    self.script_tree.insert('', 'end', values=(
                        line_num, "wait", "", str(wait_time), status_not_generated
                    ))
                    line_num += 1
                else:
                    self.script_data.append({
                        'line': line_num, 'action': "talk", 'talker': active_character_name,
                        'words': line_content, 'status': status_not_generated
                    })
                    self.script_tree.insert('', 'end', values=(
                        line_num, "talk", active_character_name, line_content, status_not_generated
                    ))
                    line_num += 1
                    i += 1

            self.log(self._("ai_theater.log.txt_loaded").format(filepath=filepath, line_count=len(self.script_data)))
            if not self.script_data:
                messagebox.showinfo(
                    self._("ai_theater.messagebox.info.txt_empty.title"),
                    self._("ai_theater.messagebox.info.txt_empty.message"),
                    parent=self.root
                )

        except FileNotFoundError:
            messagebox.showerror(self._("ai_theater.messagebox.error.file_not_found.title"), self._("ai_theater.messagebox.error.file_not_found.message").format(filepath=filepath), parent=self.root)
            self.log(self._("ai_theater.log.txt_file_not_found").format(filepath=filepath))
            self.current_script_path = None
            self.audio_output_folder = None
            self.loaded_csv_label.configure(text=self._("ai_theater.label.file_not_loaded"))
        except Exception as e:
            messagebox.showerror(self._("ai_theater.messagebox.error.text_read_failed.title"), self._("ai_theater.messagebox.error.text_read_failed.message_generic").format(e=e), parent=self.root)
            self.log(self._("ai_theater.log.txt_load_error").format(error=e))
            self.current_script_path = None
            self.audio_output_folder = None
            self.loaded_csv_label.configure(text=self._("ai_theater.label.file_not_loaded"))

    def create_new_csv_script_action(self):
        filepath = filedialog.asksaveasfilename(
            title=self._("ai_theater.filedialog.save_new_csv_script_title"),
            defaultextension=".csv",
            filetypes=[(self._("ai_theater.filedialog.csv_files"), "*.csv")],
            parent=self.root
        )
        if not filepath: return
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                csv.writer(csvfile).writerow(['action', 'talker', 'words'])
            self.log(self._("ai_theater.log.new_csv_created").format(filepath=filepath))
            self.load_csv_script_action(filepath)
            messagebox.showinfo(
                self._("ai_theater.messagebox.info.new_csv_created.title"),
                self._("ai_theater.messagebox.info.new_csv_created.message").format(filename=Path(filepath).name),
                parent=self.root
            )
        except Exception as e:
            messagebox.showerror(
                self._("ai_theater.messagebox.error.new_csv_creation_failed.title"),
                self._("ai_theater.messagebox.error.new_csv_creation_failed.message").format(e=e),
                parent=self.root
            )

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
        except (IndexError, ValueError) as e: self.log(self._("ai_theater.log.line_selection_error").format(error=e))

    def add_script_line_to_preview_action(self, and_generate=False):
        action = self.script_action_var.get()
        talker = self.script_talker_var.get() if action != "wait" else ""
        words = self.script_words_entry.get()
        if not self._validate_script_line_input(action, talker, words): return
        new_line_num = (max(item['line'] for item in self.script_data) + 1) if self.script_data else 1
        status_not_generated = self._("ai_theater.status.not_generated")
        new_line_data = {'line': new_line_num, 'action': action, 'talker': talker, 'words': words, 'status': status_not_generated}
        self.script_data.append(new_line_data)
        item_id = self.script_tree.insert('', 'end', values=(new_line_num, action, talker, words, status_not_generated))
        self.script_tree.see(item_id)
        self.log(self._("ai_theater.log.line_added").format(line_num=new_line_num, action=action, talker=talker, words_preview=words[:20]))
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
        if not selected_items:
            messagebox.showwarning(self._("ai_theater.messagebox.warning.no_line_selected_update.title"), self._("ai_theater.messagebox.warning.no_line_selected_update.message"), parent=self.root)
            return
        item_id = selected_items[0]
        try: line_num_to_update = int(self.script_tree.item(item_id, 'values')[0])
        except (IndexError, ValueError): return
        new_action = self.script_action_var.get()
        new_talker = self.script_talker_var.get() if new_action != "wait" else ""
        new_words = self.script_words_entry.get()
        if not self._validate_script_line_input(new_action, new_talker, new_words): return

        status_not_generated = self._("ai_theater.status.not_generated")
        for i, data_item in enumerate(self.script_data):
            if data_item['line'] == line_num_to_update:
                old_words = data_item['words']
                data_item.update({'action': new_action, 'talker': new_talker, 'words': new_words, 'status': status_not_generated})
                self.script_tree.item(item_id, values=(line_num_to_update, new_action, new_talker, new_words, status_not_generated))
                if old_words != new_words or data_item['action'] != new_action or data_item['talker'] != new_talker :
                    self._delete_audio_file_for_line(line_num_to_update)
                self.log(self._("ai_theater.log.line_updated").format(line_num=line_num_to_update)); break

    def clear_script_input_area_action(self):
        self.script_action_var.set("talk")
        self.script_talker_var.set(self.script_talker_combo.cget("values")[0] if self.script_talker_combo.cget("values") else "")
        self.script_words_entry.delete(0, "end")
        self.on_script_action_selected_ui_update()
        if self.script_tree.selection(): self.script_tree.selection_remove(self.script_tree.selection())

    def _validate_script_line_input(self, action, talker, words):
        if not action:
            messagebox.showwarning(self._("ai_theater.messagebox.warning.input_error.title"), self._("ai_theater.messagebox.warning.input_error.message_action"), parent=self.root); return False
        if action != "wait" and not talker:
            messagebox.showwarning(self._("ai_theater.messagebox.warning.input_error.title"), self._("ai_theater.messagebox.warning.input_error.message_talker"), parent=self.root); return False
        if not words and (action == "talk" or action == "narration"):
            messagebox.showwarning(self._("ai_theater.messagebox.warning.input_error.title"), self._("ai_theater.messagebox.warning.input_error.message_words_empty"), parent=self.root); return False
        if action == "wait" and not words.strip().replace('.', '', 1).isdigit():
            messagebox.showwarning(self._("ai_theater.messagebox.warning.input_error.title"), self._("ai_theater.messagebox.warning.input_error.message_wait_time_numeric"), parent=self.root); return False
        return True

    def _start_audio_generation_for_line(self, line_data):
        if not self.audio_output_folder:
            messagebox.showerror(self._("ai_theater.messagebox.error.audio_folder_not_set.title"), self._("ai_theater.messagebox.error.audio_folder_not_set.message"), parent=self.root); return
        self._update_line_status_in_tree(line_data['line'], self._("ai_theater.status.generating"))
        threading.Thread(target=self._synthesize_single_line_audio_thread, args=(line_data,), daemon=True).start()

    def _synthesize_single_line_audio_thread(self, line_data):
        loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
        success = False
        try: success = loop.run_until_complete(self._synthesize_script_line_logic(line_data))
        except Exception as e: self.log(self._("ai_theater.log.audio_synth_thread_error").format(line_num=line_data['line'], error=e))
        finally:
            loop.close()
            final_status = self._("ai_theater.status.success") if success else self._("ai_theater.status.failed")
            self.root.after(0, self._update_line_status_in_tree, line_data['line'], final_status)
            if not success:
                self.root.after(0, messagebox.showerror,
                                self._("ai_theater.messagebox.error.audio_generation_failed.title"),
                                self._("ai_theater.messagebox.error.audio_generation_failed.message").format(line_num=line_data['line']),
                                parent=self.root if self.root.winfo_exists() else None)

    async def _synthesize_script_line_logic(self, line_data: dict) -> bool:
        line_num, action, talker, words = line_data['line'], line_data['action'], line_data['talker'], line_data['words']
        output_wav_path = self.audio_output_folder / f"{line_num:06d}.wav"
        self.log(self._("ai_theater.log.audio_generation_started").format(line_num=line_num, action=action, talker=talker, words_preview=words[:20]))
        if action == "talk" or action == "narration":
            char_id_to_use = self._get_char_id_for_talker(talker)
            if not char_id_to_use:
                self.log(self._("ai_theater.log.talker_char_settings_not_found_skip").format(talker=talker, line_num=line_num)); return False
            char_settings = self.config_manager.get_character(char_id_to_use)
            if not char_settings: return False # Should not happen if char_id_to_use is valid
            voice_settings = char_settings.get('voice_settings', {})
            engine = voice_settings.get('engine', self.config_manager.get_system_setting("voice_engine"))
            model = voice_settings.get('model'); speed = voice_settings.get('speed', 1.0)
            api_key = self.config_manager.get_system_setting("google_ai_api_key") if "google_ai_studio" in engine else None
            audio_files = await self.voice_manager.synthesize_with_fallback(words, model, speed, preferred_engine=engine, api_key=api_key)
            if audio_files and Path(audio_files[0]).exists():
                try:
                    if output_wav_path.exists(): output_wav_path.unlink()
                    shutil.move(audio_files[0], output_wav_path)
                    self.log(self._("ai_theater.log.audio_file_generated_success").format(output_path=output_wav_path)); return True
                except Exception as e_move:
                    self.log(self._("ai_theater.log.audio_file_move_error").format(line_num=line_num, error_move=e_move))
                    if Path(audio_files[0]).exists(): Path(audio_files[0]).unlink(missing_ok=True) # Clean up temp file
                    return False
            return False # Synthesis failed or no audio file produced
        elif action == "wait":
            try:
                duration = float(words); framerate=24000; channels=1; sampwidth=2
                num_frames = int(framerate * duration); silence = b'\x00\x00' * num_frames
                with wave.open(str(output_wav_path), 'wb') as wf:
                    wf.setnchannels(channels); wf.setsampwidth(sampwidth); wf.setframerate(framerate); wf.writeframes(silence)
                self.log(self._("ai_theater.log.silent_file_created_success").format(duration=duration, output_path=output_wav_path)); return True
            except Exception as e_wave: self.log(self._("ai_theater.log.silent_file_creation_error").format(line_num=line_num, error_wave=e_wave)); return False
        return False # Should not be reached if action is valid

    def _get_char_id_for_talker(self, talker_name):
        all_chars = self.character_manager.get_all_characters()
        for char_id, data in all_chars.items():
            if data.get('name') == talker_name: return char_id
        self.log(self._("ai_theater.log.talker_char_not_found").format(talker_name=talker_name)); return None

    def _update_line_status_in_tree(self, line_num: int, status: str): # status is already translated
        for item_id in self.script_tree.get_children():
            if int(self.script_tree.item(item_id, 'values')[0]) == line_num:
                current_values = list(self.script_tree.item(item_id, 'values')); current_values[4] = status
                self.script_tree.item(item_id, values=tuple(current_values))
                for data_item in self.script_data: # Update internal data as well
                    if data_item['line'] == line_num: data_item['status'] = status; break
                break

    def _delete_audio_file_for_line(self, line_num):
        if not self.audio_output_folder: return
        audio_file = self.audio_output_folder / f"{line_num:06d}.wav"
        if audio_file.exists():
            try: audio_file.unlink(); self.log(self._("ai_theater.log.audio_file_deleted").format(audio_file=audio_file))
            except Exception as e: self.log(self._("ai_theater.log.audio_file_delete_error").format(audio_file=audio_file, error=e))

    def generate_selected_line_audio_action(self):
        selected_items = self.script_tree.selection()
        if not selected_items:
            messagebox.showwarning(self._("ai_theater.messagebox.warning.no_line_selected_generate.title"), self._("ai_theater.messagebox.warning.no_line_selected_generate.message"), parent=self.root); return
        item_id = selected_items[0]; line_num = int(self.script_tree.item(item_id, 'values')[0])
        line_data = next((item for item in self.script_data if item['line'] == line_num), None)
        if line_data: self._start_audio_generation_for_line(line_data)

    def generate_all_lines_audio_action(self):
        if not self.script_data:
            messagebox.showinfo(self._("ai_theater.messagebox.info.script_empty_generate_all.title"), self._("ai_theater.messagebox.info.script_empty_generate_all.message"), parent=self.root); return
        if not self.audio_output_folder:
            messagebox.showerror(self._("ai_theater.messagebox.error.audio_folder_not_set.title"), self._("ai_theater.messagebox.error.audio_folder_not_set_generate_all.message"), parent=self.root); return # Specific message for this case
        if not messagebox.askyesno(
            self._("ai_theater.messagebox.confirm.generate_all_audio.title"),
            self._("ai_theater.messagebox.confirm.generate_all_audio.message").format(line_count=len(self.script_data)),
            parent=self.root): return
        self.log(self._("ai_theater.log.all_lines_audio_generation_started"))
        threading.Thread(target=self._generate_all_lines_audio_thread, daemon=True).start()

    def _generate_all_lines_audio_thread(self):
        progress_root = tk.Toplevel(self.root)
        progress_root.title(self._("ai_theater.progress_popup.title"))
        progress_root.geometry("300x100")
        progress_root.transient(self.root); progress_root.grab_set()
        ttk.Label(progress_root, text=self._("ai_theater.progress_popup.label")).pack(pady=10)
        progress_var = tk.DoubleVar(); progressbar = ttk.Progressbar(progress_root, variable=progress_var, maximum=len(self.script_data), length=280)
        progressbar.pack(pady=10)

        loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
        success_count = 0; fail_count = 0

        status_generating = self._("ai_theater.status.generating")
        status_success = self._("ai_theater.status.success")
        status_failed = self._("ai_theater.status.failed")
        status_skipped = self._("ai_theater.status.success") # 既存の成功ステータスを流用
        try:
            for i, line_data in enumerate(self.script_data):
                if self.stop_requested: break

                line_num = line_data['line']
                audio_file_path = self.audio_output_folder / f"{line_num:06d}.wav"

                if audio_file_path.exists():
                    self.log(f"Line {line_num}: Audio file already exists, skipping generation.")
                    self.root.after(0, self._update_line_status_in_tree, line_num, status_skipped)
                    success_count += 1
                    progress_var.set(i + 1); progress_root.update_idletasks()
                    continue

                self.root.after(0, self._update_line_status_in_tree, line_data['line'], status_generating)
                success = loop.run_until_complete(self._synthesize_script_line_logic(line_data))
                final_status = status_success if success else status_failed
                self.root.after(0, self._update_line_status_in_tree, line_data['line'], final_status)
                if success: success_count +=1
                else: fail_count +=1
                progress_var.set(i + 1); progress_root.update_idletasks()

            self.log(self._("ai_theater.log.all_lines_audio_generation_complete").format(success_count=success_count, fail_count=fail_count))
            if fail_count > 0:
                messagebox.showwarning(
                    self._("ai_theater.messagebox.warning.some_audio_generation_failed.title"),
                    self._("ai_theater.messagebox.warning.some_audio_generation_failed.message").format(success_count=success_count, fail_count=fail_count),
                    parent=self.root if self.root.winfo_exists() else None)
            else:
                messagebox.showinfo(
                    self._("ai_theater.messagebox.info.all_audio_generation_complete.title"),
                    self._("ai_theater.messagebox.info.all_audio_generation_complete.message").format(success_count=success_count),
                    parent=self.root if self.root.winfo_exists() else None)
        except Exception as e:
            self.log(self._("ai_theater.log.all_lines_audio_generation_error").format(error=e))
            messagebox.showerror(
                self._("ai_theater.messagebox.error.bulk_generation_error.title"),
                self._("ai_theater.messagebox.error.bulk_generation_error.message").format(e=e),
                parent=self.root if self.root.winfo_exists() else None)
        finally:
            loop.close()
            if progress_root.winfo_exists(): progress_root.destroy()

    def play_selected_line_audio_action(self):
        selected_items = self.script_tree.selection()
        if not selected_items:
            messagebox.showwarning(self._("ai_theater.messagebox.warning.no_line_selected_play.title"), self._("ai_theater.messagebox.warning.no_line_selected_play.message"), parent=self.root); return
        item_id = selected_items[0]; line_num = int(self.script_tree.item(item_id, 'values')[0])
        audio_file = self.audio_output_folder / f"{line_num:06d}.wav" if self.audio_output_folder else None
        if audio_file and audio_file.exists():
            self.log(self._("ai_theater.log.audio_playback").format(audio_file=audio_file))
            def play_async():
                loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
                try: loop.run_until_complete(self.audio_player.play_audio_file(str(audio_file)))
                except Exception as e: self.log(self._("ai_theater.log.audio_playback_error").format(error=e))
                finally: loop.close()
            threading.Thread(target=play_async, daemon=True).start()
        else:
            messagebox.showinfo(
                self._("ai_theater.messagebox.info.audio_file_not_found_or_generated.title"),
                self._("ai_theater.messagebox.info.audio_file_not_found_or_generated.message"),
                parent=self.root
            )

    def play_script_sequentially_action(self):
        if not self.script_data:
            messagebox.showinfo(self._("ai_theater.messagebox.info.script_empty_play_all.title"), self._("ai_theater.messagebox.info.script_empty_play_all.message"), parent=self.root); return
        if self.is_playing_script:
            messagebox.showwarning(self._("ai_theater.messagebox.warning.already_playing.title"), self._("ai_theater.messagebox.warning.already_playing.message"), parent=self.root); return
        self.is_playing_script = True; self.stop_requested = False
        self.log(self._("ai_theater.log.sequential_play_started"))
        threading.Thread(target=self._play_script_sequentially_thread, daemon=True).start()

    def _play_script_sequentially_thread(self):
        loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)

        status_playback_ready = self._("ai_theater.status.playback_ready")
        status_generating = self._("ai_theater.status.generating")
        status_generation_failed = self._("ai_theater.status.failed") # Re-use for generation
        status_generation_success = self._("ai_theater.status.success") # Re-use for generation
        status_playing = self._("ai_theater.status.playing")
        status_played = self._("ai_theater.status.played")
        status_file_not_found = self._("ai_theater.status.file_not_found")
        try:
            for line_data in self.script_data:
                if self.stop_requested: self.log(self._("ai_theater.log.sequential_play_user_stop")); break
                line_num = line_data['line']
                self.root.after(0, self._update_line_status_in_tree, line_num, status_playback_ready)
                audio_file = self.audio_output_folder / f"{line_num:06d}.wav"
                if not audio_file.exists():
                    self.root.after(0, self._update_line_status_in_tree, line_num, status_generating)
                    if not loop.run_until_complete(self._synthesize_script_line_logic(line_data)):
                        self.root.after(0, self._update_line_status_in_tree, line_num, status_generation_failed); continue
                    self.root.after(0, self._update_line_status_in_tree, line_num, status_generation_success) # Mark as success after generation
                if audio_file.exists(): # Check again after potential generation
                    self.root.after(0, self._update_line_status_in_tree, line_num, status_playing)
                    loop.run_until_complete(self.audio_player.play_audio_file(str(audio_file)))
                    self.root.after(0, self._update_line_status_in_tree, line_num, status_played)
                else: # Still not found after trying to generate
                    self.root.after(0, self._update_line_status_in_tree, line_num, status_file_not_found)
                time.sleep(0.1) # Small delay between lines
            if not self.stop_requested: self.log(self._("ai_theater.log.sequential_play_complete"))
            if self.root.winfo_exists() and not self.stop_requested :
                messagebox.showinfo(
                    self._("ai_theater.messagebox.info.sequential_play_complete.title"),
                    self._("ai_theater.messagebox.info.sequential_play_complete.message"),
                    parent=self.root
                )
        except Exception as e:
            self.log(self._("ai_theater.log.sequential_play_error").format(error=e))
            if self.root.winfo_exists():
                messagebox.showerror(
                    self._("ai_theater.messagebox.error.playback_error.title"),
                    self._("ai_theater.messagebox.error.playback_error.message").format(e=e),
                    parent=self.root
                )
        finally: self.is_playing_script = False; self.stop_requested = False; loop.close()

    def stop_sequential_play_action(self):
        if self.is_playing_script: self.stop_requested = True; self.log(self._("ai_theater.log.sequential_play_stop_requested"))
        else: messagebox.showinfo(self._("ai_theater.messagebox.info.not_playing.title"), self._("ai_theater.messagebox.info.not_playing.message"), parent=self.root)

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
                    if Path(final_p_str).exists(): Path(final_p_str).unlink() # Ensure target is clear
                    Path(temp_p_str).rename(final_p_str)
        except Exception as e_rename: self.log(self._("ai_theater.log.audio_file_rename_error").format(error_rename=e_rename))

        self.script_tree.delete(*self.script_tree.get_children()) # Clear UI
        newly_selected_item_tree_id = None
        for item_d in self.script_data: # Re-populate UI from potentially re-ordered self.script_data
            tid = self.script_tree.insert('', 'end', values=(item_d['line'], item_d['action'], item_d['talker'], item_d['words'], item_d['status']))
            if select_new_line_num is not None and item_d['line'] == select_new_line_num:
                newly_selected_item_tree_id = tid

        if newly_selected_item_tree_id: # Re-select and focus the moved item
            self.script_tree.selection_set(newly_selected_item_tree_id)
            self.script_tree.focus(newly_selected_item_tree_id)
            self.script_tree.see(newly_selected_item_tree_id)
        self.log(self._("ai_theater.log.ui_remapping_complete"))

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
        if not messagebox.askyesno(
            self._("ai_theater.messagebox.confirm.delete_line.title"),
            self._("ai_theater.messagebox.confirm.delete_line.message").format(line_num_to_delete=line_num_to_delete, words_preview=words_preview),
            parent=self.root): return

        original_len = len(self.script_data)
        self.script_data = [item for item in self.script_data if item['line'] != line_num_to_delete]
        if len(self.script_data) < original_len: # Check if deletion actually happened
            self._delete_audio_file_for_line(line_num_to_delete)
            self._remap_lines_and_ui_after_edit() # This will re-populate the treeview and handle audio files
            self.log(self._("ai_theater.log.line_deleted").format(line_num_to_delete=line_num_to_delete))

    def export_script_to_csv_action(self):
        if not self.script_data:
            messagebox.showinfo(self._("ai_theater.messagebox.info.no_data_to_export.title"), self._("ai_theater.messagebox.info.no_data_to_export.message"), parent=self.root); return

        initial_filename = self.current_script_path.name if self.current_script_path else "script.csv"
        filepath = filedialog.asksaveasfilename(
            title=self._("ai_theater.filedialog.save_csv_script_title"),
            defaultextension=".csv",
            filetypes=[(self._("ai_theater.filedialog.csv_files"), "*.csv")],
            parent=self.root,
            initialfile=initial_filename
        )
        if not filepath: return
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=['action', 'talker', 'words'])
                writer.writeheader()
                for line_data in self.script_data: # Use the current self.script_data
                    writer.writerow({'action': line_data['action'], 'talker': line_data['talker'], 'words': line_data['words']})
            self.log(self._("ai_theater.log.csv_export_complete").format(filepath=filepath))
            messagebox.showinfo(
                self._("ai_theater.messagebox.info.export_complete.title"),
                self._("ai_theater.messagebox.info.export_complete.message").format(filename=Path(filepath).name),
                parent=self.root
            )
        except Exception as e:
            messagebox.showerror(
                self._("ai_theater.messagebox.error.export_error.title"),
                self._("ai_theater.messagebox.error.export_error.message").format(e=e),
                parent=self.root
            )

    def delete_all_audio_files_action(self):
        if not self.audio_output_folder or not self.audio_output_folder.exists():
            messagebox.showinfo(self._("ai_theater.messagebox.info.audio_folder_not_found.title"), self._("ai_theater.messagebox.info.audio_folder_not_found.message"), parent=self.root); return
        if not messagebox.askyesno(
            self._("ai_theater.messagebox.confirm.delete_all_audio.title"),
            self._("ai_theater.messagebox.confirm.delete_all_audio.message").format(folder_name=self.audio_output_folder.name),
            parent=self.root): return

        deleted_count = 0; failed_count = 0
        for item in self.audio_output_folder.iterdir():
            if item.is_file() and item.suffix.lower() == '.wav':
                try: item.unlink(); deleted_count +=1
                except Exception as e: self.log(self._("ai_theater.log.file_delete_error").format(item=item, error=e)); failed_count +=1

        self.log(self._("ai_theater.log.audio_all_deleted").format(deleted_count=deleted_count, failed_count=failed_count))

        if failed_count > 0:
            message = self._("ai_theater.messagebox.info.delete_all_audio_complete.message_some_failed").format(deleted_count=deleted_count, failed_count=failed_count)
        else:
            message = self._("ai_theater.messagebox.info.delete_all_audio_complete.message").format(deleted_count=deleted_count)
        messagebox.showinfo(self._("ai_theater.messagebox.info.delete_all_audio_complete.title"), message, parent=self.root)

        status_not_generated = self._("ai_theater.status.not_generated")
        for item_id in self.script_tree.get_children(): # Update UI
            line_num = int(self.script_tree.item(item_id, 'values')[0])
            self._update_line_status_in_tree(line_num, status_not_generated) # status is already translated

def main():
    # i18n_setup.init_i18n() # Moved to class init
    # _ = i18n_setup.get_translator() # Moved to class init
    customtkinter.set_appearance_mode("System")
    customtkinter.set_default_color_theme("blue")
    root = customtkinter.CTk()
    app = AITheaterWindow(root)
    root.mainloop()

if __name__ == "__main__":
    customtkinter.set_appearance_mode("System")
    customtkinter.set_default_color_theme("blue")
    main()
