from config import ConfigManager

# 設定マネージャーを作成
config = ConfigManager()

# filesystemサーバーの正しい設定
correct_filesystem_config = {
    "enabled": True,
    "command": "python",
    "args": ["./mcp_servers/file_system_server.py"],
    "env": {"PYTHONUNBUFFERED": "1"},
    "description": "File system operations server"
}

# 設定を修正
print("Fixing filesystem server configuration...")
config.save_mcp_server_config("filesystem", correct_filesystem_config)

print("Configuration fixed!")

# 確認
import json
filesystem_config = config.get_mcp_server_config('filesystem')
print("\nUpdated filesystem server config:")
print(json.dumps(filesystem_config, indent=2, ensure_ascii=False))