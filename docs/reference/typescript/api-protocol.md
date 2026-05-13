# Protocol API

TypeScript SDK 的协议层定义了消息传递中使用的命令（Commands）、事件（Events）、消息头（MessageHeader）及相关类型。

所有类从 `@byclaw/by-framework` 包根导入。

---

## 命令 (Commands)

所有命令都继承自 `BaseCommand`。

### BaseCommand

所有命令的抽象基类。

```typescript
import { BaseCommand, MessageHeader } from '@byclaw/by-framework';
```

**核心属性和方法：**

| 成员 | 类型 | 描述 |
|------|------|------|
| `header` | `MessageHeader` | 消息头（必填） |
| `actionType` | `string` | 命令动作类型 |
| `toDict()` | `() => Record<string, unknown>` | 序列化为普通对象 |
| `toRedisPayload()` | `() => string` | 序列化为 Redis 传输格式 |

**类型别名：**

```typescript
type GatewayCommand = BaseCommand;
```

---

### AskAgentCommand

向 Agent 发送任务请求。

```typescript
import { AskAgentCommand } from '@byclaw/by-framework';
```

```typescript
class AskAgentCommand extends BaseCommand {
  actionType: string = "ASK_AGENT";
  content: string | ReadonlyArray<unknown>;
  waitForReply: boolean;
  extraPayload?: Record<string, unknown>;
}
```

| 属性 | 类型 | 描述 |
|------|------|------|
| `actionType` | `string` | 固定为 `"ASK_AGENT"` |
| `content` | `string \| ReadonlyArray<unknown>` | 发送给 Agent 的内容 |
| `waitForReply` | `boolean` | 是否等待 Agent 回复 |
| `extraPayload` | `Record<string, unknown>` | 额外载荷 |

**示例：**

```typescript
import { AskAgentCommand, MessageHeader } from '@byclaw/by-framework';

const header = new MessageHeader("msg_001", "session_001", "trace_001");
const command = new AskAgentCommand({
  header,
  content: "请分析此数据",
  waitForReply: true,
  extraPayload: { priority: "high" }
});

console.log(command.actionType); // "ASK_AGENT"
```

---

### ResumeCommand

恢复一个挂起的任务。

```typescript
import { ResumeCommand } from '@byclaw/by-framework';
```

```typescript
class ResumeCommand extends BaseCommand {
  actionType: string = "RESUME";
  content: unknown;
  status: string;
  replyData?: unknown;
  extraPayload?: Record<string, unknown>;
}
```

| 属性 | 类型 | 描述 |
|------|------|------|
| `actionType` | `string` | 固定为 `"RESUME"` |
| `content` | `unknown` | 恢复时携带的内容 |
| `status` | `string` | 恢复状态标识 |
| `replyData` | `unknown` | 回复数据 |
| `extraPayload` | `Record<string, unknown>` | 额外载荷 |

**示例：**

```typescript
const resumeCmd = new ResumeCommand({
  header,
  content: "用户已确认",
  status: "approved",
  replyData: { confirmed: true }
});
```

---

### CancelTaskCommand

取消一个正在执行的任务。

```typescript
import { CancelTaskCommand } from '@byclaw/by-framework';
```

```typescript
class CancelTaskCommand extends BaseCommand {
  actionType: string = "CANCEL_TASK";
  targetMessageId: string;
  targetExecutionId?: string;
  targetWorkerId?: string;
  reason?: string;
  requestedBy?: string;
  cancelMode?: string;
}
```

| 属性 | 类型 | 描述 |
|------|------|------|
| `actionType` | `string` | 固定为 `"CANCEL_TASK"` |
| `targetMessageId` | `string` | 要取消的目标消息 ID（必填） |
| `targetExecutionId` | `string` | 目标执行 ID |
| `targetWorkerId` | `string` | 目标 Worker ID |
| `reason` | `string` | 取消原因 |
| `requestedBy` | `string` | 请求方标识 |
| `cancelMode` | `string` | 取消模式（如 `"graceful"`） |

**示例：**

