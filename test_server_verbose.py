"""
詳細ログ付きのMCPサーバーテスト
stdin/stdoutでの通信を詳しく記録
"""
import asyncio
import json
import sys
import logging
from pathlib import Path

# 詳細ログ設定
LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
SERVER_LOG_FILE = LOG_DIR / "verbose_server.log"

logger = logging.getLogger("VerboseServer")
logger.setLevel(logging.DEBUG)
if logger.hasHandlers():
    logger.handlers.clear()

# ファイルログ
fh = logging.FileHandler(SERVER_LOG_FILE, mode='w', encoding='utf-8')
fh.setLevel(logging.DEBUG)

# コンソールログ（stderr経由）
ch = logging.StreamHandler(sys.stderr)
ch.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)

logger.addHandler(fh)
logger.addHandler(ch)
logger.propagate = False

async def handle_stdin():
    """標準入力からのJSON-RPCメッセージを処理"""
    logger.info("VerboseServer: Starting stdin handler")
    
    while True:
        try:
            # 標準入力から1行読み取り
            logger.debug("VerboseServer: Waiting for input...")
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            
            if not line:
                logger.info("VerboseServer: EOF received, shutting down")
                break
                
            line = line.strip()
            if not line:
                continue
                
            logger.info(f"VerboseServer: Received: {line}")
            
            try:
                request = json.loads(line)
                logger.info(f"VerboseServer: Parsed request: {request}")
                
                # initialize リクエストに応答
                if request.get("method") == "initialize":
                    logger.info("VerboseServer: Handling initialize request")
                    response = {
                        "jsonrpc": "2.0",
                        "id": request.get("id"),
                        "result": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {
                                "tools": {},
                                "resources": {}
                            },
                            "serverInfo": {
                                "name": "verbose-test-server",
                                "version": "1.0.0"
                            }
                        }
                    }
                    response_line = json.dumps(response)
                    print(response_line, flush=True)
                    logger.info(f"VerboseServer: Sent response: {response_line}")
                    
                elif request.get("method") == "notifications/initialized":
                    logger.info("VerboseServer: Received initialized notification - server ready")
                    
                elif request.get("method") == "tools/list":
                    logger.info("VerboseServer: Handling tools/list request")
                    response = {
                        "jsonrpc": "2.0",
                        "id": request.get("id"),
                        "result": {
                            "tools": [
                                {
                                    "name": "test_tool",
                                    "description": "A test tool",
                                    "inputSchema": {
                                        "type": "object",
                                        "properties": {},
                                        "required": []
                                    }
                                }
                            ]
                        }
                    }
                    response_line = json.dumps(response)
                    print(response_line, flush=True)
                    logger.info(f"VerboseServer: Sent tools response: {response_line}")
                    
                else:
                    logger.warning(f"VerboseServer: Unknown method: {request.get('method')}")
                    
            except json.JSONDecodeError as e:
                logger.error(f"VerboseServer: Invalid JSON: {e}")
                
        except Exception as e:
            logger.error(f"VerboseServer: Error in stdin handler: {e}", exc_info=True)
            break

if __name__ == "__main__":
    logger.info("VerboseServer: Starting verbose MCP test server")
    logger.info(f"VerboseServer: Python executable: {sys.executable}")
    logger.info(f"VerboseServer: Working directory: {Path.cwd()}")
    logger.info(f"VerboseServer: Log file: {SERVER_LOG_FILE}")
    
    try:
        asyncio.run(handle_stdin())
    except KeyboardInterrupt:
        logger.info("VerboseServer: Shutting down via KeyboardInterrupt")
    except Exception as e:
        logger.error(f"VerboseServer: Fatal error: {e}", exc_info=True)
        
    logger.info("VerboseServer: Shutdown complete")