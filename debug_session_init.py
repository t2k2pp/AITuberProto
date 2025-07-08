import asyncio
from pathlib import Path

async def test_session_init_details():
    """ClientSession.initialize()の詳細を調査"""
    print("=== Investigating ClientSession.initialize() ===")
    
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
        
        print("=== Creating ClientSession ===")
        client_info = Implementation(name="aituber-mcp-client", version="1.0.0")
        session = ClientSession(read_stream, write_stream, client_info=client_info)
        
        print("=== Inspecting ClientSession ===")
        print(f"Session type: {type(session)}")
        print(f"Session read_stream: {type(session._read_stream)}")
        print(f"Session write_stream: {type(session._write_stream)}")
        
        # ClientSession._initializeメソッドの詳細を確認
        if hasattr(session, '_initialize'):
            print("✓ Session has _initialize method")
        if hasattr(session, 'initialize'):
            print("✓ Session has initialize method")
            
        # より詳細なロギングを有効にして initialize を実行
        import logging
        logging.getLogger('mcp').setLevel(logging.DEBUG)
        
        print("=== Calling session.initialize() with detailed logging ===")
        try:
            # より短いタイムアウトで試す
            await asyncio.wait_for(session.initialize(), timeout=8.0)
            print("✓ Session initialized successfully!")
            
        except asyncio.TimeoutError:
            print("✗ Session initialization timed out")
            
            # セッション内部の状態を確認
            print(f"Session state: {getattr(session, '_state', 'unknown')}")
            if hasattr(session, '_pending_requests'):
                print(f"Pending requests: {session._pending_requests}")
                
        except Exception as init_error:
            print(f"✗ Session initialization failed: {init_error}")
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
    asyncio.run(test_session_init_details())