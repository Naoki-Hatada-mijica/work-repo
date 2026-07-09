"""FreelanceBase 案件（jobs）読み取りヘルパー（読み取り専用）。

`fetch_view_jobs()` は保存済みビュー（例: 「募集中エンド直案件」= view-105）の
案件一覧を全件取得する。ビューは enterprise member ごとに共有設定があり、
未共有のメンバーで開くと既定ビュー（#view-3 全ての案件）にフォールバックする。
そのため、ビューが実際に適用されたことを以下で検証してから案件を返す:

  1. 最終 URL のハッシュが `#view-<id>` であること
  2. （ラベル指定時）ビュータブのラベルが DOM に存在すること
  3. `/api/enterprise/jobs/index` の payload に view の `conditions` が入っていること

初回ロード時のリクエストはビュー適用前（conditions 空）であることがあるため、
ビュータブをクリックし、conditions 非空のリクエストを採用する。
"""

from __future__ import annotations

import copy
import json
from typing import Any

from .api import enterprise_auth_headers, fetch_json
from .core import BASE_URL

JOBS_URL = f"{BASE_URL}/enterprise/jobs"
JOBS_INDEX_ENDPOINT = "/api/enterprise/jobs/index"


def _names(d: Any) -> list[str]:
    if not isinstance(d, dict):
        return []
    return [v.get("name") for v in d.values() if isinstance(v, dict) and v.get("name")]


def clean_job(j: dict) -> dict:
    """案件レコードからマッチング・診断に必要な項目だけ抽出する。"""
    return {
        "id": j.get("id_by_enterprise_id") or j.get("id"),
        "title": j.get("name") or j.get("title"),
        "detail": j.get("detail"),
        "required": j.get("required"),
        "welcome": j.get("welcome"),
        "skill_desc": j.get("skill_desc"),
        "monthly_price_from": j.get("monthly_price_f_num"),
        "monthly_price_to": j.get("monthly_price_l_num"),
        "monthly_payment_from": j.get("monthly_payment_f_num"),
        "monthly_payment_to": j.get("monthly_payment_l_num"),
        "expected_age_min": j.get("expected_age_min"),
        "expected_age_max": j.get("expected_age_max"),
        "accept_foreigner_type_id": j.get("accept_foreigner_type_id"),
        "inception_day": j.get("inception_day"),
        "work_style": _names(j.get("work_styles_key_values")),
        "business_day": _names(j.get("business_day_key_values")),
        "company": _names(j.get("company_id_by_enterprise_key_values")),
        "prefecture": _names(j.get("prefecture_key_values")),
        "skills": _names(j.get("skill_key_values")),
        "occupation": _names(j.get("occupation_key_values")),
        "dev_process": _names(j.get("dev_process_key_values")),
        "working_schedule": j.get("working_schedule"),
    }


def fetch_view_jobs(
    page: Any,
    view_id: int | str,
    *,
    expected_label: str | None = None,
    max_pages: int = 30,
    raw: bool = False,
    settle_ms: int = 3000,  # SPA 初期ロード後、jobs/index リクエストが飛ぶまでの待機
    click_ms: int = 4000,  # ビュータブ click 後、conditions 付きで再描画されるまでの待機
) -> tuple[list[dict], dict]:
    """保存済みビューの案件を全件取得する。

    ビュー適用を検証できた場合のみ案件を返す。検証できないとき（conditions 未捕捉、
    URL がビューに切り替わらない）は RuntimeError を送出する（未共有ビューを
    既定ビューと取り違えて全件返すことを防ぐ）。

    Returns:
        (jobs, verification)
        - jobs: `raw=False` なら `clean_job()` 済みの dict 配列、`raw=True` なら生レコード
        - verification: 検証情報（final_url / applied_conditions / fetched / total など）
    """
    captured: list[dict] = []

    def on_request(req: Any) -> None:
        if JOBS_INDEX_ENDPOINT in req.url and req.method == "POST":
            try:
                payload = json.loads(req.post_data or "{}")
            except Exception:
                payload = {}
            captured.append({"headers": dict(req.headers), "payload": payload})

    page.on("request", on_request)
    try:
        page.goto(f"{JOBS_URL}#view-{view_id}", wait_until="networkidle")
        page.wait_for_timeout(settle_ms)

        label_count = 0
        if expected_label:
            label = page.get_by_text(expected_label)
            label_count = label.count()
            if label_count:
                # 初回リクエストはビュー適用前のことがあるため、タブを明示クリックする
                label.first.click()
                page.wait_for_timeout(click_ms)

        with_cond = [c for c in captured if c["payload"].get("conditions")]
        verification = {
            "final_url": page.url,
            "view_id": str(view_id),
            "expected_label": expected_label,
            "label_visible_elements": label_count,
            "jobs_index_requests": len(captured),
            "requests_with_conditions": len(with_cond),
            "applied_conditions": (
                [
                    {"name": c.get("name"), "values": c.get("value")}
                    for c in (with_cond[-1]["payload"].get("conditions") or [])
                ]
                if with_cond
                else None
            ),
        }

        if not with_cond:
            raise RuntimeError(
                f"view-{view_id} の適用を検証できません（conditions 未捕捉）。"
                f" 当該ビューがログイン中アカウントに共有されているか確認してください。"
                f" final_url={page.url}"
            )
        if f"#view-{view_id}" not in (page.url or ""):
            raise RuntimeError(
                f"view-{view_id} への切り替えを確認できません（未共有だと #view-3 等に"
                f" フォールバックします）。final_url={page.url}"
            )

        auth = enterprise_auth_headers(with_cond[-1]["headers"])
        payload = with_cond[-1]["payload"]

        jobs: list[dict] = []
        total: Any = None
        page_no = 1
        while True:
            pl = copy.deepcopy(payload)
            pl["page"] = page_no
            res = fetch_json(
                page,
                endpoint=JOBS_INDEX_ENDPOINT,
                method="POST",
                auth=auth,
                payload=pl,
                dry_run=False,
                read_only=True,
            )
            if res.get("status") != 200:
                raise RuntimeError(
                    f"jobs/index status={res.get('status')} page={page_no}"
                )
            body = res.get("body") or {}
            if page_no == 1:
                total = body.get("total")
            batch = body.get("jobs") or []
            if not batch:
                break
            jobs.extend(batch)
            if isinstance(total, int) and len(jobs) >= total:
                break
            if page_no >= max_pages:
                break
            page_no += 1

        verification["fetched"] = len(jobs)
        verification["total"] = total
        if not raw:
            jobs = [clean_job(j) for j in jobs]
        return jobs, verification
    finally:
        page.remove_listener("request", on_request)
