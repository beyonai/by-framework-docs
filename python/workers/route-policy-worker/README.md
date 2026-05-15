# Route Policy Worker Sample

这个目录演示 `GatewayClient.send_message()` 和 `AgentContext.call_agent()` 共用的可用性控制面。

核心结论：不需要为每一种 `route_policy` 写一种业务 Worker。`FAIL_FAST`、`WAKE_AND_WAIT`、`WAKE_AND_QUEUE`、`QUEUE_ONLY`、`SEND_ANYWAY` 是路由和控制面的策略；业务 Worker 只声明自己支持哪些 `agent_type`，并照常处理 command。示例里使用多个 `agent_type`，只是为了模拟“在线”“冷启动”“排队后放行”等不同状态。

## 进程

- `main.py`: 通用 echo worker，可通过 `WORKER_AGENT_TYPES` 声明一个或多个 `agent_type`。
- `wakeup_controller.py`: manager/client owner 侧的参考唤醒控制器，监听 `byai_gateway:control_plane:mgmt:wakeup`。
- `orchestrator.py`: agent 侧 `context.call_agent(..., route_policy=...)` 示例。

## 运行 send_message 示例

终端 1：启动一个已经在线的 worker。

```bash
cd /Users/xiaozhongcheng/data/company/beyonai/by-framework-samples/python/workers/route-policy-worker
WORKER_ID=route-policy-online-1 WORKER_AGENT_TYPES=route-policy-online-agent uv run python main.py
```

终端 2：启动 manager 侧唤醒控制器。默认会在收到 wakeup request 后，本地拉起一个 `main.py` worker。

```bash
cd /Users/xiaozhongcheng/data/company/beyonai/by-framework-samples/python/workers/route-policy-worker
uv run python wakeup_controller.py
```

终端 3：运行 client 示例。

```bash
cd /Users/xiaozhongcheng/data/company/beyonai/by-framework-samples/python/client
uv run python send_message_route_policy.py
```

## 运行 call_agent 示例

终端 1：启动唤醒控制器。

```bash
cd /Users/xiaozhongcheng/data/company/beyonai/by-framework-samples/python/workers/route-policy-worker
uv run python wakeup_controller.py
```

终端 2：启动 orchestrator。

```bash
cd /Users/xiaozhongcheng/data/company/beyonai/by-framework-samples/python/workers/route-policy-worker
WORKER_ID=route-policy-orchestrator-1 \
WORKER_AGENT_TYPE=route-policy-orchestrator-agent \
CHILD_AGENT_TYPE=route-policy-child-agent \
CHILD_ROUTE_POLICY=WAKE_AND_WAIT \
uv run python orchestrator.py
```

终端 3：向 `route-policy-orchestrator-agent` 发送消息。

```bash
cd /Users/xiaozhongcheng/data/company/beyonai/by-framework-samples/python/client
BYAI_TARGET_AGENT_TYPE=route-policy-orchestrator-agent uv run python main.py
```

`orchestrator.py` 会调用 `route-policy-child-agent`。如果 child worker 不在线，`WAKE_AND_WAIT` 会触发 `wakeup_controller.py`，由 manager 侧拉起 worker 后再投递。
