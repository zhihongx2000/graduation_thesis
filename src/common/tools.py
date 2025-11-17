"""定义一些通用工具，例如：联网搜索工具、时间获取工具"""

import asyncio
import datetime
from typing import Any, Callable, List, cast

from langchain.agents import create_agent
from langchain.tools import tool
from langchain_tavily import TavilySearch
from langgraph.runtime import Runtime, get_runtime

from .context import Context
from .logger import get_logger

logger = get_logger(__name__)


@tool
async def get_current_time() -> str:
	"""获取当前时间"""
	return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@tool(description="Search for general web results.")
async def web_search(query: str) -> str:
	"""Search for general web results.

	This function performs a search using the Tavily search engine, which is designed
	to provide comprehensive, accurate, and trusted results. It's particularly useful
	for answering questions about current events.
	"""
	runtime = get_runtime(Context)
	wrapped = TavilySearch(max_results=runtime.context.max_search_results)
	return cast(dict[str, Any], await wrapped.ainvoke({"query": query}))


async def get_tools(runtime: Runtime) -> List[Callable[..., Any]]:
	"""Get all available tools based on configuration."""
	tools = [
		get_current_time,
		web_search,
	]

	runtime = get_runtime(Context)

	# 添加 deepwiki mcp 工具
	if runtime.context.enable_deepwiki:
		from .mcp import get_deepwiki_tools
		deepwiki_tools = await get_deepwiki_tools()
		tools.extend(deepwiki_tools)
		logger.info(f"Loaded {len(deepwiki_tools)} deepwiki tools")

	# 添加 mineru mcp 工具
	if runtime.context.enable_mineru:
		from .mcp import get_mineru_tools
		mineru_tools = await get_mineru_tools()
		tools.extend(mineru_tools)
		logger.info(f"Loaded {len(mineru_tools)} mineru_tools tools")

	return tools
