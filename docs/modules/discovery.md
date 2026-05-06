# Discovery 模块

## 核心文件

=== "Python"

    - `src/by_framework/core/discovery.py` - ServiceRegistry, DiscoveryClient
    - `src/by_framework/util/discovery_http_client.py` - DiscoveryHttpClient

=== "Java"

    - `core/discovery/ServiceRegistry.java`
    - `core/discovery/DiscoveryClient.java`
    - `util/http/DiscoveryHttpClient.java`

=== "TypeScript"

    - `src/discovery/service_registry.ts`
    - `src/discovery/discovery_client.ts`
    - `src/discovery/discovery_http_client.ts`

## ServiceRegistry

基于 Redis 的服务注册中心。

=== "Python"

    ```python
    class ServiceRegistry:
        def __init__(self, redis_client: Redis) -> None:

        async def register(self, service_name: str, endpoint: str, metadata: Optional[dict] = None) -> None:
        async def heartbeat(self, service_name: str, endpoint: str) -> None:
        async def unregister(self, service_name: str, endpoint: str) -> None:
    ```

=== "Java"

    ```java
    public class ServiceRegistry {
        public ServiceRegistry(RedisClient redisClient)

        public void register(String serviceName, String host, int port)
        public void unregister()
    }
    ```

=== "TypeScript"

    ```typescript
    export class ServiceRegistry {
        constructor(redisClient?: Redis)

        async register(params: {
            serviceName: string; host?: string; port?: number;
            weight?: number; metadata?: Record<string, unknown>;
            heartbeatInterval?: number;
        }): Promise<void>

        async unregister(): Promise<void>
    }
    ```

## DiscoveryClient

带缓存的服务发现客户端。

=== "Python"

    ```python
    class DiscoveryClient:
        def __init__(self, redis_client: Redis, cache_ttl: int = 30) -> None:

        async def discover(self, service_name: str, use_cache: bool = True) -> List[str]:
    ```

=== "Java"

    ```java
    public class DiscoveryClient {
        public DiscoveryClient(RedisClient redisClient)

        public List<ServiceInstance> getInstances(String serviceName)
        public ServiceInstance discover(String serviceName)
    }
    ```

=== "TypeScript"

    ```typescript
    export class DiscoveryClient {
        constructor(redisClient?: Redis, cacheIntervalSeconds?: number)

        async getInstances(serviceName: string, forceRefresh?: boolean): Promise<ServiceInstance[]>
        async discover(serviceName: string): Promise<ServiceInstance | null>
    }
    ```

## DiscoveryHttpClient

结合服务发现的 HTTP 客户端，支持自动重试与故障切换。

=== "Python"

    ```python
    class DiscoveryHttpClient:
        def __init__(self, redis_client: Redis, service_name: str, max_retries: int = 3) -> None:

        async def get(self, path: str, **kwargs) -> httpx.Response:
        async def post(self, path: str, **kwargs) -> httpx.Response:
        async def download(self, remote_path: str, local_path: str) -> None:
        async def upload(self, local_path: str, remote_path: str) -> None:
    ```

=== "Java"

    ```java
    public class DiscoveryHttpClient {
        public DiscoveryHttpClient(DiscoveryClient discoveryClient, String serviceName, int maxRetries)

        public HttpResponse get(String serviceName, String path)
        public HttpResponse post(String serviceName, String path, Map<String, Object> json)
    }
    ```

=== "TypeScript"

    ```typescript
    export class DiscoveryHttpClient {
        constructor(params: { discoveryClient: DiscoveryClient; retryConfig?: RetryConfig })

        async get(serviceName: string, path: string, params?: RequestParams): Promise<HttpResponse>
        async post(serviceName: string, path: string, params?: RequestParams): Promise<HttpResponse>
    }
    ```
