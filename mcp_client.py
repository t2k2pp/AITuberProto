import asyncio
import json
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import logging

logger = logging.getLogger(__name__)

# MCP SDK のインポート（簡潔版）
MCP_SDK_AVAILABLE = False
ClientSession = None
stdio_client = None
StdioServerParameters = None

try:
    from mcp.client.session import ClientSession
    from mcp.client.stdio import stdio_client, StdioServerParameters
    from mcp.types import Tool, Resource
    MCP_SDK_AVAILABLE = True
    logger.info("Successfully imported MCP SDK classes.")
except ImportError as e:
    logger.warning(f"MCP SDK not available: {e}. Some MCP functionality will be limited.")
    
    # シンプルなモッククラス
    class MockClientSession:
        def __init__(self, *args, **kwargs):
            self.name = "mock-session"
            
        async def initialize(self):
            logger.info("Mock session initialized")
            
        async def list_tools(self):
            return [{"name": "mock_tool", "description": "Mock tool for testing"}]
            
        async def list_resources(self):
            return []
            
        async def call_tool(self, tool_name: str, arguments: Dict[str, Any]):
            return {"content": [{"type": "text", "text": f"Mock result for {tool_name}"}]}
            
        async def close(self):
            logger.info("Mock session closed")
    
    class MockStdioServerParameters:
        def __init__(self, command: str, args: List[str], env: Optional[Dict[str, str]] = None):
            self.command = command
            self.args = args
            self.env = env or {}
    
    class MockStdioClient:
        def __init__(self, params):
            self.params = params
            
        async def __aenter__(self):
            return None, None  # read_stream, write_stream
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
    
    ClientSession = MockClientSession
    StdioServerParameters = MockStdioServerParameters
    stdio_client = MockStdioClient

