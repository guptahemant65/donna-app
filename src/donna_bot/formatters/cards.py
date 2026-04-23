"""Card templates — beautiful, structured messages for Donna's responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from donna_bot.formatters.escape import (
    md2,
    md2_bold,
    md2_header,
    md2_italic,
    md2_link,
    md2_progress_bar,
    md2_separator,
)


def _calc_focus_time(meetings: list[dict]) -> int:
    """Estimate focus hours in an 8h day minus meeting time."""
    total_meeting_mins = 0
    for m in meetings:
        dur = m.get("duration", "30m")
        if isinstance(dur, str):
            dur = int(dur.replace("m", "").replace("h", "")) if "h" not in dur else int(dur.replace("h", "")) * 60
        total_meeting_mins += dur
    return max(0, (480 - total_meeting_mins) // 60)


def format_briefing_card(
    incidents: list[dict],
    emails: list[dict],
    meetings: list[dict],
    sprint: dict[str, int],
    weather: dict[str, Any] | None = None,
) -> str:
    """Morning briefing — the crown jewel."""
    now = datetime.now()
    lines = [
        md2_header(),
        f"☀️ {md2_bold('MORNING BRIEFING')}",
        md2_italic(now.strftime("%A, %B %d") + " · " + now.strftime("%I:%M %p")),
        "",
    ]

    # Incidents
    if incidents:
        lines.append(f"🔴 {md2_bold('INCIDENTS')}")
        for inc in incidents:
            sev = md2(inc.get("severity", "?"))
            title = md2(inc.get("title", "Unknown"))
            status = md2(inc.get("status", "active"))
            lines.append(f"   {sev} {title} — {status}")
    else:
        lines.append(f"🟢 {md2_bold('INCIDENTS')}  {md2('All clear')}")
    lines.append("")

    # Emails
    count = len(emails)
    label = f"{count} need action" if count > 0 else "Inbox zero"
    lines.append(f"📬 {md2_bold('EMAILS')} {md2('(' + label + ')')}")
    for i, em in enumerate(emails[:5], 1):
        sender = md2(em.get("from", "?"))
        subject = md2(em.get("subject", "(no subject)"))
        lines.append(f"   {md2(str(i) + '.')} {sender} — {subject}")
    lines.append("")

    # Meetings
    focus_hours = _calc_focus_time(meetings)
    meeting_label = f"{len(meetings)} meetings · {focus_hours}h focus time"
    lines.append(f"📅 {md2_bold('TODAY')} {md2('(' + meeting_label + ')')}")
    for m in meetings[:6]:
        start = md2(m.get("start", "?"))
        subject = md2(m.get("subject", "Meeting"))
        dur = md2(m.get("duration", ""))
        lines.append(f"   {start}  {subject} {md2('(' + dur + ')')}" if dur else f"   {start}  {subject}")
    lines.append("")

    # Sprint
    done = sprint.get("done", 0)
    total = sprint.get("total", 0)
    if total > 0:
        days_left = sprint.get("days_left", "?")
        lines.append(f"🏃 {md2_bold('SPRINT')}  {md2_progress_bar(done, total)}")
        lines.append(f"   {md2(str(done) + '/' + str(total) + ' done · ' + str(days_left) + ' days left')}")
        lines.append("")

    # Weather (optional)
    if weather:
        temp = weather.get("temp", "?")
        condition = weather.get("condition", "")
        commute = weather.get("commute", "")
        weather_line = f"☁️ {md2(str(temp) + '°C Bangalore')}"
        if condition:
            weather_line += f" · {md2(condition)}"
        if commute:
            weather_line += f" · {md2(commute + ' commute')}"
        lines.append(weather_line)

    lines.append(md2_separator())
    return "\n".join(lines)


def format_email_card(
    sender: str,
    to: str,
    date: str,
    subject: str,
    body: str,
    has_attachments: bool = False,
) -> str:
    """Email detail card."""
    lines = [
        f"📬 {md2_bold('EMAIL')} {md2('━' * 22)}",
        "",
        f"{md2_bold('From:')} {md2(sender)}",
        f"{md2_bold('To:')} {md2(to)}",
        f"{md2_italic(date)}",
        f"{md2_bold('Subject:')} {md2(subject)}",
    ]
    if has_attachments:
        lines.append(f"📎 {md2_italic('Has attachments')}")
    lines.extend(["", md2(body[:500]), "", md2_separator()])
    return "\n".join(lines)


def format_meeting_card(
    subject: str,
    time: str,
    duration: str,
    location: str,
    attendees: list[str],
    context: str = "",
    talking_points: list[str] | None = None,
    join_url: str = "",
) -> str:
    """Meeting prep card."""
    lines = [
        f"📅 {md2_bold('MEETING PREP')} {md2('━' * 16)}",
        "",
        md2_bold(subject),
        f"⏰ {md2(time)} · {md2(duration)}",
        f"📍 {md2(location)}",
        f"👥 {md2(', '.join(attendees[:4]))}",
    ]
    if len(attendees) > 4:
        lines[-1] += f" {md2_italic('+' + str(len(attendees) - 4) + ' more')}"

    if context:
        lines.extend(["", f"📋 {md2_bold('CONTEXT')}", f"   {md2(context)}"])

    if talking_points:
        lines.extend(["", f"💡 {md2_bold('TALKING POINTS')}"])
        for tp in talking_points:
            lines.append(f"   • {md2(tp)}")

    if join_url:
        lines.extend(["", f"🔗 {md2_link('Join Teams Meeting', join_url)}"])

    lines.extend(["", md2_separator()])
    return "\n".join(lines)


def format_person_card(
    name: str,
    title: str,
    department: str,
    location: str,
    availability: str,
    email: str,
    manager: str = "",
) -> str:
    """Person detail card."""
    status_emoji = {"Available": "🟢", "Busy": "🔴", "Away": "🟡"}.get(availability, "⚪")
    lines = [
        f"👤 {md2_bold('PERSON')} {md2('━' * 22)}",
        "",
        md2_bold(name),
        md2_italic(title),
        md2(department),
        "",
        f"📍 {md2(location)} · {status_emoji} {md2(availability)}",
        f"📧 {md2(email)}",
    ]
    if manager:
        lines.extend(["", f"🔗 {md2_bold('Reports to:')} {md2(manager)}"])

    lines.extend(["", md2_separator()])
    return "\n".join(lines)
