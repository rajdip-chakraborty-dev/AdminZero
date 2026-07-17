"""
mock_server.py
==============
AdminZero · BetterWorldWithAI · IBM watsonx Challenge 2026

A ZERO-DEPENDENCY local mock API server that serves the AdminZero skill
endpoints defined in ``orchestrate_skills/swagger.yaml`` from the generated
mock datasets in ``sandbox_setup/output/``.

Why this exists
---------------
The live demo depends on four external free-tier accounts (IBM watsonx
Orchestrate, Azure AD / Microsoft Graph, Jira Cloud, Slack).  If any of them
are not provisioned in time, this server becomes the demo's safety net: it
mimics Microsoft Graph, GitHub, Jira, and Slack closely enough that the
watsonx Orchestrate skills — or a plain ``curl`` walkthrough — return
realistic data with no internet and no credentials.

It is written entirely on the Python 3 standard library (``http.server``),
so it runs with nothing but ``python3`` — no ``pip install`` required.

Usage
-----
    # from the repo root or sandbox_setup/
    python mock_server.py                 # serves on http://127.0.0.1:8080
    python mock_server.py --port 9000     # custom port
    python mock_server.py --host 0.0.0.0  # expose on the network

If the ``output/`` datasets are missing, the server generates them on
startup by importing ``generate_dummy_data``.

Endpoints (mirroring swagger.yaml operationIds)
-----------------------------------------------
    GET  /                                              → HTML index / health
    GET  /openapi.yaml                                  → the raw skill spec
    GET  /me/calendarView                               → get_calendar_events
    POST /me/drive/items/{id}/workbook/.../rows         → write_timesheet_row
    GET  /repos/{owner}/{repo}/pulls                     → get_open_pull_requests
    GET  /repos/{owner}/{repo}/pulls/{pull_number}       → get_pr_details
    GET  /me/messages                                    → get_recent_emails
    GET  /search                                         → get_jira_blockers
    POST /chat.postMessage                               → send_slack_message
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import runpy
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
HERE        = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR  = os.path.join(HERE, "output")
REPO_ROOT   = os.path.dirname(HERE)
SWAGGER_PATH = os.path.join(REPO_ROOT, "orchestrate_skills", "swagger.yaml")


# ---------------------------------------------------------------------------
# Data loading (auto-generates datasets if missing)
# ---------------------------------------------------------------------------

def _ensure_data() -> None:
    """Generate the mock datasets on first run if output/ is empty."""
    required = ["calendar_events.json", "github_pull_requests.json",
                "jira_tickets.json", "timesheet_ledger.csv", "outlook_emails.json"]
    if all(os.path.exists(os.path.join(OUTPUT_DIR, f)) for f in required):
        return
    print("[mock_server] output/ incomplete — running generate_dummy_data.py …")
    sys.path.insert(0, HERE)
    runpy.run_path(os.path.join(HERE, "generate_dummy_data.py"), run_name="__generated__")


def _load_json(name: str) -> list:
    path = os.path.join(OUTPUT_DIR, name)
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _load_csv(name: str) -> list[dict]:
    path = os.path.join(OUTPUT_DIR, name)
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


class DataStore:
    """In-memory copy of the mock datasets, loaded once at startup."""

    def __init__(self) -> None:
        _ensure_data()
        self.calendar     = _load_json("calendar_events.json")
        self.pull_requests = _load_json("github_pull_requests.json")
        self.jira         = _load_json("jira_tickets.json")
        self.emails       = _load_json("outlook_emails.json")
        self.timesheet    = _load_csv("timesheet_ledger.csv")
        # Rows appended during the demo via write_timesheet_row (kept in memory)
        self.timesheet_appended: list[list] = []


STORE: DataStore | None = None  # populated in main()


# ---------------------------------------------------------------------------
# Endpoint handlers — each returns (status_code, body_dict)
# ---------------------------------------------------------------------------

def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def handle_calendar_view(query: dict) -> tuple[int, dict]:
    """GET /me/calendarView → get_calendar_events"""
    events = STORE.calendar
    start = query.get("startDateTime", [None])[0]
    end   = query.get("endDateTime", [None])[0]

    def _in_range(ev: dict) -> bool:
        dt = ev["start"]["dateTime"]
        if start and dt < start:
            return False
        if end and dt > end:
            return False
        return True

    filtered = [e for e in events if _in_range(e)] if (start or end) else events
    top = int(query.get("$top", [len(filtered)])[0])
    filtered = filtered[:top]
    return 200, {
        "@odata.context": "https://graph.microsoft.com/v1.0/$metadata#users('me')/calendarView",
        "value": filtered,
    }


def handle_write_timesheet(body: dict) -> tuple[int, dict]:
    """POST /me/drive/.../tables/{tableId}/rows → write_timesheet_row"""
    values = body.get("values", []) if isinstance(body, dict) else []
    if not values or not isinstance(values, list):
        return 400, {"error": {"code": "invalidRequest",
                               "message": "Body must contain a non-empty 'values' 2D array."}}
    STORE.timesheet_appended.extend(values)
    return 201, {
        "success": True,
        "rowsWritten": len(values),
        "workbookUrl": "https://onedrive.live.com/mock/AdminZero_Timesheet.xlsx",
        "totalRowsInLedger": len(STORE.timesheet) + len(STORE.timesheet_appended),
    }


def handle_pull_requests(owner: str, repo: str, query: dict) -> tuple[int, dict]:
    """GET /repos/{owner}/{repo}/pulls → get_open_pull_requests"""
    prs = STORE.pull_requests
    full = f"{owner}/{repo}".lower()
    # Filter by repo when the caller asks for a specific one we have data for
    matched = [p for p in prs if str(p.get("repository", "")).lower() == full]
    result  = matched if matched else prs  # fall back to all repos for the demo

    state = query.get("state", ["open"])[0]
    if state != "all":
        result = [p for p in result if p.get("state") == state]

    per_page = int(query.get("per_page", [30])[0])
    page     = int(query.get("page", [1])[0])
    start    = (page - 1) * per_page
    return 200, {
        "totalOpenPRs": len(result),
        "pull_requests": result[start:start + per_page],
    }


def handle_pr_details(owner: str, repo: str, number: int) -> tuple[int, dict]:
    """GET /repos/{owner}/{repo}/pulls/{pull_number} → get_pr_details"""
    for p in STORE.pull_requests:
        if int(p.get("number", -1)) == number:
            return 200, p
    return 404, {"error": {"code": "notFound",
                           "message": f"Pull request #{number} not found in mock data."}}


def handle_messages(query: dict) -> tuple[int, dict]:
    """GET /me/messages → get_recent_emails"""
    emails = STORE.emails
    odata_filter = query.get("$filter", [""])[0]

    # Minimal OData $filter support for the two clauses the demo uses.
    if "isRead eq false" in odata_filter:
        emails = [m for m in emails if not m.get("isRead", False)]
    m = re.search(r"receivedDateTime ge ([0-9T:\-]+Z?)", odata_filter)
    if m:
        cutoff = m.group(1)
        emails = [e for e in emails if e["receivedDateTime"] >= cutoff]

    top = int(query.get("$top", [len(emails)])[0])
    return 200, {"value": emails[:top]}


def handle_jira_search(query: dict) -> tuple[int, dict]:
    """GET /search → get_jira_blockers (JQL-aware)"""
    jql = query.get("jql", [""])[0]
    issues = STORE.jira

    # Interpret the handful of JQL clauses the demo relies on.
    if "status = Blocked" in jql or "status=Blocked" in jql:
        issues = [i for i in issues if i["fields"]["status"]["name"] == "Blocked"]

    m = re.search(r"project\s*=\s*([A-Z]+)", jql)
    if m:
        key = m.group(1)
        issues = [i for i in issues
                  if i["fields"].get("project", {}).get("key") == key]

    prio = re.search(r"priority\s*=\s*(\w+)", jql)
    if prio:
        issues = [i for i in issues
                  if i["fields"]["priority"]["name"].lower() == prio.group(1).lower()]

    if "ORDER BY priority" in jql:
        order = {"Blocker": 0, "Critical": 1, "Major": 2, "Minor": 3, "Trivial": 4}
        issues = sorted(issues, key=lambda i: order.get(i["fields"]["priority"]["name"], 9))

    max_results = int(query.get("maxResults", [50])[0])
    return 200, {
        "total": len(issues),
        "maxResults": max_results,
        "issues": issues[:max_results],
    }


def handle_slack_post(body: dict) -> tuple[int, dict]:
    """POST /chat.postMessage → send_slack_message"""
    if not isinstance(body, dict) or not body.get("channel") or not body.get("text"):
        return 400, {"ok": False, "error": "channel_and_text_required"}
    ts = f"{datetime.now(timezone.utc).timestamp():.6f}"
    print(f"[slack] → {body['channel']}: {body['text']!r}")
    return 200, {
        "ok": True,
        "channel": body["channel"],
        "ts": ts,
        "message": {
            "text": body["text"],
            "username": body.get("username", "AdminZero Co-Pilot"),
            "blocks": body.get("blocks", []),
            "bot_id": "B0MOCKADMINZERO",
            "ts": ts,
        },
    }


# ---------------------------------------------------------------------------
# Landing page
# ---------------------------------------------------------------------------

def _index_html() -> str:
    n = {
        "calendar": len(STORE.calendar),
        "prs": len(STORE.pull_requests),
        "jira": len(STORE.jira),
        "emails": len(STORE.emails),
        "timesheet": len(STORE.timesheet),
    }
    blocked = sum(1 for i in STORE.jira if i["fields"]["status"]["name"] == "Blocked")
    rows = [
        ("GET",  "/me/calendarView?startDateTime=...&endDateTime=...", "get_calendar_events", f"{n['calendar']} events"),
        ("POST", "/me/drive/items/{id}/workbook/worksheets/{ws}/tables/{tbl}/rows", "write_timesheet_row", "append rows"),
        ("GET",  "/repos/{owner}/{repo}/pulls", "get_open_pull_requests", f"{n['prs']} PRs"),
        ("GET",  "/repos/{owner}/{repo}/pulls/{pull_number}", "get_pr_details", "single PR"),
        ("GET",  "/me/messages?$filter=isRead eq false", "get_recent_emails", f"{n['emails']} emails"),
        ("GET",  "/search?jql=status = Blocked", "get_jira_blockers", f"{blocked} blocked"),
        ("POST", "/chat.postMessage", "send_slack_message", "echo"),
        ("GET",  "/openapi.yaml", "—", "skill spec"),
    ]
    tr = "\n".join(
        f'<tr><td><span class="m {method.lower()}">{method}</span></td>'
        f'<td><code>{path}</code></td><td>{op}</td><td>{note}</td></tr>'
        for method, path, op, note in rows
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AdminZero · Local Mock API</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; margin: 0;
          background: #0d1117; color: #e6edf3; }}
  header {{ padding: 28px 32px; background: linear-gradient(135deg,#1f6feb,#6f42c1); }}
  header h1 {{ margin: 0; font-size: 22px; }}
  header p {{ margin: 6px 0 0; opacity: .9; font-size: 14px; }}
  .wrap {{ max-width: 980px; margin: 0 auto; padding: 24px 32px; }}
  .pill {{ display:inline-block; background:#238636; color:#fff; border-radius:999px;
           padding:2px 10px; font-size:12px; font-weight:600; }}
  table {{ width:100%; border-collapse:collapse; margin-top:16px; font-size:14px; }}
  th,td {{ text-align:left; padding:9px 10px; border-bottom:1px solid #30363d; }}
  th {{ color:#8b949e; font-weight:600; }}
  code {{ background:#161b22; padding:2px 6px; border-radius:5px; font-size:12.5px; }}
  .m {{ font-size:11px; font-weight:700; padding:2px 7px; border-radius:5px; }}
  .get {{ background:#1f6feb33; color:#58a6ff; }}
  .post {{ background:#23863633; color:#3fb950; }}
  .stats {{ display:flex; gap:10px; flex-wrap:wrap; margin-top:8px; }}
  .stat {{ background:#161b22; border:1px solid #30363d; border-radius:8px; padding:10px 14px; }}
  .stat b {{ font-size:18px; display:block; }}
  .stat span {{ font-size:12px; color:#8b949e; }}
  a {{ color:#58a6ff; }}
</style></head>
<body>
<header>
  <h1>🤖 AdminZero — Local Mock API</h1>
  <p>Zero-dependency sandbox mirroring Microsoft Graph · GitHub · Jira · Slack &nbsp;
     <span class="pill">RUNNING</span></p>
</header>
<div class="wrap">
  <div class="stats">
    <div class="stat"><b>{n['calendar']}</b><span>calendar events</span></div>
    <div class="stat"><b>{n['prs']}</b><span>pull requests</span></div>
    <div class="stat"><b>{blocked}/{n['jira']}</b><span>jira blocked</span></div>
    <div class="stat"><b>{n['emails']}</b><span>emails</span></div>
    <div class="stat"><b>{n['timesheet']}</b><span>timesheet rows</span></div>
  </div>
  <table>
    <tr><th>Method</th><th>Path</th><th>Skill (operationId)</th><th>Serves</th></tr>
    {tr}
  </table>
  <p style="margin-top:20px;color:#8b949e;font-size:13px">
    BetterWorldWithAI · IBM watsonx Challenge 2026 · point Orchestrate skill
    connections (or <code>curl</code>) at this base URL.
  </p>
</div>
</body></html>"""


