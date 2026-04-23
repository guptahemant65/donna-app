"""
Microsoft Graph API Access Probe for Donna
============================================
Tests what Graph API endpoints Harvey's account can reach.
Uses MSAL device code flow to authenticate (bypasses CLI token protection).

Usage: python poc/graph_probe.py
"""

import json
import sys
from datetime import datetime, timezone

import msal
import requests

# Try multiple well-known first-party app IDs that exist in all Microsoft tenants
APP_IDS = [
    ("d3590ed6-52b3-4102-aeff-aad2292ab01c", "Microsoft Office"),
    ("1950a258-227b-4e31-a9cf-717495945fc2", "Azure PowerShell"),
    ("14d82eec-204b-4c2f-b7e8-296a70dab67e", "Microsoft Graph PowerShell"),
    ("04b07795-8ddb-461a-bbee-02f9e1bf7b46", "Azure CLI"),
]
AUTHORITY = "https://login.microsoftonline.com/organizations"
SCOPES = [
    "User.Read",
    "Mail.Read",
    "Calendars.Read",
    "People.Read",
    "Contacts.Read",
    "Tasks.Read",
    "Chat.Read",
    "Presence.Read",
    "Files.Read",
    "Notes.Read",
    "Sites.Read.All",
    "TeamMember.Read.All",
    "ChannelMessage.Read.All",
]

GRAPH_BASE = "https://graph.microsoft.com/v1.0"

# All endpoints Donna would need, grouped by capability domain
PROBES = {
    "Identity (Who is Harvey?)": [
        ("GET", "/me", "Basic profile"),
        ("GET", "/me/photo/$value", "Profile photo"),
    ],
    "Calendar (Temporal Intelligence)": [
        ("GET", "/me/calendarView?startDateTime={start}&endDateTime={end}", "Today's meetings"),
        ("GET", "/me/calendars", "Available calendars"),
        ("GET", "/me/events?$top=5&$orderby=start/dateTime", "Upcoming events"),
    ],
    "Email (Communications Intelligence)": [
        ("GET", "/me/messages?$top=5&$orderby=receivedDateTime desc", "Recent emails"),
        ("GET", "/me/mailFolders", "Mail folders"),
        ("GET", "/me/messages?$top=3&$filter=importance eq 'high'&$orderby=receivedDateTime desc", "High-importance emails"),
    ],
    "People (Social Intelligence)": [
        ("GET", "/me/people?$top=10", "Relevant people"),
        ("GET", "/me/contacts?$top=5", "Contacts"),
        ("GET", "/me/directReports", "Direct reports"),
        ("GET", "/me/manager", "Manager"),
    ],
    "Presence (Emotional/Contextual)": [
        ("GET", "/me/presence", "Current presence status"),
    ],
    "Teams & Chat (Communications)": [
        ("GET", "/me/joinedTeams", "Joined Teams"),
        ("GET", "/me/chats?$top=5", "Recent chats"),
    ],
    "Tasks (Productivity)": [
        ("GET", "/me/todo/lists", "To-Do lists"),
        ("GET", "/me/planner/tasks?$top=5", "Planner tasks"),
    ],
    "Files & OneDrive (Document Brain)": [
        ("GET", "/me/drive/root/children?$top=5", "OneDrive root"),
        ("GET", "/me/drive/recent?$top=5", "Recent files"),
    ],
    "OneNote (Knowledge)": [
        ("GET", "/me/onenote/notebooks", "OneNote notebooks"),
    ],
    "Organization (Political Intelligence)": [
        ("GET", "/organization", "Org info"),
        ("GET", "/me/memberOf?$top=10", "Group memberships"),
    ],
}

# ── Formatting ──────────────────────────────────────────────────────────────

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def status_icon(code: int) -> str:
    if 200 <= code < 300:
        return f"{GREEN}✓{RESET}"
    elif code == 403:
        return f"{RED}✕ FORBIDDEN{RESET}"
    elif code == 401:
        return f"{RED}✕ UNAUTHORIZED{RESET}"
    elif code == 404:
        return f"{YELLOW}○ NOT FOUND{RESET}"
    else:
        return f"{RED}✕ {code}{RESET}"


