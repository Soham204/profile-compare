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
