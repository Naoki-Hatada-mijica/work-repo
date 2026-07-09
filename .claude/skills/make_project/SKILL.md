---
name: make_project
description: 新規プロジェクトの初期構築を行うスキル。新規プロジェクトのセットアップ、初期ファイル作成、Git初期化、既存プロジェクトのアップデートを行う際に使用する。「プロジェクトを初期化して」「新規プロジェクトをセットアップして」「プロジェクトの初期構築をして」「プロジェクトをアップデートして」などのリクエストに対して必ず使用すること。
---

# make_project スキル

## ステップ1：モード選択

作業を開始する前に、ユーザーに以下を必ず口頭で提示し、番号で選択してもらうこと：

「make_project スキルを開始します。以下から実行モードを選択してください：

1. 新規プロジェクトを構成する（現フォルダの中に新規プロジェクトフォルダを作成）
2. 既存のプロジェクトをアップデートする（現フォルダをプロジェクトフォルダとして使用）
3. その他・相談する

番号を入力してください。」

- **1を選択** → 「モードA：新規プロジェクト作成」へ進む
- **2を選択** → 「モードB：既存プロジェクトのアップデート」へ進む
- **3を選択** → 「モードC：対話」へ進む

---

# モードA：新規プロジェクト作成

## A-1. 事前確認
以下の情報をユーザーに確認してから作業を開始する：
- プロジェクト名（フォルダ名）：[USER_INPUT]
- GitHubリポジトリURL：[USER_INPUT]
- デフォルトブランチ名：main（変更がある場合はユーザーに確認）

※ 事前にGitHub上でリポジトリを作成しておくこと（README等は追加しない）

## A-2. プロジェクトフォルダの作成

```bash
mkdir [PROJECT_NAME]
cd [PROJECT_NAME]
```

以降の作業はすべてこのフォルダ内で実行する。

## A-3. サブフォルダ作成

```bash
mkdir -p .agent/skills
mkdir -p .agent/memory
mkdir -p .agent/handoff
mkdir -p .agent/workflows
mkdir -p .claude/commands
mkdir -p .spec
mkdir -p .output
mkdir -p .references
mkdir -p .github/workflows
```

## A-3.5. .claude/settings.json の作成（自動レビュー有効化）

新規プロジェクトでは Claude 作業完了時の自動レビュー（Codex 優先 → リミット時 Claude サブエージェントへフォールバック）を有効にする。

```bash
cat > .claude/settings.json <<'EOF'
{
  "env": {
    "CODE_REVIEW_MODE": "auto"
  }
}
EOF
```

これで Stop hook / PostToolUse hook（グローバル設定）から `/code-review` 相当の処理が走る。Codex が利用可能なら `codex exec` で `.codex-reviews/` 配下にレビュー結果を保存し、リミット中なら Claude サブエージェント（`adversarial-reviewer`）への切り替え案内を返す。
手動レビューのみにしたい場合はユーザー確認の上、値を `"manual"` に変更すること（自動 hook は走らず、`/code-review` `/claude-review` を手動実行）。

## A-3.6. セキュリティ機構の自動配置（A-weekly + C-2 + pre-push）

`mijica-inc/security-audit` の workflow テンプレを `.github/workflows/` に配置し、`core.hooksPath` を root 所有中央 hook に設定する。
- A-weekly: 週次の Trivy/gitleaks/Trivy fs スキャン → GH Issue + Slack
- C-2: PR 自動レビュー（Job 1 静的=required 候補 / Job 2 LLM=warn-only）
- pre-push hook: `core.hooksPath` で `/usr/local/share/security-audit/git-hooks/` を参照（root 所有 chmod 755 で改竄保護）

### 前提

- `~/tools/security-audit` に `mijica-inc/security-audit` が clone 済み（`bootstrap-machine.sh` 実行済み環境を想定）
- `gh` CLI 認証済み（`gh auth status`）

### 実行内容

