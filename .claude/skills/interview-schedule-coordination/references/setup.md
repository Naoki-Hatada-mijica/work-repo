# Google カレンダー連携セットアップ（初回のみ）

このスキルは Google Calendar API 連携で動く。以下は 2026-07-10 に構築済みの構成。
再構築が必要になった場合の手順・注意点をここに残す。

## 構成（構築済み）

- Google Cloud プロジェクト：`interview-scheduler`（ID: `interview-scheduler-502002`、組織 mijica.co.jp）
- Google Calendar API：有効化済み
- OAuth 同意画面：**内部（Internal）** → 審査不要
- OAuth クライアント：**デスクトップアプリ**型
- スコープ：`https://www.googleapis.com/auth/calendar`（読み書き・削除可）
- 対象カレンダー：`primary`（畑田 真輝 / Asia/Tokyo）

## 秘密情報・実行環境の置き場所（リポジトリ外）

すべて `~/.config/interview-scheduler/` に置く（本人のみ 600/700 権限）。**リポジトリには絶対に置かない・コミットしない。**

- `~/.config/interview-scheduler/client_secret.json` — OAuth クライアント（作成時に DL）
- `~/.config/interview-scheduler/token.json` — 初回認証で生成
- `~/.config/interview-scheduler/venv` — Python 実行環境（`google-api-python-client` `google-auth-oauthlib` 等）

## 初回・再認証

トークンが無い／切れている場合：

```bash
~/.config/interview-scheduler/venv/bin/python scripts/gcal_auth.py
```

ローカルサーバが立ち上がり、本人のブラウザで承認 → `token.json` が生成される。

## ハマりどころ

- **認証 JSON（client_secret）は作成時のポップアップでしか DL できない**（後から表示・DL 不可）。自動化タブ（claude-in-chrome）では DL がブロックされるため、**ユーザー本人の通常ブラウザで作成→その場で DL**する必要がある。
- **freebusy は UTC の 'Z' 表記で返ることがある** → JST に正規化が必要（`gcal_common.py` で対応済み）。
- Python 3.9 は EOL 警告（FutureWarning）が出るが動作に支障なし。
