# 服务发现指南

仓库中包含一套基于 Redis 的服务发现与 HTTP 调用工具。

## 核心组件

| 组件 | 描述 |
|------|------|
| `ServiceRegistry` | 服务注册与心跳 |
| `DiscoveryClient` | 带缓存的服务发现与负载均衡 |
| `DiscoveryHttpClient` | 结合服务发现的 HTTP 重试与节点切换 |

## ServiceRegistry

服务注册中心，负责管理服务的注册与心跳。

=== "Python"

    ```python
    from by_framework.core.discovery import ServiceRegistry

    registry = ServiceRegistry(redis_client=redis)
    await registry.register("my-service", "http://192.168.1.100:8080")
    await registry.heartbeat("my-service", "http://192.168.1.100:8080")
    ```

=== "Java"

    ```java
    import com.iwhaleai.byai.framework.core.discovery.ServiceRegistry;

    ServiceRegistry registry = new ServiceRegistry(redisClient);
    registry.register("my-service", "192.168.1.100", 8080);
    // 心跳自动通过后台线程维护
    ```

=== "TypeScript"

    ```typescript
    import { ServiceRegistry } from 'byclaw-gateway-sdk';

    const registry = new ServiceRegistry(redis);
    await registry.register({
        serviceName: "my-service",
        host: "192.168.1.100",
        port: 8080,
        heartbeatInterval: 10,  // 秒
    });
    // 心跳自动通过 setInterval 维护
    ```

## DiscoveryClient

带缓存的服务发现客户端：

=== "Python"

    ```python
    from by_framework.core.discovery import DiscoveryClient

    discovery = DiscoveryClient(redis_client=redis, cache_ttl=30)
    endpoints = await discovery.discover("my-service")
    # 返回可用的服务节点列表
    ```

=== "Java"

    ```java
    import com.iwhaleai.byai.framework.core.discovery.DiscoveryClient;

    DiscoveryClient discovery = new DiscoveryClient(redisClient);
    List<ServiceInstance> endpoints = discovery.getInstances("my-service");
    ```

=== "TypeScript"

    ```typescript
    import { DiscoveryClient } from 'byclaw-gateway-sdk';

    const discovery = new DiscoveryClient(redis, 5);  // 5秒缓存
    const endpoints = await discovery.getInstances("my-service");
    ```

## DiscoveryHttpClient

结合服务发现的 HTTP 客户端，支持自动重试与节点切换：

=== "Python"

    ```python
    from by_framework.util.discovery_http_client import DiscoveryHttpClient

    http_client = DiscoveryHttpClient(
        redis_client=redis,
        service_name="api-service",
        max_retries=3
    )

    response = await http_client.get("/api/v1/users")
    response = await http_client.post("/api/v1/users", json={"name": "test"})
    ```

=== "Java"

    ```java
    import com.iwhaleai.byai.framework.util.http.DiscoveryHttpClient;

    DiscoveryHttpClient httpClient = new DiscoveryHttpClient(
        discoveryClient, "api-service", 3  // maxRetries
    );

    HttpResponse response = httpClient.get("/api/v1/users");
    HttpResponse response = httpClient.post("/api/v1/users", Map.of("name", "test"));
    ```

=== "TypeScript"

    ```typescript
    import { DiscoveryHttpClient, DiscoveryClient } from 'byclaw-gateway-sdk';

    const discoveryClient = new DiscoveryClient(redis);
    const httpClient = new DiscoveryHttpClient({ discoveryClient });

    const response = await httpClient.get("api-service", "/api/v1/users");
    const response = await httpClient.post("api-service", "/api/v1/users", {
        json: { name: "test" },
    });
    ```
