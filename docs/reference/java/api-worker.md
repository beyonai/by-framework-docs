# Worker API (Java)

Java SDK 提供了强类型、高性能的 Worker 实现。通过继承 `GatewayWorker` 并集成 Spring Boot (可选)，可以快速构建企业级 Agent。

## GatewayWorker

`GatewayWorker` 是所有 Agent 任务处理器的基类。

### 核心方法

```java
public abstract class GatewayWorker {
    /**
     * 返回此 Worker 支持的 Agent 类型列表。
     */
    public abstract List<String> getAgentTypes();

    /**
     * 核心业务处理逻辑。
     * @param command 命令对象 (AskAgentCommand, ResumeCommand 等)
     * @param context 任务上下文
     * @return 返回值将被 normalize 为任务最终结果内容。
     *         可以直接返回 String、Map 或标准的 AgentTaskResult。
     */
    public abstract Object processCommand(GatewayCommand command, AgentContext context);
}

### 结果处理机制

`processCommand` 返回值支持灵活的数据类型，框架会自动规范化：
- **String**: 自动填充到 `content` 或 `replyData`。
- **Map / JSON Node**: 自动解析 `status`、`content`、`replyData`、`metadata` 等字段。
- **自定义对象**: 解析序列化后返回。
结束时框架如果检测到有最终结果，会自动下发 `finalAnswer` 事件。
```

---

## AgentContext

`AgentContext` 提供了与 Gateway 交互的所有能力，包含事件上报、Agent 间调用及状态管理。

### 基础属性

- `getSessionId()`: 获取当前会话 ID。
- `getTraceId()`: 获取全局追踪 ID。
- `getCurrentAgentType()`: 获取当前 Agent 类型。
- `getCurrentMessageId()`: 获取当前处理的消息 ID。

### 事件上报 (Emission)

| 方法 | 说明 |
| :--- | :--- |
| `emitChunk(String content)` | 发送流式文本片段（默认类型 `answerDelta`）。 |
| `emitState(String state)` | 发送状态变更或思考日志（默认类型 `reasoningLogDelta`）。 |
| `emitArtifact(String url)` | 发送产物（图片、文件等）链接。 |
| `askUser(String prompt)` | 挂起当前 Agent 并向用户发起表单询问。 |

### Agent 间调用

- `callAgent(String target, String content)`: 简易异步调用。
- `callAgent(String target, String content, Map payload, boolean waitForReply, Map metadata)`: 完整参数调用。

### 任务组 (Scatter-Gather)

- `dispatchGroup(List<Map<String, Object>> requests)`: 同时向多个 Agent 分发任务。
- `collectGroupResults(String taskGroupId)`: 阻塞（带超时）收集任务组中所有子任务的结果。

### 任务取消检查

- `isCancelRequested()`: 检查当前任务是否已被请求取消（检查线程中断状态）。
- `checkCancelled()`: 抛出运行时异常以终止执行（建议在耗时循环中调用）。

---

## WorkerRunner

用于启动 Worker。

```java
GatewayWorker myWorker = new MyWorker("java-worker-01");
WorkerRunner runner = new WorkerRunner(myWorker);
runner.start(); // 阻塞运行，监听 Redis Streams
```
