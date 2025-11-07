"""接入通过vllm以兼容openai接口启动的大语言模型"""

import os
from typing import Optional

from langchain_openai import ChatOpenAI


def create_vllm_model(
    provider_name: str,
    model_name: str,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> ChatOpenAI:
    """创建一个由vllm启动的，兼容openai接口的大语言模型"""
    if base_url is None:
        base_url = os.getenv("VLLM_BASE_URL")
    if api_key is None:
        api_key = os.getenv("VLLM_API_KEY")

    # 创建配置字典
    model_config = {"model": model_name, "base_url": base_url, "api_key": api_key}

    # 返回实例
    return ChatOpenAI(**model_config)
