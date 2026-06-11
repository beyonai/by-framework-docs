"""
External app trace integration example.

This file simulates an application that does not run as a by-framework Worker.
It receives a plain AskAgentCommand payload, reads the trace fields from the
command header, and writes nested Langfuse observations into the same trace.
"""

from __future__ import annotations

import os
import time
from typing import Any

from dotenv import load_dotenv
from langfuse import Langfuse

from by_framework.trace import start_langfuse_observation

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


def handle_plain_ask_agent_command(command_payload: dict[str, Any]) -> dict[str, Any]:
    """Handle a plain AskAgentCommand dict and attach work to the framework trace.

    Required header fields:
    - trace_id: framework trace id
    - langfuse_parent_observation_id: parent observation id propagated by framework

    The parent id is present when the command is dispatched by GatewayClient or
    AgentContext.call_agent while Langfuse is enabled.
    """
    header = dict(command_payload.get("header", {}))
    body = dict(command_payload.get("body", {}))
    metadata = dict(header.get("metadata", {}) or {})

    parent_observation_id = str(
        header.get("langfuse_parent_observation_id")
        or metadata.get("langfuse_parent_observation_id")
        or ""
    )
    if not parent_observation_id:
        raise ValueError(
            "AskAgentCommand header is missing langfuse_parent_observation_id"
        )

    content = body.get("content", "")

    langfuse = Langfuse()
    external_pipeline = start_langfuse_observation(
        langfuse,
        command_payload,
        name="external_plain_app",
        as_type="span",
        input_data=content,
        metadata={
            "integration": "plain-ask-agent-command",
        },
    )

    try:
        validation = external_pipeline.start_observation(
            name="Validate_Command",
            as_type="span",
            input={"content": content},
        )
        time.sleep(0.02)
        validation.update(output={"valid": True})
        validation.end()

        generation = external_pipeline.start_observation(
            name="External_LLM_Call",
            as_type="generation",
            input=f"Answer this request: {content}",
            model="gpt-4o",
            model_parameters={"temperature": 0.2},
        )
        time.sleep(0.1)
        answer = f"External app handled: {content}"
        generation.update(
            output=answer,
            usage_details={
                "input": 12,
                "output": 8,
                "total": 20,
            },
        )
        generation.end()

        external_pipeline.update(output=answer)
        external_pipeline.end()
        langfuse.flush()
        return {"status": "COMPLETED", "reply_data": answer}
    except Exception as err:
        external_pipeline.update(
            output={"error": str(err)},
            level="ERROR",
            status_message=str(err),
        )
        external_pipeline.end()
        langfuse.flush()
        raise


if __name__ == "__main__":
    # Minimal local smoke example. In production, replace this payload with the
    # AskAgentCommand dict received from Redis, HTTP, Kafka, or another transport.
    example_command = {
        "action_type": "ASK_AGENT",
        "header": {
            "message_id": "msg-example",
            "session_id": "sess-example",
            "trace_id": "e1554c44efdd4adb99d1f4cd237a8566",
            "source_agent_type": "caller-agent",
            "target_agent_type": "external-plain-app",
            "parent_message_id": "msg-parent",
            "metadata": {},
            "langfuse_parent_observation_id": "4efed5f2f3964453",
        },
        "body": {
            "content": "hello from by-framework",
            "wait_for_reply": True,
        },
    }
    print(handle_plain_ask_agent_command(example_command))
