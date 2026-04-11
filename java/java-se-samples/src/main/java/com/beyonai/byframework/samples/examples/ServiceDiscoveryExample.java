package com.beyonai.byframework.samples.examples;

import com.iwhaleai.byai.framework.common.RedisClient;
import com.iwhaleai.byai.framework.core.discovery.DiscoveryClient;
import com.iwhaleai.byai.framework.core.discovery.ServiceInstance;
import lombok.extern.slf4j.Slf4j;

import java.util.List;
import java.util.Optional;

/**
 * 示例：服务发现过程。
 * 核心演示如何从 Redis 发现活跃的服务实例，支持负载均衡机制及本地异步刷新缓存。
 */
@Slf4j
public class ServiceDiscoveryExample {

    public static void main(String[] args) {
        // 1. 获取 Redis 连接客户端。
        // RedisClient.getInstance() 会自动尝试从系统环境变量读取配置。
        RedisClient redisClient = RedisClient.getInstance();

        // 2. 初始化 DiscoveryClient (缓存刷新间隔为 5 秒，默认也是 5 秒)
        DiscoveryClient discoveryClient = new DiscoveryClient(redisClient, 5);

        String serviceName = "springboot-sample-service";

        try {
            log.info("Starting service discovery for: {}", serviceName);

            // 3. 开启后台 watch，异步维护服务列表缓存
            discoveryClient.watch(serviceName);

            // 4. 展示不同阶段的服务发现
            for (int i = 1; i <= 5; i++) {
                log.info("--- Discovery Round {} ---", i);

                // 获取所有实例详情
                List<ServiceInstance> instances = discoveryClient.getInstances(serviceName);
                log.info("Total healthy instances found: {}", instances.size());
                instances.forEach(ins -> log.info("  Instance: {} @ {}:{} (weight: {})",
                        ins.getId(), ins.getHost(), ins.getPort(), ins.getWeight()));

                // 负载均衡策略演示：随机
                Optional<ServiceInstance> randomInstance = discoveryClient.discover(serviceName, "random");
                randomInstance.ifPresent(ins -> log.info(">> [Random] Selected instance: {}", ins.getId()));

                // 负载均衡策略演示：轮询
                Optional<ServiceInstance> rrInstance = discoveryClient.discover(serviceName, "round-robin");
                rrInstance.ifPresent(ins -> log.info(">> [Round-Robin] Selected instance: {}", ins.getId()));

                log.info("Waiting for next check...");
                Thread.sleep(5000); // 间隔 5 秒，匹配缓存刷新
            }

        } catch (InterruptedException e) {
            log.error("Discovery interrupted.", e);
            Thread.currentThread().interrupt();
        } finally {
            // 5. 退出时清理资源
            discoveryClient.close();
            redisClient.close();
        }
    }
}
