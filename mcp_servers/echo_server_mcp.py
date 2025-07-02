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

echo_server_logger.info("echo_server_mcp.py loaded. If run via 'mcp run', it should pick up 'mcp_instance'.")

# `mcp run` で実行されることを期待するため、if __name__ == "__main__": ブロックは書かない。
# `mcp run` はこのファイルで見つかったFastMCPインスタンス (ここでは `mcp_instance`) を
# 自動的に実行するはず。
# もし `python echo_server_mcp.py` で直接実行したい場合は、以下のようなブロックが必要。
# if __name__ == "__main__":
#     if mcp_instance:
#         echo_server_logger.info("Starting EchoMCPServer directly via __main__.")
#         try:
#             mcp_instance.run() # FastMCP.run() はブロッキングする
#             echo_server_logger.info("EchoMCPServer run() finished.")
#         except Exception as e:
#             echo_server_logger.error(f"Error running EchoMCPServer directly: {e}", exc_info=True)
#     else:
#         echo_server_logger.error("FastMCP instance not created. Cannot run server.")
