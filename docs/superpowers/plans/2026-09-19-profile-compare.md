# Salesforce Profile Compare Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Python CLI that takes two Salesforce `*.profile-meta.xml` files and writes a self-contained HTML report of every difference, grouped by profile section.

**Architecture:** Three pure stages wired by a thin CLI: `parser.py` turns XML into a nested dict, `differ.py` compares two dicts into a sorted list of `Difference` records, `report.py` renders that list to an HTML string. A `sections.py` registry says which child element(s) identify an entry in each section; unknown sections fall back to a guessed key and emit a warning.

**Tech Stack:** Python 3.11+ standard library only (`xml.etree.ElementTree`, `argparse`, `html`, `dataclasses`). `pytest` for tests, `uv` to manage the venv.

**Spec:** `docs/superpowers/specs/2026-09-19-profile-compare-design.md`

## Global Constraints

- Python `>=3.11`; runtime code imports **only** the standard library.
- Values from XML are kept as raw strings (`"true"`, not `True`). No coercion anywhere.
- All output from `differ.diff()` is sorted by `(section, key, attribute)`.
- Every string that reaches HTML goes through `html.escape`.
- Exit codes: `0` no differences, `1` differences found, `2` usage or parse error.
- Salesforce namespace `http://soap.sforce.com/2006/04/metadata` is stripped from all tag names before any logic sees them.
- Scalar top-level elements are collected under the synthetic section name `_profile` with attribute name `value`.
- Composite keys are joined with `" / "`; empty parts are omitted from the joined string.
- Run tests with `uv run pytest` from the project root (`/home/soohm/Work/profile-compare`).

---

## File structure

| Path | Responsibility |
|---|---|
| `pyproject.toml` | Project metadata, pytest config, dev dependency on pytest |
| `profile_compare/__init__.py` | Package marker, exposes `__version__` |
| `profile_compare/sections.py` | Registry: section name → tuple of key field names; constants |
| `profile_compare/parser.py` | `parse(path)` → `(ParsedProfile, warnings)`; `ProfileParseError` |
| `profile_compare/differ.py` | `Difference` dataclass; `diff(a, b, sections)` |
| `profile_compare/report.py` | `render(diffs, ...)` → HTML string |
| `profile_compare/cli.py` | `main(argv)` → exit code |
| `profile_compare/__main__.py` | `python -m profile_compare` entry |
| `tests/fixtures/*.xml` | Small hand-written profile files |
| `tests/test_sections.py` | Registry sanity |
| `tests/test_parser.py` | Parser behaviour and error cases |
| `tests/test_differ.py` | Diff logic on plain dicts |
| `tests/test_report.py` | HTML content checks by substring |
| `tests/test_cli.py` | End-to-end with fixtures in `tmp_path` |
| `README.md` | Usage |

---

### Task 1: Project scaffold and section registry

**Files:**
- Create: `pyproject.toml`
- Create: `profile_compare/__init__.py`
- Create: `profile_compare/sections.py`
- Create: `tests/__init__.py`
- Create: `tests/test_sections.py`
- Create: `.gitignore`

**Interfaces:**
- Produces: `sections.KEY_FIELDS: dict[str, tuple[str, ...]]`, `sections.SCALAR_SECTION = "_profile"`, `sections.KEY_SEPARATOR = " / "`, `sections.NAMESPACE`, `sections.valid_section_names() -> list[str]`

- [ ] **Step 1: Create project files**

`pyproject.toml`:
```toml
[project]
name = "profile-compare"
version = "0.1.0"
description = "Compare two Salesforce profile XML files and produce an HTML diff report"
requires-python = ">=3.11"
dependencies = []

[dependency-groups]
dev = ["pytest>=8"]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

`.gitignore`:
```
.venv/
__pycache__/
*.pyc
.pytest_cache/
*.html
```

`profile_compare/__init__.py`:
```python
"""Compare two Salesforce profile metadata files."""

__version__ = "0.1.0"
```

`tests/__init__.py`: empty file.

- [ ] **Step 2: Write the failing test**

`tests/test_sections.py`:
```python
from profile_compare import sections


def test_known_sections_have_non_empty_key_tuples():
    assert sections.KEY_FIELDS
    for name, keys in sections.KEY_FIELDS.items():
        assert isinstance(keys, tuple), name
        assert len(keys) >= 1, name


