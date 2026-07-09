"""Google OAuth再認可スクリプト.

~/.config/claude-gdocs-credentials.json を使って、
Docs/Drive/Gmail readonly スコープ込みの新しい token を発行する。

実行方法（ブラウザが立ち上がります）:
    python3 ~/.claude/snippets/reauth_google.py

前提:
    - ~/.config/claude-gdocs-credentials.json が存在すること
    - 対応するGCPプロジェクトで以下APIが有効化されていること:
        - Google Docs API
        - Google Drive API
        - Gmail API  ← 追加で有効化が必要
    - OAuth同意画面のスコープに gmail.readonly が含まれていること
"""

import json
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

CREDENTIALS_PATH = Path.home() / ".config" / "claude-gdocs-credentials.json"
TOKEN_PATH = Path.home() / ".config" / "claude-gdocs-token.json"

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/gmail.readonly",
]


def main():
    if not CREDENTIALS_PATH.exists():
        raise SystemExit(f"credentials not found: {CREDENTIALS_PATH}")

    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent")

    TOKEN_PATH.write_text(
        json.dumps(
            {
                "token": creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri": creds.token_uri,
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "scopes": list(creds.scopes),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    print(f"✅ token saved: {TOKEN_PATH}")
    print(f"   scopes: {creds.scopes}")


if __name__ == "__main__":
    main()
