# Wohnungsanmeldung Bot

Monitors the Ingolstadt Buergeramt (TEVIS) booking system for early
Wohnungsanmeldung appointment slots and sends an email alert when a slot
becomes available within the next 7 days.

## How it works

```
cron-job.org (every N minutes)
    -> HTTP POST to GitHub API webhook URL
    -> triggers workflow_dispatch on this repo
    -> GitHub Actions runs wohnung_bot.py
    -> email sent if a slot is found within 7 days
```

The script uses Selenium with headless Chrome to navigate the TEVIS
booking flow (which requires session based navigation, not direct URLs),
selects the Wohnungsanmeldung service (`button-plus-246`), and reads the
next available appointment date from the result page.

## Files

- `wohnung_bot.py` - main script
- `requirements.txt` - Python dependencies
- `.github/workflows/wohnung_bot.yml` - GitHub Actions workflow (workflow_dispatch only)

## Setup

### 1. GitHub Secrets

In the repo settings, add these secrets:

| Secret        | Description                          |
|----------------|---------------------------------------|
| `SMTP_USER`   | Gmail address used to send the alert  |
| `SMTP_PASS`   | Gmail app password                    |
| `ALERT_EMAIL` | Email address to receive alerts       |

### 2. Create a GitHub Personal Access Token

- GitHub -> Settings -> Developer settings -> Personal access tokens -> Tokens (classic)
- Generate new token, scope `repo` (or just `workflow`)
- Copy the token

### 3. Set up cron-job.org

- Create a new cronjob with:
  - **URL:** `https://api.github.com/repos/vishaltala/Wohnung-Anmeldung-Bot/actions/workflows/wohnung_bot.yml/dispatches`
  - **Method:** POST
  - **Headers:**
    ```
    Authorization: Bearer YOUR_GITHUB_TOKEN
    Accept: application/vnd.github.v3+json
    Content-Type: application/json
    ```
  - **Body:**
    ```json
    {"ref": "main"}
    ```
  - **Schedule:** every 10-15 minutes

### 4. Test

Click "Run now" in cron-job.org, then check the Actions tab of the repo
for the workflow run and its logs.

## Notes

- The booking page is shared across services. Only the service ID button
  differs (`button-plus-246` for Wohnungsanmeldung vs `button-plus-255`
  for passport/Eintragung).
- An alert is sent only when the next available date is within 7 days
  of today.
