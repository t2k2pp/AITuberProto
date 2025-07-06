import subprocess
import json

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

# サーバープロセスを起動
process = subprocess.Popen(
    ['python3', 'mcp_servers/file_system_server.py'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# メッセージ送信
json_str = json.dumps(message)
print(f'Sending: {json_str}')
stdout, stderr = process.communicate(json_str)

print('STDOUT:', stdout)
print('STDERR:', stderr)
print('Return code:', process.returncode)