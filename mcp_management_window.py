import customtkinter
import tkinter as tk
from tkinter import ttk, messagebox
import json
import threading
import asyncio
import logging
from pathlib import Path

from config import ConfigManager
from mcp_client import MCPClientManager
import i18n_setup

class TreeviewToolTip:
    """
    Treeview専用のツールチップクラス
    """
    def __init__(self, treeview):
        self.treeview = treeview
        self.tooltip_window = None
        self.treeview.bind("<Motion>", self.on_motion)
        self.treeview.bind("<Leave>", self.hide_tooltip)

    def on_motion(self, event):
        # 既存のツールチップを非表示
        self.hide_tooltip()
        
        # マウス位置のアイテムを特定
        item_id = self.treeview.identify_row(event.y)
        if item_id:
            # アイテムの情報を取得
            values = self.treeview.item(item_id, 'values')
            if len(values) >= 4:  # description列がある場合
                description = values[3]  # description列
                if description and len(description) > 30:  # 長い説明の場合のみ表示
                    self.show_tooltip(event, description)

    def show_tooltip(self, event, text):
        x = event.x_root + 10
        y = event.y_root + 10
        
        self.tooltip_window = tw = tk.Toplevel(self.treeview)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(tw, text=text, justify='left',
                       background="#ffffe0", relief='solid', borderwidth=1,
                       font=("Yu Gothic UI", "9", "normal"), wraplength=400)
        label.pack(ipadx=1)

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

logger = logging.getLogger(__name__)

