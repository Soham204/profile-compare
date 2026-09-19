"""Command-line entry point: parse both files, diff, write the HTML report."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from profile_compare.differ import diff
from profile_compare.parser import ProfileParseError, parse
from profile_compare.report import render
from profile_compare.sections import valid_section_names


def _parse_sections(value: str) -> list[str]:
    names = [name.strip() for name in value.split(",") if name.strip()]
    valid = valid_section_names()
    unknown = [name for name in names if name not in valid]
    if unknown:
        raise argparse.ArgumentTypeError(
            f"unknown section(s): {', '.join(unknown)}. Valid names: {', '.join(valid)}"
        )
    return names


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="profile-compare",
        description="Compare two Salesforce profile XML files and write an HTML report.",
    )
    parser.add_argument("file_a", type=Path, help="first profile (*.profile-meta.xml)")
    parser.add_argument("file_b", type=Path, help="second profile (*.profile-meta.xml)")
    parser.add_argument(
        "--sections",
        type=_parse_sections,
        default=None,
        metavar="NAME[,NAME...]",
        help="only compare these sections (default: all)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("profile-compare-report.html"),
        help="where to write the report (default: %(default)s)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the tool. Returns 0 if identical, 1 if differences found, 2 on error."""
    args = _build_parser().parse_args(argv)

    try:
        profile_a, warnings_a = parse(args.file_a)
        profile_b, warnings_b = parse(args.file_b)
    except ProfileParseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    compared = set(profile_a) | set(profile_b)
    if args.sections is not None:
        compared &= set(args.sections)

    diffs = diff(profile_a, profile_b, args.sections)
    warnings = [f"[A] {w}" for w in warnings_a] + [f"[B] {w}" for w in warnings_b]
    html = render(
        diffs,
        name_a=args.file_a.name,
        name_b=args.file_b.name,
        sections=sorted(compared),
        warnings=warnings,
    )
    args.out.write_text(html, encoding="utf-8")
    print(f"{len(diffs)} differences written to {args.out}")
    return 1 if diffs else 0
