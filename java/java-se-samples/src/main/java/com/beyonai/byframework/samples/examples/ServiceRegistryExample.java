package com.beyonai.byframework.samples.examples;

import com.iwhaleai.byai.gateway.sdk.common.RedisClient;
import com.iwhaleai.byai.gateway.sdk.core.discovery.ServiceRegistry;
import lombok.extern.slf4j.Slf4j;

import java.util.HashMap;
import java.util.Map;

/**
 * 示例：服务注册过程。
 * 核心演示如何将本地运行的服务注册到 Redis 注册中心，并由 SDK 自动维持心跳。
 */
@Slf4j
public class ServiceRegistryExample {

    public static void main(String[] args) {
        // 1. 获取 Redis 连接客户端。
        // RedisClient.getInstance() 会自动尝试从系统环境变量读取配置。
        RedisClient redisClient = RedisClient.getInstance();

        // 2. 创建服务注册器
        ServiceRegistry registry = new ServiceRegistry(redisClient);

        // 3. 注册服务实例 (模拟 order-service)
        String serviceName = "order-service";
        int port = 8081;
        int weight = 5;
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("version", "1.0.0");
        metadata.put("region", "cn-south");
        metadata.put("canary", false);

        int heartbeatIntervalSeconds = 5; // 每 5 秒发送一次心跳

        log.info("Starting service registration for: {}", serviceName);

        // 注册并开启后台心跳
        registry.register(serviceName, null, port, weight, metadata, heartbeatIntervalSeconds);

        log.info("Service registered successfully. Current instance ID: {}",
                registry.getCurrentInstance().getId());

        // 4. 模拟服务运行，保持心跳发送
        try {
            log.info("Service is running and sending heartbeats. Press Ctrl+C to stop...");
            // 为演示效果，挂起 30 秒
            Thread.sleep(30 * 1000L);
        } catch (InterruptedException e) {
            log.warn("Service interrupted.");
            Thread.currentThread().interrupt();
        } finally {
            // 5. 优雅退出：注销实例，销毁后台心跳线程池
            log.info("Unregistering service...");
            registry.unregister();
            redisClient.close();
            log.info("Service stopped.");
        }
    }
}
