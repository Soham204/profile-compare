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
