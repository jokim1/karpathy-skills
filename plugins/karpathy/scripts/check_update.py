#!/usr/bin/env python3
"""Advisory update checker and updater for the Karpathy plugin.

Hook mode is non-mutating and non-fatal: at most once per day it compares the
installed plugin version with the GitHub version and emits a short reminder.
Manual mode powers `/karpathy update` and can either check status or run the
supported Codex plugin-manager refresh path.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


MARKETPLACE_NAME = "karpathy-skills"
PLUGIN_SELECTOR = "karpathy@karpathy-skills"
DEFAULT_CHECK_URL = (
    "https://raw.githubusercontent.com/jokim1/karpathy-skills/main/"
    "plugins/karpathy/.claude-plugin/plugin.json"
)
DEFAULT_INTERVAL_SECONDS = 24 * 60 * 60
DEFAULT_UPDATE_COMMAND_TIMEOUT_SECONDS = 120.0
SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)")


def main() -> int:
    args = sys.argv[1:]
    if "--help" in args or "-h" in args:
        print_usage()
        return 0
    if "--check" in args:
        return manual_check(json_output="--json" in args)
    if "--update" in args:
        return manual_update(json_output="--json" in args)

    try:
        run(output_mode=read_output_mode(args))
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

    status = collect_update_status(use_cache=True)
    if status is None or status.get("skipped"):
        return

    local_version = str(status["local_version"])
    latest_version = status.get("latest_version")
    if isinstance(latest_version, str) and is_newer(latest_version, local_version):
        print_update_notice(local_version, latest_version, output_mode=output_mode)


def manual_check(json_output: bool = False) -> int:
    status = collect_update_status(use_cache=False)
    if status is None:
        payload = {
            "status": "unknown",
            "message": "Could not determine the installed Karpathy plugin version.",
        }
        emit_manual_result(payload, json_output=json_output)
        return 1

    latest = status.get("latest_version")
    local = status.get("local_version")
    if not latest:
        status["status"] = "unknown"
        status["message"] = "Could not check for Karpathy plugin updates right now."
        status["instructions"] = update_instructions()
        emit_manual_result(status, json_output=json_output)
        return 1

    if status.get("update_available"):
        status["status"] = "update_available"
        status["message"] = f"Karpathy plugin update available: {local} -> {latest}."
        status["instructions"] = update_instructions()
    else:
        status["status"] = "up_to_date"
        status["message"] = f"Karpathy plugin is up to date ({local})."
    emit_manual_result(status, json_output=json_output)
    return 0


def manual_update(json_output: bool = False) -> int:
    status = collect_update_status(use_cache=False)
    if status is None:
        payload = {
            "status": "unknown",
            "action": "skipped",
            "message": "Could not determine the installed Karpathy plugin version.",
            "instructions": update_instructions(),
        }
        emit_manual_result(payload, json_output=json_output)
        return 1

    latest = status.get("latest_version")
    local = status.get("local_version")
    if not latest:
        status.update(
            {
                "status": "unknown",
                "action": "skipped",
                "message": "Could not check for Karpathy plugin updates right now.",
                "instructions": update_instructions(),
            }
        )
        emit_manual_result(status, json_output=json_output)
        return 1

    if not status.get("update_available"):
        status.update(
            {
                "status": "up_to_date",
                "action": "skipped",
                "message": f"Karpathy plugin is already up to date ({local}).",
            }
        )
        emit_manual_result(status, json_output=json_output)
        return 0

    status["status"] = "update_available"
    status["instructions"] = update_instructions()
    if not running_in_codex():
        status.update(
            {
                "action": "manual_required",
                "message": (
                    f"Karpathy plugin update available: {local} -> {latest}. "
                    "Claude Code plugin updates must run through Claude's plugin manager."
                ),
            }
        )
        emit_manual_result(status, json_output=json_output)
        return 0

    if env_truthy("KARPATHY_UPDATE_DRY_RUN"):
        status.update(
            {
                "action": "dry_run",
                "message": f"Karpathy plugin update available: {local} -> {latest}.",
                "commands": codex_update_commands(),
            }
        )
        emit_manual_result(status, json_output=json_output)
        return 0

    result = run_codex_update()
    status.update(result)
    if result["action"] == "updated":
        status["message"] = (
            f"Karpathy marketplace refreshed for Codex ({local} -> {latest}). "
            "Start a new Codex thread so refreshed skills and hooks are loaded."
        )
        clear_update_cache()
        emit_manual_result(status, json_output=json_output)
        return 0

    status["message"] = (
        f"Karpathy plugin update available: {local} -> {latest}, but the Codex "
        "plugin-manager update did not complete. Use the manual instructions below."
    )
    emit_manual_result(status, json_output=json_output)
    return 1


def collect_update_status(use_cache: bool) -> dict[str, Any] | None:
    root = plugin_root()
    local_version = read_local_version(root)
    if local_version is None:
        return None

    if use_cache:
        cache_file = update_cache_path()
        cache = read_cache(cache_file)
        now = time.time()
        interval = read_interval_seconds()
        if now - float(cache.get("last_checked_at", 0)) < interval:
            return {"skipped": True, "reason": "fresh cache"}

    latest_version = fetch_latest_version()
    if use_cache:
        write_cache(
            update_cache_path(),
            {
                "last_checked_at": time.time(),
                "latest_version": latest_version,
            },
        )

    return {
        "local_version": local_version,
        "latest_version": latest_version,
        "update_available": bool(latest_version and is_newer(latest_version, local_version)),
    }


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


def clear_update_cache() -> None:
    try:
        update_cache_path().unlink()
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


def read_update_command_timeout_seconds() -> float:
    raw = os.environ.get("KARPATHY_UPDATE_COMMAND_TIMEOUT_SECONDS")
    if raw is None:
        return DEFAULT_UPDATE_COMMAND_TIMEOUT_SECONDS
    try:
        timeout = float(raw)
    except ValueError:
        return DEFAULT_UPDATE_COMMAND_TIMEOUT_SECONDS
    return timeout if timeout > 0 else DEFAULT_UPDATE_COMMAND_TIMEOUT_SECONDS


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


def running_in_codex() -> bool:
    return bool(os.environ.get("CODEX_SHELL") or os.environ.get("CODEX_THREAD_ID") or os.environ.get("CODEX_CI"))


def codex_update_commands() -> list[str]:
    return [
        f"codex plugin marketplace upgrade {MARKETPLACE_NAME}",
        f"codex plugin add {PLUGIN_SELECTOR}",
    ]


def format_seconds(seconds: float) -> str:
    return f"{seconds:g}"


def timeout_output(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace").strip()
    return str(value).strip()


def run_codex_update() -> dict[str, Any]:
    codex = shutil.which("codex")
    if not codex:
        return {
            "action": "manual_required",
            "commands": [],
            "error": "codex CLI was not found on PATH.",
        }

    commands = [
        [codex, "plugin", "marketplace", "upgrade", MARKETPLACE_NAME],
        [codex, "plugin", "add", PLUGIN_SELECTOR],
    ]
    command_results = []
    timeout = read_update_command_timeout_seconds()
    for command in commands:
        command_label = " ".join(command)
        try:
            completed = subprocess.run(
                command,
                text=True,
                capture_output=True,
                check=False,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            command_results.append(
                {
                    "command": command_label,
                    "returncode": None,
                    "stdout": timeout_output(exc.stdout),
                    "stderr": timeout_output(exc.stderr),
                }
            )
            return {
                "action": "manual_required",
                "commands": command_results,
                "error": f"{command_label} timed out after {format_seconds(timeout)} seconds.",
            }
        command_results.append(
            {
                "command": command_label,
                "returncode": completed.returncode,
                "stdout": completed.stdout.strip(),
                "stderr": completed.stderr.strip(),
            }
        )
        if completed.returncode != 0:
            return {
                "action": "manual_required",
                "commands": command_results,
                "error": completed.stderr.strip() or completed.stdout.strip() or f"{command[0]} exited {completed.returncode}",
            }

    return {
        "action": "updated",
        "commands": command_results,
    }


def update_instructions() -> list[str]:
    return [
        "Run `/karpathy update`.",
        "If your client requires namespaced plugin commands, run `/karpathy:update`.",
        "Claude Code fallback: `/plugin marketplace update karpathy-skills`, then `/reload-plugins`.",
        "Codex fallback: `codex plugin marketplace upgrade karpathy-skills`, then `codex plugin add karpathy@karpathy-skills`, then start a new thread.",
    ]


def emit_manual_result(payload: dict[str, Any], json_output: bool = False) -> None:
    if json_output:
        json.dump(payload, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return

    message = payload.get("message")
    if message:
        sys.stdout.write(str(message).rstrip() + "\n")

    commands = payload.get("commands")
    if isinstance(commands, list) and commands:
        sys.stdout.write("\nCommands run:\n")
        for item in commands:
            if isinstance(item, dict):
                sys.stdout.write(f"  {item.get('command', '')} -> exit {item.get('returncode', '')}\n")
            else:
                sys.stdout.write(f"  {item}\n")

    error = payload.get("error")
    if error:
        sys.stdout.write(f"\nUpdate error: {error}\n")

    instructions = payload.get("instructions")
    if isinstance(instructions, list) and instructions:
        sys.stdout.write("\nUpdate instructions:\n")
        for item in instructions:
            sys.stdout.write(f"  - {item}\n")


def print_update_notice(local_version: str, latest_version: str, output_mode: str = "text") -> None:
    message = f"""Karpathy plugin update available: {local_version} -> {latest_version}

Run `/karpathy update` to install it.
If your client requires namespaced plugin commands, run `/karpathy:update`.

Set KARPATHY_DISABLE_UPDATE_CHECK=1 to disable this reminder.
"""
    if output_mode == "system-message":
        json.dump({"systemMessage": message.strip()}, sys.stdout)
        sys.stdout.write("\n")
        return

    sys.stdout.write(message)


def print_usage() -> None:
    sys.stdout.write(
        """karpathy update helper

Usage:
  check_update.py                 Hook mode: throttled advisory check
  check_update.py --system-message
  check_update.py --check [--json]
  check_update.py --update [--json]

Environment:
  KARPATHY_DISABLE_UPDATE_CHECK=1 disables hook reminders.
  KARPATHY_UPDATE_DRY_RUN=1 prints the Codex update commands without running them.
  KARPATHY_UPDATE_COMMAND_TIMEOUT_SECONDS overrides the Codex command timeout.
"""
    )


if __name__ == "__main__":
    raise SystemExit(main())
