import asyncio
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, TypedDict, Optional
import logging

# --- 専用ファイルロガー設定 ---
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
SERVER_LOG_FILE = LOG_DIR / "filesystem_server.log"

server_logger = logging.getLogger("FileSystemMCPServerProcess")
server_logger.setLevel(logging.DEBUG)
if server_logger.hasHandlers():
    server_logger.handlers.clear()
fh = logging.FileHandler(SERVER_LOG_FILE, mode='w', encoding='utf-8')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
server_logger.addHandler(fh)
server_logger.propagate = False

server_logger.info("FileSystemMCPServer process started (FastMCP implementation).")
server_logger.info(f"Current working directory: {os.getcwd()}")
server_logger.info(f"Python executable: {sys.executable}")
# --- ロガー設定ここまで ---

MCP_SDK_SERVER_AVAILABLE = False
FastMCP_SDK = None # SDKのFastMCPクラスを指す変数
TextContent_SDK = None # SDKのTextContentクラスを指す変数

try:
    from mcp.server.fastmcp import FastMCP as SDK_FastMCP
    from mcp.types import TextContent as SDK_TextContent
    MCP_SDK_SERVER_AVAILABLE = True
    FastMCP_SDK = SDK_FastMCP
    TextContent_SDK = SDK_TextContent
    server_logger.info("Successfully imported MCP SDK server classes (FastMCP, TextContent).")
except ImportError as e:
    server_logger.error(f"Failed to import MCP SDK for Server (FastMCP or TextContent) ({e}). This server will not function.", exc_info=True)
    # SDKがない場合は FastMCP のモックや TextContent のモックを定義
    class FastMCP_Mock:
        def __init__(self, name: str, version: str = "0.1.0", stateless_http: bool = False):
            self.name = name
            server_logger.info(f"Using Mock FastMCP (name={name}, version={version})")
        def tool(self, name: Optional[str] = None, description: Optional[str] = None, title: Optional[str] = None):
            def decorator(func):
                server_logger.info(f"Mock FastMCP: Tool '{name or func.__name__}' registered (mock).")
                return func
            return decorator
        def run(self):
            server_logger.info("Mock FastMCP: run() called (mock, does nothing).")
    FastMCP_SDK = FastMCP_Mock # type: ignore

    class TextContent_Mock:
        def __init__(self, type:str, text:str):
            self.type=type; self.text=text
            server_logger.info(f"Using Mock TextContent (text={text[:30]}...)")
    TextContent_SDK = TextContent_Mock # type: ignore


# --- グローバルなFastMCPインスタンス ---
if MCP_SDK_SERVER_AVAILABLE and FastMCP_SDK is not None:
    mcp_server = FastMCP_SDK(name="filesystem-server", version="1.0.1")
    server_logger.info(f"FastMCP instance created: Name='{getattr(mcp_server, 'name', 'N/A')}'")
else:
    mcp_server = None
    server_logger.critical("FastMCP could not be initialized due to missing SDK or import error.")


# --- ベースディレクトリ設定 ---
BASE_DIR = Path(__file__).resolve().parent.parent
server_logger.info(f"FileSystemMCPServer base directory set to: {BASE_DIR}")

class FileContentItem(TypedDict):
    type: str
    text: str

class ReadFileToolOutput(TypedDict):
    content: List[FileContentItem]

if mcp_server:
    @mcp_server.tool(
        name="read_file",
        description="指定されたパスのファイルの内容を読み取ります。パスはプロジェクトルートからの相対パスです。",
        title="ファイル読み取り"
    )
    async def tool_read_file(path: str) -> ReadFileToolOutput:
        server_logger.info(f"FastMCP tool 'read_file' called with path: {path}")

        if not isinstance(path, str):
            server_logger.error(f"Path argument is not a string: {type(path)}")
            raise TypeError("Path must be a string.")

        file_path_str = path
        try:
            normalized_user_path = os.path.normpath(file_path_str)
            if normalized_user_path.startswith("..") or os.path.isabs(normalized_user_path) or \
               normalized_user_path.startswith("/") or normalized_user_path.startswith("\\"):
                server_logger.warning(f"Attempted unauthorized path access (normalized): {normalized_user_path}")
                raise PermissionError("不正なパス形式です。絶対パス、親ディレクトリへの移動、ルートからのパス指定は許可されていません。")

            absolute_path = BASE_DIR.joinpath(normalized_user_path).resolve()

            if not str(absolute_path).startswith(str(BASE_DIR.resolve())):
                server_logger.warning(f"Attempted directory traversal. Base: {BASE_DIR}, Target: {absolute_path}")
                raise PermissionError(f"指定されたパス '{file_path_str}' へのアクセスは許可されていません。")

            if not absolute_path.is_file():
                server_logger.error(f"File not found at resolved path: {absolute_path}")
                raise FileNotFoundError(f"ファイル '{absolute_path}' が見つかりません。")

            server_logger.info(f"Reading file: {absolute_path}")
            with open(absolute_path, 'r', encoding='utf-8') as f:
                content_text = f.read()

            # TextContent_SDK を使用 (SDKがあれば本物、なければモック)
            # text_content_obj = TextContent_SDK(type="text", text=content_text)
            # output: ReadFileToolOutput = {"content": [text_content_obj]} # TextContentオブジェクトを直接リストに入れるのは型が違う
            # ReadFileToolOutput は FileContentItem のリストを期待

            file_item: FileContentItem = {"type": "text", "text": content_text}
            output: ReadFileToolOutput = {"content": [file_item]}

            server_logger.info(f"File '{path}' read successfully. Content length: {len(content_text)}")
            return output
        except Exception as e:
            server_logger.error(f"Error in tool_read_file for path '{path}': {e}", exc_info=True)
            raise

# --- サーバー起動 ---
if __name__ == "__main__":
    if not MCP_SDK_SERVER_AVAILABLE or mcp_server is None:
        server_logger.critical("MCP SDK not available or FastMCP server not initialized. Cannot start.")
        exit(1)
    try:
        server_logger.info(f"Starting FileSystemMCPServer (FastMCP) '{getattr(mcp_server, 'name', 'N/A')}'...")
        mcp_server.run()
        server_logger.info("FileSystemMCPServer (FastMCP) stopped.")
    except KeyboardInterrupt:
        server_logger.info("FileSystemMCPServer (FastMCP) shutting down via KeyboardInterrupt...")
    except Exception as e:
        server_logger.error(f"An error occurred while running FileSystemMCPServer (FastMCP): {e}", exc_info=True)