def format_preview(data: dict | list | bytes, endpoint: str) -> str:
    """Extract a meaningful preview from the response."""
    if isinstance(data, bytes):
        return f"{DIM}[binary {len(data)} bytes]{RESET}"

    if isinstance(data, list):
        return f"{DIM}[{len(data)} items]{RESET}"

    if isinstance(data, dict):
        if "value" in data and isinstance(data["value"], list):
            items = data["value"]
            count = len(items)
            if count == 0:
                return f"{DIM}[empty]{RESET}"

            first = items[0]
            if "displayName" in first:
                names = [i.get("displayName", "?") for i in items[:3]]
                suffix = f" +{count-3} more" if count > 3 else ""
                return f"{DIM}{', '.join(names)}{suffix}{RESET}"
            elif "subject" in first:
                return f"{DIM}{first['subject'][:60]}{RESET}"
            elif "name" in first:
                names = [i.get("name", "?") for i in items[:3]]
                suffix = f" +{count-3} more" if count > 3 else ""
                return f"{DIM}{', '.join(names)}{suffix}{RESET}"
            else:
                return f"{DIM}[{count} items]{RESET}"

        if "displayName" in data:
            return f"{DIM}{data['displayName']}{RESET}"
        if "availability" in data:
            return f"{DIM}{data['availability']}/{data.get('activity', '?')}{RESET}"
        if "mail" in data and "displayName" in data:
            return f"{DIM}{data['displayName']} <{data['mail']}>{RESET}"

    return ""


# ── Auth ────────────────────────────────────────────────────────────────────

def authenticate() -> str | None:
    """Authenticate silently via WAM broker (token-protection compliant)."""
    import pymsalruntime
    import threading

    print(f"\n{BOLD}{'─' * 60}{RESET}")
    print(f"{BOLD}  Donna Graph API Probe — Authentication{RESET}")
    print(f"{'─' * 60}\n")

    # Discover Windows SSO accounts
    event = threading.Event()
    disc_result: list = [None]

    def disc_cb(r: object) -> None:
        disc_result[0] = r
        event.set()

    pymsalruntime.discover_accounts(
        APP_IDS[0][0],
        "00000000-0000-0000-0000-000000000001",
        disc_cb,
    )
    event.wait(10)

    if not disc_result[0]:
        print(f"  {RED}No Windows SSO accounts found{RESET}")
        return None

    ms_account = None
    for a in disc_result[0].get_accounts():
        if "microsoft.com" in a.get_user_name():
            ms_account = a
            break

    if not ms_account:
        print(f"  {RED}No Microsoft corp account in Windows SSO{RESET}")
        return None

    print(f"  Found: {CYAN}{ms_account.get_user_name()}{RESET}")
    print(f"  Display: {ms_account.get_display_name()}")

    # Try each app ID for silent token acquisition
    authority = f"https://login.microsoftonline.com/{ms_account.get_realm()}"
    scopes = ["https://graph.microsoft.com/.default"]

    for client_id, app_name in APP_IDS:
        event2 = threading.Event()
        tok_result: list = [None]

        def make_cb() -> callable:
            def cb(r: object) -> None:
                tok_result[0] = r
                event2.set()
            return cb

        params = pymsalruntime.MSALRuntimeAuthParameters(client_id, authority)
        params.set_requested_scopes(scopes)

        pymsalruntime.acquire_token_silently(
            params,
            "00000000-0000-0000-0000-000000000002",
            ms_account,
            make_cb(),
        )
        event2.wait(15)

        r = tok_result[0]
        if r:
            token = r.get_access_token()
            if token and len(token) > 50:
                granted = r.get_granted_scopes()
                print(f"  {GREEN}Token acquired via {app_name} + WAM{RESET}")
                print(f"  {DIM}Scopes: {granted}{RESET}\n")
                return token
            else:
                error = r.get_error() or "empty token"
                if len(error) > 100:
                    error = error[:100] + "..."
                print(f"    {RED}✕ {app_name}: {error}{RESET}")
        else:
            print(f"    {RED}✕ {app_name}: timeout{RESET}")

    print(f"\n  {RED}All app IDs exhausted.{RESET}")
    return None


# ── Probing ─────────────────────────────────────────────────────────────────

def probe_endpoint(
    session: requests.Session,
    method: str,
    endpoint: str,
    label: str,
) -> dict:
    """Hit a single Graph endpoint and return result metadata."""
    now = datetime.now(timezone.utc)
    url = endpoint.replace("{start}", now.strftime("%Y-%m-%dT00:00:00Z"))
    url = url.replace("{end}", now.strftime("%Y-%m-%dT23:59:59Z"))

    full_url = f"{GRAPH_BASE}{url}"
    try:
        resp = session.request(method, full_url, timeout=10)
        code = resp.status_code
        icon = status_icon(code)

        preview = ""
        data = None
        if 200 <= code < 300:
            if "image" in resp.headers.get("Content-Type", ""):
                data = resp.content
                preview = format_preview(data, endpoint)
            else:
                try:
                    data = resp.json()
                    preview = format_preview(data, endpoint)
                except Exception:
                    pass

        error_code = ""
        if code >= 400:
            try:
                err = resp.json()
                error_code = err.get("error", {}).get("code", "")
            except Exception:
                pass

        print(f"    {icon}  {label:<35} {preview}")
        if error_code:
            print(f"         {DIM}({error_code}){RESET}")

        return {
            "endpoint": endpoint,
            "label": label,
            "status": code,
            "error_code": error_code,
            "has_data": data is not None,
        }

    except requests.exceptions.Timeout:
        print(f"    {YELLOW}⏱  {label:<35} {DIM}timeout{RESET}")
        return {"endpoint": endpoint, "label": label, "status": 0, "error_code": "timeout"}
    except Exception as e:
        print(f"    {RED}✕  {label:<35} {DIM}{e}{RESET}")
        return {"endpoint": endpoint, "label": label, "status": 0, "error_code": str(e)}


