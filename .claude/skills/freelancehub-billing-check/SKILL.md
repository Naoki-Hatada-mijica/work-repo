---
name: freelancehub-billing-check
description: "フリーランスHub（agent.freelance-hub.jp）の月次「課金対象チェック」を半自動化する。指定月の未確認応募者を取得し、Slack #inquiries / FreelanceBase と突合して非承認候補・要判断・承認推奨を分類。ユーザー承認後にHub管理画面で一括ステータス変更を行う。「フリーランスHub 課金対象チェック」「YYYY年MM月分のフリーランスHubチェック」「フリーランスHubの応募者を判定」などのリクエストに対して使用すること。"
---

## 概要

フリーランスHub（人材集客媒体・課金は応募ベース）の月次課金対象判定を半自動化する。
毎月50件以上発生する定常業務。

### 入力
- 対象期間（年月）— 必須。例: `2026-04` / `2026年4月`
  - 内部的に `YYYY-MM-01` 〜 `YYYY-MM-末日` に変換して URL クエリに渡す

### 出力
- `02_task/{今日のタスクフォルダ}/output/{YYYY-MM}_フリーランスHub課金対象チェック.md`
  - 3セクション（非承認候補 / 要判断 / 承認推奨）+ 各人材の詳細URL
- 同名 `.html` も同時に出力（ブラウザでクリック可能リンク・折りたたみ Slack/自己PR・色分けバッジ）
- フリーランスHub 管理画面の一括ステータス変更（ユーザー承認後）
  - 段階A: 一括非承認 + 理由チェック付与
  - 段階B: 段階A完了後にユーザー都度確認 → 承認時のみ一括承認

## 前提条件

### 環境変数（`~/.zshrc` で永続化済み）
- `FREELANCEHUB_LOGIN_KEY` / `FREELANCEHUB_EMAIL` / `FREELANCEHUB_PASSWORD`
- `FREELANCEBASE_EMAIL` / `FREELANCEBASE_PASSWORD`（突合用）
- `SLACK_USER_TOKEN`（Slack #inquiries 検索用、`xoxp-`）

### 関連サービス
| サービス | URL | 用途 |
|---|---|---|
| フリーランスHub | https://agent.freelance-hub.jp/ | 応募者一覧・ステータス変更 |
| FreelanceBase | https://freelancebase.jp/ | 営業不可フラグ突合 |
| Slack #inquiries | (workspace) | 応募者名で問い合わせ履歴を全文検索 |

### FreelanceBase 共通基盤

- ログイン: `~/.claude/snippets/playwright_freelancebase.py`
- 候補者検索/API 捕捉: `~/.claude/snippets/freelancebase/candidates.py`
- CRUD safety/画面仕様: `~/.claude/docs/freelancebase/`
- 書き込み系を追加する場合は `freelancebase.crud.OperationPreview` で差分を出し、既定 dry-run と明示承認を維持する

## 実行フロー

### Phase 1: 取得（フリーランスHub）

1. `playwright_freelancehub.login()` でログイン（セッション再利用）
2. `/entry?start_date=YYYY-MM-01&end_date=YYYY-MM-末日&approval_status=1` を直接叩く
   - `approval_status=1` で UI 上「未確認」のレコードを抽出（dropdown 内部値は「未承認」、後述「用語の表記揺れ」参照）
3. 一覧テーブルから氏名 / かな / 年齢 / メール / 電話 / 在住地域 / 稼働日数 / 応募内容 を取得
4. 各行をクリック→側面ドロワー→`a[href*="/entry/detail/"]` で**詳細URL**を取得
5. 50件超ならページネーションをループ

### Phase 2: 詳細情報取得（フリーランスHub）

各候補者の詳細URL（`/entry/detail/{token}`）を直接叩いて以下を取得：
- 「職務経歴書 / スキルシート」タブ: 経歴 / 自己PR / GitHub等
- 「承認 / 応募ステータス」タブの基本情報:
  - 生年月日 / お住まいの地域 / 最寄り駅
  - **現在の状況**（働いている等）
  - **契約形態**（個人事業主 / 正社員）← 正社員判定の決定打
  - 職業 / 職種 / 経験スキル / 経験年数
  - 希望条件（稼働開始時期 / 希望単価 / 作業可能日数 / 作業場所）

