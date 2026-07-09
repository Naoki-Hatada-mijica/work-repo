---
name: html-share
description: Publish generated HTML reports or local .html/.htm files to the user's internal HTML Share Google Apps Script service and return a share URL. Use when Codex creates an HTML report, dashboard, analysis artifact, preview page, or any HTML file that the user wants to view or share by URL instead of opening a local file.
---

# HTML Share

Use this skill when an HTML deliverable should be accessible by URL.

## Workflow

1. Create or update the HTML artifact as a real `.html` file.
2. Prefer a concise, human-readable title. Use the report title, task name, or filename.
3. Publish with the bundled script:

```bash
python3 "$HOME/.claude/skills/html-share/scripts/publish_html.py" \
  /path/to/report.html \
  --title "Report title" \
  --description "Short context" \
  --visibility company
```

4. Return the share URL to the user. Mention the local file path only when it is useful.

## Defaults

- Use `--visibility company` unless the user asks for link sharing or external temporary sharing.
- Use `--visibility link` only when anyone with the link inside the intended audience may view it.
- Use `--visibility external` only when the user clearly asks for external sharing.
- Do not set a password unless the user asks or the content is sensitive.
- Do not set an expiry unless the user asks or the content is temporary.

## Configuration

The script reads credentials in this order:

1. `HTML_SHARE_WEB_APP_URL` and `HTML_SHARE_ADMIN_TOKEN`
2. `~/.config/html_share/config.json`

Never print or commit the admin token. If publishing fails because config is missing, ask the user to set the config or locate the project `.gas-deploy.json` and create the local config.

Expected local config format:

```json
{
  "webAppUrl": "https://script.google.com/macros/s/.../exec",
  "adminToken": "..."
}
```

## Output

For normal usage, the script prints only the share URL. Use `--json` when the asset URLs or embed code are needed programmatically.

If the report was generated during a task, include the URL in the final answer:

```text
HTMLレポートを共有しました: https://script.google.com/macros/s/.../exec/s/...
```
