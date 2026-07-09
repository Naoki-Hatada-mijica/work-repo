---
name: techdirect-projects-picker
description: TechDirectの案件管理シートから先週分の案件を最大3件ピックし、シートにチェック・Slackスレッドに通知する。TechDirect案件ピック・案件選択を行う場合に使用する。
---

## 概要

TechDirect案件管理シートから先週（日〜土）作成の未処理案件を最大3件選択し、D列にチェックを付けた後、Slackスレッドに結果を通知する。

## 実行手順

### ステップ1: 案件ピック

以下のPythonスクリプトを実行する:

```bash
python3 ~/.claude/skills/techdirect-projects-picker/scripts/pick_cases.py
```

ドライラン（書き込みなしで選択結果のみ確認）:
```bash
python3 ~/.claude/skills/techdirect-projects-picker/scripts/pick_cases.py --dry-run
```

### ステップ2: Slack通知

スクリプトの出力からURL一覧を取得し、以下のスレッドにメッセージを送信する:
- チャンネルID: `C08SMK9UMFV`
- スレッドts: `1763344709.968839`

メッセージ形式:
```
<@U09J9FJHKJ4>
チェック付けました！お願いします。
- {B列の案件タイトル_1}
- {B列の案件タイトル_2}
- ...
```

`slack_send_message` ツールを使用し、`thread_ts` を指定してスレッド返信として送信する。

## 選択ロジック

### 対象シート
- スプレッドシートID: `1PStuFVOUtRM_zLhKJVElG-5uM-deGT5v3Lmd0cyGdwI`
- gid=0（デフォルトシート）

### 列構成
| 列 | 内容 |
|----|------|
| A | 日付（案件作成日） |
| B | 案件タイトル |
| C | URL |
| D | チェックボックス（ピック済みフラグ） |
| E | 商流（エンド/元請/BP） |

### 対象条件
- A列の日付が先週（日曜〜土曜）に該当する
- D列が空（未チェック）

### 優先度
1. 商流（E列）: エンド > 元請 > BP
2. 優先スキル: B列に Python, TypeScript, Go, AWS, Ruby, Kotlin, Swift, iOS, AI, 機械学習, React, Next, Node, Django, FastAPI, GCP, SRE, Android, PM, PdM を含む案件を優先
3. 同順: 行番号が大きい（新しい）ものを優先

### 多様性制約
- 同一言語カテゴリの案件は最大4件まで
- 4件を超える場合はスキップし、他カテゴリの案件を優先

## 認証
- Google Sheets: `~/.config/claude-gdocs-token.json` のOAuth2トークン（driveスコープ）
- Slack: MCP Slackツール経由

## 関連資料

TechDirect Web 画面を参照・再調査する場合は次を確認する。

- 共通helper: `~/.claude/snippets/techdirect/`
- ページ/APIカタログ: `~/.claude/docs/techdirect/pages.md`
- カラム/選択肢カタログ: `~/.claude/docs/techdirect/column-catalog.md`
- フィールド/選択肢カタログ: `~/.claude/docs/techdirect/field-catalog.md`
- 危険アクション境界: `~/.claude/docs/techdirect/danger-actions.md`
