# Protocol API

Java SDK 的协议层位于 `com.iwhaleai.byai.framework.core.protocol` 包下，定义了 Agent 系统内部通信所需的命令（Command）、事件（Event）、消息头（MessageHeader）以及相关枚举类型。

---

## Commands

命令（Command）是 Worker 与 Gateway 之间通信的基本消息单元。所有命令都实现 `GatewayCommand` 接口。

### GatewayCommand

`GatewayCommand` 是所有命令的顶层接口。

```java
public interface GatewayCommand {
    /** 获取命令的动作类型 */
    ActionType actionType();

    /** 获取消息头 */
    MessageHeader header();
}
```

### AskAgentCommand

`AskAgentCommand` 用于向 Agent 发送任务请求，是最常用的命令类型。

```java
public class AskAgentCommand implements GatewayCommand {
    /** 获取消息内容 */
    public Object content();

    /** 获取消息头 */
    public MessageHeader header();

    /** 获取动作类型（始终为 ASK_AGENT） */
    public ActionType actionType();
}
```

使用示例：

```java
MessageHeader header = MessageHeader.builder()
    .messageId("msg_001")
    .sessionId("session_001")
    .traceId("trace_001")
    .targetAgentType("data_analyzer")
    .build();

AskAgentCommand command = AskAgentCommand.builder()
    .header(header)
    .content("请分析最近一周的销售数据")
    .build();

// 在 GatewayCommand 中使用
GatewayCommand cmd = command;
System.out.println("目标 Agent: " + cmd.header().getTargetAgentType());
System.out.println("内容: " + ((AskAgentCommand) cmd).content());
```

### CancelTaskCommand

`CancelTaskCommand` 用于取消正在执行的任务。

```java
public class CancelTaskCommand implements GatewayCommand {
    /** 获取目标消息 ID（要取消的消息） */
    public String targetMessageId();

    /** 获取消息头 */
    public MessageHeader header();

    /** 获取动作类型（始终为 CANCEL_TASK） */
    public ActionType actionType();
}
```

使用示例：

```java
MessageHeader header = MessageHeader.builder()
    .messageId("cancel_001")
    .sessionId("session_001")
    .build();

CancelTaskCommand cancelCmd = CancelTaskCommand.builder()
    .header(header)
    .targetMessageId("msg_001")
    .build();
```

### ResumeCommand

`ResumeCommand` 用于恢复之前被挂起的任务（例如用户完成输入后继续执行）。

```java
public class ResumeCommand implements GatewayCommand {
    /** 获取恢复时附带的内容（用户输入等） */
    public Object content();

    /** 获取消息头 */
    public MessageHeader header();

    /** 获取动作类型（始终为 RESUME） */
    public ActionType actionType();
}
```

使用示例：

```java
MessageHeader header = MessageHeader.builder()
    .messageId("resume_001")
    .sessionId("session_001")
    .parentMessageId("msg_001")
    .build();

ResumeCommand resumeCmd = ResumeCommand.builder()
    .header(header)
    .content("用户确认继续执行")
    .build();
```

### 自定义命令注册

`GatewayCommandFactory` 支持注册自定义命令类型，扩展协议层的能力。

```java
public class GatewayCommandFactory {
    /**
     * 注册自定义命令类型。
     *
     * @param actionType   动作类型标识
     * @param commandClass 命令类
     */
    public static void registerCommand(String actionType, Class<? extends GatewayCommand> commandClass);
}
```

使用示例：

```java
// 注册自定义命令
GatewayCommandFactory.registerCommand("MY_CUSTOM_ACTION", MyCustomCommand.class);
```

---

## MessageHeader

`MessageHeader` 使用 Builder 模式构造，包含消息的路由和元信息。

```java
public class MessageHeader {
    public static Builder builder();

    public static class Builder {
        public Builder messageId(String messageId);
        public Builder sessionId(String sessionId);
        public Builder traceId(String traceId);
        public Builder targetAgentType(String targetAgentType);
        public Builder parentMessageId(String parentMessageId);
        public Builder userCode(String userCode);
        public Builder userName(String userName);
        public Builder metadata(Map<String, Object> metadata);
        public MessageHeader build();
    }
}
```

### 属性表

| 属性 | 类型 | 描述 |
|------|------|------|
| `messageId` | `String` | 消息唯一标识 |
| `sessionId` | `String` | 会话 ID |
| `traceId` | `String` | 全局链路追踪 ID |
| `targetAgentType` | `String` | 目标 Agent 类型 |
| `parentMessageId` | `String` | 父消息 ID |
| `userCode` | `String` | 用户编码 |
| `userName` | `String` | 用户名称 |
| `metadata` | `Map<String, Object>` | 扩展元数据 |

### 使用示例

```java
MessageHeader header = MessageHeader.builder()
    .messageId("msg_001")
    .sessionId("session_abc")
    .traceId("trace_xyz")
    .targetAgentType("report_agent")
    .userCode("user_123")
    .userName("张三")
    .parentMessageId("parent_msg_000")
    .metadata(Map.of("priority", "high", "source", "web"))
    .build();
```

---

## Events

事件（Event）用于 Worker 向 Gateway 上报运行时信息，包括流式输出、状态变更、产物交付和用户交互。

### StreamChunkEvent

流式文本内容事件，用于逐步输出 Agent 的处理结果。

