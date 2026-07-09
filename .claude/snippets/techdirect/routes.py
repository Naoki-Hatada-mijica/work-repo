"""Known TechDirect page-type routes for non-destructive catalog probes."""

from __future__ import annotations

from dataclasses import dataclass

ORG_ID = "39336"


@dataclass(frozen=True)
class RouteSpec:
    name: str
    path: str
    category: str
    detail_kind: str = ""
    menu_triggers: tuple[str, ...] = ()


URL_PORTAL = f"/orgs/{ORG_ID}/portal/"

ROUTES: list[RouteSpec] = [
    RouteSpec("公開案件検索", "/jobs", "public_jobs", "job"),
    RouteSpec("公開会社案件一覧", f"/orgs/{ORG_ID}/jobs", "public_org_jobs", "job"),
    RouteSpec("採用管理ダッシュボード", URL_PORTAL, "dashboard"),
    RouteSpec("旧ダッシュボード", f"{URL_PORTAL}old-dashboard", "legacy_dashboard"),
    RouteSpec("旧統計ダッシュボード", f"{URL_PORTAL}dashboard", "legacy_dashboard"),
    RouteSpec("統計一覧", f"{URL_PORTAL}analysis", "analytics"),
    RouteSpec("メッセージ/応募一覧", f"{URL_PORTAL}applications/", "applications", "application"),
    RouteSpec("採用実績一覧", f"{URL_PORTAL}accepted-users", "accepted_users", "candidate"),
    RouteSpec("案件管理一覧", f"{URL_PORTAL}jobs", "portal_jobs", "job", ("メニューを開く",)),
    RouteSpec("案件新規作成", f"{URL_PORTAL}jobs/new", "job_form"),
    RouteSpec("スカウト候補者一覧", f"{URL_PORTAL}job-seekers-tabular", "candidates", "candidate", ("条件追加", "編集", "リスト追加")),
    RouteSpec("求職者リスト管理", f"{URL_PORTAL}job-seeker-lists", "job_seeker_lists", "", ("メニューを開く",)),
    RouteSpec("求職者リスト新規作成", f"{URL_PORTAL}job-seeker-lists/new", "job_seeker_list_form"),
    RouteSpec("採用ステータス一覧", f"{URL_PORTAL}recruitment-statuses", "recruitment_statuses", "", ("メニューを開く",)),
    RouteSpec("採用ステータス新規作成", f"{URL_PORTAL}recruitment-statuses/new", "recruitment_status_form"),
    RouteSpec("メッセージ定型文一覧", f"{URL_PORTAL}message-templates", "message_templates", "", ("メニューを開く",)),
    RouteSpec("メッセージ定型文新規作成", f"{URL_PORTAL}message-templates/new", "message_template_form"),
    RouteSpec("スカウト定型文一覧", f"{URL_PORTAL}scout-templates", "scout_templates", "", ("メニューを開く",)),
    RouteSpec("スカウト定型文新規作成", f"{URL_PORTAL}scout-templates/new", "scout_template_form"),
    RouteSpec("担当者一覧", f"{URL_PORTAL}recruiters", "recruiters", "", ("メニューを開く",)),
    RouteSpec("会社情報編集", f"{URL_PORTAL}edit", "org_edit"),
    RouteSpec("プラン情報", f"{URL_PORTAL}plan", "plan"),
]