# ---------------------------------------------------------------------------
# HTTP request routing
# ---------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    server_version = "AdminZeroMock/1.0"

    # --- response helpers ---------------------------------------------------
    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, status: int, text: str, ctype: str) -> None:
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if not length:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def log_message(self, fmt: str, *args) -> None:  # noqa: A003
        sys.stderr.write(f"[mock] {self.address_string()} {fmt % args}\n")

    # --- routing ------------------------------------------------------------
    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path   = parsed.path
        query  = parse_qs(parsed.query)

        if path in ("/", "/index.html"):
            return self._send_text(200, _index_html(), "text/html; charset=utf-8")

        if path == "/openapi.yaml":
            if os.path.exists(SWAGGER_PATH):
                with open(SWAGGER_PATH, encoding="utf-8") as fh:
                    return self._send_text(200, fh.read(), "text/yaml; charset=utf-8")
            return self._send_json(404, {"error": {"message": "swagger.yaml not found"}})

        if path in ("/health", "/healthz"):
            return self._send_json(200, {"status": "ok", "time": _iso_now()})

        if path == "/me/calendarView":
            return self._send_json(*handle_calendar_view(query))

        if path == "/me/messages":
            return self._send_json(*handle_messages(query))

        if path == "/search":
            return self._send_json(*handle_jira_search(query))

        m = re.fullmatch(r"/repos/([^/]+)/([^/]+)/pulls", path)
        if m:
            return self._send_json(*handle_pull_requests(m.group(1), m.group(2), query))

        m = re.fullmatch(r"/repos/([^/]+)/([^/]+)/pulls/(\d+)", path)
        if m:
            return self._send_json(*handle_pr_details(m.group(1), m.group(2), int(m.group(3))))

        self._send_json(404, {"error": {"code": "notFound",
                                        "message": f"No mock route for GET {path}"}})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path   = parsed.path
        body   = self._read_body()

        if path == "/chat.postMessage":
            return self._send_json(*handle_slack_post(body))

        if re.fullmatch(r"/me/drive/items/[^/]+/workbook/worksheets/[^/]+/tables/[^/]+/rows", path):
            return self._send_json(*handle_write_timesheet(body))

        self._send_json(404, {"error": {"code": "notFound",
                                        "message": f"No mock route for POST {path}"}})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    global STORE
    parser = argparse.ArgumentParser(description="AdminZero local mock API server")
    parser.add_argument("--host", default="127.0.0.1", help="bind host (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="bind port (default 8080)")
    args = parser.parse_args()

    STORE = DataStore()

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    base = f"http://{args.host}:{args.port}"
    print("\n" + "=" * 60)
    print("  AdminZero · Local Mock API Server")
    print("  BetterWorldWithAI · IBM watsonx Challenge 2026")
    print("=" * 60)
    print(f"  Base URL   : {base}")
    print(f"  Index      : {base}/")
    print(f"  Skill spec : {base}/openapi.yaml")
    print(f"  Datasets   : {len(STORE.calendar)} events · {len(STORE.pull_requests)} PRs · "
          f"{len(STORE.jira)} jira · {len(STORE.emails)} emails · {len(STORE.timesheet)} ts-rows")
    print("  Ctrl+C to stop.")
    print("=" * 60 + "\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[mock_server] shutting down.")
        httpd.shutdown()


if __name__ == "__main__":
    main()
