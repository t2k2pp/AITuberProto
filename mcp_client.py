import asyncio
from typing import Dict, Any, Optional, List, Tuple, Callable # 型ヒントのために追加

# MCP SDK のインポート (mcp-integration-guide.md に基づく仮定)
# 実際のSDKの構造に合わせて調整が必要
try:
    from modelcontextprotocol.sdk.client import Client, ClientOptions, ClientTransport
    from modelcontextprotocol.sdk.client.stdio import StdioClientTransport
    # MCP SDK の型定義 (存在する場合)
    # from modelcontextprotocol.sdk.types import Tool, Resource, ToolCallResult, Error
except ImportError:
    # モックオブジェクトで代替 (SDKが利用できない環境での開発用)
    print("Warning: MCP SDK not found. Using mock objects.")

    class MockClient:
        def __init__(self, options: Dict[str, Any], client_options: Dict[str, Any]):
            self.name = options.get("name")
            self.version = options.get("version")
            self.capabilities = client_options.get("capabilities")
            self.transport = None
            print(f"MockClient created: {self.name} v{self.version}")

        async def connect(self, transport: Any):
            self.transport = transport
            print(f"MockClient {self.name}: Connected via {type(transport).__name__}")
            # 接続成功をシミュレート
            await asyncio.sleep(0.1)

        async def listTools(self) -> Dict[str, List[Dict[str, Any]]]:
            print(f"MockClient {self.name}: listTools called")
            # ダミーのツール情報を返す
            # サーバー名がfilesystemサーバーのモックであるかで判断
            if self.name == "chat-app-filesystem":
                 return {"tools": [{"name": "read_file", "description": "Reads a file from filesystem server"}]}
            return {"tools": []}


        async def listResources(self) -> Dict[str, List[Dict[str, Any]]]:
            print(f"MockClient {self.name}: listResources called")
            return {"resources": []}

        async def callTool(self, tool_call_params: Dict[str, Any]) -> Dict[str, Any]:
            tool_name = tool_call_params.get("name")
            args = tool_call_params.get("arguments")
            print(f"MockClient {self.name}: callTool '{tool_name}' with args: {args}")
            if tool_name == "read_file" and args and "path" in args:
                return {"content": f"Mock content of {args['path']}"}
            return {"error": f"Mock tool '{tool_name}' failed or not found"}

        async def disconnect(self):
            print(f"MockClient {self.name}: Disconnected")
            await asyncio.sleep(0.1)


    class MockStdioClientTransport:
        def __init__(self, config: Dict[str, Any]):
            self.command = config.get("command")
            self.args = config.get("args")
            self.env = config.get("env")
            print(f"MockStdioClientTransport created for: {self.command} {' '.join(self.args or [])}")

    Client = MockClient
    StdioClientTransport = MockStdioClientTransport
    Tool = Dict[str, Any]
    Resource = Dict[str, Any]
    ToolCallResult = Dict[str, Any]


