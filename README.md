# promptctl

A tiny command-line tool (and Python SDK) for querying the **[DevOps AI ToolKit](https://devopsaitoolkit.com) prompt library** — search, filter, and print production-ready DevOps/SRE AI prompts straight from your terminal, ready to paste into Claude, ChatGPT, or Cursor.

- **Zero dependencies** — pure Python standard library. `pip install promptctl` pulls nothing else.
- **Fast + offline-friendly** — the API is static JSON; responses are cached locally with a TTL, so repeat queries are instant and work offline after the first fetch.
- **Scriptable** — every command supports `--json` for piping into `jq`.

It talks to the public read-only API at `https://devopsaitoolkit.com/api/v1`.

> Looking for error guides / runbooks instead of prompts? A companion tool for the guides API is coming separately.

## Install

```bash
pip install promptctl                     # once published to PyPI
pip install git+https://github.com/devopsaitoolkit/promptctl   # latest from GitHub
```

From source:

```bash
git clone https://github.com/devopsaitoolkit/promptctl && cd promptctl
pip install -e .
```

Requires Python 3.8+.

## Usage

```bash
# Search (all words must match title, use case, tags, category, or prompt body)
promptctl search kubernetes crashloopbackoff
promptctl search terraform --difficulty Advanced --limit 5
promptctl search "" --category openstack        # everything in a stack

# List
promptctl list --category terraform
promptctl categories                            # categories with prompt counts

# Show the full prompt text (ready to copy)
promptctl show terraform-plan-review
promptctl show terraform-plan-review --copy      # also copy to clipboard
promptctl show terraform-plan-review --raw       # just the prompt text (pipe-friendly)

# API metadata / counts
promptctl meta
```

### Global options

| Flag | Meaning |
|---|---|
| `--json` | Machine-readable JSON output (per command) |
| `--refresh` | Bypass the local cache for this call |
| `--no-cache` | Don't read or write the cache at all |
| `--base-url URL` | Point at a different API base |
| `--version` | Print the version |

### Environment variables

| Var | Default | Purpose |
|---|---|---|
| `PROMPTCTL_BASE_URL` | `https://devopsaitoolkit.com/api/v1` | API base URL |
| `PROMPTCTL_CACHE_DIR` | `~/.cache/promptctl` | Where cached JSON lives |
| `PROMPTCTL_CACHE_TTL` | `3600` | Cache freshness, in seconds |

### Pipe-friendly examples

```bash
promptctl search kubernetes --json | jq -r '.[].id'
promptctl show terraform-plan-review --raw | pbcopy
```

## SDK

```python
from promptctl import PromptClient

client = PromptClient()
hits = client.search("crashloopbackoff", difficulty="Advanced")
for p in hits:
    print(p["id"], "-", p["title"])

full = client.get("terraform-plan-review")
print(full["prompt"])
```

## The API

`promptctl` is a thin client over the public prompt API:

| Endpoint | Returns |
|---|---|
| `GET /api/v1/meta.json` | index: counts, categories, endpoint list |
| `GET /api/v1/prompts.json` | every prompt, with full prompt text |
| `GET /api/v1/prompts/{category}.json` | prompts in one category |

Each prompt record: `id`, `title`, `category`, `difficulty`, `tools`, `tags`, `useCase`, `targetUser`, `prompt`, `safetyNotes`, `url`, `pubDate`.

## Development

```bash
python -m unittest discover -s tests -v     # tests are offline (no network)
python -m promptctl search kubernetes        # run without installing
```

## License

MIT © DevOps AI ToolKit. Prompt content is © DevOps AI ToolKit — free to query for personal and internal use; please attribute with a link back.
