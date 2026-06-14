# Worker 管理指南

by-framework 内置了一套完整的 Worker 生命周期管控体系，让运维人员无需重启进程就能精确控制集群行为。

## 生命周期状态机

每个 Worker 的 `lifecycle` 字段维护在 Redis 中，取值与含义如下：

```
                  ┌──────────────────────────────┐
                  │           active             │◀──── 默认状态（正常消费）
                  └──────┬───────────────────────┘
                         │ suspend
                         ▼
                  ┌──────────────────────────────┐
                  │          suspended           │  停止消费新任务，保持心跳在线
                  └──────┬───────────────────────┘
                         │ resume / evict
                         ▼
                  ┌──────────────────────────────┐
                  │           evicted            │  租约不再续期，从路由彻底消失
                  └──────────────────────────────┘
```

| 状态 | 是否接收新任务 | 是否保持心跳 | 是否出现在路由 |
|---|---|---|---|
| `active` | ✓ | ✓ | ✓ |
| `suspended` | ✗ | ✓ | ✗ |
| `evicted` | ✗ | ✗ | ✗ |

!!! info "双通道投递"
    生命周期命令通过两个通道同时送达，确保不丢失：

    1. **Push**：XADD 写入 Worker 专属控制流（`byai_gateway:ctrl:worker:{id}`），即时响应。
    2. **Pull**：HSET 写入管理状态 HASH（`byai_gateway:registry:worker:admin:{id}`），心跳周期内兜底读取。

---

## WorkerManager API

`WorkerManager` 是编程方式管控 Worker 的入口，无需 Worker 本身在线也可以调用。

=== "Python"

    ```python
    from by_framework.admin import WorkerManager
    from by_framework.common import get_redis

    mgr = WorkerManager(get_redis())

    # 暂停一个 Worker（停止消费，保持心跳）
    await mgr.suspend_worker("worker-01", reason="定期维护")

    # 恢复
    await mgr.resume_worker("worker-01")

    # 驱逐（从路由消失）
    await mgr.evict_worker("worker-01", reason="下线")

    # 强制驱逐（同时取消运行中的任务）
    await mgr.evict_worker("worker-01", force=True, reason="紧急下线")
    ```

=== "TypeScript"

    ```typescript
    import { WorkerManager } from '@byclaw/by-framework';

    const mgr = new WorkerManager();

    // 暂停
    await mgr.suspendWorker('worker-01', '定期维护');

    // 恢复
    await mgr.resumeWorker('worker-01');

    // 驱逐
    await mgr.evictWorker('worker-01', { force: false, reason: '下线' });

    // 强制驱逐
    await mgr.evictWorker('worker-01', { force: true, reason: '紧急下线' });
    ```

=== "Java"

    ```java
    import com.iwhaleai.byai.framework.admin.WorkerManager;
    import com.iwhaleai.byai.framework.common.RedisClient;

    WorkerManager mgr = new WorkerManager(RedisClient.getInstance());

    // 暂停
    mgr.suspendWorker("worker-01", "定期维护");

    // 恢复
    mgr.resumeWorker("worker-01");

    // 驱逐
    mgr.evictWorker("worker-01", false, "下线");

    // 强制驱逐
    mgr.evictWorker("worker-01", true, "紧急下线");
    ```

### API 一览

| 方法 | 描述 |
|---|---|
| `suspend_worker(id, reason)` | 暂停 Worker，停止接收新任务 |
| `resume_worker(id)` | 恢复已暂停的 Worker |
| `evict_worker(id, force, reason)` | 驱逐 Worker（`force=True` 时立即取消运行中任务） |
| `deny_worker_for_type(type, id)` | 禁止指定 Worker 消费某 agent_type |
| `allow_worker_for_type(type, id)` | 解除禁止 |
| `get_type_denylist(type)` | 查询某 agent_type 的 deny 名单 |
| `get_worker_admin_state(id)` | 查询单个 Worker 的管控状态 |
| `clear_worker_admin_state(id)` | 清除 Worker 管控状态（还原为默认 active） |

---

## Agent-type 准入控制

除了针对 Worker 整体的生命周期管控，还可以精细控制某个 Worker 是否允许消费特定的 agent_type 任务流。

=== "Python"

    ```python
    # 禁止 worker-01 消费 chat 类型任务（只影响这一个 Worker）
    await mgr.deny_worker_for_type("chat", "worker-01")

    # 查看 chat 类型当前的 deny 名单
    denied = await mgr.get_type_denylist("chat")
    print(denied)  # ['worker-01']

    # 恢复
    await mgr.allow_worker_for_type("chat", "worker-01")
    ```

=== "TypeScript"

    ```typescript
    await mgr.denyWorkerForType('chat', 'worker-01');

    const denied = await mgr.getTypeDenylist('chat');
    console.log(denied); // ['worker-01']

    await mgr.allowWorkerForType('chat', 'worker-01');
    ```

=== "Java"

    ```java
    mgr.denyWorkerForType("chat", "worker-01");

    List<String> denied = mgr.getTypeDenylist("chat");
    System.out.println(denied); // [worker-01]

    mgr.allowWorkerForType("chat", "worker-01");
    ```

