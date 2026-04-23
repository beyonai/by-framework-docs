package com.beyonai.byframework.samples.examples;

import com.iwhaleai.byai.framework.common.RedisClient;
import com.iwhaleai.byai.framework.core.discovery.ServiceRegistry;
import lombok.extern.slf4j.Slf4j;

/**
 * 示例：注册服务但不发送心跳。
 * 适用于静态服务，或者由外部系统管理生命周期的服务。
 */
@Slf4j
public class ServiceRegistryNoHeartbeatExample {

    public static void main(String[] args) {
        RedisClient redisClient = RedisClient.getInstance();
        ServiceRegistry registry = new ServiceRegistry(redisClient);

        String serviceName = "static-service";
        int port = 8080;

        log.info("正在执行‘仅注册’操作 (不启动后台心跳线程): {}", serviceName);

        // 使用新提供的 registerOnly 方法
        // 该方法会将实例信息写入 Redis，但不会启动定时心跳任务
        registry.registerOnly(serviceName, port);

        log.info("服务已注册。实例 ID: {}", registry.getCurrentInstance().getId());
        log.info("注意：由于未开启心跳，除非调用方配置为‘不探活’，否则该实例可能很快被视为下线。");

        try {
            // 这里我们不需要挂起程序来维持心跳，因为根本没有心跳线程
            log.info("注册完成，程序即将退出。");
        } finally {
            redisClient.close();
        }
    }
}
