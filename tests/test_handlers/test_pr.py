"""Tests for handlers/pr.py — ADO PR Intelligence handler."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from donna_bot.handlers.pr import (
    AdoRepo,
    _format_pr_detail,
    _format_pr_list,
    _parse_pr,
    _parse_pr_detail,
    _pr_detail_keyboard,
    _pr_list_keyboard,
    _vote_icon,
    build_pr_conversation,
    parse_ado_repos,
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


def _make_context(has_ado=True):
    context = MagicMock()
    context.args = []
    context.user_data = {}
    context.bot_data = {}

    settings = MagicMock()
    settings.harvey_chat_id = 496116833
    if has_ado:
        settings.ado_pat = "test-pat-123"
        settings.ado_email = "guptahemant@microsoft.com"
        settings.ado_repos_json = "powerbi/MWC/workload-fabriclivetable"
    else:
        settings.ado_pat = ""
        settings.ado_email = ""
        settings.ado_repos_json = ""
    context.bot_data["settings"] = settings
    return context


SAMPLE_REPO = AdoRepo(org="powerbi", project="MWC", repo="workload-fabriclivetable")

SAMPLE_ADO_PR = {
    "pullRequestId": 42,
    "title": "feat: add search module",
    "createdBy": {
        "displayName": "Hemant Gupta",
        "uniqueName": "guptahemant@microsoft.com",
    },
    "creationDate": "2025-01-15T10:00:00Z",
    "sourceRefName": "refs/heads/feat/search",
    "targetRefName": "refs/heads/main",
    "status": "active",
    "isDraft": False,
    "mergeStatus": "succeeded",
    "reviewers": [
        {"displayName": "Alice", "vote": 10},
        {"displayName": "Bob", "vote": 0},
        {"displayName": "Carol", "vote": -5},
    ],
}

SAMPLE_ADO_PR_DETAIL = {
    **SAMPLE_ADO_PR,
    "description": "This PR adds M365 search capability to the bot.",
    "lastMergeSourceCommit": {"commitId": "abc123def456"},
    "labels": [{"name": "enhancement"}, {"name": "search"}],
}


# ── Unit Tests: AdoRepo Config ──────────────────────────────────────────


class TestParseAdoRepos:
    def test_semicolon_format(self):
        repos = parse_ado_repos("powerbi/MWC/workload-fabriclivetable;msdata/HDInsight/repo2")
        assert len(repos) == 2
        assert repos[0].org == "powerbi"
        assert repos[0].project == "MWC"
        assert repos[0].repo == "workload-fabriclivetable"
        assert repos[1].org == "msdata"

    def test_json_format(self):
        json_str = '[{"org":"powerbi","project":"MWC","repo":"flt"}]'
        repos = parse_ado_repos(json_str)
        assert len(repos) == 1
        assert repos[0].repo == "flt"

    def test_empty_string(self):
        assert parse_ado_repos("") == []

    def test_single_repo(self):
        repos = parse_ado_repos("powerbi/MWC/workload-fabriclivetable")
        assert len(repos) == 1

    def test_invalid_triple_skipped(self):
        repos = parse_ado_repos("powerbi/MWC/repo;invalid-format")
        assert len(repos) == 1

    def test_whitespace_handling(self):
        repos = parse_ado_repos("  powerbi/MWC/repo ;  msdata/HDI/repo2  ")
        assert len(repos) == 2


class TestAdoRepo:
    def test_base_url(self):
        assert SAMPLE_REPO.base_url == "https://dev.azure.com/powerbi"

    def test_label(self):
        assert SAMPLE_REPO.label == "powerbi/MWC/workload-fabriclivetable"


# ── Unit Tests: Vote Icons ──────────────────────────────────────────────


class TestVoteIcon:
    def test_approved(self):
        assert _vote_icon(10) == "✅"

    def test_approved_suggestions(self):
        assert _vote_icon(5) == "👍"

    def test_waiting(self):
        assert _vote_icon(-5) == "⏳"

    def test_rejected(self):
        assert _vote_icon(-10) == "❌"

    def test_no_vote(self):
        assert _vote_icon(0) == "⬜"


# ── Unit Tests: Parsers ─────────────────────────────────────────────────


class TestParsePR:
    def test_parses_ado_pr(self):
        pr = _parse_pr(SAMPLE_ADO_PR, SAMPLE_REPO)
        assert pr["id"] == 42
        assert pr["title"] == "feat: add search module"
        assert pr["author"] == "Hemant Gupta"
        assert pr["source"] == "feat/search"
        assert pr["target"] == "main"
        assert pr["isDraft"] is False
        assert len(pr["reviewers"]) == 3
        assert pr["reviewers"][0]["icon"] == "✅"  # Alice approved
        assert pr["reviewers"][2]["icon"] == "⏳"  # Carol waiting

    def test_handles_missing_fields(self):
        pr = _parse_pr({}, SAMPLE_REPO)
        assert pr["id"] == 0
        assert pr["title"] == "?"

    def test_url_generated(self):
        pr = _parse_pr(SAMPLE_ADO_PR, SAMPLE_REPO)
        assert "dev.azure.com/powerbi/MWC" in pr["url"]
        assert "pullrequest/42" in pr["url"]


class TestParsePRDetail:
    def test_full_detail(self):
        pr = _parse_pr_detail(SAMPLE_ADO_PR_DETAIL, SAMPLE_REPO)
        assert pr["description"] == "This PR adds M365 search capability to the bot."
        assert "enhancement" in pr["labels"]
        assert pr["merge_id"] == "abc123de"


# ── Unit Tests: Formatters ──────────────────────────────────────────────


class TestFormatPRList:
    def test_with_prs(self):
        my = [_parse_pr(SAMPLE_ADO_PR, SAMPLE_REPO)]
        text = _format_pr_list(my, [])
        assert "YOUR PRs" in text
        assert "!42" in text or "42" in text

    def test_no_prs(self):
        text = _format_pr_list([], [])
        assert "No open PRs" in text

    def test_draft_indicator(self):
        draft = {**SAMPLE_ADO_PR, "isDraft": True}
        text = _format_pr_list([_parse_pr(draft, SAMPLE_REPO)], [])
        assert "✏️" in text

    def test_review_votes_shown(self):
        text = _format_pr_list([_parse_pr(SAMPLE_ADO_PR, SAMPLE_REPO)], [])
        assert "✅" in text  # Alice's approval vote


class TestFormatPRDetail:
    def test_full_detail(self):
        pr = _parse_pr_detail(SAMPLE_ADO_PR_DETAIL, SAMPLE_REPO)
        text = _format_pr_detail(pr)
        assert "PR" in text and "42" in text
        assert "feat/search" in text
        assert "main" in text
        assert "No conflicts" in text

    def test_conflicts(self):
        conflicted = {**SAMPLE_ADO_PR_DETAIL, "mergeStatus": "conflicts"}
        pr = _parse_pr_detail(conflicted, SAMPLE_REPO)
        text = _format_pr_detail(pr)
        assert "Conflicts" in text

    def test_reviewers_listed(self):
        pr = _parse_pr_detail(SAMPLE_ADO_PR_DETAIL, SAMPLE_REPO)
        text = _format_pr_detail(pr)
        assert "Alice" in text
        assert "✅" in text


# ── Unit Tests: Keyboards ──────────────────────────────────────────────


class TestPRKeyboards:
    def test_list_keyboard(self):
        my = [_parse_pr(SAMPLE_ADO_PR, SAMPLE_REPO)]
        kb = _pr_list_keyboard(my, [])
        all_data = [btn.callback_data for row in kb.inline_keyboard for btn in row if btn.callback_data]
        assert "pr:refresh" in all_data
        assert "pr:close" in all_data
        assert any("pr:detail" in d for d in all_data)

    def test_detail_keyboard(self):
        pr = _parse_pr_detail(SAMPLE_ADO_PR_DETAIL, SAMPLE_REPO)
        kb = _pr_detail_keyboard(pr)
        urls = [btn.url for row in kb.inline_keyboard for btn in row if btn.url]
        assert any("dev.azure.com" in u for u in urls)
        all_data = [btn.callback_data for row in kb.inline_keyboard for btn in row if btn.callback_data]
        assert "pr:back" in all_data
        assert "pr:close" in all_data

    def test_detail_button_label(self):
        pr = _parse_pr_detail(SAMPLE_ADO_PR_DETAIL, SAMPLE_REPO)
        kb = _pr_detail_keyboard(pr)
        labels = [btn.text for row in kb.inline_keyboard for btn in row]
        assert any("ADO" in lbl for lbl in labels)


# ── Handler Tests ───────────────────────────────────────────────────────


class TestPRCommand:
    @pytest.mark.asyncio
    async def test_no_ado_config(self):
        update = _make_update(text="/pr")
        context = _make_context(has_ado=False)
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
            mock_my.return_value = [_parse_pr(SAMPLE_ADO_PR, SAMPLE_REPO)]
            mock_review.return_value = []
            result = await pr_command(update, context)

        assert result == State.PR_LIST

    @pytest.mark.asyncio
    async def test_ado_error(self):
        update = _make_update(text="/pr")
        context = _make_context()

        with (
            patch("donna_bot.handlers.pr.get_my_prs", new_callable=AsyncMock) as mock_my,
            patch("donna_bot.handlers.pr.get_review_requests", new_callable=AsyncMock) as mock_review,
        ):
            mock_my.side_effect = Exception("ADO down")
            mock_review.side_effect = Exception("ADO down")
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
