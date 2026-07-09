---
name: techdirect-register-unsellable
description: TechDirectの営業対象外/お見送り候補者をFreelanceBaseに「営業不可」人材として自動登録する。TechDirect営業対象外人材のBase登録、TechDirect→FreelanceBase移行を行う場合に使用する。
---

## 概要

TechDirect 3つの対象リスト（お見送り/書類選考・営業対象外・案件が見つかるか不明）から候補者を収集し、本名が判定できる人材のみ FreelanceBase に「営業不可」人材として自動登録する。登録後、TechDirect側で既存ラベル「Base登録済み（営業対象外）」を付与して重複実行を防ぐ。

## TechDirect 画面/API 参照

TechDirect 側のスクレイピング仕様は共通リファレンスを参照する。

- 共通helper: `~/.claude/snippets/techdirect/`
- ページ/APIカタログ: `~/.claude/docs/techdirect/pages.md`
- カラム/選択肢カタログ: `~/.claude/docs/techdirect/column-catalog.md`
- フィールド/選択肢カタログ: `~/.claude/docs/techdirect/field-catalog.md`
- 危険アクション境界: `~/.claude/docs/techdirect/danger-actions.md`

候補者詳細を開くと既読化相当の `POST /v1/users/{uuid}/orgs/{id}/viewed` が発火する。調査用途では `techdirect.catalog_probe` の route guard を使い、非GETリクエストを abort する。候補者詳細の「リスト編集」はクリックしてメニュー表示までに留め、各リスト項目は状態トグルになり得るため押さない。

## 前提条件

### 環境変数（`~/.zshrc` で永続化済み）
- `TECHDIRECT_EMAIL` / `TECHDIRECT_PASSWORD`
- `FREELANCEBASE_EMAIL` / `FREELANCEBASE_PASSWORD`
- `SLACK_WEBHOOK_NOTIFICATION_URL`

### TechDirect 側の準備
- ラベル「Base登録済み（営業対象外）」が既に作成済みであること（候補者詳細「リスト」ボタンのドロップダウンに表示される）

### FreelanceBase 側の準備
- ユーザー「Claude アカウント」（内部ID=840）が存在し、自社担当者として選択可能であること
- 共通基盤 `~/.claude/snippets/freelancebase/` を使うこと
  - 候補者重複検索は `freelancebase.candidates` を優先
  - 作成・更新の拡張時は `freelancebase.crud.OperationPreview` と明示承認を挟む
  - 画面仕様は `~/.claude/docs/freelancebase/` を参照

## 実行手順

### ステップ1: スクリプト実行

**推奨（並列 + キャッシュで差分処理）:**
```bash
python3 ~/.claude/skills/techdirect-register-unsellable/scripts/register_unsellable.py \
  --parallel 5 --register-parallel 3 --continue-on-error \
  > /tmp/register_unsellable.log 2>&1 &
```

2回目以降は `output/register_unsellable/processed_urls.json` のキャッシュに
基づき、既に終状態（登録完了 / skip_*）の候補者は詳細ページアクセスを省略する。
差分のみを処理するので通常数分で完走する。

**全量再判定（四半期に1度 or キャッシュが壊れた時）:**
```bash
python3 ~/.claude/skills/techdirect-register-unsellable/scripts/register_unsellable.py \
  --parallel 5 --register-parallel 3 --continue-on-error --full-refresh \
  > /tmp/register_unsellable.log 2>&1 &
```

ドライラン（対象収集・氏名判定のみ、FreelanceBase登録・TechDirectラベル付与はスキップ）:
```bash
python3 ~/.claude/skills/techdirect-register-unsellable/scripts/register_unsellable.py --dry-run > /tmp/register_unsellable.log 2>&1 &
```

### ステップ2: OTP処理

スクリプト出力に `OTP_REQUIRED` が含まれたら:

1. Gmail MCPで最新OTPを取得:
   - 検索: `label:"01D.Claude" subject:ワンタイムパスワード newer_than:3m`
   - TechDirect OTPメールはフィルタで `01D.Claude` ラベルに自動アーカイブされるため、上記クエリが必須
2. OTPファイルに書き込み:
   ```bash
   echo "{6桁のOTP}" > /tmp/techdirect_otp.txt
   ```

### ステップ3: 結果確認

```bash
cat /tmp/register_unsellable.log
```

Slack通知はスクリプト内で自動送信される（`$SLACK_WEBHOOK_NOTIFICATION_URL`）。

## 対象者判定ルール

### 処理済みURLキャッシュ（定期実行時の差分処理）
- `output/register_unsellable/processed_urls.json` に過去の判定・登録結果を永続化
- 2回目以降の実行で、終状態（登録完了 / skip_label / skip_private / skip_partial / skip_initial / skip_nickname）のURLは詳細ページアクセスをスキップ
- `error` 状態や `valid` だが `label_applied=false` のエントリは再判定対象
- `--full-refresh` フラグでキャッシュ無視

