"""Reusable FreelanceBase automation helpers."""

from .core import (
    BASE_URL,
    CANDIDATES_URL,
    COMPANIES_URL,
    ENTERPRISE_API_PREFIX,
    LOGIN_URL,
    LoginOptions,
    build_url,
    candidate_detail_url,
    company_detail_url,
    goto,
)
from .crud import FieldChange, OperationPreview, OperationResult, dry_run_result
from .jobs import JOBS_INDEX_ENDPOINT, JOBS_URL, clean_job, fetch_view_jobs

__all__ = [
    "BASE_URL",
    "CANDIDATES_URL",
    "COMPANIES_URL",
    "ENTERPRISE_API_PREFIX",
    "LOGIN_URL",
    "LoginOptions",
    "build_url",
    "candidate_detail_url",
    "company_detail_url",
    "goto",
    "FieldChange",
    "OperationPreview",
    "OperationResult",
    "dry_run_result",
    "JOBS_URL",
    "JOBS_INDEX_ENDPOINT",
    "clean_job",
    "fetch_view_jobs",
]