```bash
# 1. cron hash 分散（リポ名 md5sum で MIN/HOUR を計算）
HASH=$(printf '%s' "[PROJECT_NAME]" | md5sum | awk '{print $1}')
CRON_MIN=$(( 0x${HASH:0:2} % 60 ))
CRON_HOUR=$(( 0x${HASH:2:2} % 24 ))

# 2. workflow 配置（template から sed 置換）
TEMPLATE_DIR="${HOME}/tools/security-audit/workflows"
sed "s|\${HASH_MIN}|${CRON_MIN}|g; s|\${HASH_HOUR}|${CRON_HOUR}|g" \
  "${TEMPLATE_DIR}/security-audit-weekly.yml.template" \
  > .github/workflows/security-audit-weekly.yml
cp "${TEMPLATE_DIR}/security-check-pr.yml.template" \
  .github/workflows/security-check-pr.yml

# 3. core.hooksPath 設定（git init 後に実行する）
git init -q 2>/dev/null || true
git config core.hooksPath /usr/local/share/security-audit/git-hooks

# 4. ラベル先打ち（リモート push 後に実行する場合は --repo オプション付与）
# gh label create security-audit --force
# gh label create heartbeat-dead --force
```

### 注意

- `~/tools/security-audit` が clone されていない環境では skip し、ユーザーに `bootstrap-machine.sh` 実行を案内
- リモート GitHub リポ作成は A-1 で済ませている前提（`gh repo create` 済み）
- ラベル作成は GitHub にプッシュした後に行う（後述の git push 後ステップで実行）
- secrets (`SLACK_WEBHOOK_NOTIFICATION_URL` / `ANTHROPIC_API_KEY`) は **GitHub Org secret で visibility 設定** することで個別リポへの set 不要

## A-4. 初期ファイル作成

### README.md

README.mdが存在しない、あるいは中身が空の時のみ以下を実行する。
プロジェクト名はA-1で確認済みのものを使用する。日時はローカル時刻、ツール名は現在使用中のツール名（例：Claude Code Opus 4.6）を記載する。

```markdown
# Project: [PROJECT_NAME]

* これは[YYYY-MM-DD HH:MM]に自動生成されたプロジェクトである
* 初期構築担当ツール名：[TOOL_NAME]
* このプロジェクトでは、生成AIおよびスキルを積極的に活用して開発する
```

### .agent/memory/MEMORY.md
```markdown
# MEMORY

## プロジェクト概要

## 学習した知識・教訓
```

### .agent/handoff/HANDOFF.md
```markdown
# HANDOFF

初回セットアップ完了。作業を開始してください。
```

### CLAUDE.md（プロジェクトルート）
```markdown
- セッション開始時に共通ルールである、AGENTS.mdを必ず読み込むこと。
- 読み込んだことを最初に報告すること
- 以下は Claude Code固有の差分のみ記載する
```

### GEMINI.md（プロジェクトルート）
```markdown
- セッション開始時に共通ルールである、AGENTS.mdを必ず読み込むこと。
- 読み込んだことを最初に報告すること
- 以下は Gemini 固有の差分のみ記載する
```

