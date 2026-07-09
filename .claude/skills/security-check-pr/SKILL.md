---
name: security-check-pr
description: PR (現在のブランチ) のセキュリティチェックを行う。静的スキャナ (Trivy / gitleaks / Checkov) を blocking 判定、LLM (/security-review) を warn-only として並列実行し、critical / high / medium / low に分類して提示する。「/security-check-pr」「PR のセキュリティチェック」「push 前にスキャン」などのリクエストに対して使用すること。
---

# security-check-pr スキル

C-1: PR pre-push チェックの Claude Code 経由インターフェイス。
本体は `/usr/local/share/security-audit/scripts/c1-pr-check.sh` (root 所有 chmod 755) または開発時は `~/tools/security-audit/scripts/c1-pr-check.sh`。

## 設計原則

- **静的スキャナ (Trivy / gitleaks / Checkov) = blocking**: critical 検出で exit 2 → push 中止
- **LLM (`/security-review`) = warn-only**: 決して exit 1 を返さない（false positive で push 不能になる事故防止）
- **`SKIP_SECURITY_CHECK=1 SKIP_REASON='reason' git push`** で bypass 可能、Slack 通知 + bypass.log に記録

## 前提

- `mijica-inc/security-audit` リポが clone 済み（`~/tools/security-audit/` 推奨）
- `bootstrap-machine.sh` 実行済み（root 所有 path に script install + `core.hooksPath` 設定）
- mac の場合: `brew install coreutils` で gtimeout を install 済（pre-push hook の hard timeout 60s 用）

## 手順

### 引数なしで起動された場合

`c1-pr-check.sh` を実行し、結果を要約する:

```bash
bash /usr/local/share/security-audit/scripts/c1-pr-check.sh \
  || bash ~/tools/security-audit/scripts/c1-pr-check.sh
```

exit code:
- 0 = pass
- 1 = warn のみ (push 許可)
- 2 = critical 静的検出 (push 中止)
- 124 = timeout (warn 扱い、push 許可)

### 結果の整形

c1-pr-check.sh の stderr 出力（`[c1] Trivy critical: N` 等）と最終 `[c1] critical=N warn=N` を読み、以下の形式で表示:

```
## C-1 PR セキュリティチェック結果

### Critical (blocking 対象)
- (各項目を 1 行ずつ)

### Warn (push 許可)
- (各項目を 1 行ずつ)

### 推奨アクション
- critical があれば修正案を提示（`docs/critical-criteria.md` 参照）
- 緊急時の bypass: `SKIP_SECURITY_CHECK=1 SKIP_REASON='hotfix-XXX' git push`
```

### --headless フラグの注意

Phase 1 で確認済み: `claude` CLI に `--headless` は **存在しない**。pre-push hook は `claude -p --bare --no-session-persistence --max-budget-usd 0.10 --output-format json --permission-mode bypassPermissions '/security-review'` の形で隔離実行する。本 skill 起動時はユーザーが Claude Code を対話で開いている状態なので、通常の `/security-review` を呼び出して構わない。

### critical 判定基準

`mijica-inc/security-audit/docs/critical-criteria.md` の定義に従う:

1. ハードコードされた credential / API key (gitleaks 検出)
2. SQL injection / command injection の決定論的パターン
3. `0.0.0.0` / `[::]` への port 公開 (Trivy config)
4. IaC misconfig (public S3 / open security group / Checkov CRITICAL)
5. postgres `COPY ... TO PROGRAM` 等の dangerous SQL
6. `eval` / `exec` の不審な使用

これらは **静的解析側で blocking**。LLM 判定は warn-only。

## 注意

- **本 skill は Mac 限定**（サーバ側は `bash run-machine-audit.sh` 直接実行）
- ネットワーク切断 / API 不通時は LLM は warn のみ、静的スキャナのみで判定
- 本 skill は `/security-check-pr` で起動可能、または pre-push hook 経由で push 時に自動起動
