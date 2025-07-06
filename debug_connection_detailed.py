import asyncio
import logging
from mcp_client import MCPClientManager
from config import ConfigManager

# ログレベルを詳細に設定
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def test_detailed():
    config = ConfigManager()
    manager = MCPClientManager(config_manager=config)
    
    server_config = config.get_mcp_server_config('filesystem')
    print(f'Server config: {server_config}')
    
    try:
        print('=== Step 1: Starting connection test ===')
        
        # 接続プロセスを段階別にテスト
        print('=== Step 2: Creating server parameters ===')
        
        from mcp.client.stdio import StdioServerParameters
        command = server_config.get("command", "python")
        raw_args = server_config.get("args", [])
        processed_args = manager._resolve_server_script_path(command, raw_args)
        
        import os
        from pathlib import Path
        effective_env = os.environ.copy()
        effective_env.update(server_config.get("env", {}))
        effective_env["PYTHONUNBUFFERED"] = "1"
        
        project_root = str(Path(__file__).resolve().parent)
        pythonpath = effective_env.get("PYTHONPATH", "")
        if project_root not in pythonpath:
            effective_env["PYTHONPATH"] = f"{project_root}{os.pathsep}{pythonpath}".strip(os.pathsep)
        
        server_params = StdioServerParameters(
            command=command,
            args=processed_args,
            env=effective_env
        )
        print(f'Server params created: {command} {processed_args}')
        
        print('=== Step 3: Creating stdio client ===')
        from mcp.client.stdio import stdio_client
        stdio_context = stdio_client(server_params)
        
        print('=== Step 4: Entering stdio context ===')
        read_stream, write_stream = await asyncio.wait_for(
            stdio_context.__aenter__(), 
            timeout=10.0
        )
        print('✓ Stdio context entered successfully')
        
        print('=== Step 5: Creating ClientSession ===')
        from mcp.client.session import ClientSession
        from mcp.types import Implementation
        
        client_info = Implementation(
            name="aituber-mcp-client",
            version="1.0.0"
        )
        
        session = ClientSession(
            read_stream, 
            write_stream,
            client_info=client_info
        )
        print('✓ ClientSession created')
        
        print('=== Step 6: Initializing session ===')
        await asyncio.wait_for(session.initialize(), timeout=10.0)
        print('✓ Session initialized successfully')
        
        print('=== Step 7: Listing tools ===')
        try:
            tools_response = await asyncio.wait_for(session.list_tools(), timeout=5.0)
            print(f'✓ Tools listed: {tools_response}')
        except Exception as tools_error:
            print(f'✗ Failed to list tools: {tools_error}')
        
        print('=== Test completed successfully ===')
        
        # クリーンアップ
        try:
            await stdio_context.__aexit__(None, None, None)
        except:
            pass
            
    except asyncio.TimeoutError as te:
        print(f'✗ Timeout during connection: {te}')
    except Exception as e:
        print(f'✗ Connection failed: {e}')
        import traceback
        traceback.print_exc()
    finally:
        try:
            await asyncio.wait_for(manager.shutdown(), timeout=5.0)
        except:
            pass

if __name__ == "__main__":
    asyncio.run(test_detailed())