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
