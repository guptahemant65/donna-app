"""PR Intelligence — Azure DevOps pull request monitoring.

Uses ADO REST API to show PRs across multiple orgs/projects/repos:
  - Open PRs authored by Harvey
  - PRs awaiting Harvey's review
  - PR detail with diff stats, reviewers, vote status

ConversationHandler flow:
  /pr → PR_LIST (my PRs + review requests)
    ↕ tap PR → PR_DETAIL (changes, reviewers, CI)
    ↕ "close" → END
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from dataclasses import dataclass
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

TIMEOUT = 15.0
API_VERSION = "7.0"


# ── ADO Repo Config ────────────────────────────────────────────────────

@dataclass(frozen=True)
class AdoRepo:
    """A single ADO repository to monitor."""

    org: str
    project: str
    repo: str

    @property
    def base_url(self) -> str:
        return f"https://dev.azure.com/{self.org}"

    @property
    def label(self) -> str:
        return f"{self.org}/{self.project}/{self.repo}"


def parse_ado_repos(repos_json: str) -> list[AdoRepo]:
    """Parse ADO_REPOS env var — JSON array or semicolon-separated triples.

    Formats:
      JSON: [{"org":"powerbi","project":"MWC","repo":"workload-fabriclivetable"}]
      Simple: powerbi/MWC/workload-fabriclivetable;msdata/HDInsight/repo2
    """
    if not repos_json:
        return []

    repos_json = repos_json.strip()

    if repos_json.startswith("["):
        items = json.loads(repos_json)
        return [AdoRepo(org=r["org"], project=r["project"], repo=r["repo"]) for r in items]

    result = []
    for triple in repos_json.split(";"):
        triple = triple.strip()
        if not triple:
            continue
        parts = triple.split("/", 2)
        if len(parts) == 3:
            result.append(AdoRepo(org=parts[0], project=parts[1], repo=parts[2]))
        else:
            logger.warning("Invalid ADO repo spec: %s (expected org/project/repo)", triple)
    return result


# ── ADO REST API ────────────────────────────────────────────────────────

def _auth_header(pat: str) -> str:
    """Build Basic auth header from ADO PAT."""
    encoded = base64.b64encode(f":{pat}".encode()).decode()
    return f"Basic {encoded}"


async def _ado_get(
    url: str,
    pat: str,
    params: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Make an authenticated ADO REST API request."""
    if params is None:
        params = {}
    params["api-version"] = API_VERSION

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            url,
            headers={"Authorization": _auth_header(pat)},
            params=params,
        )
        resp.raise_for_status()
        return resp.json()


async def get_my_prs(
    pat: str,
    repos: list[AdoRepo],
    email: str,
) -> list[dict[str, Any]]:
    """Get open PRs authored by the user across all configured repos."""
    tasks = [_fetch_prs(pat, repo, creator=email) for repo in repos]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_prs = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.warning("Failed to fetch PRs from %s: %s", repos[i].label, result)
            continue
        all_prs.extend(result)

    # Sort by most recently updated
    all_prs.sort(key=lambda p: p.get("updated", ""), reverse=True)
    return all_prs[:10]


async def get_review_requests(
    pat: str,
    repos: list[AdoRepo],
    email: str,
) -> list[dict[str, Any]]:
    """Get PRs where the user is a reviewer across all repos."""
    tasks = [_fetch_prs(pat, repo, reviewer=email) for repo in repos]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_prs = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.warning("Failed to fetch review PRs from %s: %s", repos[i].label, result)
            continue
        all_prs.extend(result)

    all_prs.sort(key=lambda p: p.get("updated", ""), reverse=True)
    return all_prs[:10]


async def _fetch_prs(
    pat: str,
    repo: AdoRepo,
    creator: str = "",
    reviewer: str = "",
) -> list[dict[str, Any]]:
    """Fetch PRs from a single ADO repo."""
    url = f"{repo.base_url}/{repo.project}/_apis/git/repositories/{repo.repo}/pullrequests"

    params: dict[str, str] = {
        "searchCriteria.status": "active",
        "$top": "10",
    }
    if creator:
        params["searchCriteria.creatorRefName"] = creator
    if reviewer:
        params["searchCriteria.reviewerRefName"] = reviewer

    data = await _ado_get(url, pat, params)
    return [_parse_pr(item, repo) for item in data.get("value", [])]


async def get_pr_detail(
    pat: str,
    repo: AdoRepo,
    pr_id: int,
) -> dict[str, Any]:
    """Get detailed PR info from ADO."""
    url = f"{repo.base_url}/{repo.project}/_apis/git/repositories/{repo.repo}/pullrequests/{pr_id}"
    data = await _ado_get(url, pat)
    return _parse_pr_detail(data, repo)


