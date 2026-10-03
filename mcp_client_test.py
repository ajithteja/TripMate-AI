import os
import asyncio
import certifi
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
import json


os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUEST_CA_BUNDLE"] = certifi.where()

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")


client = MultiServerMCPClient(
    {
        "tavily": {
            "transport": "streamable_http",
            "url": f"https://mcp.tavily.com/mcp/?tavilyApiKey={TAVILY_API_KEY}"
        }
    }
)


async def get_all_tools():
    tools = await client.get_tools()

    for tool in tools:
        print(tool.name)



# This returns tavily_search tool object
tavily_search_tool = None

async def get_tavily_search_tool():
    global tavily_search_tool
    if tavily_search_tool is not None:
        return

    tools = await client.get_tools()
    print("\nAvailable MCP Toolss:")

    for tool in tools:
        print(tool.name)

    tavily_search_tool = next(
        tool
        for tool in tools
        if tool.name == "tavily_search"
    )

    # return tavily_search_tool


# async def tavily_mcp_search(query: str):
#     await get_tavily_search_tool()
#     result = await tavily_search_tool.ainvoke(
#         {
#             "query": query
#         }
#     )

#     print("result ", result)

#     return result



async def tavily_mcp_search(query: str):
    await get_tavily_search_tool()

    result = await tavily_search_tool.ainvoke(
        {"query": query}
    )

    raw_text = result[0]["text"]
    data = json.loads(raw_text)

    results = []

    for item in data.get("results", [])[:3]:
        content = item.get("content", "")

        results.append(
            f"Title: {item.get('title')}\n"
            f"Information: {content[:600]}\n"
            f"Source: {item.get('url')}"
        )

    return "\n\n".join(results)