```java
public class StreamChunkEvent {
    /** 流式文本内容 */
    private String content;

    /** 事件类型，默认为 "answerDelta" */
    private String eventType;
}
```

使用示例：

```java
StreamChunkEvent chunk = new StreamChunkEvent();
chunk.setContent("正在处理第 1 步...");
chunk.setEventType("answerDelta");
```

### StateChangeEvent

状态变更事件，用于通知 Gateway 当前 Agent 的运行状态发生了变化。

```java
public class StateChangeEvent {
    /** 状态信息 */
    private String state;

    /** 事件类型，默认为 "stateChange" */
    private String eventType;
}
```

使用示例：

```java
StateChangeEvent stateEvent = new StateChangeEvent();
stateEvent.setState("正在调用外部 API...");
stateEvent.setEventType("reasoningLogDelta");
```

### ArtifactEvent

产物事件，用于传递生成的图片、文件等资源的链接。

```java
public class ArtifactEvent {
    /** 产物 URL */
    private String url;

    /** 事件类型，默认为 "artifact" */
    private String eventType;

    /** 附加元数据 */
    private Map<String, Object> metadata;
}
```

使用示例：

```java
ArtifactEvent artifact = new ArtifactEvent();
artifact.setUrl("https://cdn.example.com/reports/summary.pdf");
artifact.setEventType("artifact");
artifact.setMetadata(Map.of("fileName", "summary.pdf", "fileSize", 204800));
```

### AskUserEvent

用户交互事件，用于 Agent 需要等待用户输入时发送。

```java
public class AskUserEvent {
    /** 向用户展示的提示信息 */
    private String prompt;

    /** 事件类型，默认为 "askUser" */
    private String eventType;
}
```

使用示例：

```java
AskUserEvent askEvent = new AskUserEvent();
askEvent.setPrompt("请选择要生成报表的月份：");
askEvent.setEventType("askUser");
```

---

## ActionType 枚举

| 值 | 描述 |
|----|------|
| `ASK_AGENT` | 向 Agent 发送任务请求 |
| `RESUME` | 恢复挂起的任务 |
| `CANCEL_TASK` | 取消正在执行的任务 |
| `ASK_USER` | 向用户请求输入 |
| `ASK_AGENT_IDLE` | 向空闲 Agent 发送任务 |

---

## AgentState 枚举

| 值 | 描述 |
|----|------|
| `STARTING` | Agent 正在启动 |
| `PROCESSING` | Agent 正在处理任务 |
| `AWAITING_USER` | Agent 正在等待用户输入 |
| `COMPLETED` | Agent 任务已成功完成 |
| `FAILED` | Agent 任务执行失败 |
| `CANCELLING` | Agent 正在取消中 |
| `CANCELLED` | Agent 任务已被取消 |

---

## EventType 常量

| 值 | 描述 |
|----|------|
| `answerDelta` | 回答内容增量 |
| `finalAnswer` | 最终回答 |
| `reasoningLogDelta` | 推理或中间日志输出 |
| `reasoningLogStart` | 推理日志开始 |
| `reasoningLogEnd` | 推理日志结束 |
| `appStreamResponse` | 标记流结束 |
| `taskCreate` | 任务创建相关事件 |
| `stepComplete` | 步骤完成 |
| `taskStop` | 任务终止相关事件 |

---

## 完整使用示例

```java
public class ProtocolWorker extends GatewayWorker {

    @Override
    public List<String> getAgentTypes() {
        return List.of("protocol_demo");
    }

    @Override
    public Object processCommand(GatewayCommand command, AgentContext context) {
        // 1. 根据命令类型分发处理
        if (command instanceof AskAgentCommand askCmd) {
            return handleAskCommand(askCmd, context);
        } else if (command instanceof ResumeCommand resumeCmd) {
            return handleResumeCommand(resumeCmd, context);
        } else if (command instanceof CancelTaskCommand cancelCmd) {
            return handleCancelCommand(cancelCmd, context);
        }
        throw new IllegalArgumentException("Unknown command type: " + command.getClass());
    }

    private Object handleAskCommand(AskAgentCommand command, AgentContext context) {
        // 读取消息头
        MessageHeader header = command.header();
        System.out.println("[DEBUG] 处理消息: " + header.getMessageId());
        System.out.println("[DEBUG] 来源用户: " + header.getUserName());
        System.out.println("[DEBUG] 元数据: " + header.getMetadata());

        // 发送流式事件
        context.emitChunk("正在处理请求...");

        // 发送状态变更
        context.emitState("分析中");

        // 向用户询问
        context.askUser("请选择操作类型");

        // 发送产物事件
        context.emitArtifact("https://cdn.example.com/chart.png");

        return Map.of(
            "status", "COMPLETED",
            "content", "处理完成",
            "metadata", Map.of("duration_ms", 2500)
        );
    }

    private Object handleResumeCommand(ResumeCommand command, AgentContext context) {
        Object userInput = command.content();
        context.emitChunk("收到用户输入: " + userInput + "，继续执行...");
        return Map.of("status", "COMPLETED", "content", "已恢复并完成");
    }

    private Object handleCancelCommand(CancelTaskCommand command, AgentContext context) {
        System.out.println("收到取消请求，目标消息: " + command.targetMessageId());
        return Map.of("status", "CANCELLED", "content", "任务已取消");
    }
}
```
