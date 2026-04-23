"""Natural Language Fallback — intent detection + routing.

Handles messages that don't match any command.
Detects intent from text and routes to the appropriate handler.

Patterns:
  "check my emails" / "inbox" / "unread"  → /email
  "who is <name>" / "who owns <thing>"    → /who <name>
  "my calendar" / "meetings today"        → /cal
  "search for <query>"                    → /search <query>
  "morning briefing"                      → /brief
  Other → friendly "I didn't catch that" + suggestions
"""

from __future__ import annotations

import logging
import re

from telegram import Update
from telegram.ext import ContextTypes

from donna_bot.formatters.escape import md2, md2_bold, md2_header, md2_italic, md2_separator
from donna_bot.middleware.security import harvey_only

logger = logging.getLogger(__name__)


# ── Intent Patterns ─────────────────────────────────────────────────────

_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    # (compiled regex, route_command, extract_group_name_or_empty)

    # Email
    (re.compile(r"\b(emails?|inbox|unread|mail)\b", re.I), "/email", ""),
    (re.compile(r"\bcheck\s+(my\s+)?emails?\b", re.I), "/email", ""),

    # Calendar
    (re.compile(r"\b(calendar|cal|meetings?\s+today|my\s+day|schedule)\b", re.I), "/cal", ""),
    (re.compile(r"\bwhat('s| is)\s+(on\s+)?(my\s+)?(calendar|schedule)\b", re.I), "/cal", ""),

    # People
    (re.compile(r"\bwho\s+is\s+(.+)", re.I), "/who", "query"),
    (re.compile(r"\bwho\s+owns?\s+(.+)", re.I), "/who", "query"),
    (re.compile(r"\bfind\s+(person|people|someone)\s+(.+)", re.I), "/who", "query2"),
    (re.compile(r"\borg\s+chart\b", re.I), "/who", ""),

    # Search
    (re.compile(r"\bsearch\s+(?:for\s+)?(.+)", re.I), "/search", "query"),
    (re.compile(r"\bfind\s+(?:the\s+)?(.+?)(?:\s+(?:doc|document|file|email))?\s*$", re.I), "/search", "query"),
    (re.compile(r"\blook\s*(?:up|for)\s+(.+)", re.I), "/search", "query"),

    # Briefing
    (re.compile(r"\b(brief|briefing|morning|status|summary)\b", re.I), "/brief", ""),
    (re.compile(r"\bhow('s| is)\s+my\s+day\b", re.I), "/brief", ""),

    # Help
    (re.compile(r"\b(help|what can you do|commands?)\b", re.I), "/help", ""),
]


def detect_intent(text: str) -> tuple[str, str]:
    """Detect intent from natural language text.

    Returns (command, extracted_query) or ("", "") if no match.
    """
    text = text.strip()

    for pattern, command, group_name in _PATTERNS:
        match = pattern.search(text)
        if match:
            query = ""
            if group_name == "query" and match.lastindex and match.lastindex >= 1:
                query = match.group(1).strip()
            elif group_name == "query2" and match.lastindex and match.lastindex >= 2:
                query = match.group(2).strip()
            return command, query

    return "", ""


# ── Handler ─────────────────────────────────────────────────────────────

@harvey_only
async def fallback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle unmatched text messages — detect intent or suggest commands."""
    text = update.message.text or ""
    command, query = detect_intent(text)

    if command:
        # Route to detected command
        await _route_to_command(update, context, command, query)
    else:
        # Friendly fallback
        await _suggest_commands(update)


async def _route_to_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    command: str,
    query: str,
) -> None:
    """Route to the detected command handler."""
    logger.info("Intent: '%s' → %s %s", update.message.text[:30], command, query)

    # Build a route suggestion — we can't directly invoke ConversationHandlers
    # from fallback, so we tell Harvey the right command
    cmd_text = command
    if query:
        cmd_text = f"{command} {query}"

    lines = [
        md2_header(),
        "",
        md2_italic("I think you mean:"),
        "",
        f"  {md2_bold(md2(cmd_text))}",
        "",
        md2("Tap or type the command above."),
        "",
        md2_separator(),
    ]

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="MarkdownV2",
    )


async def _suggest_commands(update: Update) -> None:
    """Show helpful suggestions when no intent is detected."""
    lines = [
        md2_header(),
        "",
        md2("I didn't catch that. Here's what I can do:"),
        "",
        f"  📬 {md2('/brief')}  — Morning briefing",
        f"  📧 {md2('/mail')}   — Email inbox",
        f"  📅 {md2('/cal')}    — Calendar",
        f"  👥 {md2('/who')}    — People lookup",
        f"  🔍 {md2('/search')} — Search M365",
        "",
        md2_italic("Or just describe what you need — I'll figure it out."),
        "",
        md2_separator(),
    ]

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="MarkdownV2",
    )
