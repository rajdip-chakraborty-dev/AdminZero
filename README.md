# AdminZero — Enterprise Co-Pilot

> **IBM watsonx Challenge 2026 · Team: BetterWorldWithAI**

---

## Vision

Modern enterprise workers lose significant productive hours each week to two categories of invisible friction:

| Friction Type | Manifestation | Cost |
|---|---|---|
| **Administrative Friction** | Manually logging meeting hours, reconciling calendar entries, and submitting timesheets every Friday | ~3–4 hrs/week per employee |
| **Operational Friction** | Context-switching across GitHub, Outlook, Jira, and Slack to understand what is blocked, urgent, or overdue | ~5–6 hrs/week per knowledge worker |

**AdminZero** is a unified **Enterprise Co-Pilot** deployed on **IBM watsonx Orchestrate** that eliminates both categories simultaneously through intelligent, conversational automation powered by large language models and native enterprise integrations.

---

## The Two Pillars

### Pillar 1 — Administrative Friction Solver: Automated Time Tracking

**The Problem:** Every Friday, employees across thousands of enterprises must manually reconstruct their week — cross-referencing Outlook Calendar, Teams meetings, and Slack messages — to fill in a timesheet. This is low-value, error-prone, and universally despised.

**The Solution:** AdminZero automates the full Friday time-tracking pipeline:

1. **Microsoft Graph API** pulls the authenticated user's Outlook Calendar meeting entries for the current work week (titles, durations, attendee lists, project tags).
2. An **IBM watsonx LLM** maps each meeting to a cost centre or project code using natural language classification.
3. The classified hours are **written back to a Microsoft Excel timesheet** (via Graph API `PATCH /workbook/worksheets`) with zero manual input.
4. A **Slack notification** is sent to the employee's DM confirming the submission and surfacing any ambiguous entries that need a single-click human confirmation.

**Key Integrations:** Microsoft Graph (Outlook Calendar, Excel), Slack Incoming Webhooks, watsonx.ai (LLM classification).

---

### Pillar 2 — Operational Friction Solver: All-in-One Productivity Agent

**The Problem:** A typical engineer or product manager must visit 3–5 tools every morning to understand the state of their world: checking GitHub for open PRs, scanning Outlook for escalations, and pulling up Jira to find what is blocking the sprint.

**The Solution:** AdminZero provides a **single conversational interface** — accessible via Slack or a web chat — where users ask natural-language questions and receive synthesised answers:

| User Prompt | Agent Behaviour |
|---|---|
| `"What PRs need my review?"` | Queries GitHub REST API, returns open PRs assigned to user with age and status |
| `"Summarise my unread emails from this morning"` | Calls Microsoft Graph `/me/messages`, runs summarisation LLM chain |
| `"What's blocking the Q2 sprint?"` | Hits Jira REST API, filters `status=Blocked` issues, returns structured summary |
| `"Log this week's hours for me"` | Triggers the Pillar 1 pipeline end-to-end |

All answers are delivered in a single, coherent Slack thread — eliminating tab-switching entirely.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        User Interface Layer                          │
│              Slack Bot  ·  watsonx Orchestrate Chat UI               │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ Natural Language Input
┌──────────────────────────▼──────────────────────────────────────────┐
│                   IBM watsonx Orchestrate                            │
│   Skill Router (OpenAPI-backed skills)  ·  LLM Reasoning Engine      │
└──┬───────────────┬─────────────────┬────────────────┬───────────────┘
   │               │                 │                │
   ▼               ▼                 ▼                ▼
Microsoft       GitHub           Jira Cloud       Slack API
Graph API       REST API         REST API         Webhooks / Bot
(Outlook,Excel)
```

### Skill Inventory (watsonx Orchestrate)

| Skill Name | Backing API | Method | Description |
|---|---|---|---|
| `get_calendar_events` | Microsoft Graph | GET | Fetch calendar events in a date range |
| `write_timesheet_row` | Microsoft Graph | PATCH | Write classified hours to Excel workbook |
| `get_open_pull_requests` | GitHub REST | GET | List open PRs for a repo or user |
| `get_pr_details` | GitHub REST | GET | Get diff summary and reviewers for a PR |
| `summarise_emails` | Microsoft Graph + watsonx.ai | GET+LLM | Fetch and summarise unread email threads |
| `get_jira_blockers` | Jira REST | GET | Fetch open issues with status=Blocked |
| `send_slack_message` | Slack API | POST | Post a formatted summary to a DM or channel |

---

## Repository Structure

```
AdminZero/
├── README.md                         ← This file
├── .gitignore                        ← Python-specific ignores
│
├── sandbox_setup/
│   └── generate_dummy_data.py        ← Generates all mock data fixtures
│       ├── output/calendar_events.json
│       ├── output/timesheet_ledger.csv
│       ├── output/github_pull_requests.json
│       └── output/jira_tickets.json
│
└── orchestrate_skills/
    └── swagger.yaml                  ← OpenAPI 3.0 skill spec for watsonx Orchestrate
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Co-Pilot Platform** | IBM watsonx Orchestrate |
| **LLM Backend** | IBM watsonx.ai (`ibm/granite-13b-chat-v2`) |
| **Calendar & Email** | Microsoft Graph API v1.0 |
| **Spreadsheet Write-Back** | Microsoft Graph Excel REST API |
| **Source Control Integration** | GitHub REST API v3 |
| **Project Management** | Jira Cloud REST API v3 |
| **Notification Channel** | Slack API (Bot Token + Webhooks) |
| **Skill Definition** | OpenAPI 3.0 (swagger.yaml) |
| **Mock Data / Scripting** | Python 3.11+ |

---

## Quick Start

### Prerequisites

- Python 3.11+
- IBM watsonx Orchestrate instance (trial or enterprise)
- Azure AD App Registration (for Microsoft Graph permissions: `Calendars.Read`, `Files.ReadWrite`, `Mail.Read`)
- GitHub Personal Access Token (`repo` scope)
- Jira API Token
- Slack Bot Token (`chat:write`, `im:write`)

### 1. Generate Mock Data

```bash
cd sandbox_setup
pip install faker
python generate_dummy_data.py
# Output files written to sandbox_setup/output/
```

### 2. Register Skills in watsonx Orchestrate

1. Log in to your IBM watsonx Orchestrate instance.
2. Navigate to **Skills → Add Skill → From API (OpenAPI)**.
3. Upload `orchestrate_skills/swagger.yaml`.
4. Authenticate each connection (Microsoft OAuth2, GitHub PAT, Jira Basic Auth, Slack Bot Token).
5. Enable the skills for your personal assistant or a shared team assistant.

### 3. Test via Chat

Ask your assistant:

```
"Log my hours for this week based on my calendar."
"Show me all open PRs waiting for my review."
"What Jira tickets are blocking the current sprint?"
"Summarise my unread emails from the last 24 hours."
```

---

## Team

| Name | Role |
|---|---|
| **BetterWorldWithAI** | IBM watsonx Challenge 2026 — Team |

---

## License

MIT License. See `LICENSE` for details.

---

> *"The best admin work is the work nobody has to do."*
> — AdminZero Team, 2026