```typescript
const cancelCmd = new CancelTaskCommand({
  header,
  targetMessageId: "msg_001",
  reason: "用户主动取消",
  cancelMode: "graceful"
});
```

---

### 自定义命令注册

框架支持注册和解析自定义命令类型。

```typescript
// 注册自定义命令类
registerCommand(commandCtor: typeof BaseCommand): void;

// 注销命令类型
unregisterCommand(actionType: string): void;

// 从字典数据解析命令
commandFromDict(data: Record<string, unknown>): BaseCommand;
```

**示例：**

```typescript
import { registerCommand, commandFromDict, BaseCommand } from '@byclaw/by-framework';

class CustomCommand extends BaseCommand {
  actionType = "CUSTOM_ACTION";
  customField: string;
}

registerCommand(CustomCommand);

// 从序列化数据恢复
const cmd = commandFromDict({ actionType: "CUSTOM_ACTION", ... });
```

---

## MessageHeader

消息头包含消息的路由、追踪和上下文元信息。

```typescript
import { MessageHeader } from '@byclaw/by-framework';
```

### 构造函数

```typescript
class MessageHeader {
  constructor(
    messageId: string,
    sessionId: string,
    traceId: string,
    options?: MessageHeaderOptions
  );
}
```

### 属性

| 属性 | 类型 | 只读 | 描述 |
|------|------|------|------|
| `messageId` | `string` | 是 | 消息唯一标识 |
| `sessionId` | `string` | 是 | 会话 ID |
| `traceId` | `string` | 是 | 全局追踪 ID |
| `sourceAgentType` | `string` | 是 | 源 Agent 类型 |
| `targetAgentType` | `string` | 是 | 目标 Agent 类型 |
| `parentMessageId` | `string` | 是 | 父消息 ID |
| `taskGroupId` | `string` | 是 | 任务组 ID |
| `userCode` | `string` | 是 | 用户编码 |
| `userName` | `string` | 是 | 用户名称 |
| `metadata` | `Record<string, unknown>` | 是 | 自定义元数据 |

### 序列化方法

```typescript
// 序列化为普通对象
toDict(): Record<string, unknown>;

// 从普通对象反序列化
static fromDict(data: Record<string, unknown>): MessageHeader;
```

**示例：**

```typescript
import { MessageHeader } from '@byclaw/by-framework';

const header = new MessageHeader("msg_001", "session_001", "trace_001", {
  sourceAgentType: "web-client",
  targetAgentType: "chat-agent",
  userCode: "user_123",
  userName: "张三"
});

console.log(header.messageId); // "msg_001"
console.log(header.traceId);   // "trace_001"

// 序列化
const dict = header.toDict();

// 反序列化
const restored = MessageHeader.fromDict(dict);
```

---

## 事件 (Events)

以下接口定义了各种流式事件的数据结构。

### StreamChunkEvent

流式文本片段事件。

```typescript
interface StreamChunkEvent {
  content?: string;
  role?: string;
  function_call?: unknown;
  tool_calls?: unknown;
  metadata?: Record<string, unknown>;
}
```

| 属性 | 类型 | 描述 |
|------|------|------|
| `content` | `string` | 文本内容 |
| `role` | `string` | 角色（如 `"assistant"`） |
| `function_call` | `unknown` | 函数调用信息 |
| `tool_calls` | `unknown` | 工具调用信息 |
| `metadata` | `Record<string, unknown>` | 额外元数据 |

### StateChangeEvent

状态变更事件。

```typescript
interface StateChangeEvent {
  state: string;
  metadata?: Record<string, unknown>;
}
```

| 属性 | 类型 | 描述 |
|------|------|------|
| `state` | `string` | 当前状态描述 |
| `metadata` | `Record<string, unknown>` | 额外元数据 |

### ArtifactEvent

产物/附件事件。

```typescript
interface ArtifactEvent {
  url: string;
  metadata?: Record<string, unknown>;
}
```

| 属性 | 类型 | 描述 |
|------|------|------|
| `url` | `string` | 产物 URL |
| `metadata` | `Record<string, unknown>` | 额外元数据 |

### AskUserEvent

