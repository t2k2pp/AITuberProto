import asyncio
import json
import os
from pathlib import Path
from typing import List, Dict, Any, TypedDict # TypedDict を追加

# MCP SDK のインポート
try:
    from mcp.server.fastmcp import FastMCP
    from mcp.types import TextContent # TextContent をインポート試行
    MCP_SDK_SERVER_AVAILABLE = True
    print("Successfully imported MCP SDK server classes (FastMCP, TextContent).")
except ImportError as e:
    MCP_SDK_SERVER_AVAILABLE = False
    print(f"Warning: Failed to import MCP SDK for Server (FastMCP or TextContent) ({e}). Mocking will be limited for FileSystemMCPServer.")
    # FastMCP のモックは複雑なので、ここでは単純化する。
    # SDKなしではこのサーバーは正しく機能しないことを明確にする。
    class FastMCP: # type: ignore
        def __init__(self, name: str, version: str = "0.1.0", stateless_http: bool = False):
            self.name = name
            self.version = version
            logger.warning("Using Mock FastMCP. Server will not be fully functional.")
        def tool(self, name: Optional[str] = None, description: Optional[str] = None, title: Optional[str] = None):
            def decorator(func):
                logger.info(f"Mock FastMCP: Tool '{name or func.__name__}' registered (mock).")
                return func
            return decorator
        def run(self):
            logger.info("Mock FastMCP: run() called (mock, does nothing).")

    class TextContent: # type: ignore
         def __init__(self, type:str, text:str):
             self.type = type
             self.text = text
             logger.info(f"Mock TextContent created with text: {text[:30]}...")


# ロギング設定
import logging
logger = logging.getLogger(__name__)
if __name__ == '__main__': # このファイルが直接実行される場合のみ基本設定
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- グローバルなFastMCPインスタンス ---
# (ファイルシステムサーバーは通常一つなのでグローバルでも問題ないと判断)
# サーバー名は config.py のキーと合わせるのが望ましいが、ここでは固定
mcp_server = FastMCP(name="filesystem-server", version="1.0.1") # バージョンを少し上げる

# --- ベースディレクトリ設定 ---
# このサーバーが起動しているスクリプトの場所を基準にする
# クライアントから渡されるパスはこの base_dir からの相対パスとして解釈する
BASE_DIR = Path(__file__).resolve().parent.parent
logger.info(f"FileSystemMCPServer (FastMCP) base directory set to: {BASE_DIR}")


# --- 型定義 (ツールの出力用) ---
# mcp-integration-guide.md のサーバー側 handleReadFile の戻り値形式に合わせる
# {"content": [{"type": "text", "text": content}]}
# これを FastMCP で実現するには、ツールが List[TextContent] を返すのが適切そう
# あるいは、ツールが Dict[str, List[Dict[str,str]]] を返し、クライアントがそれをそのまま使うか。
# GitHub READMEの "Structured Output" によると、PydanticモデルやTypedDictが使える。
# ここでは TypedDict を使って、期待されるJSON構造に合うようにしてみる。
class FileContentItem(TypedDict):
    type: str
    text: str

class ReadFileToolOutput(TypedDict):
    content: List[FileContentItem]


