import {
    GatewayWorker,
    AskAgentCommand,
    AgentContext,
    type ProcessCommandResult,
} from '@byclaw/by-framework';
import type { WorkerRegistry } from '@byclaw/by-framework';
import type { Redis } from 'ioredis';
import { Agent, type AgentTool } from "@mariozechner/pi-agent-core";
import { getModel } from "@mariozechner/pi-ai";
import {
    loadSkills,
    formatSkillsForPrompt,
    getAgentDir,
    type Skill,
    type ResourceDiagnostic,
} from "@mariozechner/pi-coding-agent";
import { readFileSync } from "fs";
import { Type } from "typebox";
import "dotenv/config";

/**
 * PiWorker 集成 pi-mono (Pi Agent)
 * 使用 pi-agent-core 驱动对话逻辑，并集成 Skills 系统
 */
export class PiWorker extends GatewayWorker {
    private skillsState?: { skills: Skill[]; diagnostics: ResourceDiagnostic[] };

    constructor(
        workerId: string,
        registry?: WorkerRegistry,
        redisClient?: Redis,
        ...rest: any[]
    ) {
        super(workerId, registry, redisClient, ...rest);
    }

    getAgentTypes(): string[] {
        return ['pi-agent'];
    }

    /**
     * 从标准位置加载 Skills (~/.pi/agent/skills 和 ./.pi/skills)
     * 返回 skills 列表和诊断信息（冲突警告等）
     */
    private _loadSkills() {
        const result = loadSkills({
            cwd: process.cwd(),               // 当前工作目录，用于发现 ./.pi/skills/
            agentDir: getAgentDir(),          // 用户全局目录 ~/.pi/agent
            skillPaths: [],                   // 额外自定义路径（可选）
            includeDefaults: true,            // 启用默认路径发现
        });

        // 输出加载过程中的冲突或警告
        for (const d of result.diagnostics) {
            if (d.type === "collision") {
                console.warn(
                    `[Skill 冲突] "${d.collision!.name}" - 已加载: ${d.collision!.winnerPath}, 忽略: ${d.collision!.loserPath}`,
                );
            } else {
                console.warn(`[Skill 警告] ${d.message} (${d.path})`);
            }
        }

        if (result.skills.length > 0) {
            console.log(`[PiWorker] 已加载 ${result.skills.length} 个 Skills: ${result.skills.map((s) => s.name).join(", ")}`);
        } else {
            console.log('[PiWorker] 未加载到任何 Skills（如需使用，请将 Skill 目录放入 ~/.pi/agent/skills/ 或 ./.pi/skills/）');
        }

        return result;
    }

    /** 重新加载 Skills（在运行时新增/修改 Skill 后调用） */
    reloadSkills() {
        this.skillsState = this._loadSkills();
    }

    /**
     * 构建包含 Skills 的系统提示
     * 采用渐进式上下文：只注入 name + description，模型按需读取 SKILL.md
     */
    private _buildSystemPrompt(): string {
        if (!this.skillsState) {
            this.skillsState = this._loadSkills();
        }

        const skillsXml = formatSkillsForPrompt(this.skillsState.skills);

        return [
            "You are a helpful assistant powered by Pi Agent.",
            "",
            "你可以根据任务需要，使用 available_skills 中的技能来高效完成任务。",
            "当你决定使用某个 skill 时，请使用 read_file 工具读取其 location 路径的完整内容。",
            "",
            skillsXml,
        ].join("\n");
    }

    /**
     * 创建工具列表，核心工具：read_file（供模型读取 SKILL.md 使用）
     */
    private _createTools(): AgentTool<any>[] {
        return [
            // read_file：让模型按需读取 Skill 文件或其他文件
            {
                name: "read_file",
                label: "读取文件内容",
                description:
                    "Read the content of a file at the given path. " +
                    "Use this when a skill references its SKILL.md location or when the user asks about file contents.",
                parameters: Type.Object({ path: Type.String() }),
                execute: async (_id, params) => {
                    try {
                        const { path } = params as { path: string };
                        const text = readFileSync(path, "utf-8");
                        return {
                            content: [{ type: "text" as const, text }],
                            details: { path, size: text.length },
                        };
                    } catch (err) {
                        const message = err instanceof Error ? err.message : String(err);
                        return {
                            content: [
                                {
                                    type: "text" as const,
                                    text: `[Error reading file: ${message}]`,
                                },
                            ],
                            details: null as any,
                        };
                    }
                },
            },
            // 在此处添加你的其他工具（如 bash, write, edit, exec 等）...
        ];
    }

    /**
     * 核心处理逻辑
     */
    async processCommand(command: AskAgentCommand, context: AgentContext): Promise<ProcessCommandResult> {
        console.log(`[PiWorker] 收到请求: ${command.content}`);

        // 1. 获取基础模型定义
        const modelId = process.env.MODEL_NAME || "gpt-4o";
        let model = getModel("openai", modelId as any);

        if (!model) {
            model = {
                id: modelId,
                name: modelId,
                api: "openai-responses",
                provider: "openai",
                baseUrl: "https://api.openai.com/v1",
                reasoning: false,
                input: ["text", "image"],
                cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
                contextWindow: 128000,
                maxTokens: 4096
            } as any;
        }

        // 2. 支持自定义 URL
        const finalModel = Object.create(model);
        if (process.env.MODEL_BASE_URL) {
            finalModel.baseUrl = process.env.MODEL_BASE_URL;
        }

        // 3. 初始化 Agent 实例（注入 Skills 工具和系统提示）
        const agent = new Agent({
            initialState: {
                systemPrompt: this._buildSystemPrompt(),
                model: finalModel,
                tools: this._createTools(),
                messages: []
            },
            getApiKey: async () => process.env.MODEL_API_KEY
        });

        let fullResponse = "";

        // 4. 订阅事件流并推送到前端
        agent.subscribe((event) => {
            if (event.type === "message_update") {
                const assistantEvent = event.assistantMessageEvent;

                // 处理文本增量 (Token 流)
                if (assistantEvent.type === "text_delta") {
                    const delta = assistantEvent.delta;
                    fullResponse += delta;
                    context.emitChunk({ content: delta });
                }
                // 处理工具调用开始
                else if (assistantEvent.type === "toolcall_start") {
                    const part = (assistantEvent.partial as any).content?.[assistantEvent.contentIndex];
                    if (part && part.toolCall) {
                        context.emitChunk({ content: `\n[Pi Agent: 正在调用工具 ${part.toolCall.name}...]\n` });
                    }
                }
                // 处理工具结果
                else if (assistantEvent.type === "toolcall_end") {
                    context.emitChunk({ content: `\n[Pi Agent: 工具执行完毕]\n` });
                }
            }
        });

        // 5. 开始提示并执行
        let promptText = "";
        if (typeof command.content === 'string') {
            promptText = command.content;
        } else if (typeof command.content === 'object' && command.content !== null) {
            // 提取结构化消息中的文本
            const contentObj = (command.content as any).content;
            if (typeof contentObj === 'string') {
                promptText = contentObj;
            } else if (typeof contentObj === 'object' && contentObj !== null && contentObj.text) {
                promptText = contentObj.text;
            } else {
                promptText = JSON.stringify(command.content);
            }
        } else {
            promptText = String(command.content);
        }
        await agent.prompt(promptText);

        await context.emitChunk({ content: '\n\n[Pi Agent 流程执行完毕]' });

        return fullResponse;
    }
}
