import asyncio
from pathlib import Path

async def test_correct_message_format():
    """正しいMCPメッセージ形式でテスト"""
    print("=== Testing Correct MCP Message Format ===")
    
    try:
        from mcp.client.stdio import StdioServerParameters, stdio_client
        from mcp.types import JSONRPCMessage, RequestMessage, InitializeRequest
        from mcp.types import InitializeRequestParams, ClientCapabilities, Implementation
        
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
        
        print("=== Creating proper MCP initialize message ===")
        
        # 正しいMCPメッセージオブジェクトを作成
        client_info = Implementation(name="aituber-mcp-client", version="1.0.0")
        capabilities = ClientCapabilities()
        
        init_params = InitializeRequestParams(
            protocolVersion="2024-11-05",
            capabilities=capabilities,
            clientInfo=client_info
        )
        
        init_request = InitializeRequest(
            id=1,
            params=init_params
        )
        
        # JSONRPCMessageとしてラップ
        json_rpc_message = JSONRPCMessage(request=init_request)
        
        print(f"Message type: {type(json_rpc_message)}")
        print(f"Message attributes: {dir(json_rpc_message)}")
        
        print("=== Sending proper MCP message ===")
        await write_stream.send(json_rpc_message)
        print("✓ MCP message sent successfully")
        
        print("=== Waiting for response ===")
        try:
            response = await asyncio.wait_for(read_stream.receive(), timeout=10.0)
            print(f"✓ Received response: {response}")
            print(f"Response type: {type(response)}")
            
        except asyncio.TimeoutError:
            print("✗ No response received within 10 seconds")
            
        # クリーンアップ
        try:
            await stdio_context.__aexit__(None, None, None)
        except:
            pass
            
    except ImportError as ie:
        print(f"✗ Import error (trying alternative): {ie}")
        
        # 代替方法: SessionMessageを使用
        try:
            from mcp.client.session import SessionMessage
            from mcp.types import JSONRPCMessage, RequestMessage
            
            # より簡単な方法でテスト
            print("=== Using alternative SessionMessage approach ===")
            
        except Exception as alt_error:
            print(f"✗ Alternative approach failed: {alt_error}")
            
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_correct_message_format())