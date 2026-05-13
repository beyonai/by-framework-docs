# Plugin API 

TypeScript SDK 的插件系统允许通过 `Plugin` 抽象类扩展 Agent 功能。插件可以注册 Agent 配置并监听生命周期事件。

所有类从 `@byclaw/by-framework` 包根导入。

---

## Plugin

`Plugin` 是一个抽象基类，所有自定义插件必须继承它。

### 构造函数

```typescript
import { Plugin, PluginManifest } from '@byclaw/by-framework';

class MyPlugin extends Plugin {
  constructor() {
    super(
      {
        plugin_id: "my-plugin",
        version: "1.0.0",
        priority: 10
      },
      30 // hookTimeoutSeconds
    );
  }
}
```

```typescript
constructor(manifest: PluginManifest, hookTimeoutSeconds?: number)
```

| 参数 | 类型 | 描述 |
|------|------|------|
| `manifest` | `PluginManifest` | 插件清单（必填） |
| `hookTimeoutSeconds` | `number` | 钩子超时时间（秒），默认值由框架决定 |

### 属性

| 属性 | 类型 | 描述 |
|------|------|------|
| `manifest` | `PluginManifest` | 插件清单 |
| `name` | `string` | 插件名称（取自 `manifest.plugin_id`） |
| `pluginId` | `string` | 插件 ID（取自 `manifest.plugin_id`） |
| `version` | `string` | 插件版本（取自 `manifest.version`） |
| `hookTimeoutSeconds` | `number` | 钩子超时时间 |

---

### 必须重写的方法

#### registerAgentConfigs

插件必须重写此方法，用于注册该插件提供的 Agent 配置。

```typescript
abstract registerAgentConfigs(buildContext: PluginBuildContext): Promise<AgentConfig[] | null>
```

**示例：**

```typescript
class MyPlugin extends Plugin {
  async registerAgentConfigs(buildContext: PluginBuildContext): Promise<AgentConfig[]> {
    return [
      {
        agent_id: "my_chat_agent",
        name: "My Chat Agent",
        description: "A custom chat agent",
        prompts: {
          system: "你是一个智能助手"
        },
        tools: {
          // 工具定义
        }
      }
    ];
  }
}
```

返回 `null` 表示不注册任何 Agent 配置。

---

### 静态方法

#### Plugin.registerPluginClass

注册一个插件类，使其可被框架发现和加载。通常在插件模块中调用。

```typescript
static registerPluginClass(pluginClass: typeof Plugin): void
```

**示例：**

```typescript
import { Plugin } from '@byclaw/by-framework';

// 注册插件类
Plugin.registerPluginClass(MyPlugin);
```

---

### 生命周期钩子

所有生命周期钩子都是可选的异步方法，插件可根据需要重写。

#### onWorkerStartup

Worker 启动时调用。

```typescript
async onWorkerStartup(worker: GatewayWorker): Promise<void>
```

**示例：**

```typescript
async onWorkerStartup(worker: GatewayWorker): Promise<void> {
  console.log(`Worker ${worker.workerId} 已启动`);
  // 初始化数据库连接等资源
}
```

#### onWorkerShutdown

Worker 关闭时调用。

```typescript
async onWorkerShutdown(worker: GatewayWorker): Promise<void>
```

**示例：**

```typescript
async onWorkerShutdown(worker: GatewayWorker): Promise<void> {
  console.log(`Worker ${worker.workerId} 即将关闭`);
  // 释放资源
}
```

#### onTaskStart

任务开始时调用。

```typescript
async onTaskStart(context: AgentContext): Promise<void>
```

**示例：**

```typescript
async onTaskStart(context: AgentContext): Promise<void> {
  console.log(`任务开始: sessionId=${context.sessionId}`);
}
```

#### onTaskComplete

任务成功完成时调用。

```typescript
async onTaskComplete(context: AgentContext, result: any): Promise<void>
```

**示例：**

```typescript
async onTaskComplete(context: AgentContext, result: any): Promise<void> {
  console.log(`任务完成: sessionId=${context.sessionId}`);
  // 记录结果或清理资源
}
```

#### onTaskError

任务出错时调用。

```typescript
async onTaskError(context: AgentContext, error: Error): Promise<void>
```

**示例：**

```typescript
async onTaskError(context: AgentContext, error: Error): Promise<void> {
  console.error(`任务出错: ${error.message}`);
  // 发送告警通知
}
```

#### onTaskCancel

任务取消时调用。

```typescript
async onTaskCancel(context: AgentContext, command: any): Promise<void>
```

**示例：**

```typescript
async onTaskCancel(context: AgentContext, command: any): Promise<void> {
  console.log(`任务被取消: sessionId=${context.sessionId}`);
  // 清理运行中的资源
}
```

---

### 完整插件示例

