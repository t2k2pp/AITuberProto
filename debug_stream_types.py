import asyncio
from pathlib import Path

async def debug_stream_types():
    """MCPストリームの型を調査する"""
    print("=== MCP Stream Types Investigation ===")
    
    try:
        from mcp.client.stdio import StdioServerParameters, stdio_client
        
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
        
        print(f"Read stream type: {type(read_stream)}")
        print(f"Read stream attributes: {dir(read_stream)}")
        print(f"Write stream type: {type(write_stream)}")
        print(f"Write stream attributes: {dir(write_stream)}")
        
        # MemoryObjectSendStreamの正しい使用方法を調査
        print("=== Testing stream operations ===")
        
        # send メソッドがあるかチェック
        if hasattr(write_stream, 'send'):
            print("✓ write_stream has 'send' method")
        if hasattr(write_stream, 'aclose'):
            print("✓ write_stream has 'aclose' method")
            
        if hasattr(read_stream, 'receive'):
            print("✓ read_stream has 'receive' method")
        if hasattr(read_stream, 'aclose'):
            print("✓ read_stream has 'aclose' method")
            
        # 実際にメッセージを送信してみる
        try:
            import json
            test_message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1.0.0"}
                }
            }
            
            if hasattr(write_stream, 'send'):
                print("=== Testing send method ===")
                await write_stream.send(test_message)
                print("✓ Message sent successfully using send()")
                
                # 応答を受信してみる
                if hasattr(read_stream, 'receive'):
                    print("=== Testing receive method ===")
                    try:
                        response = await asyncio.wait_for(read_stream.receive(), timeout=5.0)
                        print(f"✓ Received response: {response}")
                    except asyncio.TimeoutError:
                        print("✗ No response received within 5 seconds")
                        
        except Exception as comm_error:
            print(f"✗ Communication test failed: {comm_error}")
            import traceback
            traceback.print_exc()
        
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
    asyncio.run(debug_stream_types())