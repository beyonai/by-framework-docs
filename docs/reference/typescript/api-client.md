# Client API 

TypeScript SDK 提供 `GatewayClient` 和 `ByaiGatewayClient`，用于从外部服务向 Agent 集群发送消息和控制任务。

所有类从 `@byclaw/by-framework` 包根导入。

---

## GatewayClient

`GatewayClient` 是与 Agent 集群通信的入口客户端。

### 构造函数

```typescript
import { GatewayClient } from '@byclaw/by-framework';

const client = new GatewayClient(registry?, redisClient?, interceptors?);
```

| 参数 | 类型 | 描述 |
|------|------|------|
| `registry` | `WorkerRegistry \| undefined` | Worker 注册表，用于发现可用 Worker |
| `redisClient` | `Redis \| undefined` | Redis 客户端实例 |
| `interceptors` | `GatewayInterceptor[] \| undefined` | 拦截器数组 |

---

### sendMessage

向指定 Agent 类型发送消息。

```typescript
async sendMessage(params: SendMessageParams): Promise<SendMessageResponse>
```

**SendMessageParams 属性：**

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `targetAgentType` | `string` | 是 | 目标 Agent 类型 |
| `sessionId` | `string` | 是 | 会话 ID |
| `content` | `unknown` | 是 | 消息内容 |
| `sourceAgentType` | `string` | 否 | 源 Agent 类型 |
| `traceId` | `string` | 否 | 追踪 ID |
| `userCode` | `string` | 否 | 用户编码 |
| `userName` | `string` | 否 | 用户名称 |
| `actionType` | `string` | 否 | 动作类型，默认 `ASK_AGENT` |
| `extraPayload` | `Record<string, unknown>` | 否 | 额外载荷 |
| `parentMessageId` | `string` | 否 | 父消息 ID |
| `messageId` | `string` | 否 | 消息 ID（不指定则自动生成） |
| `metadata` | `Record<string, unknown>` | 否 | 自定义元数据 |
| `targetWorkerId` | `string` | 否 | 指定目标 Worker ID |
| `requireOnlineWorker` | `boolean` | 否 | 是否要求 Worker 在线，默认 `true` |

**示例：**

```typescript
import { GatewayClient } from '@byclaw/by-framework';

const client = new GatewayClient();

const response = await client.sendMessage({
  targetAgentType: "chat-agent",
  sessionId: "session_001",
  content: "你好，请帮我分析一下数据",
  userCode: "user_123",
  userName: "张三"
});

console.log(response.message_id); // 返回的消息 ID
console.log(response.status);     // 任务状态
```

---

### sendCommand

直接发送一个 Command 对象。适用于需要完整控制消息构造的场景。

```typescript
async sendCommand(command: BaseCommand, streamName?: string): Promise<SendMessageResponse>
```

**示例：**

```typescript
import { GatewayClient, AskAgentCommand, MessageHeader } from '@byclaw/by-framework';

const header = new MessageHeader("msg_001", "session_001", "trace_001");
const command = new AskAgentCommand({
  header,
  content: "请处理此任务",
  waitForReply: true
});

const response = await client.sendCommand(command);
```

---

### cancelTask

取消一个正在执行的任务。

```typescript
async cancelTask(params: {
  messageId: string;
  sessionId: string;
  reason?: string;
  targetAgentType?: string;
  requestedBy?: string;
  cancelMode?: string;
}): Promise<CancelTaskResponse>
```

**参数说明：**

| 参数 | 类型 | 描述 |
|------|------|------|
| `messageId` | `string` | 要取消的消息 ID（必填） |
| `sessionId` | `string` | 会话 ID（必填） |
| `reason` | `string` | 取消原因 |
| `targetAgentType` | `string` | 目标 Agent 类型 |
| `requestedBy` | `string` | 请求方标识，默认 `"client"` |
| `cancelMode` | `string` | 取消模式，默认 `"graceful"` |

**示例：**

```typescript
const result = await client.cancelTask({
  messageId: "msg_001",
  sessionId: "session_001",
  reason: "用户主动取消",
  cancelMode: "graceful"
});

if (result.success) {
  console.log(`任务已取消，影响 ${result.cancelled_count} 个执行`);
}
```

