"""
Trace Demonstration Worker for by-framework-samples.

This worker handles "trace-demo-agent" commands and illustrates both:
1. Native, plugin-driven APM integration (zero-code trace propagation)
2. Manual Langfuse observation nesting (for external integrations)
"""

import asyncio
import os
from typing import Any, List

# by-framework imports
from by_framework.core.protocol.commands import GatewayCommand
from by_framework.worker import AgentContext, GatewayWorker, run_worker
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))


# =====================================================================
# Custom GatewayWorker Implementation
# =====================================================================
class TraceDemoWorker(GatewayWorker):
    """
    A GatewayWorker implementation designed to demonstrate trace nesting.

    When this worker starts up with PhoenixPlugin/LangfusePlugin, the parent
    trace relationship is automatically established by the framework.
    """

    def get_agent_types(self) -> List[str]:
        return ["trace-demo-agent"]

    async def process_command(
        self, command: GatewayCommand, context: AgentContext
    ) -> Any:
        self.logger.info(
            f"[TraceDemoWorker] Received command: {command.header.message_id}"
        )

        # -------------------------------------------------------------
        # 演示一：原生插件驱动的可观测性
        # -------------------------------------------------------------
        # 框架的 PluginSystem 已经在后台自动启动了对应的 Span / Observation。
        # 我们可以通过 context 动态推送进度
        await context.emit_chunk(
            "Tracing context initialized. Starting manual trace test...\n\n"
        )

        # -------------------------------------------------------------
        # 演示二：手动链路继承（模拟调用一个外部非框架系统并绑定 Trace）
        # -------------------------------------------------------------
        header = command.header
        session_id = header.session_id
        message_id = header.message_id
        content = str(command.content or "")

        # -------------------------------------------------------------
        # 【外部系统手动接入规范演示说明】
        # -------------------------------------------------------------
        # 如果你正在开发一个不使用 by-framework 的外部独立系统，并且需要手动使用 Langfuse SDK 写入 Trace，
        # 为了让你的外部 Span 能够完美融入到本 trace 体系中，请严格遵守以下规范：
        #
        # 1. 对齐 Trace ID：
        #    外部系统要沿用 AskAgentCommand.header.trace_id；如果直接写 Langfuse SDK，
        #    请使用 by-framework trace 文档里约定的 32 位 hex trace id 转换规则。
        #
        # 2. 挂载 Parent Observation ID：
        #    你应该从 AskAgentCommand Header 中提取出 langfuse_parent_observation_id 作为父级 ID。
        #
        # 示例伪代码：
        #
        # 本示例已经运行在 by-framework worker 内，所以直接在 framework
        # Langfuse observation 下创建子 observation。这样不会和 OTel 自动同步
        # 产生重复节点，最终树保持为：
        #
        # worker.execute
        #   └─ trace-demo-agent
        #       └─ external_complex_pipeline
        #           ├─ Knowledge_Retrieval
        #           ├─ LLM_Reasoning_Engine
        #           └─ Result_Formatter
        # -------------------------------------------------------------

        framework_langfuse_obs = getattr(context, "_langfuse_observation", None)
        external_observation = None
        if framework_langfuse_obs is not None and hasattr(
            framework_langfuse_obs, "start_observation"
        ):
            external_observation = framework_langfuse_obs.start_observation(
                name="external_complex_pipeline",
                as_type="span",
                input=content,
                metadata={
                    "session_id": session_id,
                    "message_id": message_id,
                    "agent_id": context.current_agent_id,
                },
            )

        # 执行业务核心模拟并写入一棵干净的 Langfuse observation 树。
        try:
            # -------------------------------------------------------------
            # 阶段 1: Knowledge Retrieval (包含二级嵌套子 Observation)
            # -------------------------------------------------------------
            await context.emit_chunk(
                "Step 1: Starting Knowledge Retrieval from Vector Database...\n"
            )
            knowledge_observation = (
                external_observation.start_observation(
                    name="Knowledge_Retrieval",
                    as_type="retriever",
                    input={"query": content, "session_id": session_id},
                )
                if external_observation is not None
                else None
            )

            # 1.1 VectorDB Search (底层 DB 级嵌套)
            vector_observation = (
                knowledge_observation.start_observation(
                    name="VectorDB_Search",
                    as_type="span",
                    input={
                        "db.system": "qdrant",
                        "statement": (
                            "search_similarity(vector, limit=5, "
                            f"filter={{'session': '{session_id}'}})"
                        ),
                    },
                )
                if knowledge_observation is not None
                else None
            )
            await asyncio.sleep(0.1)  # 模拟 DB 查询耗时
            db_results = [
                "Doc1: by-framework design guide",
                "Doc2: OpenTelemetry integration practices",
            ]
            if vector_observation is not None:
                vector_observation.update(
                    output={
                        "results": db_results,
                        "results_count": len(db_results),
                    }
                )
                vector_observation.end()

            # 1.2 Reranking
            rerank_observation = (
                knowledge_observation.start_observation(
                    name="Rerank_Candidates",
                    as_type="span",
                    input={"candidates": db_results},
                )
                if knowledge_observation is not None
                else None
            )
            await asyncio.sleep(0.05)  # 模拟重排耗时
            reranked_results = db_results[0]  # 保留最匹配的文档
            if rerank_observation is not None:
                rerank_observation.update(
                    output={
                        "top_document": reranked_results,
                        "top_score": 0.95,
                    }
                )
                rerank_observation.end()

            if knowledge_observation is not None:
                knowledge_observation.update(output=reranked_results)
                knowledge_observation.end()

            # -------------------------------------------------------------
            # 阶段 2: LLM Reasoning Engine
            # -------------------------------------------------------------
            await context.emit_chunk(
                "Step 2: Sending query to GPT-4o Reasoning Engine...\n"
            )

            llm_prompt = (
                f"Context: {reranked_results}\nUser Question: {content}\nAnswer:"
            )
            llm_reply = (
                f"[Generated Answer] Trace 一等属性重构已成功运行，在分布式调用树中展现了完美的"
                f"深度父子嵌套。这里匹配了上下文: '{reranked_results}'。"
            )

            llm_observation = None
            if external_observation is not None:
                llm_observation = external_observation.start_observation(
                    name="LLM_Reasoning_Engine",
                    as_type="generation",
                    input=llm_prompt,
                    model="gpt-4o",
                    model_parameters={"temperature": 0.2},
                )

            await asyncio.sleep(0.4)  # 模拟 LLM 推理
            if llm_observation is not None:
                llm_observation.update(
                    output=llm_reply,
                    usage_details={
                        "input": 35,
                        "output": 52,
                        "total": 87,
                    },
                    cost_details={"total": 0.000608},
                )
                llm_observation.end()

            # -------------------------------------------------------------
            # 阶段 3: Result Formatter
            # -------------------------------------------------------------
            await context.emit_chunk("Step 3: Formatting final response...\n")
            formatter_observation = (
                external_observation.start_observation(
                    name="Result_Formatter",
                    as_type="span",
                    input=llm_reply,
                )
                if external_observation is not None
                else None
            )

            await asyncio.sleep(0.03)  # 模拟轻量后处理
            final_reply = f"Pipeline execution completed successfully.\n{llm_reply}"
            if formatter_observation is not None:
                formatter_observation.update(output=final_reply)
                formatter_observation.end()

            # 记录总体输出并收尾
            if external_observation is not None:
                external_observation.update(output=final_reply)
                external_observation.end()
            await context.emit_chunk(f"\n[Trace Integration OK]\n{final_reply}\n")

        except Exception as err:
            if external_observation is not None:
                external_observation.update(
                    output={"error": str(err)},
                    level="ERROR",
                    status_message=str(err),
                )
                external_observation.end()
            raise err

        return final_reply


if __name__ == "__main__":
    # 优先将 Trace 相关的环境及插件挂载进 Worker 进程
    # （实际运行中会自动通过 PluginRegistry 执行 hook_startup 等逻辑）
    run_worker(
        TraceDemoWorker,
        worker_id=os.getenv("BYAI_WORKER_ID", "trace-demo-worker-1"),
        redis_host=os.getenv("BYAI_REDIS_HOST", "127.0.0.1"),
        redis_port=int(os.getenv("REDIS_PORT", 6379)),
        redis_db=int(os.getenv("REDIS_DB", 0)),
        redis_username=os.getenv("REDIS_USERNAME"),
        redis_password=os.getenv("REDIS_PASSWORD"),
    )
