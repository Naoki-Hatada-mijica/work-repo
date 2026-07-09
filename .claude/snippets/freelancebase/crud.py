"""Safety primitives for FreelanceBase create/update/delete automation.

This module does not perform writes. It standardizes previews, dry-run results,
and operation logs so task-specific scripts can enforce the same safety checks.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class FieldChange:
    field: str
    before: Any
    after: Any

    @property
    def changed(self) -> bool:
        return self.before != self.after


@dataclass(frozen=True)
class OperationPreview:
    action: str
    target_url: str
    target_id: str | int | None
    resource: str
    endpoint: str
    method: str
    changes: list[FieldChange] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def changed_fields(self) -> list[FieldChange]:
        return [change for change in self.changes if change.changed]

    @property
    def is_destructive(self) -> bool:
        return self.method.upper() in {"POST", "PUT", "PATCH", "DELETE"}

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def render(self) -> str:
        lines = [
            f"action: {self.action}",
            f"resource: {self.resource}",
            f"target: {self.target_url}",
            f"target_id: {self.target_id}",
            f"api: {self.method.upper()} {self.endpoint}",
        ]
        if self.warnings:
            lines.append("warnings:")
            lines.extend(f"- {warning}" for warning in self.warnings)
        lines.append("changes:")
        if not self.changes:
            lines.append("- none")
        else:
            for change in self.changes:
                marker = "changed" if change.changed else "unchanged"
                lines.append(
                    f"- {change.field}: {change.before!r} -> {change.after!r} ({marker})"
                )
        return "\n".join(lines)


@dataclass(frozen=True)
class OperationResult:
    preview: OperationPreview
    dry_run: bool
    executed: bool
    status: int | None = None
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def dry_run_result(preview: OperationPreview, message: str = "dry-run: not executed") -> OperationResult:
    return OperationResult(preview=preview, dry_run=True, executed=False, message=message)


def require_explicit_write(*, dry_run: bool, approved: bool, action: str) -> None:
    """Raise unless a write operation has explicit approval."""
    if dry_run:
        return
    if not approved:
        raise RuntimeError(f"{action} requires explicit approval")


def write_operation_log(result: OperationResult, path: str | Path) -> Path:
    """Append a JSONL operation log entry without secrets or raw response bodies."""
    out = Path(path).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "logged_at": datetime.now().isoformat(timespec="seconds"),
        **result.to_dict(),
    }
    with out.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return out