class MCPManagementWindow:
    def __init__(self, root: customtkinter.CTk):
        i18n_setup.init_i18n()
        self._ = i18n_setup.get_translator()
        
        self.root = root
        self.root.title(self._("mcp_management.title"))
        self.root.geometry("800x600")
        
        self.config = ConfigManager()
        self.mcp_client_manager = MCPClientManager(config_manager=self.config)
        
        # フォント設定
        self.default_font = ("Yu Gothic UI", 12)
        self.header_font = ("Yu Gothic UI", 14, "bold")
        
        self.create_widgets()
        self.load_mcp_servers()
        
        # ウィンドウが閉じられる時の処理
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def create_widgets(self):
        # メインフレーム
        main_frame = customtkinter.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # ヘッダー
        header_label = customtkinter.CTkLabel(
            main_frame, 
            text=self._("mcp_management.header"), 
            font=self.header_font
        )
        header_label.pack(pady=(10, 20))
        
        # 左右分割フレーム
        content_frame = customtkinter.CTkFrame(main_frame)
        content_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 左側：サーバーリスト
        left_frame = customtkinter.CTkFrame(content_frame)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        # サーバーリストラベル
        list_label = customtkinter.CTkLabel(
            left_frame, 
            text=self._("mcp_management.server_list"), 
            font=self.header_font
        )
        list_label.pack(pady=(10, 5), padx=10, anchor="w")
        
        # サーバーリスト用フレーム
        list_frame = customtkinter.CTkFrame(left_frame)
        list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Treeview for server list
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview", font=self.default_font, rowheight=25)
        style.configure("Treeview.Heading", font=self.header_font)
        
        self.server_tree = ttk.Treeview(
            list_frame, 
            columns=('name', 'status', 'enabled', 'description'), 
            show='headings',
            style="Treeview"
        )
        
        # カラム設定
        self.server_tree.heading('name', text=self._("mcp_management.column.name"))
        self.server_tree.heading('status', text=self._("mcp_management.column.status"))
        self.server_tree.heading('enabled', text=self._("mcp_management.column.enabled"))
        self.server_tree.heading('description', text=self._("mcp_management.column.description"))
        
        self.server_tree.column('name', width=120, stretch=False)
        self.server_tree.column('status', width=80, stretch=False)
        self.server_tree.column('enabled', width=80, stretch=False)
        self.server_tree.column('description', width=200, stretch=True)
        
        # スクロールバー
        scrollbar_y = ttk.Scrollbar(list_frame, orient="vertical", command=self.server_tree.yview)
        self.server_tree.configure(yscrollcommand=scrollbar_y.set)
        
        scrollbar_y.pack(side="right", fill="y")
        self.server_tree.pack(side="left", fill="both", expand=True)
        
        # 選択イベント
        self.server_tree.bind('<<TreeviewSelect>>', self.on_server_selected)
        
        # ツールチップを追加
        self.tree_tooltip = TreeviewToolTip(self.server_tree)
        
        # 右側：詳細・操作パネル
        right_frame = customtkinter.CTkFrame(content_frame)
        right_frame.pack(side="right", fill="y", padx=(5, 0))
        right_frame.configure(width=300)
        
        # 詳細情報ラベル
        detail_label = customtkinter.CTkLabel(
            right_frame, 
            text=self._("mcp_management.server_details"), 
            font=self.header_font
        )
        detail_label.pack(pady=(10, 5), padx=10, anchor="w")
        
        # 詳細情報表示フレーム
        self.detail_frame = customtkinter.CTkFrame(right_frame)
        self.detail_frame.pack(fill="x", padx=10, pady=5)
        
        # サーバー名
        self.name_label = customtkinter.CTkLabel(
            self.detail_frame, 
            text=self._("mcp_management.detail.no_selection"), 
            font=self.default_font,
            anchor="w"
        )
        self.name_label.pack(fill="x", padx=10, pady=5)
        
        # 操作ボタンフレーム
        button_frame = customtkinter.CTkFrame(right_frame)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        # 有効/無効切り替えボタン
        self.toggle_button = customtkinter.CTkButton(
            button_frame,
            text=self._("mcp_management.button.toggle_enable"),
            command=self.toggle_server_enabled,
            state="disabled"
        )
        self.toggle_button.pack(fill="x", padx=5, pady=2)
        
        # 接続テストボタン
        self.test_button = customtkinter.CTkButton(
            button_frame,
            text=self._("mcp_management.button.test_connection"),
            command=self.test_server_connection,
            state="disabled"
        )
        self.test_button.pack(fill="x", padx=5, pady=2)
        
        # リフレッシュボタン
        self.refresh_button = customtkinter.CTkButton(
            button_frame,
            text=self._("mcp_management.button.refresh"),
            command=self.refresh_servers
        )
        self.refresh_button.pack(fill="x", padx=5, pady=2)
        
        # 全体操作フレーム
        global_frame = customtkinter.CTkFrame(right_frame)
        global_frame.pack(fill="x", padx=10, pady=10)
        
        global_label = customtkinter.CTkLabel(
            global_frame,
            text=self._("mcp_management.global_operations"),
            font=self.header_font
        )
        global_label.pack(pady=(5, 10))
        
        # 全サーバー接続テスト
        self.test_all_button = customtkinter.CTkButton(
            global_frame,
            text=self._("mcp_management.button.test_all"),
            command=self.test_all_servers
        )
        self.test_all_button.pack(fill="x", padx=5, pady=2)
        
        # ステータス表示
        self.status_label = customtkinter.CTkLabel(
            main_frame,
            text=self._("mcp_management.status.ready"),
            font=self.default_font
        )
        self.status_label.pack(side="bottom", pady=5)
        
        self.selected_server = None
        
    def load_mcp_servers(self):
        """設定からMCPサーバー情報を読み込み、リストに表示"""
        # 既存のアイテムをクリア
        for item in self.server_tree.get_children():
            self.server_tree.delete(item)
            
        mcp_settings = self.config.get_mcp_settings()
        servers = mcp_settings.get("servers", {})
        
        for server_name, server_config in servers.items():
            enabled = server_config.get("enabled", True)
            description = server_config.get("description", "")
            
            # 接続状態を確認
            status = self._("mcp_management.status.disconnected")
            if server_name in self.mcp_client_manager.sessions:
                status = self._("mcp_management.status.connected")
            elif not enabled:
                status = self._("mcp_management.status.disabled")
                
            enabled_text = self._("mcp_management.enabled") if enabled else self._("mcp_management.disabled")
            
            self.server_tree.insert('', 'end', values=(
                server_name, 
                status, 
                enabled_text, 
                description
            ), iid=server_name)
            
    def on_server_selected(self, event):
        """サーバーが選択された時の処理"""
        selection = self.server_tree.selection()
        if not selection:
            self.selected_server = None
            self.update_detail_panel(None)
            return
            
        server_name = selection[0]
        self.selected_server = server_name
        server_config = self.config.get_mcp_server_config(server_name)
        self.update_detail_panel(server_name, server_config)
        
    def update_detail_panel(self, server_name, server_config=None):
        """詳細パネルを更新"""
        # 既存の詳細情報をクリア
        for widget in self.detail_frame.winfo_children():
            widget.destroy()
            
        if not server_name or not server_config:
            self.name_label = customtkinter.CTkLabel(
                self.detail_frame,
                text=self._("mcp_management.detail.no_selection"),
                font=self.default_font
            )
            self.name_label.pack(fill="x", padx=10, pady=5)
            
            # ボタンを無効化
            self.toggle_button.configure(state="disabled")
            self.test_button.configure(state="disabled")
            return
            
        # サーバー詳細情報を表示
        details = [
            (self._("mcp_management.detail.name"), server_name),
            (self._("mcp_management.detail.enabled"), 
             self._("mcp_management.enabled") if server_config.get("enabled", True) else self._("mcp_management.disabled")),
            (self._("mcp_management.detail.command"), server_config.get("command", "")),
            (self._("mcp_management.detail.args"), " ".join(server_config.get("args", []))),
            (self._("mcp_management.detail.description"), server_config.get("description", "")),
        ]
        
        for label_text, value_text in details:
            detail_row = customtkinter.CTkFrame(self.detail_frame)
            detail_row.pack(fill="x", padx=5, pady=2)
            
            label = customtkinter.CTkLabel(
                detail_row,
                text=f"{label_text}:",
                font=(self.default_font[0], self.default_font[1], "bold"),
                anchor="w"
            )
            label.pack(anchor="w", padx=5)
            
            value = customtkinter.CTkLabel(
                detail_row,
                text=str(value_text),
                font=self.default_font,
                anchor="w",
                wraplength=250
            )
            value.pack(anchor="w", padx=15)
            
        # ボタンを有効化
        self.toggle_button.configure(state="normal")
        self.test_button.configure(state="normal")
        
        # トグルボタンのテキストを更新
        enabled = server_config.get("enabled", True)
        toggle_text = self._("mcp_management.button.disable") if enabled else self._("mcp_management.button.enable")
        self.toggle_button.configure(text=toggle_text)
        
    def toggle_server_enabled(self):
        """選択されたサーバーの有効/無効を切り替え"""
        if not self.selected_server:
            return
            
        server_config = self.config.get_mcp_server_config(self.selected_server)
        if not server_config:
            return
            
        current_enabled = server_config.get("enabled", True)
        new_enabled = not current_enabled
        
        server_config["enabled"] = new_enabled
        self.config.save_mcp_server_config(self.selected_server, server_config)
        
        # UI更新
        self.load_mcp_servers()
        self.update_detail_panel(self.selected_server, server_config)
        
        action = self._("mcp_management.enabled") if new_enabled else self._("mcp_management.disabled")
        self.status_label.configure(text=self._("mcp_management.status.server_toggled", server=self.selected_server, action=action))
        
    def test_server_connection(self):
        """選択されたサーバーへの接続をテスト"""
        if not self.selected_server:
            return
            
        self.test_button.configure(state="disabled", text=self._("mcp_management.button.testing"))
        self.status_label.configure(text=self._("mcp_management.status.testing_connection", server=self.selected_server))
        
        # 別スレッドでテスト実行
        threading.Thread(
            target=self._test_server_connection_async, 
            args=(self.selected_server,), 
            daemon=True
        ).start()
        
    def _test_server_connection_async(self, server_name):
        """非同期でサーバー接続をテスト"""
        async def test_connection():
            try:
                server_config = self.config.get_mcp_server_config(server_name)
                if not server_config:
                    self.root.after(0, self._show_test_result, server_name, False, "Server configuration not found")
                    return
                    
                if not server_config.get("enabled", True):
                    self.root.after(0, self._show_test_result, server_name, False, "Server is disabled")
                    return
                    
                # 一時的なMCPクライアントマネージャーで接続テスト
                test_manager = MCPClientManager(config_manager=self.config)
                
                try:
                    # 接続テストにタイムアウトを設定
                    await asyncio.wait_for(
                        test_manager.connect_to_server(server_name, server_config),
                        timeout=10  # 10秒タイムアウト
                    )
                    
                    # ツール一覧取得テスト
                    tools = list(test_manager.available_tools.keys())
                    tool_count = len(tools)
                    
                    self.root.after(0, self._show_test_result, server_name, True, f"Successfully connected. Found {tool_count} tools.")
                    
                except asyncio.TimeoutError:
                    self.root.after(0, self._show_test_result, server_name, False, "Connection timeout (10 seconds)")
                except Exception as e:
                    self.root.after(0, self._show_test_result, server_name, False, str(e))
                finally:
                    # 確実にクリーンアップを実行
                    try:
                        await test_manager.shutdown()
                    except Exception as cleanup_error:
                        # クリーンアップエラーはログに記録するが、UIには表示しない
                        logger.warning(f"Cleanup error for {server_name}: {cleanup_error}")
            except Exception as e:
                self.root.after(0, self._show_test_result, server_name, False, str(e))
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(test_connection())
            loop.close()
        except Exception as e:
            self.root.after(0, self._show_test_result, server_name, False, str(e))
            
    def _show_test_result(self, server_name, success, message):
        """テスト結果を表示"""
        self.test_button.configure(state="normal", text=self._("mcp_management.button.test_connection"))
        
        if success:
            self.status_label.configure(text=self._("mcp_management.status.test_success", server=server_name, message=message))
            messagebox.showinfo(
                self._("mcp_management.test_result.title"),
                self._("mcp_management.test_result.success", server=server_name, message=message),
                parent=self.root
            )
        else:
            self.status_label.configure(text=self._("mcp_management.status.test_failed", server=server_name, error=message))
            messagebox.showerror(
                self._("mcp_management.test_result.title"),
                self._("mcp_management.test_result.failed", server=server_name, error=message),
                parent=self.root
            )
            
    def test_all_servers(self):
        """全サーバーへの接続をテスト"""
        self.test_all_button.configure(state="disabled", text=self._("mcp_management.button.testing_all"))
        self.status_label.configure(text=self._("mcp_management.status.testing_all"))
        
        threading.Thread(target=self._test_all_servers_async, daemon=True).start()
        
    def _test_all_servers_async(self):
        """全サーバーの接続を非同期でテスト"""
        async def test_all_connections():
            try:
                mcp_settings = self.config.get_mcp_settings()
                servers = mcp_settings.get("servers", {})
                
                results = []
                for server_name, server_config in servers.items():
                    if not server_config.get("enabled", True):
                        results.append((server_name, False, "Disabled"))
                        continue
                        
                    test_manager = None
                    try:
                        test_manager = MCPClientManager(config_manager=self.config)
                        await asyncio.wait_for(
                            test_manager.connect_to_server(server_name, server_config),
                            timeout=10  # 10秒タイムアウト
                        )
                        tool_count = len(test_manager.available_tools)
                        results.append((server_name, True, f"{tool_count} tools"))
                    except asyncio.TimeoutError:
                        results.append((server_name, False, "Connection timeout"))
                    except Exception as e:
                        results.append((server_name, False, str(e)[:50]))
                    finally:
                        # 確実にクリーンアップを実行
                        if test_manager:
                            try:
                                await test_manager.shutdown()
                            except Exception as cleanup_error:
                                logger.warning(f"Cleanup error for {server_name}: {cleanup_error}")
                        
                self.root.after(0, self._show_all_test_results, results)
                
            except Exception as e:
                self.root.after(0, self._show_all_test_results, [("Error", False, str(e))])
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(test_all_connections())
            loop.close()
        except Exception as e:
            self.root.after(0, self._show_all_test_results, [("Error", False, str(e))])
            
    def _show_all_test_results(self, results):
        """全テスト結果を表示"""
        self.test_all_button.configure(state="normal", text=self._("mcp_management.button.test_all"))
        
        # 結果をダイアログで表示
        result_text = self._("mcp_management.test_all_results.header") + "\n\n"
        for server_name, success, message in results:
            status = "✓" if success else "✗"
            result_text += f"{status} {server_name}: {message}\n"
            
        messagebox.showinfo(
            self._("mcp_management.test_all_results.title"),
            result_text,
            parent=self.root
        )
        
        successful_count = sum(1 for _, success, _ in results if success)
        total_count = len(results)
        self.status_label.configure(
            text=self._("mcp_management.status.test_all_complete", successful=successful_count, total=total_count)
        )
        
    def refresh_servers(self):
        """サーバーリストを更新"""
        self.status_label.configure(text=self._("mcp_management.status.refreshing"))
        self.load_mcp_servers()
        self.status_label.configure(text=self._("mcp_management.status.refreshed"))
        
    def on_closing(self):
        """ウィンドウが閉じられる時の処理"""
        try:
            # MCPクライアントマネージャーのクリーンアップ
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.mcp_client_manager.shutdown())
            loop.close()
        except Exception as e:
            logger.error(f"Error during MCP management window cleanup: {e}")
        finally:
            self.root.destroy()


def main():
    customtkinter.set_appearance_mode("System")
    customtkinter.set_default_color_theme("blue")
    
    root = customtkinter.CTk()
    app = MCPManagementWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()