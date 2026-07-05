"""promptctl — a tiny CLI/SDK for querying the DevOps AI ToolKit prompt API.

Queries https://devopsaitoolkit.com/api/v1 for DevOps AI prompts: search,
list, filter by stack/difficulty, and print the full prompt text ready to
copy into Claude, ChatGPT, or Cursor. Zero runtime dependencies (stdlib only).
"""

__version__ = "0.1.0"

from .client import PromptClient, APIError, DEFAULT_BASE_URL

__all__ = ["PromptClient", "APIError", "DEFAULT_BASE_URL", "__version__"]