def test_layout_assignments_use_composite_key():
    assert sections.KEY_FIELDS["layoutAssignments"] == ("layout", "recordType")


def test_field_permissions_keyed_by_field():
    assert sections.KEY_FIELDS["fieldPermissions"] == ("field",)


def test_valid_section_names_includes_registry_and_scalar_section():
    names = sections.valid_section_names()
    assert names == sorted(names)
    assert sections.SCALAR_SECTION in names
    assert "fieldPermissions" in names
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/test_sections.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'profile_compare.sections'` (uv will create `.venv` and install pytest on first run).

- [ ] **Step 4: Write the registry**

`profile_compare/sections.py`:
```python
"""Registry describing how each profile section identifies its entries.

A Salesforce profile is a flat list of repeated elements such as
<fieldPermissions> or <objectPermissions>. Inside each one, some child
elements *identify* the entry (the key) and the rest are the values we want
to compare (the attributes). This table records the key fields per section.
"""

NAMESPACE = "http://soap.sforce.com/2006/04/metadata"

# Synthetic section for top-level scalars like <custom>, <userLicense>.
SCALAR_SECTION = "_profile"

# Used to join the parts of a composite key for display and dict lookup.
KEY_SEPARATOR = " / "

KEY_FIELDS: dict[str, tuple[str, ...]] = {
    "applicationVisibilities": ("application",),
    "classAccesses": ("apexClass",),
    "customMetadataTypeAccesses": ("name",),
    "customPermissions": ("name",),
    "customSettingAccesses": ("name",),
    "externalDataSourceAccesses": ("externalDataSource",),
    "fieldPermissions": ("field",),
    "flowAccesses": ("flow",),
    "layoutAssignments": ("layout", "recordType"),
    "objectPermissions": ("object",),
    "pageAccesses": ("apexPage",),
    "recordTypeVisibilities": ("recordType",),
    "tabVisibilities": ("tab",),
    "userPermissions": ("name",),
}


def valid_section_names() -> list[str]:
    """Section names accepted by the CLI's --sections flag, sorted."""
    return sorted([*KEY_FIELDS, SCALAR_SECTION])
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_sections.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .gitignore profile_compare/__init__.py profile_compare/sections.py tests/__init__.py tests/test_sections.py uv.lock
git commit -m "feat: project scaffold and section registry"
```

---

### Task 2: Parser — happy path for known sections

**Files:**
- Create: `profile_compare/parser.py`
- Create: `tests/fixtures/basic_a.xml`
- Create: `tests/test_parser.py`

**Interfaces:**
- Consumes: `sections.KEY_FIELDS`, `sections.SCALAR_SECTION`, `sections.KEY_SEPARATOR`
- Produces: `parser.ParsedProfile` type alias (`dict[str, dict[str, dict[str, str]]]`), `parser.parse(path: Path | str) -> tuple[ParsedProfile, list[str]]`, `parser.ProfileParseError(Exception)`

- [ ] **Step 1: Create the fixture**

`tests/fixtures/basic_a.xml`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Profile xmlns="http://soap.sforce.com/2006/04/metadata">
    <custom>true</custom>
    <userLicense>Salesforce</userLicense>
    <fieldPermissions>
        <editable>true</editable>
        <field>Account.Industry</field>
        <readable>true</readable>
    </fieldPermissions>
    <fieldPermissions>
        <editable>false</editable>
        <field>Account.Rating</field>
        <readable>true</readable>
    </fieldPermissions>
    <objectPermissions>
        <allowCreate>true</allowCreate>
        <allowDelete>false</allowDelete>
        <allowEdit>true</allowEdit>
        <allowRead>true</allowRead>
        <modifyAllRecords>false</modifyAllRecords>
        <object>Account</object>
        <viewAllRecords>false</viewAllRecords>
    </objectPermissions>
    <layoutAssignments>
        <layout>Account-Account Layout</layout>
    </layoutAssignments>
    <layoutAssignments>
        <layout>Account-Partner Layout</layout>
        <recordType>Account.Partner</recordType>
    </layoutAssignments>
    <userPermissions>
        <enabled>true</enabled>
        <name>ApiEnabled</name>
    </userPermissions>
</Profile>
```

