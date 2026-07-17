"""
generate_dummy_data.py
======================
AdminZero · BetterWorldWithAI · IBM watsonx Challenge 2026

Generates four realistic mock dataset files used for local development,
demo walkthroughs, and watsonx Orchestrate skill testing:

  output/calendar_events.json        – Microsoft Outlook Calendar meeting entries
  output/timesheet_ledger.csv        – Microsoft Excel-style timesheet ledger
  output/github_pull_requests.json   – Active GitHub Pull Request payloads
  output/jira_tickets.json           – Open Jira project bug / blocker tickets
  output/outlook_emails.json         – Microsoft Outlook unread email messages

Dependencies:
    pip install faker

Usage:
    python generate_dummy_data.py
"""

from __future__ import annotations

import csv
import json
import os
import random
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# Optional faker dependency — graceful fallback to built-in word lists
# ---------------------------------------------------------------------------
try:
    from faker import Faker
    _faker = Faker()
    _USE_FAKER = True
except ImportError:
    _USE_FAKER = False
    print("[WARN] 'faker' not installed. Using built-in word lists. "
          "Run `pip install faker` for richer data.")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")

TEAM_MEMBERS = [
    {"name": "Rajdip Chakraborty",   "email": "rajdip.chakraborty@betterworld.ai"},
    {"name": "Priya Nair",           "email": "priya.nair@betterworld.ai"},
    {"name": "Marcus Silva",         "email": "marcus.silva@betterworld.ai"},
    {"name": "Anya Petrov",          "email": "anya.petrov@betterworld.ai"},
    {"name": "David Okonkwo",        "email": "david.okonkwo@betterworld.ai"},
    {"name": "Selin Yilmaz",         "email": "selin.yilmaz@betterworld.ai"},
    {"name": "Thomas Braun",         "email": "thomas.braun@betterworld.ai"},
    {"name": "Mei Lin",              "email": "mei.lin@betterworld.ai"},
]

PROJECT_CODES = ["PROJ-ALPHA", "PROJ-BETA", "PROJ-GAMMA", "PROJ-DELTA", "INTERNAL", "OVERHEAD"]

MEETING_TEMPLATES = [
    "Sprint Planning – {project}",
    "Q{quarter} Business Review",
    "Architecture Sync: {component} Redesign",
    "1:1 with {manager}",
    "Stakeholder Demo – {project} Release",
    "Incident Post-Mortem: {service} Outage",
    "Cross-Functional Alignment – {project}",
    "Hiring Panel: {role} Candidate",
    "Product Roadmap Review",
    "Onboarding Session – {new_hire}",
    "OKR Check-in: Q{quarter} Milestone Review",
    "Security Review: {component} Audit",
    "Customer Success Sync – {customer}",
    "Budget Planning: {quarter} Forecast",
    "AI Ethics Review Board",
    "watsonx Orchestrate Integration Demo",
    "AdminZero Co-Pilot Launch Readiness",
]

COMPONENTS = ["Auth Service", "Payment Gateway", "Notification Engine",
              "Data Pipeline", "ML Inference API", "Orchestrate Skills Layer"]
SERVICES   = ["prod-api", "data-ingestion", "auth-svc", "billing-worker"]
ROLES      = ["Senior SWE", "Product Manager", "ML Engineer", "DevOps Lead"]
CUSTOMERS  = ["Acme Corp", "GlobalBank Ltd", "HealthNet Inc", "RetailFirst Group"]

PR_TITLE_TEMPLATES = [
    "feat({scope}): add {feature} endpoint",
    "fix({scope}): resolve {bug} race condition",
    "refactor({scope}): extract {component} into shared module",
    "chore(deps): bump {lib} from {v1} to {v2}",
    "feat({scope}): integrate watsonx Orchestrate skill for {action}",
    "fix({scope}): handle null response from {service} API",
    "docs({scope}): update README with {topic} setup guide",
    "test({scope}): add unit tests for {component} parser",
    "perf({scope}): cache {resource} to reduce Graph API calls",
    "ci: add {tool} workflow for automated skill validation",
]

EMAIL_SUBJECT_TEMPLATES = [
    "Re: {project} timeline slipping — need a call today",
    "Action required: approve Q{quarter} budget by EOD",
    "Escalation: {customer} reported {service} degradation",
    "Review request: PR for {component} is blocking the release",
    "FYI — watsonx Orchestrate trial credentials provisioned",
    "Reminder: submit your weekly timesheet before Friday 5pm",
    "Meeting notes: {project} architecture sync",
    "Question about the {component} OAuth scopes",
    "Weekly digest: {project} sprint progress",
    "Invite: {customer} stakeholder demo next week",
    "Heads up: {service} maintenance window this weekend",
    "Follow-up: onboarding checklist for new hire",
]

