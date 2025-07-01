import asyncio
import json # JSONを扱うためにインポート
import os # パス操作のためにインポート
from pathlib import Path # パス操作のためにインポート

# MCP SDK のインポート (mcp-integration-guide.md に基づく仮定)
# 実際のSDKの構造に合わせて調整が必要
try:
    from modelcontextprotocol.sdk.server import Server, ServerTransport
    from modelcontextprotocol.sdk.server.stdio import StdioServerTransport
    # from modelcontextprotocol.sdk.types import ToolCallRequest, ToolListRequest, ToolResponse
except ImportError:
    print("Warning: MCP SDK (Server) not found. Using mock objects for FileSystemMCPServer.")

    class MockServer:
        def __init__(self, server_info: dict, server_options: dict):
            self.name = server_info.get("name")
            self.version = server_info.get("version")
            self.capabilities = server_options.get("capabilities")
            self.request_handlers: dict[str, callable] = {}
            print(f"MockServer created: {self.name} v{self.version}")

        def setRequestHandler(self, route: str, handler: callable):
            print(f"MockServer {self.name}: Setting request handler for route '{route}'")
            self.request_handlers[route] = handler

        async def connect(self, transport: any):
            print(f"MockServer {self.name}: Connected via {type(transport).__name__}")
            # ここで transport からの入力を待ち受けるループを開始するシミュレーションが必要だが、
            # StdioServerTransport の具体的な動作が不明なため簡略化
            await asyncio.sleep(0.1) # 接続処理を模倣
            # 実際には transport.run() のようなメソッドを呼び出すか、
            # transport がコールバックを登録する形式かもしれない。
            # このモックでは、外部からの呼び出しは直接ハンドラを叩く形を想定。

        async def _process_request(self, request_data: dict):
            """ダミーリクエスト処理。stdio transportがこれを使う想定"""
            route = request_data.get("route")
            params = request_data.get("params")
            request_id = request_data.get("id", "unknown_id")

            if route in self.request_handlers:
                try:
                    response_data = await self.request_handlers[route]({"id": request_id, "params": params})
                    print(f"MockServer: Request to {route} handled. Response: {response_data}")
                    # 実際には transport 経由でクライアントに送り返す
                except Exception as e:
                    print(f"MockServer: Error handling request to {route}: {e}")
                    # エラーレスポンスをクライアントに送り返す
            else:
                print(f"MockServer: No handler for route {route}")
                # エラーレスポンス

    class MockStdioServerTransport:
        def __init__(self):
            print("MockStdioServerTransport created.")
            # 実際のStdioServerTransportは標準入出力を監視するループを持つはず
            # ここではその動作をシミュレートしない

        async def run(self, server_instance: MockServer):
            # このメソッドはSDKの transport.connect(server) のようなものかもしれないし、
            # server.connect(transport) の中で transport.run() が呼ばれるかもしれない。
            # ここでは、サーバーが接続後に transport を実行すると仮定。
            print("MockStdioServerTransport: Running (simulated stdio loop would be here)")
            # 標準入力からのメッセージを待ち受け、server_instance._process_request を呼び出す、
            # というような処理がここに入る。このモックでは省略。
            # テストのために手動で _process_request を呼び出す必要がある。
            pass


    Server = MockServer # type: ignore
    StdioServerTransport = MockStdioServerTransport # type: ignore
    # ToolCallRequest = dict # type: ignore
    # ToolListRequest = dict # type: ignore
    # ToolResponse = dict # type: ignore


