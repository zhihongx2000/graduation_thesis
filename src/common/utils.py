"""定义一些常用的辅助函数，例如：init_chat_model()"""

from typing import Union

from langchain.chat_models import BaseChatModel, init_chat_model
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI


def get_message_text(msg: BaseMessage) -> str:
    """Get the text content of a message."""
    content = msg.content
    if isinstance(content, str):
        return content
    elif isinstance(content, dict):
        return content.get("text", "")
    else:
        txts = [c if isinstance(c, str) else (c.get("text") or "") for c in content]
        return "".join(txts).strip()


def load_chat_model(
    fully_specified_name: str,
) -> Union[BaseChatModel, ChatOpenAI]:
    """Load a chat model from a fully specified name.

    Args:
        fully_specified_name (str): String in the format 'provider:model'.
    """
    provider, model = fully_specified_name.split(":", maxsplit=1)
    provider_lower = provider.lower()

    # 处理由 vllm 启动的模型
    if provider_lower == "vllm":
        from .models import create_vllm_model

        return create_vllm_model(provider_lower, model)

    # 处理 兼容openai接口 启动的模型：openai_deepseek,openai_qwen
    if provider_lower in ["openai_deepseek", "openai_qwen"]:
        from .models import create_openai_compatible_model

        return create_openai_compatible_model(provider_lower, model)

    # 处理其他模型提供商
    return init_chat_model(model, model_provider=provider)


if __name__ == "__main__":
    
    llm = load_chat_model("openai_deepseek:deepseek-reasoner")
    result = llm.invoke("你好，请简单介绍你自己。")
    print(result.content)
    print()
    
    llm = load_chat_model("openai_qwen:qwen-max")
    result = llm.invoke("你好，请简单介绍你自己。")
    print(result.content)
    print()