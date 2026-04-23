"""People Intelligence — who, org chart, person detail.

ConversationHandler flow:
  /who <name> → PEOPLE_SEARCH (search results list)
    ↕ tap person → PEOPLE_DETAIL (person card with presence)
      ↕ "org" → ORG_CHART (manager chain + direct reports)
      ↕ "email" → compose email flow (stub for Phase 5)
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
)

from donna_bot.formatters.cards import format_person_card
from donna_bot.formatters.escape import md2, md2_bold, md2_header, md2_italic, md2_separator
from donna_bot.graph.client import GraphClient
from donna_bot.graph.people import (
    get_direct_reports,
    get_org_chain,
    get_user_presence,
    search_people,
)
from donna_bot.middleware.security import harvey_only
from donna_bot.state.machine import State

logger = logging.getLogger(__name__)


# ── Helpers ─────────────────────────────────────────────────────────────

def _get_graph(context: ContextTypes.DEFAULT_TYPE) -> GraphClient | None:
    return context.bot_data.get("graph")


_PRESENCE_ICONS = {
    "Available": "🟢",
    "Busy": "🔴",
    "DoNotDisturb": "⛔",
    "Away": "🟡",
    "BeRightBack": "🟡",
    "Offline": "⚫",
    "PresenceUnknown": "⚪",
}


def _presence_icon(availability: str) -> str:
    return _PRESENCE_ICONS.get(availability, "⚪")


def _format_search_results(people: list[dict[str, Any]], query: str) -> str:
    """Format people search results as a list card."""
    lines = [
        md2_header(),
        f"👥 {md2_bold('PEOPLE')} — {md2_italic(md2(query))}",
        "",
    ]

    if not people:
        lines.append(md2("Nobody found. Try a different name."))
    else:
        for i, p in enumerate(people[:10], 1):
            name = md2(p.get("name", "?"))
            title = md2(p.get("title", ""))
            dept = md2(p.get("department", ""))

            lines.append(f"  {md2_bold(str(i) + '.')} {name}")
            if title:
                lines.append(f"      {md2_italic(title)}")
            if dept:
                lines.append(f"      {md2(dept)}")
            lines.append("")

    lines.append(md2_separator())
    return "\n".join(lines)


def _format_person_detail(person: dict[str, Any], presence: dict[str, Any]) -> str:
    """Format a person detail card with presence."""
    availability = presence.get("availability", "PresenceUnknown")

    return format_person_card(
        name=person.get("name", "?"),
        title=person.get("title", ""),
        department=person.get("department", ""),
        email=person.get("email", ""),
        location=person.get("location", ""),
        availability=availability,
    )


def _format_org_chart(
    person: dict[str, Any],
    chain: list[dict[str, Any]],
    reports: list[dict[str, Any]],
) -> str:
    """Format org chart view: manager chain ↑ + direct reports ↓."""
    name = md2(person.get("name", "?"))
    lines = [
        md2_header(),
        f"🏢 {md2_bold('ORG CHART')} — {name}",
        "",
    ]

    # Manager chain (reverse so top is first)
    if chain:
        lines.append(f"  {md2_bold('REPORTS TO')}")
        for i, mgr in enumerate(reversed(chain)):
            indent = "    " * (i + 1)
            mgr_name = md2(mgr.get("name", "?"))
            mgr_title = md2(mgr.get("title", ""))
            lines.append(f"{indent}▸ {mgr_name}")
            if mgr_title:
                lines.append(f"{indent}  {md2_italic(mgr_title)}")
        lines.append("")

    # The person themselves
    lines.append(f"  {md2_bold('◆ ' + md2(person.get('name', '?')))}")
    title = person.get("title", "")
    if title:
        lines.append(f"    {md2_italic(md2(title))}")
    lines.append("")

    # Direct reports
    if reports:
        lines.append(f"  {md2_bold('DIRECT REPORTS')} {md2_italic('(' + str(len(reports)) + ')')}")
        for r in reports[:15]:
            r_name = md2(r.get("name", "?"))
            r_title = md2(r.get("title", ""))
            lines.append(f"    ▾ {r_name}")
            if r_title:
                lines.append(f"      {md2_italic(r_title)}")
    else:
        lines.append(f"  {md2_italic('No direct reports')}")

    lines.append("")
    lines.append(md2_separator())
    return "\n".join(lines)


def _search_keyboard(people: list[dict[str, Any]]) -> InlineKeyboardMarkup:
    """Build keyboard for search results."""
    buttons = []

    for i, p in enumerate(people[:10], 1):
        name = p.get("name", "Person")[:25]
        buttons.append([
            InlineKeyboardButton(
                f"{i}. {name}",
                callback_data=f"who:select:{i-1}",
            ),
        ])

    buttons.append([
        InlineKeyboardButton("✕ Close", callback_data="who:close"),
    ])

    return InlineKeyboardMarkup(buttons)


def _person_keyboard(person: dict[str, Any]) -> InlineKeyboardMarkup:
    """Build keyboard for person detail view."""
    person_id = person.get("id", "")

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🏢 Org Chart", callback_data=f"who:org:{person_id}"),
        ],
        [
            InlineKeyboardButton("◀ Back", callback_data="who:back"),
            InlineKeyboardButton("✕ Close", callback_data="who:close"),
        ],
    ])


def _org_keyboard(person_id: str) -> InlineKeyboardMarkup:
    """Org chart view keyboard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("◀ Back", callback_data=f"who:detail:{person_id}"),
            InlineKeyboardButton("✕ Close", callback_data="who:close"),
        ],
    ])


