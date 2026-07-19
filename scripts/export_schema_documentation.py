"""Xuất schema SQLite hiện hành thành JSON và từ điển dữ liệu dễ đọc."""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils.cli import VietnameseArgumentParser


def schema_catalog() -> dict:
    from src.db.migrations import current_schema_version
    from src.db.schema import create_schema

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    create_schema(conn)
    tables = []
    names = [row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )]
    for name in names:
        columns = [dict(row) for row in conn.execute(f'PRAGMA table_info("{name}")')]
        foreign_keys = [dict(row) for row in conn.execute(f'PRAGMA foreign_key_list("{name}")')]
        indexes = []
        for index_row in conn.execute(f'PRAGMA index_list("{name}")'):
            index = dict(index_row)
            index["columns"] = [row[2] for row in conn.execute(f'PRAGMA index_info("{index["name"]}")')]
            indexes.append(index)
        tables.append({"name": name, "columns": columns, "foreign_keys": foreign_keys, "indexes": indexes})
    version = current_schema_version(conn)
    conn.close()
    return {"schema_version": version, "source": "src/db/schema.py + src/db/migrations.py",
            "runtime_data_included": False, "tables": tables}


def markdown(catalog: dict) -> str:
    lines = ["# Từ điển dữ liệu SQLite MP2027", "",
             "> Được tạo từ cơ sở dữ liệu trong bộ nhớ. Không đọc hoặc đưa dữ liệu người dùng/runtime vào báo cáo.", "",
             f"Phiên bản schema: **{catalog['schema_version']}**", "", "## Quan hệ thực thể", "",
             "```mermaid", "erDiagram"]
    relationships = []
    for table in catalog["tables"]:
        for fk in table["foreign_keys"]:
            relationships.append(f"    {fk['table']} ||--o{{ {table['name']} : {fk['from']}")
    lines.extend(relationships or ["    dim_cost_centers ||--o{ fact_allocation_log : dest_cc"])
    lines += ["```", "", "## Nhóm bảng", "",
              "- `dim_*`: các danh mục tham khảo.", "- `map_*`: ánh xạ nghiệp vụ và điều kiện áp dụng.",
              "- `fact_*`: đầu vào chuẩn hóa, yếu tố phân bổ, phép tính và dữ liệu thiếu.",
              "- `audit_*`: bản ghi truy vết/bằng chứng; không phải đầu vào tính toán chính.",
              "- `sys_*` và `schema_migrations`: cấu hình ứng dụng và vòng đời schema.", ""]
    for table in catalog["tables"]:
        lines += [f"## `{table['name']}`", "", "| Cột | Kiểu | Bắt buộc | Khóa chính | Mặc định |",
                  "|---|---|---:|---:|---|"]
        for col in table["columns"]:
            default = str(col["dflt_value"] or "").replace("|", "/")
            lines.append(f"| `{col['name']}` | `{col['type'] or 'ANY'}` | {'có' if col['notnull'] else 'không'} | {'có' if col['pk'] else 'không'} | `{default}` |")
        if table["foreign_keys"]:
            lines += ["", "Khóa ngoại:"]
            for fk in table["foreign_keys"]:
                lines.append(f"- `{fk['from']}` -> `{fk['table']}.{fk['to']}`")
        lines.append("")
    lines += ["## Tạo lại tài liệu", "", "```powershell", "py scripts/export_schema_documentation.py", "```", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = VietnameseArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, default=ROOT / "docs" / "database" / "schema_catalog.json")
    parser.add_argument("--markdown", type=Path, default=ROOT / "docs" / "database" / "data_dictionary.md")
    args = parser.parse_args(argv)
    catalog = schema_catalog()
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(markdown(catalog), encoding="utf-8")
    print(f"Đã xuất {len(catalog['tables'])} bảng (schema phiên bản {catalog['schema_version']}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
