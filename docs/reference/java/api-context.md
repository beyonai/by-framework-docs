# Context API

Java SDK 中的 `AgentContext` 位于 `com.iwhaleai.byai.framework.worker` 包下，为 Agent 任务执行提供完整的运行时上下文环境，包含会话管理、事件上报、Agent 间调用及状态管理能力。

## AgentContext

`AgentContext` 是每次任务执行时由框架注入的上下文对象，Worker 通过它来与 Gateway 进行交互。

### 基础属性

| 方法 | 返回类型 | 描述 |
|------|---------|------|
| `getSessionId()` | `String` | 获取当前会话 ID |
| `getTraceId()` | `String` | 获取全局链路追踪 ID |
| `getCurrentAgentType()` | `String` | 获取当前 Agent 类型 |
| `getCurrentMessageId()` | `String` | 获取当前处理的消息 ID |

### 事件上报 (Emission)

#### emitChunk

```java
/**
 * 发送流式文本片段。
 * @param content 流式文本内容
 */
public void emitChunk(String content);
```

使用示例：

```java
context.emitChunk("正在分析数据...");
context.emitChunk("已完成第 1 步分析。");
```

#### emitState

```java
/**
 * 发送状态变更。
 * @param state 状态描述或状态信息
 */
public void emitState(String state);
```

使用示例：

```java
context.emitState("PROCESSING");
context.emitState("等待外部服务响应...");
```

#### emitArtifact

```java
/**
 * 发送产物或文件链接。
 * @param url 产物 URL（图片、文件等）
 */
public void emitArtifact(String url);
```

使用示例：

```java
context.emitArtifact("https://cdn.example.com/output/report.pdf");
context.emitArtifact("https://cdn.example.com/images/chart_001.png");
```

#### askUser

```java
/**
 * 挂起当前 Agent 执行，向用户发起输入请求。
 * 用户回复后将自动继续执行。
 *
 * @param prompt 向用户展示的提示信息
 * @return 用户输入的结果
 */
public Map<String, Object> askUser(String prompt);
```

使用示例：

```java
Map<String, Object> userInput = context.askUser("请确认是否继续执行？");
String confirm = (String) userInput.get("content");
```

### Agent 间调用

`callAgent` 提供多个重载方法，用于向其他 Agent 发起调用。

#### 简易调用

```java
/**
 * 简化版 Agent 调用。
 *
 * @param targetAgentType 目标 Agent 类型
 * @param content 发送的内容
 * @return 目标 Agent 的执行结果
 */
public Map<String, Object> callAgent(String targetAgentType, String content);
```

使用示例：

```java
Map<String, Object> result = context.callAgent("data_analyzer", "分析这批数据");
String analysisResult = (String) result.get("content");
```

#### 完整参数调用

```java
/**
 * 完整版 Agent 调用，支持全部参数。
 *
 * @param targetAgentType  目标 Agent 类型
 * @param content          发送的内容
 * @param extraPayload     额外负载数据
 * @param waitForReply     是否等待回复
 * @param metadata         元数据
 * @param messageId        消息 ID（可为 null）
 * @param parentMessageId  父消息 ID（可为 null）
 * @return 目标 Agent 的执行结果
 */
public Map<String, Object> callAgent(
    String targetAgentType,
    String content,
    Map<String, Object> extraPayload,
    boolean waitForReply,
    Map<String, Object> metadata,
    String messageId,
    String parentMessageId
);
```

使用示例：

```java
Map<String, Object> result = context.callAgent(
    "report_generator",
    "生成月度报表",
    Map.of("format", "pdf", "lang", "zh"),
    true,
    Map.of("priority", "high"),
    null,
    null
);
```

### 任务组 (Scatter-Gather)

#### dispatchGroup

```java
/**
 * 向多个 Agent 同时分发任务（散射）。
 *
 * @param tasks        任务列表，每个元素为一个包含目标 Agent 类型和内容的 Map
 * @param waitForReply 是否等待所有子任务回复
 * @return 分发结果，包含 taskGroupId
 */
public Map<String, Object> dispatchGroup(List<Map<String, Object>> tasks, boolean waitForReply);
```

使用示例：

```java
List<Map<String, Object>> tasks = List.of(
    Map.of("targetAgentType", "data_collector", "content", "收集销售数据"),
    Map.of("targetAgentType", "data_collector", "content", "收集用户数据"),
    Map.of("targetAgentType", "market_analyzer", "content", "分析市场趋势")
);

Map<String, Object> dispatchResult = context.dispatchGroup(tasks, true);
String taskGroupId = (String) dispatchResult.get("taskGroupId");
```

#### collectGroupResults

```java
/**
 * 收集任务组中所有子任务的结果（聚集）。
 *
 * @param taskGroupId 任务组 ID
 * @return 所有子任务的执行结果
 */
public Map<String, Object> collectGroupResults(String taskGroupId);
```

使用示例：

```java
Map<String, Object> results = context.collectGroupResults(taskGroupId);
List<Map<String, Object>> taskResults = (List<Map<String, Object>>) results.get("results");

for (Map<String, Object> r : taskResults) {
    System.out.println("任务 " + r.get("messageId") + " 完成: " + r.get("content"));
}
```

### 任务取消检查

#### isCancelRequested

```java
/**
 * 检查当前任务是否已被请求取消。
 *
 * @return true 表示已收到取消请求
 */
public boolean isCancelRequested();
```

使用示例：

```java
for (int i = 0; i < 100; i++) {
    if (context.isCancelRequested()) {
        System.out.println("收到取消请求，停止处理。");
        break;
    }
    // 执行批量处理...
    processBatch(i);
}
```

#### checkCancelled

```java
/**
 * 如果任务已被请求取消，则抛出运行时异常终止执行。
 * 建议在耗时循环或关键检查点中调用。
 */
public void checkCancelled();
```

使用示例：

```java
// 在每个步骤开始前检查
context.checkCancelled();
stepOne();

context.checkCancelled();
stepTwo();
```

---

## 完整使用示例

```java
public class MyAgentWorker extends GatewayWorker {

    @Override
    public List<String> getAgentTypes() {
        return List.of("my_agent");
    }

    @Override
    public Object processCommand(GatewayCommand command, AgentContext context) {
        // 1. 发送流式提示
        context.emitChunk("开始处理您的请求...");

        // 2. 向用户提问
        Map<String, Object> userResponse = context.askUser("请选择分析维度：销售 / 用户 / 市场");
        String dimension = (String) userResponse.get("content");

        // 3. 调用子 Agent
        context.emitChunk("正在调用分析引擎...");
        Map<String, Object> analysisResult = context.callAgent(
            "analysis_engine",
            "分析维度: " + dimension,
            Map.of("timeRange", "last_30_days"),
            true,
            Map.of(),
            null,
            null
        );

        // 4. 散射-聚集多个分析任务
        List<Map<String, Object>> tasks = List.of(
            Map.of("targetAgentType", "chart_builder", "content", analysisResult),
            Map.of("targetAgentType", "report_writer", "content", analysisResult)
        );
        Map<String, Object> dispatchResult = context.dispatchGroup(tasks, true);
        String groupId = (String) dispatchResult.get("taskGroupId");

        // 5. 定期检查取消状态
        context.checkCancelled();

        // 6. 收集结果
        Map<String, Object> finalResults = context.collectGroupResults(groupId);

        // 7. 发送产物
        context.emitArtifact("https://reports.example.com/latest/report.pdf");

        // 8. 返回最终结果
        return finalResults;
    }
}
```
