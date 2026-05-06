# 链路追踪 (Tracing)

by-framework 支持通过插件系统集成主流的 LLM 观测平台，帮助开发者监控 Agent 的执行质量、性能和成本。

## 支持的平台

目前我们提供对以下平台的原生支持：

1. **Langfuse**：开源、轻量级的 LLM 追踪和评估平台。
2. **Arize Phoenix**：专注于 LLM 评估、可观测性和数据集管理的开源平台。

---

## Langfuse 集成

=== "Python"

    `by-framework-trace-langfuse` 插件支持自动上报。

    **安装**
    ```bash
    pip install by-framework-trace-langfuse
    ```

    **配置 (环境变量)**
    - `LANGFUSE_PUBLIC_KEY`: 项目公钥
    - `LANGFUSE_SECRET_KEY`: 项目秘钥
    - `LANGFUSE_BASE_URL`: API 地址

=== "Java"

    Java SDK 通过拦截器机制支持 Langfuse 追踪。

    **配置**
    在应用启动时设置系统属性或环境变量。

=== "TypeScript"

    TS SDK 集成了 Langfuse Web SDK。

---

## Arize Phoenix 集成

=== "Python"

    `by-framework-trace-phoenix` 提供 OpenTelemetry 兼容的导出器。

    **安装**
    ```bash
    pip install by-framework-trace-phoenix
    ```

    **配置**
    设置 `PHOENIX_COLLECTOR_HTTP_ENDPOINT` 等环境变量。

=== "Java / TS"

    支持通过标准的 OpenTelemetry 协议 (OTLP) 将追踪数据发送到 Phoenix。

---

## 特性

- **自动追踪**: 自动记录任务输入、输出及耗时。
- **异步上报**: 采用后台线程发送，不影响业务延迟。
- **错误捕获**: 自动记录任务执行中的异常堆栈。
- **上下文关联**: 自动关联 Session ID 和 User ID。
