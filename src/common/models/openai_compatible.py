"""处理兼容openai接口的主流模型，例如deepseek，qwen等"""

import os
from typing import Optional

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


load_dotenv()


def create_openai_compatible_model(
		provider_name: str,
		model_name: str,
		base_url: Optional[str] = None,
		api_key: Optional[str] = None,
) -> ChatOpenAI:
	"""创建兼容openai接口的模型，如：deepseek, qwen"""

	# 处理 deepseek 系列模型
	if provider_name == "openai_deepseek":
		if base_url is None:
			base_url = os.getenv("DEEPSEEK_BASE_URL")
		if api_key is None:
			api_key = os.getenv("DEEPSEEK_API_KEY")
	elif provider_name == "openai_qwen":
		if base_url is None:
			base_url = os.getenv("DASHSCOPE_BASE_URL")
		if api_key is None:
			api_key = os.getenv("DASHSCOPE_API_KEY")
	elif provider_name == "openai_silicon":
		if base_url is None:
			base_url = os.getenv("SILICONFLOW_BASE_URL")
		if api_key is None:
			api_key = os.getenv("SILICONFLOW_API_KEY")
	else:
		raise ValueError(f"不支持的模型提供者：{provider_name}")
	# 创建配置字典
	model_config = {"model": model_name, "base_url": base_url, "api_key": api_key}

	print(model_config)

	# 返回实例
	return ChatOpenAI(**model_config)


if __name__ == "__main__":
	llm = create_openai_compatible_model(
		provider_name="openai_deepseek",
		model_name="deepseek-chat"
	)
	result = llm.invoke("你好，请简单介绍你自己。")
	print(result)
	print(result.content_blocks)

	llm = create_openai_compatible_model(
		provider_name="openai_qwen",
		model_name="qwen-max"
	)
	result = llm.invoke("你好，请简单介绍你自己。")
	print(result.content)
	print()
