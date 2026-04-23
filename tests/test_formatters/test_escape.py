"""Tests for MarkdownV2 escaping."""

from __future__ import annotations

from donna_bot.formatters.escape import md2, md2_bold, md2_code, md2_italic, md2_link, md2_pre


class TestMd2Escape:
    def test_escapes_special_chars(self) -> None:
        assert md2("Hello.World!") == r"Hello\.World\!"

    def test_preserves_plain_text(self) -> None:
        assert md2("Hello World") == "Hello World"

    def test_escapes_underscore(self) -> None:
        assert "\\_" in md2("test_value")

    def test_escapes_parens(self) -> None:
        assert "\\(" in md2("func()")

    def test_bold(self) -> None:
        assert md2_bold("Hello") == "*Hello*"

    def test_italic(self) -> None:
        assert md2_italic("Hello") == "_Hello_"

    def test_code(self) -> None:
        result = md2_code("print()")
        assert result.startswith("`")
        assert result.endswith("`")

    def test_link(self) -> None:
        result = md2_link("Click", "https://example.com/path")
        assert result.startswith("[Click]")
        assert "example" in result

    def test_pre_block(self) -> None:
        result = md2_pre("line1\nline2")
        assert result.startswith("```\n")
        assert result.endswith("\n```")
