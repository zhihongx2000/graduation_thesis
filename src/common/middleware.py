"""创建通用的agent middleware，例如工具组中间件"""

from datetime import datetime
from typing import Any, Awaitable, Callable, cast

from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain.agents.middleware.types import ModelCallResult
from langchain.messages import HumanMessage
from langchain.tools import ToolRuntime, tool
from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool
from langchain_dev_utils.message_convert import format_sequence
from langgraph.types import Command
from typing_extensions import TypedDict

from . import load_chat_model


class ToolGroupState(AgentState):
    tool_group: list[str]


class ToolGroupType(TypedDict):
    group_name: str
    group_description: str
    group_tools: list[BaseTool]


@tool
def enable_tool_group(group_name_list: list[str], runtime: ToolRuntime):
    """启用若干个工具组"""
    tool_groups = runtime.state.get("tool_group", [])
    return Command(
        update={
            "messages": [
                ToolMessage(
                    content=f"success enable tool group:{group_name_list}",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
            "tool_group": list(set(tool_groups) | set(group_name_list)),
        }
    )


@tool
def disable_tool_group(group_name_list: list[str], runtime: ToolRuntime):
    """禁用若干个工具组"""
    tool_groups = runtime.state.get("tool_group", [])
    tool_groups = list(set(tool_groups) - set(group_name_list))
    return Command(
        update={
            "messages": [
                ToolMessage(
                    content=f"success disable tool group:{group_name_list}",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
            "tool_group": tool_groups,
        }
    )


_BASE_SYSTEM_PROMPT = """
你是一个智能助手，你的任务是帮助用户完成任务。
你有两个核心工具：
1. enable_tool_group: 启用若干个工具组
2. disable_tool_group: 禁用若干个工具组
接下来会给你若干个工具组，每个工具组中都有其名称、描述和若干个工具。（为了节省上下文，仅提供名称和描述，工具会在该工具组被激活时添加）
工具组有：
{tool_group}
你需要做的是，针对用户的问题，判断是否需要启用某些工具组，当你的工具数量太多的时候，也可以根据用户需求，选择某些工具组禁用。
请开始你的工作吧！
"""


class ToolGroupMiddleware(AgentMiddleware):
    state_schema = ToolGroupState

    def __init__(
        self,
        tool_group: list[ToolGroupType],
    ) -> None:
        super().__init__()
        self.tool_group = tool_group
        tool_group_desc = format_sequence(
            [
                f"{tool_group['group_name']}: {tool_group['group_description']}"
                for tool_group in tool_group
            ],
            with_num=True,
        )
        self.system_prompt = _BASE_SYSTEM_PROMPT.format(tool_group=tool_group_desc)
        additional_tools = []
        for group in tool_group:
            additional_tools.extend(group["group_tools"])
        self.tools = [
            enable_tool_group,
            disable_tool_group,
            *additional_tools,
        ]

    def _get_tools(self, state: Any) -> list[BaseTool | dict]:
        tools = [
            enable_tool_group,
            disable_tool_group,
        ]
        enable_tool_group_name_list = state.get("tool_group", [])
        for tool_group in self.tool_group:
            if tool_group["group_name"] in enable_tool_group_name_list:
                tools.extend(tool_group["group_tools"])
        return cast(list[BaseTool | dict], tools)

    def wrap_model_call(
        self, request: ModelRequest, handler: Callable[[ModelRequest], ModelResponse]
    ) -> ModelCallResult:
        request.system_prompt = (
            request.system_prompt + "\n\n" + self.system_prompt
            if request.system_prompt
            else self.system_prompt
        )
        request.tools = self._get_tools(state=request.state)
        return handler(request)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelCallResult:
        request.system_prompt = (
            request.system_prompt + "\n\n" + self.system_prompt
            if request.system_prompt
            else self.system_prompt
        )
        request.tools = self._get_tools(state=request.state)
        return await handler(request)


if __name__ == "__main__":

    @tool
    def get_current_time():
        """获取当前时间"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @tool
    def get_current_weather():
        """获取当前天气"""
        return "晴天"

    @tool
    def get_current_user():
        """获取当前用户"""
        return "张三"

    @tool
    def get_current_city():
        """获取当前城市"""
        return "New York"

    @tool
    def recommend_movie():
        """推荐电影"""
        return "电影XXX"

    @tool
    def recommend_music():
        """推荐音乐"""
        return "音乐XXX"

    llm = load_chat_model("openai_qwen:qwen-max")
    
    agent = create_agent(
        llm,
        middleware=[
            ToolGroupMiddleware(
                tool_group=[
                    {
                        "group_name": "实用性工具",
                        "group_description": "一些实用性工具，帮助用户完成任务，包括查询时间、查询天气、查询用户、查询城市",
                        "group_tools": [
                            get_current_time,
                            get_current_weather,
                            get_current_user,
                            get_current_city,
                        ],
                    },
                    {
                        "group_name": "娱乐工具",
                        "group_description": "一些娱乐工具，帮助用户完成任务，包括推荐电影、推荐音乐",
                        "group_tools": [
                            recommend_movie,
                            recommend_music,
                        ],
                    },
                ]
            )
        ],
    )
    
    result = agent.invoke(
        input = {
            "messages":[
                HumanMessage(content="现在日期是什么时候？")
            ]
        }
    )
    print(result)
