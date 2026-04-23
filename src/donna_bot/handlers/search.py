"""Search Intelligence — cross-tenant M365 search.

ConversationHandler flow:
  /search <query> → SEARCH_RESULTS (grouped by type)
    ↕ tap result → opens link or shows detail
    ↕ "refine" → prompts new query → SEARCH_RESULTS
    ↕ "close" → END
"""

from __future__ import annotations

import logging
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from donna_bot.formatters.escape import md2, md2_bold, md2_header, md2_italic, md2_separator
from donna_bot.graph.client import GraphClient
from donna_bot.graph.search import search_m365
from donna_bot.middleware.security import harvey_only
from donna_bot.state.machine import State

logger = logging.getLogger(__name__)


# ── Formatters ──────────────────────────────────────────────────────────

_TYPE_ICONS = {
    "emails": "📧",
    "files": "📁",
    "events": "📅",
    "chats": "💬",
    "lists": "📋",
    "other": "📎",
}


def _format_search_results(
    results: dict[str, list[dict[str, Any]]],
    query: str,
) -> str:
    """Format grouped search results."""
    lines = [
        md2_header(),
        f"🔍 {md2_bold('SEARCH')} — {md2_italic(md2(query))}",
        "",
    ]

    total = sum(len(hits) for hits in results.values())

    if total == 0:
        lines.append(md2("Nothing found. Try a different query."))
        lines.append(md2_separator())
        return "\n".join(lines)

    lines.append(md2_italic(f"{total} results across M365"))
    lines.append("")

    for type_key, hits in results.items():
        if not hits:
            continue

        icon = _TYPE_ICONS.get(type_key, "📎")
        lines.append(f"{icon} {md2_bold(type_key.upper())} {md2_italic('(' + str(len(hits)) + ')')}")
        lines.append("")

        for i, hit in enumerate(hits[:5], 1):
            if hit["type"] == "email":
                subject = md2(hit.get("subject", "?")[:40])
                sender = md2(hit.get("from", "?")[:20])
                lines.append(f"  {md2_bold(str(i) + '.')} {subject}")
                lines.append(f"      {md2_italic('from ' + sender)}")
            elif hit["type"] == "file":
                name = md2(hit.get("name", "?")[:40])
                author = md2(hit.get("createdBy", "")[:20])
                lines.append(f"  {md2_bold(str(i) + '.')} {name}")
                if author:
                    lines.append(f"      {md2_italic('by ' + author)}")
            elif hit["type"] == "event":
                subject = md2(hit.get("subject", "?")[:40])
                org = md2(hit.get("organizer", "")[:20])
                lines.append(f"  {md2_bold(str(i) + '.')} {subject}")
                if org:
                    lines.append(f"      {md2_italic('by ' + org)}")
            else:
                name = md2(hit.get("name", "?")[:40])
                lines.append(f"  {md2_bold(str(i) + '.')} {name}")

            # Summary snippet (if any)
            summary = hit.get("summary", "")
            if summary:
                clean = summary.replace("<c0>", "").replace("</c0>", "")[:80]
                lines.append(f"      {md2(clean)}")

            lines.append("")

        if len(hits) > 5:
            lines.append(f"  {md2_italic('... and ' + str(len(hits) - 5) + ' more')}")
            lines.append("")

    lines.append(md2_separator())
    return "\n".join(lines)


def _results_keyboard(
    results: dict[str, list[dict[str, Any]]],
) -> InlineKeyboardMarkup:
    """Build keyboard for search results."""
    buttons = []

    # Link buttons for top results with webLink/webUrl
    idx = 0
    for hits in results.values():
        for hit in hits[:3]:
            url = hit.get("webLink", "") or hit.get("webUrl", "")
            if url:
                label = hit.get("subject", hit.get("name", "Open"))[:25]
                buttons.append([InlineKeyboardButton(f"🔗 {label}", url=url)])
                idx += 1
            if idx >= 5:
                break
        if idx >= 5:
            break

    buttons.append([
        InlineKeyboardButton("🔄 New Search", callback_data="search:refine"),
        InlineKeyboardButton("✕ Close", callback_data="search:close"),
    ])

    return InlineKeyboardMarkup(buttons)


# ── Handlers ────────────────────────────────────────────────────────────

@harvey_only
async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /search <query>."""
    graph = _get_graph(context)
    if not graph:
        await update.message.reply_text(
            "Graph client not configured\\.",
            parse_mode="MarkdownV2",
        )
        return ConversationHandler.END

    query = " ".join(context.args) if context.args else ""
    if not query:
        await update.message.reply_text(
            f"{md2_header()}\n\n{md2('Usage: /search <query>')}\n"
            f"{md2('Example: /search FMV design doc')}\n"
            f"{md2('Searches emails, files, and calendar.')}",
            parse_mode="MarkdownV2",
        )
        return ConversationHandler.END

    return await _execute_search(update, context, query)


async def _execute_search(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    query: str,
    edit: bool = False,
) -> int:
    """Run the search and display results."""
    graph = _get_graph(context)

    try:
        results = await search_m365(graph, query)
    except Exception:
        logger.exception("M365 search failed for: %s", query)
        error = f"{md2_header()}\n\n{md2('Search failed. Try again.')}"
        if edit and update.callback_query:
            await update.callback_query.edit_message_text(error, parse_mode="MarkdownV2")
        else:
            await update.message.reply_text(error, parse_mode="MarkdownV2")
        return ConversationHandler.END

    context.user_data["search_results"] = results
    context.user_data["search_query"] = query

    text = _format_search_results(results, query)
    kb = _results_keyboard(results)

    if edit and update.callback_query:
        await update.callback_query.edit_message_text(
            text, parse_mode="MarkdownV2", reply_markup=kb,
        )
    else:
        await update.message.reply_text(
            text, parse_mode="MarkdownV2", reply_markup=kb,
        )

    return State.SEARCH_RESULTS


@harvey_only
async def results_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle search result callbacks."""
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    if data == "search:close":
        await query.edit_message_text(
            f"{md2_header()}\n\n{md2('Search closed.')}",
            parse_mode="MarkdownV2",
        )
        return ConversationHandler.END

    if data == "search:refine":
        await query.edit_message_text(
            f"{md2_header()}\n\n{md2('Type your new search query:')}",
            parse_mode="MarkdownV2",
        )
        return State.SEARCH_QUERY

    return State.SEARCH_RESULTS


@harvey_only
async def refine_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle refined search query text input."""
    query = update.message.text.strip()
    if not query:
        await update.message.reply_text(
            f"{md2_header()}\n\n{md2('Please enter a search query.')}",
            parse_mode="MarkdownV2",
        )
        return State.SEARCH_QUERY

    return await _execute_search(update, context, query)


def _get_graph(context: ContextTypes.DEFAULT_TYPE) -> GraphClient | None:
    return context.bot_data.get("graph")


# ── ConversationHandler Factory ─────────────────────────────────────────

def build_search_conversation() -> ConversationHandler:
    """Build the search ConversationHandler.

    Flow:
      /search <query> → SEARCH_RESULTS
        ↕ refine → SEARCH_QUERY → (text) → SEARCH_RESULTS
    """
    return ConversationHandler(
        entry_points=[
            CommandHandler("search", search_command),
            CommandHandler("find", search_command),  # alias
        ],
        states={
            State.SEARCH_RESULTS: [
                CallbackQueryHandler(results_callback, pattern=r"^search:"),
            ],
            State.SEARCH_QUERY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, refine_query),
            ],
        },
        fallbacks=[],
        name="search_flow",
        persistent=False,
        per_message=False,
    )
