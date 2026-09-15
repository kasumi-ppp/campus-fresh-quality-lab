"""Check whether the manual test-case workbook is ready for submission.

The workbook intentionally leaves execution fields for members to complete.
This script only checks completeness; it does not generate or execute cases.
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
TEXT_TAG = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t"
REQUIRED = ("F", "G", "H", "I", "J", "K", "L", "M")


def read_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    """读取共享字符串表。

    Excel 保存工作簿时会把单元格文本集中存到 sharedStrings.xml，单元格里只留下
    一个数字下标。不解析这张表就会把下标当成内容读出来。
    """
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    return [
        "".join(node.text or "" for node in item.iter(TEXT_TAG))
        for item in root.findall("x:si", NS)
    ]


def cell_value(cell: ET.Element, shared: list[str]) -> str:
    kind = cell.attrib.get("t")
    if kind == "s":
        value = cell.find("x:v", NS)
        if value is None or value.text is None:
            return ""
        index = int(value.text)
        return shared[index].strip() if 0 <= index < len(shared) else ""
    if kind == "inlineStr":
        inline = cell.find("x:is", NS)
        if inline is None:
            return ""
        return "".join(node.text or "" for node in inline.iter(TEXT_TAG)).strip()
    value = cell.find("x:v", NS)
    return "" if value is None or value.text is None else value.text.strip()


def read_case_rows(workbook: Path) -> list[dict[str, str]]:
    with zipfile.ZipFile(workbook) as archive:
        shared = read_shared_strings(archive)
        sheet = ET.fromstring(archive.read("xl/worksheets/sheet2.xml"))

    rows: list[dict[str, str]] = []
    for row in sheet.findall("x:sheetData/x:row", NS):
        row_number = int(row.attrib["r"])
        if row_number == 1:
            continue
        values = {}
        for cell in row.findall("x:c", NS):
            ref = cell.attrib.get("r", "")
            column = "".join(char for char in ref if char.isalpha())
            values[column] = cell_value(cell, shared)
        if values.get("A"):
            values["_row"] = str(row_number)
            rows.append(values)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "workbook",
        nargs="?",
        type=Path,
        default=Path("docs/testing/module1-manual-test-case-matrix.xlsx"),
    )
    parser.add_argument("--strict", action="store_true", help="fail unless at least 30 complete cases exist")
    args = parser.parse_args()

    if not args.workbook.exists():
        print(f"workbook not found: {args.workbook}", file=sys.stderr)
        return 2

    rows = read_case_rows(args.workbook)
    complete = [row for row in rows if all(row.get(column, "") for column in REQUIRED)]
    incomplete = [row for row in rows if row not in complete]
    executed = [row for row in complete if row.get("L") in {"通过", "失败", "阻塞"}]
    methods = sorted({row.get("E", "") for row in executed if row.get("E")})

    print(f"framework_rows={len(rows)}")
    print(f"complete_rows={len(complete)}")
    print(f"executed_rows={len(executed)}")
    print(f"methods={','.join(methods) or '(none)'}")
    if incomplete:
        preview = ", ".join(f"{row.get('A')} (row {row.get('_row')})" for row in incomplete[:8])
        print(f"incomplete_preview={preview}")

    if args.strict and len(executed) < 30:
        print("FAIL: fewer than 30 complete executed manual cases", file=sys.stderr)
        return 1
    print("PASS: completeness threshold met" if len(executed) >= 30 else "CHECK: member execution still required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
