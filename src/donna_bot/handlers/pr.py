"""PR Intelligence — GitHub pull request monitoring.

Uses GitHub REST API to show:
  - Open PRs authored by Harvey
  - PRs awaiting Harvey's review
  - PR detail with review status, CI checks

ConversationHandler flow:
  /pr → PR_LIST (my PRs + review requests)
    ↕ tap PR → PR_DETAIL (diff summary, reviews, CI)
    ↕ "close" → END
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
)

from donna_bot.formatters.escape import md2, md2_bold, md2_header, md2_italic, md2_separator
from donna_bot.middleware.security import harvey_only
from donna_bot.state.machine import State

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
TIMEOUT = 15.0


# ── GitHub API ──────────────────────────────────────────────────────────

async def _github_get(
    path: str,
    token: str,
    params: dict[str, str] | None = None,
) -> dict[str, Any] | list[dict[str, Any]]:
    """Make an authenticated GitHub API request."""
    async with httpx.AsyncClient(
        base_url=GITHUB_API,
        timeout=TIMEOUT,
    ) as client:
        resp = await client.get(
            path,
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            params=params,
        )
        resp.raise_for_status()
        return resp.json()


async def get_my_prs(
    token: str,
    username: str,
    org: str = "",
) -> list[dict[str, Any]]:
    """Get open PRs authored by the user."""
    query = f"is:pr is:open author:{username}"
    if org:
        query += f" org:{org}"

    data = await _github_get(
        "/search/issues",
        token=token,
        params={"q": query, "sort": "updated", "per_page": "10"},
    )
    return [_parse_pr(item) for item in data.get("items", [])]


async def get_review_requests(
    token: str,
    username: str,
    org: str = "",
) -> list[dict[str, Any]]:
    """Get PRs where the user is requested for review."""
    query = f"is:pr is:open review-requested:{username}"
    if org:
        query += f" org:{org}"

    data = await _github_get(
        "/search/issues",
        token=token,
        params={"q": query, "sort": "updated", "per_page": "10"},
    )
    return [_parse_pr(item) for item in data.get("items", [])]


async def get_pr_detail(
    token: str,
    owner: str,
    repo: str,
    number: int,
) -> dict[str, Any]:
    """Get PR details including reviews and checks."""
    pr = await _github_get(f"/repos/{owner}/{repo}/pulls/{number}", token=token)
    return _parse_pr_detail(pr)


def _parse_pr(item: dict[str, Any]) -> dict[str, Any]:
    """Parse a PR search result."""
    repo_url = item.get("repository_url", "")
    repo_name = "/".join(repo_url.split("/")[-2:]) if repo_url else ""

    labels = [lbl.get("name", "") for lbl in item.get("labels", [])]

    return {
        "number": item.get("number", 0),
        "title": item.get("title", "?"),
        "repo": repo_name,
        "author": item.get("user", {}).get("login", "?"),
        "url": item.get("html_url", ""),
        "created": item.get("created_at", "")[:10],
        "updated": item.get("updated_at", "")[:10],
        "comments": item.get("comments", 0),
        "labels": labels,
        "draft": item.get("draft", False),
    }


def _parse_pr_detail(pr: dict[str, Any]) -> dict[str, Any]:
    """Parse full PR detail."""
    return {
        "number": pr.get("number", 0),
        "title": pr.get("title", "?"),
        "body": (pr.get("body", "") or "")[:300],
        "author": pr.get("user", {}).get("login", "?"),
        "url": pr.get("html_url", ""),
        "state": pr.get("state", ""),
        "draft": pr.get("draft", False),
        "mergeable": pr.get("mergeable"),
        "additions": pr.get("additions", 0),
        "deletions": pr.get("deletions", 0),
        "changed_files": pr.get("changed_files", 0),
        "base": pr.get("base", {}).get("ref", "?"),
        "head": pr.get("head", {}).get("ref", "?"),
        "created": pr.get("created_at", "")[:10],
        "updated": pr.get("updated_at", "")[:10],
        "reviewers": [
            r.get("login", "?")
            for r in pr.get("requested_reviewers", [])
        ],
    }


# ── Formatters ──────────────────────────────────────────────────────────

def _format_pr_list(
    my_prs: list[dict[str, Any]],
    review_prs: list[dict[str, Any]],
) -> str:
    """Format PR overview card."""
    lines = [
        md2_header(),
        f"🔧 {md2_bold('PULL REQUESTS')}",
        "",
    ]

    if my_prs:
        lines.append(f"{md2_bold('YOUR PRs')} {md2_italic('(' + str(len(my_prs)) + ')')}")
        lines.append("")
        for pr in my_prs[:5]:
            draft = " ✏️" if pr.get("draft") else ""
            title = md2(pr.get("title", "?")[:40])
            repo = md2(pr.get("repo", "?").split("/")[-1][:15])
            lines.append(f"  {md2_bold('#' + str(pr['number']))} {title}{draft}")
            lines.append(f"      {repo} · {md2(pr.get('updated', ''))}")
            lines.append("")
    else:
        lines.append(md2_italic("No open PRs. Go write some code."))
        lines.append("")

    if review_prs:
        lines.append(f"{md2_bold('REVIEW REQUESTS')} {md2_italic('(' + str(len(review_prs)) + ')')}")
        lines.append("")
        for pr in review_prs[:5]:
            title = md2(pr.get("title", "?")[:40])
            author = md2(pr.get("author", "?"))
            lines.append(f"  {md2_bold('#' + str(pr['number']))} {title}")
            lines.append(f"      by {author} · {md2(pr.get('updated', ''))}")
            lines.append("")

    lines.append(md2_separator())
    return "\n".join(lines)


def _format_pr_detail(pr: dict[str, Any]) -> str:
    """Format PR detail card."""
    lines = [
        md2_header(),
        f"🔧 {md2_bold('PR #' + str(pr['number']))}",
        "",
        md2_bold(md2(pr.get("title", "?"))),
        "",
        f"  {md2_bold('Branch:')} {md2(pr.get('head', '?'))} → {md2(pr.get('base', '?'))}",
        f"  {md2_bold('Author:')} {md2(pr.get('author', '?'))}",
        f"  {md2_bold('Changes:')} {md2_italic('+' + str(pr.get('additions', 0)))} / "
        f"{md2_italic('-' + str(pr.get('deletions', 0)))} "
        f"in {md2(str(pr.get('changed_files', 0)))} files",
    ]

    if pr.get("draft"):
        lines.append(f"  {md2_bold('Status:')} ✏️ Draft")

    mergeable = pr.get("mergeable")
    if mergeable is True:
        lines.append(f"  {md2_bold('Merge:')} ✅ Ready")
    elif mergeable is False:
        lines.append(f"  {md2_bold('Merge:')} ❌ Conflicts")

    reviewers = pr.get("reviewers", [])
    if reviewers:
        lines.append(f"  {md2_bold('Reviewers:')} {md2(', '.join(reviewers[:4]))}")

    body = pr.get("body", "")
    if body:
        lines.extend(["", md2(body[:200])])

    lines.extend(["", md2_separator()])
    return "\n".join(lines)


def _pr_list_keyboard(
    my_prs: list[dict[str, Any]],
    review_prs: list[dict[str, Any]],
) -> InlineKeyboardMarkup:
    """Build keyboard for PR list."""
    buttons = []

    for pr in (my_prs + review_prs)[:8]:
        label = f"#{pr['number']} {pr.get('title', '?')[:20]}"
        repo = pr.get("repo", "")
        buttons.append([
            InlineKeyboardButton(
                label,
                callback_data=f"pr:detail:{repo}:{pr['number']}",
            ),
        ])

    buttons.append([
        InlineKeyboardButton("🔄 Refresh", callback_data="pr:refresh"),
        InlineKeyboardButton("✕ Close", callback_data="pr:close"),
    ])

    return InlineKeyboardMarkup(buttons)


def _pr_detail_keyboard(pr: dict[str, Any]) -> InlineKeyboardMarkup:
    """Build keyboard for PR detail."""
    buttons = [[InlineKeyboardButton("🔗 Open in GitHub", url=pr.get("url", ""))]]
    buttons.append([
        InlineKeyboardButton("◀ Back", callback_data="pr:back"),
        InlineKeyboardButton("✕ Close", callback_data="pr:close"),
    ])
    return InlineKeyboardMarkup(buttons)


# ── Handlers ────────────────────────────────────────────────────────────

def _get_github_config(context: ContextTypes.DEFAULT_TYPE) -> tuple[str, str, str]:
    """Get GitHub token, username, and org from settings."""
    settings = context.bot_data.get("settings")
    token = getattr(settings, "github_token", "") if settings else ""
    username = getattr(settings, "github_username", "") if settings else ""
    org = getattr(settings, "github_org", "") if settings else ""
    return token, username, org


@harvey_only
async def pr_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /pr — show open PRs."""
    token, username, org = _get_github_config(context)

    if not token or not username:
        await update.message.reply_text(
            f"{md2_header()}\n\n"
            f"{md2('GitHub not configured.')}\n"
            f"{md2('Set GITHUB_TOKEN and GITHUB_USERNAME in .env')}",
            parse_mode="MarkdownV2",
        )
        return ConversationHandler.END

    return await _show_pr_list(update, context, token, username, org)


