# Context 模块

## 核心文件

=== "Python"

    - `src/by_framework/worker/context.py` - AgentContext
    - `src/by_framework/worker/byai_context.py` - ByaiAgentContext

=== "Java"

    - `worker/AgentContext.java` - AgentContext

=== "TypeScript"

    - `src/context.ts` - AgentContext

## AgentContext

运行时上下文，用于任务执行过程中与环境交互。

### 属性

| 属性 | 描述 |
|------|------|
| `sessionId` | 会话ID |
| `traceId` | 追踪ID |
| `messageId` | 消息ID |
| `parentMessageId` | 父消息ID |
| `currentAgentType` | 当前 Agent 类型 |

### 核心方法

#### emitChunk

发送流式文本片段：

=== "Python"

    ```python
    async def emit_chunk(
        self,
        event: Union[StreamChunkEvent, str],
        event_type: Optional[str] = None
    ) -> None:
    ```

=== "Java"

    ```java
    public void emitChunk(String content)
    public void emitChunk(String content, String eventType)
    ```

=== "TypeScript"

    ```typescript
    async emitChunk(content: string, eventType?: string): Promise<void>
    ```

#### emitState

发送状态更新：

=== "Python"

    ```python
    async def emit_state(
        self,
        event: Union[StateChangeEvent, str],
        event_type: Optional[str] = None
    ) -> None:
    ```

=== "Java"

    ```java
    public void emitState(String state)
    ```

=== "TypeScript"

    ```typescript
    async emitState(event: { state: string }): Promise<void>
    ```

#### callAgent

调用其他 Agent：

=== "Python"

    ```python
    async def call_agent(
        self,
        target_agent_type: str,
        content: object,
        **kwargs
    ) -> dict:
    ```

=== "Java"

    ```java
    public Map<String, Object> callAgent(
        String targetAgentType,
        Object content,
        boolean waitForReply
    )
    ```

=== "TypeScript"

    ```typescript
    async callAgent(params: {
        targetAgentType: string;
        content: string | unknown[];
        waitForReply?: boolean;
        payload?: Record<string, unknown>;
    }): Promise<CallAgentResult>
    ```

#### askUser

向用户请求输入（挂起当前任务）：

=== "Python"

    ```python
    async def ask_user(
        self,
        event: Union[AskUserEvent, str]
    ) -> dict:
    ```

=== "Java"

    ```java
    public Object askUser(String prompt)
    ```

=== "TypeScript"

    ```typescript
    async askUser(event: { prompt: string }): Promise<any>
    ```

#### dispatchGroup

分发任务组：

=== "Python"

    ```python
    async def dispatch_group(
        self,
        tasks: list[dict],
        **kwargs
    ) -> dict:
    ```

=== "Java"

    ```java
    public Map<String, Object> dispatchGroup(
        List<Map<String, Object>> tasks,
        boolean waitForReply
    )
    ```

=== "TypeScript"

    ```typescript
    async dispatchGroup(params: {
        tasks: Array<{ targetAgentType: string; content: string; }>;
        waitForReply?: boolean;
    }): Promise<DispatchGroupResult>
    ```