JIRA_SUMMARY_TEMPLATES = [
    "[BLOCKER] {service} integration returns 401 on OAuth token refresh",
    "[BUG] Calendar events missing timezone offset in Graph API response",
    "[BLOCKER] Slack webhook silently drops messages > 3000 chars",
    "[BUG] Timesheet write-back fails when Excel workbook is open in browser",
    "[BLOCKER] Jira API rate-limit hit during bulk ticket fetch for large sprints",
    "[BUG] GitHub PR list pagination breaks on repos with > 100 open PRs",
    "[BLOCKER] watsonx Orchestrate skill auth token not refreshing after 1h",
    "[BUG] LLM classification maps 'All-hands meeting' to wrong cost centre",
    "[BLOCKER] Microsoft Graph `/me/events` returns empty array for service account",
    "[BUG] PR summary truncated for diffs exceeding context window limit",
    "[BLOCKER] Jira project key lookup fails for archived sprints",
    "[BUG] Outlook email summarisation strips inline code blocks",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rand_name() -> str:
    if _USE_FAKER:
        return _faker.name()
    return random.choice(TEAM_MEMBERS)["name"]

def _rand_sentence(words: int = 12) -> str:
    if _USE_FAKER:
        return _faker.sentence(nb_words=words)
    nouns = ["pipeline", "endpoint", "service", "client", "token", "schema",
             "workflow", "payload", "response", "integration", "handler"]
    verbs = ["processes", "validates", "serialises", "authenticates",
             "fetches", "transforms", "routes", "caches"]
    return " ".join(random.choices(nouns + verbs, k=words)).capitalize() + "."

def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + "Z"

def _week_start(ref: datetime) -> datetime:
    """Return Monday 09:00 UTC of the week containing `ref`."""
    monday = ref - timedelta(days=ref.weekday())
    return monday.replace(hour=9, minute=0, second=0, microsecond=0)

def _meeting_title() -> str:
    tpl = random.choice(MEETING_TEMPLATES)
    return tpl.format(
        project=random.choice(PROJECT_CODES),
        quarter=random.randint(1, 4),
        component=random.choice(COMPONENTS),
        manager=random.choice(TEAM_MEMBERS)["name"].split()[0],
        service=random.choice(SERVICES),
        role=random.choice(ROLES),
        new_hire=random.choice(TEAM_MEMBERS)["name"],
        customer=random.choice(CUSTOMERS),
    )

def _pr_title() -> str:
    tpl = random.choice(PR_TITLE_TEMPLATES)
    scopes   = ["calendar", "timesheet", "github-skill", "jira-skill", "slack-notifier", "auth"]
    features = ["bulk-fetch", "token-refresh", "rate-limit-retry", "streaming-response"]
    bugs     = ["null-pointer", "off-by-one", "memory-leak", "deadlock"]
    libs     = [("requests", "2.28.2", "2.31.0"), ("pydantic", "1.10.4", "2.6.0"),
                ("httpx", "0.23.0", "0.27.0"), ("aiohttp", "3.8.1", "3.9.3")]
    lib      = random.choice(libs)
    actions  = ["email-summarisation", "timesheet-write-back", "pr-listing", "jira-blockers"]
    resources= ["calendar-events", "pr-list", "email-threads", "jira-issues"]
    topics   = ["OAuth2", "watsonx Orchestrate", "Microsoft Graph", "GitHub PAT"]
    tools    = ["ruff", "mypy", "pytest", "bandit"]
    return tpl.format(
        scope=random.choice(scopes),
        feature=random.choice(features),
        bug=random.choice(bugs),
        component=random.choice(COMPONENTS),
        lib=lib[0], v1=lib[1], v2=lib[2],
        action=random.choice(actions),
        service=random.choice(SERVICES),
        resource=random.choice(resources),
        topic=random.choice(topics),
        tool=random.choice(tools),
    )


# ---------------------------------------------------------------------------
# Generator 1 — Outlook Calendar Events (JSON)
# ---------------------------------------------------------------------------

def generate_calendar_events(n: int = 25, ref: datetime | None = None) -> list[dict]:
    """
    Simulate Microsoft Graph API `GET /me/calendarView` response items.
    One full work-week worth of meetings for the current user.
    """
    if ref is None:
        ref = datetime.now(timezone.utc)

    week_mon = _week_start(ref)
    events   = []

    for i in range(n):
        day_offset    = random.randint(0, 4)          # Mon–Fri
        hour_offset   = random.randint(0, 7)          # 09:00–16:00
        duration_mins = random.choice([30, 45, 60, 90, 120])
        start_dt      = week_mon + timedelta(days=day_offset, hours=hour_offset)
        end_dt        = start_dt + timedelta(minutes=duration_mins)

        attendees = random.sample(TEAM_MEMBERS, k=random.randint(2, 6))
        project   = random.choice(PROJECT_CODES)

        events.append({
            "id": f"AAMkADc{random.randint(10000, 99999)}==",
            "subject": _meeting_title(),
            "start": {
                "dateTime": _iso(start_dt),
                "timeZone": "UTC"
            },
            "end": {
                "dateTime": _iso(end_dt),
                "timeZone": "UTC"
            },
            "durationMinutes": duration_mins,
            "organizer": {
                "emailAddress": {
                    "name": random.choice(TEAM_MEMBERS)["name"],
                    "address": random.choice(TEAM_MEMBERS)["email"]
                }
            },
            "attendees": [
                {
                    "emailAddress": {"name": a["name"], "address": a["email"]},
                    "status": {"response": random.choice(["accepted", "tentativelyAccepted", "none"])}
                }
                for a in attendees
            ],
            "isOnlineMeeting": random.choice([True, False]),
            "onlineMeetingProvider": random.choice(["teamsForBusiness", "unknown"]),
            "categories": [project],
            "importance": random.choice(["normal", "high"]),
            "sensitivity": "normal",
            "projectCode": project,   # synthetic field for AdminZero skill
        })

    # Sort by start time for realism
    events.sort(key=lambda e: e["start"]["dateTime"])
    return events


# ---------------------------------------------------------------------------
# Generator 2 — Excel Timesheet Ledger (CSV)
# ---------------------------------------------------------------------------

def generate_timesheet_ledger(n_employees: int = 8,
                               ref: datetime | None = None) -> list[dict]:
    """
    Simulate a Microsoft Excel timesheet with one row per employee-day-project.
    """
    if ref is None:
        ref = datetime.now(timezone.utc)

    week_mon = _week_start(ref)
    rows     = []
    row_id   = 1

    for employee in TEAM_MEMBERS[:n_employees]:
        # Each employee has 5 work days
        daily_hours: dict[str, float] = {}
        for day in range(5):
            date_str = (week_mon + timedelta(days=day)).strftime("%Y-%m-%d")
            remaining = 8.0
            projects  = random.sample(PROJECT_CODES, k=random.randint(1, 3))
            for j, proj in enumerate(projects):
                if j == len(projects) - 1:
                    hours = round(remaining, 2)
                else:
                    hours = round(random.uniform(1.0, remaining - (len(projects) - j - 1)), 2)
                    remaining = round(remaining - hours, 2)

                rows.append({
                    "RowID":        row_id,
                    "EmployeeName": employee["name"],
                    "EmployeeEmail":employee["email"],
                    "Date":         date_str,
                    "DayOfWeek":    (week_mon + timedelta(days=day)).strftime("%A"),
                    "ProjectCode":  proj,
                    "TaskCategory": random.choice(["Development", "Meetings", "Review",
                                                   "Documentation", "Planning", "Support"]),
                    "HoursLogged":  hours,
                    "Notes":        _rand_sentence(8),
                    "Submitted":    random.choice([True, False]),
                    "ApprovedBy":   random.choice(TEAM_MEMBERS)["name"] if random.random() > 0.4 else "",
                })
                row_id += 1

    return rows


# ---------------------------------------------------------------------------
# Generator 3 — GitHub Pull Requests (JSON)
# ---------------------------------------------------------------------------

def generate_github_prs(n: int = 15) -> list[dict]:
    """
    Simulate GitHub REST API `GET /repos/{owner}/{repo}/pulls` response items.
    """
    repos = [
        "BetterWorldWithAI/AdminZero",
        "BetterWorldWithAI/orchestrate-skills-lib",
        "BetterWorldWithAI/graph-api-connector",
        "BetterWorldWithAI/jira-skill-adapter",
        "BetterWorldWithAI/slack-notifier-bot",
    ]
    labels_pool = [
        {"name": "enhancement",   "color": "84b6eb"},
        {"name": "bug",           "color": "d73a4a"},
        {"name": "documentation", "color": "0075ca"},
        {"name": "needs-review",  "color": "e4e669"},
        {"name": "blocked",       "color": "b60205"},
        {"name": "watsonx",       "color": "6f42c1"},
    ]

    prs = []
    for i in range(1, n + 1):
        created_at = datetime.now(timezone.utc) - timedelta(days=random.randint(0, 14),
                                                             hours=random.randint(0, 23))
        author     = random.choice(TEAM_MEMBERS)
        reviewers  = random.sample([m for m in TEAM_MEMBERS if m != author], k=random.randint(1, 3))
        repo       = random.choice(repos)

        prs.append({
            "id":     1000 + i,
            "number": 100 + i,
            "title":  _pr_title(),
            "state":  "open",
            "draft":  random.random() < 0.15,
            "html_url": f"https://github.com/{repo}/pull/{100 + i}",
            "repository": repo,
            "user": {
                "login": author["email"].split("@")[0].replace(".", "_"),
                "name":  author["name"],
                "email": author["email"],
            },
            "body": _rand_sentence(20),
            "labels": random.sample(labels_pool, k=random.randint(0, 3)),
            "created_at":       _iso(created_at),
            "updated_at":       _iso(created_at + timedelta(hours=random.randint(0, 48))),
            "requested_reviewers": [
                {"login": r["email"].split("@")[0].replace(".", "_"), "name": r["name"]}
                for r in reviewers
            ],
            "review_comments": random.randint(0, 12),
            "commits":         random.randint(1, 20),
            "additions":       random.randint(5, 800),
            "deletions":       random.randint(0, 300),
            "changed_files":   random.randint(1, 25),
            "mergeable":       random.choice([True, False, None]),
            "ci_status":       random.choice(["success", "pending", "failure", "neutral"]),
        })

    prs.sort(key=lambda p: p["created_at"], reverse=True)
    return prs


# ---------------------------------------------------------------------------
# Generator 4 — Jira Project Bug / Blocker Tickets (JSON)
# ---------------------------------------------------------------------------

def generate_jira_tickets(n: int = 20) -> list[dict]:
    """
    Simulate Jira Cloud REST API `GET /rest/api/3/search` (issues) response items.
    """
    projects  = ["ADMZ", "ORCH", "GRAPH", "SLACK", "JIRASK"]
    issue_types = ["Bug", "Story", "Task", "Epic", "Subtask"]
    priorities  = ["Blocker", "Critical", "Major", "Minor", "Trivial"]
    statuses    = ["Blocked", "In Progress", "Open", "Reopened", "Under Review"]
    sprint_names= ["Sprint 1 – Scaffold", "Sprint 2 – Integrations",
                   "Sprint 3 – LLM Wiring", "Sprint 4 – UAT & Hardening"]

    tickets = []
    for i in range(1, n + 1):
        project      = random.choice(projects)
        issue_key    = f"{project}-{random.randint(10, 999)}"
        created_at   = datetime.now(timezone.utc) - timedelta(days=random.randint(1, 30))
        updated_at   = created_at + timedelta(hours=random.randint(1, 72))
        reporter     = random.choice(TEAM_MEMBERS)
        assignee     = random.choice(TEAM_MEMBERS) if random.random() > 0.2 else None
        priority     = random.choice(priorities)
        status       = "Blocked" if priority in ("Blocker", "Critical") and random.random() > 0.3 \
                       else random.choice(statuses)

        tickets.append({
            "id":  str(20000 + i),
            "key": issue_key,
            "self": f"https://betterworld.atlassian.net/rest/api/3/issue/{20000 + i}",
            "fields": {
                "summary":     random.choice(JIRA_SUMMARY_TEMPLATES),
                "description": _rand_sentence(25),
                "issuetype": {
                    "name": "Bug" if "BUG" in random.choice(JIRA_SUMMARY_TEMPLATES) else random.choice(issue_types)
                },
                "priority":    {"name": priority},
                "status": {
                    "name": status,
                    "statusCategory": {
                        "name": "In Progress" if status not in ("Open", "Reopened") else "To Do"
                    }
                },
                "project": {
                    "key":  project,
                    "name": f"AdminZero – {project} Module"
                },
                "reporter": {
                    "displayName": reporter["name"],
                    "emailAddress": reporter["email"]
                },
                "assignee": {
                    "displayName": assignee["name"],
                    "emailAddress": assignee["email"]
                } if assignee else None,
                "labels": random.sample(
                    ["blocker", "watsonx", "graph-api", "slack", "github", "jira-skill",
                     "oauth2", "performance", "security", "regression"],
                    k=random.randint(0, 4)
                ),
                "sprint": {
                    "name": random.choice(sprint_names),
                    "state": random.choice(["active", "future", "closed"])
                },
                "created": _iso(created_at),
                "updated": _iso(updated_at),
                "dueDate":  (_iso(created_at + timedelta(days=random.randint(3, 14)))
                             if random.random() > 0.4 else None),
                "storyPoints": random.choice([1, 2, 3, 5, 8, 13, None]),
                "blockedReason": (_rand_sentence(10) if status == "Blocked" else None),
            }
        })

    return tickets


# ---------------------------------------------------------------------------
# Generator 5 — Outlook Unread Emails (JSON)
# ---------------------------------------------------------------------------

def generate_emails(n: int = 18, ref: datetime | None = None) -> list[dict]:
    """
    Simulate Microsoft Graph API `GET /me/messages` response items.
    Recent (mostly unread) inbox messages for the current user, used by the
    email-summarisation skill (Pillar 2).
    """
    if ref is None:
        ref = datetime.now(timezone.utc)

    messages = []
    for i in range(1, n + 1):
        received  = ref - timedelta(hours=random.randint(0, 72),
                                    minutes=random.randint(0, 59))
        sender    = random.choice(TEAM_MEMBERS)
        subject   = random.choice(EMAIL_SUBJECT_TEMPLATES).format(
            project=random.choice(PROJECT_CODES),
            quarter=random.randint(1, 4),
            component=random.choice(COMPONENTS),
            service=random.choice(SERVICES),
            customer=random.choice(CUSTOMERS),
        )
        messages.append({
            "id":               f"AAMkMSG{random.randint(100000, 999999)}==",
            "subject":          subject,
            "from": {
                "emailAddress": {"name": sender["name"], "address": sender["email"]}
            },
            "receivedDateTime": _iso(received),
            "bodyPreview":      _rand_sentence(18),
            "isRead":           random.random() < 0.25,
            "importance":       random.choice(["normal", "high"]),
            "hasAttachments":   random.random() < 0.3,
            "conversationId":   f"CONV{random.randint(1000, 9999)}",
        })

    messages.sort(key=lambda m: m["receivedDateTime"], reverse=True)
    return messages


# ---------------------------------------------------------------------------
# Write utilities
# ---------------------------------------------------------------------------

def _write_json(data: object, filename: str) -> None:
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    print(f"  [OK] Written {path}  ({len(data)} records)")  # type: ignore[arg-type]


def _write_csv(rows: list[dict], filename: str) -> None:
    if not rows:
        return
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"  [OK] Written {path}  ({len(rows)} rows)")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ref = datetime.now(timezone.utc)

    print("\n╔══════════════════════════════════════════════════════╗")
    print("║  AdminZero · Mock Data Generator                    ║")
    print("║  BetterWorldWithAI · IBM watsonx Challenge 2026     ║")
    print("╚══════════════════════════════════════════════════════╝\n")

    print("➤  Generating Outlook Calendar events …")
    calendar_data = {
        "context":      "https://graph.microsoft.com/v1.0/$metadata#users('me')/calendarView",
        "generatedAt":  _iso(ref),
        "weekStart":    _iso(_week_start(ref)),
        "weekEnd":      _iso(_week_start(ref) + timedelta(days=4, hours=8)),
        "totalEvents":  25,
        "value":        generate_calendar_events(25, ref),
    }
    _write_json(calendar_data["value"], "calendar_events.json")

    print("\n➤  Generating Excel Timesheet ledger …")
    timesheet_rows = generate_timesheet_ledger(8, ref)
    _write_csv(timesheet_rows, "timesheet_ledger.csv")

    print("\n➤  Generating GitHub Pull Requests …")
    pr_data = {
        "generatedAt":    _iso(ref),
        "totalOpenPRs":   15,
        "pull_requests":  generate_github_prs(15),
    }
    _write_json(pr_data["pull_requests"], "github_pull_requests.json")

    print("\n➤  Generating Jira tickets …")
    jira_data = {
        "generatedAt":  _iso(ref),
        "maxResults":   20,
        "total":        20,
        "issues":       generate_jira_tickets(20),
    }
    _write_json(jira_data["issues"], "jira_tickets.json")

    print("\n➤  Generating Outlook unread emails …")
    email_data = generate_emails(18, ref)
    _write_json(email_data, "outlook_emails.json")

    print("\n✔  All mock datasets written to:")
    print(f"   {OUTPUT_DIR}\n")


if __name__ == "__main__":
    main()
