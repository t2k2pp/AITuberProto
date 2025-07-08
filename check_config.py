from config import ConfigManager
import json

config = ConfigManager()

print('Current MCP settings:')
print(json.dumps(config.get_mcp_settings(), indent=2, ensure_ascii=False))
print()
print('Config file path:', config.config_file)
print()

# 特にfilesystemサーバーの設定を詳しく確認
filesystem_config = config.get_mcp_server_config('filesystem')
print('Filesystem server config:')
print(json.dumps(filesystem_config, indent=2, ensure_ascii=False))