def _parse_pr(item: dict[str, Any], repo: AdoRepo) -> dict[str, Any]:
    """Parse an ADO PR into a clean dict."""
    reviewers = []
    for r in item.get("reviewers", []):
        vote = r.get("vote", 0)
        vote_icon = _vote_icon(vote)
        reviewers.append({
            "name": r.get("displayName", "?"),
            "vote": vote,
            "icon": vote_icon,
        })

    pr_url = (
        f"https://dev.azure.com/{repo.org}/{repo.project}"
        f"/_git/{repo.repo}/pullrequest/{item.get('pullRequestId', 0)}"
    )

    return {
        "id": item.get("pullRequestId", 0),
        "title": item.get("title", "?"),
        "repo": repo.repo,
        "repo_label": repo.label,
        "author": item.get("createdBy", {}).get("displayName", "?"),
        "author_email": item.get("createdBy", {}).get("uniqueName", ""),
        "url": pr_url,
        "created": item.get("creationDate", "")[:10],
        "updated": (item.get("closedDate") or item.get("creationDate", ""))[:10],
        "status": item.get("status", "active"),
        "isDraft": item.get("isDraft", False),
        "source": item.get("sourceRefName", "").replace("refs/heads/", ""),
        "target": item.get("targetRefName", "").replace("refs/heads/", ""),
        "reviewers": reviewers,
        "merge_status": item.get("mergeStatus", ""),
        "_repo": repo,
    }


def _parse_pr_detail(pr: dict[str, Any], repo: AdoRepo) -> dict[str, Any]:
    """Parse full PR detail from ADO."""
    base = _parse_pr(pr, repo)
    base["description"] = (pr.get("description", "") or "")[:300]
    base["merge_id"] = pr.get("lastMergeSourceCommit", {}).get("commitId", "")[:8]
    base["labels"] = [lbl.get("name", "") for lbl in pr.get("labels", [])]
    return base


def _vote_icon(vote: int) -> str:
    """Map ADO reviewer vote to icon."""
    if vote == 10:
        return "✅"   # Approved
    if vote == 5:
        return "👍"   # Approved with suggestions
    if vote == -5:
        return "⏳"   # Waiting for author
    if vote == -10:
        return "❌"   # Rejected
    return "⬜"       # No vote


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
            draft = " ✏️" if pr.get("isDraft") else ""
            title = md2(pr.get("title", "?")[:40])
            repo = md2(pr.get("repo", "?")[:20])
            votes = " ".join(r["icon"] for r in pr.get("reviewers", [])[:4])
            lines.append(f"  {md2_bold('!' + str(pr['id']))} {title}{draft}")
            lines.append(f"      {repo} {votes}")
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
            lines.append(f"  {md2_bold('!' + str(pr['id']))} {title}")
            lines.append(f"      by {author}")
            lines.append("")

    lines.append(md2_separator())
    return "\n".join(lines)


def _format_pr_detail(pr: dict[str, Any]) -> str:
    """Format PR detail card."""
    lines = [
        md2_header(),
        f"🔧 {md2_bold('PR !' + str(pr['id']))}",
        "",
        md2_bold(md2(pr.get("title", "?"))),
        "",
        f"  {md2_bold('Branch:')} {md2(pr.get('source', '?'))} → {md2(pr.get('target', '?'))}",
        f"  {md2_bold('Author:')} {md2(pr.get('author', '?'))}",
        f"  {md2_bold('Repo:')} {md2(pr.get('repo', '?'))}",
    ]

    if pr.get("isDraft"):
        lines.append(f"  {md2_bold('Status:')} ✏️ Draft")

    merge = pr.get("merge_status", "")
    if merge == "succeeded":
        lines.append(f"  {md2_bold('Merge:')} ✅ No conflicts")
    elif merge == "conflicts":
        lines.append(f"  {md2_bold('Merge:')} ❌ Conflicts")

    reviewers = pr.get("reviewers", [])
    if reviewers:
        rv_lines = [f"{r['icon']} {md2(r['name'])}" for r in reviewers[:6]]
        lines.append(f"  {md2_bold('Reviewers:')}")
        for rv in rv_lines:
            lines.append(f"    {rv}")

    labels = pr.get("labels", [])
    if labels:
        lines.append(f"  {md2_bold('Labels:')} {md2(', '.join(labels[:4]))}")

    desc = pr.get("description", "")
    if desc:
        lines.extend(["", md2(desc[:200])])

    lines.extend(["", md2_separator()])
    return "\n".join(lines)


def _pr_list_keyboard(
    my_prs: list[dict[str, Any]],
    review_prs: list[dict[str, Any]],
) -> InlineKeyboardMarkup:
    """Build keyboard for PR list."""
    buttons = []

    for pr in (my_prs + review_prs)[:8]:
        label = f"!{pr['id']} {pr.get('title', '?')[:20]}"
        # Encode repo index for callback routing
        repo_label = pr.get("repo_label", "")
        buttons.append([
            InlineKeyboardButton(
                label,
                callback_data=f"pr:detail:{repo_label}:{pr['id']}",
            ),
        ])

    buttons.append([
        InlineKeyboardButton("🔄 Refresh", callback_data="pr:refresh"),
        InlineKeyboardButton("✕ Close", callback_data="pr:close"),
    ])

    return InlineKeyboardMarkup(buttons)


