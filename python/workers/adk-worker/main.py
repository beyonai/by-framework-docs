"""Sample ADK Worker implementation.

This sample demonstrates how to build a worker that integrates with
Google ADK (Agent Development Kit).
"""

import asyncio
import os
import datetime
from zoneinfo import ZoneInfo

from by_framework.core.protocol.commands import GatewayCommand
from by_framework.worker.app import run_worker
from by_framework.worker.context import AgentContext
from by_framework_adk.worker import AdkWorker

from dotenv import load_dotenv

from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm

load_dotenv()

def get_current_time(city: str) -> dict:
    """Returns the current time in a specified city.

    Args:
        city (str): The name of the city for which to retrieve the current time.

    Returns:
        dict: status and result or error msg.
    """

    if city.lower() == "new york":
        tz_identifier = "America/New_York"
    else:
        return {
            "status": "error",
            "error_message": (
                f"Sorry, I don't have timezone information for {city}."
            ),
        }

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    report = (
        f'The current time in {city} is {now.strftime("%Y-%m-%d %H:%M:%S %Z%z")}'
    )
    return {"status": "success", "report": report}

def get_weather(city: str) -> dict:
    """Retrieves the current weather report for a specified city.

    Args:
        city (str): The name of the city for which to retrieve the weather report.

    Returns:
        dict: status and result or error msg.
    """
    if city.lower() == "new york":
        return {
            "status": "success",
            "report": (
                "The weather in New York is sunny with a temperature of 25 degrees"
                " Celsius (77 degrees Fahrenheit)."
            ),
        }
    else:
        return {
            "status": "error",
            "error_message": f"Weather information for '{city}' is not available. I can only provide weather information for New York.",
        }

class SampleAdkWorker(AdkWorker):
    """A sample worker using Google ADK."""

    def get_agent_types(self) -> list[str]:
        """Define the agent types this worker handles."""
        return ["sample-adk-agent"]

    def build_agent(self, context: AgentContext, command: GatewayCommand) -> LlmAgent:
        """Build and configure the ADK Agent.
        
        You can use context or command parameters here to customize 
        the agent instruction per session or user request.
        """
        instruction = (
            "You are a helpful assistant. "
            "Your main task is to help users get the current weather and time information. "
            "Always be concise and accurate."
        )

        return LlmAgent(
            name="sample_weather_time_assistant",
            model=LiteLlm(
                model=os.getenv("LLM_MODEL", "gpt-4o"),
                temperature=0.2,
                api_key=os.getenv("OPENAI_API_KEY"),
                api_base=os.getenv("OPENAI_BASE_URL"),
                parallel_tool_calls=True,
            ),
            tools=[get_current_time, get_weather],
            instruction=instruction,
        )


if __name__ == "__main__":
    # Ensure Redis is running locally, or configure the BYAI_REDIS_URL env variable.
    run_worker(
        SampleAdkWorker,
        worker_id=os.getenv("BYAI_WORKER_ID", "adk-worker"),
        redis_host=os.getenv("BYAI_REDIS_HOST", "127.0.0.1"),
        redis_port=int(os.getenv("BYAI_REDIS_PORT", 6379)),
        redis_username=os.getenv("BYAI_REDIS_USERNAME", ""),
        redis_password=os.getenv("BYAI_REDIS_PASSWORD", ""),
    )