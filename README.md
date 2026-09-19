# profile-compare

A small, dependency-free Python tool that compares two Salesforce **profile**
metadata files and produces a self-contained HTML report of every difference,
grouped by section.

Use it to answer questions like:

- *"What can a Sales Rep do in Org A that a Field Sales user can't in Org B?"*
- *"Did this deployment change any field-level security on the Admin profile?"*
- *"Has our sandbox Admin profile drifted from production?"*

It works on any two `*.profile-meta.xml` files — same profile from two orgs,
two different profiles from one org, or anything in between.

---

## Quick start

```bash
git clone https://github.com/Soham204/profile-compare.git
cd profile-compare

# compare two profiles and write an HTML report
uv run python -m profile_compare OrgA/Admin.profile-meta.xml OrgB/Admin.profile-meta.xml --out report.html
# -> 383 differences written to report.html

# open it
xdg-open report.html        # Linux
open report.html            # macOS
start report.html           # Windows
```

Requirements: Python 3.11+. No third-party packages at runtime, so plain
`python -m profile_compare ...` works too — `uv` is only used to manage the
virtualenv for the test suite.

---

## Getting profile files out of an org

The tool reads files, not orgs. Retrieve profiles with the Salesforce CLI from
inside any SFDX project:

```bash
sf project retrieve start --target-org MyOrg \
    --metadata Profile:Admin \
    --metadata CustomObject:Account \
    --metadata CustomObject:Contact \
    --metadata ApexClass:*
```

The files land in `force-app/main/default/profiles/`.

> **Important Salesforce quirk:** a retrieved profile only contains
> `fieldPermissions`, `objectPermissions`, `classAccesses`, etc. for metadata
> that was retrieved **in the same request**. Retrieving `Profile:Admin` alone
> gives you a nearly empty file. Include the objects, classes, and apps you care
> about, or use a manifest with `<members>*</members>` for those types.

Repeat for the second org (`sf org login web -a OrgB` first if needed) and
point the tool at both files.

---

## Command-line options

```
python -m profile_compare FILE_A FILE_B [--sections NAME[,NAME...]] [--out FILE]
```

| Flag | Meaning | Default |
|---|---|---|
| `--out FILE` | where to write the HTML report | `profile-compare-report.html` |
| `--sections a,b` | only compare these sections | all |
| `--help` | full usage | |

### Exit codes

| Code | Meaning |
|---|---|
| `0` | no differences in the compared sections |
| `1` | differences found |
| `2` | usage error, or a file could not be parsed |

This makes it usable as a CI drift check:

```bash
python -m profile_compare prod/Admin.profile-meta.xml sandbox/Admin.profile-meta.xml \
    || echo "Admin profile has drifted from production"
```

---

## What gets compared

Every section of the profile. Each entry is identified by a **key** (what it
is) and compared on its **attributes** (what it allows):

| Section | Key | Attributes compared |
|---|---|---|
| `fieldPermissions` | `field` | `readable`, `editable` |
| `objectPermissions` | `object` | `allowCreate`, `allowRead`, `allowEdit`, `allowDelete`, `viewAllRecords`, `modifyAllRecords`, … |
| `userPermissions` | `name` | `enabled` |
| `classAccesses` | `apexClass` | `enabled` |
| `pageAccesses` | `apexPage` | `enabled` |
| `applicationVisibilities` | `application` | `visible`, `default` |
| `tabVisibilities` | `tab` | `visibility` |
| `recordTypeVisibilities` | `recordType` | `visible`, `default`, … |
| `layoutAssignments` | `layout` + `recordType` | *(none — presence only)* |
| `flowAccesses` | `flow` | `enabled` |
| `customPermissions` | `name` | `enabled` |
| `customMetadataTypeAccesses` | `name` | `enabled` |
| `customSettingAccesses` | `name` | `enabled` |
| `externalDataSourceAccesses` | `externalDataSource` | `enabled` |
| `_profile` *(synthetic)* | element name | `value` — covers top-level scalars like `custom`, `userLicense`, `description` |

Any section **not** in this list is still compared: the tool uses the first
child element as the key and shows a warning at the top of the report so you
know a guess was made. The full registry lives in
[`profile_compare/sections.py`](profile_compare/sections.py).

### Three kinds of difference

| Kind | Meaning | Example |
|---|---|---|
| **only in A** | the entry exists in file A but not B | `Account.Region__c` exists in Org A only |
| **only in B** | the entry exists in file B but not A | Org B has a Flow that Org A doesn't |
| **changed** | same entry in both, attribute differs | `Account.Industry` is `editable=true` in A, `false` in B |

The first two often mean the *schema* differs between orgs (a field only exists
in one), not just the permission — the report keeps them separate so you can
tell which is which.

---

## The report

A single HTML file with no external assets, so it can be emailed or attached to
a ticket.

- **Header** — the two file names, timestamp, and any warnings
- **Summary table** — one row per section with counts of only-in-A / only-in-B
  / changed. Sections with no differences are shown greyed out.
- **One collapsible block per section** with a table:
  `Key | Attribute | <file A> | <file B> | Kind`, colour-coded by kind
  (green = only in A, blue = only in B, amber = changed)

Values are shown exactly as they appear in the XML (`true`/`false`, `DefaultOn`,
etc.) — nothing is reinterpreted.

---

## How it works

Three pure stages, wired together by a thin CLI:

```
parser.py          differ.py             report.py
XML file  ──▶  {section: {key: {attr: value}}}  ──▶  [Difference, ...]  ──▶  HTML
```

| Module | Responsibility |
|---|---|
| `sections.py` | Registry: which child element(s) identify an entry in each section |
| `parser.py` | Read one XML file into a nested dict; strip the Salesforce namespace; raise `ProfileParseError` on missing/malformed/non-Profile input |
| `differ.py` | Compare two dicts into a sorted list of `Difference` records. No I/O. |
| `report.py` | Render the differences as HTML. All strings escaped. |
| `cli.py` | Argument parsing, wiring, exit codes |

Each module can be tested on its own — `differ` tests use plain dicts, `report`
tests check substrings, `cli` tests run end-to-end against small fixtures.

Design decisions and the implementation plan are in
[`docs/superpowers/`](docs/superpowers/).

---

## Development

```bash
uv run pytest          # run the 38 tests
uv run pytest -v       # verbose
```

Tests live in `tests/`, with hand-written profile fixtures in
`tests/fixtures/`. Every module was written test-first.

---

## Limitations / ideas for later

- **Layout diffs show as pairs.** Because `layoutAssignments` is keyed by
  layout name, "Org A uses *Application Layout*, Org B uses *Opportunity
  Layout* for Opportunity" appears as one *only in A* + one *only in B*, not a
  single *changed* row.
- **Files only.** It doesn't call the org; retrieve first with `sf`.
- **Profiles only.** Permission sets have a very similar structure and would be
  an easy extension.
- **No CSV/JSON output.** The `Difference` records are plain dataclasses, so
  adding another renderer is straightforward.
