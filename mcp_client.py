import asyncio
import json
import subprocess # subprocess をインポート
import os # os をインポート
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Callable

# MCP SDK のインポート (ClientSessionなどはsubprocess直接利用時は使わないが、型ヒント用に残す場合もある)
try:
    from mcp.client.session import ClientSession # 今回のテストでは直接は使わない
    from mcp.client.stdio import StdioServerParameters # 設定読み込みには使う
    # from mcp.types import Tool, Resource # 必要なら
    print("Successfully imported MCP SDK classes from 'mcp' package (for type hints or parameters).")
    MCP_SDK_AVAILABLE = True
except ImportError as e_mcp:
    MCP_SDK_AVAILABLE = False
    print(f"Warning: Failed to import MCP SDK from 'mcp' package ({e_mcp}). Subprocess test will proceed, but full functionality requires SDK.")
    # モック定義は subprocess テスト中は不要なので削除またはコメントアウト
    # class ClientSession: pass
    class StdioServerParameters: # type: ignore
        def __init__(self, command: str, args: List[str], env: Optional[Dict[str, str]] = None):
            self.command = command
            self.args = args
            self.env = env if env is not None else {}
    # Tool = Dict[str, Any]
    # Resource = Dict[str, Any]


import logging
logger = logging.getLogger(__name__)

