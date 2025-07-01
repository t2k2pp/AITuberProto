# 生成AIチャットアプリにMCP機能を追加するための実装ガイド

## 1. MCPとは何か - 基本概念の理解

### Model Context Protocol (MCP)の基本思想

MCPは、AI言語モデルが外部のデータソースやツールと安全かつ標準的な方法で接続するためのプロトコルです。従来は各アプリケーションが独自の方法で外部連携を行っていましたが、MCPは統一された仕様を提供します。

### なぜMCPが必要なのか

チャットアプリが単なる会話だけでなく、ファイルの読み書き、データベース検索、API呼び出しなどの実際の作業を行えるようになるためです。MCPを使用することで、これらの機能を安全で管理しやすい形で追加できます。

## 2. MCPの全体アーキテクチャ

### 主要な構成要素

```
[チャットアプリ] ←→ [MCPクライアント] ←→ [MCPサーバー] ←→ [外部リソース]
     (UI)              (仲介役)           (実行環境)      (DB, API等)
```

この構造を理解することが重要です。チャットアプリは直接外部リソースにアクセスするのではなく、MCPクライアントを通じてMCPサーバーと通信し、サーバーが実際の作業を行います。

### プロトコルの動作原理

MCPは双方向の通信プロトコルです。クライアントがサーバーに「何ができるか」を問い合わせ、サーバーが利用可能なツールやリソースの一覧を返答します。その後、実際の操作要求と結果のやり取りが行われます。

## 3. 実装の準備段階

### 必要な依存関係

```javascript
// package.jsonに追加する主要な依存関係
{
  "dependencies": {
    "@modelcontextprotocol/sdk": "^0.4.0",
    "ws": "^8.0.0",
    "node-fetch": "^3.0.0"
  }
}
```

### 開発環境の設定

プロジェクトの構造を整理することから始めます。MCPクライアントとサーバーの両方を扱うため、明確なディレクトリ構造が重要です。

```
project/
├── src/
│   ├── mcp/
│   │   ├── client/     # MCPクライアント実装
│   │   └── servers/    # MCPサーバー実装
│   ├── chat/           # チャットアプリのUI
│   └── utils/          # 共通ユーティリティ
```

## 4. MCPクライアントの実装

### 基本的なクライアントクラス

```javascript
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

class MCPClientManager {
  constructor() {
    this.clients = new Map(); // 複数のMCPサーバーを管理
    this.availableTools = new Map();
    this.availableResources = new Map();
  }

  // MCPサーバーへの接続を確立
  async connectToServer(serverName, serverConfig) {
    try {
      // トランスポート層の設定（サーバーとの通信方法）
      const transport = new StdioClientTransport({
        command: serverConfig.command,
        args: serverConfig.args,
        env: serverConfig.env
      });

      // クライアントインスタンスの作成
      const client = new Client({
        name: `chat-app-${serverName}`,
        version: "1.0.0"
      }, {
        capabilities: {
          tools: {}, // ツール使用の許可
          resources: {} // リソースアクセスの許可
        }
      });

      // 接続の開始
      await client.connect(transport);
      
      // サーバーの能力を取得
      await this.discoverServerCapabilities(client, serverName);
      
      this.clients.set(serverName, client);
      console.log(`MCPサーバー "${serverName}" に正常に接続しました`);
      
    } catch (error) {
      console.error(`MCPサーバー接続エラー: ${error.message}`);
      throw error;
    }
  }

  // サーバーが提供する機能を発見
  async discoverServerCapabilities(client, serverName) {
    // 利用可能なツールを取得
    const toolsResponse = await client.listTools();
    if (toolsResponse.tools) {
      toolsResponse.tools.forEach(tool => {
        this.availableTools.set(`${serverName}:${tool.name}`, {
          serverName,
          ...tool
        });
      });
    }

    // 利用可能なリソースを取得
    const resourcesResponse = await client.listResources();
    if (resourcesResponse.resources) {
      resourcesResponse.resources.forEach(resource => {
        this.availableResources.set(`${serverName}:${resource.uri}`, {
          serverName,
          ...resource
        });
      });
    }
  }

  // ツールの実行
  async executeTool(toolName, parameters) {
    const tool = this.availableTools.get(toolName);
    if (!tool) {
      throw new Error(`ツール "${toolName}" が見つかりません`);
    }

    const client = this.clients.get(tool.serverName);
    if (!client) {
      throw new Error(`サーバー "${tool.serverName}" が接続されていません`);
    }

    try {
      const result = await client.callTool({
        name: tool.name,
        arguments: parameters
      });
      
      return this.processToolResult(result);
    } catch (error) {
      console.error(`ツール実行エラー: ${error.message}`);
      throw error;
    }
  }

  // ツール実行結果の処理
  processToolResult(result) {
    // 結果の形式を統一し、エラーハンドリングを行う
    if (result.content) {
      return {
        success: true,
        data: result.content,
        metadata: result.metadata || {}
      };
    } else if (result.error) {
      throw new Error(result.error);
    }
    
    return { success: true, data: result };
  }
}
```

