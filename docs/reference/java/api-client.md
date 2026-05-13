# Client API

Java SDK 的客户端 API 位于 `com.iwhaleai.byai.framework.client` 包下，提供了向 Agent 网关发送消息、取消任务以及拦截器机制的能力。

## GatewayClient\<T\>

`GatewayClient` 是泛型客户端基类，通过 Redis 与 Gateway 通信，支持消息发送、任务取消和拦截器链。

### 构造方法

```java
/**
 * 构造一个 GatewayClient 实例。
 *
 * @param redisClient Redis 客户端实例
 */
public GatewayClient(RedisClient redisClient);
```

使用示例：

```java
RedisClient redisClient = new RedisClient("localhost", 6379);
GatewayClient<Object> client = new GatewayClient<>(redisClient);
```

### sendMessage (简易版)

```java
/**
 * 简化版消息发送。
 *
 * @param targetAgentType 目标 Agent 类型
 * @param sessionId       会话 ID
 * @param content         消息内容
 * @return SendResponse 响应对象
 */
public SendResponse sendMessage(
    String targetAgentType,
    String sessionId,
    Object content
);
```

使用示例：

```java
SendResponse response = client.sendMessage("my_agent", "session_001", "帮我分析数据");
if (response.isSuccess()) {
    System.out.println("消息已发送，messageId: " + response.getMessageId());
}
```

### sendMessage (完整版)

```java
/**
 * 完整版消息发送，支持全部参数。
 *
 * @param targetAgentType 目标 Agent 类型
 * @param sessionId       会话 ID
 * @param content         消息内容
 * @param userCode        用户编码
 * @param userName        用户名称
 * @param actionType      动作类型
 * @param taskId          任务 ID
 * @param plan            任务计划
 * @param artifacts       产物列表
 * @param payload         额外负载
 * @param metadata        元数据
 * @return SendResponse 响应对象
 */
public SendResponse sendMessage(
    String targetAgentType,
    String sessionId,
    Object content,
    String userCode,
    String userName,
    ActionType actionType,
    String taskId,
    Object plan,
    Object artifacts,
    Map<String, Object> payload,
    Map<String, Object> metadata
);
```

使用示例：

```java
SendResponse response = client.sendMessage(
    "report_agent",
    "session_001",
    "生成月度销售报表",
    "user_123",
    "张三",
    ActionType.ASK_AGENT_IDLE,
    "task_456",
    null,
    null,
    Map.of("format", "pdf", "language", "zh"),
    Map.of("priority", "high")
);
```

### sendCommand

```java
/**
 * 发送预构造的 GatewayCommand 对象。
 *
 * @param command 预构造的命令对象
 * @return SendResponse 响应对象
 */
public SendResponse sendCommand(GatewayCommand command);
```

使用示例：

```java
MessageHeader header = MessageHeader.builder()
    .messageId("msg_001")
    .sessionId("session_001")
    .traceId("trace_001")
    .targetAgentType("my_agent")
    .build();

AskAgentCommand command = AskAgentCommand.builder()
    .header(header)
    .content("分析这组数据")
    .build();

SendResponse response = client.sendCommand(command);
```

### cancelTask

```java
/**
 * 取消指定的任务。
 *
 * @param messageId  目标消息 ID
 * @param sessionId  会话 ID
 * @param reason     取消原因
 * @param cancelType 取消类型
 * @param source     取消来源
 * @param strategy   取消策略（如 "graceful" 或 "force"）
 * @return CancelTaskResponse 响应对象
 */
public CancelTaskResponse cancelTask(
    String messageId,
    String sessionId,
    String reason,
    String cancelType,
    String source,
    String strategy
);
```

使用示例：

```java
CancelTaskResponse cancelResp = client.cancelTask(
    "msg_001",
    "session_001",
    "用户手动取消",
    "user_cancel",
    "client",
    "graceful"
);

if (cancelResp.isSuccess()) {
    System.out.println("任务已成功取消");
}
```

### addInterceptor

```java
/**
 * 添加网关拦截器。
 *
 * @param interceptor 拦截器实例
 */
public void addInterceptor(GatewayInterceptor interceptor);
```

使用示例：

```java
client.addInterceptor(new GatewayInterceptor() {
    @Override
    public void beforeSend(MessageHeader header, Object content) {
        System.out.println("即将发送消息到: " + header.getTargetAgentType());
    }

    @Override
    public void afterSend(MessageHeader header, SendResponse response) {
        System.out.println("消息发送完成: " + response.getMessageId());
    }
});
```

---

## ByaiGatewayClient

`ByaiGatewayClient` 继承自 `GatewayClient`，自动注册了 `ByaiMessageInterceptor`，用于适配 BeyonAI 平台内部的消息格式。