### 一覧スキップ（TechDirect一覧で可能なら早期スキップ）
- 候補者に既に「Base登録済み（営業対象外）」ラベルが付いている場合はスキップ（初回実行時は詳細ページで判定、2回目以降はキャッシュでさらに手前の段階でスキップ）

### 氏名判定（ルールベース自動判定）
人材詳細画面の氏名フィールドを取得し、**すべて満たす**場合のみ登録対象:
- 姓と名の両方が含まれる（空白/中黒/漢字カナ混在で区切り）
- 漢字・カタカナ・平仮名・ラテン文字のいずれかで構成

以下は自動除外:
- イニシャルのみ（例: `A.B.`, `T.Y`, `K`）
- 姓のみ / 名のみ
- 明らかなあだ名・ハンドル（数字のみ・nickname・英字のみ等）
- 「非公開」表示

### 添付ファイルによる補足（スキルシート・職務経歴書）
- 氏名フィールドが `非公開` / 姓名分離不能の場合、TD候補者詳細の `/media/portfolio-files/` リンクから添付を DL しテキスト抽出→氏名正規表現マッチングでフォールバック
- 対応拡張子: `.pdf` (pdfplumber) / `.xlsx` (openpyxl) / `.docx` (python-docx)
- 正規表現パターン:
  - A: `氏名: 山田 太郎` 形式（スペース区切り）
  - B: `氏名 姓名 生年月日 ...` 形式（連結）→ 2+2 / 2+3 / 3+2 / 3+3 で分割
- フォームラベル（生年月日 / 最寄駅 / 年齢 など）は `_LABEL_BLACKLIST` で除外
- 抽出成功時は `valid` 判定、失敗時は元の `skip_private` / `skip_partial` のまま継続

## FreelanceBase 登録フィールド

### 新規作成ドロワー（「人材を作成」→「通常作成」）
| 項目 | 値 |
|------|-----|
| 所属 | 自社（デフォルト） |
| メールアドレス | `sample.claude{YYYYMMDDHHMMSS}@example.com`（タイムスタンプ一意） |
| 氏名 | TechDirectまたは添付から取得した姓名 |

### 候補者詳細 > 管理情報ドロワー
| 項目 | 値 | 内部値 |
|------|-----|--------|
| 集客ステータス | 個別連絡 | SELECT value=3 |
| 営業ステータス | 営業不可 | SELECT value=3 |
| 自社担当者1 | Claude アカウント | SELECT value=840 |
| 掘り起こし | 対象外 | `potential_flg=0` |
| 人材ランク | E | `candidate_rank_id=5` |
| 営業種別 | 新規 | `Sales_Type=New` |
| 流入経路 | TechDirect | `traffic_source=techdirect` |

### コメント欄
- 「社内向け情報」（基本情報ドロワー内の textarea）に TechDirect 人材詳細画面URLを記載

## エラーハンドリング

- **1件でもエラーが発生したら即中断**
- エラー種別に応じて Slack に通知（ログイン失敗 / OTP失敗 / 一覧取得失敗 / 登録失敗 / ラベル付与失敗）
- 処理済み候補者（登録＋ラベル付与まで完了したもの）は巻き戻さない

## Slack 通知内容

- 実行モード（通常 / ドライラン）
- 登録成功件数 / スキップ件数（ラベル済・氏名不明） / エラー件数
- エラー時はエラー種別・該当候補者URL・例外メッセージ抜粋

## 依存

- Python 3 + playwright (`pip3 install playwright && playwright install chromium`)
- 既存スニペット: `~/.claude/snippets/playwright_techdirect.py` / `playwright_freelancebase.py` / `freelancebase/`
- 再利用: `.claude/skills/freelance-meeting-summarize/scripts/crm_write.py` のヘルパー群（`open_section` / `get_drawer` / `save_drawer` / `set_radio` 等）

## 関連ファイル

- スクリプト本体: `.claude/skills/techdirect-register-unsellable/scripts/register_unsellable.py`
- TechDirect共通helper: `~/.claude/snippets/techdirect/`
- TechDirect画面仕様: `~/.claude/docs/techdirect/`
- 実行時状態: `.claude/skills/techdirect-register-unsellable/state/`（`.gitignore` 対象）
  - `processed_urls.json`（判定済みURLキャッシュ）
  - `run_YYYYMMDD_HHMMSS.json` / `refs_*.json`（実行結果・refs）
  - `debug/`（登録失敗時のスクリーンショット・HTML）
- 開発時の調査・検証記録: `02_task/20260421-スキル作成・修正_TechDirect営業対象外人材-Base登録/`
  - DOM調査結果: `output/explore_*/`
  - 探索スクリプト: `explore_techdirect.py` / `explore_freelancebase_v3.py`
  - 過去の実行結果JSON: `output/register_unsellable/run_*.json`
