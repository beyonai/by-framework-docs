# Python 服务注册与发现示例

本目录包含基于 `by-framework` SDK 的服务注册与发现机制的完整示例。

## 环境需求

1.  **Python**: 3.12+ (推荐使用 [uv](https://docs.astral.sh/uv/) 管理项目)
2.  **Redis**: 必须在本地或通过网络访问一个运行中的 Redis 实例（默认连接 `localhost:6379`）。你可以通过修改 `.env` 文件来配置 Redis。
3.  **SDK**: 自带 `by-framework` Python SDK。
4.  **环境配置**: 复制示例配置并修改：
    ```bash
    cp .env.example .env
    ```

## 快速上手

### 1. 安装依赖

在当前目录下使用 `uv` 安装项目及 SDK：

```bash
uv pip install -e .
```

或者使用 `pip`:

```bash
pip install -e .
```

### 2. 运行示例

建议开启两个终端窗口分别测试。

#### 第一步：启动服务提供者 (Provider)

运行 `provider_example.py` 将服务注册到 Redis 并维持心跳。

```bash
python provider_example.py
```

*输出示例:*
```bash
[*] 正在注册服务: demo-service (host=127.0.0.1, port=8080, weight=10)...
[+] 服务 'demo-service' 注册成功，正在运行心跳维护...
[!] 按 Ctrl+C 停止服务并注销。
```

#### 第二步：运行服务消费者 (Consumer)

在另一窗口运行 `consumer_example.py` 发现已注起的实例。

```bash
python consumer_example.py
```

*输出示例:*
```bash
[*] 正在监听服务: demo-service...
[+] 发现 1 个活跃实例:
    - ID: demo-service:xxxxxxxx, 地址: 127.0.0.1:8080, 权重: 10, 元数据: {'version': '1.0.0', 'region': 'shanghai'}

[负载均衡演示] 模拟 5 次服务发现请求:
--- 策略: random ---
    第 1 次选中: demo-service:xxxxxxxx (127.0.0.1:8080)
    ...
```

#### 第三步：演示服务发现 HTTP 调用 (Discovery HTTP Client)


运行 `discovery_http_client_example.py` 演示如何自动解析服务名并进行 HTTP 调用，同时包含重试机制。

```bash
python discovery_http_client_example.py
```

*输出示例:*
```bash
[*] 准备调用服务: demo-service

--- 演示 GET 请求 (path: /health) ---
[+] 成功! 响应状态码: 200
    内容: {"status": "UP"}
...
```

> [!TIP]
> 如果你在运行此示例时没有启动真正的 HTTP 服务（如 Spring Boot 示例中对应的端口），脚本会捕获异常。此示例重点展示了 SDK 的重试逻辑和自动地址转换。

## 核心机制

- **ServiceRegistry**: 负责向 Redis 写入实例详情（HASH）和活跃心跳（ZSET）。如果进程崩溃或未注销，Redis 中的 ZSET 会在心跳超时后判定该实例失效。
- **DiscoveryClient**: 集成了**内存缓存**和**负载均衡**逻辑。
    - `watch()`: 开启后台异步刷新。
    - `discover(strategy="random")`: 随机策略轮询。
    - `discover(strategy="round-robin")`: 轮询策略。
- **DiscoveryHttpClient**: 高级 HTTP 客户端，集成了服务发现与**节点切换重试**。
    - 自动将 `service_name` 转换为健康的 `http://host:port`。
    - `RetryConfig`: 支持配置重试次数及触发重试的状态码。当请求失败时，会自动拉取新实例进行重试。
- **权重支持**: 注册时可传入 `weight`，由发现端按权重进行实例筛选（目前版本支持基于权重的随机，进阶版可深入扩展）。

## 维护建议

- **生产环境**: 请根据实际 Redis 地址修改 `ServiceRegistry(redis_client=...)` 或通过环境变量配置。
- **服务下线**: 务必调用 `registry.unregister()` 以确保实例能实时从注册中心移除。
