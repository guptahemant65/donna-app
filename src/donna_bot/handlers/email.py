"""Email Intelligence — list, read, compose, reply, archive.

Full ConversationHandler flow:
  /email → EMAIL_LIST ↔ EMAIL_READ ↔ EMAIL_COMPOSE → IDLE

State transitions:
  IDLE → /email → EMAIL_LIST
  EMAIL_LIST → tap email → EMAIL_READ
  EMAIL_LIST → "more" → EMAIL_LIST (next page)
  EMAIL_LIST → "back" → ConversationHandler.END
  EMAIL_READ → "reply" → EMAIL_COMPOSE
  EMAIL_READ → "archive" → EMAIL_LIST (refreshed)
  EMAIL_READ → "back" → EMAIL_LIST
  EMAIL_COMPOSE → text input → confirm
  EMAIL_COMPOSE → confirm yes → send + EMAIL_READ
  EMAIL_COMPOSE → confirm no → EMAIL_READ
  EMAIL_COMPOSE → /cancel → EMAIL_READ
"""

from __future__ import annotations

import logging
from typing import Any

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from donna_bot.formatters.cards import format_email_card
from donna_bot.formatters.escape import md2, md2_bold, md2_header, md2_italic, md2_separator
from donna_bot.formatters.keyboards import (
    confirm_keyboard,
    email_action_keyboard,
)
from donna_bot.graph.client import GraphClient
from donna_bot.graph.mail import archive, get_email, get_inbox, get_unread, mark_read, reply
from donna_bot.middleware.security import harvey_only
from donna_bot.state.machine import State

logger = logging.getLogger(__name__)

_PAGE_SIZE = 5


# ── Helpers ─────────────────────────────────────────────────────────────

def _get_graph(context: ContextTypes.DEFAULT_TYPE) -> GraphClient | None:
    """Extract Graph client from bot_data."""
    return context.bot_data.get("graph")


def _format_email_list_text(
    emails: list[dict[str, Any]],
    page: int,
    total: int,
    unread_count: int | None = None,
) -> str:
    """Format the email list card."""
    lines = [
        md2_header(),
        f"📬 {md2_bold('INBOX')}",
    ]

    if unread_count is not None:
        lines.append(md2_italic(f"{unread_count} unread · page {page}"))
    else:
        lines.append(md2_italic(f"page {page}"))

    lines.append("")

    if not emails:
        lines.append(md2("Nothing here. Inbox zero achieved."))
    else:
        for i, em in enumerate(emails, 1):
            read_marker = "  " if em.get("isRead", True) else "● "
            importance = "!" if em.get("importance") == "high" else " "
            sender = md2(em.get("from", "?")[:20])
            subject = md2(em.get("subject", "(no subject)")[:35])
            date = md2(em.get("date", ""))
            lines.append(
                f"{md2(read_marker)}{md2(importance)}{md2_bold(sender)}"
            )
            lines.append(f"   {subject}")
            lines.append(f"   {md2_italic(date)}")
            lines.append("")

    lines.append(md2_separator())
    return "\n".join(lines)


def _enriched_email_list_keyboard(
    emails: list[dict[str, Any]],
    page: int,
    total: int,
) -> Any:
    """Build keyboard with email buttons + pagination."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    buttons = []
    for i, em in enumerate(emails):
        read_dot = "" if em.get("isRead", True) else "● "
        sender = em.get("from", "?")[:18]
        subj = em.get("subject", "")[:15]
        label = f"{read_dot}{sender} — {subj}"
        buttons.append([
            InlineKeyboardButton(label, callback_data=f"email:read:{em.get('id', '')}")
        ])

    # Pagination row
    nav_row = []
    total_pages = max(1, (total + _PAGE_SIZE - 1) // _PAGE_SIZE)
    if page > 1:
        nav_row.append(InlineKeyboardButton("◀ Prev", callback_data=f"email:page:{page - 1}"))
    nav_row.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("Next ▶", callback_data=f"email:page:{page + 1}"))
    buttons.append(nav_row)

    # Close button
    buttons.append([InlineKeyboardButton("✕ Close", callback_data="email:close")])

    return InlineKeyboardMarkup(buttons)


# ── Handlers ────────────────────────────────────────────────────────────

@harvey_only
async def email_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /email — show unread inbox."""
    graph = _get_graph(context)
    if not graph:
        await update.message.reply_text(
            "Graph client not configured\\. Can't access inbox\\.",
            parse_mode="MarkdownV2",
        )
        return ConversationHandler.END

    context.user_data["email_page"] = 1
    return await _show_email_list(update, context, page=1, edit=False)


