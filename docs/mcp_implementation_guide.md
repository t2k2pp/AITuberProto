# MCP (Model Context Protocol) Python実装ガイド

## 1. MCPとは

Model Context Protocol（MCP）は、LLMアプリケーションと外部データソースやツールとの間でシームレスな統合を可能にするオープンプロトコルです。JSON-RPC 2.0を基盤として、ステートフルな接続を維持しながら、AIアプリケーションが様々な外部リソースにアクセスできるように設計されています。

## 2. JSON-RPC 2.0メッセージフォーマット

MCPは、すべての通信にJSON-RPC 2.0仕様に従います。メッセージは3つのタイプに分類されます。

### 2.1 リクエストメッセージ

```json
{
  "jsonrpc": "2.0",
  "method": "method_name",
  "params": {
    // メソッド固有のパラメータ
  },
  "id": "unique_request_id"
}
```

### 2.2 レスポンスメッセージ（成功）

```json
{
  "jsonrpc": "2.0",
  "result": {
    // メソッドの実行結果
  },
  "id": "unique_request_id"
}
```

### 2.3 レスポンスメッセージ（エラー）

```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32000,
    "message": "エラーの説明",
    "data": {
      // 追加のエラー情報（オプション）
    }
  },
  "id": "unique_request_id"
}
```

### 2.4 通知メッセージ

```json
{
  "jsonrpc": "2.0",
  "method": "notification_method",
  "params": {
    // 通知のパラメータ
  }
}
```

## 3. 標準入出力でのメッセージフォーマット

MCPサーバーは標準入出力（stdin/stdout）を通じて通信を行います。メッセージは改行区切りで送信され、各メッセージは1行に収まっている必要があります。

### 3.1 基本的な通信パターン

**標準入力への送信例（クライアント → サーバー）:**
```json
{"jsonrpc": "2.0", "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}}, "id": 1}
```

**標準出力からの受信例（サーバー → クライアント）:**
```json
{"jsonrpc": "2.0", "result": {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}}, "id": 1}
```

### 3.2 具体的なメッセージ例

**初期化リクエスト:**
```json
{
  "jsonrpc": "2.0",
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "tools": {},
      "resources": {}
    },
    "clientInfo": {
      "name": "my-chat-app",
      "version": "1.0.0"
    }
  },
  "id": 1
}
```

**ツール呼び出しリクエスト:**
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "search_tool",
    "arguments": {
      "query": "Python MCP implementation",
      "limit": 10
    }
  },
  "id": 2
}
```

**リソース読み取りリクエスト:**
```json
{
  "jsonrpc": "2.0",
  "method": "resources/read",
  "params": {
    "uri": "file:///path/to/document.txt"
  },
  "id": 3
}
```

## 4. Pythonパッケージ情報

### 4.1 公式Python SDK

調査の結果、MCPの公式Python SDKは `modelcontextprotocol/python-sdk` GitHubリポジトリで開発されていることが確認されました。PyPIでの `modelcontextprotocol` パッケージは、MCPとは異なるターミナルチャットインターフェースのようです。

### 4.2 推奨インストール方法

```bash
# 公式SDKの場合（GitHubから直接インストール）
pip install git+https://github.com/modelcontextprotocol/python-sdk.git

# または、個別のMCPサーバー実装を利用
pip install mcp-atlassian  # Atlassian統合
pip install playwright-mcp  # Playwright統合
```

### 4.3 基本的なインポート方法

```python
# 基本的なMCPクライアント/サーバー機能
from mcp import Client, Server
from mcp.types import Tool, Resource, TextContent

# JSON-RPC通信用
import json
import sys
import asyncio
```

## 5. Python実装例

### 5.1 基本的なMCPサーバー実装

```python
import asyncio
import json
import sys
from typing import Dict, Any, Optional

