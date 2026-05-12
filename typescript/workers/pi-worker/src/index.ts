import "dotenv/config";
import {
    WorkerRegistry,
    getRedis,
    closeRedis,
    AskAgentCommand,
    MessageHeader,
} from '@byclaw/by-framework';
import { PiWorker } from './worker.js';

/**
 * 运行 Pi Worker 的辅助函数（无实例依赖，通过环境变量配置 Redis）
 */
async function runWorker(
    input: string,
    sessionId?: string,
    traceId?: string,
) {
    // 1. 初始化全局 Redis 连接
    const redis = getRedis();



    // 2. 内部生成完整的 Command
    const sid = sessionId || `session_pi_${Date.now()}`;
    const messageId = `msg_${Date.now()}`;
    const tid = traceId || `trace_${Date.now()}`;

    const header = new MessageHeader(messageId, sid, tid, {
        targetAgentType: 'pi-agent',
    });
    const command = new AskAgentCommand(header, input);

    try {
        const registry = new WorkerRegistry(redis);
        const worker = new PiWorker(`worker-pi-${process.pid}`, registry, redis);

        const agentTaskResults = await worker.handleMessage(command);

        return agentTaskResults.replyData;
    }
    catch (error) {
        console.error("Worker 运行失败:", error);
        return `worker运行失败: ${error}`;
    }
    finally {
        // 执行完毕后优雅释放全局连接，确保清空挂起命令并退出事件循环
        await closeRedis();
    }
}

export default runWorker;
