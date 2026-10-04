import logging
import os
import sys
from pathlib import Path
from langchain_mcp_adapters.client import MultiServerMCPClient

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def build_server_config() -> dict:
    return {
        "travel": {
            "transport": "stdio",
            "command": sys.executable,
            "args": ["-m", "app.mcp_tools.servers.travel_server"],
            "cwd": str(PROJECT_ROOT),
            "env": dict(os.environ),
        }
    }


class MCPToolProvider:
    """Connects to MCP servers and returns their tools as LangChain tools."""

    def __init__(self, servers: dict):
        self._client = MultiServerMCPClient(servers)

    async def load(self, allowed: set[str] | None = None) -> list:
        tools = await self._client.get_tools()
        if allowed is not None:
            tools = [t for t in tools if t.name in allowed]
        logger.info("MCP tools loaded: %s", [t.name for t in tools])
        return tools