async def _show_email_list(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    page: int = 1,
    edit: bool = True,
) -> int:
    """Fetch and display email list for a given page."""
    graph = _get_graph(context)
    skip = (page - 1) * _PAGE_SIZE

    try:
        result = await get_inbox(graph, top=_PAGE_SIZE, skip=skip)
        emails = result["emails"]
        total = result["total"]
    except Exception:
        logger.exception("Failed to fetch inbox")
        error_text = f"{md2_header()}\n\n{md2('Failed to load inbox. Try again.')}"
        if edit and update.callback_query:
            await update.callback_query.edit_message_text(
                error_text, parse_mode="MarkdownV2",
            )
        else:
            await update.message.reply_text(error_text, parse_mode="MarkdownV2")
        return ConversationHandler.END

    # Get unread count for display
    try:
        unread = await get_unread(graph, top=1)
        # Total unread is approximate — use inbox count
        unread_count = sum(1 for e in emails if not e.get("isRead", True))
    except Exception:
        unread_count = None

    context.user_data["email_page"] = page
    context.user_data["email_total"] = total
    context.user_data["current_emails"] = emails

    text = _format_email_list_text(emails, page, total, unread_count)
    kb = _enriched_email_list_keyboard(emails, page, total)

    if edit and update.callback_query:
        await update.callback_query.edit_message_text(
            text, parse_mode="MarkdownV2", reply_markup=kb,
        )
    else:
        await update.message.reply_text(
            text, parse_mode="MarkdownV2", reply_markup=kb,
        )

    return State.EMAIL_LIST


@harvey_only
async def email_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle callbacks from email list: read, page, close."""
    query = update.callback_query
    await query.answer()

    data = query.data or ""

    # Pagination
    if data.startswith("email:page:"):
        page = int(data.split(":")[-1])
        return await _show_email_list(update, context, page=page, edit=True)

    # Read a specific email
    if data.startswith("email:read:"):
        email_id = data.replace("email:read:", "")
        return await _show_email_detail(update, context, email_id)

    # Close
    if data == "email:close":
        await query.edit_message_text(
            f"{md2_header()}\n\n{md2('Inbox closed.')}",
            parse_mode="MarkdownV2",
        )
        return ConversationHandler.END

    # Noop (page counter button)
    if data == "noop":
        return State.EMAIL_LIST

    return State.EMAIL_LIST


async def _show_email_detail(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    email_id: str,
) -> int:
    """Fetch and display a single email."""
    graph = _get_graph(context)
    query = update.callback_query

    try:
        email_data = await get_email(graph, email_id)

        # Mark as read
        try:
            await mark_read(graph, email_id)
        except Exception:
            logger.debug("Could not mark email as read")

    except Exception:
        logger.exception("Failed to fetch email %s", email_id[:8])
        await query.edit_message_text(
            f"{md2_header()}\n\n{md2('Failed to load email.')}",
            parse_mode="MarkdownV2",
        )
        return State.EMAIL_LIST

    context.user_data["current_email_id"] = email_id
    context.user_data["current_email"] = email_data

    to_str = ", ".join(email_data.get("to", []))[:50]
    card = format_email_card(
        sender=email_data.get("from", "?"),
        to=to_str,
        date=email_data.get("date", ""),
        subject=email_data.get("subject", "(no subject)"),
        body=email_data.get("body", ""),
        has_attachments=email_data.get("hasAttachments", False),
    )
    kb = email_action_keyboard(email_id)

    await query.edit_message_text(
        card, parse_mode="MarkdownV2", reply_markup=kb,
    )

    return State.EMAIL_READ


@harvey_only
async def email_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle email detail actions: reply, archive, back."""
    query = update.callback_query
    await query.answer()

    data = query.data or ""

    # Back to list
    if data == "email:back":
        page = context.user_data.get("email_page", 1)
        return await _show_email_list(update, context, page=page, edit=True)

    # Archive
    if data.startswith("email:archive:"):
        email_id = data.replace("email:archive:", "")
        return await _handle_archive(update, context, email_id)

    # Reply
    if data.startswith("email:reply:"):
        email_id = data.replace("email:reply:", "")
        return await _enter_compose(update, context, email_id)

    # Forward (stub for now)
    if data.startswith("email:fwd:"):
        await query.edit_message_text(
            f"{md2_header()}\n\n{md2('Forward is coming soon.')}",
            parse_mode="MarkdownV2",
        )
        return State.EMAIL_READ

    return State.EMAIL_READ


async def _handle_archive(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    email_id: str,
) -> int:
    """Archive an email and refresh the list."""
    graph = _get_graph(context)
    query = update.callback_query

    try:
        await archive(graph, email_id)
        await query.answer("Archived", show_alert=False)
    except Exception:
        logger.exception("Archive failed for %s", email_id[:8])
        await query.answer("Archive failed", show_alert=True)
        return State.EMAIL_READ

    # Refresh list
    page = context.user_data.get("email_page", 1)
    return await _show_email_list(update, context, page=page, edit=True)


async def _enter_compose(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    email_id: str,
) -> int:
    """Enter reply compose mode."""
    query = update.callback_query
    email_data = context.user_data.get("current_email", {})

    context.user_data["reply_to_id"] = email_id
    context.user_data["reply_to_subject"] = email_data.get("subject", "")
    context.user_data["reply_to_sender"] = email_data.get("from", "")

    subject = md2(email_data.get("subject", "(no subject)")[:40])
    sender = md2(email_data.get("from", "?"))

    lines = [
        md2_header(),
        f"↩ {md2_bold('REPLY')}",
        "",
        f"{md2_bold('To:')} {sender}",
        f"{md2_bold('Re:')} {subject}",
        "",
        md2("Type your reply below."),
        md2("Send /cancel to go back."),
        "",
        md2_separator(),
    ]

    await query.edit_message_text(
        "\n".join(lines), parse_mode="MarkdownV2",
    )

    return State.EMAIL_COMPOSE