### Phase 3: 突合

#### 3a. Slack #inquiries 検索（**必須**）
- `https://slack.com/api/search.messages` を `SLACK_USER_TOKEN` (`xoxp-`) で直叩き（`urllib.request`）
- **3段クエリで OR 検索**（Slack 上の氏名表記揺れに対応、`"姓 名"` 単一クエリだとほぼ 0 ヒットになるため必須）：
  1. `"姓 名" in:#inquiries` — スペース込み完全一致
  2. `"姓名" in:#inquiries` — スペース無し完全一致
  3. `"姓" in:#inquiries` — 姓のみ。本文に `姓名` / `姓 名` / `名` / `姓さん` のいずれかを含むメッセージに限定して採用（同姓別人を排除）
- ヒットメッセージごとに `conversations.replies` で**スレッド全体を取得**して `slack_hits` に追加（過去経緯・続く返信が重要な判断材料のため絶対に省略しない）。`is_reply` フラグでリプライ識別。
- レート制限対策: 各呼び出し間 `SLACK_MIN_INTERVAL=3.2s` の最低間隔 + 429 時は `Retry-After` 待機してリトライ（Tier2 = 20回/分を順守）
- ヒットメッセージの `text` / `permalink` / `ts` / `thread_ts` / `is_reply` を判定材料として保持
- `SLACK_USER_TOKEN` 未設定時は **エラー終了**（サイレントスキップしない）

#### 3b. FreelanceBase 営業不可判定
- 既存スキル `techdirect-register-unsellable` の `check_fb_duplicate()` パターンを流用
- `/api/enterprise/candidates/index` POST に `keyword=氏名` で検索
- 完全一致した候補の `sales_status_id ∈ {2, 3, 4}` を「FB非OKステータス」として全てヒット対象に含める
  - `1=営業中(OK)` / `2=営業終了` / `3=営業不可` / `4=取引停止`

### Phase 4: 判定

候補者プロファイルを統合し、以下の **9つの内部判定理由** で判定：

| 内部理由 | 判定ロジック概略 | システム理由マッピング |
|---|---|---|
| 海外在住 | 在住地域が海外、または海外在住と推定される | 在住地域 |
| 50歳以上 | 生年月日 / 年齢から判定 | 年齢(高) |
| 稼働日数不足 | 作業可能日数=週1〜2、または週3+で副業推定 | 稼働日数不足 |
| 経歴詐称 | 経験スキル全領域5年以上 等の不自然な内容 | 経歴詐称 |
| ヒューマンNG | Slack 履歴等で対応がビジネスマナーに反する | ヒューマンNG |
| 日本語能力不足 | 外国籍 + N1未保持 / 自己PR が英語のみ等 | 日本語能力不足 |
| 正社員（副業推定） | 契約形態=正社員 **かつ** 稼働可能日数=週1〜2日（副業推定の複合条件） | **その他** + メモ「正社員+副業推定のため」 |
| 営業行為 | 候補者本人ではなくエージェント等からの応募 | **その他** + メモ「営業行為のため」 |
| 過去流入（Slack） | Slack #inquiries に応募日より 14 日以上前のメッセージあり（=過去にも流入があった証跡）→ FB ヒットの有無に関わらず非承認 | **ヒューマンNG**（Hub 側指示・2026-06 奥山さん回答） |
| FB非OK（過去流入あり） | FB `sales_status_id ∈ {2,3,4}` (営業終了/営業不可/取引停止) **かつ** Slack 過去履歴あり（過去流入ルールと重複ヒット） | **ヒューマンNG**（過去流入のある営業対象外人材） |
| FB非OK（過去流入不明） | FB `sales_status_id ∈ {2,3,4}` だが Slack に過去流入の証跡なし → **要判断**（今回応募の書類落ち結果としてステータス登録された可能性あり） | （要判断送り、info_gaps に追記） |

