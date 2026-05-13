# 部署指南

## 单机部署

### 1. 准备环境

=== "Python"

    ```bash
    cd by-framework-python
    uv sync
    ```

=== "Java"

    ```bash
    cd by-framework-java
    mvn clean install -DskipTests
    ```

=== "TypeScript"

    ```bash
    npm install @byclaw/by-framework
    npm run build
    ```

### 2. 启动 Redis

```bash
docker run -d --name gateway-redis \
  -p 6379:6379 \
  --restart unless-stopped \
  redis:7-alpine
```

### 3. 启动 Worker

=== "Python"

    ```bash
    uv run python -m by_framework \
      --worker-class my_agent.MyAgent \
      --worker-id worker-01 \
      --redis-host localhost
    ```

=== "Java"

    ```bash
    java -cp target/my-worker.jar MyAgent \
      --worker-id worker-01
    ```

=== "TypeScript"

    ```bash
    node dist/my_agent.mjs
    ```

## 多 Worker 部署

如需横向扩展，可以启动多个不同 `worker_id` 的 Worker 进程，并让它们共享同一个 Redis 实例与相同的 `target_agent_type` stream。

## 生产环境建议

### 使用连接池

=== "Python"

    ```python
    run_worker(
        worker_class=MyAgent,
        redis_max_connections=50
    )
    ```

=== "Java"

    ```java
    // Java SDK 使用 Jedis 连接池，通过配置类设置
    RedisConfig config = RedisConfig.builder()
        .maxConnections(50)
        .build();
    ```

=== "TypeScript"

    ```typescript
    runWorker(MyAgent, {
        redisMaxConnections: 50,
    });
    ```

### 配置监控

=== "Python"

    ```python
    import logging
    from by_framework.common.logger import setup_logging

    setup_logging(level=logging.INFO, use_json=True)
    ```

=== "Java"

    ```java
    // Java SDK 使用 SLF4J + Logback
    // 在 logback.xml 中配置 JSON 格式输出
    ```

=== "TypeScript"

    ```typescript
    // TypeScript SDK 使用 console 输出
    // 可通过 pluginConfigurator 配置自定义日志插件
    ```

### 环境变量

| 环境变量 | 描述 | 默认值 |
|---------|------|-------|
| `BYAI_WORKER_CONCURRENCY` | 最大并发数 | `50` |
| `BYAI_WORKER_FETCH_COUNT` | 批量获取消息数 | `10` |
| `BYAI_REDIS_MAX_CONNECTIONS` | Redis 最大连接数 | `max_concurrency + 10` |
| `REDIS_HOST` | Redis 主机地址 | `localhost` |
| `REDIS_PORT` | Redis 端口 | `6379` |
| `REDIS_PASSWORD` | Redis 密码 | *(无)* |

## run_worker 配置参数

=== "Python"

    | 参数 | 类型 | 描述 | 默认值 |
    | :--- | :--- | :--- | :--- |
    | `worker_class` | `Type[GatewayWorker]` | **必填**。业务 Worker 类。 | - |
    | `worker_id` | `str` | Worker 实例的唯一标识名。 | `"worker-1"` |
    | `redis_host` | `str` | Redis 服务器地址。 | `"localhost"` |
    | `redis_port` | `int` | Redis 端口。 | `6379` |
    | `redis_db` | `int` | Redis 数据库号。 | `0` |
    | `redis_password` | `str` | Redis 密码 (可选)。 | `None` |
    | `workspace_dir` | `str` | 任务执行的本地工作目录。 | `"/tmp/gateway-workspace"` |
    | `consumer_group` | `str` | Redis 消费者组名称。 | `"agent_engines"` |
    | `max_concurrency` | `int` | 最大并发处理数。 | `50` |
    | `fetch_count` | `int` | 每次批量获取的消息数量。 | `10` |

=== "Java"

    | 参数 | 类型 | 描述 | 默认值 |
    | :--- | :--- | :--- | :--- |
    | `workerId` | `String` | Worker 实例的唯一标识名。 | `"worker-1"` |
    | `RedisConfig` | `RedisConfig` | Redis 连接配置。 | 自动从环境变量读取 |
    | `WorkerConfig` | `WorkerConfig` | Worker 运行参数配置。 | 默认值 |

=== "TypeScript"

    | 参数 | 类型 | 描述 | 默认值 |
    | :--- | :--- | :--- | :--- |
    | `workerId` | `string` | Worker 实例的唯一标识名。 | `"worker-1"` |
    | `redisHost` | `string` | Redis 服务器地址。 | `"localhost"` |
    | `redisPort` | `number` | Redis 端口。 | `6379` |
    | `redisDb` | `number` | Redis 数据库号。 | `0` |
    | `redisPassword` | `string` | Redis 密码 (可选)。 | `undefined` |
    | `workspaceDir` | `string` | 任务执行的本地工作目录。 | `"/tmp/gateway-workspace"` |
    | `consumerGroup` | `string` | Redis 消费者组名称。 | `"agent_engines"` |
    | `maxConcurrency` | `number` | 最大并发处理数。 | `50` |
    | `fetchCount` | `number` | 每次批量获取的消息数量。 | `10` |
    | `pluginList` | `Plugin[]` | 插件实例列表。 | `[]` |
    | `pluginDir` | `string` | 插件目录路径。 | `undefined` |
