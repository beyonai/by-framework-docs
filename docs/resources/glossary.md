# 术语表

## A

### Agent

AI Agent，能够处理任务并返回结果的智能体。

### AgentContext

运行时上下文，提供与运行环境交互的能力。

### AgentType

Agent 类型标识，用于路由和分发任务。

## C

### Consumer Group

Redis Streams 消费组，支持多个消费者竞争消费同一消息流。

### Control Stream

控制流，用于任务分发和调度指令。

## G

### GatewayClient

向 Redis Streams 发送命令的客户端。

### GatewayWorker

Worker 基类，处理来自 Redis Streams 的命令。

## M

### Membership

Worker 声明自己支持哪些 agent_types 的静态关系。

## P

### Plugin

插件，扩展框架能力的组件。

### PluginRegistry

插件注册表，管理插件的注册和发现。

### process_command

Worker 处理命令的核心方法。

## R

### Redis Streams

Redis 的消息队列实现，支持持久化、消费组、ACK 机制。

### run_worker

启动 Worker 的入口函数。

## S

### Session

会话，代表一次完整的对话交互。

### Stream Chunk

流式输出片段，用于实时返回 AI 生成的内容。

## W

### Worker

工作者，处理任务的进程或线程。

### WorkerRegistry

Worker 注册表，管理 Worker 的在线状态和心跳。

### Worker ID Lock

防止同一 worker_id 被重复启动的实例互斥机制。