**経験不足（Slack言及）**: フリーランスHub の経験年数欄は使わないが、Slack #inquiries で経験浅さに言及されていた場合は非承認候補に格上げ。検出キーワード: `未経験` / `ほぼ未経験` / `経験浅` / `経験不足` / `経験が浅` / `ジュニア` / `新人` / `経験少な` / `経験が少な` / `経験半年` / `経験1年` 等。システム理由マッピングは **経験不足**（2026-06 に Hub 管理画面へ追加された専用項目。それ以前は「その他」へ寄せていた）。

**注意**: フリーランスHub 管理画面の「経験年数」欄は判定根拠に使わない（未登録のまま応募する人が多く、空欄=未経験を意味しないため）。

**Slack NG 言及キーワード**（detect_human_ng）: `クレーム`, `対応NG`, `ブラックリスト`, `NG人材`, `N人材`, `対応不可`, `NGにしておきます`

⚠️ **「見送り / お見送り / 対応なし」は detect_human_ng のキーワードに含めない**。
理由: お見送りされたこと自体は非承認の根拠にならない。お見送り理由（経験不足 / 海外 / 過去流入 / 正社員副業 / 経歴詐称 等）に該当した場合は、それぞれ専用の検出器（`detect_experience_low_slack` / `detect_overseas` / `detect_past_inflow` / `detect_full_time_employee` / `detect_fake_history`）が拾うため二重判定不要。`detect_human_ng` は理由を問わず確実に対象外とすべき強い表現のみに限定する。

### 未実装: Base コメント欄 / Webエントリー欄からの過去応募検出
- 現状は Slack のみで過去流入を判定
- FB の `/api/enterprise/candidates/{id}/comments` 等から過去のコメント取得は将来課題

確信度に応じて3分類：
- **非承認候補**: 1つ以上の理由が明確に該当
- **要判断**: 情報不足・グレー（**契約形態=正社員 単独はここに分類** — フリーランス転向の可能性あるため）
- **承認推奨**: いずれの理由にも該当しない

### Phase 5: レポート出力

`02_task/{タスクフォルダ}/output/{YYYY-MM}_フリーランスHub課金対象チェック.md` に書き出す。

```markdown
# フリーランスHub 課金対象チェック - YYYY年MM月分

## メタ情報
- 対象期間: YYYY-MM-01 〜 YYYY-MM-末日
- 取得件数: N件
- 判定内訳: 非承認候補 X / 要判断 Y / 承認推奨 Z

## 非承認候補 (X件)
### {氏名} ({年齢}歳)
- 詳細URL: {detail_url}
- 非承認理由（システム）: 在住地域, 稼働日数不足
- 内部判定理由: 海外在住, 副業推定
- 判定根拠:
  - Hub: 在住=フィリピン
  - Slack: スレッド XXX「副業で受けたい」発言
  - FB: 該当なし
- 承認理由メモ案: 「{自動生成された統合メモ}」

## 要判断 (Y件)
### {氏名} ({年齢}歳)
- 詳細URL: {detail_url}
- 論点: 自己PR が英語のみだが日本語スキルシート添付あり、N1所持有無不明
- 参考情報: ...

## 承認推奨 (Z件)
### {氏名} ({年齢}歳)
- 詳細URL: {detail_url}
- 簡易プロファイル: {年齢}歳 / {地域} / 週{N}日 / {職種}
```

ターミナルにも判定内訳を表示。

### Phase 6: ステータス一括変更（2段階・ユーザー都度承認）

#### 段階A: 一括非承認

1. ユーザーに Markdown を確認してもらい「非承認候補N件をこのまま反映してよいか」を明示確認
2. 承認後、Playwright で各候補の詳細ページを開き:
   - 「承認 / 応募ステータス」タブ → 承認情報の「変更」ボタン
   - モーダル: 承認ステータス を「非承認」に変更
   - 該当する非承認理由チェックボックスをON（複数可）
   - 「保存」ボタン