```typescript
import { Plugin, PluginManifest, AgentContext, AgentConfig, GatewayWorker, PluginBuildContext } from '@byclaw/by-framework';

class MonitoringPlugin extends Plugin {
  constructor() {
    super({
      plugin_id: "monitoring-plugin",
      version: "1.0.0",
      priority: 5,
      enabled: true
    });
  }

  async registerAgentConfigs(buildContext: PluginBuildContext): Promise<AgentConfig[]> {
    return [
      {
        agent_id: "monitored_agent",
        name: "Monitored Agent",
        description: "An agent with monitoring"
      }
    ];
  }

  async onWorkerStartup(worker: GatewayWorker): Promise<void> {
    console.log("监控插件: Worker 已启动");
  }

  async onTaskStart(context: AgentContext): Promise<void> {
    console.log(`监控插件: 任务开始 [${context.sessionId}]`);
  }

  async onTaskComplete(context: AgentContext, result: any): Promise<void> {
    console.log(`监控插件: 任务完成 [${context.sessionId}]`);
  }

  async onTaskError(context: AgentContext, error: Error): Promise<void> {
    console.error(`监控插件: 任务出错 [${context.sessionId}] ${error.message}`);
  }
}

// 注册插件类
Plugin.registerPluginClass(MonitoringPlugin);
```

---

## PluginManifest 接口

```typescript
interface PluginManifest {
  plugin_id: string;
  version?: string;
  priority?: number;
  enabled?: boolean;
}
```

| 属性 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `plugin_id` | `string` | 是 | 插件唯一标识 |
| `version` | `string` | 否 | 插件版本号 |
| `priority` | `number` | 否 | 优先级，数值越大优先级越高 |
| `enabled` | `boolean` | 否 | 是否启用，默认 `true` |

---

## AgentConfig 接口

`AgentConfig` 定义了一个 Agent 的完整运行时配置。

```typescript
interface AgentConfig {
  agent_id: string;
  name?: string;
  description?: string;
  prompts?: Record<string, any>;
  tools?: Record<string, any>;
  skills?: Record<string, any>;
  callbacks?: Partial<Record<CallbackType, Array<(...args: any[]) => any>>>;
  knowledge_bases?: Record<string, any>;
  sub_agents?: string[];
  on_conflict?: 'error' | 'overwrite' | 'skip';
}
```

| 属性 | 类型 | 描述 |
|------|------|------|
| `agent_id` | `string` | Agent 唯一标识（必填） |
| `name` | `string` | Agent 名称 |
| `description` | `string` | Agent 描述 |
| `prompts` | `Record<string, any>` | 提示词模板集合 |
| `tools` | `Record<string, any>` | 工具定义集合 |
| `skills` | `Record<string, any>` | 技能定义集合 |
| `callbacks` | `Partial<Record<CallbackType, Array<(...args: any[]) => any>>>` | 回调钩子集合 |
| `knowledge_bases` | `Record<string, any>` | 知识库配置 |
| `sub_agents` | `string[]` | 子 Agent 类型列表 |
| `on_conflict` | `'error' \| 'overwrite' \| 'skip'` | 配置冲突时的处理策略 |

---

## PluginRegistry

`PluginRegistry` 管理所有已注册的插件。

```typescript
import { PluginRegistry } from '@byclaw/by-framework';
```

### 方法

#### registerBundle

注册单个插件。

```typescript
registerBundle(plugin: Plugin): void
```

#### registerBundles

批量注册插件。

```typescript
registerBundles(plugins: Plugin[]): void
```

#### getPlugin

根据插件 ID 获取插件实例。

```typescript
getPlugin(pluginId: string): Plugin | undefined
```

#### listPlugins

列出所有已注册的插件。

```typescript
listPlugins(): Plugin[]
```

#### loadPluginsFromDir

从指定目录异步加载所有插件。

```typescript
async loadPluginsFromDir(dir: string): Promise<void>
```

#### initializePlugins

初始化所有已注册的插件。调用每个插件的 `registerAgentConfigs` 方法，收集所有 Agent 配置。

```typescript
async initializePlugins(buildContext?: PluginBuildContext): Promise<void>
```

**示例：**

```typescript
const registry = new PluginRegistry();

// 批量注册
registry.registerBundles([new MonitoringPlugin(), new AuthPlugin()]);

// 获取指定插件
const plugin = registry.getPlugin("monitoring-plugin");

// 列出所有插件
const allPlugins = registry.listPlugins();

// 从目录加载插件
await registry.loadPluginsFromDir("/path/to/plugins");

// 初始化所有插件，收集 Agent 配置
await registry.initializePlugins(buildContext);
```

---

## PluginBuildContext

`PluginBuildContext` 在插件初始化时传递给 `registerAgentConfigs`，提供构建期的上下文信息。

```typescript
interface PluginBuildContext {
  // 构建阶段可用的上下文信息
  // 具体属性由框架注入
}
```