import logging
logger = logging.getLogger(__name__)
# このファイルが直接実行される場合に備えて基本的なロギング設定
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class FileSystemMCPServer:
    def __init__(self):
        self.server_name = "filesystem-server"
        self.server_version = "1.0.0"
        # このサーバーが起動しているスクリプトの場所を基準にする
        self.base_dir = Path(__file__).resolve().parent.parent # プロジェクトルートを想定
        logger.info(f"FileSystemMCPServer base directory set to: {self.base_dir}")

        self.server = Server({ # type: ignore
            "name": self.server_name,
            "version": self.server_version
        }, { # type: ignore
            "capabilities": {
                "tools": {
                    "listSupported": True # tools/list をサポート
                },
                # resources は今回は実装しない
            }
        })

        self._setup_tool_handlers()

    def _setup_tool_handlers(self):
        # 利用可能なツールの一覧を提供
        self.server.setRequestHandler('tools/list', self._handle_list_tools) # type: ignore

        # ファイル読み取りツール
        self.server.setRequestHandler('tools/call', self._handle_call_tool) # type: ignore

    async def _handle_list_tools(self, request: dict) -> dict:
        # request の中身はSDKによるが、通常 request_id などが含まれる
        # request_id = request.get("id")
        logger.info(f"'{self.server_name}' received tools/list request.")
        return {
            # "id": request_id, # レスポンスにIDを含めるかはSDK仕様による
            "tools": [
                {
                    "name": 'read_file',
                    "description": '指定されたパスのファイルの内容を読み取ります。パスはプロジェクトルートからの相対パスです。',
                    "inputSchema": {
                        "type": 'object',
                        "properties": {
                            "path": {
                                "type": 'string',
                                "description": '読み取るファイルの相対パス (例: "data/my_text.txt")'
                            }
                        },
                        "required": ['path']
                    },
                    "outputSchema": { # 出力スキーマも定義しておくと良い
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "ファイルの内容"
                            }
                        }
                    }
                }
                # 他のツール (write_file, list_directory など) もここに追加可能
            ]
        }

    async def _handle_call_tool(self, request: dict) -> dict:
        # request_id = request.get("id")
        params = request.get("params", {})
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        logger.info(f"'{self.server_name}' received tools/call request for tool '{tool_name}' with arguments: {arguments}")

        try:
            if tool_name == 'read_file':
                result_content = await self._tool_read_file(arguments)
                # ガイドの形式に合わせる: content: [{ type: 'text', text: content }]
                # ただし、クライアント側がシンプルな文字列を期待しているならそれに合わせる
                return {
                    # "id": request_id,
                    "content": [{ "type": "text", "text": result_content }]
                    # "content": result_content # よりシンプルな場合
                }
            else:
                logger.warning(f"Unknown tool requested: {tool_name}")
                raise ValueError(f"未知のツールです: {tool_name}")
        except Exception as e:
            logger.error(f"Error executing tool '{tool_name}': {e}")
            # エラーレスポンスの形式はSDK仕様による
            return {
                # "id": request_id,
                "error": str(e),
                "details": {"tool_name": tool_name, "arguments": arguments}
            }

    async def _tool_read_file(self, args: dict) -> str:
        file_path_str = args.get("path")
        if not file_path_str:
            raise ValueError("ファイルパス 'path' が指定されていません。")

        # セキュリティ: パストラバーサル攻撃を防ぐ
        # Path.resolve() を使うと絶対パスになるので、それが base_dir の中にあるか確認
        try:
            # ユーザー指定パスを base_dir からの相対パスとして解決
            # Path.joinpath は .. を含むパスを正しく解決してくれる
            # (例: base_dir / "subdir" / "../file.txt" -> base_dir / "file.txt")
            # ただし、base_dir の外に出るような ".." (例: "../../etc/passwd") は防げない
            # Path.resolve() はシンボリックリンクを解決する。
            # os.path.abspath は純粋に文字列として絶対パスにする。

            # 1. ユーザー入力をノーマライズ
            normalized_user_path = os.path.normpath(file_path_str)
            if normalized_user_path.startswith("..") or os.path.isabs(normalized_user_path):
                raise PermissionError("不正なパス形式です。絶対パスや親ディレクトリへの移動は許可されていません。")

            # 2. base_dir と結合して絶対パスに
            absolute_path = self.base_dir.joinpath(normalized_user_path).resolve()

            # 3. 解決されたパスが base_dir の中にあるか確認
            #   os.path.commonpath を使ってチェックする方法もある
            if not str(absolute_path).startswith(str(self.base_dir.resolve())):
                 raise PermissionError(f"指定されたパス '{file_path_str}' へのアクセスは許可されていません (ディレクトリトラバーサル)。")

            # 4. ファイルが存在するか確認
            if not absolute_path.is_file():
                raise FileNotFoundError(f"ファイル '{absolute_path}' が見つかりません。")

            logger.info(f"Reading file: {absolute_path}")
            # ここで非同期ファイル読み取りを使うのが理想だが、Python標準には簡単な方法がない
            # aiofiles などのライブラリが必要。ここでは同期読み込みで代用。
            # 大容量ファイルを扱う場合は非同期化を検討すること。
            with open(absolute_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content

        except PermissionError as e:
            logger.error(f"Permission denied for path '{file_path_str}': {e}")
            raise
        except FileNotFoundError as e:
            logger.error(f"File not found at path '{file_path_str}': {e}")
            raise
        except Exception as e:
            logger.error(f"Error reading file '{file_path_str}': {e}")
            raise ValueError(f"ファイル読み取りエラー: {e}")


    async def start(self) -> None:
        transport = StdioServerTransport() # type: ignore
        logger.info(f"Starting {self.server_name} v{self.server_version} on stdio transport...")
        # server.connect(transport) の中で transport.run(self.server) が呼ばれるか、
        # transport が server のリクエストハンドラを直接知るか、SDKの設計による。
        # Mock の場合は transport.run(self.server) のような形を想定しているが、
        # 実際のSDKでは server.connect が完了するまで待つだけで良いかもしれない。
        await self.server.connect(transport) # type: ignore
        logger.info(f"{self.server_name} started and listening for requests.")
        # モックSDKの場合、ここで手動でリクエストをシミュレートしないと何も起こらない。
        # 実際のSDKでは StdioServerTransport が標準入力を監視するループを開始する。


async def main():
    server = FileSystemMCPServer()
    try:
        await server.start()
        # StdioServerTransportが適切に動作していれば、ここでプロセスは終了せず、
        # 標準入力からのメッセージを待ち受ける状態になる。
        # Mock の場合は start() がすぐに完了してしまうので、テストのためには
        # server.server._process_request(...) を手動で呼び出す必要がある。
        # 例:
        if isinstance(server.server, MockServer) and isinstance(server.server.transport, MockStdioServerTransport) : # type: ignore
            logger.info("MockServer detected. Simulating some client requests for testing.")
            # tools/list のテスト
            list_tools_req = {"route": "tools/list", "id": "req1"}
            await server.server._process_request(list_tools_req) # type: ignore

            # read_file のテスト (成功例)
            # テスト用のファイルを作成
            test_file_path = server.base_dir / "mcp_servers" / "test_readable_file.txt"
            with open(test_file_path, "w", encoding="utf-8") as tf:
                tf.write("これはMCPサーバーから読み込まれるテストファイルです。")

            read_file_req_success = {
                "route": "tools/call",
                "id": "req2",
                "params": {"name": "read_file", "arguments": {"path": "mcp_servers/test_readable_file.txt"}}
            }
            await server.server._process_request(read_file_req_success) # type: ignore
            os.remove(test_file_path) # テスト用ファイル削除

            # read_file のテスト (失敗例: ファイルなし)
            read_file_req_notfound = {
                "route": "tools/call",
                "id": "req3",
                "params": {"name": "read_file", "arguments": {"path": "non_existent_file.txt"}}
            }
            await server.server._process_request(read_file_req_notfound) # type: ignore

            # read_file のテスト (失敗例: パストラバーサル)
            read_file_req_traversal = {
                "route": "tools/call",
                "id": "req4",
                "params": {"name": "read_file", "arguments": {"path": "../config.py"}} # プロジェクトルートのconfig.pyを狙う
            }
            await server.server._process_request(read_file_req_traversal) # type: ignore

            logger.info("Mock request simulation finished. Server would normally keep running.")
            # 実際のSDKならここでCtrl+Cなどで終了するまで待機
            while True: # 実際のサーバーのように待機するのを模倣
                await asyncio.sleep(1)


    except KeyboardInterrupt:
        logger.info("FileSystemMCPServer shutting down...")
    except Exception as e:
        logger.error(f"An error occurred in FileSystemMCPServer: {e}", exc_info=True)
    finally:
        logger.info("FileSystemMCPServer stopped.")


if __name__ == "__main__":
    # Python 3.7+
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Exiting FileSystemMCPServer (main)...")
    # 古いPythonでの実行方法
    # loop = asyncio.get_event_loop()
    # try:
    #     loop.run_until_complete(main())
    # except KeyboardInterrupt:
    #     logger.info("Exiting FileSystemMCPServer (main loop)...")
    # finally:
    #     loop.close()
