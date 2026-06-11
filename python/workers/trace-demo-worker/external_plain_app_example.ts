/**
 * External app trace integration example in TypeScript.
 *
 * This file simulates an application that does not run as a by-framework Worker.
 * It receives a plain AskAgentCommand payload, reads the trace fields from the
 * command header, and writes nested Langfuse observations into the same trace.
 */

import * as crypto from 'crypto';
import * as dotenv from 'dotenv';
import * as path from 'path';
import { Langfuse } from 'langfuse';

// Load environment variables from .env file in the same directory
dotenv.config({ path: path.join(__dirname, '.env') });

/**
 * Command Payload interface matching the structure of AskAgentCommand.
 */
export interface CommandPayload {
  action_type: string;
  header: {
    message_id: string;
    session_id: string;
    trace_id: string;
    source_agent_type: string;
    target_agent_type: string;
    parent_message_id?: string;
    metadata?: Record<string, any>;
    langfuse_parent_observation_id?: string;
  };
  body: {
    content: string;
    wait_for_reply?: boolean;
  };
}

/**
 * Match by-framework's deterministic conversion to an OTel/Langfuse trace id.
 */
function strToUint128(value: string): bigint {
  if (value.length === 32) {
    try {
      if (/^[0-9a-fA-F]{32}$/.test(value)) {
        return BigInt('0x' + value);
      }
    } catch (e) {
      // Ignore conversion failure and fallback to md5
    }
  }
  const hash = crypto.createHash('md5').update(value).digest('hex');
  const converted = BigInt('0x' + hash);
  return converted === 0n ? 1n : converted;
}

/**
 * Convert MessageHeader.trace_id into the 32-char hex id used by Langfuse.
 */
function toLangfuseTraceId(frameworkTraceId: string): string {
  return strToUint128(frameworkTraceId).toString(16).padStart(32, '0');
}

/**
 * Helper to simulate delay/sleep.
 */
const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Helper to clean environment variables (removing wrapped single/double quotes).
 */
const cleanEnvVar = (value: string | undefined): string | undefined => {
  if (!value) return value;
  return value.replace(/^['"]|['"]$/g, '');
};

/**
 * Handle a plain AskAgentCommand payload and attach work to the framework trace.
 *
 * Required header fields:
 * - trace_id: framework trace id
 * - langfuse_parent_observation_id: parent observation id propagated by framework
 *
 * The parent id is present when the command is dispatched by GatewayClient or
 * AgentContext.call_agent while Langfuse is enabled.
 */
export async function handlePlainAskAgentCommand(commandPayload: CommandPayload): Promise<any> {
  const header = commandPayload.header || {};
  const body = commandPayload.body || {};
  const metadata = header.metadata || {};

  const frameworkTraceId = String(header.trace_id);
  const parentObservationId = String(
    header.langfuse_parent_observation_id ||
    metadata.langfuse_parent_observation_id ||
    ""
  );

  if (!parentObservationId) {
    throw new Error(
      "AskAgentCommand header is missing langfuse_parent_observation_id"
    );
  }

  const traceId = toLangfuseTraceId(frameworkTraceId);
  const content = body.content || "";

  // Clean environment variables to prevent issues with wrapped quotes (common when loaded by some shell utilities)
  const publicKey = cleanEnvVar(process.env.LANGFUSE_PUBLIC_KEY);
  const secretKey = cleanEnvVar(process.env.LANGFUSE_SECRET_KEY);
  const baseUrl = cleanEnvVar(process.env.LANGFUSE_BASE_URL);

  // Initialize Langfuse explicitly with cleaned credentials
  const langfuse = new Langfuse({
    publicKey,
    secretKey,
    baseUrl,
  });

  // Start the root span representing this external application integration
  const externalPipeline = langfuse.span({
    name: "external_plain_app",
    traceId: traceId,
    parentObservationId: parentObservationId,
    input: content,
    metadata: {
      session_id: header.session_id || "",
      message_id: header.message_id || "",
      source_agent_type: header.source_agent_type || "",
      target_agent_type: header.target_agent_type || "",
      integration: "plain-ask-agent-command",
    },
  });


  try {
    // 1. Validation observation
    const validation = externalPipeline.span({
      name: "Validate_Command",
      input: { content: content },
    });
    await delay(20);
    validation.update({ output: { valid: true } });
    validation.end();

    // 2. LLM Call observation (generation)
    const generation = externalPipeline.generation({
      name: "External_LLM_Call",
      input: `Answer this request: ${content}`,
      model: "gpt-4o",
      modelParameters: { temperature: 0.2 },
    });
    await delay(100);
    const answer = `External app handled: ${content}`;

    // Update generation output and usage tokens
    generation.update({
      output: answer,
      usage: {
        promptTokens: 12,
        completionTokens: 8,
        totalTokens: 20,
      },
    });
    generation.end();

    // Finalize outer span
    externalPipeline.update({ output: answer });
    externalPipeline.end();

    // Flush the queue to ensure all events are sent before returning
    await langfuse.flushAsync();

    return { status: "COMPLETED", reply_data: answer };
  } catch (err: any) {
    externalPipeline.update({
      output: { error: err.message || String(err) },
      level: "ERROR",
      statusMessage: err.message || String(err),
    });
    externalPipeline.end();
    await langfuse.flushAsync();
    throw err;
  }
}

// Check if this module is run directly by node or a ts runner
const isMain = (): boolean => {
  if (typeof require !== 'undefined' && typeof module !== 'undefined' && require.main === module) {
    return true;
  }
  if (process.argv[1]) {
    const mainPath = process.argv[1];
    return mainPath.endsWith('external_plain_app_example.ts') || mainPath.endsWith('external_plain_app_example.js');
  }
  return false;
};

if (isMain()) {
  // Minimal local smoke example. In production, replace this payload with the
  // AskAgentCommand dict received from Redis, HTTP, Kafka, or another transport.
  const exampleCommand: CommandPayload = {
    action_type: "ASK_AGENT",
    header: {
      message_id: "msg-example",
      session_id: "sess-example",
      trace_id: "50d8a2ca5bcb4506a152aaefdf59b1f4",
      source_agent_type: "caller-agent",
      target_agent_type: "external-plain-app",
      parent_message_id: "msg-parent",
      metadata: {},
      langfuse_parent_observation_id: "4030fd5ae018a087",
    },
    body: {
      content: "hello from by-framework",
      wait_for_reply: true,
    },
  };

  console.log("Running TypeScript external plain app example...");
  handlePlainAskAgentCommand(exampleCommand)
    .then((result) => {
      console.log("Result:", result);
    })
    .catch((err) => {
      console.error("Error executing command:", err);
    });
}
