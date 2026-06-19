#!/usr/bin/env python3
"""Advisory update checker for the Karpathy plugin.

Runs safely from Claude Code or Codex plugin hooks. It never mutates files and
never fails the hook; at most once per day it compares the installed plugin
version with the GitHub version and emits update instructions when newer code is
available.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_CHECK_URL = (
    "https://raw.githubusercontent.com/jokim1/karpathy-skills/main/"
    "plugins/karpathy/.claude-plugin/plugin.json"
)
DEFAULT_INTERVAL_SECONDS = 24 * 60 * 60
SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)")


def main() -> int:
    try:
        run(output_mode=read_output_mode(sys.argv[1:]))
    except Exception:
        # Update checks should never break a user's coding session.
        return 0
    return 0


def read_output_mode(args: list[str]) -> str:
    if "--system-message" in args:
        return "system-message"
    return "text"


def run(output_mode: str = "text") -> None:
    if env_truthy("KARPATHY_DISABLE_UPDATE_CHECK"):
        return

    root = plugin_root()
    local_version = read_local_version(root)
    if local_version is None:
        return

    cache_file = update_cache_path()
    cache = read_cache(cache_file)
    now = time.time()
    interval = read_interval_seconds()
    if now - float(cache.get("last_checked_at", 0)) < interval:
        return

    latest_version = fetch_latest_version()
    write_cache(
        cache_file,
        {
            "last_checked_at": now,
            "latest_version": latest_version,
        },
    )

    if latest_version and is_newer(latest_version, local_version):
        print_update_notice(local_version, latest_version, output_mode=output_mode)


def env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def plugin_root() -> Path:
    env_root = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.environ.get("PLUGIN_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()
    return Path(__file__).resolve().parents[1]


def read_local_version(root: Path) -> str | None:
    for relative in (
        ".claude-plugin/plugin.json",
        ".codex-plugin/plugin.json",
    ):
        manifest = root / relative
        if not manifest.is_file():
            continue
        try:
            payload = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        version = payload.get("version")
        if isinstance(version, str) and version.strip():
            return version.strip()
    return None


def update_cache_path() -> Path:
    data_root = (
        os.environ.get("CLAUDE_PLUGIN_DATA")
        or os.environ.get("PLUGIN_DATA")
        or os.environ.get("KARPATHY_PLUGIN_DATA")
    )
    if data_root:
        path = Path(data_root).expanduser()
    else:
        cache_home = os.environ.get("XDG_CACHE_HOME")
        path = Path(cache_home).expanduser() if cache_home else Path.home() / ".cache"
        path = path / "karpathy-skills"
    path.mkdir(parents=True, exist_ok=True)
    return path / "update-check.json"


def read_cache(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def write_cache(path: Path, payload: dict[str, Any]) -> None:
    try:
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError:
        pass


def read_interval_seconds() -> int:
    raw = os.environ.get("KARPATHY_UPDATE_CHECK_INTERVAL_SECONDS")
    if raw is None:
        return DEFAULT_INTERVAL_SECONDS
    try:
        return max(0, int(raw))
    except ValueError:
        return DEFAULT_INTERVAL_SECONDS


def fetch_latest_version() -> str | None:
    url = os.environ.get("KARPATHY_UPDATE_CHECK_URL", DEFAULT_CHECK_URL)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "karpathy-skills-update-check"},
    )
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None
    version = payload.get("version") if isinstance(payload, dict) else None
    return version.strip() if isinstance(version, str) and version.strip() else None


def semver_key(version: str) -> tuple[int, int, int]:
    base = version.split("+", 1)[0].split("-", 1)[0]
    match = SEMVER_RE.match(base)
    if not match:
        return (0, 0, 0)
    return tuple(int(part) for part in match.groups())


def is_newer(latest: str, local: str) -> bool:
    return semver_key(latest) > semver_key(local)


def print_update_notice(local_version: str, latest_version: str, output_mode: str = "text") -> None:
    message = f"""Karpathy plugin update available: {local_version} -> {latest_version}

Claude Code:
  claude plugin marketplace update karpathy-skills
  /reload-plugins

Codex:
  codex plugin marketplace upgrade karpathy-skills
  restart Codex or start a new thread if needed

Set KARPATHY_DISABLE_UPDATE_CHECK=1 to disable this reminder.
"""
    if output_mode == "system-message":
        json.dump({"systemMessage": message.strip()}, sys.stdout)
        sys.stdout.write("\n")
        return

    sys.stdout.write(message)


if __name__ == "__main__":
    raise SystemExit(main())
