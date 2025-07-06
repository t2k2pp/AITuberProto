# 生成AIがMCPツールを認識・選択・実行する意思決定ロジックの実装

## 1. 全体の処理フローの理解

生成AIがMCPツールを活用する過程は、人間が作業を行う際の思考プロセスと似ています。まず「何が求められているか」を理解し、「どのツールが使えるか」を確認し、「最適なツールを選択」し、「実行して結果を確認」し、最後に「結果を踏まえた回答を作成」します。

この一連の流れを技術的に実装するには、AIモデルが各段階で適切な判断を下せるよう、明確な指示と判断基準を提供する必要があります。

### メッセージ処理の基本フロー

```javascript
class AIMessageProcessor {
  constructor(mcpManager, aiClient) {
    this.mcpManager = mcpManager;
    this.aiClient = aiClient; // OpenAI、Claude等のAPIクライアント
    this.toolExecutionHistory = [];
  }

  async processMessage(userMessage, conversationHistory = []) {
    // ステップ1: ユーザーメッセージの意図分析
    const intentAnalysis = await this.analyzeUserIntent(userMessage, conversationHistory);
    
    // ステップ2: 必要なツールの特定
    const requiredTools = await this.identifyRequiredTools(intentAnalysis);
    
    // ステップ3: ツールの実行計画作成
    const executionPlan = await this.createExecutionPlan(requiredTools, intentAnalysis);
    
    // ステップ4: ツールの順次実行
    const toolResults = await this.executeTools(executionPlan);
    
    // ステップ5: 結果を統合した最終応答の生成
    const finalResponse = await this.generateFinalResponse(
      userMessage, 
      toolResults, 
      conversationHistory
    );
    
    return finalResponse;
  }
}
```

## 2. ユーザー意図の分析と理解

AIがMCPツールを使うべきかどうかを判断する最初のステップは、ユーザーのメッセージから「実際の作業が必要かどうか」を見極めることです。これは単純なキーワードマッチングではなく、文脈を理解した上での判断が必要です。

### 意図分析の実装

```javascript
async analyzeUserIntent(userMessage, conversationHistory) {
  // AIモデルに意図分析を依頼するためのプロンプト
  const analysisPrompt = this.buildIntentAnalysisPrompt(userMessage, conversationHistory);
  
  const analysisResponse = await this.aiClient.complete({
    model: "gpt-4",
    messages: [
      {
        role: "system",
        content: `あなたは、ユーザーのメッセージを分析して、どのような作業が必要かを判断するアシスタントです。
        
利用可能なツールカテゴリ:
- ファイル操作 (読み取り、書き込み、検索)
- データベース操作 (検索、更新、集計)
- Web検索 (情報収集、リアルタイムデータ)
- 計算・分析 (数値計算、データ分析)
- システム情報 (時刻、環境情報)

以下のJSON形式で回答してください:
{
  "needsTools": boolean,
  "confidence": number (0-1),
  "requiredActions": ["action1", "action2"],
  "toolCategories": ["category1", "category2"],
  "reasoning": "判断理由の説明"
}`
      },
      {
        role: "user",
        content: analysisPrompt
      }
    ],
    temperature: 0.3 // 一貫した判断のため低めに設定
  });

  // レスポンスをパースして構造化データに変換
  return this.parseIntentAnalysis(analysisResponse);
}

buildIntentAnalysisPrompt(userMessage, conversationHistory) {
  let prompt = `ユーザメッセージ: "${userMessage}"\n\n`;
  
  if (conversationHistory.length > 0) {
    prompt += `会話履歴:\n`;
    conversationHistory.slice(-3).forEach((msg, index) => {
      prompt += `${msg.role}: ${msg.content}\n`;
    });
    prompt += `\n`;
  }
  
  prompt += `このメッセージを分析して、実際の作業（ファイル操作、データ検索、計算等）が必要かどうかを判断してください。`;
  
  return prompt;
}
```

### 意図分析の具体例

実際のユーザーメッセージに対してAIがどのような分析を行うかを見てみましょう。

```javascript
// 例1: ファイル操作が必要なケース
const userMessage1 = "昨日保存したレポートファイルの内容を確認して、売上データの部分を教えて";

// AIの分析結果:
{
  "needsTools": true,
  "confidence": 0.9,
  "requiredActions": ["file_search", "file_read", "content_extraction"],
  "toolCategories": ["file_operations"],
  "reasoning": "ユーザーは特定のファイルの内容確認と、その中から特定情報の抽出を求めている"
}

// 例2: 一般的な質問のケース
const userMessage2 = "機械学習の基本的な概念について教えて";

// AIの分析結果:
{
  "needsTools": false,
  "confidence": 0.95,
  "requiredActions": ["explain_concept"],
  "toolCategories": [],
  "reasoning": "一般的な知識の説明であり、外部ツールは不要"
}
```

