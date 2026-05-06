# Worker 模块

## 核心文件

=== "Python"

    - `src/by_framework/worker/worker.py` - GatewayWorker 基类
    - `src/by_framework/worker/runner.py` - Worker 运行循环
    - `src/by_framework/worker/processor.py` - 任务处理器
    - `src/by_framework/worker/app.py` - 启动入口

=== "Java"

    - `worker/GatewayWorker.java` - GatewayWorker 基类
    - `worker/WorkerRunner.java` - Worker 运行循环
    - `worker/AgentContext.java` - 运行时上下文
    - `worker/ExecutionTracker.java` - 任务追踪器

=== "TypeScript"

    - `src/worker.ts` - GatewayWorker 基类
    - `src/runner.ts` - Worker 运行循环
    - `src/processor.ts` - 任务处理器
    - `src/app.ts` - 启动入口（runWorker）

## GatewayWorker

=== "Python"

    ```python
    class GatewayWorker:
        """Abstract base class for Gateway Workers."""

        async def process_command(self, command, context: AgentContext) -> Any:
            """Process incoming command. Must be implemented by subclass."""
            raise NotImplementedError

        def get_agent_types(self) -> List[str]:
            """Return list of agent types this worker can handle."""
            raise NotImplementedError

        async def get_capabilities(self) -> List[WorkerCapability]:
            """Return list of worker capabilities."""
            return []
    ```

=== "Java"

    ```java
    public abstract class GatewayWorker {
        protected final String workerId;

        public GatewayWorker(String workerId) {
            this.workerId = workerId;
        }

        /** 返回此 Worker 能处理的 Agent 类型列表 */
        public abstract List<String> getAgentTypes();

        /** 处理传入的命令，必须由子类实现 */
        public abstract Object processCommand(GatewayCommand command, AgentContext context);
    }
    ```

=== "TypeScript"

    ```typescript
    export abstract class GatewayWorker {
        readonly workerId: string;

        /** 返回此 Worker 能处理的 Agent 类型列表 */
        abstract getAgentTypes(): ReadonlyArray<string>;

        /** 处理传入的命令，必须由子类实现 */
        abstract processCommand(
            command: GatewayCommand,
            context: AgentContext
        ): Promise<ProcessCommandResult>;
    }
    ```

## Runner 双循环架构

WorkerRunner 采用双循环设计（各语言实现细节略有不同，但核心逻辑一致）：

```
_control_loop          # 控制循环 - 管理生命周期、心跳、状态
    ↓
_run_once              # 单次执行 - 批量拉取并处理消息
```

### 控制循环

负责：
- Worker 注册/注销
- 心跳维护
- 优雅退出信号处理
- 任务状态同步

### 消息处理

负责：
- 从 Redis Stream 批量拉取消息
- 并发处理任务（Python: asyncio.gather / Java: ExecutorService / TypeScript: Promise.all）
- 错误重试与死信处理

## 任务处理流程

=== "Python"

    ```python
    async def _run_once(self) -> None:
        # 1. 批量拉取消息
        messages = await self._fetch_messages()

        # 2. 并发处理
        tasks = [
            self._process_single(message)
            for message in messages
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

        # 3. ACK 已处理消息
        for message in messages:
            await self._ack_message(message)
    ```

=== "Java"

    ```java
    private void runOnce() {
        // 1. 批量拉取消息
        List<StreamEntry> messages = fetchMessages();

        // 2. 线程池并发处理
        for (StreamEntry message : messages) {
            executor.submit(() -> processSingle(message));
        }

        // 3. ACK 已处理消息
        for (StreamEntry message : messages) {
            ackMessage(message);
        }
    }
    ```

=== "TypeScript"

    ```typescript
    private async runOnce(): Promise<void> {
        // 1. 批量拉取消息
        const messages = await this.fetchMessages();

        // 2. Promise.all 并发处理
        await Promise.all(
            messages.map(msg => this.processSingle(msg))
        );

        // 3. ACK 已处理消息
        for (const msg of messages) {
            await this.ackMessage(msg);
        }
    }
    ```
