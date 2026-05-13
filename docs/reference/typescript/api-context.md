# Context API  

TypeScript SDK 的 `AgentContext` 类提供 Agent 任务执行的运行时上下文。

---

## AgentContext

### 属性

| 属性 | 类型 | 描述 |
|------|------|------|
| `sessionId` | `string` | 当前会话 ID |
| `traceId` | `string` | 全局追踪 ID |
| `messageId` | `string` | 当前消息 ID |
| `currentMessageId` | `string` | 当前消息 ID（别名，同 `messageId`） |
| `currentCommand` | `GatewayCommand \| undefined` | 当前正在执行的命令 |
| `pluginRegistry` | `PluginRegistry \| undefined` | 插件注册表引用 |

---

### 事件上报 (Emission)

事件上报方法用于向客户端实时推送流式内容、状态更新和产物。

#### emitChunk

发送流式文本片段或结构化事件。

```typescript
async emitChunk(event: StreamChunkEvent | string, eventType?: string): Promise<void>
```

**参数：**
- `event` — `StreamChunkEvent` 对象或纯文本字符串
- `eventType` — 可选，自定义事件类型

**示例：**

```typescript
import { AgentContext, StreamChunkEvent } from '@byclaw/by-framework';

// 发送纯文本流式片段
await context.emitChunk("正在分析数据...");

// 发送结构化事件
await context.emitChunk({
  content: "分析完成",
  role: "assistant"
}, "answerDelta");
```

#### emitState

发送状态更新事件。

```typescript
async emitState(event: StateChangeEvent | string, eventType?: string): Promise<void>
```

**示例：**

```typescript
await context.emitState({ state: "processing" });
await context.emitState("数据加载完成", "stepComplete");
```

#### emitArtifact

发送产物或附件（图片、文件链接等）。

```typescript
async emitArtifact(event: ArtifactEvent | string, eventType?: string): Promise<void>
```

**示例：**

```typescript
await context.emitArtifact({
  url: "https://example.com/report.pdf",
  metadata: { filename: "report.pdf", size: 102400 }
});
```

#### askUser

挂起当前执行，向用户发送请求并等待输入。

```typescript
async askUser(event: AskUserEvent | string): Promise<{ readonly status: string }>
```

**示例：**

```typescript
const response = await context.askUser({
  prompt: "请确认是否继续执行？",
  metadata: { options: ["确认", "取消"] }
});
console.log(response.status);
```

---

### Agent 间调用 (callAgent)

调用另一个 Agent 执行任务。TS 版本使用对象参数模式以提高可读性。

```typescript
async callAgent(params: {
  targetAgentType: string;
  content: unknown;
  payload?: Record<string, unknown>;
  waitForReply?: boolean;
  metadata?: Record<string, unknown>;
  messageId?: string;
  parentMessageId?: string;
  probeAgentType?: string;
}): Promise<CallAgentResult>
```

**参数说明：**

| 参数 | 类型 | 描述 |
|------|------|------|
| `targetAgentType` | `string` | 目标 Agent 类型（必填） |
| `content` | `unknown` | 发送给目标 Agent 的内容（必填） |
| `payload` | `Record<string, unknown>` | 附加载荷数据 |
| `waitForReply` | `boolean` | 是否挂起等待回复，默认 `false` |
| `metadata` | `Record<string, unknown>` | 自定义元数据 |
| `messageId` | `string` | 指定消息 ID |
| `parentMessageId` | `string` | 指定父消息 ID |
| `probeAgentType` | `string` | 探测目标 Agent 类型 |

**示例：**

```typescript
const result = await context.callAgent({
  targetAgentType: "expert-agent",
  content: "请分析此组数据",
  waitForReply: true,
  payload: { datasetId: "ds_001" }
});

console.log(result.reply); // 目标 Agent 的返回值
```

---

### 任务组分发 (dispatchGroup)

并行分发多个子任务，实现 scatter-gather 模式。

