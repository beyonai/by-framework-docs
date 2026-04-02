import os
import asyncio
from typing import List, Any
from dotenv import load_dotenv

from by_framework.core.protocol.commands import GatewayCommand
from by_framework.worker import AgentContext, GatewayWorker, run_worker
from by_framework.core.extensions import PluginManifest

# 加载 .env 配置文件 (加载当前目录下的 .env)
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    load_dotenv()  # 兜底加载工作目录下的 .env

from logging_plugin import LoggingPlugin

class LoggingWorker(GatewayWorker):
    """
    集成插件功能的示例 Gateway Worker。
    它将简单处理命令，并展示插件钩子的自动触发。
    """

    def get_capabilities(self) -> List[str]:
        """返回此 Worker 支持的智能体类型列表。"""
        # 注意：这里可以包含插件动态注册的 'debug-agent'
        return ["logging-agent", "debug-agent"]

    async def process_command(
        self, command: GatewayCommand, context: AgentContext
    ) -> Any:
        """处理来自 Gateway 的命令。"""
        self.logger.info(f"[*] Worker 正在处理任务: {context.message_id}")

        agent_config = context.agent_runtime_state.config_manager.get_config("debug-agent")
        
        tools = agent_config.tools

        prompts = agent_config.prompts

        self.logger.info(f"[*] Tools len: {len(tools)}")
        self.logger.info(f"[*] Prompts len: {len(prompts)}")
        
        # 模拟业务逻辑处理耗时
        await asyncio.sleep(0.8)
        
        response_text = f"已成功处理您的请求: '{command.content}'"
        return response_text

if __name__ == "__main__":
    # 1. 准备插件实例
    manifest = PluginManifest(
        plugin_id="logging-stats",
        version="1.2.0",
        priority=10
    )
    plugin = LoggingPlugin(manifest)

    # 显示加载的环境变量调试
    r_host = os.getenv("BYAI_REDIS_HOST", "127.0.0.1")
    r_port = int(os.getenv("BYAI_REDIS_PORT", 6379))
    r_password = os.getenv("BYAI_REDIS_PASSWORD", "mypassword")
    r_user = os.getenv("BYAI_REDIS_USERNAME", "myuser")

    print(f"[*] 启动参数: ID={os.getenv('BYAI_WORKER_ID', 'demo')}, Redis={r_host}:{r_port} (User={r_user})")

    # 2. 启动 Worker，并通过 plugin_list 注入插件
    run_worker(
        LoggingWorker,
        worker_id=os.getenv("BYAI_WORKER_ID", "logging-worker-demo"),
        redis_host=r_host,
        redis_port=r_port,
        redis_db=int(os.getenv("BYAI_REDIS_DB", 0)),
        redis_password=r_password,
        redis_username=r_user,
        # 注入插件列表
        plugin_list=[plugin]
    )