!!! tip "零延迟生效"
    Deny 条目写入 Redis 后，Worker 在下一次心跳周期（默认 5 秒）自动同步到内存缓存，无需重启进程，**对当前已在处理的任务不产生影响**。

---

## by-admin CLI 工具

`by-admin` 是配套的命令行工具，直连 Redis，适合运维人员手动操作集群。

### 安装

```bash
pip install "by-framework[cli]"
```

### Redis 连接配置

连接地址优先级（高 → 低）：

```bash
by-admin --redis-url redis://host:6379/0 worker list   # 命令行参数（最高优先级）
export BYAI_REDIS_URL=redis://host:6379/0              # 专用环境变量
export REDIS_URL=redis://host:6379/0                   # 通用环境变量
# 缺省：redis://localhost:6379/0
```

### worker 命令组

```bash
# 列出所有在线 Worker（Rich 表格）
by-admin worker list

# 按 agent_type 过滤
by-admin worker list --type chat

# JSON 输出（适合脚本集成 / jq）
by-admin worker list --json

# 查看单个 Worker 详情
by-admin worker info worker-01

# 暂停 / 恢复 / 驱逐
by-admin worker suspend worker-01 --reason "维护窗口"
by-admin worker resume  worker-01
by-admin worker evict   worker-01
by-admin worker evict   worker-01 --force
```

`worker list` 典型输出：

```
  Worker ID          Lifecycle   Agent Types        IP             Last Seen (ms)
 ─────────────────────────────────────────────────────────────────────────────────
  worker-abc123      active      chat, embed        192.168.1.5    1718432100000
  worker-def456      suspended   chat               192.168.1.6    1718432090000

  2 worker(s)
```

`lifecycle` 列带颜色：active 绿色、suspended 黄色、evicted 红色。

### type 命令组

```bash
# 查看 chat 类型的 deny 名单
by-admin type denylist chat

# 禁止 / 恢复
by-admin type deny  chat worker-01
by-admin type allow chat worker-01
```

### metrics 命令组

```bash
# 当前集群快照
by-admin metrics snapshot

# 最近 20 条历史趋势点
by-admin metrics history

# 输出更多点
by-admin metrics history --limit 50

# JSON 输出
by-admin metrics snapshot --json
by-admin metrics history  --json
```

`metrics snapshot` 典型输出：

```
Cluster Snapshot
  Workers online:     3
  Agent types:        2
  Active executions:  5
  Queue depth total:  12
```

---

## 健康检查与自驱逐

Worker 内置消费循环存活探测：若主消费线程在 **30 秒**内没有推进（未触发 tick 更新），心跳线程将**主动停止续期**，租约 TTL 到期后 Worker 自动从路由消失，避免"僵尸 Worker"持续占用消费位但不处理任务。

```
Consumer loop  ──tick──▶  lastConsumerTick
                               │
Heartbeat loop ──每 5 秒──▶ 检查 (now - lastConsumerTick) < 30s
                               │
                          失败 ──▶ 停止续期 → 租约过期 → 路由消失
```

!!! warning "与 evict 的区别"
    - `evict` 是**主动**操作，立即清除租约和路由。
    - 健康检查触发的驱逐是**被动**的，租约自然过期（最长 15 秒），不立即取消正在运行的任务。

---

## Worker IP 地址

Worker 启动时自动通过 UDP socket 探测本机出站 IP，并写入 Redis 租约 key 的 JSON payload。`worker list` 和 `worker info` 均会展示此字段，方便在多机部署时定位具体节点。

```python
# 通过 WorkerRegistry 查询
registry = WorkerRegistry(get_redis())
workers = await registry.get_all_workers()
for wid, info in workers.items():
    print(f"{wid}  ip={info['ip_address']}")
```

---

## 相关 Redis Key

| Key | 类型 | 描述 |
|---|---|---|
| `byai_gateway:registry:worker:admin:{id}` | Hash | Worker 管控状态（lifecycle / reason / updated_at） |
| `byai_gateway:registry:agent_type:denied:{type}` | Set | 某 agent_type 的 Worker deny 名单 |
| `byai_gateway:registry:worker:online:{id}` | String | Worker 心跳租约（含 ip_address，TTL 15s） |
| `by_framework:obs:collector_lock` | String | MetricsCollector 分布式锁（SET NX） |
| `by_framework:obs:history` | ZSet | 历史趋势点（score = timestamp ms） |

---

## 最佳实践

**维护窗口**：优先用 `suspend` 而非 `evict`，这样 Worker 进程本身保持活跃，维护完成后 `resume` 立即生效，无需重启。

**灰度流量**：用 `type deny` 把待升级的 Worker 从某个 agent_type 的消费中摘除，升级完成后再 `allow` 恢复，实现零停机滚动升级。

**紧急熔断**：所有 Worker 均支持 `evict --force`，可在数秒内从路由中完全剔除一个异常节点，避免影响其他任务。

**脚本集成**：所有读取命令均支持 `--json` 输出，可直接与 `jq`、Prometheus 脚本、CI/CD 流水线集成：

```bash
# 检查是否有 suspended 状态的 Worker
by-admin worker list --json | jq '[.[] | select(.lifecycle=="suspended")] | length'
```