```typescript
async dispatchGroup(params: {
  tasks: Array<{ targetAgentType: string; content: unknown; payload?: unknown; metadata?: unknown }>;
  waitForReply?: boolean;
  messageId?: string;
  parentMessageId?: string;
}): Promise<DispatchGroupResult>
```

**示例：**

```typescript
const { taskGroupId } = await context.dispatchGroup({
  tasks: [
    { targetAgentType: "data-fetcher", content: "获取用户数据" },
    { targetAgentType: "data-fetcher", content: "获取订单数据" },
    { targetAgentType: "analyzer", content: "分析趋势" }
  ],
  waitForReply: true
});

// 收集所有子任务结果
const results = await context.collectGroupResults(taskGroupId);
for (const r of results) {
  console.log(`Agent: ${r.sourceAgentType}, Result:`, r.content);
}
```

#### collectGroupResults

收集指定任务组的所有结果。

```typescript
async collectGroupResults(taskGroupId: string, timeout?: number): Promise<GroupResult[]>
```

**参数：**

- `taskGroupId` — 任务组 ID
- `timeout` — 可选，超时时间（毫秒）

---

### 任务取消检查

#### isCancelRequested

检查当前任务是否已被请求取消，不会抛出异常。

```typescript
isCancelRequested(): boolean
```

**示例：**

```typescript
// 在长时间循环中检查取消状态
for (const item of items) {
  if (context.isCancelRequested()) {
    console.log("检测到取消请求，中止处理");
    break;
  }
  await process(item);
}
```

#### checkCancelled

如果任务已被取消则抛出异常，适用于需要在取消时立即停止执行的场景。

```typescript
async checkCancelled(): Promise<void>
```

**示例：**

```typescript
// 在每个步骤前检查
await context.checkCancelled();
await context.emitChunk("步骤 1 完成");

await context.checkCancelled();
await context.emitChunk("步骤 2 完成");
```

---

### 配置管理

管理 Agent 运行时配置。

#### setAgentConfigs

设置 Agent 配置列表。

```typescript
setAgentConfigs(newConfigs: ReadonlyArray<AgentConfig>): void
```

#### getAgentConfig

获取单个 Agent 的配置。

```typescript
getAgentConfig(agentId: string): AgentConfig | undefined
```

#### listAgentConfigs

列出所有已注册的 Agent 配置。

```typescript
listAgentConfigs(): ReadonlyArray<AgentConfig>
```

**示例：**

```typescript
// 设置配置
context.setAgentConfigs([
  {
    agent_id: "my_agent",
    name: "My Agent",
    description: "A custom agent"
  }
]);

// 获取单个 Agent 配置
const config = context.getAgentConfig("my_agent");
if (config) {
  console.log(config.name);
}

// 列出所有配置
const allConfigs = context.listAgentConfigs();
```

---

### 工具调用 (callTool)

在 Agent 执行过程中调用已注册的工具。

```typescript
async callTool(name: string, args?: Record<string, unknown>): Promise<unknown>
```

**示例：**

```typescript
const result = await context.callTool("web_search", {
  query: "最新 AI 动态",
  limit: 5
});
console.log(result);
```

---

### 状态管理

#### updateExecutionState

更新当前执行状态的描述信息。

```typescript
async updateExecutionState(status: string): Promise<void>
```

**示例：**

```typescript
await context.updateExecutionState("正在加载数据...");
// 执行数据加载
await context.updateExecutionState("正在生成报告...");
```

#### flushToHistory

将当前会话历史刷新到持久化存储。

```typescript
async flushToHistory(): Promise<void>
```

**示例：**

```typescript
// 在任务完成前确保历史已持久化
await context.flushToHistory();
```

#### getActiveWorkers

获取集群中所有活跃的 Worker 信息。

```typescript
async getActiveWorkers(): Promise<Record<string, unknown>>
```

**示例：**

```typescript
const workers = await context.getActiveWorkers();
console.log(`当前活跃 Worker 数: ${Object.keys(workers).length}`);
```
