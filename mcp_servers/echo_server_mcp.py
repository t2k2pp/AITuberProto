import logging
from pathlib import Path
from typing import Optional # Optional をインポート

# --- 専用ファイルロガー設定 ---
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
ECHO_SERVER_LOG_FILE = LOG_DIR / "echo_server_mcp.log"

echo_server_logger = logging.getLogger("EchoMCPServerProcess")
echo_server_logger.setLevel(logging.DEBUG)
if echo_server_logger.hasHandlers():
    echo_server_logger.handlers.clear()
fh = logging.FileHandler(ECHO_SERVER_LOG_FILE, mode='w', encoding='utf-8') # 起動ごとに上書き
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
echo_server_logger.addHandler(fh)
echo_server_logger.propagate = False

echo_server_logger.info("EchoMCPServer process script started.")
# --- ロガー設定ここまで ---

mcp_instance = None # グローバルで定義しておく

try:
    from mcp.server.fastmcp import FastMCP
    echo_server_logger.info("Successfully imported FastMCP from mcp.server.fastmcp.")
    mcp_instance = FastMCP(name="EchoServerExample")
    echo_server_logger.info(f"FastMCP instance '{getattr(mcp_instance, 'name', 'N/A')}' created.")
except Exception as e:
    echo_server_logger.error(f"Failed to import or initialize FastMCP: {e}", exc_info=True)
    # モックは作らず、エラーのままにする。SDKがなければこのサーバーは機能しない。

if mcp_instance:
    @mcp_instance.tool(name="echo", description="Echoes the input message.")
    async def echo_tool(message: str) -> str:
        echo_server_logger.info(f"Tool 'echo' called with message: '{message}'")
        return message # 受け取ったメッセージをそのまま返す

    echo_server_logger.info("Tool 'echo' defined for FastMCP instance.")
else:
    echo_server_logger.warning("mcp_instance is None, 'echo' tool cannot be defined.")

echo_server_logger.info("echo_server_mcp.py loaded. Attempting to run mcp_instance if it exists.")

if mcp_instance:
    echo_server_logger.info(f"Attempting to explicitly call mcp_instance.run() for '{getattr(mcp_instance, 'name', 'N/A')}'")
    try:
        # この呼び出しがサーバーを起動し、リクエストを待ち受ける（ブロッキングする）はず
        mcp_instance.run()
        echo_server_logger.info(f"mcp_instance.run() for '{getattr(mcp_instance, 'name', 'N/A')}' finished.")
    except Exception as e_run:
        echo_server_logger.error(f"Error during explicit mcp_instance.run(): {e_run}", exc_info=True)
else:
    echo_server_logger.error("mcp_instance is None at the end of the script. Server cannot run.")

# `mcp run` で実行される場合、このファイルがモジュールとしてインポートされ、
# グローバルスコープの mcp_instance が `mcp run` コマンドによって実行されることを期待している。
# 一方で、`python echo_server_mcp.py` のように直接実行された場合にもサーバーが起動するように、
# このようにファイルの末尾で run() を呼び出す形にする。
# SDKの `mcp run` がこの末尾の run() 呼び出しをどう扱うか（二重呼び出しにならないか等）は
# やや不明瞭だが、まずはサーバーが待ち受け状態になることを優先する。
