import "dotenv/config";
import {
    WorkerRunner,
    WorkerRegistry,
    createRedis,
    type GatewayCommand,
} from '@byclaw/by-framework';
import { LangGraphWorker } from './worker.js';

/**
 * 运行 Worker 的辅助函数（通过环境变量配置 Redis）
 * @param streamName 流名称
 * @param msgId 消息 ID
 * @param data 指令数据
 */
async function runWorker(
    streamName: string,
    msgId: string,
    data: GatewayCommand
) {
    // 1. 初始化 Redis 连接
    const redis = createRedis({
        host: process.env.REDIS_HOST || 'localhost',
        port: parseInt(process.env.REDIS_PORT || '6379'),
        db: parseInt(process.env.REDIS_DB || '0'),
        ...(process.env.REDIS_USERNAME ? { username: process.env.REDIS_USERNAME } : {}),
        ...(process.env.REDIS_PASSWORD ? { password: process.env.REDIS_PASSWORD } : {})
    });

    try {
        const registry = new WorkerRegistry(redis);
        const worker = new LangGraphWorker(`worker-langgraph-${process.pid}`, registry);
        const runner = new WorkerRunner(worker, { redisClient: redis });
        
        await runner.processAndAck(streamName, msgId, data);
    } finally {
        // 执行完毕后释放连接
        redis.disconnect();
    }
}

export default runWorker;