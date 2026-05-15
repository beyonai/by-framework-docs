# By-Framework Python Client Sample

这是一个使用 `uv` 进行项目管理的 Python 客户端示例，演示了如何向 `by-framework` Gateway 发送消息。

## 特性
- **uv 管理**: 使用 `pyproject.toml` 定义依赖。
- **Workspace 集成**: 自动关联主仓库中的 `by-framework` 核心库。
- **流式响应**: 内置监听逻辑，支持获取 Worker 的实时输出。

## 快速上手

### 1. 准备环境
由于该项目已集成在 `by-framework-samples` 的 workspace 中，请在根目录或本目录下执行：

```bash
uv sync
```

### 2. 配置环境变量
复制示例配置文件并根据需要修改：

```bash
cp .env.example .env
```

### 3. 运行项目

**首先确保至少有一个 Worker 已开启**，例如：
```bash
cd ../workers/langgraph-worker
uv run python main.py
```

**在本目录下运行客户端:**
```bash
uv run python main.py
```

运行新版 `send_message` 路由策略示例：

```bash
uv run python send_message_route_policy.py
```

配套 worker 示例在：

```bash
../workers/route-policy-worker
```

## 核心功能说明

项目核心逻辑封装在 `main.py` 的 `SyncGatewayClient` 类中，主要提供以下能力：

1. **`send_message` (非阻塞发送)**
   纯异步即发即弃调用，向目标 Worker 发送消息后立即返回 `response` 对象，不阻塞等待流式回复。适用于后台离线任务或纯指令触发。

2. **`send_message_sync` (同步阻塞等待)**
   发送消息并阻塞当前协程，自动监听并拼接 Redis 流中的实时事件（如 `answerDelta`、`reasoningLogDelta`）。
   支持超时配置（`timeout_seconds`），若指定时间内未收到任何新 Token，将自动结束阻塞并返回当前已收集到的文本内容。

3. **`subscribe_data_queue` (单独数据流监听)**
   传入指定的 `session_id` 单独发起流式队列（Redis Stream）监听。内部兼容了 `bytes/str` 格式的数据解析，提供极具鲁棒性的容错和退出机制。

## 新版 send_message 路由策略

`send_message_route_policy.py` 演示了新的单一参数 `route_policy`：

- `RoutePolicy.FAIL_FAST`: 检查在线 Worker，没有可用 Worker 时直接返回失败。
- `RoutePolicy.SEND_ANYWAY`: 跳过在线检查，直接写入目标 `agent_type` 控制队列。
- `RoutePolicy.WAKE_AND_WAIT`: 无在线 Worker 时触发控制面唤醒，并等待可用后再投递。
- `RoutePolicy.WAKE_AND_QUEUE`: 无在线 Worker 时触发唤醒，并将控制消息写入 pending delivery。
- `RoutePolicy.QUEUE_ONLY`: 只写入 pending delivery，不触发唤醒。

示例中的 `user_code` 会作为控制面 quota、dedupe 等策略的用户维度使用。

默认情况下，示例会按策略打到不同 `agent_type`：

- `route-policy-online-agent`: 用于演示 `FAIL_FAST` 的在线投递。
- `route-policy-wakeup-agent`: 用于演示 `WAKE_AND_WAIT` 的冷启动等待。
- `route-policy-queued-agent`: 用于演示 `WAKE_AND_QUEUE` 的 pending delivery。
- `route-policy-manual-agent`: 用于演示 `SEND_ANYWAY` 的跳过在线检查。

（*注：日志输出已统一采用标准的 Python `logging` 模块管理，便于与您的生产环境整合。*）
