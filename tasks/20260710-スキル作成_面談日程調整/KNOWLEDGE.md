# Knowledge

過去の学びや注意点をここに記録する。

## 初期メモ（2026-07-10）
- 現状 Google カレンダーを直接操作できるコネクタ（MCP）は未接続。連携方式が本スキルの肝。
- カレンダーの「面談調整中ブロック削除」は破壊的操作。対象を列挙して確認してから実行する運用にする。
- 候補日程は毎回フォーマットが違う（不定形）前提。パースに迷う候補は勝手に確定しない。

## カレンダー連携の調査結果（2026-07-10）
- ユーザーは案A（連携追加）を希望。
- ただし MCP レジストリ検索（google calendar / workspace / gmail 等）で **ワンクリック追加できる Google カレンダー連携は見つからず**。
- ローカルにも gcalcli / gam などの CLI は未インストール。
- → 案Aの実現には「一度だけの初期セットアップ」が必要：
  - 選択肢A-1：Google カレンダー API を使うローカルスクリプト（Google Cloud で OAuth クライアント作成 → 初回認証。以降は自動）。安定・確実だが初期設定にひと手間。
  - 選択肢A-2：gcalcli を導入（内部で同じ OAuth 認証が必要）。
  - どちらも秘密情報（クライアントシークレット・トークン）はファイルに書かない／コミットしない運用にする（ローカルの安全な場所＋.gitignore）。
- 暫定運用として、連携セットアップが済むまでは「判定＋整形返信＋確定フォーマット生成」を先に自動化し、カレンダー登録・削除だけ手動、という段階導入も可能。

## カレンダー連携セットアップ完了（2026-07-10）
案A（API 連携）でセットアップ完了・動作確認済み。
- Google Cloud プロジェクト: `interview-scheduler`（ID: `interview-scheduler-502002`、組織 mijica.co.jp）
- Google Calendar API 有効化済み
- OAuth 同意画面: **内部**（Internal）で構成 → 審査不要
- OAuth クライアント: デスクトップアプリ型
- 秘密情報の保管場所（リポジトリ外・本人のみ 600/700 権限）:
  - `~/.config/interview-scheduler/client_secret.json`
  - `~/.config/interview-scheduler/token.json`（初回認証で生成）
- 実行環境: `~/.config/interview-scheduler/venv`（google-api-python-client 等）
- スコープ: `https://www.googleapis.com/auth/calendar`（読み書き・削除可）
- 動作確認: primary カレンダー（畑田 真輝 / Asia/Tokyo）の予定取得に成功
### ハマりどころ
- 認証 JSON は**作成時のポップアップでしか DL できない**（後から表示・DL 不可の仕様）。
- 私が操作する自動化タブ（claude-in-chrome）では DL がブロックされる。ユーザー自身の通常タブで作成→その場で DL してもらう必要があった。
- Python 3.9 は EOL 警告が出るが動作に支障なし。

## 書き込み実装・スキル化完了（2026-07-10）
- 共通処理を `gcal_common.py` に切り出し、`gcal_match.py`（読み取り整形）／`gcal_register.py`（フェーズ1登録）／`gcal_confirm.py`（フェーズ2確定）が import して使う構成。
- **下見（apply=false）→ 内容確認 → 実行（apply=true）の二段構え**を全書き込みで統一。削除は破壊的操作なので必ず対象を列挙して確認。
- 面談調整ブロックは `transparency:transparent`（仮押さえ＝他予定をブロックしない）。色分け：調整=バナナ(5)／確定=トマト(11)／バッファ=グラファイト(8)。
- 削除対象の特定は **events.list の q（全文検索）で拾い、summary の完全一致でフィルタ**（部分一致だと別候補者を巻き込むため）。
- freebusy の calendars キーは `primary` ではなく実アドレスで返ることがある → `next(iter(cals))` でフォールバック。
- 実カレンダーで登録→確定→削除まで通し検証済み。テストイベント（ZZ検証削除用）は後片付けで全削除。
- スキルは `.claude/skills/interview-schedule-coordination/` に scripts・references/setup.md を同梱して自己完結。scripts を実行する Python は script 同ディレクトリを sys.path に含むため、どの cwd からでも import が通る。
