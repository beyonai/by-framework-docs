# Plugin API

在 Java SDK 中，插件体系基于 `PluginRegistry` 构建。与 Python SDK 中显式的 `Plugin` 抽象基类不同，Java SDK 将 `GatewayWorker` 作为主要的扩展点，并通过 `PluginRegistry` 来管理插件式组件。这种架构设计使 Java 开发者可以更直接地利用强类型特性来组织可复用的业务模块。

## 架构对比

| 概念 | Python SDK | Java SDK |
|------|-----------|----------|
| 扩展基类 | `Plugin` 抽象基类 | `GatewayWorker` 抽象类（直接扩展） |
| 配置注册 | `Plugin.register_agent_configs()` | `GatewayWorker.getAgentTypes()` + `PluginRegistry` |
| 插件注册 | `PluginRegistry.register_bundle()` | `PluginRegistry.registerBundle()` |
| 生命周期钩子 | `Plugin` 的生命周期方法 | Worker 配置中的回调 / 钩子方法 |

在 Java SDK 中，通常不需要单独定义一个 "Plugin" 类。开发者直接继承 `GatewayWorker` 并通过 `PluginRegistry` 注册即可完成插件式组装。

---

## GatewayWorker（扩展点）

`GatewayWorker` 是 Java SDK 中所有可扩展业务逻辑的基类。它既是 Worker 的核心，也承担了 Python SDK 中 `Plugin` 的角色。

```java
public abstract class GatewayWorker {
    /**
     * 返回此 Worker 支持的 Agent 类型列表。
     * 相当于 Python SDK 中 Plugin.register_agent_configs() 的 agent_id 列表。
     */
    public abstract List<String> getAgentTypes();

    /**
     * 核心业务处理逻辑。
     *
     * @param command 命令对象
     * @param context 任务上下文
     * @return 任务处理结果
     */
    public abstract Object processCommand(GatewayCommand command, AgentContext context);
}
```

### 生命周期钩子

Worker 配置支持以下生命周期回调，可以通过覆写对应方法或注册回调来实现：

```java
public class MyWorker extends GatewayWorker {

    @Override
    public List<String> getAgentTypes() {
        return List.of("my_agent", "data_processor");
    }

    @Override
    public Object processCommand(GatewayCommand command, AgentContext context) {
        // 核心处理逻辑
        return Map.of("status", "completed", "content", "处理完成");
    }

    /** Worker 启动时调用 */
    public void onWorkerStartup() {
        System.out.println("Worker 已启动");
    }

    /** Worker 关闭时调用 */
    public void onWorkerShutdown() {
        System.out.println("Worker 正在关闭");
    }

    /** 任务开始前调用 */
    public void onTaskStart(AgentContext context) {
        System.out.println("任务开始: " + context.getCurrentMessageId());
    }

    /** 任务成功完成时调用 */
    public void onTaskComplete(AgentContext context, Object result) {
        System.out.println("任务完成: " + context.getCurrentMessageId());
    }

    /** 任务出错时调用 */
    public void onTaskError(AgentContext context, Exception error) {
        System.err.println("任务出错: " + error.getMessage());
    }

    /** 任务取消时调用 */
    public void onTaskCancel(AgentContext context) {
        System.out.println("任务被取消: " + context.getCurrentMessageId());
    }
}
```

---

## PluginRegistry

`PluginRegistry` 负责管理已注册的 Worker 实例（即插件式组件），提供统一的查找和配置能力。

```java
public class PluginRegistry {
    /**
     * 注册一个 Worker 实例（插件包）。
     *
     * @param worker 要注册的 GatewayWorker 实例
     */
    public void registerBundle(GatewayWorker worker);

    /**
     * 根据 Agent 类型获取对应的 Worker。
     *
     * @param agentType Agent 类型标识
     * @return 对应的 GatewayWorker 实例，若未找到则返回 null
     */
    public GatewayWorker getPlugin(String agentType);

    /**
     * 列出所有已注册的 Agent 类型及其 Worker。
     *
     * @return Agent 类型到 Worker 实例的映射
     */
    public Map<String, GatewayWorker> listPlugins();
}
```

### 使用示例

```java
// 创建 PluginRegistry
PluginRegistry registry = new PluginRegistry();

// 注册多个 Worker（相当于注册插件）
registry.registerBundle(new MyDataAnalyzer());
registry.registerBundle(new MyReportGenerator());
registry.registerBundle(new MyChartBuilder());

// 查询已注册的插件
GatewayWorker dataAnalyzer = registry.getPlugin("data_analyzer");
System.out.println("找到 worker: " + dataAnalyzer.getClass().getSimpleName());

// 列出所有已注册的 Agent 类型
Map<String, GatewayWorker> allPlugins = registry.listPlugins();
for (String agentType : allPlugins.keySet()) {
    System.out.println("已注册 Agent 类型: " + agentType);
}
```

