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
