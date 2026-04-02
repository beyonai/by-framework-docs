"""原生 By-Framework 插件示例：LoggingPlugin"""
import time
from typing import Any, Optional
from by_framework.core.extensions import (
    Plugin, 
    PluginManifest, 
    PluginBuildContext, 
    AgentConfig
)
from by_framework.worker import AgentContext
from langchain_core.tools import tool

class LoggingPlugin(Plugin):
    """
    一个遵循 by-framework 原生规范的日志扩展插件。
    它可以自动化记录任务执行的生命周期，并预置 Agent 配置。
    """
    
    def __init__(self, manifest: PluginManifest):
        super().__init__(manifest)
        self._start_times = {}

    async def register_agent_configs(
        self, build_context: PluginBuildContext
    ) -> list[AgentConfig] | None:
        """
        插件注册阶段：向系统中注入预置的 Agent 配置。
        """
        print(f"[*] 插件 {self.plugin_id} 正在注册 Agent 配置与 LangChain 工具...")

        # --- 定义真实的 LangChain 工具 ---
        def get_worker_stats():
            @tool
            async def get_worker_stats(metrics: list[str] = None) -> str:
                """实时获取当前 Worker 的资源指标（CPU、内存等）。"""
                # 模拟执行逻辑
                return f"[插件执行] 成功获取指标 {metrics or 'all'}: CPU 占用 12.4%, 内存剩余 4.2GB"
            return get_worker_stats

        def flush_plugin_cache():
            @tool
            async def flush_plugin_cache() -> str:
                """强制清空插件内部记录的任务开始时间缓存。"""
                self._start_times.clear()
                return "[插件执行] 内部统计缓存已重置"
            return flush_plugin_cache

        # --- 丰富预置的调试 Agent 配置 ---
        debug_config = AgentConfig(
            agent_id="debug-agent",
            name="By-Framework 诊断专家",
            description="由 LoggingPlugin 动态注入的专家级智能体，具备全链路监控与日志分析能力。",
            # 丰富提示词模板 (Prompts)
            prompts={
                "system": (
                    "你是一个 By-Framework 内部体系架构诊断专家。\n"
                    "当前插件 ID: {plugin_id}\n"
                    "你的任务是根据历史 Trace 和当前任务上下文，识别潜在的性能瓶颈或错误原因。"
                ),
                "analyze_error": "请针对以下错误堆栈进行深度分析：\n{error_stack}",
                "predict_latency": "根据组件 {component} 的负载，预估下一个任务的延迟。"
            },
            # 注册真实的 LangChain 工具对象
            tools={
                get_worker_stats().name: get_worker_stats(),
                flush_plugin_cache().name: flush_plugin_cache()
            },
            # 修正后的技能描述 (Skills)
            skills={
                "log_pattern_recognition": "/tmp/log_pattern_recognition",
                "realtime_tracing": "/tmp/realtime_tracing"
            },
            # 扩展元数据 (Extra)
            extra={
                "plugin_origin": self.plugin_id,
                "version": self.manifest.version,
                "injected_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "capabilities": ["monitoring", "tracing", "profiling"],
                "tags": ["core", "debug", "framework"]
            }
        )
        
        return [debug_config]

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
