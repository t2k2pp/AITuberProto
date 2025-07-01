import asyncio
import json
import os
import subprocess # subprocess は shutdown でプロセスID確認のために残す可能性あり
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Callable

# MCP SDK のインポート
try:
    from mcp.client.session import ClientSession
    from mcp.client.stdio import stdio_client, StdioServerParameters
    from mcp.types import Tool as SDKTool, Resource as SDKResource # SDKが提供する型名に合わせる (仮)
    # ToolCallResult に相当する型もあればインポート
    print("Successfully imported MCP SDK classes from 'mcp' package.")
    MCP_SDK_AVAILABLE = True
except ImportError as e_mcp:
    MCP_SDK_AVAILABLE = False
    print(f"CRITICAL: Failed to import MCP SDK from 'mcp' package ({e_mcp}). MCP functionality will be severely limited or non-functional.")

    # SDKがない場合はフォールバック用のモックを定義 (限定的な動作)
    class MockClientSession:
        def __init__(self, read_stream, write_stream, sampling_callback=None, server_name_for_mock: Optional[str] = None):
            self.name = server_name_for_mock or "mock-session"
            self._server_name_for_mock = server_name_for_mock
            logger.info(f"MockClientSession created for {self.name}")
        async def initialize(self): logger.info(f"MockClientSession {self.name}: Initialized."); await asyncio.sleep(0.01)
        async def list_tools(self) -> List[Dict[str, Any]]:
            logger.info(f"MockClientSession {self.name}: list_tools called")
            if self._server_name_for_mock == "filesystem":
                 return [{"name": "read_file", "description": "Reads a file (mock_session)"}]
            return []
        async def list_resources(self) -> List[Dict[str, Any]]: return []
        async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
            logger.info(f"MockClientSession {self.name}: call_tool '{tool_name}' with args: {arguments}")
            if self._server_name_for_mock == "filesystem" and tool_name == "read_file" and "path" in arguments:
                return {"content": [{"type": "text", "text": f"Mock content of {arguments['path']} from MockClientSession"}]}
            return {"error": f"Mock tool '{tool_name}' failed or not found in MockClientSession"}
        async def close(self): logger.info(f"MockClientSession {self.name}: Closed."); await asyncio.sleep(0.01)

    class MockStdioServerParameters:
        def __init__(self, command: str, args: List[str], env: Optional[Dict[str, str]] = None):
            self.command = command; self.args = args; self.env = env or {}

    class MockStdioClientContextManager:
        def __init__(self, params: MockStdioServerParameters): self._params = params
        async def __aenter__(self): return (None, None) # read_stream, write_stream
        async def __aexit__(self, exc_type, exc_val, exc_tb): pass

    if not MCP_SDK_AVAILABLE: # グローバル名をモックで上書き
        ClientSession = MockClientSession # type: ignore
        StdioServerParameters = MockStdioServerParameters # type: ignore
        stdio_client = MockStdioClientContextManager # type: ignore
        SDKTool = Dict[str, Any] # type: ignore
        SDKResource = Dict[str, Any] # type: ignore

import logging
logger = logging.getLogger(__name__)

