# Worker Manager

通过 `WorkerManager` 在运行时对 Worker 施加生命周期控制和订阅管控，无需重启进程。

## 快速开始

```bash
cd python/manager
uv sync
uv run python worker_admin.py --scenario <场景> --worker-id <worker-id>
```

## 场景说明

### 1. 维护窗口（maintenance）

暂停 Worker → 执行维护 → 恢复。Worker 在暂停期间不消费新消息，in-flight 任务继续跑完。

```bash
uv run python worker_admin.py --scenario maintenance --worker-id worker-1
```

```
[维护窗口] 目标 Worker: worker-1
  → 暂停 Worker...
  ✓ Worker 状态: {'lifecycle': 'suspended', 'reason': 'scheduled maintenance', ...}
  → 执行维护中（模拟 5s）...
  → 恢复 Worker...
  ✓ Worker 状态: {'lifecycle': 'active', 'reason': '', ...}
[维护窗口] 完成
```

### 2. 缩容下线（scale-down）

发送优雅驱逐命令，Worker 完成当前所有 in-flight 任务后进程自然退出。

```bash
uv run python worker_admin.py --scenario scale-down --worker-id worker-2
```

### 3. 紧急下线（emergency）

强制驱逐，Worker 立即退出。in-flight 任务中断，客户端等待超时后收到失败响应。

```bash
uv run python worker_admin.py --scenario emergency --worker-id worker-3
```

> **注意**：消息语义为 at-most-once，框架不做重投递，避免 LLM 任务被重复执行。

### 4. 流量路由（routing）

通过 Denylist 控制 Worker 对某个 agent_type 的订阅权限。

```bash
uv run python worker_admin.py --scenario routing --worker-id worker-4 --agent-type gpt-4o
```

```
[流量路由] Worker: worker-4, agent_type: gpt-4o
  当前 denylist: (空，所有 Worker 均可消费)
  → 将 worker-4 加入 gpt-4o denylist...
  ℹ 生效时机：Worker 心跳刷新（≤5s）
  ✓ 当前 denylist: ['worker-4']
  → 从 denylist 移除 worker-4...
  ✓ 恢复后 denylist: (空)
[流量路由] 完成
```

**典型用途：**
- 灰度发布时只允许部分 Worker 消费新 agent_type
- 隔离故障 Worker 的某类任务，不影响其他类型的消费

### 5. 状态查询（status）

查看 Worker 当前的 admin 控制状态。

```bash
uv run python worker_admin.py --scenario status --worker-id worker-1
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `BYAI_REDIS_HOST` | `127.0.0.1` | Redis 地址 |
| `BYAI_REDIS_PORT` | `6379` | Redis 端口 |
| `BYAI_REDIS_DB` | `0` | Redis 数据库 |
| `BYAI_REDIS_PASSWORD` | *(无)* | Redis 密码 |

## 双通道机制

管控命令通过两条通道送达 Worker，互为冗余：

```
WorkerManager
  ├─ Push：XADD → ctrl:worker:{worker_id}     立即送达
  └─ Pull：HSET → registry:worker:admin:{id}  心跳兜底（≤5s）
```

即使 Push 消息因网络抖动丢失，Worker 的心跳线程每 5 秒读取一次 HASH，确保指令最终生效。

## Worker 侧行为

| 操作 | 感知时机 | Worker 行为 |
|------|----------|-------------|
| `suspend_worker()` | 立即 / ≤5s 兜底 | 停止消费新消息，in-flight 任务继续 |
| `resume_worker()` | 立即 / ≤5s 兜底 | 恢复正常消费 |
| `evict_worker()` | 立即 / ≤5s 兜底 | 等 in-flight 完成 → 进程退出 |
| `evict_worker(force=True)` | 立即 / ≤5s 兜底 | 立即退出 |
| `deny_worker_for_type()` | ≤5s（心跳刷新缓存） | 不再消费该 agent_type 消息 |

## 注意事项

- Worker 重启后 `admin:{worker_id}` HASH 仍然存在。若希望重启后以默认状态运行，需调用 `clear_worker_admin_state()` 或 `resume_worker()`。
- `suspend` / `evict`（non-force）不会中断正在执行的 LLM 调用。
- `evict` 后进程自然退出，无需手动 kill。