# --- ツール定義 ---
@mcp_server.tool(
    name="read_file", # ツール名を明示
    description="指定されたパスのファイルの内容を読み取ります。パスはプロジェクトルートからの相対パスです。",
    title="ファイル読み取り" # オプションでタイトルも
)
async def tool_read_file(path: str) -> ReadFileToolOutput: # 戻り値の型アノテーション
    """
    ファイルの内容を読み取り、MCPが期待する形式で返します。
    """
    logger.info(f"FastMCP tool 'read_file' called with path: {path}")

    if not isinstance(path, str):
        # FastMCPが型チェックしてくれるはずだが念のため
        logger.error(f"Path argument is not a string: {type(path)}")
        # エラーの返し方はFastMCPの作法に合わせる。通常は例外をraiseする。
        raise TypeError("Path must be a string.")

    file_path_str = path

    try:
        # セキュリティ: パストラバーサル攻撃を防ぐ
        normalized_user_path = os.path.normpath(file_path_str)
        if normalized_user_path.startswith("..") or os.path.isabs(normalized_user_path) or \
           normalized_user_path.startswith("/") or normalized_user_path.startswith("\\"):
            logger.warning(f"Attempted unauthorized path access (normalized): {normalized_user_path}")
            raise PermissionError("不正なパス形式です。絶対パスや親ディレクトリへの移動、ルートからのパス指定は許可されていません。")

        absolute_path = BASE_DIR.joinpath(normalized_user_path).resolve()

        if not str(absolute_path).startswith(str(BASE_DIR.resolve())):
            logger.warning(f"Attempted directory traversal. Base: {BASE_DIR}, Target: {absolute_path}")
            raise PermissionError(f"指定されたパス '{file_path_str}' へのアクセスは許可されていません。")

        if not absolute_path.is_file():
            logger.error(f"File not found at resolved path: {absolute_path}")
            raise FileNotFoundError(f"ファイル '{absolute_path}' が見つかりません。")

        logger.info(f"Reading file: {absolute_path}")
        # 大容量ファイルを扱う場合は非同期ファイルI/O (例: aiofiles) を検討
        with open(absolute_path, 'r', encoding='utf-8') as f:
            content_text = f.read()

        # mcp-integration-guide.md のレスポンス形式に合わせる
        output: ReadFileToolOutput = {
            "content": [
                {"type": "text", "text": content_text}
            ]
        }
        logger.info(f"File '{path}' read successfully. Content length: {len(content_text)}")
        return output

    except PermissionError as e:
        logger.error(f"Permission denied for path '{file_path_str}': {e}")
        # FastMCPは例外をキャッチしてエラーレスポンスに変換するはず
        raise # 再raiseしてFastMCPに処理させる
    except FileNotFoundError as e:
        logger.error(f"File not found at path '{file_path_str}': {e}")
        raise
    except Exception as e:
        logger.error(f"Error reading file '{file_path_str}': {e}", exc_info=True)
        # 包括的なエラーもFastMCPが処理する
        raise ValueError(f"ファイル読み取り中に予期せぬエラーが発生しました: {e}")


# --- サーバー起動 ---
async def main(): # FastMCPのrunは同期的だが、将来的に非同期になる可能性も考慮
    if not MCP_SDK_SERVER_AVAILABLE:
        logger.critical("MCP SDK (Server) is not available. FileSystemMCPServer cannot start properly.")
        logger.info("This instance will use a mock FastMCP and will not function as a real MCP server.")
        # モックの場合、mcp_server.run()は実際には何もしないので、ここで終了しても良い
        # が、他のテストとの整合性のため、一応呼び出す

    # 実際のSDKでは mcp_server.run() がブロッキングするサーバー起動になるはず
    # (例: uvicorn を内部で使用するなど)
    # 開発時は mcp dev file_system_server.py のようにCLIから起動することも多い
    try:
        logger.info(f"Starting FileSystemMCPServer (FastMCP) '{mcp_server.name}'...") # .version 参照を削除
        # FastMCP().run() は引数なしで、デフォルトでstdioトランスポートを使用するはず
        # (あるいは、mcp cli から `mcp run file_system_server.py` のように実行されることを想定しているかも)
        # GitHub README の "Direct Execution" の例では `mcp.run()`
        # ここでは、このファイルが直接実行された場合にサーバーが起動するようにする
        mcp_server.run() # これがサーバープロセスを起動し、リクエストを待ち受ける
        logger.info("FileSystemMCPServer (FastMCP) stopped.") # 通常はrun()が終了するまでここには来ない
    except KeyboardInterrupt:
        logger.info("FileSystemMCPServer (FastMCP) shutting down via KeyboardInterrupt...")
    except Exception as e:
        logger.error(f"An error occurred while running FileSystemMCPServer (FastMCP): {e}", exc_info=True)

if __name__ == "__main__":
    # このファイルを直接 `python file_system_server.py` で実行するとサーバーが起動する
    asyncio.run(main())
