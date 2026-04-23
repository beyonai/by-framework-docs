package com.beyonai.byframework.samples.examples;

import com.iwhaleai.byai.framework.common.Constants;
import com.iwhaleai.byai.framework.common.RedisClient;
import com.iwhaleai.byai.framework.core.discovery.DiscoveryClient;
import com.iwhaleai.byai.framework.util.http.DiscoveryHttpClient;
import com.iwhaleai.byai.framework.util.http.HttpResponse;
import lombok.extern.slf4j.Slf4j;

import java.util.concurrent.TimeUnit;

/**
 * 示例：发送请求时不进行服务探活。
 * 适用于调用那些不发心跳的静态服务，或者对实时性要求极高且确定服务在线的场景。
 */
@Slf4j
public class DiscoveryNoLivenessExample {

    public static void main(String[] args) {
        RedisClient redisClient = RedisClient.getInstance();
        DiscoveryClient discoveryClient = new DiscoveryClient(redisClient, 5);

        String serviceName = "static-service";

        log.info("准备调用服务（跳过健康检查）: {}", serviceName);

        // 通过 DiscoveryHttpClient 进行调用，并配置健康阈值为 SD_NO_HEALTH_CHECK (-1)
        // 这样即使实例在 Redis 中的心跳分数已过期，依然会被选中并尝试调用
        try (DiscoveryHttpClient client = DiscoveryHttpClient.builder()
                .discoveryClient(discoveryClient)
                .healthThresholdMs(Constants.SD_NO_HEALTH_CHECK)
                .build()) {

            HttpResponse response = client.get(serviceName, "/", null, null)
                    .get(10, TimeUnit.SECONDS);

            if (response.isSuccess()) {
                log.info("[+] 调用成功! 响应内容: {}", response.getData());
            } else {
                log.warn("[!] 调用返回失败码: {}", response.getStatusCode());
            }

        } catch (Exception e) {
            log.error("[!] 调用发生异常: ", e);
        } finally {
            discoveryClient.close();
            redisClient.close();
        }
    }
}