### AGENTS.md（プロジェクトルート）
```markdown
# Project guide line

## プロジェクトの原則
- 本プロジェクトのプラン作成、および回答は全て日本語で行う

## プロジェクトの目的
-

## Local Skills
- セッション開始時にプロジェクトのローカルスキルを `.agent/skills/` 配下で確認する

# Memory & Handoff Instructions

## 3ファイルの役割と哲学
- 本ファイル（AGENTS.md）は「厳格なルール」、人が作成
- MEMORY.mdは「積み上がる経験」、AIが作成・AIが利用
- HANDOFF.mdは「セッション間の引き継ぎ」、AIが作成・AIが利用、ただし人間がレビューし必要な情報をキュレーションする

## セッション開始時（必須）
セッション開始時、ユーザーへの最初の応答の前に、以下の2ファイルを読み込み、読み込んだことを報告すること：
- `.agent/memory/MEMORY.md`  （学習した知識・教訓）
- `.agent/handoff/HANDOFF.md` （前回の作業引き継ぎ）

## メモリ管理
- 新しい知識・教訓を記録する際は `.agent/memory/MEMORY.md` を更新
- 既存のMEMORY.mdを更新する前に、現在のファイルを`.agent/memory/YYYY-MM-DD.md` にアーカイブしてから新規作成
- ローカルの自動メモリ機能（~/.claude/ 配下）は使用しない
- MEMORY.mdは200行以内を維持すること
- 本ファイルと重複する内容はMEMORY.mdに書かない

## ハンドオフ管理
- ハンドオフは `/handoff` コマンドで作成（Claude Codeの場合）
- 保存先は `.agent/handoff/HANDOFF.md`（固定名）
- 作成時は既存ファイルを `.agent/handoff/YYYY-MM-DD-HHMM.md` にリネームしてからHANDOFF.mdを新規作成する
- 時刻はローカル時刻・24時間表記

## 仕様駆動開発（SDD）ルール
- コーディングや業務作業を開始する前に、必ず `.spec/` 配下の4ファイルを確認・更新すること
- 作業の順序：PLAN（目的確認）→ SPEC（要件確認）→ TODO（タスク確認）→ 実作業
- **PLAN.mdは人間の口頭メモ・自由記述**であり、箇条書き・口語・断片的な内容で構わない
- PLAN.mdを読んだら、そのまま実装に入らず、不明点をヒアリングしながらSPEC.mdを作成・確定させること
- SPEC.mdが確定してからTODO.mdのタスク分解を行い、ユーザーの承認を得てから実作業を開始する
- 作業完了後は TODO.md の該当タスクにチェックを入れ、KNOWLEDGE.md に学びを記録する
- 仕様が不明確な場合は作業を開始せず、ユーザーに確認してから SPEC.md を更新する
- 新しい開発サイクルを始める際は `/newplan` コマンドを使用する

## フォルダ用途
- `.spec/`：設計ドキュメント（PLAN / SPEC / TODO / KNOWLEDGE）
- `.output/`：成果物・アウトプット（記事MD、コード、資料など完成したもの）
- `.references/`：参考資料・素材（PDFや画像、URLメモ、サンプルコードなど作業の入力素材）
```

## A-5. 仕様駆動開発ファイルの作成（.spec/）

### .spec/PLAN.md
```markdown
# PLAN - やりたいこと

<!-- ここに思ったことを自由に書いてください。箇条書きでも口語でもOK -->
<!-- Claude がこの内容を読んでヒアリングし、SPEC.md を作成します -->
```

### .spec/SPEC.md
```markdown
# SPEC - 技術仕様・要件定義

## 機能要件
## 非機能要件
## 技術構成
```

### .spec/TODO.md
```markdown
# TODO - タスクリスト

## 優先度：高
## 優先度：中
## 優先度：低
## 完了済み
- [x] 初期セットアップ
```

### .spec/KNOWLEDGE.md
```markdown
# KNOWLEDGE - ドメイン知識・調査結果

## 業務・ドメイン知識
## 調査・リサーチ結果
## 技術的な知見
## 決定事項と理由
```

## A-6. newplan コマンドの作成

以下の内容で2つのファイルを作成する：
- `.claude/commands/newplan.md`
- `.agent/workflows/newplan.md`

