import subprocess
import sys
import time
import os
from pathlib import Path

def test_server_direct():
    """MCPサーバーが直接起動できるかテストする"""
    print("Testing MCP server startup directly...")
    
    # ログディレクトリの確認
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "filesystem_server.log"
    
    # 以前のログファイルがあれば削除
    if log_file.exists():
        os.remove(log_file)
    
    try:
        # MCPサーバーを起動（5秒でタイムアウト）
        print("Starting MCP server process...")
        process = subprocess.Popen(
            [sys.executable, "./mcp_servers/file_system_server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={**os.environ, "PYTHONUNBUFFERED": "1"}
        )
        
        # 5秒待機
        print("Waiting 5 seconds for server to initialize...")
        time.sleep(5)
        
        # プロセスの状態を確認
        poll_result = process.poll()
        if poll_result is None:
            print("✓ Server process is running")
            # プロセスを終了
            process.terminate()
            try:
                process.wait(timeout=3)
                print("✓ Server terminated gracefully")
            except subprocess.TimeoutExpired:
                process.kill()
                print("✗ Server had to be force-killed")
        else:
            print(f"✗ Server process exited with code: {poll_result}")
            stdout, stderr = process.communicate()
            if stdout:
                print(f"STDOUT: {stdout}")
            if stderr:
                print(f"STDERR: {stderr}")
        
        # ログファイルの内容を確認
        if log_file.exists():
            print(f"\n--- Log file content ({log_file}) ---")
            with open(log_file, 'r', encoding='utf-8') as f:
                log_content = f.read()
                print(log_content)
        else:
            print(f"✗ Log file not created: {log_file}")
            
    except Exception as e:
        print(f"✗ Error testing server: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_server_direct()