class MCPServer:
    def __init__(self):
        self.capabilities = {
            "tools": {},
            "resources": {}
        }
        self.tools = {}
        self.resources = {}
    
    async def handle_message(self, message: str) -> Optional[str]:
        """受信したJSON-RPCメッセージを処理"""
        try:
            data = json.loads(message.strip())
            
            # リクエストの場合
            if "method" in data and "id" in data:
                response = await self.handle_request(data)
                return json.dumps(response)
            
            # 通知の場合
            elif "method" in data:
                await self.handle_notification(data)
                return None
                
        except Exception as e:
            # エラーレスポンスを返す
            if "id" in data:
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": str(e)
                    },
                    "id": data["id"]
                }
                return json.dumps(error_response)
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """リクエストメソッドの処理"""
        method = request["method"]
        params = request.get("params", {})
        request_id = request["id"]
        
        if method == "initialize":
            return await self.initialize(params, request_id)
        elif method == "tools/list":
            return await self.list_tools(request_id)
        elif method == "tools/call":
            return await self.call_tool(params, request_id)
        else:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                },
                "id": request_id
            }
    
    async def initialize(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """初期化処理"""
        return {
            "jsonrpc": "2.0",
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": self.capabilities,
                "serverInfo": {
                    "name": "sample-mcp-server",
                    "version": "1.0.0"
                }
            },
            "id": request_id
        }
    
    async def list_tools(self, request_id: str) -> Dict[str, Any]:
        """利用可能なツールのリストを返す"""
        tools_list = [
            {
                "name": tool_name,
                "description": tool_info.get("description", ""),
                "inputSchema": tool_info.get("inputSchema", {})
            }
            for tool_name, tool_info in self.tools.items()
        ]
        
        return {
            "jsonrpc": "2.0",
            "result": {
                "tools": tools_list
            },
            "id": request_id
        }
    
    async def call_tool(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """ツールの実行"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name not in self.tools:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32602,
                    "message": f"Tool not found: {tool_name}"
                },
                "id": request_id
            }
        
        # ツールの実行ロジックをここに実装
        result = await self.execute_tool(tool_name, arguments)
        
        return {
            "jsonrpc": "2.0",
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": str(result)
                    }
                ]
            },
            "id": request_id
        }
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """ツールの実際の実行処理"""
        # ここに実際のツール実行ロジックを実装
        return f"Tool {tool_name} executed with arguments: {arguments}"
    
    async def handle_notification(self, notification: Dict[str, Any]):
        """通知メッセージの処理"""
        pass
    
    def register_tool(self, name: str, description: str, input_schema: Dict[str, Any]):
        """ツールの登録"""
        self.tools[name] = {
            "description": description,
            "inputSchema": input_schema
        }
        self.capabilities["tools"][name] = True
    
    async def run(self):
        """メインループ：標準入力からメッセージを読み取り、標準出力に応答を送信"""
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                
                response = await self.handle_message(line)
                if response:
                    print(response, flush=True)
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                # エラーログを標準エラー出力に送信
                print(f"Error: {e}", file=sys.stderr)

# 使用例
async def main():
    server = MCPServer()
    
    # サンプルツールの登録
    server.register_tool(
        name="search",
        description="テキスト検索を実行します",
        input_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "検索クエリ"
                },
                "limit": {
                    "type": "integer",
                    "description": "結果の最大数"
                }
            },
            "required": ["query"]
        }
    )
    
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())
```

### 5.2 基本的なMCPクライアント実装

```python
import asyncio
import json
import subprocess
import uuid
from typing import Dict, Any, Optional

class MCPClient:
    def __init__(self, server_command: list):
        self.server_command = server_command
        self.process = None
        self.request_id_counter = 0
    
    async def start_server(self):
        """MCPサーバープロセスを開始"""
        self.process = await asyncio.create_subprocess_exec(
            *self.server_command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
    
    def generate_request_id(self) -> str:
        """ユニークなリクエストIDを生成"""
        self.request_id_counter += 1
        return str(self.request_id_counter)
    
    async def send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """リクエストを送信して応答を受信"""
        request_id = self.generate_request_id()
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "id": request_id
        }
        
        if params:
            request["params"] = params
        
        # リクエストを送信
        request_json = json.dumps(request) + "\n"
        self.process.stdin.write(request_json.encode())
        await self.process.stdin.drain()
        
        # 応答を受信
        response_line = await self.process.stdout.readline()
        response = json.loads(response_line.decode().strip())
        
        return response
    
    async def initialize(self):
        """サーバーとの初期化"""
        params = {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
                "resources": {}
            },
            "clientInfo": {
                "name": "sample-mcp-client",
                "version": "1.0.0"
            }
        }
        
        response = await self.send_request("initialize", params)
        return response
    
    async def list_tools(self):
        """利用可能なツールの一覧を取得"""
        response = await self.send_request("tools/list")
        return response
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]):
        """ツールを呼び出し"""
        params = {
            "name": tool_name,
            "arguments": arguments
        }
        
        response = await self.send_request("tools/call", params)
        return response
    
    async def close(self):
        """サーバープロセスを終了"""
        if self.process:
            self.process.terminate()
            await self.process.wait()

# 使用例
async def main():
    client = MCPClient(["python", "mcp_server.py"])
    
    try:
        await client.start_server()
        
        # 初期化
        init_response = await client.initialize()
        print("初期化応答:", init_response)
        
        # ツール一覧の取得
        tools_response = await client.list_tools()
        print("利用可能なツール:", tools_response)
        
        # ツールの呼び出し
        tool_response = await client.call_tool(
            "search", 
            {"query": "Python", "limit": 5}
        )
        print("ツール実行結果:", tool_response)
        
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## 6. エラーハンドリングとベストプラクティス

### 6.1 エラーコード

MCPでは、JSON-RPC 2.0のエラーコードに加えて、プロトコル固有のエラーコードも定義されています。

- `-32700`: Parse error（パースエラー）
- `-32600`: Invalid Request（無効なリクエスト）
- `-32601`: Method not found（メソッドが見つからない）
- `-32602`: Invalid params（無効なパラメータ）
- `-32603`: Internal error（内部エラー）

### 6.2 実装時の注意点

MCPを実装する際は、以下の点に注意してください。

まず、メッセージは必ず改行区切りで送信し、各メッセージに埋め込み改行を含めてはいけません。これは標準入出力通信の基本的な制約です。

次に、すべてのリクエストには一意のIDを付与し、対応するレスポンスで同じIDを返すことで、非同期通信での応答の対応関係を明確にします。

エラーハンドリングでは、予期しない例外が発生した場合も適切なJSON-RPCエラーレスポンスを返すようにしましょう。

最後に、サーバーのログ出力は標準エラー出力（stderr）に送信し、標準出力（stdout）はJSON-RPCメッセージ専用として使い分けることが重要です。

## 7. まとめ

Model Context Protocol（MCP）は、LLMアプリケーションに外部ツールやデータソースを統合するための強力な仕組みです。JSON-RPC 2.0を基盤とし、標準入出力を通じた単純で効率的な通信方式を採用しています。

Pythonでの実装では、公式SDKの利用を検討しつつ、この文書で示したような基本的な構造を理解することで、独自のMCPサーバーやクライアントを構築できるようになります。特に、メッセージフォーマットの理解と適切なエラーハンドリングが、安定したMCP実装の鍵となります。