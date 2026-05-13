# 数据流设计

## 数据流概览

```mermaid
graph TB
    User["用户请求"]
    Client["GatewayClient"]
    CtrlStream["Control Stream<br/>byai_gateway:ctrl:agent_type:type"]
    Worker["GatewayWorker"]
    DataStream["Session Data Stream<br/>byai_gateway:session:sid:data_stream"]
    Backend["Backend / WebSocket"]
    Frontend["Frontend UI"]

    User --> Client
    Client --> CtrlStream
    CtrlStream --> Worker
    Worker --> DataStream
    DataStream --> Backend
    Backend --> Frontend
    Worker --> CtrlStream

```

## 控制流 vs 数据流

by-framework 采用**控制流与数据流分离**的设计，这是整个架构的核心特征：

```mermaid
graph LR
    subgraph LayerCtrl ["控制流 - 指令通道"]
        direction TB
        CS1["byai_gateway:ctrl:agent_type:type"]
        CS2["byai_gateway:ctrl:worker:id"]
    end

    subgraph LayerData ["数据流 - 输出通道"]
        direction TB
        DS["byai_gateway:session:sid:data_stream"]
    end

    Client["Client"] --> LayerCtrl
    LayerCtrl --> Worker["Worker"]
    Worker --> LayerData
    LayerData --> Consumer["Backend"]

```

### 控制流 (Control Stream)

| 属性 | 说明 |
|------|------|
| **Key** | `byai_gateway:ctrl:agent_type:{agent_type}` |
| **用途** | 任务分发、调度指令 |
| **消费模式** | 竞争消费 — 多 Worker 通过 Consumer Group 抢单 |
| **Consumer Group** | `byai_gateway:consumer_group:agent_engines` |

### Worker 定向控制流

| 属性 | 说明 |
|------|------|
| **Key** | `byai_gateway:ctrl:worker:{worker_id}` |
| **用途** | 定向下发给指定 Worker（debug / 取消任务） |
| **消费模式** | 单 Worker 独占消费 |

### 数据流 (Data Stream)

| 属性 | 说明 |
|------|------|
| **Key** | `byai_gateway:session:{session_id}:data_stream` |
| **用途** | 流式输出、状态变更、产物数据 |
| **消费模式** | 共享订阅 — 所有消费者都能读到全部消息 |

## 消息生命周期

```mermaid
sequenceDiagram
    participant C as Client
    participant Ctrl as Control Stream
    participant W as Worker
    participant Ctx as AgentContext
    participant Data as Data Stream
    participant B as Backend

    C->>Ctrl: 1. XADD 写入命令
    Note over Ctrl: byai_gateway:ctrl:agent_type

    Ctrl->>W: 2. XREADGROUP 竞争消费
    W->>W: 3. processCommand

    loop 流式输出
        W->>Ctx: emit_chunk
        Ctx->>Data: 4. XADD 写入事件
        Note over Data: byai_gateway:session:sid:data_stream
        Data->>B: 5. XREAD 消费事件
    end

    W->>Ctrl: 6. XACK 确认完成
```

1. **① 发送**: Client 调用 `sendMessage()` 向 Control Stream 写入命令
2. **② 路由**: Redis Consumer Group 将消息分发到某个 Worker
3. **③ 处理**: Worker 的 `processCommand()` 执行业务逻辑
4. **④ 输出**: Worker 通过 `context.emit_*()` 向 Session Data Stream 写入事件
5. **⑤ 消费**: Backend 持续读取 Data Stream 并通过 WebSocket 推送给前端
6. **⑥ 确认**: Worker 处理完成后发送 XACK 确认消息

## Agent 间调用数据流

当一个 Agent 需要调用另一个 Agent 时，控制流会产生级联：

```mermaid
sequenceDiagram
    participant O as Orchestrator Worker
    participant Ctrl_A as SubAgent Control
    participant S as SubWorker
    participant Ctrl_O as Orchestrator Control

    Note over O: processCommand 执行中
    O->>Ctrl_A: callAgent
    Note over O: 挂起等待 ResumeCommand

    Ctrl_A->>S: XREADGROUP
    S->>S: processCommand
    S->>Ctrl_O: 完成后 XADD ResumeCommand

    Ctrl_O->>O: XREADGROUP 获取 ResumeCommand
    Note over O: 恢复执行
```

## Scatter-Gather 数据流

`dispatchGroup()` 实现一对多分发与结果收集：

```mermaid
sequenceDiagram
    participant O as Orchestrator
    participant R as Redis
    participant W1 as Worker-A
    participant W2 as Worker-B

    O->>R: 创建 TaskGroup 计数器
    Note over R: byai_gateway:task_group:gid
    O->>R: XADD 写入任务 A
    O->>R: XADD 写入任务 B
    Note over O: 挂起等待

    par 并行执行
        R->>W1: 消费任务
        W1->>R: 完成并写入结果
    and
        R->>W2: 消费任务
        W2->>R: 完成并写入结果
    end

    Note over R: 全部任务完成
    R->>O: 最后完成的 Worker 发送 ResumeCommand

    O->>R: collectGroupResults
```
