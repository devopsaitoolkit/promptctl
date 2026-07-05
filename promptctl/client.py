"""API client for the DevOps AI ToolKit prompt API (stdlib only).

The API (https://devopsaitoolkit.com/api/v1) serves static, cacheable JSON:
  - meta.json                    — index, counts, categories
  - prompts.json                 — every prompt (with full prompt text)
  - prompts/{category}.json      — prompts in one category

Responses are cached under ~/.cache/promptctl with a TTL so repeated queries are
fast and work offline after the first fetch.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Optional

__version__ = "0.1.0"

DEFAULT_BASE_URL = os.environ.get(
    "PROMPTCTL_BASE_URL", "https://devopsaitoolkit.com/api/v1"
)
DEFAULT_TTL = int(os.environ.get("PROMPTCTL_CACHE_TTL", "3600"))
CACHE_DIR = Path(
    os.environ.get("PROMPTCTL_CACHE_DIR", str(Path.home() / ".cache" / "promptctl"))
)
USER_AGENT = f"promptctl/{__version__} (+https://github.com/devopsaitoolkit/promptctl)"


class APIError(RuntimeError):
    """Raised when the API can't be reached or returns an error."""


class PromptClient:
    """Read-only client for the prompt API."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        ttl: int = DEFAULT_TTL,
        cache: bool = True,
        timeout: int = 30,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.ttl = ttl
        self.cache = cache
        self.timeout = timeout

    # -- low-level fetch with caching -------------------------------------
    def _cache_path(self, path: str) -> Path:
        return CACHE_DIR / (path.replace("/", "__"))

    def _read_cache(self, path: str, allow_stale: bool = False) -> Optional[Any]:
        cp = self._cache_path(path)
        if not cp.exists():
            return None
        if not allow_stale and (time.time() - cp.stat().st_mtime) >= self.ttl:
            return None
        try:
            return json.loads(cp.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return None

    def _write_cache(self, path: str, data: Any) -> None:
        if not self.cache:
            return
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            self._cache_path(path).write_text(
                json.dumps(data), encoding="utf-8"
            )
        except OSError:
            pass  # cache is best-effort

    def fetch(self, path: str, refresh: bool = False) -> Any:
        """Fetch and decode a JSON resource (e.g. 'prompts.json'), using the cache."""
        if self.cache and not refresh:
            cached = self._read_cache(path)
            if cached is not None:
                return cached

        url = f"{self.base_url}/{path}"
        req = urllib.request.Request(
            url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise APIError(f"HTTP {exc.code} fetching {url}") from exc
        except urllib.error.URLError as exc:
            stale = self._read_cache(path, allow_stale=True)
            if stale is not None:
                return stale  # offline: serve stale cache rather than fail
            raise APIError(f"Network error fetching {url}: {exc.reason}") from exc
        except ValueError as exc:
            raise APIError(f"Invalid JSON from {url}: {exc}") from exc

        self._write_cache(path, data)
        return data

    # -- high-level API ----------------------------------------------------
    def meta(self, refresh: bool = False) -> dict:
        """Return the API index (counts, categories, endpoints)."""
        return self.fetch("meta.json", refresh=refresh)

    def prompts(self, category: Optional[str] = None, refresh: bool = False) -> list[dict]:
        """Return prompts, optionally scoped to a single category slug."""
        path = f"prompts/{category}.json" if category else "prompts.json"
        return self.fetch(path, refresh=refresh).get("items", [])

    def get(self, prompt_id: str, refresh: bool = False) -> Optional[dict]:
        """Return a single prompt by id, or None if not found."""
        for prompt in self.prompts(refresh=refresh):
            if prompt.get("id") == prompt_id:
                return prompt
        return None

    def categories(self, refresh: bool = False) -> list[dict]:
        """Return the category list with per-category counts."""
        return self.meta(refresh=refresh).get("categories", [])

    def search(
        self,
        query: str = "",
        category: Optional[str] = None,
        difficulty: Optional[str] = None,
        tool: Optional[str] = None,
        tag: Optional[str] = None,
        refresh: bool = False,
    ) -> list[dict]:
        """Search prompts. All words in `query` must match somewhere in the
        title, use case, target user, tags, category, or prompt body. Filters
        (category/difficulty/tool/tag) are ANDed with the query."""
        items = self.prompts(category=category, refresh=refresh)
        terms = [t for t in query.lower().split() if t]

        def matches(p: dict) -> bool:
            if difficulty and p.get("difficulty", "").lower() != difficulty.lower():
                return False
            if tool and tool.lower() not in [t.lower() for t in p.get("tools", [])]:
                return False
            if tag and tag.lower() not in [t.lower() for t in p.get("tags", [])]:
                return False
            if not terms:
                return True
            blob = " ".join(
                [
                    p.get("title", ""),
                    p.get("useCase", ""),
                    p.get("targetUser", ""),
                    " ".join(p.get("tags", [])),
                    p.get("category", ""),
                    p.get("prompt", ""),
                ]
            ).lower()
            return all(term in blob for term in terms)

        return [p for p in items if matches(p)]
