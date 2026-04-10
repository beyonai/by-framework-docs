# Claude Agent Worker

将 [Claude Agent SDK](https://pypi.org/project/claude-agent-sdk/)（含 Agent Teams）封装为 by-framework `GatewayWorker`。

## 架构

```
Redis Stream (AskAgentCommand)
          │
          ▼
  ClaudeAgentWorker.process_command()
          │
          ▼
  ClaudeSDKClient (持久化连接，进程级复用)
    │  .query(prompt, session_id)
    │  .receive_response()
    │           │           │
    ▼           ▼           ▼
  TextBlock   ToolUseBlock  ResultMessage
    │           │              │
    ▼           ▼              ▼
  emit_chunk  emit_chunk     return result
  (ANSWER)    (REASONING)    (完成)
```

使用 `ClaudeSDKClient` 维护持久化会话连接：
- 通过 `session_id` 参数自然隔离不同 framework session 的对话上下文
- 同一 session 的多次请求自动续接 Claude 对话，无需 Redis session 映射
- 内部自动管理工具调用（Read/Write/Bash 等）和 Agent Teams 子代理协调
- 支持通过 `client.interrupt()` 中断正在执行的任务

## 快速开始

### 1. 环境准备

```bash
cd python/workers/claude-agent
cp .env.example .env
# 编辑 .env，配置 Redis 连接等
```

### 2. 安装依赖

```bash
uv sync
```

### 3. 启动 Worker

```bash
uv run python claude_agent_worker.py
```

Worker 启动后，会注册 `claude-agent` 类型到 Redis，等待来自 Gateway 的命令。

## 配置说明

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `BYAI_REDIS_HOST` | `127.0.0.1` | Redis 地址 |
| `BYAI_REDIS_PORT` | `6379` | Redis 端口 |
| `BYAI_REDIS_DB` | `0` | Redis 数据库 |
| `BYAI_WORKER_ID` | `claude-agent-worker-1` | Worker 唯一 ID |
| `CLAUDE_AGENT_CWD` | `.` | Claude Code 的工作目录 |
| `CLAUDE_MAX_TURNS` | `200` | 最大 LLM 交互轮次 |
| `CLAUDE_SYSTEM_PROMPT` | *(无)* | 自定义系统提示词 |
| `CLAUDE_CLI_PATH` | *(SDK 自带)* | Claude CLI 路径 |

## 输出映射

| Claude SDK 消息类型 | by-framework 映射 | 前端展示 |
|--------------------|--------------------|---------| 
| `TextBlock`（主代理） | `emit_chunk(event_type=ANSWER_DELTA)` | 正式回答 |
| `TextBlock`（子代理） | `emit_chunk(event_type=REASONING_LOG_DELTA)` | 推理日志 |
| `ToolUseBlock` (Task) | `emit_chunk(event_type=REASONING_LOG_DELTA)` | 子任务派发 |
| `ToolUseBlock` (其他) | `emit_chunk(event_type=REASONING_LOG_DELTA)` | 工具调用 |
| `ToolResultBlock` | `emit_chunk(event_type=REASONING_LOG_DELTA)` | 工具返回 |
| Thinking block | `emit_chunk(event_type=REASONING_LOG_DELTA)` | 思维链 |
| `ResultMessage` | `return result` | 最终结果 |

## 注意事项

1. **Claude CLI**：`claude-agent-sdk` 自带 Claude CLI，无需单独安装
2. **权限模式**：默认使用 `bypassPermissions`，Claude Code 拥有完全自主权（包括文件读写、命令执行）
3. **Agent Teams**：通过 `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` 自动启用
4. **取消支持**：收到 by-framework 的 `check_cancelled()` 取消信号时，调用 `client.interrupt()` 中断 Claude 执行
5. **异常恢复**：发生连接级异常时，自动重置 `ClaudeSDKClient` 并在下次请求时重建连接

## 与其他 Worker 示例对比

| 特性 | multi-workers | agent-teams | **claude-agent** |
|------|--------------|-------------|-----------------|
| LLM 引擎 | LangChain + OpenAI | LangChain + OpenAI | **Claude Agent SDK** |
| 编排方式 | LangGraph ReAct | LangGraph StateGraph | **SDK 内置 Agent Teams** |
| 会话模式 | 手动消息管理 | LangGraph MemorySaver | **ClaudeSDKClient 内置** |
| 子任务派发 | `call_agent()` | `dispatch_group()` | **SDK 自动管理** |
| 工具能力 | 自定义工具 | 自定义工具 | **完整 Claude Code 工具链** |
| 中断支持 | `interrupt()` | `interrupt()` | **`client.interrupt()`** |
