"""Small dependency-free terminal formatting helpers."""

from __future__ import annotations

import os
import sys
from collections.abc import Iterable, Mapping
from typing import Any

RESET = "\033[0m"
COLORS = {
    "bold": "\033[1m",
    "dim": "\033[2m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
}


def supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("CLICOLOR_FORCE"):
        return True
    return sys.stdout.isatty()


def color(text: str, name: str) -> str:
    if not supports_color():
        return text
    return f"{COLORS.get(name, '')}{text}{RESET}"


def ok(message: str) -> None:
    print(f"{color('OK', 'green')} {message}")


def warn(message: str) -> None:
    print(f"{color('WARN', 'yellow')} {message}")


def err(message: str) -> None:
    print(f"{color('ERROR', 'red')} {message}", file=sys.stderr)


def info(message: str) -> None:
    print(f"{color('INFO', 'cyan')} {message}")


def print_kv_table(rows: Mapping[str, Any] | Iterable[tuple[str, Any]]) -> None:
    items = list(rows.items()) if isinstance(rows, Mapping) else list(rows)
    if not items:
        return
    width = max(len(str(key)) for key, _ in items)
    for key, value in items:
        print(f"{color(str(key).ljust(width), 'dim')}  {value}")


def section(message: str) -> None:
    print(color(message, "bold"))
