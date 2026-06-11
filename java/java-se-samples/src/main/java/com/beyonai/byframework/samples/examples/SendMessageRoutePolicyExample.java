package com.beyonai.byframework.samples.examples;

import com.iwhaleai.byai.framework.client.ByaiGatewayClient;
import com.iwhaleai.byai.framework.client.GatewayClient;
import com.iwhaleai.byai.framework.common.RedisClient;
import com.iwhaleai.byai.framework.core.availability.RoutePolicy;

import java.util.UUID;

/**
 * Java 版本的 route_policy 样例。
 * 演示如何使用最新的 RoutePolicy 策略进行可用性路由控制。
 *
 * <p>
 * 对标 Python 的 send_message_route_policy.py。
 */
public class SendMessageRoutePolicyExample {

        private static final String FAIL_FAST_AGENT_TYPE = env("BYAI_FAIL_FAST_AGENT_TYPE",
                        env("BYAI_TARGET_AGENT_TYPE", "route-policy-online-agent"));
        private static final String WAKE_AND_WAIT_AGENT_TYPE = env("BYAI_WAKE_AND_WAIT_AGENT_TYPE",
                        "route-policy-wakeup-agent");
        private static final String WAKE_AND_QUEUE_AGENT_TYPE = env("BYAI_WAKE_AND_QUEUE_AGENT_TYPE",
                        "route-policy-queued-agent");
        private static final String SEND_ANYWAY_AGENT_TYPE = env("BYAI_SEND_ANYWAY_AGENT_TYPE",
                        "route-policy-manual-agent");
        private static final String USER_CODE = env("BYAI_USER_CODE", "demo-user");

        public static void main(String[] args) {
                // 1. 初始化 Redis 客户端 (自动从环境变量读取配置)。
                RedisClient redisClient = RedisClient.getInstance();

                // 2. 创建 ByaiGatewayClient。
                ByaiGatewayClient client = new ByaiGatewayClient(redisClient);

                // 3. 使用不同路由策略发送消息。
                sendWithPolicy(client, FAIL_FAST_AGENT_TYPE, USER_CODE, RoutePolicy.FAIL_FAST,
                                "FAIL_FAST: 只有在线 Worker 存在时才会投递。");

                sendWithPolicy(client, WAKE_AND_WAIT_AGENT_TYPE, USER_CODE, RoutePolicy.WAKE_AND_WAIT,
                                "WAKE_AND_WAIT: 如果当前没有在线 Worker，请先触发唤醒并等待可用后再投递。");

                sendWithPolicy(client, WAKE_AND_QUEUE_AGENT_TYPE, USER_CODE, RoutePolicy.WAKE_AND_QUEUE,
                                "WAKE_AND_QUEUE: 如果当前没有在线 Worker，请触发唤醒并先进入 pending delivery 队列。");

                sendWithPolicy(client, SEND_ANYWAY_AGENT_TYPE, USER_CODE, RoutePolicy.SEND_ANYWAY,
                                "SEND_ANYWAY: 跳过在线检查，直接写入目标 agent_type 控制队列。");

                // 4. 清理资源。
                redisClient.close();
        }

        private static void sendWithPolicy(
                        ByaiGatewayClient client,
                        String targetAgentType,
                        String userCode,
                        String routePolicy,
                        String content) {

                String sessionId = "session_" + UUID.randomUUID().toString().replace("-", "").substring(0, 8);

                System.out.println();
                System.out.println("--- route_policy=" + routePolicy + " ---");
                System.out.println("  target_agent_type: " + targetAgentType);
                System.out.println("  content: " + content);

                // 调用 16 参数版本的 sendMessage，传入指定 routePolicy 和超时时间。
                GatewayClient.SendResponse response = client.sendMessage(
                                targetAgentType,
                                sessionId,
                                content,
                                userCode,
                                null, // userName
                                null, // actionType (默认 ASK_AGENT)
                                null, // parentMessageId
                                null, // messageId (自动生成)
                                null, // traceId (自动生成)
                                null, // payload
                                null, // metadata
                                null, // targetWorkerId
                                routePolicy,
                                10000L, // availabilityTimeoutMs (10秒超时)
                                null, // region
                                null  // priority
                );

                // 打印结果。
                System.out.println("  success:      " + response.isSuccess());
                System.out.println("  status:       " + response.getStatus());
                System.out.println("  message_id:   " + response.getMessageId());
                System.out.println("  trace_id:     " + response.getTraceId());
                if (response.getTargetWorkerId() != null && !response.getTargetWorkerId().isEmpty()) {
                        System.out.println("  worker_id:    " + response.getTargetWorkerId());
                }
                if (response.getError() != null) {
                        System.out.println("  error:        " + response.getError());
                }
                if (response.getErrorCode() != null) {
                        System.out.println("  error_code:   " + response.getErrorCode());
                }

                if (response.isSuccess()) {
                        System.out.println("  > 消息投递处理结果：" + response.getStatus());
                } else {
                        System.out.println("  > 消息未投递，错误原因：" + response.getError());
                }
        }

        private static String env(String key, String defaultValue) {
                String value = System.getenv(key);
                return value != null && !value.isEmpty() ? value : defaultValue;
        }
}
