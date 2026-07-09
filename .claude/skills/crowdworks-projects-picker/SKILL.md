---
name: crowdworks-projects-picker
description: クラウドワークスのスカウト用案件管理シートから毎日3件の案件をピックし、シートに記入する。案件ピック・クラウドワークス案件選択を行う場合に使用する。
---

## 概要

「スカウト用案件管理」シートから未処理の案件を3件選択し、B/C/D列に記入した後、Slackスレッドに結果を通知する。

土日・日本の祝日はスクリプトが早期 return するため、シート書き込み・Slack通知ともに行われず、週上限カウント（WEEKLY_CAP=12）も消費されない。

## 実行手順

### ステップ1: 案件ピック

以下のPythonスクリプトを実行する:

```bash
python3 ~/.claude/skills/crowdworks-projects-picker/scripts/pick_cases.py
```

ドライラン（書き込みなしで選択結果のみ確認）:
```bash
python3 ~/.claude/skills/crowdworks-projects-picker/scripts/pick_cases.py --dry-run
```

### ステップ2: Slack通知

スクリプトの出力から案件NOを取得し、以下のスレッドにメッセージを送信する:
- チャンネルID: `C08SMK9UMFV`
- スレッドts: `1760520785.812989`

メッセージ形式:
```
<@U09J9FJHKJ4>
お願いします！
- {案件NO1}
- {案件NO2}
- {案件NO3}
```

`slack_send_message` ツールを使用し、`thread_ts` を指定してスレッド返信として送信する。

## 選択ロジック

### 対象シート
- スプレッドシートID: `1_J2UsFr8JeUsDCxforI8Fkaf7CgfY9gsVGZuLF6VgFM`
- シート名: `スカウト用案件管理`

### 未処理行の条件
- A列（案件NO）が存在する
- E列（メインスキル）が存在する
- B列が空、C列がFALSE、D列が空

### 優先度
1. A列の背景色: 青 > 赤 > 白
2. 同色内: E/F列に優先スキル（Python, TypeScript, Go, AWS, Ruby, Kotlin, Swift, iOS, AI・機械学習）を含む案件を優先
3. 同順: 行番号が大きい（新しい）ものを優先

### 記入内容
- B列: 今日の日付（yyyy/mm/dd）
- C列: TRUE（チェックボックスON）
- D列: open

## 認証
- Google Sheets: `~/.config/claude-gdocs-token.json` のOAuth2トークン（driveスコープ）
- Slack: MCP Slackツール経由