async def _show_pr_list(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    token: str,
    username: str,
    org: str,
    edit: bool = False,
) -> int:
    """Fetch and display PR list."""
    try:
        my_prs = await get_my_prs(token, username, org)
        review_prs = await get_review_requests(token, username, org)
    except Exception:
        logger.exception("GitHub API failed")
        error = f"{md2_header()}\n\n{md2('Failed to fetch PRs from GitHub.')}"
        if edit and update.callback_query:
            await update.callback_query.edit_message_text(error, parse_mode="MarkdownV2")
        else:
            await update.message.reply_text(error, parse_mode="MarkdownV2")
        return ConversationHandler.END

    context.user_data["my_prs"] = my_prs
    context.user_data["review_prs"] = review_prs

    text = _format_pr_list(my_prs, review_prs)
    kb = _pr_list_keyboard(my_prs, review_prs)

    if edit and update.callback_query:
        await update.callback_query.edit_message_text(
            text, parse_mode="MarkdownV2", reply_markup=kb,
        )
    else:
        await update.message.reply_text(
            text, parse_mode="MarkdownV2", reply_markup=kb,
        )

    return State.PR_LIST


@harvey_only
async def pr_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle PR list callbacks."""
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    if data == "pr:close":
        await query.edit_message_text(
            f"{md2_header()}\n\n{md2('PR view closed.')}",
            parse_mode="MarkdownV2",
        )
        return ConversationHandler.END

    if data == "pr:refresh":
        token, username, org = _get_github_config(context)
        return await _show_pr_list(update, context, token, username, org, edit=True)

    if data.startswith("pr:detail:"):
        # Format: pr:detail:owner/repo:number
        parts = data.replace("pr:detail:", "").rsplit(":", 1)
        if len(parts) == 2:
            repo_full = parts[0]
            number = int(parts[1])
            return await _show_pr_detail(update, context, repo_full, number)

    return State.PR_LIST


async def _show_pr_detail(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    repo_full: str,
    number: int,
) -> int:
    """Show PR detail card."""
    token, _, _ = _get_github_config(context)

    parts = repo_full.split("/")
    if len(parts) != 2:
        return State.PR_LIST

    owner, repo = parts

    try:
        pr = await get_pr_detail(token, owner, repo, number)
    except Exception:
        logger.exception("Failed to fetch PR #%d from %s", number, repo_full)
        await update.callback_query.edit_message_text(
            f"{md2_header()}\n\n{md2('Failed to load PR details.')}",
            parse_mode="MarkdownV2",
        )
        return State.PR_LIST

    context.user_data["current_pr"] = pr

    text = _format_pr_detail(pr)
    kb = _pr_detail_keyboard(pr)

    await update.callback_query.edit_message_text(
        text, parse_mode="MarkdownV2", reply_markup=kb,
    )

    return State.PR_DETAIL


@harvey_only
async def pr_detail_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle PR detail callbacks."""
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    if data == "pr:close":
        await query.edit_message_text(
            f"{md2_header()}\n\n{md2('PR view closed.')}",
            parse_mode="MarkdownV2",
        )
        return ConversationHandler.END

    if data == "pr:back":
        token, username, org = _get_github_config(context)
        return await _show_pr_list(update, context, token, username, org, edit=True)

    return State.PR_DETAIL


# ── ConversationHandler Factory ─────────────────────────────────────────

def build_pr_conversation() -> ConversationHandler:
    """Build the PR intelligence ConversationHandler."""
    return ConversationHandler(
        entry_points=[
            CommandHandler("pr", pr_command),
            CommandHandler("prs", pr_command),  # alias
        ],
        states={
            State.PR_LIST: [
                CallbackQueryHandler(pr_list_callback, pattern=r"^pr:"),
            ],
            State.PR_DETAIL: [
                CallbackQueryHandler(pr_detail_callback, pattern=r"^pr:"),
            ],
        },
        fallbacks=[],
        name="pr_flow",
        persistent=False,
        per_message=False,
    )
