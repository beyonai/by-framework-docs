package com.beyonai.byframework.samples.examples;

import com.iwhaleai.byai.framework.common.RedisClient;
import com.iwhaleai.byai.framework.core.discovery.DiscoveryClient;
import com.iwhaleai.byai.framework.util.http.DiscoveryHttpClient;
import com.iwhaleai.byai.framework.util.http.HttpResponse;
import com.iwhaleai.byai.framework.util.http.RetryConfig;
import lombok.extern.slf4j.Slf4j;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

/**
 * 示例：使用 DiscoveryHttpClient 进行服务发现调用。
 *
 * 该示例演示如何：
 * 1. 初始化 Redis 和服务发现客户端
 * 2. 配置 DiscoveryHttpClient 进行服务调用
 * 3. 使用 GET/POST 请求调用服务
 * 4. 当请求失败时自动切换到其他健康节点重试
 */
@Slf4j
public class DiscoveryHttpClientExample {

    public static void main(String[] args) {
        // 1. 获取 Redis 连接客户端
        RedisClient redisClient = RedisClient.getInstance();

        // 2. 初始化 DiscoveryClient (缓存刷新间隔为 5 秒)
        DiscoveryClient discoveryClient = new DiscoveryClient(redisClient, 5);

        // 3. 配置重试策略 (节点切换重试)
        // 当请求失败或返回 502, 503, 504 时，
        // DiscoveryHttpClient 会自动尝试发现另一个健康的节点并重试
        RetryConfig retryConfig = RetryConfig.builder()
                .maxAttempts(3)
                .retryOnStatusCodes(java.util.Set.of(502, 503, 504))
                .build();

        String serviceName = System.getenv("SERVICE_NAME");
        if (serviceName == null || serviceName.isEmpty()) {
            serviceName = "springboot-sample-service";
        }

        log.info("准备调用服务: {}", serviceName);

        // 4. 使用 DiscoveryHttpClient 进行调用
        try (DiscoveryHttpClient client = DiscoveryHttpClient.builder()
                .discoveryClient(discoveryClient)
                .retryConfig(retryConfig)
                .build()) {

            // 演示 GET 请求
            log.info("--- 演示 GET 请求 (path: /) ---");
            try {
                HttpResponse response = client.get(serviceName, "/", null, null)
                        .get(30, TimeUnit.SECONDS);

                if (response.isSuccess()) {
                    log.info("[+] 成功! 响应状态码: {}", response.getStatusCode());
                    log.info("    内容: {}", response.getData());
                } else {
                    log.warn("[!] 请求失败: {}", response.getStatusCode());
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                log.error("[!] 请求被中断", e);
            } catch (ExecutionException | TimeoutException e) {
                log.error("[!] 请求执行失败: {}", e.getMessage(), e);
            }

            // 演示 POST 请求
            log.info("--- 演示 POST 请求 (path: /api/echo) ---");
            try {
                Map<String, Object> payload = new HashMap<>();
                payload.put("message", "hello beyondai");
                payload.put("data", java.util.List.of(1, 2, 3));

                HttpResponse response = client.post(serviceName, "/api/echo", null, payload, null)
                        .get(30, TimeUnit.SECONDS);

                if (response.isSuccess()) {
                    log.info("[+] 成功! 响应状态码: {}", response.getStatusCode());
                    log.info("    内容: {}", response.getData());
                } else {
                    log.warn("[!] 请求失败: {}", response.getStatusCode());
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                log.error("[!] 请求被中断", e);
            } catch (ExecutionException | TimeoutException e) {
                log.error("[!] 请求执行失败: {}", e.getMessage(), e);
            }

        } catch (Exception e) {
            log.error("[!] 发生异常 (可能是因为没有启动提供者): {}", e.getMessage(), e);
        } finally {
            // 5. 清理资源
            discoveryClient.close();
            redisClient.close();
            log.info("[-] 演示结束。");
        }
    }
}
