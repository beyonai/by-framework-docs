# 状态与记忆 (History)

Agent 的对话历史管理对于长对话和上下文一致性至关重要。by-framework 提供了可插拔的历史存储后端。

## 存储后端

目前支持以下存储方式：

### 1. Byclaw History (默认)
专为 Byclaw 平台优化的存储方案，支持版本管理和结构化检索。

=== "Python"
    ```bash
    pip install by-framework-history-byclaw
    ```

### 2. Postgres History
基于传统关系型数据库的存储方案，适合对数据一致性有要求的场景。

=== "Python"
    ```bash
    pip install by-framework-history-postgres
    ```

=== "Java"
    使用 JPA 或 JDBC 存储实现，通过 `HistoryProvider` 接口扩展。

---

## 使用方法

在 Worker 初始化时指定历史记录处理器：

=== "Python"

    ```python
    from by_framework_history_postgres import PostgresHistoryProvider

    class MyAgent(ByaiWorker):
        def get_history_provider(self):
            return PostgresHistoryProvider(dsn=os.getenv("DATABASE_URL"))
    ```

=== "Java"

    ```java
    @Bean
    public HistoryProvider postgresHistoryProvider() {
        return new PostgresHistoryProvider(dataSource);
    }
    ```

## 核心接口

无论使用哪种后端，Agent 都可以通过 `context.history` 进行访问：

- `load()`: 加载最近的会话记录。
- `save()`: 保存新的消息或状态。
- `clear()`: 清空会话历史。
