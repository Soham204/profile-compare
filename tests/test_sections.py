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
