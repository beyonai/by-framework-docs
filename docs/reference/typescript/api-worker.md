# Worker API (TypeScript)

TypeScript SDK 采用类 Python 的异步编程模型，深度适配 Node.js 生态。

## GatewayWorker

通过继承 `GatewayWorker` 类来实现自定义 Agent。

### 核心方法

```typescript
import { GatewayWorker, GatewayCommand, AgentContext } from '@byclaw/by-framework';

class MyWorker extends GatewayWorker {
  /**
   * 声明支持的 Agent 类型
   */
  getAgentTypes(): ReadonlyArray<string> {
    return ["ts-chat-agent"];
  }

  /**
   * 核心业务逻辑
   */
  async processCommand(command: GatewayCommand, context: AgentContext): Promise<any> {
    await context.emitChunk("Hello from TS!");
    return "处理完成";
  }
}
```

---

## AgentContext

### 基础属性

- `sessionId`: 当前会话 ID。
- `traceId`: 全局追踪 ID。
- `currentMessageId`: 当前处理的消息 ID。

### 事件上报 (Emission)

| 方法 | 类型定义 | 说明 |
| :--- | :--- | :--- |
| `emitChunk(event: string \| Event)` | `Promise<void>` | 发送流式文本或结构化事件。 |
| `emitState(event: string \| Event)` | `Promise<void>` | 更新 Agent 执行状态消息。 |
| `emitArtifact(event: string \| Event)` | `Promise<void>` | 发送产物（图片、链接等）。 |
| `askUser(event: string \| Event)` | `Promise<any>` | 挂起执行，向用户请求表单输入。 |

### Agent 间调用 (callAgent)

TS 版使用对象参数以提高可读性。

```typescript
await context.callAgent({
  targetAgentType: "expert-agent",
  content: "请分析此数据",
  waitForReply: true,  // 是否挂起等待返回
  payload: { key: "val" }
});
```

### 任务组 (dispatchGroup)

并行分发多个子任务。

```typescript
const { taskGroupId } = await context.dispatchGroup({
  tasks: [
    { targetAgentType: "a", content: "task1" },
    { targetAgentType: "b", content: "task2" }
  ],
  waitForReply: true
});

const results = await context.collectGroupResults(taskGroupId);
```

### 任务取消检查

- `isCancelRequested()`: 返回 `boolean`。
- `await checkCancelled()`: 如果已取消则抛出 `TaskCancelledError`。

### 配置管理

```typescript
// 设置 Agent 配置
context.setAgentConfigs([config1, config2]);

// 获取单个 Agent 配置
const config = context.getAgentConfig("my_agent_id");

// 列出所有 Agent 配置
const allConfigs = context.listAgentConfigs();
```

### 工具调用

```typescript
// 调用工具
const result = await context.callTool("tool_name", { arg1: "value" });
```

### 状态管理

```typescript
// 更新执行状态
await context.updateExecutionState("running");
```

---

## runWorker

快捷启动辅助函数。

```typescript
import { runWorker } from '@byclaw/by-framework';

runWorker(MyWorker, {
  workerId: "ts-worker-01",
  redisHost: "127.0.0.1",
  redisPort: 6379
});
```

### 自定义 Redis 连接启动

你也可以通过自定义初始化 `WorkerRunner` 来接管 Redis 连接生命周期：

```typescript
import { WorkerRunner, WorkerRegistry, createRedis } from '@byclaw/by-framework';

const redis = createRedis({ host: 'localhost', port: 6379 });
try {
    const registry = new WorkerRegistry(redis);
    const worker = new MyWorker(`worker-${process.pid}`, registry);
    
    // 传入自定义 Redis 实例
    const runner = new WorkerRunner(worker, { redisClient: redis });
    await runner.processAndAck(streamName, msgId, data);
} finally {
    // 处理完成后释放连接
    redis.disconnect();
}
```