## 3. 利用可能ツールの発見と選択

意図分析でツールが必要だと判断された場合、次のステップは「どのツールが利用可能で、どれを使うべきか」を決定することです。これは動的に行われる必要があります。なぜなら、MCPサーバーの状態や利用可能性は実行時に変わる可能性があるからです。

### ツール発見と選択のロジック

```javascript
async identifyRequiredTools(intentAnalysis) {
  if (!intentAnalysis.needsTools) {
    return { tools: [], strategy: "no_tools_needed" };
  }

  // 現在利用可能な全ツールを取得
  const availableTools = await this.mcpManager.getAllAvailableTools();
  
  // AIに最適なツールの選択を依頼
  const toolSelectionPrompt = this.buildToolSelectionPrompt(
    intentAnalysis, 
    availableTools
  );
  
  const toolSelectionResponse = await this.aiClient.complete({
    model: "gpt-4",
    messages: [
      {
        role: "system",
        content: `あなたは、与えられたタスクに最適なツールを選択する専門家です。
        
利用可能なツールの情報を基に、タスクを完了するために必要なツールとその使用順序を決定してください。

回答は以下のJSON形式で行ってください:
{
  "selectedTools": [
    {
      "toolName": "ツール名",
      "purpose": "使用目的",
      "priority": 実行優先度(1-10),
      "expectedInput": "想定される入力パラメータ"
    }
  ],
  "executionStrategy": "sequential|parallel",
  "reasoning": "選択理由"
}`
      },
      {
        role: "user", 
        content: toolSelectionPrompt
      }
    ],
    temperature: 0.2
  });

  return this.parseToolSelection(toolSelectionResponse);
}

buildToolSelectionPrompt(intentAnalysis, availableTools) {
  let prompt = `分析されたユーザー意図:\n`;
  prompt += `- 必要なアクション: ${intentAnalysis.requiredActions.join(', ')}\n`;
  prompt += `- ツールカテゴリ: ${intentAnalysis.toolCategories.join(', ')}\n`;
  prompt += `- 判断理由: ${intentAnalysis.reasoning}\n\n`;
  
  prompt += `利用可能なツール一覧:\n`;
  availableTools.forEach(tool => {
    prompt += `- ${tool.name}: ${tool.description}\n`;
    prompt += `  入力スキーマ: ${JSON.stringify(tool.inputSchema, null, 2)}\n`;
  });
  
  return prompt;
}
```

## 4. ツール実行計画の作成と実行

適切なツールが選択されたら、次は「どの順序で、どのような入力で実行するか」を計画し、実際に実行します。ここでは、ツール間の依存関係や、エラーが発生した場合の回復戦略も考慮する必要があります。

### 実行計画の作成

```javascript
async createExecutionPlan(toolSelection, intentAnalysis) {
  const executionPlan = {
    steps: [],
    fallbackStrategies: [],
    maxRetries: 3
  };

  // 選択されたツールを優先度順にソート
  const sortedTools = toolSelection.selectedTools.sort((a, b) => a.priority - b.priority);

  for (const tool of sortedTools) {
    // 各ツールの実行に必要なパラメータを生成
    const parameters = await this.generateToolParameters(tool, intentAnalysis);
    
    executionPlan.steps.push({
      toolName: tool.toolName,
      parameters: parameters,
      purpose: tool.purpose,
      dependsOn: this.identifyDependencies(tool, executionPlan.steps),
      errorHandling: this.defineErrorHandling(tool)
    });
  }

  return executionPlan;
}

async generateToolParameters(tool, intentAnalysis) {
  // AIに具体的なパラメータ生成を依頼
  const parameterPrompt = `
ツール: ${tool.toolName}
用途: ${tool.purpose}
入力スキーマ: ${JSON.stringify(tool.expectedInput)}
ユーザーの要求: ${intentAnalysis.reasoning}

このツールを実行するための具体的なパラメータをJSON形式で生成してください。
`;

  const parameterResponse = await this.aiClient.complete({
    model: "gpt-4",
    messages: [
      { role: "system", content: "ツール実行に必要なパラメータを正確に生成してください。" },
      { role: "user", content: parameterPrompt }
    ],
    temperature: 0.1
  });

  return JSON.parse(parameterResponse);
}
```

### ツールの実際の実行