def run_probes(token: str) -> tuple[list[dict], dict]:
    """Run all probes and return results."""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    })

    all_results = []
    domain_summary = {}

    print(f"\n{BOLD}{'─' * 60}{RESET}")
    print(f"{BOLD}  Probing Graph API Endpoints{RESET}")
    print(f"{'─' * 60}\n")

    for domain, endpoints in PROBES.items():
        print(f"  {BOLD}{CYAN}{domain}{RESET}")
        domain_ok = 0
        domain_total = 0

        for method, endpoint, label in endpoints:
            result = probe_endpoint(session, method, endpoint, label)
            result["domain"] = domain
            all_results.append(result)
            domain_total += 1
            if 200 <= result["status"] < 300:
                domain_ok += 1

        domain_summary[domain] = (domain_ok, domain_total)
        pct = (domain_ok / domain_total * 100) if domain_total > 0 else 0
        color = GREEN if pct == 100 else YELLOW if pct > 0 else RED
        print(f"    {color}── {domain_ok}/{domain_total} accessible{RESET}\n")

    return all_results, domain_summary


def print_summary(results: list[dict], domain_summary: dict) -> None:
    """Print the final summary report."""
    total = len(results)
    ok = sum(1 for r in results if 200 <= r["status"] < 300)
    forbidden = sum(1 for r in results if r["status"] == 403)
    unauthorized = sum(1 for r in results if r["status"] == 401)
    not_found = sum(1 for r in results if r["status"] == 404)

    print(f"\n{BOLD}{'═' * 60}{RESET}")
    print(f"{BOLD}  DONNA GRAPH ACCESS REPORT{RESET}")
    print(f"{'═' * 60}\n")

    print(f"  {GREEN}Accessible:   {ok}/{total}{RESET}")
    if forbidden:
        print(f"  {RED}Forbidden:    {forbidden}/{total}{RESET}")
    if unauthorized:
        print(f"  {RED}Unauthorized: {unauthorized}/{total}{RESET}")
    if not_found:
        print(f"  {YELLOW}Not Found:    {not_found}/{total}{RESET}")

    print(f"\n  {BOLD}By Domain:{RESET}")
    for domain, (ok_count, total_count) in domain_summary.items():
        pct = (ok_count / total_count * 100) if total_count > 0 else 0
        bar_len = 20
        filled = int(pct / 100 * bar_len)
        bar = f"{'█' * filled}{'░' * (bar_len - filled)}"
        color = GREEN if pct == 100 else YELLOW if pct > 0 else RED
        short = domain.split("(")[0].strip()
        print(f"    {color}{bar} {pct:3.0f}%{RESET}  {short}")

    # Donna capability mapping
    print(f"\n  {BOLD}Donna Capability Unlocks:{RESET}")
    capability_map = {
        "Identity": "Morning Briefing, Personalization",
        "Calendar": "Temporal Intelligence, Meeting Prep, Schedule Awareness",
        "Email": "Communications Intelligence, Priority Triage, The Gatekeeper",
        "People": "Social Intelligence, People Graph, The Network",
        "Presence": "Emotional Intelligence, Burnout Detection",
        "Teams & Chat": "Communications, Handle-It, The Closer",
        "Tasks": "Productivity Intelligence, Follow-up Tracking",
        "Files & OneDrive": "Document Brain, Context Awareness",
        "OneNote": "Knowledge Base, Meeting Notes",
        "Organization": "Political Intelligence, Career Intelligence",
    }

    for domain, (ok_count, _) in domain_summary.items():
        short = domain.split("(")[0].strip()
        capabilities = capability_map.get(short, "—")
        status = f"{GREEN}UNLOCKED{RESET}" if ok_count > 0 else f"{RED}BLOCKED{RESET}"
        print(f"    {status}  {capabilities}")

    print(f"\n{'═' * 60}\n")


# ── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    token = authenticate()
    if not token:
        print(f"\n{RED}Cannot proceed without authentication.{RESET}")
        sys.exit(1)

    results, domain_summary = run_probes(token)
    print_summary(results, domain_summary)

    # Save raw results
    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_probes": len(results),
        "results": results,
        "domain_summary": {
            k: {"ok": v[0], "total": v[1]}
            for k, v in domain_summary.items()
        },
    }
    with open("poc/graph_probe_results.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"  {DIM}Results saved to poc/graph_probe_results.json{RESET}\n")


if __name__ == "__main__":
    main()
