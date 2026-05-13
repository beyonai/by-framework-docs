# Multi-Workers Multi-Agent Sample

这个示例展示了如何在 `by-framework` 中通过 **两个独立的进程** 实现跨 Worker 的智能调度。

## 🏗️ 架构说明

1.  **进程 A (`orchestrator.py`)**: 运行 `orchestrator-agent`。它包含 LLM 决策逻辑，但不具备实际转换能力，必须通过 **跨进程 RPC** 调度。
2.  **进程 B (`sub_worker.py`)**: 运行 `sub-worker-agent`。它是一个纯粹的计算节点，负责执行文本反转。
3.  **连接层**: 两个进程共享同一个 Redis 集群。

## 🚀 启动指南

### 1. 配置环境
确保项目根目录或当前目录下有 `.env` 文件，包含必要的 `REDIS` 和 `OPENAI` 配置。

### 2. 启动执行层 (Process-B)
首选打开一个终端窗口，运行子工作进程：
```bash
uv run python sub_worker.py
```
*你会看到日志显示 `sub-worker-process-1` 已启动并准备就绪。*

### 3. 启动协调层 (Process-A)
打开第二个终端窗口，运行协调工作进程：
```bash
uv run python orchestrator.py
```
*你会看到日志显示 `orchestrator-process-1` 已启动。*

### 4. 发送指令
使用客户端向 `orchestrator-agent` 发送请求：
> “请反转字符串：**Hello MultiProcess**”

## 🔍 观察点

-   在 **Orchestrator** 的终端中，你会看到 `[Decision] LLM 确认调用工具`。
-   在 **SubWorker** 的终端中，紧接着会出现 `[Sub-worker] 🔨 接收到计算任务`。
-   计算完成后，**SubWorker** 完成任务，**Orchestrator** 接收到 `ResumeCommand` 并输出最终结果。

这证明了 `by-framework` 强大的服务发现和分布式调度能力。