class MCPClientManager:
    def __init__(self, config_manager: Optional[Any] = None):
        # self.sessions: Dict[str, ClientSession] = {} # subprocess直接利用時はClientSessionはまだ作らない
        self.server_processes: Dict[str, subprocess.Popen] = {} # 起動したサブプロセスを保持
        self.available_tools: Dict[str, Any] = {} # Anyの代わりにTool型を使いたい
        self.available_resources: Dict[str, Any] = {} # Anyの代わりにResource型を使いたい
        self.config_manager = config_manager

    def _resolve_server_script_path(self, command: str, raw_args: List[str]) -> List[str]:
        processed_args = []
        if command == "python" and raw_args:
            script_path_arg = raw_args[0]
            try:
                project_root = Path(__file__).resolve().parent
                if script_path_arg.startswith('./'):
                    script_path_arg = script_path_arg[2:]
                elif script_path_arg.startswith('.\\'):
                    script_path_arg = script_path_arg[2:]
                absolute_script_path = (project_root / script_path_arg).resolve()
                if absolute_script_path.is_file():
                    processed_args.append(str(absolute_script_path))
                    processed_args.extend(raw_args[1:])
                    logger.info(f"Resolved server script path to: {absolute_script_path}")
                else:
                    logger.warning(f"Server script path '{script_path_arg}' (resolved to '{absolute_script_path}') does not exist or is not a file. Using raw args: {raw_args}")
                    processed_args = list(raw_args)
            except Exception as path_e:
                logger.error(f"Error resolving server script path '{script_path_arg}': {path_e}. Using raw args: {raw_args}", exc_info=True)
                processed_args = list(raw_args)
        else:
            processed_args = list(raw_args)
        return processed_args

    async def connect_to_server(self, server_name: str, server_config: Dict[str, Any]) -> None:
        if server_name in self.server_processes and self.server_processes[server_name].poll() is None:
            logger.info(f"MCPサーバー \"{server_name}\" のプロセスは既に起動済みか、起動試行中です。")
            return

        try:
            command = server_config.get("command")
            raw_args = server_config.get("args", [])
            env_config = server_config.get("env", {}).copy()

            processed_args = self._resolve_server_script_path(command, raw_args)

            if not command or not processed_args:
                raise ValueError(f"サーバー '{server_name}' のコマンドまたは引数が正しく設定されていません。")

            env_for_subprocess = os.environ.copy() # 現在の環境変数を引き継ぐ
            env_for_subprocess.update(env_config) # 設定ファイルからの環境変数を上書き/追加
            env_for_subprocess["PYTHONUNBUFFERED"] = "1" # バッファリング無効を強制

            # PYTHONPATHにカレントディレクトリ（プロジェクトルート想定）を追加してみる
            # これにより、サブプロセスがモジュールを見つけやすくなるかもしれない
            project_root_str = str(Path(__file__).resolve().parent)
            existing_pythonpath = env_for_subprocess.get("PYTHONPATH", "")
            if project_root_str not in existing_pythonpath.split(os.pathsep):
                env_for_subprocess["PYTHONPATH"] = f"{project_root_str}{os.pathsep}{existing_pythonpath}".strip(os.pathsep)
            logger.info(f"Effective PYTHONPATH for subprocess: {env_for_subprocess.get('PYTHONPATH')}")


            logger.info(f"Attempting to launch server '{server_name}' via subprocess.Popen:")
            logger.info(f"  Command: {command}")
            logger.info(f"  Args: {processed_args}")
            # Popenのcwdは、スクリプトパスが絶対パスなら不要かもしれないが、念のため設定
            # スクリプトが自身の位置からの相対パスで何かを読み込む場合に影響する
            script_dir = Path(processed_args[0]).parent if processed_args else Path(__file__).resolve().parent
            logger.info(f"  CWD (for Popen): {script_dir}")
            logger.info(f"  Env (selected items for log): PYTHONUNBUFFERED={env_for_subprocess.get('PYTHONUNBUFFERED')}, PYTHONPATH={env_for_subprocess.get('PYTHONPATH')}")


            # subprocess.PIPE を使うと、communicate() で待つか、非同期で読み出す必要がある
            # 今回はダミースクリプトがファイルにログを出すので、stdout/stderrはキャプチャせずOSデフォルトへ
            process = subprocess.Popen(
                [command] + processed_args,
                text=True,
                encoding='utf-8',
                env=env_for_subprocess,
                cwd=script_dir, # スクリプトがあるディレクトリをCWDに
                # stdin=subprocess.DEVNULL, # stdinは使わないので閉じておく (stdio_clientは接続する)
                # stdout=subprocess.PIPE, # デバッグ用にキャプチャする場合
                # stderr=subprocess.PIPE  # デバッグ用にキャプチャする場合
            )
            self.server_processes[server_name] = process

            logger.info(f"Subprocess for '{server_name}' launched with PID: {process.pid}. Waiting a few seconds for it to initialize and create log files...")
            await asyncio.sleep(5) # 5秒待機

            logger.info(f"Subprocess test for '{server_name}' finished waiting. Please check for 'logs/dummy_server_startup.log' and 'logs/dummy_server_flag.txt'.")

            retcode = process.poll()
            if retcode is not None:
                logger.warning(f"Subprocess for '{server_name}' exited early with code: {retcode}")
                # もしstdout/stderrをPIPEにしていればここで読み出せる
                # stdout_data, stderr_data = process.communicate(timeout=1)
                # logger.info(f"Subprocess stdout: {stdout_data}")
                # logger.error(f"Subprocess stderr: {stderr_data}")
            else:
                logger.info(f"Subprocess for '{server_name}' is still running.")

        except Exception as e:
            logger.error(f"Error launching or interacting with subprocess for server '{server_name}': {e}", exc_info=True)

    async def _discover_server_capabilities(self, session: Any, server_name: str) -> None: # sessionの型をAnyに
        # このテスト中は呼び出されない想定
        logger.info("_discover_server_capabilities called, but not functional in subprocess test mode.")
        pass

    async def execute_tool(self, tool_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        # このテスト中は呼び出されない想定
        logger.info(f"execute_tool '{tool_id}' called, but not functional in subprocess test mode.")
        return {"success": False, "error": "Not functional in subprocess test mode"}

    def _process_tool_result(self, result: Any) -> Dict[str, Any]:
        # このテスト中は呼び出されない想定
        return {}

    async def initialize_servers_from_config(self) -> None:
        if not self.config_manager:
            logger.warning("ConfigManagerが設定されていません。MCPサーバーの初期化をスキップします。")
            return
        mcp_config = self.config_manager.get_mcp_settings()
        if not mcp_config or "servers" not in mcp_config:
            logger.info("MCPサーバーの設定が見つかりません。")
            return
        for server_name, server_settings in mcp_config["servers"].items():
            if isinstance(server_settings, dict) and server_settings.get("enabled", True):
                try:
                    # connect_to_server は非同期なので create_task で並行実行も可能だが、
                    # ここでは順次実行（デバッグしやすいため）
                    await self.connect_to_server(server_name, server_settings)
                except Exception as e:
                    logger.error(f"サーバー \"{server_name}\" の初期化(connect_to_server呼び出し)中にエラー: {e}", exc_info=True)
            else:
                logger.info(f"サーバー \"{server_name}\" は無効化されているか、設定が不正です。スキップします。")

    async def shutdown(self) -> None:
        logger.info("全てのMCPサーバープロセスをシャットダウンします...")
        for server_name, process in list(self.server_processes.items()):
            if process.poll() is None: # プロセスがまだ実行中なら
                logger.info(f"Terminating server process '{server_name}' (PID: {process.pid})...")
                process.terminate() # SIGTERM を送信
                try:
                    process.wait(timeout=5) # 最大5秒待つ
                    logger.info(f"Server process '{server_name}' terminated with code {process.returncode}.")
                except subprocess.TimeoutExpired:
                    logger.warning(f"Server process '{server_name}' did not terminate in time, killing...")
                    process.kill() # 強制終了
                    logger.info(f"Server process '{server_name}' killed.")
                except Exception as e:
                    logger.error(f"Error during server process '{server_name}' shutdown: {e}", exc_info=True)
            else:
                logger.info(f"Server process '{server_name}' already exited with code {process.returncode}.")
            del self.server_processes[server_name]

        self.available_tools.clear()
        self.available_resources.clear()
        logger.info("MCPクライアントのシャットダウンが完了しました。")

# (main_test はSDKの具体的なAPIが判明してから書き直す必要があるため一旦コメントアウト)