```java
/**
 * ByaiGatewayClient 构造方法。
 * 自动包含 ByaiMessageInterceptor，无需手动添加。
 *
 * @param redisClient Redis 客户端实例
 */
public ByaiGatewayClient(RedisClient redisClient);
```

使用示例：

```java
RedisClient redisClient = new RedisClient("localhost", 6379);
ByaiGatewayClient client = new ByaiGatewayClient(redisClient);

// 直接使用，无需额外配置拦截器
SendResponse response = client.sendMessage("agent_type", "session_001", "Hello");
```

---

## GatewayInterceptor

`GatewayInterceptor` 接口提供了消息发送前后的拦截能力，可用于日志记录、参数校验、消息转换等场景。

```java
public interface GatewayInterceptor {
    /**
     * 发送前拦截，可修改消息头或内容。
     */
    void beforeSend(MessageHeader header, Object content);

    /**
     * 发送后拦截，可处理响应结果。
     */
    void afterSend(MessageHeader header, SendResponse response);
}
```

使用示例：

```java
GatewayInterceptor logInterceptor = new GatewayInterceptor() {
    @Override
    public void beforeSend(MessageHeader header, Object content) {
        System.out.println("[INFO] 发送消息 - target: " + header.getTargetAgentType());
    }

    @Override
    public void afterSend(MessageHeader header, SendResponse response) {
        if (response.isSuccess()) {
            System.out.println("[INFO] 消息发送成功 - messageId: " + response.getMessageId());
        } else {
            System.err.println("[ERROR] 消息发送失败 - " + response.getError());
        }
    }
};

client.addInterceptor(logInterceptor);
```

---

## SendResponse

`SendResponse` 是 `GatewayClient` 的内部类，封装了消息发送的响应结果。

```java
public class SendResponse {
    /** 消息发送是否成功 */
    public boolean isSuccess();

    /** 获取分配的消息 ID */
    public String getMessageId();

    /** 获取目标 Worker ID */
    public String getTargetWorkerId();

    /** 获取发送状态 */
    public String getStatus();

    /** 获取错误信息（如有） */
    public String getError();
}
```

### 属性表

| 方法 | 返回类型 | 描述 |
|------|---------|------|
| `isSuccess()` | `boolean` | 消息是否发送成功 |
| `getMessageId()` | `String` | 分配的消息 ID |
| `getTargetWorkerId()` | `String` | 目标 Worker ID |
| `getStatus()` | `String` | 发送状态 |
| `getError()` | `String` | 错误信息（成功时为空字符串） |

---

## CancelTaskResponse

`CancelTaskResponse` 是 `GatewayClient` 的内部类，封装了任务取消操作的响应结果。

```java
public class CancelTaskResponse {
    /** 取消操作是否成功 */
    public boolean isSuccess();

    /** 被取消的消息 ID */
    public String getMessageId();

    /** 取消状态 */
    public String getStatus();

    /** 错误信息（如有） */
    public String getError();
}
```

### 属性表

| 方法 | 返回类型 | 描述 |
|------|---------|------|
| `isSuccess()` | `boolean` | 取消操作是否成功 |
| `getMessageId()` | `String` | 被取消的消息 ID |
| `getStatus()` | `String` | 取消操作状态 |
| `getError()` | `String` | 错误信息（成功时为空字符串） |

---

## 完整使用示例

```java
// 1. 初始化客户端
RedisClient redisClient = new RedisClient("localhost", 6379);
ByaiGatewayClient client = new ByaiGatewayClient(redisClient);

// 2. 添加自定义拦截器
client.addInterceptor(new GatewayInterceptor() {
    @Override
    public void beforeSend(MessageHeader header, Object content) {
        System.out.println("[LOG] 准备发送消息到: " + header.getTargetAgentType());
    }

    @Override
    public void afterSend(MessageHeader header, SendResponse response) {
        System.out.println("[LOG] 发送结果: " + response.getStatus());
    }
});

// 3. 发送消息
SendResponse response = client.sendMessage(
    "data_analyzer",
    "session_abc",
    "请分析最近一周的数据",
    "user_001",
    "李四",
    ActionType.ASK_AGENT_IDLE,
    null,
    null,
    null,
    Map.of("dataSource", "mysql"),
    Map.of("priority", "normal")
);

// 4. 检查响应
if (response.isSuccess()) {
    System.out.println("消息发送成功，messageId: " + response.getMessageId());
    System.out.println("目标 Worker: " + response.getTargetWorkerId());
} else {
    System.err.println("消息发送失败: " + response.getError());
}

// 5. 取消任务（如果需要）
CancelTaskResponse cancelResp = client.cancelTask(
    response.getMessageId(),
    "session_abc",
    "不再需要结果",
    "user_cancel",
    "client",
    "graceful"
);

System.out.println("取消结果: " + cancelResp.isSuccess());
```
