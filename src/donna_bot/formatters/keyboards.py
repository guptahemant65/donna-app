"""Inline keyboard builders — Donna's action buttons."""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def briefing_keyboard(email_count: int = 0, meeting_count: int = 0) -> InlineKeyboardMarkup:
    """Briefing card actions with counts."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"📬 Emails ({email_count})", callback_data="brief:emails"),
            InlineKeyboardButton(f"📅 Calendar ({meeting_count})", callback_data="brief:cal"),
        ],
        [
            InlineKeyboardButton("👥 People", callback_data="brief:people"),
            InlineKeyboardButton("🔄 Refresh", callback_data="brief:refresh"),
        ],
    ])


def email_list_keyboard(emails: list[dict]) -> InlineKeyboardMarkup:
    """Email list — one button per email."""
    buttons = []
    for i, em in enumerate(emails[:5]):
        sender = em.get("from", "?")[:15]
        buttons.append([
            InlineKeyboardButton(
                f"{i + 1}. {sender}", callback_data=f"email:read:{em.get('id', i)}"
            )
        ])
    buttons.append([
        InlineKeyboardButton("◀ Back", callback_data="email:back"),
        InlineKeyboardButton("More ▶", callback_data="email:more"),
    ])
    return InlineKeyboardMarkup(buttons)


def email_action_keyboard(email_id: str) -> InlineKeyboardMarkup:
    """Single email actions."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("↩ Reply", callback_data=f"email:reply:{email_id}"),
            InlineKeyboardButton("↪ Forward", callback_data=f"email:fwd:{email_id}"),
            InlineKeyboardButton("📥 Archive", callback_data=f"email:archive:{email_id}"),
        ],
        [InlineKeyboardButton("◀ Back to list", callback_data="email:back")],
    ])


def meeting_keyboard(meeting_id: str, join_url: str = "") -> InlineKeyboardMarkup:
    """Meeting detail actions."""
    row1 = [
        InlineKeyboardButton("📋 Prep", callback_data=f"meeting:prep:{meeting_id}"),
        InlineKeyboardButton("📝 Notes", callback_data=f"meeting:notes:{meeting_id}"),
    ]
    if join_url:
        row1.append(InlineKeyboardButton("🔗 Join", url=join_url))
    return InlineKeyboardMarkup([
        row1,
        [InlineKeyboardButton("◀ Back", callback_data="cal:back")],
    ])


def person_keyboard(email: str) -> InlineKeyboardMarkup:
    """Person card actions."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📧 Email", callback_data=f"person:email:{email}"),
            InlineKeyboardButton("💬 Teams", callback_data=f"person:teams:{email}"),
            InlineKeyboardButton("🏢 Org", callback_data=f"person:org:{email}"),
        ],
        [InlineKeyboardButton("◀ Back", callback_data="person:back")],
    ])


def confirm_keyboard(action: str) -> InlineKeyboardMarkup:
    """Confirmation dialog."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✓ Go", callback_data=f"confirm:yes:{action}"),
            InlineKeyboardButton("✕ Cancel", callback_data=f"confirm:no:{action}"),
        ],
    ])


def pagination_keyboard(prefix: str, page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Pagination controls."""
    buttons = []
    if page > 1:
        buttons.append(InlineKeyboardButton("◀ Prev", callback_data=f"{prefix}:page:{page - 1}"))
    buttons.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        buttons.append(InlineKeyboardButton("Next ▶", callback_data=f"{prefix}:page:{page + 1}"))
    return InlineKeyboardMarkup([buttons])
