from fastmcp import Client

from app.config import MCP_SERVER_URL


async def call_mcp_tool(tool_name: str, arguments: dict):
    client = Client(MCP_SERVER_URL)

    async with client:
        result = await client.call_tool(tool_name, arguments)

    return result.data