def _pr_detail_keyboard(pr: dict[str, Any]) -> InlineKeyboardMarkup:
    """Build keyboard for PR detail."""
    buttons = [[InlineKeyboardButton("🔗 Open in ADO", url=pr.get("url", ""))]]
    buttons.append([
        InlineKeyboardButton("◀ Back", callback_data="pr:back"),
        InlineKeyboardButton("✕ Close", callback_data="pr:close"),
    ])
    return InlineKeyboardMarkup(buttons)


# ── Handlers ────────────────────────────────────────────────────────────

def _get_ado_config(context: ContextTypes.DEFAULT_TYPE) -> tuple[str, list[AdoRepo], str]:
    """Get ADO PAT, repos, and email from settings."""
    settings = context.bot_data.get("settings")
    pat = getattr(settings, "ado_pat", "") if settings else ""
    repos_json = getattr(settings, "ado_repos_json", "") if settings else ""
    email = getattr(settings, "ado_email", "") if settings else ""
    repos = parse_ado_repos(repos_json)
    return pat, repos, email


@harvey_only
async def pr_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /pr — show open PRs across ADO repos."""
    pat, repos, email = _get_ado_config(context)

    if not pat or not repos:
        await update.message.reply_text(
            f"{md2_header()}\n\n"
            f"{md2('Azure DevOps not configured.')}\n"
            f"{md2('Set ADO_PAT and ADO_REPOS in .env')}",
            parse_mode="MarkdownV2",
        )
        return ConversationHandler.END

    return await _show_pr_list(update, context, pat, repos, email)


async def _show_pr_list(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    pat: str,
    repos: list[AdoRepo],
    email: str,
    edit: bool = False,
) -> int:
    """Fetch and display PR list."""
    try:
        my_prs, review_prs = await asyncio.gather(
            get_my_prs(pat, repos, email),
            get_review_requests(pat, repos, email),
        )
    except Exception:
        logger.exception("ADO API failed")
        error = f"{md2_header()}\n\n{md2('Failed to fetch PRs from Azure DevOps.')}"
        if edit and update.callback_query:
            await update.callback_query.edit_message_text(error, parse_mode="MarkdownV2")
        else:
            await update.message.reply_text(error, parse_mode="MarkdownV2")
        return ConversationHandler.END

    # Remove duplicates (same PR in both lists)
    review_ids = {p["id"] for p in my_prs}
    review_prs = [p for p in review_prs if p["id"] not in review_ids]

    context.user_data["my_prs"] = my_prs
    context.user_data["review_prs"] = review_prs
    context.user_data["all_prs"] = {
        f"{p['repo_label']}:{p['id']}": p for p in my_prs + review_prs
    }

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
        pat, repos, email = _get_ado_config(context)
        return await _show_pr_list(update, context, pat, repos, email, edit=True)

    if data.startswith("pr:detail:"):
        # Format: pr:detail:org/project/repo:id
        rest = data[len("pr:detail:"):]
        parts = rest.rsplit(":", 1)
        if len(parts) == 2:
            repo_label = parts[0]
            pr_id = int(parts[1])
            return await _show_pr_detail(update, context, repo_label, pr_id)

    return State.PR_LIST


async def _show_pr_detail(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    repo_label: str,
    pr_id: int,
) -> int:
    """Show PR detail card."""
    pat, _, _ = _get_ado_config(context)

    # Try to find cached PR first
    all_prs = context.user_data.get("all_prs", {})
    key = f"{repo_label}:{pr_id}"
    cached = all_prs.get(key)

    if cached and "_repo" in cached:
        repo = cached["_repo"]
    else:
        # Parse repo_label back into AdoRepo
        parts = repo_label.split("/", 2)
        if len(parts) != 3:
            return State.PR_LIST
        repo = AdoRepo(org=parts[0], project=parts[1], repo=parts[2])

    try:
        pr = await get_pr_detail(pat, repo, pr_id)
    except Exception:
        logger.exception("Failed to fetch PR !%d from %s", pr_id, repo_label)
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
        pat, repos, email = _get_ado_config(context)
        return await _show_pr_list(update, context, pat, repos, email, edit=True)

    return State.PR_DETAIL


# ── ConversationHandler Factory ─────────────────────────────────────────

def build_pr_conversation() -> ConversationHandler:
    """Build the PR intelligence ConversationHandler."""
    return ConversationHandler(
        entry_points=[
            CommandHandler("pr", pr_command),
            CommandHandler("prs", pr_command),
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
