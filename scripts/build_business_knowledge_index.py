"""Build script for MP2027 Document-grounded RAG v3 index.

Reads approved sources from docs/knowledge/business_chat/source_inventory.json
and generates docs/knowledge/business_chat/knowledge_index.json.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path
root = Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from src.services.business_knowledge_index import build_index_data, save_index
from scripts.build_coverage_evidence_report import generate_coverage_evidence_report


def main() -> int:
    print("Building MP2027 Document-grounded RAG v3 index...")
    try:
        data = build_index_data(root)
        out = save_index(data)
        print(f"Successfully built index with {data.get('total_chunks', 0)} chunks at {out}")

        # Also build and update coverage evidence report
        report = generate_coverage_evidence_report()
        print(f"Coverage & Evidence Report status: {report['status']} ({report['metrics']['evidence_coverage_percentage']}%)")
        return 0
    except Exception as exc:
        print(f"Error building knowledge index: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
