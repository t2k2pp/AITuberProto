"""
MCP SDK のバージョンと互換性をチェック
"""
import sys

def check_mcp_version():
    print("=== MCP SDK Version Check ===")
    
    try:
        import mcp
        print(f"✓ MCP module found: {mcp}")
        
        # バージョン情報を取得
        if hasattr(mcp, '__version__'):
            print(f"✓ MCP version: {mcp.__version__}")
        else:
            print("✗ MCP version not available")
            
        # 主要なクラスの存在を確認
        try:
            from mcp.client.session import ClientSession
            print("✓ ClientSession imported successfully")
        except ImportError as e:
            print(f"✗ ClientSession import failed: {e}")
            
        try:
            from mcp.client.stdio import stdio_client, StdioServerParameters
            print("✓ stdio_client imported successfully")
        except ImportError as e:
            print(f"✗ stdio_client import failed: {e}")
            
        try:
            from mcp.types import Implementation, JSONRPCMessage
            print("✓ MCP types imported successfully")
        except ImportError as e:
            print(f"✗ MCP types import failed: {e}")
            
        # FastMCP server の確認
        try:
            from mcp.server.fastmcp import FastMCP
            print("✓ FastMCP server imported successfully")
        except ImportError as e:
            print(f"✗ FastMCP server import failed: {e}")
            
    except ImportError as e:
        print(f"✗ MCP module not found: {e}")
        
    print("\n=== Python Environment Info ===")
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    
    # インストール済みパッケージの確認
    try:
        import subprocess
        result = subprocess.run([sys.executable, "-m", "pip", "list", "--format=freeze"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            mcp_packages = [line for line in result.stdout.split('\n') if 'mcp' in line.lower()]
            if mcp_packages:
                print("\n=== MCP-related packages ===")
                for pkg in mcp_packages:
                    print(f"  {pkg}")
            else:
                print("\n✗ No MCP packages found in pip list")
        else:
            print(f"✗ Failed to get pip list: {result.stderr}")
    except Exception as e:
        print(f"✗ Error checking packages: {e}")

if __name__ == "__main__":
    check_mcp_version()