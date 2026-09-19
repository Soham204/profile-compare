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