```javascript
async executeTools(executionPlan) {
  const results = [];
  const context = new Map(); // 実行結果を後続のツールで利用するため

  for (const step of executionPlan.steps) {
    try {
      // 依存関係のチェック
      if (step.dependsOn.length > 0) {
        await this.waitForDependencies(step.dependsOn, results);
      }

      // パラメータに前のステップの結果を反映
      const enrichedParameters = this.enrichParametersWithContext(
        step.parameters, 
        context
      );

      console.log(`ツール実行開始: ${step.toolName}`);
      const startTime = Date.now();

      // 実際のツール実行
      const result = await this.mcpManager.executeTool(
        step.toolName, 
        enrichedParameters
      );

      const executionTime = Date.now() - startTime;
      
      // 結果をコンテキストに保存
      context.set(step.toolName, result);
      
      results.push({
        step: step,
        result: result,
        executionTime: executionTime,
        success: true
      });

      console.log(`ツール実行完了: ${step.toolName} (${executionTime}ms)`);

    } catch (error) {
      console.error(`ツール実行エラー: ${step.toolName}`, error);
      
      // エラーハンドリング戦略の実行
      const recoveryResult = await this.handleToolExecutionError(
        step, 
        error, 
        executionPlan
      );
      
      results.push({
        step: step,
        result: null,
        error: error,
        recovery: recoveryResult,
        success: false
      });
    }
  }

  return results;
}

async handleToolExecutionError(step, error, executionPlan) {
  // エラーの種類に応じた回復戦略
  if (error.message.includes('file not found')) {
    // ファイルが見つからない場合の代替手段
    return await this.tryAlternativeFileSearch(step.parameters);
  } else if (error.message.includes('permission denied')) {
    // 権限エラーの場合の対処
    return await this.requestPermissionEscalation(step);
  } else if (error.message.includes('timeout')) {
    // タイムアウトの場合のリトライ
    return await this.retryWithTimeout(step, executionPlan.maxRetries);
  }

  // その他のエラーは上位に委譲
  throw error;
}
```

## 5. 結果の統合と最終応答の生成

すべてのツールの実行が完了したら、その結果を統合してユーザーに分かりやすい形で応答を生成します。これは単純にツールの出力をそのまま返すのではなく、ユーザーの元の質問に対する適切な回答として整理する必要があります。

### 結果統合のロジック

```javascript
async generateFinalResponse(userMessage, toolResults, conversationHistory) {
  // ツール実行結果の要約作成
  const resultSummary = this.summarizeToolResults(toolResults);
  
  // 最終応答生成のためのプロンプト構築
  const responsePrompt = this.buildFinalResponsePrompt(
    userMessage,
    resultSummary,
    conversationHistory
  );

  const finalResponse = await this.aiClient.complete({
    model: "gpt-4",
    messages: [
      {
        role: "system",
        content: `あなたは、ツールの実行結果を基にユーザーの質問に回答するアシスタントです。

重要な指針:
1. ツールの生の出力をそのまま返すのではなく、ユーザーの質問に対する適切な回答として整理する
2. 複数のツールを使用した場合は、結果を統合して一貫した回答を作成する
3. ツールの実行に失敗した場合は、その旨を適切に説明し、代替案があれば提案する
4. 技術的な詳細は適度に省略し、ユーザーにとって有用な情報を重点的に伝える`
      },
      {
        role: "user",
        content: responsePrompt
      }
    ],
    temperature: 0.7 // 自然な応答のため適度な創造性を許可
  });

  return {
    response: finalResponse,
    toolsUsed: toolResults.map(r => r.step.toolName),
    executionSummary: resultSummary,
    metadata: {
      totalExecutionTime: toolResults.reduce((sum, r) => sum + (r.executionTime || 0), 0),
      successfulTools: toolResults.filter(r => r.success).length,
      failedTools: toolResults.filter(r => !r.success).length
    }
  };
}

summarizeToolResults(toolResults) {
  return toolResults.map(result => {
    if (result.success) {
      return {
        tool: result.step.toolName,
        purpose: result.step.purpose,
        success: true,
        summary: this.extractResultSummary(result.result),
        data: result.result.data
      };
    } else {
      return {
        tool: result.step.toolName,
        purpose: result.step.purpose,
        success: false,
        error: result.error.message,
        recovery: result.recovery
      };
    }
  });
}

buildFinalResponsePrompt(userMessage, resultSummary, conversationHistory) {
  let prompt = `ユーザーの質問: "${userMessage}"\n\n`;
  
  if (conversationHistory.length > 0) {
    prompt += `会話の文脈:\n`;
    conversationHistory.slice(-2).forEach(msg => {
      prompt += `${msg.role}: ${msg.content}\n`;
    });
    prompt += `\n`;
  }

  prompt += `実行されたツールとその結果:\n`;
  resultSummary.forEach(summary => {
    prompt += `\nツール: ${summary.tool}\n`;
    prompt += `目的: ${summary.purpose}\n`;
    if (summary.success) {
      prompt += `結果: ${summary.summary}\n`;
    } else {
      prompt += `エラー: ${summary.error}\n`;
      if (summary.recovery) {
        prompt += `回復措置: ${summary.recovery}\n`;
      }
    }
  });

  prompt += `\n上記の結果を基に、ユーザーの質問に対する包括的で分かりやすい回答を作成してください。`;

  return prompt;
}
```

