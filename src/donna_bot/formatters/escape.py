"""MarkdownV2 escaping — Telegram's most annoying format.

Telegram MarkdownV2 requires escaping these characters OUTSIDE of
code/pre blocks: _ * [ ] ( ) ~ ` > # + - = | { } . !

Inside code blocks, only ` and \\ need escaping.
Inside link URLs, only ) and \\ need escaping.
"""

from __future__ import annotations

import re

_SPECIAL = re.compile(r"([_*\[\]()~`>#+\-=|{}.!\\])")


def md2(text: str) -> str:
    """Escape text for MarkdownV2 — all special chars backslashed."""
    return _SPECIAL.sub(r"\\\1", text)


def md2_bold(text: str) -> str:
    """Bold text — *text* (text is auto-escaped)."""
    return f"*{md2(text)}*"


def md2_italic(text: str) -> str:
    """Italic text — _text_ (text is auto-escaped)."""
    return f"_{md2(text)}_"


def md2_code(text: str) -> str:
    """Inline code — `text` (special chars escaped inside)."""
    escaped = text.replace("\\", "\\\\").replace("`", "\\`")
    escaped = _SPECIAL.sub(r"\\\1", escaped)
    return f"`{escaped}`"


def md2_pre(text: str, language: str = "") -> str:
    """Code block — ```text``` (minimal escaping inside)."""
    inner = text.replace("\\", "\\\\").replace("`", "\\`")
    if language:
        return f"```{language}\n{inner}\n```"
    return f"```\n{inner}\n```"


def md2_link(label: str, url: str) -> str:
    """Markdown link — [label](url)."""
    escaped_label = md2(label)
    escaped_url = url.replace("\\", "\\\\").replace(")", "\\)")
    escaped_url = escaped_url.replace(".", "\\.")
    return f"[{escaped_label}]({escaped_url})"


def md2_separator() -> str:
    """Visual separator line."""
    return md2("━" * 30)


def md2_header() -> str:
    """Donna-style header: ◆ DONNA ━━━━━━━━━━━━━━━━"""
    return f"◆ {md2_bold('DONNA')} {md2('━' * 22)}"


def md2_section(emoji: str, title: str) -> str:
    """Section header: 📬 EMAILS"""
    return f"{emoji} {md2_bold(title)}"


def md2_progress_bar(current: int, total: int, width: int = 15) -> str:
    """Progress bar: ████████░░░░ 67%"""
    if total == 0:
        return md2("░" * width + " 0%")
    pct = min(current / total, 1.0)
    filled = int(width * pct)
    empty = width - filled
    bar = "█" * filled + "░" * empty
    return md2(f"{bar}  {current}/{total} ({int(pct * 100)}%)")