# ロギング設定 (必要に応じて調整)
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class MCPClientManager:
    def __init__(self, config_manager: Optional[Any] = None): # config_manager を受け取る
        self.clients: Dict[str, Client] = {}
        self.available_tools: Dict[str, Tool] = {}
        self.available_resources: Dict[str, Resource] = {}
        self.config_manager = config_manager # ConfigManagerのインスタンスを保持

    async def connect_to_server(self, server_name: str, server_config: Dict[str, Any]) -> None:
        """MCPサーバーへの接続を確立する"""
        if server_name in self.clients:
            logger.info(f"MCPサーバー \"{server_name}\" には既に接続済みです。")
            return

        try:
            logger.info(f"MCPサーバー \"{server_name}\" への接続を開始します。設定: {server_config}")
            # トランスポート層の設定（サーバーとの通信方法）
            # StdioClientTransport の設定が mcp-integration-guide.md と SDK の間で異なる可能性あり
            # command はリスト形式 ["command", "arg1", "arg2"] の場合と、
            # command="command", args=["arg1", "arg2"] の場合がある。SDK仕様に合わせる。
            # ここではガイドの形式に合わせる
            transport_command = server_config.get("command")
            transport_args = server_config.get("args", [])
            transport_env = server_config.get("env", {})

            if not transport_command:
                raise ValueError(f"サーバー '{server_name}' の 'command' 設定がありません。")

            transport_config = {
                "command": transport_command,
                "args": transport_args,
                "env": transport_env
            }
            transport = StdioClientTransport(transport_config) # type: ignore


            # クライアントインスタンスの作成
            # SDK の Client コンストラクタの引数を確認する
            client = Client({ # type: ignore
                "name": f"chat-app-{server_name}", # type: ignore
                "version": "1.0.0" # type: ignore
            }, { # type: ignore
                "capabilities": { # type: ignore
                    "tools": {},  # ツール使用の許可 (空のオブジェクトは全てのツールを意味する場合がある)
                    "resources": {} # リソースアクセスの許可
                }
            })

            # 接続の開始
            await client.connect(transport) # type: ignore

            # サーバーの能力を取得
            await self._discover_server_capabilities(client, server_name) # type: ignore

            self.clients[server_name] = client # type: ignore
            logger.info(f"MCPサーバー \"{server_name}\" に正常に接続しました。")

        except Exception as e:
            logger.error(f"MCPサーバー \"{server_name}\" への接続エラー: {e}")
            # ここでエラーを再raiseするか、エラー情報を保持して後で処理するか検討
            # raise

    async def _discover_server_capabilities(self, client: Client, server_name: str) -> None:
        """サーバーが提供する機能（ツールやリソース）を発見する"""
        try:
            # 利用可能なツールを取得
            tools_response = await client.listTools() # type: ignore
            if tools_response and tools_response.get("tools"): # type: ignore
                for tool in tools_response["tools"]: # type: ignore
                    tool_id = f"{server_name}:{tool['name']}" # type: ignore
                    self.available_tools[tool_id] = { # type: ignore
                        "serverName": server_name,
                        **tool # type: ignore
                    }
                    logger.info(f"ツール発見: {tool_id} ({tool.get('description')})") # type: ignore
            else:
                logger.info(f"サーバー \"{server_name}\" からツール情報は提供されませんでした。")


            # 利用可能なリソースを取得 (同様に実装)
            resources_response = await client.listResources() # type: ignore
            if resources_response and resources_response.get("resources"): # type: ignore
                for resource in resources_response["resources"]: # type: ignore
                    resource_id = f"{server_name}:{resource['uri']}" # type: ignore
                    self.available_resources[resource_id] = { # type: ignore
                        "serverName": server_name,
                        **resource # type: ignore
                    }
                    logger.info(f"リソース発見: {resource_id} ({resource.get('description')})") # type: ignore
            else:
                logger.info(f"サーバー \"{server_name}\" からリソース情報は提供されませんでした。")

        except Exception as e:
            logger.error(f"サーバー \"{server_name}\" の機能発見中にエラー: {e}")
            # 必要に応じてエラー処理

    async def execute_tool(self, tool_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """指定されたツールを実行する"""
        if tool_id not in self.available_tools:
            logger.error(f"ツール \"{tool_id}\" が見つかりません。利用可能なツール: {list(self.available_tools.keys())}")
            raise ValueError(f"ツール \"{tool_id}\" が見つかりません。")

        tool_info = self.available_tools[tool_id]
        server_name = tool_info["serverName"] # type: ignore

        client = self.clients.get(server_name)
        if not client:
            logger.error(f"ツール \"{tool_id}\" のサーバー \"{server_name}\" が接続されていません。")
            raise ConnectionError(f"サーバー \"{server_name}\" が接続されていません。")

        try:
            logger.info(f"ツール \"{tool_id}\" をパラメータ {parameters} で実行します。")
            # SDKの callTool の引数を確認
            result: ToolCallResult = await client.callTool({ # type: ignore
                "name": tool_info["name"], # type: ignore
                "arguments": parameters
            })
            logger.info(f"ツール \"{tool_id}\" の実行結果: {result}")
            return self._process_tool_result(result)

        except Exception as e:
            logger.error(f"ツール \"{tool_id}\" の実行エラー: {e}")
            # エラーをラップして再raiseするか、エラー情報を返す
            raise RuntimeError(f"ツール \"{tool_id}\" の実行に失敗しました: {e}")

    def _process_tool_result(self, result: ToolCallResult) -> Dict[str, Any]:
        """ツール実行結果を標準化された形式で処理する"""
        # ガイドの形式に合わせる
        if result and isinstance(result, dict):
            if "content" in result: # type: ignore
                # content がリストの場合、中身の型を確認する
                # ガイドでは content: [{ type: 'text', text: content }] のような形式
                # SDK の実際の返り値に合わせる
                content_data = result.get("content") # type: ignore
                processed_content = content_data
                if isinstance(content_data, list) and len(content_data) > 0 and isinstance(content_data[0], dict) and "text" in content_data[0]:
                    processed_content = content_data[0]["text"] # シンプルなテキストを返す例

                return {
                    "success": True,
                    "data": processed_content,
                    "metadata": result.get("metadata", {}) # type: ignore
                }
            elif "error" in result: # type: ignore
                logger.error(f"ツール実行エラー (サーバーからのエラー): {result['error']}") # type: ignore
                # raise ValueError(f"ツール実行エラー: {result['error']}") # type: ignore
                return {
                    "success": False,
                    "error": str(result['error']), # type: ignore
                    "details": result.get("details") # type: ignore
                }
        # 不明な形式の場合
        logger.warning(f"予期しないツール結果形式: {result}")
        return {"success": True, "data": result} # そのまま返すか、エラーとするか

    async def initialize_servers_from_config(self) -> None:
        """設定ファイルからMCPサーバー情報を読み込み、接続を試みる"""
        if not self.config_manager:
            logger.warning("ConfigManagerが設定されていません。MCPサーバーの初期化をスキップします。")
            return

        # config_manager からMCPサーバー設定を取得する (このメソッドはConfigManagerに後で追加)
        mcp_config = self.config_manager.get_mcp_settings() # 仮のメソッド
        if not mcp_config or "servers" not in mcp_config:
            logger.info("MCPサーバーの設定が見つかりません。")
            return

        for server_name, server_settings in mcp_config["servers"].items():
            if isinstance(server_settings, dict) and server_settings.get("enabled", True): # 有効なサーバーのみ接続
                try:
                    await self.connect_to_server(server_name, server_settings)
                except Exception as e:
                    logger.error(f"サーバー \"{server_name}\" の初期化中にエラーが発生しました: {e}")
            else:
                logger.info(f"サーバー \"{server_name}\" は無効化されているか、設定が不正です。スキップします。")

    async def shutdown(self) -> None:
        """全てのMCPサーバー接続を閉じる"""
        logger.info("全てのMCPクライアント接続をシャットダウンします...")
        for server_name, client in self.clients.items():
            try:
                await client.disconnect() # type: ignore
                logger.info(f"サーバー \"{server_name}\" との接続を正常に切断しました。")
            except Exception as e:
                logger.error(f"サーバー \"{server_name}\" との切断中にエラー: {e}")
        self.clients.clear()
        self.available_tools.clear()
        self.available_resources.clear()
        logger.info("MCPクライアントのシャットダウンが完了しました。")


# 簡単なテスト用 (非同期実行のため)
async def main_test():
    # ダミーのConfigManagerの代わり
    class MockConfigManager:
        def get_mcp_settings(self):
            return {
                "servers": {
                    "filesystem": {
                        "enabled": True,
                        "command": "python", # 実行するコマンド (例: python)
                        "args": ["./mcp_servers/file_system_server.py"], # サーバープログラムのパス
                        "env": {"PYTHONUNBUFFERED": "1"} # 環境変数 (例)
                    },
                    "another_server": {
                        "enabled": False, # このサーバーは接続されない
                        "command": "echo",
                        "args": ["hello from another_server"]
                    }
                }
            }

    manager = MCPClientManager(config_manager=MockConfigManager()) # type: ignore

    # サーバー初期化 (実際にはアプリケーションの起動時に行う)
    # このテストでは、file_system_server.py が存在し、実行可能である必要がある
    # 実際のSDKがないため、MockStdioClientTransport が使われる
    await manager.initialize_servers_from_config()

    if "filesystem" in manager.clients:
        print("\nファイルシステムサーバーへの接続成功 (モック)")
        # 利用可能なツール一覧表示
        print("利用可能なツール:")
        for tool_id, tool_info in manager.available_tools.items():
            print(f"  - {tool_id}: {tool_info.get('description')}") # type: ignore

        # ツール実行テスト (read_file があれば)
        if "filesystem:read_file" in manager.available_tools:
            try:
                print("\n'filesystem:read_file' ツールを実行します...")
                result = await manager.execute_tool("filesystem:read_file", {"path": "/example/file.txt"})
                print(f"ツール実行結果: {result}")
            except Exception as e:
                print(f"ツール実行エラー: {e}")
        else:
            print("\n'filesystem:read_file' ツールが見つかりません。")
    else:
        print("\nファイルシステムサーバーへの接続に失敗 (モック)")


    # シャットダウン
    await manager.shutdown()

if __name__ == "__main__":
    # Python 3.7+
    # asyncio.run(main_test())
    # 古いPythonバージョンでの実行方法
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main_test())
    finally:
        loop.close()