---

## AgentConfig

`AgentConfig` 是一个数据类，描述单个 Agent 的配置信息。通常由 `GatewayWorker` 在注册阶段提供。

```java
public class AgentConfig {
    /** Agent 唯一标识 */
    private String agentId;

    /** Agent 显示名称 */
    private String name;

    /** Agent 描述信息 */
    private String description;

    /** 工具函数映射（工具名 -> 函数引用） */
    private Map<String, Object> tools;

    /** 提示词配置 */
    private Map<String, String> prompts;

    /** 技能配置 */
    private Map<String, Object> skills;

    /** 回调配置 */
    private Map<String, List<Object>> callbacks;

    /** 知识库配置 */
    private Map<String, Object> knowledgeBases;

    /** 子 Agent 列表 */
    private List<String> subAgents;

    /** 扩展配置 */
    private Map<String, Object> extra;

    /** 注册冲突时的处理策略 */
    private String onConflict;
}
```

### 属性表

| 属性 | 类型 | 描述 |
|------|------|------|
| `agentId` | `String` | Agent 唯一标识 |
| `name` | `String` | Agent 显示名称 |
| `description` | `String` | Agent 描述信息 |
| `tools` | `Map<String, Object>` | 工具函数映射 |
| `prompts` | `Map<String, String>` | 提示词配置 |
| `skills` | `Map<String, Object>` | 技能配置 |
| `callbacks` | `Map<String, List<Object>>` | 生命周期回调配置 |
| `knowledgeBases` | `Map<String, Object>` | 知识库配置 |
| `subAgents` | `List<String>` | 依赖的子 Agent 类型列表 |
| `extra` | `Map<String, Object>` | 扩展配置项 |
| `onConflict` | `String` | 冲突处理策略（默认 `"error"`，可选 `"replace"`, `"skip"`） |

### 使用示例

```java
AgentConfig config = new AgentConfig();
config.setAgentId("smart_assistant");
config.setName("智能助手");
config.setDescription("处理用户自然语言请求的智能 Agent");
config.setTools(Map.of(
    "search", searchFunction,
    "calculate", calculateFunction
));
config.setPrompts(Map.of(
    "system", "你是一个智能助手，负责回答用户问题。",
    "welcome", "你好，请问有什么可以帮助你的？"
));
config.setSubAgents(List.of("data_analyzer", "report_generator"));
config.setOnConflict("error");
```

---

## 完整使用示例

以下示例展示如何通过 `PluginRegistry` 注册多个 Worker，构建一个完整的 Agent 插件体系：

```java
// 1. 定义数据分析器 Worker
public class DataAnalyzer extends GatewayWorker {

    private AgentConfig config;

    public DataAnalyzer() {
        config = new AgentConfig();
        config.setAgentId("data_analyzer");
        config.setName("数据分析器");
        config.setDescription("对输入数据执行统计分析");
    }

    @Override
    public List<String> getAgentTypes() {
        return List.of("data_analyzer");
    }

    @Override
    public Object processCommand(GatewayCommand command, AgentContext context) {
        // 分析逻辑
        context.emitChunk("正在分析数据...");
        return Map.of("status", "completed", "content", "分析结果");
    }

    public void onWorkerStartup() {
        System.out.println("[DataAnalyzer] 启动完成");
    }
}

// 2. 定义报表生成器 Worker
public class ReportGenerator extends GatewayWorker {

    @Override
    public List<String> getAgentTypes() {
        return List.of("report_generator");
    }

    @Override
    public Object processCommand(GatewayCommand command, AgentContext context) {
        context.emitChunk("正在生成报表...");
        context.emitArtifact("https://reports.example.com/report_001.pdf");
        return Map.of("status", "completed", "content", "报表已生成");
    }
}

// 3. 通过 PluginRegistry 管理所有 Worker
public class PluginManager {
    private PluginRegistry registry;

    public PluginManager() {
        registry = new PluginRegistry();
        initializePlugins();
    }

    private void initializePlugins() {
        // 注册所有 Worker（相当于注册插件）
        registry.registerBundle(new DataAnalyzer());
        registry.registerBundle(new ReportGenerator());

        System.out.println("已注册 " + registry.listPlugins().size() + " 个插件");
    }

    public GatewayWorker getPlugin(String agentType) {
        return registry.getPlugin(agentType);
    }
}
```
