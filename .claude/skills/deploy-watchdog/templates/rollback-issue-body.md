[CC]

deploy.yml の run #{{run_id}} が conclusion=failure で終了しました。

- failed commit: {{commit_sha}}
- failed PR: #{{merged_pr_number}}
- workflow run: {{workflow_run_url}}
- environment: {{environment}}

以下を実行してください:
1. 最後に成功した commit (= one before merged) に revert する PR を作成
2. revert PR の body に `Reverts #{{merged_pr_number}}` を含める
3. revert PR は `[deploy-ok]` label を operator が貼ってから merge

---
source: deploy-watchdog:run-{{run_id}}
fingerprint: deploy-wd:{{repo}}:deploy:{{environment}}