@harvey_only
async def compose_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle free text input during compose — stage the reply."""
    text = update.message.text or ""
    if not text.strip():
        await update.message.reply_text(
            md2("Empty reply. Type something or /cancel."),
            parse_mode="MarkdownV2",
        )
        return State.EMAIL_COMPOSE

    context.user_data["reply_draft"] = text

    subject = md2(context.user_data.get("reply_to_subject", "")[:40])
    sender = md2(context.user_data.get("reply_to_sender", "?"))
    preview = md2(text[:200])

    lines = [
        md2_header(),
        f"↩ {md2_bold('CONFIRM REPLY')}",
        "",
        f"{md2_bold('To:')} {sender}",
        f"{md2_bold('Re:')} {subject}",
        "",
        md2_bold("Your reply:"),
        preview,
        "",
        md2("Send this reply?"),
        "",
        md2_separator(),
    ]

    kb = confirm_keyboard("reply")
    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="MarkdownV2",
        reply_markup=kb,
    )

    return State.EMAIL_COMPOSE


@harvey_only
async def compose_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle confirm/cancel for reply."""
    query = update.callback_query
    await query.answer()

    data = query.data or ""

    if data == "confirm:yes:reply":
        return await _send_reply(update, context)

    # Cancelled — go back to email detail
    email_id = context.user_data.get("reply_to_id", "")
    if email_id:
        return await _show_email_detail(update, context, email_id)

    # Fallback — go to list
    return await _show_email_list(update, context, page=1, edit=True)


async def _send_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Actually send the reply via Graph."""
    graph = _get_graph(context)
    query = update.callback_query

    email_id = context.user_data.get("reply_to_id", "")
    draft = context.user_data.get("reply_draft", "")

    if not email_id or not draft:
        await query.edit_message_text(
            f"{md2_header()}\n\n{md2('Missing reply data. Try again.')}",
            parse_mode="MarkdownV2",
        )
        return State.EMAIL_LIST

    try:
        await reply(graph, email_id, draft)

        lines = [
            md2_header(),
            "",
            f"✓ {md2_bold('Reply sent')}",
            "",
            f"{md2_bold('To:')} {md2(context.user_data.get('reply_to_sender', '?'))}",
            f"{md2_bold('Re:')} {md2(context.user_data.get('reply_to_subject', '')[:40])}",
            "",
            md2_separator(),
        ]

        await query.edit_message_text(
            "\n".join(lines), parse_mode="MarkdownV2",
        )

        logger.info("Reply sent to email %s", email_id[:8])

    except Exception:
        logger.exception("Failed to send reply to %s", email_id[:8])
        await query.edit_message_text(
            f"{md2_header()}\n\n{md2('Failed to send reply. Try again.')}",
            parse_mode="MarkdownV2",
        )

    # Clean up compose state
    context.user_data.pop("reply_draft", None)
    context.user_data.pop("reply_to_id", None)
    context.user_data.pop("reply_to_subject", None)
    context.user_data.pop("reply_to_sender", None)

    return ConversationHandler.END


@harvey_only
async def cancel_compose(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /cancel during compose — go back to email detail."""
    email_id = context.user_data.get("reply_to_id", "")

    # Clean up compose state
    context.user_data.pop("reply_draft", None)
    context.user_data.pop("reply_to_id", None)
    context.user_data.pop("reply_to_subject", None)
    context.user_data.pop("reply_to_sender", None)

    await update.message.reply_text(
        f"{md2_header()}\n\n{md2('Reply cancelled.')}",
        parse_mode="MarkdownV2",
    )

    return ConversationHandler.END


# ── ConversationHandler Factory ─────────────────────────────────────────

def build_email_conversation() -> ConversationHandler:
    """Build the full email ConversationHandler.

    Flow:
      /email → EMAIL_LIST
        ↕ email:read:<id> → EMAIL_READ
          ↕ email:reply:<id> → EMAIL_COMPOSE
              ↕ text → confirm → send
    """
    return ConversationHandler(
        entry_points=[
            CommandHandler("email", email_command),
            CommandHandler("mail", email_command),  # alias
        ],
        states={
            State.EMAIL_LIST: [
                CallbackQueryHandler(email_list_callback, pattern=r"^email:"),
                CallbackQueryHandler(email_list_callback, pattern=r"^noop$"),
            ],
            State.EMAIL_READ: [
                CallbackQueryHandler(email_action_callback, pattern=r"^email:"),
            ],
            State.EMAIL_COMPOSE: [
                CommandHandler("cancel", cancel_compose),
                CallbackQueryHandler(compose_confirm_callback, pattern=r"^confirm:"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, compose_text_handler),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_compose),
        ],
        name="email_flow",
        persistent=False,
        per_message=False,
    )