## 6. 実行例: 実際の処理フローの追跡

具体的な例を通して、全体の流れがどのように動作するかを見てみましょう。

### シナリオ: レポートファイルの分析依頼

```javascript
// ユーザーメッセージ
const userMessage = "今月の売上レポートファイルを読んで、先月と比較して増減を教えて";

// ステップ1: 意図分析の結果
const intentAnalysis = {
  needsTools: true,
  confidence: 0.92,
  requiredActions: ["file_search", "file_read", "data_comparison", "calculation"],
  toolCategories: ["file_operations", "data_analysis"],
  reasoning: "レポートファイルの読み取りと、データの比較分析が必要"
};

// ステップ2: ツール選択の結果
const toolSelection = {
  selectedTools: [
    {
      toolName: "file_search",
      purpose: "今月の売上レポートファイルを検索",
      priority: 1,
      expectedInput: { pattern: "*売上*", timeframe: "current_month" }
    },
    {
      toolName: "file_read", 
      purpose: "見つかったファイルの内容を読み取り",
      priority: 2,
      expectedInput: { path: "{{file_search.result}}" }
    },
    {
      toolName: "data_analysis",
      purpose: "売上データの抽出と前月比較",
      priority: 3,
      expectedInput: { data: "{{file_read.content}}", analysis_type: "month_comparison" }
    }
  ],
  executionStrategy: "sequential"
};

// ステップ3: 実際の実行結果
const executionResults = [
  {
    step: { toolName: "file_search" },
    result: { data: ["/reports/sales_2024_03.xlsx"] },
    success: true,
    executionTime: 150
  },
  {
    step: { toolName: "file_read" },
    result: { data: "売上データの内容..." },
    success: true,
    executionTime: 300
  },
  {
    step: { toolName: "data_analysis" },
    result: { 
      data: {
        current_month: 1500000,
        previous_month: 1200000,
        change: 300000,
        change_percent: 25
      }
    },
    success: true,
    executionTime: 500
  }
];

// ステップ4: 最終応答
const finalResponse = {
  response: `今月の売上レポートを分析した結果、以下のことが分かりました：

今月の売上: 1,500,000円
先月の売上: 1,200,000円
増減額: +300,000円（25%増）

先月と比較して売上が大幅に増加しています。これは非常に良い傾向ですね。`,
  toolsUsed: ["file_search", "file_read", "data_analysis"],
  metadata: {
    totalExecutionTime: 950,
    successfulTools: 3,
    failedTools: 0
  }
};
```

## 7. エラー処理と学習機能

実際の運用では、ツールの実行が常に成功するとは限りません。AIシステムが失敗から学習し、将来的により良い判断を下せるようになる仕組みも重要です。

### 学習機能の実装

```javascript
class MCPLearningSystem {
  constructor() {
    this.executionHistory = [];
    this.patternLearning = new Map();
  }

  recordExecution(userMessage, intentAnalysis, toolSelection, results) {
    const record = {
      timestamp: new Date(),
      userMessage,
      intentAnalysis,
      toolSelection,
      results,
      success: results.every(r => r.success),
      totalTime: results.reduce((sum, r) => sum + (r.executionTime || 0), 0)
    };

    this.executionHistory.push(record);
    this.updatePatterns(record);
  }

  updatePatterns(record) {
    // 成功パターンの学習
    if (record.success) {
      const pattern = this.extractPattern(record);
      const existing = this.patternLearning.get(pattern.key) || { count: 0, avgTime: 0 };
      
      existing.count++;
      existing.avgTime = (existing.avgTime * (existing.count - 1) + record.totalTime) / existing.count;
      existing.lastUsed = record.timestamp;
      
      this.patternLearning.set(pattern.key, existing);
    }
  }

  // 過去の成功例から最適なツール選択を提案
  suggestOptimalTools(intentAnalysis) {
    const similarPatterns = this.findSimilarPatterns(intentAnalysis);
    
    return similarPatterns
      .sort((a, b) => b.successRate - a.successRate)
      .slice(0, 3)
      .map(pattern => ({
        tools: pattern.tools,
        confidence: pattern.successRate,
        averageTime: pattern.avgTime
      }));
  }
}
```

この実装により、生成AIがユーザーのメッセージを受け取ってから、適切なMCPツールを選択・実行し、結果を統合した回答を返すまでの全プロセスが明確になります。重要なのは、各ステップでAIが適切な判断を下せるよう、十分な情報と明確な指示を提供することです。

また、実際の運用では失敗例からの学習機能も重要で、システムが使われるほど精度が向上する仕組みを組み込むことで、より実用的なアシスタントとして成長させることができます。