# ── Handlers ────────────────────────────────────────────────────────────

@harvey_only
async def who_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /who <name> — search for a person."""
    graph = _get_graph(context)
    if not graph:
        await update.message.reply_text(
            "Graph client not configured\\.",
            parse_mode="MarkdownV2",
        )
        return ConversationHandler.END

    # Extract query from command args
    query = " ".join(context.args) if context.args else ""
    if not query:
        await update.message.reply_text(
            f"{md2_header()}\n\n{md2('Usage: /who <name>')}\n{md2('Example: /who John Smith')}",
            parse_mode="MarkdownV2",
        )
        return ConversationHandler.END

    return await _do_search(update, context, query)


async def _do_search(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    query: str,
    edit: bool = False,
) -> int:
    """Execute people search and show results."""
    graph = _get_graph(context)

    try:
        people = await search_people(graph, query)
    except Exception:
        logger.exception("People search failed for %s", query)
        error = f"{md2_header()}\n\n{md2('Search failed. Try again.')}"
        if edit and update.callback_query:
            await update.callback_query.edit_message_text(error, parse_mode="MarkdownV2")
        else:
            await update.message.reply_text(error, parse_mode="MarkdownV2")
        return ConversationHandler.END

    context.user_data["people_results"] = people
    context.user_data["people_query"] = query

    text = _format_search_results(people, query)
    kb = _search_keyboard(people)

    if edit and update.callback_query:
        await update.callback_query.edit_message_text(
            text, parse_mode="MarkdownV2", reply_markup=kb,
        )
    else:
        await update.message.reply_text(
            text, parse_mode="MarkdownV2", reply_markup=kb,
        )

    return State.PEOPLE_SEARCH


@harvey_only
async def search_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle search result callbacks: select person, close."""
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    if data == "who:close":
        await query.edit_message_text(
            f"{md2_header()}\n\n{md2('People search closed.')}",
            parse_mode="MarkdownV2",
        )
        return ConversationHandler.END

    if data.startswith("who:select:"):
        index = int(data.replace("who:select:", ""))
        return await _show_person_detail(update, context, index)

    return State.PEOPLE_SEARCH


async def _show_person_detail(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    index: int,
) -> int:
    """Show detail card for selected person."""
    graph = _get_graph(context)
    people = context.user_data.get("people_results", [])

    if index >= len(people):
        await update.callback_query.edit_message_text(
            f"{md2_header()}\n\n{md2('Person not found.')}",
            parse_mode="MarkdownV2",
        )
        return State.PEOPLE_SEARCH

    person = people[index]
    context.user_data["current_person"] = person

    # Get presence
    person_id = person.get("id", "")
    presence = {"availability": "PresenceUnknown", "activity": "PresenceUnknown"}
    if person_id and graph:
        presence = await get_user_presence(graph, person_id)

    text = _format_person_detail(person, presence)
    kb = _person_keyboard(person)

    await update.callback_query.edit_message_text(
        text, parse_mode="MarkdownV2", reply_markup=kb,
    )

    return State.PEOPLE_DETAIL


