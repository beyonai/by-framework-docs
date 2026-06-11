package com.beyonai.byframework.samples.examples;

import com.iwhaleai.byai.framework.client.ByaiGatewayClient;
import com.iwhaleai.byai.framework.client.GatewayClient;
import com.iwhaleai.byai.framework.common.RedisClient;
import com.iwhaleai.byai.framework.core.protocol.ActionType;

import java.util.HashMap;
import java.util.Map;

/**
 * Java 版本的 sendMessage 样例。
 * 演示如何初始化 GatewayClient 并发送消息给指定类型的 Agent。
 */
public class SendMessageExample {

    public static void main(String[] args) {
        // 1. 初始化 Redis 客户端。
        // RedisClient.getInstance() 会自动从环境变量读取配置：
        // REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_USERNAME, REDIS_PASSWORD
        // 如果环境变量未设置，默认连接 localhost:6379, db 0
        RedisClient redisClient = RedisClient.getInstance();

        // 2. 创建 ByaiGatewayClient。
        // 它会自动包含 ByaiMessageInterceptor，支持直接发送 BaiYingMessage 或其列表。
        ByaiGatewayClient client = new ByaiGatewayClient(redisClient);

        // 3. 准备消息参数。
        String targetAgentType = "langgraph-extension-demo";
        String sessionId = "session-demo-a-b-a12";
        String content = "查一下广州的天气";
        String userCode = "user-1";
        String userName = "测试用户";

        // 扩展参数 (可选)
        Map<String, Object> payload = new HashMap<>();
        payload.put("source", "java-example");
        payload.put("timestamp", System.currentTimeMillis());

        Map<String, Object> metadata = new HashMap<>();
        metadata.put("user_tag", "vip");

        System.out.println("正在向 Agent (" + targetAgentType + ") 发送消息 (使用 Interceptor 模式)...");

        // 4. 发送消息。
        // 虽然 content 是 String，但 ByaiGatewayClient 也支持 BaiYingMessage 类型，
        // 拦截器会自动识别并处理转换。
        // Java SDK 会自动生成 trace_id / trace_parent_span_id，并 best-effort 写入
        // Redis trace meta、client.dispatch span 和 session/worker/agent 索引。
        GatewayClient.SendResponse response = client.sendMessage(
                targetAgentType,
                sessionId,
                content,
                userCode,
                userName,
                ActionType.ASK_AGENT,
                null,
                null,
                null,
                payload,
                metadata);

        // 5. 处理响应。
        if (response.isSuccess()) {
            System.out.println("✅ 消息发送成功！");
            System.out.println("   Message ID: " + response.getMessageId());
            System.out.println("   Trace ID: " + response.getTraceId());
            System.out.println("   Target Worker: " + response.getTargetWorkerId());
            System.out.println("   Status: " + response.getStatus());
            System.out.println("   Trace Dashboard 可使用该 Trace ID 查询完整链路。");
        } else {
            System.err.println("❌ 消息发送失败！");
            System.err.println("   Error: " + response.getError());
        }

        // 6. 关闭连接池 (生产环境通常在应用关闭时执行)。
        redisClient.close();
    }
}
