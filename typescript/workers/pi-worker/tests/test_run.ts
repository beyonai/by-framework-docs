
import runWorker from "../src/index.js";

async function main() {
    console.log("🚀 开始测试 runWorker...");
    const userInput = "你好，请自我介绍一下！";
    const sessionId = "test_session_123";
    const traceId = "test_trace_123";

    try {
        const result = await runWorker(userInput, sessionId, traceId);
        console.log("✅ 测试执行完毕, 返回结果:", result);
    } catch (error) {
        console.error("❌ 执行出错:", error);
        process.exit(1);
    }

    // 强制退出（因为底层的某些第三方库比如 Redis/Http client 可能会残留 keep-alive 定时器）
    process.exit(0);
}

main();
