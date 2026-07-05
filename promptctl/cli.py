"""Command-line interface for promptctl."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import textwrap
from typing import Optional

from . import __version__
from .client import DEFAULT_BASE_URL, APIError, PromptClient

# ---- tiny tty-aware styling (no dependencies) --------------------------------
_TTY = sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _TTY else text


def bold(t: str) -> str:
    return _c("1", t)


def dim(t: str) -> str:
    return _c("2", t)


def accent(t: str) -> str:
    return _c("36", t)


def err(msg: str) -> None:
    print(_c("31", "error:") + " " + msg, file=sys.stderr)


# ---- rendering ---------------------------------------------------------------
def _print_row(p: dict) -> None:
    meta = " · ".join(
        x for x in [accent(p.get("category", "")), p.get("difficulty", "")] if x
    )
    print(f"{bold(p.get('id', ''))}  {meta}")
    title = p.get("title", "")
    if title:
        print(f"  {title}")
    use = p.get("useCase", "")
    if use:
        print(dim("  " + textwrap.shorten(use, width=100, placeholder="…")))
    print()


def _copy_to_clipboard(text: str) -> bool:
    for cmd in (["pbcopy"], ["wl-copy"], ["xclip", "-selection", "clipboard"], ["clip"]):
        if shutil.which(cmd[0]):
            try:
                subprocess.run(cmd, input=text.encode("utf-8"), check=True)
                return True
            except (subprocess.SubprocessError, OSError):
                continue
    return False


# ---- commands ----------------------------------------------------------------
def cmd_search(args: argparse.Namespace, client: PromptClient) -> int:
    results = client.search(
        query=" ".join(args.query),
        category=args.category,
        difficulty=args.difficulty,
        tool=args.tool,
        tag=args.tag,
        refresh=args.refresh,
    )
    if args.limit:
        results = results[: args.limit]
    if args.json:
        print(json.dumps(results, indent=2))
        return 0
    if not results:
        print("No matching prompts.")
        return 0
    print(bold(f"{len(results)} prompt(s):\n"))
    for p in results:
        _print_row(p)
    print(dim(f"Tip: promptctl show <id>  to print the full prompt text."))
    return 0


def cmd_list(args: argparse.Namespace, client: PromptClient) -> int:
    items = client.prompts(category=args.category, refresh=args.refresh)
    if args.difficulty:
        items = [p for p in items if p.get("difficulty", "").lower() == args.difficulty.lower()]
    if args.limit:
        items = items[: args.limit]
    if args.json:
        print(json.dumps(items, indent=2))
        return 0
    for p in items:
        print(f"{bold(p.get('id',''))}  {accent(p.get('category',''))}  {p.get('title','')}")
    print(dim(f"\n{len(items)} prompt(s)."))
    return 0


def cmd_show(args: argparse.Namespace, client: PromptClient) -> int:
    p = client.get(args.id, refresh=args.refresh)
    if not p:
        err(f"prompt not found: {args.id}")
        return 1
    if args.json:
        print(json.dumps(p, indent=2))
        return 0
    if args.raw:
        print(p.get("prompt", ""))
        return 0
    print(bold(p.get("title", "")))
    print(
        dim(
            " · ".join(
                x
                for x in [
                    p.get("id", ""),
                    p.get("category", ""),
                    p.get("difficulty", ""),
                    ", ".join(p.get("tools", [])),
                ]
                if x
            )
        )
    )
    if p.get("useCase"):
        print("\n" + p["useCase"])
    print("\n" + bold("Prompt:"))
    print(p.get("prompt", ""))
    notes = p.get("safetyNotes") or []
    if notes:
        print("\n" + bold("Safety notes:"))
        for n in notes:
            print(f"  - {n}")
    if p.get("url"):
        print(dim("\n" + p["url"]))
    if args.copy:
        ok = _copy_to_clipboard(p.get("prompt", ""))
        print(dim("\n[copied prompt to clipboard]" if ok else "\n[clipboard tool not found]"))
    return 0


def cmd_categories(args: argparse.Namespace, client: PromptClient) -> int:
    cats = client.categories(refresh=args.refresh)
    if args.json:
        print(json.dumps(cats, indent=2))
        return 0
    width = max((len(c["slug"]) for c in cats), default=10)
    for c in sorted(cats, key=lambda c: c.get("prompts", 0), reverse=True):
        print(f"  {bold(c['slug'].ljust(width))}  {str(c.get('prompts',0)).rjust(4)} prompts  {dim(c.get('name',''))}")
    return 0


def cmd_meta(args: argparse.Namespace, client: PromptClient) -> int:
    m = client.meta(refresh=args.refresh)
    if args.json:
        print(json.dumps(m, indent=2))
        return 0
    print(bold(f"{m.get('name','DevOps AI ToolKit API')}  ({m.get('version','')})"))
    counts = m.get("counts", {})
    print(f"  prompts: {counts.get('prompts','?')}   guides: {counts.get('guides','?')}   error guides: {counts.get('errorGuides','?')}")
    print(dim(f"  base: {m.get('base','')}"))
    print(dim(f"  generated: {m.get('generatedAt','')}"))
    return 0


# ---- parser ------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="promptctl",
        description="Query the DevOps AI ToolKit prompt library from the command line.",
        epilog="Examples:\n"
        "  promptctl search kubernetes crashloop --difficulty Advanced\n"
        "  promptctl list --category terraform\n"
        "  promptctl show terraform-plan-review --copy\n"
        "  promptctl categories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--version", action="version", version=f"promptctl {__version__}")
    p.add_argument("--base-url", default=DEFAULT_BASE_URL, help="API base URL")
    p.add_argument("--refresh", action="store_true", help="bypass the local cache")
    p.add_argument("--no-cache", action="store_true", help="do not read or write the cache")
    sub = p.add_subparsers(dest="command", metavar="<command>")

    s = sub.add_parser("search", help="search prompts by keyword + filters")
    s.add_argument("query", nargs="*", help="search words (all must match)")
    s.add_argument("--category", "-c", help="filter by category slug")
    s.add_argument("--difficulty", "-d", help="Beginner | Intermediate | Advanced")
    s.add_argument("--tool", help="filter by AI tool (e.g. Claude)")
    s.add_argument("--tag", help="filter by tag")
    s.add_argument("--limit", "-n", type=int, help="max results")
    s.add_argument("--json", action="store_true", help="output raw JSON")
    s.set_defaults(func=cmd_search)

    ls = sub.add_parser("list", help="list prompts (metadata)")
    ls.add_argument("--category", "-c", help="filter by category slug")
    ls.add_argument("--difficulty", "-d", help="filter by difficulty")
    ls.add_argument("--limit", "-n", type=int, help="max results")
    ls.add_argument("--json", action="store_true", help="output raw JSON")
    ls.set_defaults(func=cmd_list)

    sh = sub.add_parser("show", help="print a prompt's full text by id")
    sh.add_argument("id", help="prompt id (slug)")
    sh.add_argument("--copy", action="store_true", help="copy the prompt text to the clipboard")
    sh.add_argument("--raw", action="store_true", help="print only the prompt text")
    sh.add_argument("--json", action="store_true", help="output raw JSON")
    sh.set_defaults(func=cmd_show)

    ca = sub.add_parser("categories", help="list categories with prompt counts")
    ca.add_argument("--json", action="store_true", help="output raw JSON")
    ca.set_defaults(func=cmd_categories)

    mt = sub.add_parser("meta", help="show API metadata")
    mt.add_argument("--json", action="store_true", help="output raw JSON")
    mt.set_defaults(func=cmd_meta)

    return p


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    client = PromptClient(base_url=args.base_url, cache=not args.no_cache)
    try:
        return args.func(args, client)
    except APIError as exc:
        err(str(exc))
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