用户输入请求事件。

```typescript
interface AskUserEvent {
  prompt: string;
  metadata?: Record<string, unknown>;
}
```

| 属性 | 类型 | 描述 |
|------|------|------|
| `prompt` | `string` | 提示文本 |
| `metadata` | `Record<string, unknown>` | 额外元数据 |

**事件使用示例：**

```typescript
import { AgentContext } from '@byclaw/by-framework';

// 发送流式文本
await context.emitChunk({
  content: "正在分析数据...",
  role: "assistant"
});

// 发送状态变更
await context.emitState({ state: "processing" });

// 发送产物
await context.emitArtifact({
  url: "https://example.com/chart.png",
  metadata: { type: "image" }
});

// 请求用户输入
const response = await context.askUser({
  prompt: "请选择下一步操作",
  metadata: { options: ["继续", "停止"] }
});
```

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

### ExecutionStatus

```typescript
class ExecutionStatus {
  // 任务的当前执行状态信息
  // 具体属性由框架定义
}
```

---

## 枚举

### ActionType 枚举

定义消息的请求类型。

| 值 | 描述 |
|----|------|
| `ASK_AGENT` | 向 Agent 发送任务请求 |
| `RESUME` | 恢复挂起的任务 |
| `CANCEL_TASK` | 取消任务 |
| `ASK_USER` | 向用户请求输入 |

### EventType 枚举

定义流式事件类型。

| 值 | 描述 |
|----|------|
| `answerDelta` | 回答内容增量推送 |
| `reasoningLogDelta` | 推理日志增量 |
| `reasoningLogStart` | 推理日志开始标记 |
| `reasoningLogEnd` | 推理日志结束标记 |
| `appStreamResponse` | 应用流响应 |
| `taskCreate` | 任务创建事件 |
| `stepComplete` | 步骤完成标记 |
| `taskStop` | 任务终止事件 |

### AgentState 枚举

定义 Agent 任务的生命周期状态。

| 值 | 描述 |
|----|------|
| `STARTING` | 任务启动中 |
| `QUEUED` | 任务排队中 |
| `CALLING_AGENT` | 正在调用其他 Agent |
| `WAITING_AGENT` | 等待 Agent 回复 |
| `WAITING_USER` | 等待用户输入 |
| `CANCELLING` | 取消中 |
| `CANCELLED` | 已取消 |
| `COMPLETED` | 已完成 |
| `FAILED` | 执行失败 |
| `RESUMED` | 已恢复 |

**辅助常量和函数：**

```typescript
import { TERMINAL_STATES, isTerminalState } from '@byclaw/by-framework';

// TERMINAL_STATES 为只读数组，包含所有终态
// [CANCELLED, COMPLETED, FAILED]

// 检查是否为终态
if (isTerminalState(currentState)) {
  console.log("任务已结束");
}
```

### SseMessageType 枚举

定义 SSE 推送的消息类型。

| 值 | 编码 | 描述 |
|----|------|------|
| `text` | 1002 | 纯文本消息 |
| `echart` | 2001 | EChart 图表 |
| `form` | 2002 | 表单 |
| `digit` | 2003 | 数字展示 |
| `iframe` | 2006 | 内嵌页面 |
| `task` | 2008 | 任务卡片 |

### SseReasonMessageType 枚举

定义 SSE 推理相关的消息类型。

| 值 | 编码 | 描述 |
|----|------|------|
| `think_title` | 3003 | 思考标题 |
| `think_sub_title` | 3005 | 思考子标题 |
| `think_text` | 1002 | 思考文本 |
| `think_code_answer` | 3008 | 思考代码答案 |
| `think_code` | 3006 | 思考代码 |
| `think_code_result` | 3007 | 思考代码结果 |
| `task_finished` | 3009 | 任务完成 |
| `task_user_input` | 3013 | 任务用户输入 |
| `task_create_file` | 3010 | 任务创建文件 |
| `task_title` | 3011 | 任务标题 |
| `agent_card` | 2015 | Agent 卡片 |
| `async_card` | 2014 | 异步卡片 |
