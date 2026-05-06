# 常见问题

## 快速问题

### Q: 如何保证任务不丢失？

A: Redis Streams 提供持久化机制。Worker 使用 `XACK` 确认消息处理完成，未确认的消息会被重新投递。

### Q: 如何实现 Worker 负载均衡？

A: 多个 Worker 连接同一个 Redis Stream，Redis 会自动在消费者组内进行负载分配。

### Q: 如何横向扩展 Worker？

A: 启动多个不同 `worker_id` 的 Worker 进程，共享同一个 Redis 实例和相同的 `target_agent_type` stream。

### Q: 消息处理失败后会自动重试吗？

A: 是的，未 ACK 的消息会在重新读取时被重新投递。但建议在 `processCommand` 中实现重试逻辑。

## 高级问题

### Q: 如何实现定向消息发送？

A: 传入 `target_worker_id` 参数，消息会写入 `worker:{worker_id}` stream：

=== "Python"

    ```python
    response = await client.send_message(
        target_agent_type="my_agent",
        session_id="sess_123",
        content="hello",
        target_worker_id="specific-worker-01",
    )
    ```

=== "Java"

    ```java
    SendResponse response = client.sendMessage(
        "my_agent", "sess_123", "hello",
        null, null, null,
        "specific-worker-01",  // targetWorkerId
        null, null, null, null
    );
    ```

=== "TypeScript"

    ```typescript
    const response = await client.sendMessage({
        targetAgentType: "my_agent",
        sessionId: "sess_123",
        content: "hello",
        targetWorkerId: "specific-worker-01",
    });
    ```

### Q: 如何处理人机交互场景？

A: 使用 `context.askUser()` 挂起任务，等待用户回复：

=== "Python"

    ```python
    result = await context.ask_user(
        AskUserEvent(prompt="请确认")
    )
    # 任务会挂起，用户回复后以 ResumeCommand 形式恢复
    ```

=== "Java"

    ```java
    Object result = context.askUser("请确认");
    // 任务会挂起，用户回复后以 ResumeCommand 形式恢复
    ```

=== "TypeScript"

    ```typescript
    const result = await context.askUser({ prompt: "请确认" });
    // 任务会挂起，用户回复后以 ResumeCommand 形式恢复
    ```

### Q: 如何监控 Worker 状态？

=== "Python"

    ```python
    workers = await registry.get_online_workers(agent_type="my_agent")
    for worker in workers:
        print(f"Worker: {worker['worker_id']}, Last seen: {worker['last_heartbeat']}")
    ```

=== "Java"

    ```java
    List<Map<String, Object>> workers = registry.getOnlineWorkers("my_agent");
    for (Map<String, Object> worker : workers) {
        System.out.println("Worker: " + worker.get("worker_id"));
    }
    ```

=== "TypeScript"

    ```typescript
    const workers = await registry.getOnlineWorkers("my_agent");
    for (const worker of workers) {
        console.log(`Worker: ${worker.worker_id}`);
    }
    ```

### Q: 如何配置插件超时？

=== "Python"

    ```python
    run_worker(
        worker_class=MyWorker,
        plugin_hook_timeout_seconds=30,
    )
    ```

=== "TypeScript"

    ```typescript
    runWorker(MyWorker, {
        pluginHookTimeoutSeconds: 30,
    });
    ```

### Q: 如何使用服务发现？

=== "Python"

    ```python
    from by_framework.core.discovery import ServiceRegistry

    registry = ServiceRegistry(redis_client=redis)
    await registry.register("my-service", "http://192.168.1.100:8080")
    ```

=== "Java"

    ```java
    ServiceRegistry registry = new ServiceRegistry(redisClient);
    registry.register("my-service", "192.168.1.100", 8080);
    ```

=== "TypeScript"

    ```typescript
    const registry = new ServiceRegistry(redis);
    await registry.register({
        serviceName: "my-service",
        host: "192.168.1.100",
        port: 8080,
    });
    ```
