---
name: techdirect-scout-filter
description: TechDirectの候補者一覧から除外対象（年齢超過[デザイナー50歳以上/エンジニア57歳以上]・海外在住・CRM NG人材）を自動判定し、営業対象外リストに追加する。TechDirectスカウト・候補者フィルタリングを行う場合に使用する。
---

## 概要

TechDirectの候補者一覧を自動巡回し、以下の除外条件に該当する候補者を「営業対象外」リストに追加する。結果はSlack Webhookで自動通知される。

- 年齢超過（誕生年から判定。職種別しきい値: デザイナー50歳以上 / エンジニア・その他57歳以上）
- 都道府県が「海外」
- フリーランスベースで営業ステータスが「営業不可」or「取引停止」

## TechDirect 画面/API 参照

画面仕様・詳細画面カラム・選択肢・危険アクション境界は、作業前に必要箇所だけ確認する。

- 共通helper: `~/.claude/snippets/techdirect/`
- ページ/APIカタログ: `~/.claude/docs/techdirect/pages.md`
- カラム/選択肢カタログ: `~/.claude/docs/techdirect/column-catalog.md`
- フィールド/選択肢カタログ: `~/.claude/docs/techdirect/field-catalog.md`
- 危険アクション境界: `~/.claude/docs/techdirect/danger-actions.md`

候補者詳細を開くと既読化相当の `POST /v1/users/{uuid}/orgs/{id}/viewed` が発火する。調査用途では `techdirect.catalog_probe` の route guard を使い、非GETリクエストを abort する。

## 前提条件

以下の環境変数が設定されていること（~/.zshrcで永続化済み）:
- `TECHDIRECT_EMAIL` / `TECHDIRECT_PASSWORD`
- `FREELANCEBASE_EMAIL` / `FREELANCEBASE_PASSWORD`
- `SLACK_WEBHOOK_NOTIFICATION_URL`

## 実行手順

### ステップ1: スクリプト実行

バックグラウンドで実行する:

```bash
python3 ~/.claude/skills/techdirect-scout-filter/scripts/scout_filter.py > /tmp/scout_output.txt 2>&1 &
```

ドライラン（リスト追加・Slack通知なし）:
```bash
python3 ~/.claude/skills/techdirect-scout-filter/scripts/scout_filter.py --dry-run > /tmp/scout_output.txt 2>&1 &
```

### ステップ2: OTP処理

スクリプト出力に `OTP_REQUIRED` が含まれたら:

1. Gmail MCPで最新のOTPを取得:
   - 検索: `label:"01D.Claude" subject:ワンタイムパスワード newer_than:3m`
   - TechDirect OTPメールはフィルタで `01D.Claude` ラベルに自動アーカイブされる
   - snippetから6桁の数字を抽出
2. OTPファイルに書き込み:
   ```bash
   echo "{6桁のOTP}" > /tmp/techdirect_otp.txt
   ```

### ステップ3: 結果確認

スクリプト完了後、出力を読む:
```bash
cat /tmp/scout_output.txt
```

Slack通知はスクリプト内で自動送信される（#notification チャンネル、Bot名義）。

## 除外条件

| 条件 | 判定方法 |
|------|----------|
| 年齢超過（デザイナー50歳以上 / エンジニア・その他57歳以上） | TechDirect詳細画面の誕生年から計算。職種は「希望する求職条件 > 職種」直下の最上位カテゴリ（エンジニア/デザイナー）で判定 |
| 海外在住 | TechDirect詳細画面の都道府県が「海外」 |
| CRM NG人材 | フリーランスベース営業ステータスが「営業不可」or「取引停止」 |

※ TechDirectで氏名が「非公開」の候補者はフリーランスベース照合をスキップ
※ 職種の判定: デザイナーは「デザイナー」を含むカテゴリ（Webデザイナー等）。それ以外（エンジニア・職種不明）は57歳しきい値を適用

## 認証

- TechDirect: 環境変数 + メールOTP（Gmail MCP経由で自動取得）
- フリーランスベース: 環境変数
- Slack: Webhook（`SLACK_WEBHOOK_NOTIFICATION_URL`）

## 依存

- Python 3 + playwright (`pip3 install playwright && playwright install chromium`)
- headless=True で実行（Playwright 1.58+ではnew headlessがデフォルト）

## 関連ファイル

- スクリプト: `02_task/毎日-TechDirectスカウト/scout_filter.py`
- TechDirectログイン: `~/.claude/snippets/playwright_techdirect.py`
- TechDirect共通helper: `~/.claude/snippets/techdirect/`
- TechDirect画面仕様: `~/.claude/docs/techdirect/`
- フリーランスベースログイン: `~/.claude/snippets/playwright_freelancebase.py`
- フリーランスベース検索/API helper: `~/.claude/snippets/freelancebase/`
- フリーランスベース画面仕様: `~/.claude/docs/freelancebase/`