---

### addInterceptor

添加消息拦截器。拦截器在消息发送前后执行。

```typescript
addInterceptor(interceptor: GatewayInterceptor): void
```

**示例：**

```typescript
const myInterceptor: GatewayInterceptor = {
  beforeSend(params) {
    console.log("发送前:", params);
    // 可修改参数
    return params;
  },
  afterSend(response) {
    console.log("发送后:", response);
    // 可修改响应
    return response;
  }
};

client.addInterceptor(myInterceptor);
```

---

### 使用拦截器配置

也可以在构造函数中直接传入拦截器：

```typescript
const client = new GatewayClient(registry, redisClient, [myInterceptor]);
```

---

## ByaiGatewayClient

`ByaiGatewayClient` 继承自 `GatewayClient`，使用 Byai 特定的消息序列化格式。

```typescript
import { ByaiGatewayClient } from '@byclaw/by-framework';
```

### 构造函数

```typescript
new ByaiGatewayClient(interceptors?: GatewayInterceptor[], registry?: WorkerRegistry, redisClient?: Redis)
```

| 参数 | 类型 | 描述 |
|------|------|------|
| `interceptors` | `GatewayInterceptor[] \| undefined` | 拦截器数组 |
| `registry` | `WorkerRegistry \| undefined` | Worker 注册表 |
| `redisClient` | `Redis \| undefined` | Redis 客户端实例 |

`ByaiGatewayClient` 重写了 `sendMessage` 方法，在发送前对消息进行 Byai 格式的序列化处理。

**示例：**

```typescript
import { ByaiGatewayClient } from '@byclaw/by-framework';

const client = new ByaiGatewayClient();

const response = await client.sendMessage({
  targetAgentType: "byai-chat",
  sessionId: "session_001",
  content: "你好"
});
```

> 注意：与 Python SDK 不同，TS 版本的 `ByaiGatewayClient` 构造函数参数顺序为 `interceptors` 在前。

---

## GatewayInterceptor 接口

拦截器接口定义了两个可选的生命周期钩子。

```typescript
interface GatewayInterceptor {
  beforeSend?(params: SendMessageParams): SendMessageParams | Promise<SendMessageParams>;
  afterSend?(response: SendMessageResponse): SendMessageResponse | Promise<SendMessageResponse>;
}
```

| 钩子 | 签名 | 描述 |
|------|------|------|
| `beforeSend` | `(params: SendMessageParams) => SendMessageParams \| Promise<SendMessageParams>` | 发送前拦截，可修改发送参数 |
| `afterSend` | `(response: SendMessageResponse) => SendMessageResponse \| Promise<SendMessageResponse>` | 发送后拦截，可修改响应结果 |

---

## 响应类型

### SendMessageResponse

```typescript
interface SendMessageResponse {
  success: boolean;
  message_id: string;
  trace_id: string;
  target_worker_id: string;
  timestamp: number;
  status: string;
  error?: string;
  error_code?: string;
}
```

| 属性 | 类型 | 描述 |
|------|------|------|
| `success` | `boolean` | 是否成功 |
| `message_id` | `string` | 消息 ID |
| `trace_id` | `string` | 追踪 ID |
| `target_worker_id` | `string` | 目标 Worker ID |
| `timestamp` | `number` | 时间戳 |
| `status` | `string` | 状态 |
| `error` | `string` | 错误信息（失败时） |
| `error_code` | `string` | 错误码（失败时） |

### CancelTaskResponse

```typescript
interface CancelTaskResponse {
  success: boolean;
  message_id: string;
  execution_id: string;
  worker_id: string;
  status: string;
  timestamp: number;
  error?: string;
  cancelled_count?: number;
}
```

| 属性 | 类型 | 描述 |
|------|------|------|
| `success` | `boolean` | 是否成功 |
| `message_id` | `string` | 消息 ID |
| `execution_id` | `string` | 执行 ID |
| `worker_id` | `string` | Worker ID |
| `status` | `string` | 状态 |
| `timestamp` | `number` | 时间戳 |
| `error` | `string` | 错误信息（失败时） |
| `cancelled_count` | `number` | 被取消的任务数量 |