class MCPClientManager:
    def __init__(self, config_manager: Optional[Any] = None):
        self.sessions: Dict[str, ClientSession] = {}
        self.active_stdio_contexts: Dict[str, Any] = {} # stdio_client のコンテキストマネージャインスタンス
        self.available_tools: Dict[str, SDKTool] = {} # SDKのTool型を期待
        self.available_resources: Dict[str, SDKResource] = {} # SDKのResource型を期待
        self.config_manager = config_manager
        # self.server_processes は stdio_client が管理するので不要になる

    def _resolve_server_script_path(self, command: str, raw_args: List[str]) -> List[str]:
        # (このヘルパーメソッドは変更なし)
        processed_args = []
        if command == "python" and raw_args:
            script_path_arg = raw_args[0]
            try:
                project_root = Path(__file__).resolve().parent
                if script_path_arg.startswith('./'): script_path_arg = script_path_arg[2:]
                elif script_path_arg.startswith('.\\'): script_path_arg = script_path_arg[2:]
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
        if server_name in self.sessions:
            logger.info(f"MCPサーバー \"{server_name}\" のセッションは既に確立済みか試行中です。")
            return

        if not MCP_SDK_AVAILABLE: # SDKがなければ何もしない（またはエラー）
            logger.critical("MCP SDK is not available. Cannot establish ClientSession.")
            return

        try:
            command = server_config.get("command")
            raw_args = server_config.get("args", [])
            env_config = server_config.get("env", {}).copy()

            processed_args = self._resolve_server_script_path(command, raw_args)

            if not command or not processed_args:
                raise ValueError(f"サーバー '{server_name}' のコマンドまたは引数が正しく設定されていません。")

            effective_env = os.environ.copy()
            effective_env.update(env_config)
            effective_env["PYTHONUNBUFFERED"] = "1"

            project_root_str = str(Path(__file__).resolve().parent)
            existing_pythonpath = effective_env.get("PYTHONPATH", "")
            if project_root_str not in existing_pythonpath.split(os.pathsep):
                effective_env["PYTHONPATH"] = f"{project_root_str}{os.pathsep}{existing_pythonpath}".strip(os.pathsep)

            logger.info(f"Attempting to connect to server '{server_name}' using stdio_client:")
            logger.info(f"  Command: {command}, Args: {processed_args}")
            logger.info(f"  Env (selected): PYTHONUNBUFFERED={effective_env.get('PYTHONUNBUFFERED')}, PYTHONPATH={effective_env.get('PYTHONPATH')}")

            server_params = StdioServerParameters(command=command, args=processed_args, env=effective_env)

            stdio_cm = stdio_client(server_params)
            self.active_stdio_contexts[server_name] = stdio_cm # __aexit__ のために保持
            read_stream, write_stream = await stdio_cm.__aenter__()

            session = ClientSession(read_stream, write_stream)
            # モックの場合の特別処理はMCP_SDK_AVAILABLEがFalseのブロックに任せる
            # if not MCP_SDK_AVAILABLE and isinstance(session, MockClientSession):
            #     session._server_name_for_mock = server_name

            await session.initialize()
            await self._discover_server_capabilities(session, server_name)

            self.sessions[server_name] = session
            logger.info(f"MCPサーバー \"{server_name}\" とのセッションを正常に確立しました。")

        except Exception as e:
            logger.error(f"MCPサーバー \"{server_name}\" への接続エラー: {e}", exc_info=True)
            if server_name in self.active_stdio_contexts:
                try:
                    await self.active_stdio_contexts[server_name].__aexit__(type(e), e, e.__traceback__)
                except Exception as e_exit:
                    logger.error(f"Error during __aexit__ for {server_name} after connection error: {e_exit}")
                del self.active_stdio_contexts[server_name]


    async def _discover_server_capabilities(self, session: ClientSession, server_name: str) -> None:
        try:
            tools_list: List[SDKTool] = await session.list_tools() # SDKのTool型を期待
            logger.info(f"Raw tools_response from server '{server_name}': {tools_list}")
            if tools_list:
                for tool_obj in tools_list:
                    # SDKToolがどのような属性を持つか (name, description, inputSchemaなど) はSDK仕様による
                    # ここでは tool_obj が .name, .description 属性を持つと仮定
                    if hasattr(tool_obj, 'name'):
                        tool_id = f"{server_name}:{tool_obj.name}"
                        self.available_tools[tool_id] = tool_obj # Toolオブジェクトをそのまま保存
                        logger.info(f"ツール発見: {tool_id} (Description: {getattr(tool_obj, 'description', 'N/A')})")
                    else:
                        logger.warning(f"Received tool object without a 'name' attribute: {tool_obj}")
            else:
                logger.info(f"サーバー \"{server_name}\" からツール情報は提供されませんでした (空またはNone)。")

            resources_list: List[SDKResource] = await session.list_resources()
            logger.info(f"Raw resources_response from server '{server_name}': {resources_list}")
            if resources_list:
                for res_obj in resources_list:
                    if hasattr(res_obj, 'uri'):
                        res_id = f"{server_name}:{res_obj.uri}"
                        self.available_resources[res_id] = res_obj
                        logger.info(f"リソース発見: {res_id} (Description: {getattr(res_obj, 'description', 'N/A')})")
                    else:
                        logger.warning(f"Received resource object without a 'uri' attribute: {res_obj}")
            else:
                logger.info(f"サーバー \"{server_name}\" からリソース情報は提供されませんでした (空またはNone)。")

        except Exception as e:
            logger.error(f"サーバー \"{server_name}\" の機能発見中にエラー: {e}", exc_info=True)

    async def execute_tool(self, tool_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        if tool_id not in self.available_tools:
            logger.error(f"ツール \"{tool_id}\" が見つかりません。利用可能なツール: {list(self.available_tools.keys())}")
            # 利用可能なツールの詳細もログに出す
            for tid, t_obj in self.available_tools.items():
                logger.debug(f"Available tool detail: ID={tid}, Name={getattr(t_obj, 'name', 'N/A')}")
            raise ValueError(f"ツール \"{tool_id}\" が見つかりません。")

        tool_obj = self.available_tools[tool_id]
        server_name = tool_id.split(":", 1)[0] # tool_id からサーバー名を取得 (より堅牢な方法も検討可)
        original_tool_name = getattr(tool_obj, 'name', None)

        if not original_tool_name:
             raise ValueError(f"ツールオブジェクト '{tool_id}' にname属性がありません。")

        session = self.sessions.get(server_name)
        if not session:
            raise ConnectionError(f"サーバー \"{server_name}\" のセッションが接続されていません。")

        try:
            logger.info(f"ツール \"{original_tool_name}\" (ID: {tool_id}) をパラメータ {parameters} で実行します。")
            result = await session.call_tool(tool_name=original_tool_name, arguments=parameters)
            logger.info(f"ツール \"{tool_id}\" の実行結果 (RAW from SDK): {result}")
            return self._process_tool_result(result)
        except Exception as e:
            logger.error(f"ツール \"{tool_id}\" の実行エラー: {e}", exc_info=True)
            raise RuntimeError(f"ツール \"{tool_id}\" の実行に失敗しました: {e}")

    def _process_tool_result(self, result: Any) -> Dict[str, Any]:
        # result は session.call_tool() の戻り値。SDKの型を想定。
        # GitHub README "Writing MCP Clients" -> "Call a tool" の例では result の型は不明。
        # mcp-integration-guide.md (JS SDK) では result.content や result.error を想定。
        # FastMCPサーバーのツールが返す型 (例: ReadFileToolOutput) がどうラップされてくるか。
        # ReadFileToolOutput は {"content": [{"type": "text", "text": "..."}]}

        # 最も可能性が高いのは、result がこの辞書そのもの、あるいはそれに近い属性を持つオブジェクト。
        if hasattr(result, 'content'): # ガイドのJS SDKに近いケース
            content_data = result.content
        elif isinstance(result, dict) and 'content' in result: # Python dictの場合
            content_data = result['content']
        elif hasattr(result, 'result') and isinstance(result.result, str): # プリミティブラッパーの可能性
             return {"success": True, "data": result.result}
        elif isinstance(result, str): # 単純な文字列が返ってきた場合
             return {"success": True, "data": result}
        else: # 不明な形式、またはエラー
            if hasattr(result, 'error'):
                error_msg = str(result.error)
            elif isinstance(result, dict) and 'error' in result:
                error_msg = str(result['error'])
            else:
                logger.warning(f"ツール結果の解釈に失敗。未知の形式またはエラー情報なし: {result}")
                # エラーとして扱うのが安全か
                return {"success": False, "error": f"未知のツール結果形式: {str(result)[:100]}"}

            logger.error(f"ツール実行エラー (サーバーからのエラー): {error_msg}")
            return {"success": False, "error": error_msg, "details": str(result)}

        # content_data の処理 (mcp-integration-guide.md のクライアント側処理に準拠)
        processed_content = content_data
        if isinstance(content_data, list) and len(content_data) > 0 and \
           isinstance(content_data[0], dict) and "text" in content_data[0]:
            processed_content = content_data[0]["text"]
        elif isinstance(content_data, dict) and "text" in content_data and content_data.get("type") == "text": # TextContentオブジェクトのような辞書の場合
            processed_content = content_data["text"]
        # TextContent_SDK オブジェクトの場合 (もしSDKがオブジェクトを直接返すなら)
        # elif MCP_SDK_AVAILABLE and TextContent_SDK and isinstance(content_data, TextContent_SDK):
        #    processed_content = content_data.text

        return {
            "success": True,
            "data": processed_content,
            "metadata": getattr(result, 'metadata', {}) if hasattr(result, 'metadata') else (result.get("metadata", {}) if isinstance(result, dict) else {})
        }

    async def initialize_servers_from_config(self) -> None:
        # (このメソッドは変更なし)
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
                    await self.connect_to_server(server_name, server_settings)
                except Exception as e:
                    logger.error(f"サーバー \"{server_name}\" の初期化(connect_to_server呼び出し)中にエラー: {e}", exc_info=True)
            else:
                logger.info(f"サーバー \"{server_name}\" は無効化されているか、設定が不正です。スキップします。")

    async def shutdown(self) -> None:
        logger.info("全てのMCPクライアントセッションと関連プロセスをシャットダウンします...")
        for server_name, session in list(self.sessions.items()):
            try:
                await session.close()
                logger.info(f"サーバー \"{server_name}\" とのセッションを正常にクローズしました。")
            except Exception as e:
                logger.error(f"サーバー \"{server_name}\" とのセッションクローズ中にエラー: {e}", exc_info=True)
            # ClientSession.close() が transport/process の終了も管理することを期待
            # そうでない場合は、active_stdio_contexts から対応する context を見つけて __aexit__ する必要がある
            if server_name in self.active_stdio_contexts:
                 logger.info(f"stdio_client context for {server_name} should be exited by session.close().")
                 # await self.active_stdio_contexts[server_name].__aexit__(None, None, None)
                 # del self.active_stdio_contexts[server_name] # __aexit__が呼ばれたら削除
            del self.sessions[server_name]

        # もし session.close() で context が終了しない場合に備えて残りの context も処理
        for server_name, stdio_cm_instance in list(self.active_stdio_contexts.items()):
            logger.warning(f"stdio_client context for {server_name} was not cleaned up by session.close(). Attempting explicit __aexit__.")
            try:
                await stdio_cm_instance.__aexit__(None, None, None)
                logger.info(f"サーバー \"{server_name}\" のstdioプロセスコンテキストを正常に終了しました。")
            except Exception as e:
                logger.error(f"サーバー \"{server_name}\" のstdioプロセスコンテキスト終了中にエラー: {e}", exc_info=True)
            finally:
                del self.active_stdio_contexts[server_name]

        self.available_tools.clear()
        self.available_resources.clear()
        logger.info("MCPクライアントのシャットダウンが完了しました。")

# (main_test はコメントアウトのまま)
