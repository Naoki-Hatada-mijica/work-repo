---
name: freelance-meeting-prep
description: "ITフリーランスの登録面談前の事前準備として、Slack #inquiries の応募スレッド（URL or 氏名）を起点に経歴書・人材マスタ・募集中エンド直案件を取得し、経歴把握・追加ヒアリング論点・希望条件の市場観・マッチ案件を整理した「ヒアリングシート（追記済みMD）」を1ファイルで生成する。登録面談準備・面談前準備・ヒアリングシート作成・「この人の面談準備して」を行う場合に使用する。面談後のCRMサマリ作成は freelance-meeting-summarize を使う。"
---

## 概要

ITフリーランスの**登録面談「前」**の事前準備を自動化する。Slack `#inquiries` の応募スレッド（スレッドURL もしくは候補者氏名）を入力に、

1. スレッド内の各媒体応募URL・添付経歴書をすべて取得
2. FreelanceBase の人材マスタ（候補者レコード）を取得
3. FreelanceBase の「募集中エンド直案件」ビュー（view-105）を取得しマッチ案件を選定

した上で、社内標準のヒアリングフォーマット（[HEARING_TEMPLATE.md](HEARING_TEMPLATE.md)）に判明情報を追記し、最下部に「事前準備サマリ」（経歴把握・追加ヒアリング論点・希望条件と市場観・マッチ案件候補・面談の進め方）を付けた**1ファイル**を `output/` に出力して VS Code で開く。

**このスキルは読み取り専用。** CRM／FreelanceBase への書き込みは行わない。

### 姉妹スキルとの使い分け（重要）

| スキル | タイミング | 用途 |
|---|---|---|
| **`freelance-meeting-prep`（本スキル）** | 面談**前** | 経歴書・希望条件から事前準備。ヒアリングシート（追記済み）を作る |
| `freelance-meeting-summarize` | 面談**後** | 議事録・録画・スキルシートを統合し CRM 貼り付け用サマリを作る |
| `sales-matching-score-diagnosis` | 随時 | 提示された案件×候補者を100点満点でスコアリング |
| `sales-talents-to-projects-matching` | 随時 | 営業開始人材をオープン案件マスタ全件へ逆引きマッチング |

> 本スキルのマッチ案件選定は「面談準備の材料出し」であり、厳密なスコアリングではない。定量採点が必要なら `sales-matching-score-diagnosis`、人材起点の全件逆引きは `sales-talents-to-projects-matching` を使う。
> 将来的に `freelance-meeting-summarize` と連携した一気通貫フロー（準備→面談→サマリ）に統合する構想があるが、現時点では独立スキル。

## 前提・依存

- Slack 応募スレッドは `#inquiries`（channel_id `C083TN7QDEE`）に集約されている
- マッチ案件の参照元: FreelanceBase 募集中エンド直案件ビュー <https://freelancebase.jp/enterprise/jobs#view-105>
- スクリプトは複製しない。FreelanceBase アクセスは共通基盤 `~/.claude/snippets/freelancebase/`（および入口 `playwright_freelancebase.py`）、本スキルの薄いラッパーは `scripts/fetch_prep_data.py` を使う
- 経歴書（xlsx/pdf/docx）のテキスト化は `.claude/skills/sales-matching-score-diagnosis/scripts/extract.py` を再利用する（新規に複製しない）

### 環境・認証

- **FreelanceBase**: `FREELANCEBASE_EMAIL` / `FREELANCEBASE_PASSWORD`（`~/.zshrc` に設定済み・OTP 不要）。セッションは `~/.cache/freelance-meeting-prep/fb_state.json` に再利用キャッシュ
- **Slack 添付DL**: `$SLACK_USER_TOKEN`（xoxp、`files:read` スコープ）で `files.info` → `url_private_download` を curl 取得
- **Playwright 実行系**: 既定の `python3`（3.14）には Playwright 未導入。**`~/.pyenv/versions/3.12.13/bin/python3` で実行する**
- 依存パッケージ: `pip3 install playwright openpyxl pdfplumber python-docx && playwright install chromium`

### FreelanceBase ビュー共有（重要・ハマりどころ）

案件ビュー（view-105 等）は enterprise member ごとに**共有設定**がある。Claude 用アカウント（`claude@mijica.co.jp` / member id 840）に当該ビューが共有されていないと、`#view-105` を開いても**既定ビュー `#view-3`（全ての案件）にフォールバック**し、対象外の案件が混ざる。`fetch_prep_data.py jobs` は以下3点でビュー適用を検証し、検証できないときは**エラーで中断**する（誤った全件取得を防ぐ）:

1. 最終 URL が `#view-105`
2. ビュータブのラベル「募集中エンド直案件」が DOM に存在
3. `/api/enterprise/jobs/index` の payload にビューの `conditions`（募集状況=募集中 × 案件ランク A/B/C/D/未選択）が入っている

