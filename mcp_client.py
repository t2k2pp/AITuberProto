import asyncio
import json
from pathlib import Path # Pathをインポート
from typing import Dict, Any, Optional, List, Tuple, Callable

# MCP SDK のインポート
try:
    from mcp.client.session import ClientSession
    from mcp.client.stdio import stdio_client, StdioServerParameters
    from mcp.types import Tool, Resource # MCP SDKが提供する型 (仮定、実際の型名に合わせる)
    # 例: from mcp.common.types import ToolDefinition, ResourceDefinition, ToolCallResult
    # 上記は仮なので、実際のSDKの型定義を探して使う
    # Tool, Resource, ToolCallResult はDict[str,Any]で一旦代用も可
    print("Successfully imported MCP SDK classes from 'mcp' package.")
    MCP_SDK_AVAILABLE = True
except ImportError as e_mcp:
    MCP_SDK_AVAILABLE = False
    # SDKがない場合は動作しないので、エラーを出すか、限定的なモックにする。
    # 今回は、SDKが必須であるという前提で進めるため、エラーをraiseしてもよいが、
    # 既存の動作を維持するため、一旦モックを残すが、いずれ削除する。
    print(f"CRITICAL: Failed to import MCP SDK from 'mcp' package ({e_mcp}). This integration will not work without the SDK.")

    # --- フォールバック用のモック (いずれ削除) ---
    class MockClientSession: # ClientSessionのモック
        def __init__(self, read_stream, write_stream, sampling_callback=None):
            self.name = "mock-session" # 仮
            logger.info(f"MockClientSession created for {self.name}")

        async def initialize(self):
            logger.info(f"MockClientSession {self.name}: Initialized.")
            await asyncio.sleep(0.01)

        async def list_tools(self) -> List[Dict[str, Any]]: # listTools -> list_tools, 戻り値もSDKに合わせる
            logger.info(f"MockClientSession {self.name}: list_tools called")
            # filesystemサーバーのモックの場合のみツールを返す
            if hasattr(self, '_server_name_for_mock') and self._server_name_for_mock == "filesystem":
                 return [{"name": "read_file", "description": "Reads a file (mock_session)"}]
            return []

        async def list_resources(self) -> List[Dict[str, Any]]:
            logger.info(f"MockClientSession {self.name}: list_resources called")
            return []

        async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
            logger.info(f"MockClientSession {self.name}: call_tool '{tool_name}' with args: {arguments}")
            if hasattr(self, '_server_name_for_mock') and self._server_name_for_mock == "filesystem" and \
               tool_name == "read_file" and "path" in arguments:
                return {"content": [{"type": "text", "text": f"Mock content of {arguments['path']} from MockClientSession"}]}
            return {"error": f"Mock tool '{tool_name}' failed or not found in MockClientSession"}

        async def close(self):
            logger.info(f"MockClientSession {self.name}: Closed.")
            await asyncio.sleep(0.01)

    # StdioServerParameters のモック (もし必要なら)
    class MockStdioServerParameters:
        def __init__(self, command: str, args: List[str], env: Optional[Dict[str, str]] = None):
            self.command = command
            self.args = args
            self.env = env if env is not None else {}

    # stdio_client のモック (非同期コンテキストマネージャ)
    class MockStdioClientContextManager:
        def __init__(self, params: MockStdioServerParameters):
            self._params = params
            logger.info(f"MockStdioClientContextManager initialized for command: {params.command}")

        async def __aenter__(self):
            logger.info("MockStdioClientContextManager: __aenter__ called. Simulating stream acquisition.")
            # ダミーのストリームを返す (実際には transport が持つべきもの)
            # ClientSessionのモックがストリームを直接使わないので、Noneでも良いかもしれない
            return (None, None) # (read_stream, write_stream)

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            logger.info("MockStdioClientContextManager: __aexit__ called. Simulating process termination.")

    if not MCP_SDK_AVAILABLE: # グローバル名をモックで上書き
        ClientSession = MockClientSession # type: ignore
        StdioServerParameters = MockStdioServerParameters # type: ignore
        stdio_client = MockStdioClientContextManager # type: ignore
        Tool = Dict[str, Any]
        Resource = Dict[str, Any]
        # ToolCallResult は call_tool の戻り値なので Dict[str, Any] でよい

# --- ここまでMCP SDKインポート & モック定義 ---

