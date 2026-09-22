"""Validate manual-test evidence paths recorded in the Excel matrix.

The checker does not decide whether a screenshot proves a result. It verifies
the auditable parts of the submission: executed rows have evidence paths,
referenced media exists inside the evidence directory, and the strict
submission threshold is met.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from check_manual_cases import read_case_rows


DEFAULT_WORKBOOK = Path("docs/testing/module1-manual-test-case-matrix.xlsx")
DEFAULT_EVIDENCE = Path("docs/testing/evidence")
EXECUTED_STATES = {"通过", "失败", "阻塞"}
MEDIA_SUFFIXES = {
    ".bmp",
    ".gif",
    ".jpeg",
    ".jpg",
    ".m4v",
    ".mov",
    ".mp4",
    ".png",
    ".webm",
    ".webp",
}


def split_evidence_paths(value: str) -> list[str]:
    """Accept the workbook's newline-separated evidence path convention."""
    return [item.strip() for item in value.replace("\r", "\n").split("\n") if item.strip()]


def resolve_evidence_path(raw: str, project_root: Path, evidence_root: Path) -> Path | None:
    """Resolve a workbook path while preventing references outside evidence/."""
    candidate = Path(raw)
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        resolved = (project_root / candidate).resolve()

    try:
        resolved.relative_to(evidence_root.resolve())
    except ValueError:
        return None
    return resolved


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", nargs="?", type=Path, default=DEFAULT_WORKBOOK)
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        default=DEFAULT_EVIDENCE,
        help="directory containing screenshots and recordings",
    )
    parser.add_argument("--strict", action="store_true", help="require at least 30 valid executed cases")
    args = parser.parse_args()

    workbook = args.workbook.resolve()
    project_root = Path.cwd().resolve()
    evidence_root = args.evidence_dir.resolve()
    if not workbook.exists():
        print(f"workbook not found: {args.workbook}", file=sys.stderr)
        return 2
    if not evidence_root.is_dir():
        print(f"evidence directory not found: {args.evidence_dir}", file=sys.stderr)
        return 2

    rows = read_case_rows(workbook)
    executed = [row for row in rows if row.get("L", "") in EXECUTED_STATES]
    missing: list[str] = []
    invalid: list[str] = []
    valid_rows = 0

    for row in executed:
        case_id = row.get("A", "(unknown)")
        paths = split_evidence_paths(row.get("M", ""))
        if not paths:
            missing.append(f"{case_id}: evidence path is empty")
            continue

        row_valid = True
        for raw in paths:
            resolved = resolve_evidence_path(raw, project_root, evidence_root)
            if resolved is None:
                invalid.append(f"{case_id}: outside evidence directory: {raw}")
                row_valid = False
                continue
            if resolved.suffix.lower() not in MEDIA_SUFFIXES:
                invalid.append(f"{case_id}: unsupported media type: {raw}")
                row_valid = False
            elif not resolved.is_file():
                missing.append(f"{case_id}: file not found: {raw}")
                row_valid = False
        if row_valid:
            valid_rows += 1

    print(f"framework_rows={len(rows)}")
    print(f"executed_rows={len(executed)}")
    print(f"valid_evidence_rows={valid_rows}")
    print(f"missing_evidence={len(missing)}")
    print(f"invalid_evidence={len(invalid)}")
    for item in (missing + invalid)[:20]:
        print(f"issue={item}")

    if args.strict and (len(executed) < 30 or valid_rows < 30 or missing or invalid):
        print("FAIL: strict manual evidence requirements are not met", file=sys.stderr)
        return 1
    if missing or invalid:
        print("FAIL: evidence references need attention", file=sys.stderr)
        return 1
    print("PASS: manual evidence references are valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
