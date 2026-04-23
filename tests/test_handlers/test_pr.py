"""Tests for handlers/pr.py — PR Intelligence handler + GitHub API."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from donna_bot.handlers.pr import (
    _format_pr_detail,
    _format_pr_list,
    _parse_pr,
    _parse_pr_detail,
    _pr_detail_keyboard,
    _pr_list_keyboard,
    build_pr_conversation,
    get_my_prs,
    get_review_requests,
    pr_command,
    pr_detail_callback,
    pr_list_callback,
)
from donna_bot.state.machine import State


# ── Helpers ─────────────────────────────────────────────────────────────


def _make_update(text="", is_callback=False, callback_data=""):
    update = MagicMock()
    chat = MagicMock()
    chat.id = 496116833
    update.effective_chat = chat
    if is_callback:
        update.callback_query = MagicMock()
        update.callback_query.data = callback_data
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.message = None
    else:
        update.message = MagicMock()
        update.message.text = text
        update.message.reply_text = AsyncMock()
        update.message.from_user = MagicMock()
        update.message.from_user.id = 496116833
        update.callback_query = None
    return update


def _make_context(has_github=True):
    context = MagicMock()
    context.args = []
    context.user_data = {}
    context.bot_data = {}

    settings = MagicMock()
    settings.harvey_chat_id = 496116833
    if has_github:
        settings.github_token = "ghp_test123"
        settings.github_username = "harvey"
        settings.github_org = "microsoft"
    else:
        settings.github_token = ""
        settings.github_username = ""
        settings.github_org = ""
    context.bot_data["settings"] = settings
    return context


SAMPLE_PR_ITEM = {
    "number": 42,
    "title": "feat: add search module",
    "repository_url": "https://api.github.com/repos/microsoft/donna",
    "user": {"login": "harvey"},
    "html_url": "https://github.com/microsoft/donna/pull/42",
    "created_at": "2025-01-15T10:00:00Z",
    "updated_at": "2025-01-16T10:00:00Z",
    "comments": 3,
    "labels": [{"name": "enhancement"}],
    "draft": False,
}

SAMPLE_PR_DETAIL_RAW = {
    "number": 42,
    "title": "feat: add search module",
    "body": "This PR adds M365 search capability.",
    "user": {"login": "harvey"},
    "html_url": "https://github.com/microsoft/donna/pull/42",
    "state": "open",
    "draft": False,
    "mergeable": True,
    "additions": 250,
    "deletions": 10,
    "changed_files": 5,
    "base": {"ref": "main"},
    "head": {"ref": "feat/search"},
    "created_at": "2025-01-15T10:00:00Z",
    "updated_at": "2025-01-16T10:00:00Z",
    "requested_reviewers": [{"login": "alice"}, {"login": "bob"}],
}


# ── Unit Tests: Parsers ─────────────────────────────────────────────────


class TestParsePR:
    def test_parses_search_item(self):
        pr = _parse_pr(SAMPLE_PR_ITEM)
        assert pr["number"] == 42
        assert pr["title"] == "feat: add search module"
        assert pr["repo"] == "microsoft/donna"
        assert pr["author"] == "harvey"
        assert pr["created"] == "2025-01-15"
        assert pr["comments"] == 3
        assert "enhancement" in pr["labels"]
        assert pr["draft"] is False

    def test_handles_missing_fields(self):
        pr = _parse_pr({"number": 1})
        assert pr["number"] == 1
        assert pr["title"] == "?"
        assert pr["repo"] == ""
        assert pr["author"] == "?"


class TestParsePRDetail:
    def test_parses_full_detail(self):
        pr = _parse_pr_detail(SAMPLE_PR_DETAIL_RAW)
        assert pr["number"] == 42
        assert pr["additions"] == 250
        assert pr["deletions"] == 10
        assert pr["changed_files"] == 5
        assert pr["base"] == "main"
        assert pr["head"] == "feat/search"
        assert pr["mergeable"] is True
        assert "alice" in pr["reviewers"]
        assert "bob" in pr["reviewers"]

    def test_handles_missing(self):
        pr = _parse_pr_detail({})
        assert pr["number"] == 0
        assert pr["reviewers"] == []


# ── Unit Tests: Formatters ──────────────────────────────────────────────


class TestFormatPRList:
    def test_with_prs(self):
        my = [_parse_pr(SAMPLE_PR_ITEM)]
        review = [_parse_pr({**SAMPLE_PR_ITEM, "number": 99, "title": "fix: bug"})]
        text = _format_pr_list(my, review)
        assert "YOUR PRs" in text
        assert "REVIEW REQUESTS" in text
        assert "#42" in text
        assert "#99" in text

    def test_no_prs(self):
        text = _format_pr_list([], [])
        assert "No open PRs" in text

    def test_draft_indicator(self):
        draft_item = {**SAMPLE_PR_ITEM, "draft": True}
        text = _format_pr_list([_parse_pr(draft_item)], [])
        assert "✏️" in text


class TestFormatPRDetail:
    def test_full_detail(self):
        pr = _parse_pr_detail(SAMPLE_PR_DETAIL_RAW)
        text = _format_pr_detail(pr)
        assert "PR" in text and "42" in text
        assert "feat/search" in text
        assert "main" in text
        assert "250" in text  # additions
        assert "5 files" in text

    def test_mergeable_ready(self):
        pr = _parse_pr_detail({**SAMPLE_PR_DETAIL_RAW, "mergeable": True})
        text = _format_pr_detail(pr)
        assert "Ready" in text

    def test_mergeable_conflicts(self):
        pr = _parse_pr_detail({**SAMPLE_PR_DETAIL_RAW, "mergeable": False})
        text = _format_pr_detail(pr)
        assert "Conflicts" in text


# ── Unit Tests: Keyboards ──────────────────────────────────────────────


class TestPRKeyboards:
    def test_list_keyboard(self):
        my = [_parse_pr(SAMPLE_PR_ITEM)]
        kb = _pr_list_keyboard(my, [])
        all_data = [btn.callback_data for row in kb.inline_keyboard for btn in row if btn.callback_data]
        assert "pr:refresh" in all_data
        assert "pr:close" in all_data
        assert any("pr:detail" in d for d in all_data)

    def test_detail_keyboard(self):
        pr = _parse_pr_detail(SAMPLE_PR_DETAIL_RAW)
        kb = _pr_detail_keyboard(pr)
        urls = [btn.url for row in kb.inline_keyboard for btn in row if btn.url]
        assert any("github.com" in u for u in urls)
        all_data = [btn.callback_data for row in kb.inline_keyboard for btn in row if btn.callback_data]
        assert "pr:back" in all_data
        assert "pr:close" in all_data


# ── Handler Tests ───────────────────────────────────────────────────────


class TestPRCommand:
    @pytest.mark.asyncio
    async def test_no_github_config(self):
        update = _make_update(text="/pr")
        context = _make_context(has_github=False)
        result = await pr_command(update, context)
        assert result == -1  # END
        assert "not configured" in update.message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_successful_pr_list(self):
        update = _make_update(text="/pr")
        context = _make_context()

        with (
            patch("donna_bot.handlers.pr.get_my_prs", new_callable=AsyncMock) as mock_my,
            patch("donna_bot.handlers.pr.get_review_requests", new_callable=AsyncMock) as mock_review,
        ):
            mock_my.return_value = [_parse_pr(SAMPLE_PR_ITEM)]
            mock_review.return_value = []
            result = await pr_command(update, context)

        assert result == State.PR_LIST

    @pytest.mark.asyncio
    async def test_github_error(self):
        update = _make_update(text="/pr")
        context = _make_context()

        with patch("donna_bot.handlers.pr.get_my_prs", new_callable=AsyncMock) as mock_my:
            mock_my.side_effect = Exception("GitHub down")
            result = await pr_command(update, context)

        assert result == -1  # END


class TestPRListCallback:
    @pytest.mark.asyncio
    async def test_close(self):
        update = _make_update(is_callback=True, callback_data="pr:close")
        context = _make_context()
        result = await pr_list_callback(update, context)
        assert result == -1  # END

    @pytest.mark.asyncio
    async def test_refresh(self):
        update = _make_update(is_callback=True, callback_data="pr:refresh")
        context = _make_context()

        with (
            patch("donna_bot.handlers.pr.get_my_prs", new_callable=AsyncMock) as mock_my,
            patch("donna_bot.handlers.pr.get_review_requests", new_callable=AsyncMock) as mock_review,
        ):
            mock_my.return_value = []
            mock_review.return_value = []
            result = await pr_list_callback(update, context)

        assert result == State.PR_LIST


class TestPRDetailCallback:
    @pytest.mark.asyncio
    async def test_close(self):
        update = _make_update(is_callback=True, callback_data="pr:close")
        context = _make_context()
        result = await pr_detail_callback(update, context)
        assert result == -1

    @pytest.mark.asyncio
    async def test_back(self):
        update = _make_update(is_callback=True, callback_data="pr:back")
        context = _make_context()

        with (
            patch("donna_bot.handlers.pr.get_my_prs", new_callable=AsyncMock) as mock_my,
            patch("donna_bot.handlers.pr.get_review_requests", new_callable=AsyncMock) as mock_review,
        ):
            mock_my.return_value = []
            mock_review.return_value = []
            result = await pr_detail_callback(update, context)

        assert result == State.PR_LIST


class TestBuildConversation:
    def test_returns_handler(self):
        handler = build_pr_conversation()
        assert handler is not None
        assert handler.name == "pr_flow"
