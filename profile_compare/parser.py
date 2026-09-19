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