import logging
logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class MCPClientManager:
    def __init__(self, config_manager: Optional[Any] = None):
        self.sessions: Dict[str, ClientSession] = {} # Client -> ClientSession
        self.active_stdio_contexts: Dict[str, Any] = {} # 起動したstdio_clientのコンテキストを保持
        self.available_tools: Dict[str, Tool] = {}
        self.available_resources: Dict[str, Resource] = {}
        self.config_manager = config_manager

    async def connect_to_server(self, server_name: str, server_config: Dict[str, Any]) -> None:
        if server_name in self.sessions:
            logger.info(f"MCPサーバー \"{server_name}\" のセッションは既に確立済みです。")
            return

        if not MCP_SDK_AVAILABLE:
            logger.error("MCP SDK is not available. Cannot connect to server.")
            # モックを使う場合でも、モックのstdio_clientが非同期コンテキストマネージャを返すように修正したので、
            # 以下はSDKがある場合とほぼ同じロジックで進められるはず。
            # ただし、MockClientSessionに _server_name_for_mock を設定する必要がある。
            # この部分は、SDKが本当にない場合は機能しないことを明確にするため、returnしてもよい。
            # return # SDKがなければ接続処理を中断

        try:
            logger.info(f"MCPサーバー \"{server_name}\" への接続を開始します。設定: {server_config}")

            command = server_config.get("command")
            raw_args = server_config.get("args", [])
            env = server_config.get("env", {})

            processed_args = []
            if command == "python" and raw_args:
                script_path_arg = raw_args[0]
                try:
                    project_root = Path(__file__).resolve().parent # mcp_client.py がプロジェクトルート直下にある想定

                    # './' や '.\' で始まっている場合、それを除去 (os.path.normpathでも良いが、確実性のため)
                    if script_path_arg.startswith('./'):
                        script_path_arg = script_path_arg[2:]
                    elif script_path_arg.startswith('.\\'):
                        script_path_arg = script_path_arg[2:]

                    absolute_script_path = (project_root / script_path_arg).resolve() # resolve()で正規化と存在確認(シンボリックリンク等)

                    if absolute_script_path.is_file(): # resolve()後にis_file()で実ファイルか確認
                        processed_args.append(str(absolute_script_path))
                        processed_args.extend(raw_args[1:])
                        logger.info(f"Resolved server script path to: {absolute_script_path}")
                    else:
                        logger.warning(f"Server script path {script_path_arg} (resolved to {absolute_script_path}) does not exist or is not a file. Using raw args: {raw_args}")
                        processed_args = list(raw_args)
                except Exception as path_e:
                    logger.error(f"Error resolving server script path '{script_path_arg}': {path_e}. Using raw args: {raw_args}", exc_info=True)
                    processed_args = list(raw_args)
            else:
                processed_args = list(raw_args)

            if not command:
                raise ValueError(f"サーバー '{server_name}' の 'command' 設定がありません。")

            server_params = StdioServerParameters(command=command, args=processed_args, env=env)

            # stdio_client を非同期コンテキストマネージャとして使用
            # self.active_stdio_contexts にコンテキストを保存し、shutdownで解放する
            # stdio_client は関数なので、呼び出し結果がコンテキストマネージャになる
            stdio_cm = stdio_client(server_params)
            self.active_stdio_contexts[server_name] = stdio_cm # 後で __aexit__ するために保持
            read_stream, write_stream = await stdio_cm.__aenter__() # 手動でenter

            # ClientSession の作成と初期化
            # sampling_callback はLLMがクライアント側で動作する場合に使うもの。今回は不要。
            session = ClientSession(read_stream, write_stream)
            # SDKが利用可能な場合は、sessionがMockClientSessionであることはないので、以下の分岐は不要
            # if not MCP_SDK_AVAILABLE and isinstance(session, MockClientSession):
            #     session._server_name_for_mock = server_name


            await session.initialize() # MCPハンドシェイク

            await self._discover_server_capabilities(session, server_name)

            self.sessions[server_name] = session
            logger.info(f"MCPサーバー \"{server_name}\" とのセッションを正常に確立しました。")

        except Exception as e:
            logger.error(f"MCPサーバー \"{server_name}\" への接続エラー: {e}", exc_info=True)
            if server_name in self.active_stdio_contexts: # エラー発生時にもexitを試みる
                try:
                    await self.active_stdio_contexts[server_name].__aexit__(type(e), e, e.__traceback__)
                except Exception as e_exit:
                    logger.error(f"Error during __aexit__ for {server_name} after connection error: {e_exit}")
                del self.active_stdio_contexts[server_name]


    async def _discover_server_capabilities(self, session: ClientSession, server_name: str) -> None:
        try:
            tools_response = await session.list_tools() # listTools -> list_tools
            # tools_response の形式はSDKによる。List[Tool] を期待。
            # Tool 型もSDKで定義されているはず。ここでは Dict[str, Any] と仮定。
            if tools_response: # tools_response が None でないかつ空でないリストであることを確認
                for tool_data in tools_response: # list_tools() がリストを返すと仮定
                    # tool_data が辞書であることを期待 (Tool型が辞書的な場合)
                    if isinstance(tool_data, dict) and 'name' in tool_data:
                        tool_name = tool_data['name']
                        tool_id = f"{server_name}:{tool_name}"
                        self.available_tools[tool_id] = {
                            "serverName": server_name,
                            "name": tool_name, # 明示的にnameを再度格納
                            **tool_data # tool_data の他のキー (description, inputSchemaなど) も展開
                        }
                        logger.info(f"ツール発見: {tool_id} ({tool_data.get('description')})")
                    elif hasattr(tool_data, 'name'): # オブジェクトの場合
                        tool_name = tool_data.name
                        tool_id = f"{server_name}:{tool_name}"
                        # Toolオブジェクトをそのまま保存するか、辞書に変換するか検討
                        # ここでは辞書に変換する例
                        self.available_tools[tool_id] = {
                            "serverName": server_name,
                            "name": tool_name,
                            "description": getattr(tool_data, 'description', None),
                            "inputSchema": getattr(tool_data, 'inputSchema', None),
                             # 他の属性も同様に
                        }
                        logger.info(f"ツール発見: {tool_id} ({getattr(tool_data, 'description', '')})")

            else:
                logger.info(f"サーバー \"{server_name}\" からツール情報は提供されませんでした (空またはNone)。")

            # resources についても同様 (session.list_resources())
            resources_response = await session.list_resources()
            if resources_response:
                for res_data in resources_response:
                    if isinstance(res_data, dict) and 'uri' in res_data:
                        res_uri = res_data['uri']
                        res_id = f"{server_name}:{res_uri}"
                        self.available_resources[res_id] = {
                            "serverName": server_name,
                            "uri": res_uri,
                            **res_data
                        }
                        logger.info(f"リソース発見: {res_id} ({res_data.get('description')})")
                    elif hasattr(res_data, 'uri'):
                        res_uri = res_data.uri
                        res_id = f"{server_name}:{res_uri}"
                        self.available_resources[res_id] = {
                            "serverName": server_name,
                            "uri": res_uri,
                            "description": getattr(res_data, 'description', None),
                        }
                        logger.info(f"リソース発見: {res_id} ({getattr(res_data, 'description', '')})")
            else:
                logger.info(f"サーバー \"{server_name}\" からリソース情報は提供されませんでした (空またはNone)。")

        except Exception as e:
            logger.error(f"サーバー \"{server_name}\" の機能発見中にエラー: {e}", exc_info=True)

    async def execute_tool(self, tool_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        if tool_id not in self.available_tools:
            logger.error(f"ツール \"{tool_id}\" が見つかりません。利用可能なツール: {list(self.available_tools.keys())}")
            raise ValueError(f"ツール \"{tool_id}\" が見つかりません。")

        tool_info = self.available_tools[tool_id]
        server_name = tool_info["serverName"]
        original_tool_name = tool_info["name"] # サーバー側でのツール名

        session = self.sessions.get(server_name)
        if not session:
            logger.error(f"ツール \"{tool_id}\" のサーバー \"{server_name}\" のセッションが接続されていません。")
            raise ConnectionError(f"サーバー \"{server_name}\" のセッションが接続されていません。")

        try:
            logger.info(f"ツール \"{original_tool_name}\" (ID: {tool_id}) をパラメータ {parameters} で実行します。")
            # call_tool の引数は (tool_name: str, arguments: dict)
            result = await session.call_tool(tool_name=original_tool_name, arguments=parameters)
            # result の形式はSDKによる。mcp-integration-guide.md では {"content": ...} や {"error": ...} を想定。
            logger.info(f"ツール \"{tool_id}\" の実行結果 (RAW): {result}") # 生の結果をログに出力
            return self._process_tool_result(result)

        except Exception as e:
            logger.error(f"ツール \"{tool_id}\" の実行エラー: {e}", exc_info=True)
            raise RuntimeError(f"ツール \"{tool_id}\" の実行に失敗しました: {e}")

    def _process_tool_result(self, result: Any) -> Dict[str, Any]: # resultの型はSDKのcall_toolの戻り値による
        # SDKの call_tool が返すオブジェクトの構造に合わせて調整が必要
        # ガイドでは result.content や result.error を見ていた
        # ここでは、result が辞書であることを期待し、キー 'content' または 'error' を持つと仮定する
        # 実際のSDKでは、resultが特定のクラスインスタンスである可能性が高い

        if isinstance(result, dict):
            if "content" in result:
                # content が [{"type": "text", "text": "..."}] のようなリスト形式か、
                # 単純な文字列やオブジェクトか、SDK仕様による。
                # ガイドの FileSystemMCPServer は content: [{ type: 'text', text: content }] を返していた。
                # その場合、クライアント側でそれをどう受け取るか。
                # ここでは、ガイドのクライアント側 processToolResult に合わせる。
                content_data = result.get("content")
                # content_data がリストで、最初の要素が辞書で "text" キーを持つ場合、その値を取得
                processed_content = content_data
                if isinstance(content_data, list) and len(content_data) > 0 and \
                   isinstance(content_data[0], dict) and "text" in content_data[0]:
                    processed_content = content_data[0]["text"]

                return {
                    "success": True,
                    "data": processed_content, # もし TextContent オブジェクトなら .text などでアクセス
                    "metadata": result.get("metadata", {})
                }
            elif "error" in result:
                logger.error(f"ツール実行エラー (サーバーからのエラー): {result['error']}")
                return {
                    "success": False,
                    "error": str(result['error']),
                    "details": result.get("details")
                }

        # 上記に当てはまらない場合、result が直接的なデータか、あるいは未知の形式
        # もし result が TextContent のようなオブジェクトなら、その .text 属性などを取得する
        if hasattr(result, 'text') and isinstance(getattr(result, 'text'), str) : # 例: TextContent オブジェクト
             return {"success": True, "data": getattr(result, 'text')}
        if hasattr(result, 'result') : # 例: {"result": value} のようなプリミティブラッパー
             return {"success": True, "data": getattr(result, 'result')}


        logger.warning(f"予期しないツール結果形式、またはエラー情報なし: {result}")
        # そのまま返すか、エラーとして扱うか。
        # ここでは成功としてそのままデータを渡すが、より厳密なエラー処理が必要かもしれない。
        return {"success": True, "data": result}


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
                    await self.connect_to_server(server_name, server_settings)
                except Exception as e:
                    logger.error(f"サーバー \"{server_name}\" の初期化中にエラーが発生しました: {e}", exc_info=True)
            else:
                logger.info(f"サーバー \"{server_name}\" は無効化されているか、設定が不正です。スキップします。")

    async def shutdown(self) -> None:
        logger.info("全てのMCPクライアントセッションとプロセスをシャットダウンします...")
        for server_name, session in list(self.sessions.items()): # list()でコピーしてイテレート
            try:
                await session.close()
                logger.info(f"サーバー \"{server_name}\" とのセッションを正常にクローズしました。")
            except Exception as e:
                logger.error(f"サーバー \"{server_name}\" とのセッションクローズ中にエラー: {e}", exc_info=True)
            finally:
                del self.sessions[server_name]

        for server_name, stdio_cm_instance in list(self.active_stdio_contexts.items()):
            try:
                # 非同期コンテキストマネージャの __aexit__ を呼び出す
                await stdio_cm_instance.__aexit__(None, None, None)
                logger.info(f"サーバー \"{server_name}\" のstdioプロセスを正常に終了しました。")
            except Exception as e:
                logger.error(f"サーバー \"{server_name}\" のstdioプロセス終了中にエラー: {e}", exc_info=True)
            finally:
                del self.active_stdio_contexts[server_name]

        self.available_tools.clear()
        self.available_resources.clear()
        logger.info("MCPクライアントのシャットダウンが完了しました。")


# (main_test はSDKの具体的なAPIが判明してから書き直す必要があるため一旦コメントアウト)
# async def main_test():
#     # ...
#     pass

# if __name__ == "__main__":
#     # loop = asyncio.get_event_loop()
#     # try:
#     #     loop.run_until_complete(main_test())
#     # finally:
#     #     loop.close()
#     pass
