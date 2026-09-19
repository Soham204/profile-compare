# Salesforce Profile Compare — Design

**Date:** 2026-09-19
**Status:** Approved for planning

## Purpose

Compare two Salesforce profile metadata files (`*.profile-meta.xml`) that may
come from different orgs and may be different profiles, and produce a
self-contained HTML report of every difference, grouped by section.

Typical use: `Sales_Rep.profile-meta.xml` from Org A vs
`Field_Sales.profile-meta.xml` from Org B.

## Scope

**In scope**
- Two input XML files, both with root element `<Profile>`.
- All permission/visibility sections in the profile, with an optional
  `--sections` filter to restrict which are compared.
- Three kinds of difference, always reported:
  - `only_in_a` — entry (by key) exists in A but not B
  - `only_in_b` — entry exists in B but not A
  - `changed` — entry exists in both, but one or more attributes differ
- Single-file HTML report with summary counts and collapsible per-section
  tables.

**Out of scope (YAGNI)**
- Retrieving profiles from an org (`sf project retrieve`).
- Permission sets or any other metadata type.
- CSV / JSON / terminal-table output.
- Comparing more than two files.
- Any "apply" or merge functionality.

## Language and dependencies

Python 3.11+, standard library only (`xml.etree.ElementTree`, `argparse`,
`html`, `dataclasses`). Tests use `pytest`.

## Architecture

```
profile_compare/
  __init__.py
  parser.py     # XML file  -> ParsedProfile
  differ.py     # two ParsedProfile -> list[Difference]
  report.py     # list[Difference] -> HTML string
  cli.py        # argparse entry point; wires the three together
  sections.py   # registry of known sections and their key fields
tests/
  fixtures/     # small hand-written profile XML files
  test_parser.py
  test_differ.py
  test_report.py
  test_cli.py
```

Each module has one responsibility and is testable in isolation:
`differ.py` never touches XML; `report.py` never touches the filesystem.

### Data model

```python
# Result of parsing one file
ParsedProfile = dict[str, dict[str, dict[str, str]]]
#                  section    key        attr   value

@dataclass(frozen=True)
class Difference:
    section: str          # e.g. "fieldPermissions"
    key: str              # e.g. "Account.Industry"
    attribute: str | None # e.g. "editable"; None for only_in_a / only_in_b
    value_a: str | None
    value_b: str | None
    kind: Literal["only_in_a", "only_in_b", "changed"]
```

Values are kept as raw strings from the XML (`"true"`, `"false"`,
`"DefaultOn"`, …). No type coercion — the report shows exactly what is in
the file.

### Section registry (`sections.py`)

A dict mapping section element name to the tuple of child element names that
together identify one entry. Everything else under the entry is an attribute.

| Section | Key field(s) |
|---|---|
| `applicationVisibilities` | `application` |
| `classAccesses` | `apexClass` |
| `customMetadataTypeAccesses` | `name` |
| `customPermissions` | `name` |
| `customSettingAccesses` | `name` |
| `externalDataSourceAccesses` | `externalDataSource` |
| `fieldPermissions` | `field` |
| `flowAccesses` | `flow` |
| `layoutAssignments` | `layout`, `recordType` |
| `objectPermissions` | `object` |
| `pageAccesses` | `apexPage` |
| `recordTypeVisibilities` | `recordType` |
| `tabVisibilities` | `tab` |
| `userPermissions` | `name` |

Composite keys are joined with `" / "` for display (e.g.
`Account-Account Layout / Account.Partner`). A missing optional key part
(e.g. `layoutAssignments` with no `recordType`) is treated as empty string.

**Scalar sections** — top-level children with no sub-elements (`custom`,
`description`, `userLicense`, `fullName`) are collected into a synthetic
section `_profile` where the key is the element name and the single
attribute is `value`.

**Unknown sections** — any repeated element not in the registry is handled
by a generic fallback: the first child element is used as the key, the rest
as attributes. The parser records the section name in a
`warnings: list[str]` that flows through to the report header
(`"Section 'foo' is not in the registry; compared using guessed key 'bar'"`).

### Parser (`parser.py`)

`parse(path: Path) -> tuple[ParsedProfile, list[str]]`

- Strips the Salesforce namespace
  (`http://soap.sforce.com/2006/04/metadata`) from tags so callers see
  plain names.
- Groups top-level children by tag; builds the nested dict using the
  registry.
- Duplicate keys within a section (shouldn't happen, but can in
  hand-edited files): last one wins, and a warning is recorded.

Errors raised as `ProfileParseError` with a human message:
- file does not exist
- file is not well-formed XML
- root element is not `Profile`

### Differ (`differ.py`)

`diff(a: ParsedProfile, b: ParsedProfile, sections: set[str] | None = None) -> list[Difference]`

- Union of section names from both sides, filtered by `sections` if given.
- For each section, union of keys. Key in one side only → one `only_in_*`
  difference with `attribute=None`. Key in both → for each attribute in the
  union of attribute names, emit `changed` if values differ (an attribute
  missing on one side counts as `None`, which differs from any string).
- Output is sorted by `(section, key, attribute)` so the report and tests
  are deterministic.
- Pure function; no I/O.

### Report (`report.py`)

`render(diffs: list[Difference], *, name_a: str, name_b: str, warnings: list[str]) -> str`

- One HTML document, inline `<style>`, no external assets or JavaScript
  beyond native `<details>/<summary>`.
- Header: the two file names, timestamp, any warnings.
- Summary table: per section, counts of `only_in_a`, `only_in_b`,
  `changed`, and total. Sections with zero differences are listed but
  shown muted.
- One `<details>` per section (open by default if it has differences) with
  a table: `Key | Attribute | <name_a> | <name_b> | Kind`. Rows colour-coded
  by kind (green = only in A, blue = only in B, amber = changed).
- All text passed through `html.escape`.
- If there are no differences at all, the body says so clearly.

### CLI (`cli.py`)

```
python -m profile_compare A.profile-meta.xml B.profile-meta.xml \
    [--sections fieldPermissions,objectPermissions] \
    [--out report.html]
```

- `--out` defaults to `profile-compare-report.html` in the current
  directory.
- `--sections` is comma-separated; an unknown name is a usage error
  (exit 2) listing the valid names.
- Prints a one-line summary to stdout (`"42 differences written to
  report.html"`).
- Exit codes: `0` no differences, `1` differences found (useful in CI),
  `2` usage/parse error with message on stderr.

## Error handling summary

| Condition | Behaviour |
|---|---|
| Input file missing / unreadable | exit 2, message |
| Not well-formed XML | exit 2, message with line/column from parser |
| Root is not `<Profile>` | exit 2, message |
| Unknown `--sections` name | exit 2, list valid names |
| Unknown section in file | warning in report, continue |
| Duplicate key in a section | warning in report, last wins |

## Testing strategy

- `test_parser.py`: one fixture per section type; asserts the nested dict
  shape, namespace stripping, composite keys, scalar `_profile` section,
  unknown-section fallback + warning, and each error condition.
- `test_differ.py`: plain-dict inputs, no XML. Covers each `kind`,
  attribute missing on one side, section filter, sort order, empty input.
- `test_report.py`: asserts escaping, summary counts, that each section
  appears, and the "no differences" message. Checks substrings, not full
  HTML equality.
- `test_cli.py`: runs `main([...])` with fixture paths in a `tmp_path`;
  asserts exit codes and that the output file exists.

All tests are written before the code they exercise (TDD).
