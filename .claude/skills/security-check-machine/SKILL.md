---
name: security-check-machine
description: マシン全体のセキュリティ監査を実行する (B 層)。listen ports / docker bind / weak credentials / 不審プロセス / persistence (cron, systemd, launchd, authorized_keys, sudoers, ld.so.preload) を OS 別 (mac/Linux) に check し、Tier1 (事故由来 / 最優先) と Tier2 (一般) に分類して提示する。「/security-check-machine」「マシン監査」「サーバ audit」などのリクエストに対して使用すること。
---

# security-check-machine スキル

B 層: マシン全体監査の Claude Code 経由インターフェイス。
本体は `~/tools/security-audit/scripts/run-machine-audit.sh`。

## 設計原則

- **OS 判定で `lib/macos.sh` または `lib/linux.sh` を source**
- **共通 JSON インタフェース**: 各 check は `{check, tier, severity, findings}` を stdout に
- **集約 Markdown レポート**: `~/.local/state/security-audit/report-YYYY-MM-DD.md` に `chmod 600` で保存（IOC を含むため）
- **Tier 1 (事故由来)**: listen ports / docker bind / weak credentials / 不審プロセス / SUID baseline diff
- **Tier 2 (一般)**: persistence / package security updates / firewall / auth log / SSH 設定 / rkhunter / Lynis / osquery

## 前提

- `mijica-inc/security-audit` リポが clone 済み（`~/tools/security-audit/`）
- `bootstrap-machine.sh` 実行済み
- Mac: `brew install` で coreutils / jq / lynis / trivy / gitleaks
- Linux サーバ: `apt install` で coreutils / jq / python3 / lynis / rkhunter

## 手順

### 引数なしで起動された場合

`run-machine-audit.sh` を実行し、結果 JSON を Markdown 化して提示:

```bash
bash ~/tools/security-audit/scripts/run-machine-audit.sh
```

stdout に出力された JSON 配列を読み、以下の順で要約:

1. **Tier 1 critical** (最優先、事故由来)
2. **Tier 1 high / medium / low**
3. **Tier 2 critical** (一般)
4. **Tier 2 high / medium / low**
5. info はサマリで件数のみ

### `--baseline` 引数

初回 SUID baseline 取得モード:

```bash
bash ~/tools/security-audit/scripts/run-machine-audit.sh --baseline
```

`~/.local/state/security-audit/suid-baseline.txt` を作成して終了。次回以降の audit で baseline 差分を `suid_baseline_diff` check が high として報告。

### `--notify-slack` 引数

systemd timer (B 層 user service) から呼ばれる時の挙動:

```bash
bash ~/tools/security-audit/scripts/run-machine-audit.sh --notify-slack
```

Tier 1 critical があれば Slack 通知（`$SLACK_WEBHOOK_NOTIFICATION_URL` 必須）。手動起動時は通常不要。

## レポート整形

```
## B 層マシン監査結果 (host=$(hostname), $(date -u +%FT%TZ))

### Tier 1 critical (事故由来 / 最優先)
- listen_ports: 0.0.0.0:5432 postgres (container db-1)
- docker_bind: 0.0.0.0:8080:80 nginx-1
- weak_credentials: POSTGRES_PASSWORD = <weak password matched dictionary>

### Tier 1 high
- suid_baseline_diff: /tmp/test-suid (new SUID, baseline 差分)

### Tier 2
- persistence_cron: 5 entries (no anomaly)
- package_security_updates: 3 security updates available
- ...

### 推奨アクション
- listen_ports critical: docker-compose.yml の `ports: "5432:5432"` を `ports: "127.0.0.1:5432:5432"` に変更
- weak_credentials: POSTGRES_PASSWORD を強い random password に変更（dictionary に含まれない値）
```

## 出力先

`~/.local/state/security-audit/report-$(date -u +%Y-%m-%d).md` (chmod 600)

ファイル冒頭には `# DO NOT COMMIT - contains IOC` magic comment。`~/.gitignore_global` で誤 commit 防止。

## 注意

- 本 skill は **Mac 用ラッパ**。サーバ (claude-vps / aiseki 本番) は systemd timer が直接 `run-machine-audit.sh --notify-slack` を呼ぶ
- mac で `find / -xdev -perm -4000` は数十秒かかる（SUID baseline 取得時）
- D 層 (runtime-monitor) とは別: D は root 実行で 1 時間ごと、本 skill は user 実行で 30 日警告ベース手動
- 異常系: Lynis 不在 / osquery 不在 → skip + warn のみ
