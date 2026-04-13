"""原生 By-Framework 插件示例：LoggingPlugin"""
import time
from typing import Any, Optional
from by_framework.core.extensions import (
    Plugin, 
    PluginManifest, 
    PluginBuildContext, 
    AgentConfig
)
from by_framework.common.logger import logger
from by_framework.worker import AgentContext
from by_framework.core.protocol.commands import AskAgentCommand
from langchain_core.tools import tool

class LoggingPlugin(Plugin):
    """
    一个遵循 by-framework 原生规范的日志扩展插件。
    它可以自动化记录任务执行的生命周期，并预置 Agent 配置。
    """
    
    def __init__(self, manifest: PluginManifest = None):
        if manifest is None:
            manifest = PluginManifest(
                plugin_id="logging-stats",
                version="1.2.0",
                priority=10
            )
        super().__init__(manifest)
        self._start_times = {}

    async def register_agent_configs(
        self, build_context: PluginBuildContext
    ) -> list[AgentConfig] | None:
        return None

    async def on_task_start(self, context: AgentContext) -> None:
        """
        任务开始钩子：记录开始时间。
        """
        task_id = context.message_id
        self._start_times[task_id] = time.time()
        print(f"[插件钩子 - {self.name}] 任务 {task_id} 已由插件检测并开始执行。")

    async def on_task_complete(self, context: AgentContext, result: Any) -> None:
        """
        任务完成钩子：计算耗时并输出。
        """
        task_id = context.message_id
        start_time = self._start_times.pop(task_id, time.time())
        duration = time.time() - start_time
        
        print(f"[插件钩子 - {self.name}] 任务 {task_id} 执行成功！")
        print(f"    - 耗时: {duration:.4f}s")
        print(f"    - 结果摘要: {str(result)[:50]}...")

    async def on_worker_startup(self, worker: Any) -> None:
        """
        Worker 启动时调用。
        """
        print(f"[插件钩子 - {self.name}] Worker {getattr(worker, 'worker_id', 'unknown')} 正在启动，插件已就绪。")

    async def on_call_agent_start(self, context: AgentContext, command: AskAgentCommand) -> None:
        """
        调用 Agent 开始钩子：记录开始时间。
        """
        # command.header.source_agent_type = ""
        logger.info("on_call_agent_start")