検証エラーが出たら、赤木に「FreelanceBase で当該ビューを Claude アカウントに共有してください」と依頼してから再実行する。

## 入力

- (a) **Slack スレッド URL**（`#inquiries` の応募スレッド）
- (b) **候補者氏名のみ** → `#inquiries` を氏名で検索して該当スレッドを特定する
- スレッドには各媒体（フリーランスHub等）の応募URL・人材マスタURL・希望条件・添付経歴書がまとまっている。**貼られたURLにはすべてアクセス**して情報を取得する

## 手順

### ステップ0: 入力の受け取りとスレッド特定

1. PLAN.md / 直近の指示から、スレッドURL または 候補者氏名を受け取る
2. **氏名のみ**のときは `#inquiries` を検索してスレッドを特定する:
   - `mcp__claude_ai_Slack__slack_search_public_and_private` query=`<氏名> in:#inquiries`
   - 親メッセージ（`Reply count` のある投稿）の `Message_ts` と `channel_id` を控える
3. `mcp__claude_ai_Slack__slack_read_thread` でスレッド全文を取得する
   - 各媒体の応募URL・**人材マスタURL（`freelancebase.jp/enterprise/candidates/<id>`）**・希望条件（単価/稼働/リモート/開始）・ポートフォリオURL・添付ファイル（`Files: <name> (ID: <file_id>, ...)`）を洗い出す
   - 人材マスタURLの末尾IDが FreelanceBase の enterprise ID（管理用IDとは別物）

### ステップ1: 経歴書・参照URLの取得

1. **添付経歴書のDL**（Slack MCP はDLできないため API 直叩き）:

   ```bash
   cd "<タスクフォルダ>/input" && \
   url=$(curl -s -H "Authorization: Bearer $SLACK_USER_TOKEN" "https://slack.com/api/files.info?file=<FILE_ID>" \
     | python3 -c "import sys,json;print(json.load(sys.stdin)['file']['url_private_download'])") && \
   curl -sL -H "Authorization: Bearer $SLACK_USER_TOKEN" "$url" -o "経歴書_<氏名>.xlsx"
   ```

2. **スレッド内の参照URL（ポートフォリオ・導入事例・公開実績等）にアクセス**して内容を把握する（WebFetch / curl）。Microsoft 等の導入事例記事は経歴の裏取りに使える。公開終了で404のページもあるため取得可否を記録する
3. 経歴書をテキスト化する（複製せず既存 extract.py を使う）:

   ```bash
   python3 .claude/skills/sales-matching-score-diagnosis/scripts/extract.py "<タスクフォルダ>/input/経歴書_<氏名>.xlsx"
   ```

   - xlsx の各案件行（期間 / 業務内容 / 役割・規模 / 言語 / DB / OS / FW・ツール / 担当工程）を時系列で読む

### ステップ2: FreelanceBase 人材マスタの取得

```bash
~/.pyenv/versions/3.12.13/bin/python3 \
  .claude/skills/freelance-meeting-prep/scripts/fetch_prep_data.py candidate "<氏名 or enterprise ID>" \
  --out "<タスクフォルダ>/input/fb_candidate.json"
```

- 氏名でヒットしないときは姓のみでも検索する（`search_candidates` は keyword 部分一致）
- 取得レコードから読み取る主な項目: `name` / `age` / `birth_date` / `prefecture_key_values`（都道府県）/ `station_key_values`（最寄駅）/ `business_day_key_values`（稼働日数）/ `work_styles_key_values`（常駐/リモート可否）/ `monthly_price_f_num`・`monthly_price_num`（希望単価。**最低=希望が同額で入ることがある**）/ `skill_key_values`（スキルとレベル）/ `desc_skill_summary`（経験年数・スキルサマリ）/ `traffic_source_key_values`（流入経路）/ `email` / `tel` / `resume_url` / `name_for_company`（管理用ID）
- スキルシート本文は FB レコードに含まれないため、経歴の詳細は経歴書（ステップ1）を主とする

### ステップ3: マッチ案件の取得（募集中エンド直案件 view-105）

```bash
~/.pyenv/versions/3.12.13/bin/python3 \
  .claude/skills/freelance-meeting-prep/scripts/fetch_prep_data.py jobs \
  --view 105 --label "募集中エンド直案件" \
  --out "<タスクフォルダ>/input/fb_jobs.json"
```

- 冒頭の `=== VIEW VERIFICATION ===` で `final_url` が `#view-105`、`applied_conditions` に募集状況・案件ランクが入っていることを確認する
- 検証エラー（未共有→#view-3 フォールバック等）で中断したら、ビュー共有を依頼してから再実行（前述「FreelanceBase ビュー共有」）
- 各案件の `id` / `title` / `monthly_price_from`〜`to` / `work_style` / `business_day` / `prefecture` / `skills` / `occupation` / `expected_age_max` / `inception_day` / `detail` / `required` / `welcome` を読み、候補者のスキル・希望条件と突き合わせる

