# By-Framework LangGraph Multi-Agent Sample

这个示例演示了如何结合 **LangGraph** 和 `by-framework` 来实现复杂的跨 Agent 协作流程。

## 场景描述
- **Orchestrator Graph (协调者)**: 
    - 使用 `StateGraph` 构建任务流。
    - **节点 1 (`call_sub`)**: 接收输入执行到此节点时，调用 `context.call_agent` 向子任务发送请求。
    - **挂起与恢复**: 框架会自动挂起主任务。当子任务完成后，主任务收到 `ResumeCommand`。
    - **节点 2 (`aggregate`)**: 协调者从 `ResumeCommand` 中读取 `reply_data`，并将其注入图的状态，继续执行直至完成。
- **Sub-Worker Graph (子 Agent)**:
    - 简单的 LangGraph 节点，负责文本转换。

## 快速上手

### 1. 准备环境
在 `python/workers/multi-agent-sample` 目录下运行：

```bash
uv sync
```

### 2. 运行项目
```bash
uv run python main.py
```

## 执行流程
1. **Client** (Ask: "hello") -> **Orchestrator**
2. **Orchestrator** (Node: `call_sub`) -> **Sub-Worker** (Ask: "hello")
3. **Sub-Worker** (Node: `worker_process`) -> **Orchestrator** (Result: "OLLEH")
4. **Orchestrator** (Resume -> Node: `aggregate`) -> **Client** (Final Result)
