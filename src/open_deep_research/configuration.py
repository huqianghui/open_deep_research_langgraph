import os
from dataclasses import dataclass, fields
from enum import Enum
from typing import Any, Optional

from langchain_core.runnables import RunnableConfig

DEFAULT_REPORT_STRUCTURE = """Use this structure to create a report on the user-provided topic:

1. Introduction (no research needed)
   - Brief overview of the topic area

2. Main Body Sections:
   - Each section should focus on a sub-topic of the user-provided topic
   
3. Conclusion
   - Aim for 1 structural element (either a list of table) that distills the main body sections 
   - Provide a concise summary of the report"""

class SearchAPI(Enum):
    AZURE = "bing_search"
    PERPLEXITY = "perplexity"
    TAVILY = "tavily"

class PlannerProvider(Enum):
    AZURE_OPENAI = "azure_openai"
    OPENAI = "openai"
    GROQ = "groq"

class WriterProvider(Enum):
    AZURE_OPENAI = "azure_openai"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GROQ = "groq"

@dataclass(kw_only=True)
class Configuration:
    """The configurable fields for the chatbot."""
    report_structure: str = DEFAULT_REPORT_STRUCTURE # Defaults to the default report structure
    number_of_queries: int = 2 # Number of search queries to generate per iteration
    max_search_depth: int = 2 # Maximum number of reflection + search iterations
    planner_provider: PlannerProvider = PlannerProvider.AZURE_OPENAI  # Defaults to OpenAI as provider
    planner_model: str = "o3-mini" # Defaults to OpenAI o3-mini as planner model
    writer_provider: WriterProvider = WriterProvider.AZURE_OPENAI   # Defaults to Anthropic as provider
    writer_model: str = "o3-mini" # Defaults to Anthropic as provider
    search_api: SearchAPI = SearchAPI.AZURE # Default to TAVILY

    # 下面是 Azure OpenAI 相关的字段
    azure_endpoint: str = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
    deployment_name: str = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "")
    openai_api_version: str = os.environ.get("AZURE_OPENAI_API_VERSION", "")
    openai_api_key: str = os.environ.get("AZURE_OPENAI_API_KEY", "")

    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> "Configuration":
        """Create a Configuration instance from a RunnableConfig."""
        configurable = (
            config["configurable"] if config and "configurable" in config else {}
        )
        values: dict[str, Any] = {
            f.name: os.environ.get(f.name.upper(), configurable.get(f.name))
            for f in fields(cls)
            if f.init
        }
        return cls(**{k: v for k, v in values.items() if v})