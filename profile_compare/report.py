"""Render a list of Difference records as a self-contained HTML page."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime
from html import escape

from profile_compare.differ import Difference, Kind

KIND_LABELS: dict[Kind, str] = {
    "only_in_a": "only in A",
    "only_in_b": "only in B",
    "changed": "changed",
}

_CSS = """
body { font-family: system-ui, sans-serif; margin: 2rem; color: #222; }
h1 { font-size: 1.5rem; }
table { border-collapse: collapse; margin-bottom: 1.5rem; }
th, td { border: 1px solid #ccc; padding: 0.3rem 0.6rem; text-align: left; vertical-align: top; font-size: 0.9rem; }
th { background: #f0f0f0; }
tr.muted td { color: #999; }
tr.only_in_a td { background: #e6f4ea; }
tr.only_in_b td { background: #e8f0fe; }
tr.changed  td { background: #fef3e0; }
details { margin-bottom: 1rem; }
summary { cursor: pointer; font-weight: 600; font-size: 1.05rem; padding: 0.3rem 0; }
.warnings { background: #fff4e5; border: 1px solid #f0c36d; padding: 0.6rem 1rem; margin-bottom: 1.5rem; }
.meta { color: #666; font-size: 0.85rem; }
"""


def render(
    diffs: list[Difference],
    *,
    name_a: str,
    name_b: str,
    sections: Iterable[str],
    warnings: Iterable[str] = (),
) -> str:
    """Build the full HTML document as a string."""
    by_section: dict[str, list[Difference]] = defaultdict(list)
    for d in diffs:
        by_section[d.section].append(d)
    section_names = sorted(set(sections) | set(by_section))
    warnings = list(warnings)

    parts = [
        "<!DOCTYPE html>",
        '<html lang="en"><head><meta charset="utf-8">',
        "<title>Profile compare</title>",
        f"<style>{_CSS}</style></head><body>",
        "<h1>Salesforce profile comparison</h1>",
        f'<p class="meta"><b>A:</b> {escape(name_a)} &nbsp; <b>B:</b> {escape(name_b)}'
        f" &nbsp; generated {datetime.now():%Y-%m-%d %H:%M}</p>",
    ]

    if warnings:
        parts.append('<div class="warnings"><b>Warnings</b><ul>')
        parts.extend(f"<li>{escape(w)}</li>" for w in warnings)
        parts.append("</ul></div>")

    if not diffs:
        parts.append("<p><b>No differences found.</b></p>")

    parts.append(_summary_table(section_names, by_section))
    for section in section_names:
        if by_section[section]:
            parts.append(_section_details(section, by_section[section], name_a, name_b))

    parts.append("</body></html>")
    return "\n".join(parts)


def _summary_table(section_names: list[str], by_section: dict[str, list[Difference]]) -> str:
    rows = [
        "<h2>Summary</h2>",
        "<table><thead><tr><th>Section</th><th>Only in A</th><th>Only in B</th>"
        "<th>Changed</th><th>Total</th></tr></thead><tbody>",
    ]
    for section in section_names:
        section_diffs = by_section[section]
        counts = {kind: sum(1 for d in section_diffs if d.kind == kind) for kind in KIND_LABELS}
        css = "section-row muted" if not section_diffs else "section-row"
        rows.append(
            f'<tr class="{css}"><td>{escape(section)}</td>'
            f"<td>{counts['only_in_a']}</td><td>{counts['only_in_b']}</td>"
            f"<td>{counts['changed']}</td><td>{len(section_diffs)}</td></tr>"
        )
    rows.append("</tbody></table>")
    return "\n".join(rows)


def _section_details(
    section: str, section_diffs: list[Difference], name_a: str, name_b: str
) -> str:
    rows = [
        f'<details open id="section-{escape(section)}">',
        f"<summary>{escape(section)} ({len(section_diffs)})</summary>",
        f"<table><thead><tr><th>Key</th><th>Attribute</th><th>{escape(name_a)}</th>"
        f"<th>{escape(name_b)}</th><th>Kind</th></tr></thead><tbody>",
    ]
    for d in section_diffs:
        rows.append(
            f'<tr class="{d.kind}"><td>{escape(d.key)}</td>'
            f"<td>{escape(d.attribute or '')}</td>"
            f"<td>{escape(d.value_a or '')}</td>"
            f"<td>{escape(d.value_b or '')}</td>"
            f"<td>{KIND_LABELS[d.kind]}</td></tr>"
        )
    rows.append("</tbody></table></details>")
    return "\n".join(rows)
