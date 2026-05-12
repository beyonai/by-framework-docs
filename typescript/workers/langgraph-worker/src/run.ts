import "dotenv/config";
import {
    createRedis,
    WorkerRunner,
} from '@byclaw/by-framework';
import { LangGraphWorker } from './worker.js';

/**
 * 独立运行 Worker 的主函数
 */
async function main() {
    // 初始化 Redis 连接
    const redis = createRedis({
        host: process.env.REDIS_HOST || 'localhost',
        port: parseInt(process.env.REDIS_PORT || '6379'),
        db: parseInt(process.env.REDIS_DB || '0'),
        ...(process.env.REDIS_USERNAME ? { username: process.env.REDIS_USERNAME } : {}),
        ...(process.env.REDIS_PASSWORD ? { password: process.env.REDIS_PASSWORD } : {})
    });

    // 创建 Worker 实例
    const worker = new LangGraphWorker(`worker-langgraph-${process.pid}`);

    // 使用 WorkerRunner 运行 Worker
    const runner = new WorkerRunner(worker, { redisClient: redis });

    console.log(`[Main] 启动 LangGraph Worker...`);

    // 启动并自动处理 SIGINT/SIGTERM 信号
    await runner.start({ handleSignals: true });
}

main().catch(err => {
    console.error("Worker 启动失败:", err);
    process.exit(1);
});