### チャットアプリとの統合

```javascript
class ChatApp {
  constructor() {
    this.mcpManager = new MCPClientManager();
    this.conversationHistory = [];
  }

  async initialize() {
    // 設定ファイルからMCPサーバーの情報を読み込み
    const mcpConfig = await this.loadMCPConfiguration();
    
    // 各サーバーに接続
    for (const [serverName, config] of Object.entries(mcpConfig.servers)) {
      await this.mcpManager.connectToServer(serverName, config);
    }
  }

  async processUserMessage(userMessage) {
    // ユーザーのメッセージを解析し、MCP機能が必要かを判断
    const analysisResult = await this.analyzeMessageForMCPNeeds(userMessage);
    
    if (analysisResult.needsMCP) {
      // MCP機能を使用した処理
      return await this.handleMCPMessage(userMessage, analysisResult);
    } else {
      // 通常のチャット処理
      return await this.handleRegularMessage(userMessage);
    }
  }

  async handleMCPMessage(userMessage, analysisResult) {
    try {
      // 必要なツールを実行
      const toolResults = [];
      for (const toolCall of analysisResult.toolCalls) {
        const result = await this.mcpManager.executeTool(
          toolCall.name, 
          toolCall.parameters
        );
        toolResults.push(result);
      }

      // AI言語モデルに結果を含めて応答生成を依頼
      const aiResponse = await this.generateAIResponse(
        userMessage, 
        toolResults
      );
      
      return aiResponse;
      
    } catch (error) {
      return this.handleMCPError(error);
    }
  }
}
```

## 5. MCPサーバーの実装

### カスタムMCPサーバーの作成

特定の用途向けのMCPサーバーを作成することで、チャットアプリの機能を拡張できます。

```javascript
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';

class FileSystemMCPServer {
  constructor() {
    this.server = new Server({
      name: "filesystem-server",
      version: "1.0.0"
    }, {
      capabilities: {
        tools: {
          // このサーバーが提供するツールの種類
          listSupported: true
        },
        resources: {
          // このサーバーが管理するリソースの種類
          subscribe: true,
          listChanged: true
        }
      }
    });

    this.setupToolHandlers();
    this.setupResourceHandlers();
  }

  setupToolHandlers() {
    // ファイル読み取りツール
    this.server.setRequestHandler('tools/call', async (request) => {
      const { name, arguments: args } = request.params;

      switch (name) {
        case 'read_file':
          return await this.handleReadFile(args);
        case 'write_file':
          return await this.handleWriteFile(args);
        case 'list_directory':
          return await this.handleListDirectory(args);
        default:
          throw new Error(`未知のツール: ${name}`);
      }
    });

    // 利用可能なツールの一覧を提供
    this.server.setRequestHandler('tools/list', async () => {
      return {
        tools: [
          {
            name: 'read_file',
            description: 'ファイルの内容を読み取ります',
            inputSchema: {
              type: 'object',
              properties: {
                path: {
                  type: 'string',
                  description: '読み取るファイルのパス'
                }
              },
              required: ['path']
            }
          },
          {
            name: 'write_file',
            description: 'ファイルに内容を書き込みます',
            inputSchema: {
              type: 'object',
              properties: {
                path: { type: 'string', description: 'ファイルパス' },
                content: { type: 'string', description: '書き込む内容' }
              },
              required: ['path', 'content']
            }
          }
        ]
      };
    });
  }

  async handleReadFile(args) {
    try {
      const fs = await import('fs/promises');
      const content = await fs.readFile(args.path, 'utf-8');
      
      return {
        content: [{
          type: 'text',
          text: content
        }]
      };
    } catch (error) {
      throw new Error(`ファイル読み取りエラー: ${error.message}`);
    }
  }

  async handleWriteFile(args) {
    try {
      const fs = await import('fs/promises');
      await fs.writeFile(args.path, args.content, 'utf-8');
      
      return {
        content: [{
          type: 'text',
          text: `ファイル "${args.path}" に正常に書き込みました`
        }]
      };
    } catch (error) {
      throw new Error(`ファイル書き込みエラー: ${error.message}`);
    }
  }

  async start() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.log('FileSystem MCPサーバーが開始されました');
  }
}

// サーバーの起動
const server = new FileSystemMCPServer();
server.start().catch(console.error);
```

## 6. セキュリティとエラーハンドリング

### セキュリティ考慮事項

MCPを実装する際は、セキュリティが最重要です。外部システムへのアクセスを許可するため、適切な制限と検証が必要です。