- [ ] **Step 2: Write the failing tests**

`tests/test_parser.py`:
```python
from pathlib import Path

import pytest

from profile_compare.parser import ProfileParseError, parse

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_field_permissions_keyed_by_field_with_namespace_stripped():
    profile, warnings = parse(FIXTURES / "basic_a.xml")
    assert warnings == []
    assert profile["fieldPermissions"]["Account.Industry"] == {
        "editable": "true",
        "readable": "true",
    }
    assert profile["fieldPermissions"]["Account.Rating"]["editable"] == "false"


def test_parse_object_permissions():
    profile, _ = parse(FIXTURES / "basic_a.xml")
    account = profile["objectPermissions"]["Account"]
    assert account["allowCreate"] == "true"
    assert account["viewAllRecords"] == "false"
    assert "object" not in account  # key field is not an attribute


def test_parse_layout_assignments_composite_key():
    profile, _ = parse(FIXTURES / "basic_a.xml")
    layouts = profile["layoutAssignments"]
    assert "Account-Account Layout" in layouts  # no recordType -> no separator
    assert "Account-Partner Layout / Account.Partner" in layouts
    assert layouts["Account-Partner Layout / Account.Partner"] == {}


def test_parse_scalars_go_into_profile_section():
    profile, _ = parse(FIXTURES / "basic_a.xml")
    assert profile["_profile"] == {
        "custom": {"value": "true"},
        "userLicense": {"value": "Salesforce"},
    }


def test_parse_accepts_str_path():
    profile, _ = parse(str(FIXTURES / "basic_a.xml"))
    assert "userPermissions" in profile
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_parser.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'profile_compare.parser'`

- [ ] **Step 4: Write the parser**

`profile_compare/parser.py`:
```python
"""Turn a profile XML file into a nested dict: section -> key -> attributes."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from profile_compare.sections import KEY_FIELDS, KEY_SEPARATOR, SCALAR_SECTION

# section name -> entry key -> attribute name -> raw string value
ParsedProfile = dict[str, dict[str, dict[str, str]]]


class ProfileParseError(Exception):
    """Raised when a file cannot be read as a Salesforce profile."""


def _local_name(tag: str) -> str:
    """Strip the '{namespace}' prefix ElementTree puts on tag names."""
    return tag.rsplit("}", 1)[-1]


def _text(elem: ET.Element) -> str:
    return (elem.text or "").strip()


def parse(path: Path | str) -> tuple[ParsedProfile, list[str]]:
    """Parse one profile file.

    Returns the nested dict plus a list of human-readable warnings about
    things that were tolerated but look suspicious (unknown sections,
    duplicate keys).
    """
    path = Path(path)
    root = _load_root(path)

    profile: ParsedProfile = {}
    warnings: list[str] = []
    guessed_keys: dict[str, str] = {}

    for elem in root:
        section_name = _local_name(elem.tag)
        children = list(elem)

        if not children:
            profile.setdefault(SCALAR_SECTION, {})[section_name] = {"value": _text(elem)}
            continue

        key_fields = KEY_FIELDS.get(section_name)
        if key_fields is None:
            key_fields = (_local_name(children[0].tag),)
            if section_name not in guessed_keys:
                guessed_keys[section_name] = key_fields[0]
                warnings.append(
                    f"Section '{section_name}' is not in the registry; "
                    f"compared using guessed key '{key_fields[0]}'"
                )

        values = {_local_name(child.tag): _text(child) for child in children}
        key = KEY_SEPARATOR.join(part for part in (values.get(k, "") for k in key_fields) if part)
        attributes = {name: value for name, value in values.items() if name not in key_fields}

        section = profile.setdefault(section_name, {})
        if key in section:
            warnings.append(
                f"Duplicate key '{key}' in section '{section_name}'; last occurrence wins"
            )
        section[key] = attributes

    return profile, warnings


def _load_root(path: Path) -> ET.Element:
    if not path.is_file():
        raise ProfileParseError(f"File not found: {path}")
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise ProfileParseError(f"{path} is not well-formed XML: {exc}") from exc
    if _local_name(root.tag) != "Profile":
        raise ProfileParseError(
            f"{path}: root element is <{_local_name(root.tag)}>, expected <Profile>"
        )
    return root
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_parser.py -v`
Expected: 5 passed

