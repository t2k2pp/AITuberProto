import asyncio
import logging
import json
from pathlib import Path

# ログレベルを最大詳細に設定
logging.basicConfig(level=logging.DEBUG)

async def test_protocol_init():
    """プロトコル初期化の詳細をテスト"""
    print("=== Manual MCP Protocol Initialization Test ===")
    
    try:
        from mcp.client.stdio import StdioServerParameters, stdio_client
        from mcp.client.session import ClientSession
        from mcp.types import Implementation
        
        # サーバーパラメータ
        server_script = str(Path(__file__).parent / "mcp_servers" / "file_system_server.py")
        server_params = StdioServerParameters(
            command="python",
            args=[server_script],
            env={"PYTHONUNBUFFERED": "1"}
        )
        
        print("=== Creating stdio context ===")
        stdio_context = stdio_client(server_params)
        
        print("=== Entering stdio context ===")
        read_stream, write_stream = await stdio_context.__aenter__()
        print("✓ Stdio streams established")
        
        # 手動でプロトコル初期化をテスト
        print("=== Testing manual protocol initialization ===")
        
        # 初期化リクエストを手動で送信
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {
                        "listChanged": True
                    },
                    "sampling": {}
                },
                "clientInfo": {
                    "name": "aituber-mcp-client",
                    "version": "1.0.0"
                }
            }
        }
        
        print("=== Sending initialize request ===")
        message_bytes = (json.dumps(init_request) + "\n").encode('utf-8')
        write_stream.write(message_bytes)
        await write_stream.drain()
        print(f"✓ Sent: {json.dumps(init_request)}")
        
        print("=== Waiting for initialize response ===")
        try:
            # 5秒でタイムアウト
            response_data = await asyncio.wait_for(read_stream.readline(), timeout=5.0)
            response_text = response_data.decode('utf-8').strip()
            print(f"✓ Received: {response_text}")
            
            try:
                response_json = json.loads(response_text)
                if "result" in response_json:
                    print("✓ Initialize response is valid")
                    
                    # initialized通知を送信
                    initialized_notification = {
                        "jsonrpc": "2.0",
                        "method": "notifications/initialized"
                    }
                    
                    print("=== Sending initialized notification ===")
                    notif_bytes = (json.dumps(initialized_notification) + "\n").encode('utf-8')
                    write_stream.write(notif_bytes)
                    await write_stream.drain()
                    print(f"✓ Sent: {json.dumps(initialized_notification)}")
                    
                    print("=== Protocol initialization completed manually ===")
                    
                else:
                    print(f"✗ Unexpected response format: {response_json}")
            except json.JSONDecodeError as je:
                print(f"✗ Invalid JSON response: {je}")
                
        except asyncio.TimeoutError:
            print("✗ No response received within 5 seconds")
            print("This indicates the server is not responding to initialize requests")
            
        # クリーンアップ
        try:
            await stdio_context.__aexit__(None, None, None)
        except:
            pass
            
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_protocol_init())