@harvey_only
async def detail_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle person detail callbacks: org, back, close."""
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    if data == "who:close":
        await query.edit_message_text(
            f"{md2_header()}\n\n{md2('People view closed.')}",
            parse_mode="MarkdownV2",
        )
        return ConversationHandler.END

    if data == "who:back":
        # Re-show search results from cache
        people = context.user_data.get("people_results", [])
        q = context.user_data.get("people_query", "")
        text = _format_search_results(people, q)
        kb = _search_keyboard(people)
        await query.edit_message_text(
            text, parse_mode="MarkdownV2", reply_markup=kb,
        )
        return State.PEOPLE_SEARCH

    if data.startswith("who:org:"):
        person_id = data.replace("who:org:", "")
        return await _show_org_chart(update, context, person_id)

    if data.startswith("who:detail:"):
        person_id = data.replace("who:detail:", "")
        # Navigate to person detail by ID
        person = context.user_data.get("current_person", {})
        if person and person.get("id") == person_id:
            presence = {"availability": "PresenceUnknown"}
            graph = _get_graph(context)
            if graph:
                presence = await get_user_presence(graph, person_id)
            text = _format_person_detail(person, presence)
            kb = _person_keyboard(person)
            await query.edit_message_text(
                text, parse_mode="MarkdownV2", reply_markup=kb,
            )
            return State.PEOPLE_DETAIL

    return State.PEOPLE_DETAIL


async def _show_org_chart(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    person_id: str,
) -> int:
    """Show org chart for a person."""
    graph = _get_graph(context)
    person = context.user_data.get("current_person", {})

    if not graph or not person_id:
        await update.callback_query.edit_message_text(
            f"{md2_header()}\n\n{md2('Cannot load org chart.')}",
            parse_mode="MarkdownV2",
        )
        return State.PEOPLE_DETAIL

    try:
        chain = await get_org_chain(graph, person_id)
        reports = await get_direct_reports(graph, person_id)
    except Exception:
        logger.exception("Org chart failed for %s", person_id[:8])
        await update.callback_query.edit_message_text(
            f"{md2_header()}\n\n{md2('Failed to load org chart.')}",
            parse_mode="MarkdownV2",
        )
        return State.PEOPLE_DETAIL

    text = _format_org_chart(person, chain, reports)
    kb = _org_keyboard(person_id)

    await update.callback_query.edit_message_text(
        text, parse_mode="MarkdownV2", reply_markup=kb,
    )

    return State.ORG_CHART


@harvey_only
async def org_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle org chart callbacks: back to detail, close."""
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    if data == "who:close":
        await query.edit_message_text(
            f"{md2_header()}\n\n{md2('Org chart closed.')}",
            parse_mode="MarkdownV2",
        )
        return ConversationHandler.END

    if data.startswith("who:detail:"):
        person_id = data.replace("who:detail:", "")
        person = context.user_data.get("current_person", {})
        if person and person.get("id") == person_id:
            presence = {"availability": "PresenceUnknown"}
            graph = _get_graph(context)
            if graph:
                presence = await get_user_presence(graph, person_id)
            text = _format_person_detail(person, presence)
            kb = _person_keyboard(person)
            await query.edit_message_text(
                text, parse_mode="MarkdownV2", reply_markup=kb,
            )
            return State.PEOPLE_DETAIL

    return State.ORG_CHART


# ── ConversationHandler Factory ─────────────────────────────────────────

def build_people_conversation() -> ConversationHandler:
    """Build the people lookup ConversationHandler.

    Flow:
      /who <name> → PEOPLE_SEARCH
        ↕ select → PEOPLE_DETAIL
          ↕ org → ORG_CHART
    """
    return ConversationHandler(
        entry_points=[
            CommandHandler("who", who_command),
            CommandHandler("people", who_command),  # alias
        ],
        states={
            State.PEOPLE_SEARCH: [
                CallbackQueryHandler(search_callback, pattern=r"^who:"),
            ],
            State.PEOPLE_DETAIL: [
                CallbackQueryHandler(detail_callback, pattern=r"^who:"),
            ],
            State.ORG_CHART: [
                CallbackQueryHandler(org_callback, pattern=r"^who:"),
            ],
        },
        fallbacks=[],
        name="people_flow",
        persistent=False,
        per_message=False,
    )