- [ ] **Step 6: Commit**

```bash
git add profile_compare/parser.py tests/fixtures/basic_a.xml tests/test_parser.py
git commit -m "feat: parse profile XML into section/key/attribute dict"
```

---

### Task 3: Parser — unknown sections, duplicates, and errors

**Files:**
- Modify: `tests/test_parser.py` (append)
- Create: `tests/fixtures/unknown_section.xml`
- Create: `tests/fixtures/duplicate_key.xml`
- Create: `tests/fixtures/not_a_profile.xml`
- Create: `tests/fixtures/malformed.xml`

**Interfaces:**
- Consumes: `parser.parse`, `parser.ProfileParseError` from Task 2
- Produces: nothing new; verifies the warning and error behaviour Task 2's code already implements

- [ ] **Step 1: Create the fixtures**

`tests/fixtures/unknown_section.xml`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Profile xmlns="http://soap.sforce.com/2006/04/metadata">
    <widgetAccesses>
        <widget>Foo</widget>
        <enabled>true</enabled>
    </widgetAccesses>
    <widgetAccesses>
        <widget>Bar</widget>
        <enabled>false</enabled>
    </widgetAccesses>
</Profile>
```

`tests/fixtures/duplicate_key.xml`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Profile xmlns="http://soap.sforce.com/2006/04/metadata">
    <userPermissions>
        <enabled>false</enabled>
        <name>ApiEnabled</name>
    </userPermissions>
    <userPermissions>
        <enabled>true</enabled>
        <name>ApiEnabled</name>
    </userPermissions>
</Profile>
```

`tests/fixtures/not_a_profile.xml`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<PermissionSet xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>Not a profile</label>
</PermissionSet>
```

`tests/fixtures/malformed.xml`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Profile xmlns="http://soap.sforce.com/2006/04/metadata">
    <custom>true</custom>
```

- [ ] **Step 2: Append the failing tests**

Append to `tests/test_parser.py`:
```python


def test_unknown_section_uses_first_child_as_key_and_warns_once():
    profile, warnings = parse(FIXTURES / "unknown_section.xml")
    assert profile["widgetAccesses"] == {
        "Foo": {"enabled": "true"},
        "Bar": {"enabled": "false"},
    }
    assert warnings == [
        "Section 'widgetAccesses' is not in the registry; compared using guessed key 'widget'"
    ]


def test_duplicate_key_last_wins_and_warns():
    profile, warnings = parse(FIXTURES / "duplicate_key.xml")
    assert profile["userPermissions"]["ApiEnabled"] == {"enabled": "true"}
    assert warnings == [
        "Duplicate key 'ApiEnabled' in section 'userPermissions'; last occurrence wins"
    ]


def test_missing_file_raises():
    with pytest.raises(ProfileParseError, match="File not found"):
        parse(FIXTURES / "does_not_exist.xml")


def test_malformed_xml_raises():
    with pytest.raises(ProfileParseError, match="not well-formed XML"):
        parse(FIXTURES / "malformed.xml")


def test_wrong_root_element_raises():
    with pytest.raises(ProfileParseError, match="expected <Profile>"):
        parse(FIXTURES / "not_a_profile.xml")
```

- [ ] **Step 3: Run tests**

