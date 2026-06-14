"""
WorkerManager 管控示例
======================

演示四种典型运维场景：
  1. 维护窗口  — 暂停 Worker → 执行维护 → 恢复
  2. 缩容下线  — 优雅驱逐（等待 in-flight 任务完成）
  3. 紧急下线  — 强制驱逐（立即退出）
  4. 流量路由  — 用 Denylist 控制哪些 Worker 可消费某个 agent_type

用法：
  uv run python worker_admin.py --scenario maintenance --worker-id worker-1
  uv run python worker_admin.py --scenario scale-down  --worker-id worker-2
  uv run python worker_admin.py --scenario emergency   --worker-id worker-3
  uv run python worker_admin.py --scenario routing     --worker-id worker-4 --agent-type gpt-4o
  uv run python worker_admin.py --scenario status      --worker-id worker-1
"""

from by_framework import get_redis
import argparse
import asyncio
import os

from dotenv import load_dotenv
from by_framework.common.redis_client import init_redis

from by_framework import WorkerManager

import logging

logger = logging.getLogger(__name__)

load_dotenv()


# ---------------------------------------------------------------------------
# 场景 1：维护窗口
# ---------------------------------------------------------------------------

async def scenario_maintenance(manager: WorkerManager, worker_id: str) -> None:
    """
    维护窗口操作流程：
      1. 暂停 Worker（停止消费新消息，in-flight 任务继续跑完）
      2. 执行维护动作（此处模拟等待 5 秒）
      3. 恢复 Worker
    """
    print(f"\n[维护窗口] 目标 Worker: {worker_id}")

    print("  → 暂停 Worker...")
    await manager.suspend_worker(worker_id, reason="scheduled maintenance")

    state = await manager.get_worker_admin_state(worker_id)
    print(f"  ✓ Worker 状态: {state}")

    # print("  → 执行维护中（模拟 5s）...")
    # await asyncio.sleep(5)

    # print("  → 恢复 Worker...")
    # await manager.resume_worker(worker_id)

    # state = await manager.get_worker_admin_state(worker_id)
    # print(f"  ✓ Worker 状态: {state}")
    # print("[维护窗口] 完成")


# ---------------------------------------------------------------------------
# 场景 2：缩容下线（优雅）
# ---------------------------------------------------------------------------

async def scenario_scale_down(manager: WorkerManager, worker_id: str) -> None:
    """
    优雅缩容：
      Worker 完成当前所有 in-flight 任务后进程自然退出，无需手动 kill。
    """
    print(f"\n[缩容下线] 目标 Worker: {worker_id}")

    print("  → 发送优雅驱逐命令...")
    await manager.evict_worker(worker_id, reason="scale down")

    state = await manager.get_worker_admin_state(worker_id)
    print(f"  ✓ Worker 状态: {state}")
    print("  ℹ Worker 将在 in-flight 任务完成后自动退出，无需手动 kill")
    print("[缩容下线] 命令已送达")


# ---------------------------------------------------------------------------
# 场景 3：紧急下线（强制）
# ---------------------------------------------------------------------------

async def scenario_emergency(manager: WorkerManager, worker_id: str) -> None:
    """
    紧急强制驱逐：
      Worker 立即退出，in-flight 任务中断，客户端等待超时后收到失败响应。

    注意：消息语义为 at-most-once，框架不重投递，避免 LLM 任务重复执行。
    """
    print(f"\n[紧急下线] 目标 Worker: {worker_id}")
    print("  ⚠ 强制驱逐将立即终止进程，in-flight 任务将超时失败")

    print("  → 发送强制驱逐命令...")
    await manager.evict_worker(worker_id, force=True, reason="OOM / emergency eviction")

    state = await manager.get_worker_admin_state(worker_id)
    print(f"  ✓ Worker 状态: {state}")
    print("[紧急下线] 命令已送达")


# ---------------------------------------------------------------------------
# 场景 4：流量路由（Denylist）
# ---------------------------------------------------------------------------

async def scenario_routing(
    manager: WorkerManager, worker_id: str, agent_type: str
) -> None:
    """
    Denylist 路由控制——灰度/隔离场景：

    示例：将 worker_id 从 agent_type 的消费者中隔离出去，
    再查看黑名单，最后恢复。

    实际用途：
      - 灰度发布时只允许部分 Worker 消费新 agent_type
      - 隔离故障 Worker 的某类任务，不影响其他任务消费
    """
    print(f"\n[流量路由] Worker: {worker_id}, agent_type: {agent_type}")

    # 查看当前黑名单
    denied_before = await manager.get_type_denylist(agent_type)
    print(f"  当前 denylist: {denied_before or '(空，所有 Worker 均可消费)'}")

    # 禁止该 Worker 消费此 agent_type
    print(f"  → 将 {worker_id} 加入 {agent_type} denylist...")
    await manager.deny_worker_for_type(agent_type, worker_id)
    print("  ℹ 生效时机：Worker 心跳刷新（≤5s）")

    denied_after = await manager.get_type_denylist(agent_type)
    print(f"  ✓ 当前 denylist: {denied_after}")

    # 恢复
    print(f"  → 从 denylist 移除 {worker_id}...")
    await manager.allow_worker_for_type(agent_type, worker_id)

    denied_final = await manager.get_type_denylist(agent_type)
    print(f"  ✓ 恢复后 denylist: {denied_final or '(空)'}")
    print("[流量路由] 完成")


# ---------------------------------------------------------------------------
# 场景 5：状态查询
# ---------------------------------------------------------------------------

async def scenario_status(manager: WorkerManager, worker_id: str) -> None:
    """查看 Worker 当前的 admin 状态。"""
    print(f"\n[状态查询] Worker: {worker_id}")

    state = await manager.get_worker_admin_state(worker_id)
    if state:
        print(f"  lifecycle : {state.get('lifecycle', '-')}")
        print(f"  reason    : {state.get('reason', '-')}")
        print(f"  updated_at: {state.get('updated_at', '-')}")
    else:
        print("  (无 admin 状态，Worker 处于默认 active 状态)")


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

SCENARIOS = {
    "maintenance": scenario_maintenance,
    "scale-down":  scenario_scale_down,
    "emergency":   scenario_emergency,
    "status":      scenario_status,
}


async def main() -> None:
    parser = argparse.ArgumentParser(description="WorkerManager 管控示例")
    parser.add_argument(
        "--scenario",
        choices=[*SCENARIOS, "routing"],
        required=True,
        help="运行场景",
    )
    parser.add_argument("--worker-id", required=True, help="目标 Worker ID")
    parser.add_argument(
        "--agent-type",
        default="gpt-4o",
        help="agent_type（仅 routing 场景使用）",
    )
    args = parser.parse_args()

    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", 6379))
    redis_db = int(os.getenv("REDIS_DB", 0))
    redis_password = os.getenv("REDIS_PASSWORD")
    redis_username = os.getenv("REDIS_USERNAME")

    logger.info(f"正在连接 Redis: {redis_host}:{redis_port} (DB: {redis_db}, 用户: {redis_username or 'default'}, 密码已设置: {'Yes' if redis_password else 'No'})")

    # 3. 初始化全局单例
    redis = init_redis(
        host=redis_host,
        port=redis_port,
        db=redis_db,
        password=redis_password or None,
        username=redis_username or None
    )
    manager = WorkerManager(redis_client=redis)

    try:
        if args.scenario == "routing":
            await scenario_routing(manager, args.worker_id, args.agent_type)
        else:
            await SCENARIOS[args.scenario](manager, args.worker_id)
    finally:
        await redis.aclose()


if __name__ == "__main__":
    asyncio.run(main())
