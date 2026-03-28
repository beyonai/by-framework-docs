# BeyonAI Framework Samples

本项目包含了基于 `by-framework` 分布式 Agent 调度框架的 Worker 实现示例。

## 项目结构

```text
.
├── python
│   └── workers
│       ├── adk-worker         # 基础 Worker 示例
│       ├── langgraph-worker   # 集成 LangGraph 的 Worker 示例 (支持流式输出)
│       └── multi-workers      # 多进程分布式流式协作示例 (Orchestrator + Poet)
├── java                       # (待补充 Java Worker 示例)
└── pyproject.toml             # uv 工作区配置
```

## 快速开始

### 1. 环境准备

- **Python**: 3.12+ (推荐使用 `uv` 管理)
- **Redis**: 用于任务队列和心跳注册。
- **OpenAI API Key**: (仅 `langgraph-worker` 需要)

### 2. 安装依赖

在项目根目录下运行：

```bash
uv sync
```

### 3. 配置环境变量

每个 Worker 目录下都有一个 `.env.example` 文件。请根据您的 Redis 和 LLM 配置创建 `.env` 文件。

以 `langgraph-worker` 为例：

```bash
cd python/workers/langgraph-worker
cp .env.example .env
# 编辑 .env 文件，填入：
# BYAI_REDIS_HOST=...
# OPENAI_API_KEY=...
```

### 4. 启动 Worker

在 Worker 目录下执行：

```bash
uv run python main.py
```

## 核心组件说明

### LangGraph Worker

该示例展示了如何将 LangGraph 的复杂工作流集成到 `by-framework` 中：

- **能力注册**: 自动注册 `langgraph-agent` 能力。
- **流式输出**: 集成 `graph.astream` 与 `AgentContext.emit_chunk`，支持向前端实时推送 Token。
- **配置化**: 支持通过环境变量灵活调整参数。

### Multi-Workers (分布式流式协作)

该示例展示了 `by-framework` 在多进程环境下的分布式调度与实时同步能力：

- **Orchestrator (进程 A)**: 跨进程任务分发。当 LLM 决策需要文学创作时，调度远程诗人。
- **Poet Sub-Worker (进程 B)**: 分布式诗人节点。生成的诗句通过 `emit_chunk` 跨进程即时推送到同一个 Session 的客户端。
- **状态同步**: 完美结合 `ResumeCommand` 机制，展示跨 Worker 的控制流闭环。

## 常见问题

- **Redis 认证失败**: 如果看到 `AuthenticationError`，请检查 `.env` 中的 `BYAI_REDIS_USERNAME` 和 `BYAI_REDIS_PASSWORD` 是否正确。
- **LLM 模型不可用**: 确保 `OPENAI_API_KEY` 有效，或在 `.env` 中通过 `LLM_MODEL` 切换模型。
- **环境隔离**: `uv run` 会自动根据 `pyproject.toml` 中的 `tool.uv.workspace` 使用正确的环境。

## 许可

Apache License 2.0
