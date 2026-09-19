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
