# 可观测性 (Observability)

`by-framework` 提供了强大的可观测性支持，允许开发者通过插件化的方式集成各种第三方追踪、日志和监控系统。

## 设计目标

- **低侵入性**：核心调度引擎不依赖任何具体的第三方 SDK。
- **透明追踪**：自动在 Agent 调用链中传递 `trace_id` 和 `message_id`。
- **插拔式设计**：通过安装不同的 Trace Provider 扩展包，实现一键切换后端。

## 工作原理

可观测性系统通过 `Plugin` 机制实现。框架会在任务执行的关键生命周期（如 `onTaskStart`, `onTaskComplete` 等）触发钩子，由已启用的 Trace 插件负责将数据上报给后端。

### 统一标识符

为了实现全链路追踪，框架会自动维护以下 ID：

- **Trace ID**: 代表一个完整的会话或请求链。
- **Message ID**: 代表当前步骤（Span）的唯一标识。
- **Parent Message ID**: 关联父级步骤，形成调用树。

## 快速开始

### 1. 安装 Provider
根据你的需求选择一个追踪后端：

- **Langfuse**: 适合专门的 LLM 观测。
- **Arize Phoenix**: 基于 OpenTelemetry 标准，适合通用链路分析。

### 2. 启用追踪
追踪插件通常通过环境变量自动发现和加载。只要对应的环境变量已设置，Worker 在启动时就会自动加载该插件。

例如，启用 Langfuse：
```bash
export LANGFUSE_PUBLIC_KEY="..."
export LANGFUSE_SECRET_KEY="..."
export LANGFUSE_BASE_URL="https://cloud.langfuse.com"
```

### 3. 多 Provider 处理
系统目前支持同时安装多个 Provider，但**同一时间建议只激活一个**。如果 Worker 发现有多个 Provider 同时处于"已配置且可用"状态，为了避免数据重复和上下文冲突，Worker 将会报错并拒绝启动。

## 常见问题

**Q: 开启追踪会影响性能吗？**
A: 绝大多数 Trace Provider 都是异步上报数据的，对核心调度流程的影响微乎其微。

**Q: 我可以自定义 Trace Provider 吗？**
A: 可以。请参考 [Plugin 开发指南](../guide/plugin-guide.md)。