Run: `uv run pytest tests/test_parser.py -v`
Expected: 10 passed. (Task 2's implementation already covers these paths; this task locks them in with tests. If any fail, fix `parser.py` to match the assertions — the tests are the contract.)

- [ ] **Step 4: Commit**

```bash
git add tests/fixtures/unknown_section.xml tests/fixtures/duplicate_key.xml tests/fixtures/not_a_profile.xml tests/fixtures/malformed.xml tests/test_parser.py
git commit -m "test: parser warnings and error cases"
```

---

### Task 4: Differ

**Files:**
- Create: `profile_compare/differ.py`
- Create: `tests/test_differ.py`

**Interfaces:**
- Consumes: `parser.ParsedProfile` type alias
- Produces:
  - `differ.Kind = Literal["only_in_a", "only_in_b", "changed"]`
  - `differ.Difference` frozen dataclass with fields `section: str, key: str, attribute: str | None, value_a: str | None, value_b: str | None, kind: Kind`
  - `differ.diff(a: ParsedProfile, b: ParsedProfile, sections: Iterable[str] | None = None) -> list[Difference]`
  - For `only_in_*` records, `attribute` is `None` and the present side's value is a summary string `"attr1=v1, attr2=v2"` (sorted by attr name; `""` if the entry has no attributes). The absent side is `None`.

- [ ] **Step 1: Write the failing tests**

`tests/test_differ.py`:
```python
from profile_compare.differ import Difference, diff


def test_identical_profiles_produce_no_differences():
    a = {"fieldPermissions": {"Account.Industry": {"editable": "true", "readable": "true"}}}
    assert diff(a, dict(a)) == []


def test_changed_attribute_reported_once_per_attribute():
    a = {"fieldPermissions": {"Account.Industry": {"editable": "true", "readable": "true"}}}
    b = {"fieldPermissions": {"Account.Industry": {"editable": "false", "readable": "true"}}}
    assert diff(a, b) == [
        Difference("fieldPermissions", "Account.Industry", "editable", "true", "false", "changed")
    ]


def test_key_only_in_a_is_reported_with_attribute_summary():
    a = {"userPermissions": {"ApiEnabled": {"enabled": "true"}}}
    b = {"userPermissions": {}}
    assert diff(a, b) == [
        Difference("userPermissions", "ApiEnabled", None, "enabled=true", None, "only_in_a")
    ]


def test_key_only_in_b_when_section_missing_entirely_from_a():
    a = {}
    b = {"objectPermissions": {"Account": {"allowRead": "true", "allowCreate": "false"}}}
    assert diff(a, b) == [
        Difference(
            "objectPermissions", "Account", None, None, "allowCreate=false, allowRead=true", "only_in_b"
        )
    ]


def test_entry_with_no_attributes_only_in_a_has_empty_summary():
    a = {"layoutAssignments": {"Account-Account Layout": {}}}
    assert diff(a, {}) == [
        Difference("layoutAssignments", "Account-Account Layout", None, "", None, "only_in_a")
    ]


def test_attribute_missing_on_one_side_is_a_change_with_none():
    a = {"objectPermissions": {"Account": {"allowRead": "true", "viewAllFields": "true"}}}
    b = {"objectPermissions": {"Account": {"allowRead": "true"}}}
    assert diff(a, b) == [
        Difference("objectPermissions", "Account", "viewAllFields", "true", None, "changed")
    ]


def test_sections_filter_limits_comparison():
    a = {
        "fieldPermissions": {"Account.Industry": {"editable": "true"}},
        "userPermissions": {"ApiEnabled": {"enabled": "true"}},
    }
    b = {
        "fieldPermissions": {"Account.Industry": {"editable": "false"}},
        "userPermissions": {"ApiEnabled": {"enabled": "false"}},
    }
    result = diff(a, b, sections=["userPermissions"])
    assert [d.section for d in result] == ["userPermissions"]


def test_output_sorted_by_section_key_attribute():
    a = {
        "userPermissions": {"ViewSetup": {"enabled": "true"}},
        "fieldPermissions": {
            "Account.Rating": {"readable": "true", "editable": "true"},
            "Account.Industry": {"editable": "true"},
        },
    }
    b = {
        "userPermissions": {"ViewSetup": {"enabled": "false"}},
        "fieldPermissions": {
            "Account.Rating": {"readable": "false", "editable": "false"},
            "Account.Industry": {"editable": "false"},
        },
    }
    result = diff(a, b)
    assert [(d.section, d.key, d.attribute) for d in result] == [
        ("fieldPermissions", "Account.Industry", "editable"),
        ("fieldPermissions", "Account.Rating", "editable"),
        ("fieldPermissions", "Account.Rating", "readable"),
        ("userPermissions", "ViewSetup", "enabled"),
    ]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_differ.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'profile_compare.differ'`

- [ ] **Step 3: Write the differ**

`profile_compare/differ.py`:
```python
"""Compare two parsed profiles. Pure functions, no I/O."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from profile_compare.parser import ParsedProfile

Kind = Literal["only_in_a", "only_in_b", "changed"]


@dataclass(frozen=True)
class Difference:
    section: str
    key: str
    attribute: str | None  # None for only_in_a / only_in_b
    value_a: str | None
    value_b: str | None
    kind: Kind


def _summary(attributes: dict[str, str]) -> str:
    """Compact one-line rendering of an entry's attributes, e.g. 'editable=true, readable=true'."""
    return ", ".join(f"{name}={value}" for name, value in sorted(attributes.items()))


def diff(
    a: ParsedProfile,
    b: ParsedProfile,
    sections: Iterable[str] | None = None,
) -> list[Difference]:
    """Return every difference between a and b, sorted by (section, key, attribute)."""
    section_names = set(a) | set(b)
    if sections is not None:
        section_names &= set(sections)

    result: list[Difference] = []
    for section in section_names:
        entries_a = a.get(section, {})
        entries_b = b.get(section, {})
        for key in set(entries_a) | set(entries_b):
            if key not in entries_b:
                result.append(
                    Difference(section, key, None, _summary(entries_a[key]), None, "only_in_a")
                )
            elif key not in entries_a:
                result.append(
                    Difference(section, key, None, None, _summary(entries_b[key]), "only_in_b")
                )
            else:
                attrs_a, attrs_b = entries_a[key], entries_b[key]
                for attribute in set(attrs_a) | set(attrs_b):
                    value_a, value_b = attrs_a.get(attribute), attrs_b.get(attribute)
                    if value_a != value_b:
                        result.append(
                            Difference(section, key, attribute, value_a, value_b, "changed")
                        )

    result.sort(key=lambda d: (d.section, d.key, d.attribute or ""))
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_differ.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add profile_compare/differ.py tests/test_differ.py
git commit -m "feat: diff two parsed profiles into sorted Difference records"
```

---

### Task 5: HTML report

**Files:**
- Create: `profile_compare/report.py`
- Create: `tests/test_report.py`

**Interfaces:**
- Consumes: `differ.Difference`, `differ.Kind`
- Produces: `report.render(diffs: list[Difference], *, name_a: str, name_b: str, sections: Iterable[str], warnings: Iterable[str] = ()) -> str`
  - `sections` is the full list of section names that were compared (so zero-diff sections can be listed muted).

- [ ] **Step 1: Write the failing tests**

`tests/test_report.py`:
```python
from profile_compare.differ import Difference
from profile_compare.report import render

DIFFS = [
    Difference("fieldPermissions", "Account.Industry", "editable", "true", "false", "changed"),
    Difference("userPermissions", "ApiEnabled", None, "enabled=true", None, "only_in_a"),
    Difference("userPermissions", "ViewSetup", None, None, "enabled=true", "only_in_b"),
]
SECTIONS = ["fieldPermissions", "objectPermissions", "userPermissions"]


def _render(diffs=DIFFS, **kwargs):
    defaults = dict(name_a="a.xml", name_b="b.xml", sections=SECTIONS)
    defaults.update(kwargs)
    return render(diffs, **defaults)


def test_is_a_complete_html_document_with_file_names():
    html = _render()
    assert html.startswith("<!DOCTYPE html>")
    assert "</html>" in html
    assert "a.xml" in html and "b.xml" in html


def test_summary_counts_per_section():
    html = _render()
    # fieldPermissions: 0 only-A, 0 only-B, 1 changed, 1 total
    assert '<tr class="section-row"><td>fieldPermissions</td><td>0</td><td>0</td><td>1</td><td>1</td></tr>' in html
    # userPermissions: 1 only-A, 1 only-B, 0 changed, 2 total
    assert '<tr class="section-row"><td>userPermissions</td><td>1</td><td>1</td><td>0</td><td>2</td></tr>' in html


def test_sections_without_differences_are_listed_muted():
    html = _render()
    assert '<tr class="section-row muted"><td>objectPermissions</td><td>0</td><td>0</td><td>0</td><td>0</td></tr>' in html


def test_each_section_with_differences_has_open_details_block():
    html = _render()
    assert '<details open id="section-fieldPermissions">' in html
    assert '<details open id="section-userPermissions">' in html
    assert 'id="section-objectPermissions"' not in html


def test_rows_are_classed_by_kind_and_show_values():
    html = _render()
    assert '<tr class="changed"><td>Account.Industry</td><td>editable</td><td>true</td><td>false</td><td>changed</td></tr>' in html
    assert '<tr class="only_in_a"><td>ApiEnabled</td><td></td><td>enabled=true</td><td></td><td>only in A</td></tr>' in html
    assert '<tr class="only_in_b"><td>ViewSetup</td><td></td><td></td><td>enabled=true</td><td>only in B</td></tr>' in html


def test_values_are_html_escaped():
    diffs = [Difference("fieldPermissions", "Acc<b>t", "x", "<script>", "a&b", "changed")]
    html = _render(diffs, name_a="<a>.xml")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "Acc&lt;b&gt;t" in html
    assert "a&amp;b" in html
    assert "&lt;a&gt;.xml" in html


def test_warnings_are_shown():
    html = _render(warnings=["Section 'foo' is not in the registry; compared using guessed key 'bar'"])
    assert "guessed key &#x27;bar&#x27;" in html or "guessed key 'bar'" in html
    assert 'class="warnings"' in html


def test_no_warnings_block_when_none():
    assert 'class="warnings"' not in _render()


def test_no_differences_message():
    html = _render([])
    assert "No differences found" in html
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_report.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'profile_compare.report'`

- [ ] **Step 3: Write the report renderer**

`profile_compare/report.py`:
```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_report.py -v`
Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
git add profile_compare/report.py tests/test_report.py
git commit -m "feat: render differences as self-contained HTML report"
```

---

### Task 6: CLI and `python -m` entry point

**Files:**
- Create: `profile_compare/cli.py`
- Create: `profile_compare/__main__.py`
- Create: `tests/fixtures/basic_b.xml`
- Create: `tests/test_cli.py`

**Interfaces:**
- Consumes: `parser.parse`, `parser.ProfileParseError`, `differ.diff`, `report.render`, `sections.valid_section_names`
- Produces: `cli.main(argv: list[str] | None = None) -> int`

- [ ] **Step 1: Create the second fixture**

`tests/fixtures/basic_b.xml` — same as `basic_a.xml` but with `Account.Industry` not editable, `Account.Rating` removed, and a new `Contact.Email` field:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Profile xmlns="http://soap.sforce.com/2006/04/metadata">
    <custom>true</custom>
    <userLicense>Salesforce</userLicense>
    <fieldPermissions>
        <editable>false</editable>
        <field>Account.Industry</field>
        <readable>true</readable>
    </fieldPermissions>
    <fieldPermissions>
        <editable>true</editable>
        <field>Contact.Email</field>
        <readable>true</readable>
    </fieldPermissions>
    <objectPermissions>
        <allowCreate>true</allowCreate>
        <allowDelete>false</allowDelete>
        <allowEdit>true</allowEdit>
        <allowRead>true</allowRead>
        <modifyAllRecords>false</modifyAllRecords>
        <object>Account</object>
        <viewAllRecords>false</viewAllRecords>
    </objectPermissions>
    <layoutAssignments>
        <layout>Account-Account Layout</layout>
    </layoutAssignments>
    <layoutAssignments>
        <layout>Account-Partner Layout</layout>
        <recordType>Account.Partner</recordType>
    </layoutAssignments>
    <userPermissions>
        <enabled>true</enabled>
        <name>ApiEnabled</name>
    </userPermissions>
</Profile>
```

- [ ] **Step 2: Write the failing tests**

`tests/test_cli.py`:
```python
from pathlib import Path

import pytest

from profile_compare.cli import main

FIXTURES = Path(__file__).parent / "fixtures"
A = str(FIXTURES / "basic_a.xml")
B = str(FIXTURES / "basic_b.xml")


def test_identical_files_exit_0_and_write_report(tmp_path, capsys):
    out = tmp_path / "r.html"
    assert main([A, A, "--out", str(out)]) == 0
    assert out.is_file()
    assert "No differences found" in out.read_text()
    assert capsys.readouterr().out.strip() == f"0 differences written to {out}"


def test_different_files_exit_1_and_report_contains_diffs(tmp_path, capsys):
    out = tmp_path / "r.html"
    assert main([A, B, "--out", str(out)]) == 1
    html = out.read_text()
    assert "Account.Industry" in html
    assert "Account.Rating" in html  # only in A
    assert "Contact.Email" in html   # only in B
    assert capsys.readouterr().out.strip() == f"3 differences written to {out}"


def test_default_output_path_is_in_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    main([A, B])
    assert (tmp_path / "profile-compare-report.html").is_file()


def test_sections_filter(tmp_path, capsys):
    out = tmp_path / "r.html"
    assert main([A, B, "--sections", "userPermissions,objectPermissions", "--out", str(out)]) == 0
    assert capsys.readouterr().out.strip() == f"0 differences written to {out}"


def test_unknown_section_name_is_usage_error(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        main([A, B, "--sections", "nope", "--out", str(tmp_path / "r.html")])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "nope" in err
    assert "fieldPermissions" in err  # valid names are listed


def test_parse_error_exits_2_with_message(tmp_path, capsys):
    rc = main([A, str(FIXTURES / "malformed.xml"), "--out", str(tmp_path / "r.html")])
    assert rc == 2
    assert "not well-formed XML" in capsys.readouterr().err
    assert not (tmp_path / "r.html").exists()


def test_parser_warnings_are_prefixed_with_side_in_report(tmp_path):
    out = tmp_path / "r.html"
    main([A, str(FIXTURES / "unknown_section.xml"), "--out", str(out)])
    assert "[B] Section &#x27;widgetAccesses&#x27;" in out.read_text() or "[B] Section 'widgetAccesses'" in out.read_text()
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_cli.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'profile_compare.cli'`

- [ ] **Step 4: Write the CLI**

`profile_compare/cli.py`:
```python
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
```

`profile_compare/__main__.py`:
```python
import sys

from profile_compare.cli import main

sys.exit(main())
```

- [ ] **Step 5: Run the full suite**

Run: `uv run pytest -v`
Expected: all tests pass (4 sections + 10 parser + 8 differ + 9 report + 7 cli = 38).

- [ ] **Step 6: Smoke-test the module entry point**

Run: `uv run python -m profile_compare tests/fixtures/basic_a.xml tests/fixtures/basic_b.xml --out /tmp/smoke.html; echo "exit=$?"`
Expected: prints `3 differences written to /tmp/smoke.html` and `exit=1`. Open `/tmp/smoke.html` in a browser and confirm the summary table and three colour-coded rows appear.

- [ ] **Step 7: Commit**

```bash
git add profile_compare/cli.py profile_compare/__main__.py tests/fixtures/basic_b.xml tests/test_cli.py
git commit -m "feat: CLI with --sections filter, --out, and CI-friendly exit codes"
```

---

### Task 7: README

**Files:**
- Create: `README.md`

**Interfaces:**
- Consumes: the CLI surface from Task 6

- [ ] **Step 1: Write the README**

`README.md`:
````markdown
# profile-compare

Compare two Salesforce profile metadata files (`*.profile-meta.xml`) — from the
same org or different orgs — and get a self-contained HTML report of every
difference, grouped by section.

## Usage

```bash
uv run python -m profile_compare OrgA/Sales_Rep.profile-meta.xml OrgB/Field_Sales.profile-meta.xml
# -> 42 differences written to profile-compare-report.html

# only some sections, custom output path
uv run python -m profile_compare a.xml b.xml \
    --sections fieldPermissions,objectPermissions \
    --out sales-vs-field.html
```

No third-party runtime dependencies — plain `python -m profile_compare ...`
works too if you have Python 3.11+.

### Exit codes

| Code | Meaning |
|---|---|
| 0 | profiles are identical (in the compared sections) |
| 1 | differences found |
| 2 | usage error or a file could not be parsed |

Handy for CI drift checks: `python -m profile_compare prod.xml sandbox.xml || echo "drift!"`

### What gets compared

Every repeated section in the profile (`fieldPermissions`, `objectPermissions`,
`userPermissions`, `layoutAssignments`, …) plus top-level scalars
(`custom`, `userLicense`, …) under the synthetic section `_profile`.
Run `python -m profile_compare --help` or see `profile_compare/sections.py`
for the full list of section names accepted by `--sections`.

Sections the tool doesn't know about are still compared, using the first
child element as the key; the report shows a warning when this happens.

## Development

```bash
uv run pytest
```

Design: `docs/superpowers/specs/2026-09-19-profile-compare-design.md`
````

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: README with usage and exit codes"
```
