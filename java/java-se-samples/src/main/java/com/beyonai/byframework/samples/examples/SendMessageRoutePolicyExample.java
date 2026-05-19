package com.beyonai.byframework.samples.examples;

import com.iwhaleai.byai.framework.client.ByaiGatewayClient;
import com.iwhaleai.byai.framework.client.GatewayClient;
import com.iwhaleai.byai.framework.common.RedisClient;
import com.iwhaleai.byai.framework.core.availability.AvailabilityStatus;
import com.iwhaleai.byai.framework.core.availability.RoutePolicy;

import java.util.UUID;

/**
 * Java 版本的 route_policy 样例。
 * 演示如何使用新的 route_policy API 替代 require_online_worker 进行可用性控制。
 *
 * <p>
 * 对标 Python 的 send_message_route_policy.py。
 */
public class SendMessageRoutePolicyExample {

        private static final String FAIL_FAST_AGENT_TYPE = env("BYAI_FAIL_FAST_AGENT_TYPE",
                        env("BYAI_TARGET_AGENT_TYPE", "route-policy-online-agent"));
        private static final String WAKE_AND_WAIT_AGENT_TYPE = env("BYAI_WAKE_AND_WAIT_AGENT_TYPE",
                        "route-policy-child-agent");
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

                // 3. 依次使用四种 RoutePolicy 发送消息。
                sendWithPolicy(client, FAIL_FAST_AGENT_TYPE, USER_CODE, RoutePolicy.FAIL_FAST,
                                "FAIL_FAST: 只有在线 Worker 存在时才会投递。");

                sendWithPolicy(client, WAKE_AND_WAIT_AGENT_TYPE, USER_CODE, RoutePolicy.WAKE_AND_WAIT,
                                "如果当前没有在线 Worker，请先触发唤醒并等待可用后再投递。");

                sendWithPolicy(client, WAKE_AND_QUEUE_AGENT_TYPE, USER_CODE, RoutePolicy.WAKE_AND_QUEUE,
                                "如果当前没有在线 Worker，请触发唤醒并先进入 pending delivery。");

                sendWithPolicy(client, SEND_ANYWAY_AGENT_TYPE, USER_CODE, RoutePolicy.SEND_ANYWAY,
                                "跳过在线检查，直接写入目标 agent_type 控制队列。");

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

                // 调用完整参数的 sendMessage，传入 route_policy 和 availability_timeout_ms。
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
                                routePolicy, // routePolicy
                                10_000L, // availabilityTimeoutMs (10s)
                                null, // region
                                null // priority
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

                // 特殊状态说明。
                if (AvailabilityStatus.QUEUE_PENDING.equals(response.getStatus())) {
                        System.out.println("  > 消息已进入 pending queue，等待 Worker 上线后投递。");
                } else if (AvailabilityStatus.WAIT_AND_DELIVER.equals(response.getStatus())) {
                        System.out.println("  > Worker 已唤醒，消息已投递。");
                }
        }

        private static String env(String key, String defaultValue) {
                String value = System.getenv(key);
                return value != null && !value.isEmpty() ? value : defaultValue;
        }
}
