import {
    GatewayWorker,
    AskAgentCommand,
    AgentContext,
} from '@byclaw/by-framework';
import { StateGraph, MessagesAnnotation, START, END } from "@langchain/langgraph";
import { ToolNode } from "@langchain/langgraph/prebuilt";
import { AIMessage, HumanMessage } from "@langchain/core/messages";
import { ChatOpenAI } from "@langchain/openai";
import { z } from "zod";
import { tool } from "@langchain/core/tools";

/**
 * 使用新的 tool 定义方式，使类型推断更准确
 */
const getWeather = tool(
    async ({ location }) => {
        console.log(`[Tool] 执行获取天气: ${location}`);
        return `The weather in ${location} is 25°C and sunny.`;
    },
    {
        name: "get_weather",
        description: "Get the current weather in a given location",
        schema: z.object({
            location: z.string().describe("The city and state, e.g. San Francisco, CA"),
        }),
    }
);

// 工具列表
const tools = [getWeather];
const toolNode = new ToolNode(tools);

/**
 * 集成真实大模型和 ReAct Agent 逻辑的 Worker
 */
export class LangGraphWorker extends GatewayWorker {
    private app;
    private model;

    constructor(workerId: string, registry?: any) {
        super(workerId, registry);

        // 1. 初始化真正的大模型
        this.model = new ChatOpenAI({
            modelName: process.env.MODEL_NAME || "gpt-4o",
            temperature: 0,
            openAIApiKey: process.env.MODEL_API_KEY,
            configuration: {
                baseURL: process.env.MODEL_BASE_URL, // 支持自定义 API 端点
            }
        }).bindTools(tools);

        this.app = this.buildReActGraph();
    }

    /**
     * 构建 ReAct (Reason + Act) 状态图
     */
    private buildReActGraph() {
        // 2. Agent 节点：调用大模型
        const callModel = async (state: typeof MessagesAnnotation.State) => {
            console.log(`[Node: Agent] 正在调用模型进行推理...`);
            const response = await this.model.invoke(state.messages);
            return { messages: [response] };
        };

        // 3. 路由逻辑：判断是继续调用工具还是结束
        const shouldContinue = (state: typeof MessagesAnnotation.State) => {
            const lastMessage = state.messages[state.messages.length - 1] as AIMessage;
            if (lastMessage.tool_calls && lastMessage.tool_calls.length > 0) {
                return "tools";
            }
            return END;
        };

        // 4. 组装图
        const workflow = new StateGraph(MessagesAnnotation)
            .addNode("agent", callModel)
            .addNode("tools", toolNode)
            .addEdge(START, "agent")
            .addConditionalEdges("agent", shouldContinue)
            .addEdge("tools", "agent");

        return workflow.compile();
    }

    getAgentTypes(): string[] {
        return ['langgraph-agent'];
    }

    async processCommand(command: AskAgentCommand, context: AgentContext): Promise<any> {
        console.log(`[${this.workerId}] 启动真实大模型流式处理...`);

        const initialState = {
            messages: [new HumanMessage(command.content.toString())]
        };

        // 检查 API Key 是否配置
        if (!process.env.MODEL_API_KEY) {
            const errorMsg = "错误：未检测到 MODEL_API_KEY 环境变量，请在 .env 中配置。";
            await context.emitChunk({ content: errorMsg });
            return { status: 'error', reply: errorMsg };
        }

        // 使用 streamEvents (v2) 获取更细粒度的事件流
        // 它可以捕捉到大模型生成的每一个 token (on_chat_model_stream)
        const eventStream = await this.app.streamEvents(initialState, { version: "v2" });

        let fullResponse = "";

        for await (const event of eventStream) {
            const eventType = event.event;
            const nodeName = event.metadata?.langgraph_node;

            // 1. 节点开始执行的通知
            if (eventType === "on_chain_start" && nodeName && event.name === nodeName) {
                await context.emitChunk({ content: `\n[系统: 开始执行节点 ${nodeName}]\n` });
            }

            // 2. 核心：捕获大模型的实时 Token 流
            if (eventType === "on_chat_model_stream") {
                const content = event.data.chunk?.content;
                if (content) {
                    const text = content.toString();
                    fullResponse += text;
                    // 实时将 Token 推送到前端
                    await context.emitChunk({ content: text });
                }
            }

            // 3. 捕获工具调用详情
            if (eventType === "on_chat_model_end") {
                const toolCalls = event.data.output?.tool_calls;
                if (toolCalls && toolCalls.length > 0) {
                    for (const tc of toolCalls) {
                        await context.emitChunk({ content: `\n(正在调用工具: ${tc.name} 参数: ${JSON.stringify(tc.args)})\n` });
                    }
                }
            }

            // 4. 工具执行结果
            if (eventType === "on_tool_end") {
                const output = event.data.output;
                await context.emitChunk({ content: `\n(工具结果: ${output})\n` });
            }
        }

        await context.emitChunk({ content: '\n\n[流程执行完毕]' });

        return {
            status: 'done',
            reply: fullResponse || '任务处理成功',
        };
    }
}
