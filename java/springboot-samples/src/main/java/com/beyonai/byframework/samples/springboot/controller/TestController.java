package com.beyonai.byframework.samples.springboot.controller;

import com.iwhaleai.byai.gateway.sdk.core.discovery.ServiceRegistry;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.Map;

/**
 * 示例接口：返回当前服务的注册状态信息。
 */
@RestController
@RequiredArgsConstructor
public class TestController {

    private final ServiceRegistry serviceRegistry;

    @GetMapping("/status")
    public Map<String, Object> getStatus() {
        Map<String, Object> result = new HashMap<>();
        result.put("status", "UP");
        result.put("instance", serviceRegistry.getCurrentInstance());
        result.put("timestamp", System.currentTimeMillis());
        return result;
    }
}
