"""定义agent运行时，可提供的上下文，例如：模型选择、提示词选择..."""

from dataclasses import dataclass, field
from typing import Annotated

from . import prompts


@dataclass
class Context:
    """智能体运行时，提供给智能体的上下文"""

    system_prompt: str = field(
        default=prompts.SYSTEM_PROMPT,
        metadata={
            "description": "The system prompt to use for the agent's interactions. "
            "This prompt sets the context and behavior for the agent.",
        },
    )

    model: Annotated[str, {"__template_metadata__": {"provider": "llm"}}] = field(
        default="zhipu:glm-4.5-flash",
        metadata={
            "description": "The name of the language model to use for the agent's main interactions. "
            "Should be in the form: provider:model-name.",
            "json_schema_extra": {"langgraph_nodes": ["call_model"]},
        },
    )

    max_search_results: int = field(
        default=5,
        metadata={
            "description": "The maximum number of search results to return for each search query.",
            "json_schema_extra": {"langgraph_nodes": ["tools"]},
        },
    )

    max_rag_search_results: int = field(
        default=5,
        metadata={
            "description": "The maximum number of search results to return from the RAG system.",
        },
    )

    enable_deepwiki: bool = field(
        default=False,
        metadata={
            "description": "Whether to enable the DeepWiki MCP tool for accessing open source project documentation.",
            "json_schema_extra": {"langgraph_nodes": ["tools"]},
        },
    )
    
    enable_mineru: bool = field(
        default=True,
        metadata={
            "description": "Whether to enable the MCP tool for document processing,.",
            "json_schema_extra": {"langgraph_nodes": ["tools"]},
        },
    )

    def __post_init__(self) -> None:
        """Fetch env vars for attributes that were not passed as args."""
        import os
        from dataclasses import fields

        for f in fields(self):
            if not f.init:
                continue

            current_value = getattr(self, f.name)
            default_value = f.default
            env_var_name = f.name.upper()
            env_value = os.environ.get(env_var_name)

            # Only override with environment variable if current value equals default
            # This preserves explicit configuration from LangGraph configurable
            if current_value == default_value and env_value is not None:
                if isinstance(default_value, bool):
                    # Handle boolean environment variables
                    env_bool_value = env_value.lower() in ("true", "1", "yes", "on")
                    setattr(self, f.name, env_bool_value)
                else:
                    setattr(self, f.name, env_value)
