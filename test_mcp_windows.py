import subprocess
import json
import sys
import os

# 正しい形式のJSON-RPCメッセージ（clientInfo付き）
message = {
    'jsonrpc': '2.0',
    'method': 'initialize',
    'params': {
        'protocolVersion': '2024-11-05',
        'capabilities': {},
        'clientInfo': {
            'name': 'test-client',
            'version': '1.0.0'
        }
    },
    'id': 1
}

print(f"Current directory: {os.getcwd()}")
print(f"Python executable: {sys.executable}")

# Windows用のパス形式
server_script = os.path.join('mcp_servers', 'file_system_server.py')
print(f"Server script path: {server_script}")
print(f"Server script exists: {os.path.exists(server_script)}")

# サーバープロセスを起動（Windows用）
try:
    process = subprocess.Popen(
        [sys.executable, server_script],  # 現在のPython実行ファイルを使用
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # メッセージ送信
    json_str = json.dumps(message)
    print(f'Sending: {json_str}')
    
    # タイムアウト付きで通信
    try:
        stdout, stderr = process.communicate(json_str, timeout=10)
        print('STDOUT:', stdout)
        print('STDERR:', stderr)
        print('Return code:', process.returncode)
    except subprocess.TimeoutExpired:
        print("Process timed out")
        process.kill()
        stdout, stderr = process.communicate()
        print('STDOUT (after kill):', stdout)
        print('STDERR (after kill):', stderr)
        
except FileNotFoundError as e:
    print(f"FileNotFoundError: {e}")
except Exception as e:
    print(f"Error: {e}")