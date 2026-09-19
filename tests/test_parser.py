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