### ステップ4: 分析

経歴書・人材マスタ・参照URL・案件一覧をもとに、以下を Claude 本体が組み立てる:

1. **経歴の把握**: 人物像（年齢/拠点/経験年数/コア領域）＋主要経歴の時系列要約。**留意点をフェアに**（実装ブランク、経歴書と公開情報の数字の食い違い、空白期間、公開終了URL 等）
2. **追加ヒアリング論点**（優先順）: 経歴書から読み取れない点。キャリアの方向性（PM/PdM か 開発か）・契約形態遍歴（いつからフリーランスか）・単価の柔軟性・稼働スタイルの現実線（在住地と常駐可否）・主要スキルの実務深度・英語・空白期間・コーディングテスト可否・並行状況・インボイス登録 など
3. **希望条件と市場観**: 単価/稼働/場所/領域それぞれに本人希望と市場観・相談ポイントを併記。想定される潜在的な希望条件も推測
4. **マッチ案件**: view-105 から候補者に合う案件を選定（5件前後＋次点＋見送り判断）。各案件に適合理由と論点（必須要件の充足可否・単価ギャップ・勤務地）を添える

#### 記載ルール（厳守）

- **確定**（応募情報・経歴書・人材マスタに記載がある）→ そのまま記載
- **推測**（おそらくそうだが予想の範疇）→ **「（推測）」を付けて**記載し、根拠も添える
- **不明**（全く読み取れない）→ **追記せず項目を空欄のまま残す**（★で要確認マークを付けてよい）
- 事実と推測を混同しない。営業文的な「盛り」をしない（本人が「得意ではない」と言っている領域を強い表現にしない）

#### 単価の扱い

- 提案単価を検討する場合は**税別表記**。本人希望が税込なら ÷1.10 →万円単位で切り上げ →+10万円（例: 希望80万税込 → 73万税別 → 提案83万税別）
- 人材マスタの希望単価は最低=希望が同額のことがある。下限の柔軟性と税込/税別は面談で要確認、と論点に必ず入れる

### ステップ5: ヒアリングシート生成と出力

1. [HEARING_TEMPLATE.md](HEARING_TEMPLATE.md) をベースに追記する:
   - 先頭に面談日時・記載ルールの注記を1行
   - 【名前】【提案案件】【流入経路】【経歴】を埋める（流入経路は該当媒体を太字、非該当は取消線でもよい）
   - 【共通事項】各項目を 確定／推測／不明 ルールで埋める
   - **【スキルチェック】は候補者の職種に該当するセクションのみ残し、他職種セクションは削除する**
   - 【諸条件】【事務連絡】を埋める
   - 末尾に「事前準備サマリ」（経歴把握 / 追加ヒアリング論点 / 希望条件と市場観 / マッチ案件候補 / 面談の進め方）
2. `output/{タスクフォルダ名}_ヒアリングシート.md` に**1ファイル**で出力する
3. VS Code で開く:

   ```bash
   open -a "Visual Studio Code" "<タスクフォルダ>/output/{タスクフォルダ名}_ヒアリングシート.md"
   ```

### ステップ6: サマリ報告

チャットに以下を要約する:
- 候補者の人物像（1〜2文）
- 主な面談論点（3〜5点）
- マッチ案件の最有力（社名/案件名・単価・形態）と次点
- ビュー適用を検証した旨（`#view-105`・条件・件数）
- 出力ファイルパス

## セルフチェック（出力前に必ず）

1. 【スキルチェック】が候補者の職種セクションのみに絞られているか（他職種が残っていないか）
2. 確定／推測（「（推測）」明記）／不明（空欄）の3区分が守られているか。推測に根拠が添えてあるか
3. スレッド内の全URL（応募・人材マスタ・ポートフォリオ）にアクセスしたか。取得不可（404等）は明記したか
4. マッチ案件が view-105 の検証済みデータから選ばれているか（#view-3 フォールバックでないか）
5. 単価の論点（税込/税別・下限の柔軟性）が入っているか
6. 出力が1ファイルで、最下部に事前準備サマリがあるか

1つでも違反があれば修正して再出力する。

## 非スコープ

- CRM／FreelanceBase への書き込み（読み取り専用）
- 面談後の議事録・CRM サマリ作成（→ `freelance-meeting-summarize`）
- 厳密な100点スコアリング（→ `sales-matching-score-diagnosis`）
- オープン案件マスタ全件からの逆引き（→ `sales-talents-to-projects-matching`）
- Slack への自動返信・候補者への連絡