3. 各処理結果（成功/失敗/スキップ）をターミナルに表示
4. 途中失敗時は失敗件数のみ報告。**途中再開機能は未実装**のため、失敗した候補者は管理画面で手動対応する

⚠️ **承認ステータス変更モーダルに「メモ」入力欄は存在しない**（HTML 上 `対応メモ` テキストはあるが、それは別セクション=対応情報側の表示のみ）。生成済みの `approval_memo` はレポート (JSON/MD/HTML) 上の人手参照用に保持するのみで Hub への書き込みは行わない。

#### 段階B: 一括承認（段階A完了後に提案）

1. 「承認推奨リスト Z件 を一括承認しますか？」を都度確認
2. 承認の場合のみ実行: モーダルで「承認済」を選択 → 保存
3. 「要判断」は対象外（ユーザーが詳細URLから個別判断）

## 実行コマンド例

```bash
# Phase 1〜5: 取得→詳細→突合→判定→レポート出力（ステータス変更しない）
/usr/bin/python3 ~/.claude/skills/freelancehub-billing-check/scripts/run.py \
  --month 2026-04 --output-dir /path/to/task/output \
  > /tmp/freelancehub_check.log 2>&1 &

# FB 突合のみスキップしたいとき（Slack は必須のためスキップ不可）
/usr/bin/python3 .../scripts/run.py --month 2026-04 --output-dir output \
  --skip-fb

# Phase 6 段階A: 非承認候補を一括非承認
#   先に Phase 1〜5 を走らせて出力された JSON のパスを --report に渡す
/usr/bin/python3 .../scripts/run.py \
  --apply-reject --report /path/to/2026-04_freelancehub_candidates_YYYYMMDD_HHMMSS.json

# Phase 6 段階B: 承認推奨を一括承認
/usr/bin/python3 .../scripts/run.py \
  --apply-approve --report /path/to/2026-04_freelancehub_candidates_YYYYMMDD_HHMMSS.json

# 確認プロンプトをスキップ（自動化向け）
/usr/bin/python3 .../scripts/run.py --apply-reject --report <json> --yes
```

**注意**: pyenv の python3.12 には playwright が無いため、必ず `/usr/bin/python3`（system Python 3.9）を使う。

## 用語の表記揺れ（重要）

フリーランスHub の UI には3場面で表記揺れがある：

| 場面 | 表記 |
|---|---|
| 一覧画面の承認ステータスフィルター dropdown | 未**承認** / **承認済** / 非承認 |
| 一覧テーブル内の状態セル | 未**確認** / **承認済** / 非承認 |
| 詳細ページのステータス変更モーダル dropdown | 未**確認** / **承認** / 非承認 |

スキル内部・ユーザー向け文言は **「未確認」** で統一。
- dropdown フィルター操作時は「未承認」（`approval_status=1`）
- モーダルでステータス変更時は「承認」/「非承認」（モーダルでは「承認済」ではなく「承認」）

## 依存

- Python 3 + playwright (`/usr/bin/python3` を使用、playwright 1.58.0 が入っている)
- 既存スニペット:
  - `~/.claude/snippets/playwright_freelancehub.py`（本スキル用に新規作成）
  - `~/.claude/snippets/playwright_freelancebase.py`（FB ログイン）
  - `~/.claude/snippets/freelancebase/`（FB 候補者検索/API 捕捉/CRUD safety）
- 既存スキル `techdirect-register-unsellable` の `check_fb_duplicate()` パターン
- Slack 検索: `SLACK_USER_TOKEN` で `https://slack.com/api/search.messages` を直叩き

## 関連ファイル

- スクリプト本体: `.claude/skills/freelancehub-billing-check/scripts/run.py`
- 実行時状態: `.claude/skills/freelancehub-billing-check/state/`（`.gitignore` 対象）
  - `session.json`（フリーランスHub セッション）
  - `run_YYYYMMDD_HHMMSS.json`（実行結果）
  - `debug/`（HTML / スクリーンショット）
- 開発時の調査・検証記録: `02_task/20260510-スキル作成・修正_フリーランスHub課金対象チェック/`
