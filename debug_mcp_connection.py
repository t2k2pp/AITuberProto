import asyncio
from mcp_client import MCPClientManager
from config import ConfigManager

async def test():
    config = ConfigManager()
    manager = MCPClientManager(config_manager=config)
    
    # filesystemサーバーの設定を取得
    server_config = config.get_mcp_server_config('filesystem')
    print(f'Server config: {server_config}')
    
    try:
        print('Starting connection test...')
        # タイムアウトを追加して接続テスト
        await asyncio.wait_for(
            manager.connect_to_server('filesystem', server_config),
            timeout=15.0
        )
        print(f'Available tools: {list(manager.available_tools.keys())}')
        print('Connection successful!')
    except asyncio.TimeoutError:
        print('Connection timed out after 15 seconds')
        print('This suggests the server process is not responding or there is a communication issue')
    except Exception as e:
        print(f'Connection failed: {e}')
        import traceback
        traceback.print_exc()
    finally:
        try:
            await asyncio.wait_for(manager.shutdown(), timeout=5.0)
        except:
            pass

if __name__ == "__main__":
    asyncio.run(test())