class MCPClientManager:
    def __init__(self, config_manager: Optional[Any] = None):
        self.sessions: Dict[str, Any] = {}
        self.stdio_contexts: Dict[str, Any] = {}  # 旧形式、互換性のため保持
        self.exit_stacks: Dict[str, Any] = {}  # AsyncExitStack の管理（公式パターン）
        self.available_tools: Dict[str, Any] = {}
        self.available_resources: Dict[str, Any] = {}
        self.config_manager = config_manager

    def _resolve_server_script_path(self, command: str, raw_args: List[str]) -> List[str]:
        # (このヘルパーメソッドは変更なし)
        processed_args = []
        if command == "python" and raw_args:
            script_path_arg = raw_args[0]
            try:
                project_root = Path(__file__).resolve().parent
                if script_path_arg.startswith('./'): script_path_arg = script_path_arg[2:]
                elif script_path_arg.startswith('.\\'): script_path_arg = script_path_arg[2:]
                absolute_script_path = (project_root / script_path_arg).resolve()
                if absolute_script_path.is_file():
                    processed_args.append(str(absolute_script_path))
                    processed_args.extend(raw_args[1:])
                    logger.info(f"Resolved server script path to: {absolute_script_path}")
                else:
                    logger.warning(f"Server script path '{script_path_arg}' (resolved to '{absolute_script_path}') does not exist or is not a file. Using raw args: {raw_args}")
                    processed_args = list(raw_args)
            except Exception as path_e:
                logger.error(f"Error resolving server script path '{script_path_arg}': {path_e}. Using raw args: {raw_args}", exc_info=True)
                processed_args = list(raw_args)
        else:
            processed_args = list(raw_args)
        return processed_args

    async def connect_to_server(self, server_name: str, server_config: Dict[str, Any]) -> None:
        if server_name in self.sessions:
            logger.info(f"MCPサーバー '{server_name}' は既に接続済みです。")
            return

        # 公式パターンに従って AsyncExitStack を使用
        from contextlib import AsyncExitStack
        
        try:
            command = server_config.get("command", "python")
            raw_args = server_config.get("args", [])
            env_config = server_config.get("env", {})

            # 引数を処理してスクリプトパスを解決
            processed_args = self._resolve_server_script_path(command, raw_args)
            
            if not processed_args:
                raise ValueError(f"サーバー '{server_name}' の設定が不正です。")

            # 環境変数を設定
            effective_env = os.environ.copy()
            effective_env.update(env_config)
            effective_env["PYTHONUNBUFFERED"] = "1"
            
            # プロジェクトルートをPYTHONPATHに追加
            project_root = str(Path(__file__).resolve().parent)
            pythonpath = effective_env.get("PYTHONPATH", "")
            if project_root not in pythonpath:
                effective_env["PYTHONPATH"] = f"{project_root}{os.pathsep}{pythonpath}".strip(os.pathsep)

            logger.info(f"Connecting to MCP server '{server_name}': {command} {' '.join(processed_args)}")

            # StdioServerParametersでサーバープロセスを設定
            server_params = StdioServerParameters(
                command=command,
                args=processed_args,
                env=effective_env
            )

            # 公式パターン: AsyncExitStack でリソース管理
            exit_stack = AsyncExitStack()
            self.exit_stacks[server_name] = exit_stack
            
            # stdio_client を AsyncExitStack で管理
            stdio_transport = await exit_stack.enter_async_context(stdio_client(server_params))
            read_stream, write_stream = stdio_transport
            
            # ClientSession を AsyncExitStack で管理
            session = await exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            
            # セッション初期化（公式パターン通り）
            logger.info(f"Initializing session for '{server_name}'...")
            await session.initialize()
            
            # サーバーの機能を発見
            await self._discover_server_capabilities(session, server_name)
            
            self.sessions[server_name] = session
            logger.info(f"MCPサーバー '{server_name}' に正常に接続しました。")

        except Exception as e:
            logger.error(f"MCPサーバー '{server_name}' への接続に失敗: {e}", exc_info=True)
            # AsyncExitStack のクリーンアップ
            if server_name in self.exit_stacks:
                try:
                    await self.exit_stacks[server_name].aclose()
                except Exception:
                    pass
                del self.exit_stacks[server_name]
            raise


    async def _discover_server_capabilities(self, session: Any, server_name: str) -> None:
        try:
            logger.info(f"Discovering capabilities for server '{server_name}'...")
            
            # ツール一覧を取得
            tools_response = await session.list_tools()
            logger.info(f"Tools response from '{server_name}': {tools_response}")
            
            if tools_response and hasattr(tools_response, 'tools'):
                tools_list = tools_response.tools
            elif isinstance(tools_response, list):
                tools_list = tools_response
            else:
                tools_list = []
            
            for tool in tools_list:
                if hasattr(tool, 'name'):
                    tool_id = f"{server_name}:{tool.name}"
                    self.available_tools[tool_id] = tool
                    description = getattr(tool, 'description', 'No description')
                    logger.info(f"Found tool: {tool_id} - {description}")
                elif isinstance(tool, dict) and 'name' in tool:
                    tool_id = f"{server_name}:{tool['name']}"
                    self.available_tools[tool_id] = tool
                    description = tool.get('description', 'No description')
                    logger.info(f"Found tool: {tool_id} - {description}")

            # リソース一覧を取得
            try:
                resources_response = await session.list_resources()
                logger.info(f"Resources response from '{server_name}': {resources_response}")
                
                if resources_response and hasattr(resources_response, 'resources'):
                    resources_list = resources_response.resources
                elif isinstance(resources_response, list):
                    resources_list = resources_response
                else:
                    resources_list = []
                
                for resource in resources_list:
                    if hasattr(resource, 'uri'):
                        resource_id = f"{server_name}:{resource.uri}"
                        self.available_resources[resource_id] = resource
                        logger.info(f"Found resource: {resource_id}")
                    elif isinstance(resource, dict) and 'uri' in resource:
                        resource_id = f"{server_name}:{resource['uri']}"
                        self.available_resources[resource_id] = resource
                        logger.info(f"Found resource: {resource_id}")
                        
            except Exception as e:
                logger.warning(f"Failed to list resources for '{server_name}': {e}")

        except Exception as e:
            logger.error(f"Error discovering capabilities for server '{server_name}': {e}", exc_info=True)

    async def execute_tool(self, tool_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        if tool_id not in self.available_tools:
            available = list(self.available_tools.keys())
            logger.error(f"Tool '{tool_id}' not found. Available tools: {available}")
            raise ValueError(f"Tool '{tool_id}' not found.")

        tool_obj = self.available_tools[tool_id]
        server_name = tool_id.split(":", 1)[0]
        
        # ツール名を取得
        if hasattr(tool_obj, 'name'):
            tool_name = tool_obj.name
        elif isinstance(tool_obj, dict) and 'name' in tool_obj:
            tool_name = tool_obj['name']
        else:
            raise ValueError(f"Cannot determine tool name for '{tool_id}'")

        session = self.sessions.get(server_name)
        if not session:
            raise ConnectionError(f"Server '{server_name}' is not connected.")

        try:
            logger.info(f"Executing tool '{tool_name}' with parameters: {parameters}")
            result = await session.call_tool(name=tool_name, arguments=parameters)
            logger.info(f"Tool execution result: {result}")
            return self._process_tool_result(result)
        except Exception as e:
            logger.error(f"Tool execution failed for '{tool_id}': {e}", exc_info=True)
            raise RuntimeError(f"Tool execution failed: {e}")

    def _process_tool_result(self, result: Any) -> Dict[str, Any]:
        """ツール実行結果を統一フォーマットに変換"""
        try:
            # エラーチェック
            if hasattr(result, 'isError') and result.isError:
                return {"success": False, "error": str(getattr(result, 'content', 'Unknown error'))}
            
            # content属性からデータを取得
            content_data = None
            if hasattr(result, 'content'):
                content_data = result.content
            elif isinstance(result, dict) and 'content' in result:
                content_data = result['content']
            elif isinstance(result, str):
                return {"success": True, "data": result}
            else:
                return {"success": True, "data": str(result)}

            # content_dataの処理
            if isinstance(content_data, list) and len(content_data) > 0:
                # 最初の要素からテキストを抽出
                first_item = content_data[0]
                if isinstance(first_item, dict) and 'text' in first_item:
                    processed_data = first_item['text']
                elif hasattr(first_item, 'text'):
                    processed_data = first_item.text
                else:
                    processed_data = str(first_item)
            elif isinstance(content_data, dict) and 'text' in content_data:
                processed_data = content_data['text']
            elif hasattr(content_data, 'text'):
                processed_data = content_data.text
            else:
                processed_data = str(content_data)

            return {
                "success": True,
                "data": processed_data,
                "metadata": getattr(result, 'metadata', {}) if hasattr(result, 'metadata') else {}
            }

        except Exception as e:
            logger.error(f"Error processing tool result: {e}")
            return {"success": False, "error": f"Result processing error: {e}"}

    async def initialize_servers_from_config(self) -> None:
        """設定からMCPサーバーを初期化"""
        if not self.config_manager:
            logger.warning("ConfigManager not available. Skipping MCP server initialization.")
            return
            
        mcp_config = self.config_manager.get_mcp_settings()
        if not mcp_config or "servers" not in mcp_config:
            logger.info("No MCP server configuration found.")
            return
            
        for server_name, server_settings in mcp_config["servers"].items():
            if isinstance(server_settings, dict) and server_settings.get("enabled", True):
                try:
                    await self.connect_to_server(server_name, server_settings)
                except Exception as e:
                    logger.error(f"Failed to initialize server '{server_name}': {e}", exc_info=True)
            else:
                logger.info(f"Server '{server_name}' is disabled or has invalid configuration.")

    async def shutdown(self) -> None:
        """全てのMCPセッションをシャットダウン（公式パターン対応）"""
        logger.info("Shutting down all MCP client sessions...")
        
        # 公式パターン: AsyncExitStack を閉じる
        for server_name, exit_stack in list(self.exit_stacks.items()):
            try:
                # AsyncExitStack の aclose でリソース全体をクリーンアップ
                await asyncio.wait_for(exit_stack.aclose(), timeout=10.0)
                logger.info(f"Resources for server '{server_name}' closed successfully.")
            except asyncio.TimeoutError:
                logger.warning(f"Timeout closing resources for server '{server_name}'")
            except (Exception, BaseExceptionGroup) as e:
                # TaskGroupエラーを含む全ての例外を捕捉
                if "TaskGroup" in str(type(e)) or "unhandled errors" in str(e):
                    logger.warning(f"TaskGroup cleanup error for server '{server_name}' (safely ignored)")
                else:
                    logger.error(f"Error closing resources for server '{server_name}': {e}")
            finally:
                # 参照を削除
                if server_name in self.exit_stacks:
                    del self.exit_stacks[server_name]
                if server_name in self.sessions:
                    del self.sessions[server_name]

        # 旧形式のstdio contextsがあれば閉じる（互換性）
        for server_name, stdio_context in list(self.stdio_contexts.items()):
            try:
                await asyncio.wait_for(
                    stdio_context.__aexit__(None, None, None), 
                    timeout=5.0
                )
                logger.info(f"Legacy stdio context for server '{server_name}' closed.")
            except (Exception, BaseExceptionGroup) as e:
                if "TaskGroup" in str(type(e)) or "unhandled errors" in str(e):
                    logger.warning(f"Legacy TaskGroup cleanup error for server '{server_name}' (safely ignored)")
                else:
                    logger.error(f"Error closing legacy stdio context for server '{server_name}': {e}")
            finally:
                if server_name in self.stdio_contexts:
                    del self.stdio_contexts[server_name]

        self.available_tools.clear()
        self.available_resources.clear()
        logger.info("MCP client shutdown completed.")

# (main_test はコメントアウトのまま)
