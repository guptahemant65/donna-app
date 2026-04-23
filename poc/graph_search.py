"""
Microsoft Graph /search/query — Donna's M365 Search Brain
==========================================================
Uses WAM broker auth to search across Harvey's entire M365 tenant:
emails, files, Teams messages, events, people — everything.

Usage: python poc/graph_search.py "MCP server"
"""

import json
import sys
import threading
from datetime import datetime, timezone

import pymsalruntime
import requests

APP_IDS = [
    ("d3590ed6-52b3-4102-aeff-aad2292ab01c", "Microsoft Office"),
    ("14d82eec-204b-4c2f-b7e8-296a70dab67e", "Microsoft Graph PowerShell"),
]
GRAPH_BASE = "https://graph.microsoft.com/v1.0"

# ANSI colors
BOLD, RESET, CYAN, GREEN, RED, DIM, YELLOW = (
    "\033[1m", "\033[0m", "\033[36m", "\033[32m",
    "\033[31m", "\033[2m", "\033[33m",
)


def authenticate() -> str | None:
    """WAM broker silent auth — reuses graph_probe pattern."""
    event = threading.Event()
    disc_result = [None]

    def disc_cb(r):
        disc_result[0] = r
        event.set()

    pymsalruntime.discover_accounts(
        APP_IDS[0][0], "00000000-0000-0000-0000-000000000001", disc_cb,
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
        print(f"  {RED}No Microsoft corp account{RESET}")
        return None

    print(f"  {DIM}Account: {ms_account.get_user_name()}{RESET}")

    authority = f"https://login.microsoftonline.com/{ms_account.get_realm()}"
    scopes = ["https://graph.microsoft.com/.default"]

    for client_id, app_name in APP_IDS:
        event2 = threading.Event()
        tok_result = [None]

        def make_cb():
            def cb(r):
                tok_result[0] = r
                event2.set()
            return cb

        params = pymsalruntime.MSALRuntimeAuthParameters(client_id, authority)
        params.set_requested_scopes(scopes)
        pymsalruntime.acquire_token_silently(
            params, "00000000-0000-0000-0000-000000000002", ms_account, make_cb(),
        )
        event2.wait(15)

        r = tok_result[0]
        if r:
            token = r.get_access_token()
            if token and len(token) > 50:
                print(f"  {GREEN}Token via {app_name} + WAM{RESET}\n")
                return token

    print(f"  {RED}Auth failed{RESET}")
    return None


def search_m365(token: str, query: str, entity_types: list[str], size: int = 10) -> dict:
    """Call POST /search/query — searches across all M365."""
    url = f"{GRAPH_BASE}/search/query"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    body = {
        "requests": [
            {
                "entityTypes": entity_types,
                "query": {"queryString": query},
                "from": 0,
                "size": size,
            }
        ]
    }
    resp = requests.post(url, headers=headers, json=body, timeout=30)
    return resp.status_code, resp.json()


def print_results(data: dict, entity_type: str) -> int:
    """Pretty-print search results. Returns count."""
    count = 0
    for connection in data.get("value", []):
        for hit_container in connection.get("hitsContainers", []):
            total = hit_container.get("total", 0)
            hits = hit_container.get("hits", [])
            count = len(hits)

            print(f"  {BOLD}{entity_type}: {total} total results, showing {count}{RESET}")
            print(f"  {'─' * 56}")

            for i, hit in enumerate(hits):
                resource = hit.get("resource", {})
                summary_text = hit.get("summary", "")

                if entity_type == "message":
                    subject = resource.get("subject", "(no subject)")
                    sender = resource.get("sender", {}).get("emailAddress", {}).get("name", "?")
                    date = resource.get("receivedDateTime", "")[:10]
                    print(f"  {CYAN}{i+1}.{RESET} {subject}")
                    print(f"     {DIM}From: {sender} | {date}{RESET}")
                    if summary_text:
                        clean = summary_text.replace("<c0>", f"{YELLOW}").replace("</c0>", f"{RESET}")
                        print(f"     {clean[:200]}")

                elif entity_type == "driveItem":
                    name = resource.get("name", "?")
                    web_url = resource.get("webUrl", "")
                    modified = resource.get("lastModifiedDateTime", "")[:10]
                    created_by = resource.get("createdBy", {}).get("user", {}).get("displayName", "?")
                    print(f"  {CYAN}{i+1}.{RESET} {name}")
                    print(f"     {DIM}By: {created_by} | Modified: {modified}{RESET}")
                    if summary_text:
                        clean = summary_text.replace("<c0>", f"{YELLOW}").replace("</c0>", f"{RESET}")
                        print(f"     {clean[:200]}")

                elif entity_type == "chatMessage":
                    preview = resource.get("body", {}).get("content", "")[:150]
                    sender_name = resource.get("from", {}).get("emailAddress", {}).get("name", "?")
                    date = resource.get("createdDateTime", "")[:10]
                    print(f"  {CYAN}{i+1}.{RESET} {DIM}[Teams]{RESET} {sender_name} ({date})")
                    if summary_text:
                        clean = summary_text.replace("<c0>", f"{YELLOW}").replace("</c0>", f"{RESET}")
                        print(f"     {clean[:200]}")
                    elif preview:
                        print(f"     {DIM}{preview}{RESET}")

                elif entity_type == "event":
                    subject = resource.get("subject", "(no subject)")
                    start = resource.get("start", {}).get("dateTime", "")[:16]
                    print(f"  {CYAN}{i+1}.{RESET} {subject}")
                    print(f"     {DIM}{start}{RESET}")
                    if summary_text:
                        clean = summary_text.replace("<c0>", f"{YELLOW}").replace("</c0>", f"{RESET}")
                        print(f"     {clean[:200]}")

                elif entity_type == "listItem":
                    title = resource.get("fields", {}).get("title", resource.get("name", "?"))
                    web_url = resource.get("webUrl", "")
                    print(f"  {CYAN}{i+1}.{RESET} {title}")
                    if web_url:
                        print(f"     {DIM}{web_url[:100]}{RESET}")
                    if summary_text:
                        clean = summary_text.replace("<c0>", f"{YELLOW}").replace("</c0>", f"{RESET}")
                        print(f"     {clean[:200]}")

                else:
                    name = resource.get("displayName", resource.get("name", resource.get("subject", "?")))
                    print(f"  {CYAN}{i+1}.{RESET} {name}")
                    if summary_text:
                        clean = summary_text.replace("<c0>", f"{YELLOW}").replace("</c0>", f"{RESET}")
                        print(f"     {clean[:200]}")

                print()

    return count


def main():
    queries = sys.argv[1:] if len(sys.argv) > 1 else [
        "MCP server internal",
        "Graph API automation agent",
        "Model Context Protocol",
    ]

    print(f"\n{BOLD}{'═' * 60}{RESET}")
    print(f"{BOLD}  Donna M365 Search — /search/query{RESET}")
    print(f"{'═' * 60}\n")

    token = authenticate()
    if not token:
        sys.exit(1)

    # Entity types to search across
    search_configs = [
        ("message", "Emails"),
        ("driveItem", "Files (OneDrive/SharePoint)"),
        ("chatMessage", "Teams Messages"),
        ("event", "Calendar Events"),
        ("listItem", "SharePoint Lists"),
    ]

    results_file = {}

    for query in queries:
        print(f"\n{BOLD}{'━' * 60}{RESET}")
        print(f"  {BOLD}Query: \"{query}\"{RESET}")
        print(f"{'━' * 60}\n")

        results_file[query] = {}

        for entity_type, label in search_configs:
            print(f"  {YELLOW}▸ Searching {label}...{RESET}")
            try:
                status, data = search_m365(token, query, [entity_type], size=5)
                if status == 200:
                    count = print_results(data, entity_type)
                    results_file[query][entity_type] = {
                        "status": status,
                        "total": 0,
                        "shown": count,
                    }
                    # Extract total from response
                    for conn in data.get("value", []):
                        for hc in conn.get("hitsContainers", []):
                            results_file[query][entity_type]["total"] = hc.get("total", 0)
                else:
                    error = data.get("error", {}).get("message", str(data)[:200])
                    print(f"  {RED}  HTTP {status}: {error}{RESET}\n")
                    results_file[query][entity_type] = {"status": status, "error": error}
            except Exception as e:
                print(f"  {RED}  Error: {e}{RESET}\n")
                results_file[query][entity_type] = {"error": str(e)}

    # Save raw results
    out_path = "poc/graph_search_results.json"
    with open(out_path, "w") as f:
        json.dump(results_file, f, indent=2, default=str)
    print(f"\n{GREEN}Results saved to {out_path}{RESET}\n")


if __name__ == "__main__":
    main()