```javascript
class SecureMCPManager {
  constructor() {
    this.allowedPaths = ['/safe/directory', '/public/files'];
    this.blockedCommands = ['rm', 'del', 'format', 'sudo'];
    this.rateLimiter = new Map();
  }

  // パス検証
  validatePath(path) {
    const normalizedPath = path.normalize(path);
    
    // パストラバーサル攻撃の防止
    if (normalizedPath.includes('..')) {
      throw new Error('不正なパスが検出されました');
    }

    // 許可されたディレクトリ内かチェック
    const isAllowed = this.allowedPaths.some(allowedPath => 
      normalizedPath.startsWith(allowedPath)
    );
    
    if (!isAllowed) {
      throw new Error('アクセス権限がありません');
    }

    return normalizedPath;
  }

  // レート制限
  checkRateLimit(clientId) {
    const now = Date.now();
    const clientRequests = this.rateLimiter.get(clientId) || [];
    
    // 1分以内のリクエストをフィルタ
    const recentRequests = clientRequests.filter(
      time => now - time < 60000
    );
    
    if (recentRequests.length >= 100) {
      throw new Error('レート制限に達しました');
    }

    recentRequests.push(now);
    this.rateLimiter.set(clientId, recentRequests);
  }
}
```

### エラーハンドリング戦略

```javascript
class RobustMCPClient {
  async executeToolWithRetry(toolName, parameters, maxRetries = 3) {
    let lastError;
    
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        return await this.mcpManager.executeTool(toolName, parameters);
      } catch (error) {
        lastError = error;
        
        if (this.isRetryableError(error) && attempt < maxRetries) {
          const delay = Math.pow(2, attempt) * 1000; // 指数バックオフ
          await this.sleep(delay);
          continue;
        }
        
        break;
      }
    }

    // 全ての試行が失敗した場合
    throw new Error(`ツール実行失敗 (${maxRetries}回試行): ${lastError.message}`);
  }

  isRetryableError(error) {
    // 一時的なエラーかどうかを判定
    const retryableMessages = [
      'connection timeout',
      'server temporarily unavailable',
      'rate limit'
    ];
    
    return retryableMessages.some(msg => 
      error.message.toLowerCase().includes(msg)
    );
  }
}
```

## 7. 設定管理とデプロイメント

### 設定ファイルの構造

```json
{
  "mcp": {
    "servers": {
      "filesystem": {
        "command": "node",
        "args": ["./mcp-servers/filesystem-server.js"],
        "env": {
          "SAFE_DIRECTORY": "/app/safe"
        }
      },
      "database": {
        "command": "python",
        "args": ["./mcp-servers/database-server.py"],
        "env": {
          "DB_CONNECTION": "postgresql://localhost/mydb"
        }
      }
    },
    "security": {
      "maxConcurrentConnections": 10,
      "requestTimeout": 30000,
      "allowedOrigins": ["https://myapp.com"]
    }
  }
}
```

### Docker環境での実行

```dockerfile
# Dockerfile example
FROM node:18-alpine
WORKDIR /app

# MCPサーバーの依存関係をインストール
COPY package*.json ./
RUN npm install

# アプリケーションファイルをコピー
COPY . .

# セキュリティのため専用ユーザーを作成
RUN addgroup -g 1001 -S mcpuser && \
    adduser -S mcpuser -u 1001

USER mcpuser

# ポートを公開
EXPOSE 3000

CMD ["node", "server.js"]
```

## 8. テストとデバッグ

### MCPクライアントのテスト

```javascript
describe('MCPクライアント', () => {
  let mcpManager;

  beforeEach(async () => {
    mcpManager = new MCPClientManager();
    // テスト用のモックサーバーに接続
    await mcpManager.connectToServer('test-server', {
      command: 'node',
      args: ['./test/mock-server.js']
    });
  });

  test('ツールの実行が正常に動作する', async () => {
    const result = await mcpManager.executeTool(
      'test-server:echo',
      { message: 'Hello MCP' }
    );

    expect(result.success).toBe(true);
    expect(result.data).toContain('Hello MCP');
  });

  test('無効なツール名でエラーが発生する', async () => {
    await expect(
      mcpManager.executeTool('invalid-tool', {})
    ).rejects.toThrow('ツール "invalid-tool" が見つかりません');
  });
});
```

## 9. 運用とモニタリング

### パフォーマンス監視

```javascript
class MCPMetrics {
  constructor() {
    this.metrics = {
      toolCalls: 0,
      errors: 0,
      averageResponseTime: 0,
      activeConnections: 0
    };
  }

  async recordToolCall(toolName, executionTime, success) {
    this.metrics.toolCalls++;
    
    if (!success) {
      this.metrics.errors++;
    }

    // 移動平均でレスポンス時間を更新
    this.metrics.averageResponseTime = 
      (this.metrics.averageResponseTime * 0.9) + (executionTime * 0.1);

    // メトリクスを外部システムに送信（例：Prometheus）
    await this.sendMetrics();
  }
}
```

## まとめ

MCP機能をチャットアプリに統合することで、単純な会話から実際の作業を行えるアシスタントへと進化させることができます。重要なポイントは、セキュリティを最優先に考え、段階的に機能を追加していくことです。

実装を始める際は、まず簡単なファイルシステムサーバーから始めて、動作を確認してから他の機能を追加することをお勧めします。また、本番環境では適切なログ記録、監視、エラーハンドリングが不可欠です。