内容：
```
以下の手順で新しい開発サイクルを開始してください：

1. `.spec/` 配下の4ファイルが存在する場合、本日の日付（ローカル時刻）でアーカイブする：
   - `PLAN.md`      → `PLAN-YYYY-MM-DD.md`      にリネーム
   - `SPEC.md`      → `SPEC-YYYY-MM-DD.md`      にリネーム
   - `TODO.md`      → `TODO-YYYY-MM-DD.md`      にリネーム
   - `KNOWLEDGE.md` → `KNOWLEDGE-YYYY-MM-DD.md` にリネーム

2. 新しいファイルを以下の通り作成する：
   - `PLAN.md`：空テンプレートで新規作成
   - `SPEC.md`：空テンプレートで新規作成
   - `TODO.md`：空テンプレートで新規作成
   - `KNOWLEDGE.md`：アーカイブした内容をそのままコピーして新規作成（知見を引き継ぐ）

3. PLAN.mdをVS Codeで開く（`open -a "Visual Studio Code"` を使用）
4. ユーザーに「VS Code上でPLAN.mdを編集してください。音声入力・コピペ・手書きなど自由に記載してください。完了したら教えてください」と伝え、完了の返答を待つ
5. 完了後、PLAN.mdを読み取る
6. 内容に不明点・不足があればターミナル上で質問し、回答をPLAN.mdに追記する
7. 質問がなければ、または質問完了後、PLAN.mdの内容を構造化して書き直す
8. PLAN.mdの内容をもとにユーザーと壁打ちし、SPEC.mdの要件・観点・制約を整理して記載する
9. SPEC.mdからTODO.mdのタスクを分解し、チェックリスト形式で記載する
10. 完了後、以下を報告する：
    - アーカイブしたファイル一覧
    - 新しいPLAN.md / SPEC.md / TODO.mdの概要
```

## A-7. handoff コマンドの作成

以下の内容で2つのファイルを作成する：
- `.claude/commands/handoff.md`
- `.agent/workflows/handoff.md`

内容：
```
以下の手順でハンドオフを作成してください：

1. `.agent/handoff/HANDOFF.md` が存在する場合：
   - そのファイルの更新日時（ローカル時刻）を取得
   - `.agent/handoff/YYYY-MM-DD-HHMM.md` にリネーム

2. 新しい `.agent/handoff/HANDOFF.md` を以下のテンプレートに従って作成し、完了後「HANDOFF.mdを作成しました」と報告してください。各項目には、現在までのチャット履歴や作業内容からAI自身が自己の行動を要約し、具体的な内容を記入してから保存してください。単なる空のテンプレートのまま保存してはいけません。

---
# HANDOFF - {日時}

## 使用ツール
Claude Code / Codex CLI / Gemini CLI など、該当するツール名を記載

## 現在のタスクと進捗
- [ ] タスク名：現在の状況

## 試したこと・結果
- 成功したアプローチ
- 失敗したアプローチ（理由）

## 次のセッションで最初にやること
1. 最初のアクション
2. 次のアクション

## 注意点・ブロッカー
- 注意すべき事項
---
```

## A-8. Git初期化

### .gitignore の作成
```
# Logs
logs
*.log

node_modules
dist
dist-ssr
*.local

# Editor directories and files
.vscode/*
!.vscode/extensions.json
.idea
.DS_Store
.env
```

### Git初期化とpush
```bash
git init
git add .
git commit -m "first commit"
git remote add origin [USER_INPUT]
git push -u origin main
```

## A-9. 完了報告

全手順完了後、以下を報告する：
- 作成したファイル・フォルダの一覧
- GitHubへのpush結果
- 次のステップの案内（「一旦このプロジェクトを終了し、新規作成したプロジェクトに入り直して下さい。新規プロジェクトのAGENTS.mdにプロジェクト概要を記載し、PLAN.mdにやりたいことを書いてください」など）

---

# モードB：既存プロジェクトのアップデート

## B-1. 現状の精査

本スキル（make_project）のモードAのA-3以降に記載されているすべての要素を正として、
現在のプロジェクトフォルダの状態と照合し、不足・未作成の要素をリストアップする。

精査完了後、以下を報告する：
「以下の差分が見つかりました。アップデートを適用してよいですか？
- 追加・作成するもの：[不足している要素の一覧]
- スキップするもの（既存）：[すでに存在する要素の一覧]」

ユーザーの承認を得てから B-2 に進む。

## B-2. 差分の適用

B-1で不足と判定された要素のみ、モードAの対応する手順を実行する。
既存ファイル・フォルダは上書きしない。
AGENTS.mdへの追記は既存内容と重複しないよう確認してから行う。

## B-3. 完了報告

適用した内容とスキップした内容の一覧を報告する。

---

# モードC：対話

ユーザーの相談内容をヒアリングし、このスキルの範囲でできることを提案する。
必要に応じてモードAまたはモードBへ誘導する。
