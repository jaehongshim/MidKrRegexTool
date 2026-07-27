"""Tests for <letter>-aware XML parsing (letter-per-document handling)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from midkrregextool.cli import CLIArgs, collect_input_files, run_corpus_list
from midkrregextool.parser import (
    convert_to_century,
    get_info_from_letters,
    has_letters,
    letter_sort_key,
    parse_file,
    trimming_date,
)


def _write(path: Path, xml: str) -> Path:
    path.write_text(xml, encoding="utf-8")
    return path


# 1. sender/receiver/year as <letter> attributes
def test_letter_attribute_metadata(tmp_path: Path) -> None:
    xml = """<TEI>
  <letter sender="A" receiver="B" year="1452">
    <sent page="1a" n="1" lang="kor">hana tul</sent>
  </letter>
</TEI>"""
    root = ET.fromstring(xml)
    infos = get_info_from_letters(root)
    assert len(infos) == 1
    info = infos[0]
    assert info.sender == "A"
    assert info.receiver == "B"
    assert info.raw_year == "1452"
    assert info.published_year == 1452
    assert info.published_century == 15


# 2. writer attribute used instead of sender
def test_letter_writer_attribute(tmp_path: Path) -> None:
    xml = """<TEI>
  <letter writer="C" receiver="D" year="1500">
    <sent page="1a" n="1" lang="kor">sey ney</sent>
  </letter>
</TEI>"""
    root = ET.fromstring(xml)
    info = get_info_from_letters(root)[0]
    assert info.sender == "C"
    assert info.receiver == "D"
    assert info.published_century == 15


# 3. inner <writer>/<addressee>/<year> elements
def test_letter_inner_elements(tmp_path: Path) -> None:
    xml = """<TEI>
  <letter>
    <writer>E</writer>
    <addressee>F</addressee>
    <year>1620</year>
    <sent page="1a" n="1" lang="kor">tasus yeoseos</sent>
  </letter>
</TEI>"""
    root = ET.fromstring(xml)
    info = get_info_from_letters(root)[0]
    assert info.sender == "E"
    assert info.receiver == "F"
    assert info.raw_year == "1620"
    assert info.published_century == 17


# 4. <date> used instead of <year>
def test_letter_date_instead_of_year(tmp_path: Path) -> None:
    xml = """<TEI>
  <letter>
    <writer>G</writer>
    <addressee>H</addressee>
    <date>1710년</date>
    <sent page="1a" n="1" lang="kor">ilgop yeodeulb</sent>
  </letter>
</TEI>"""
    root = ET.fromstring(xml)
    info = get_info_from_letters(root)[0]
    assert info.raw_year == "1710년"
    assert info.published_year == 1710
    assert info.published_century == 18


# 5. metadata as siblings of <letter>, under a shared parent
def test_letter_sibling_metadata(tmp_path: Path) -> None:
    xml = """<TEI>
  <text>
    <writer>I</writer>
    <addressee>J</addressee>
    <year>1810</year>
    <letter>
      <sent page="1a" n="1" lang="kor">ahob yeoal</sent>
    </letter>
  </text>
</TEI>"""
    root = ET.fromstring(xml)
    info = get_info_from_letters(root)[0]
    assert info.sender == "I"
    assert info.receiver == "J"
    assert info.raw_year == "1810"
    assert info.published_century == 19


# 6 & 7. multiple letters of different centuries in one file; period filter
# only tokenizes the matching century's <sent>.
def _mixed_century_file(tmp_path: Path) -> Path:
    xml = """<TEI>
  <teiHeader><titleStmt><title>Sample Letters</title></titleStmt></teiHeader>
  <letter sender="A" receiver="B" year="1452">
    <sent page="1a" n="1" lang="kor">hana tul</sent>
  </letter>
  <text>
    <writer>I</writer>
    <addressee>J</addressee>
    <year>1810</year>
    <letter>
      <sent page="2a" n="1" lang="kor">sey ney</sent>
    </letter>
  </text>
</TEI>"""
    return _write(tmp_path / "mixed.xml", xml)


def test_mixed_century_letters_in_one_file(tmp_path: Path) -> None:
    path = _mixed_century_file(tmp_path)
    root = ET.parse(path).getroot()
    infos = get_info_from_letters(root)
    centuries = sorted(info.published_century for info in infos)
    assert centuries == [15, 19]


def test_period_filter_only_tokenizes_matching_letter(tmp_path: Path) -> None:
    path = _mixed_century_file(tmp_path)

    tokens_15c = parse_file(path, period=15)
    assert [t.pua for t in tokens_15c] == ["hana", "tul"]

    tokens_19c = parse_file(path, period=19)
    assert [t.pua for t in tokens_19c] == ["sey", "ney"]

    tokens_all = parse_file(path, period=None)
    assert [t.pua for t in tokens_all] == ["hana", "tul", "sey", "ney"]


# 8. run_corpus_list() emits one row per <letter>
def test_run_corpus_list_multiple_letter_rows(tmp_path: Path, monkeypatch) -> None:
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    _mixed_century_file(corpus_dir)
    monkeypatch.chdir(tmp_path)

    args = CLIArgs(
        path=corpus_dir,
        period=None,
        model_parameter=None,
        pattern=None,
        purpose=None,
        sort=None,
        corpus_list=True,
        document_type=None,
    )
    run_corpus_list(args)

    lines = (tmp_path / "corpus_list.txt").read_text(encoding="utf-8").splitlines()
    header, *rows = lines
    assert header.split("\t") == [
        "Directory",
        "File name",
        "Letter #",
        "Century",
        "Title",
        "Volume",
        "Year",
        "Raw Year",
        "Author",
        "Sender",
        "Receiver",
    ]
    assert len(rows) == 2
    centuries = sorted(row.split("\t")[3] for row in rows)
    assert centuries == ["15", "19"]


# 9. mixed int/str published_year values must not raise TypeError when sorted
def test_mixed_int_and_string_year_sorting_does_not_raise(tmp_path: Path) -> None:
    xml = """<TEI>
  <letter sender="A" receiver="B" year="1452">
    <sent page="1a" n="1" lang="kor">hana</sent>
  </letter>
  <letter sender="C" receiver="D" year="미상">
    <sent page="2a" n="1" lang="kor">tul</sent>
  </letter>
</TEI>"""
    root = ET.fromstring(xml)
    infos = get_info_from_letters(root)

    assert isinstance(infos[0].published_year, int)
    assert isinstance(infos[1].published_year, str)
    assert infos[1].published_century is None

    sorted_infos = sorted(infos, key=letter_sort_key)
    # int-valued years always sort before string-valued years.
    assert sorted_infos[0].published_year == 1452


# 10. a letter with no discoverable year does not crash the pipeline
def test_letter_missing_year_does_not_crash(tmp_path: Path) -> None:
    xml = """<TEI>
  <letter sender="X" receiver="Y">
    <sent page="1a" n="1" lang="kor">yeoseos</sent>
  </letter>
</TEI>"""
    path = _write(tmp_path / "no_year.xml", xml)
    root = ET.parse(path).getroot()
    info = get_info_from_letters(root)[0]

    assert info.raw_year == ""
    assert info.published_year == ""
    assert info.published_century is None

    # period=None means "no century filter" -> the letter is still processed.
    tokens = parse_file(path, period=None)
    assert [t.pua for t in tokens] == ["yeoseos"]


# 11. general (non-letter) XML behavior is unchanged
def test_general_xml_unchanged(tmp_path: Path) -> None:
    xml = """<TEI>
  <teiHeader><titleStmt><title>General Text</title><date>1459</date></titleStmt></teiHeader>
  <sent page="1a" n="1" lang="kor">yeol seumul</sent>
</TEI>"""
    path = _write(tmp_path / "general.xml", xml)
    root = ET.parse(path).getroot()

    assert has_letters(root) is False

    tokens = parse_file(path, period=99)  # period is ignored for general XML
    assert [t.pua for t in tokens] == ["yeol", "seumul"]
    assert tokens[0].source_id == "1459_General Text:1a:1:kor"


def test_collect_input_files_separates_letter_and_general(tmp_path: Path) -> None:
    letter_dir = tmp_path
    _mixed_century_file(letter_dir)

    general_xml = """<TEI>
  <teiHeader><titleStmt><title>General</title><date>1512</date></titleStmt></teiHeader>
  <sent page="1a" n="1" lang="kor">seuwool</sent>
</TEI>"""
    _write(letter_dir / "general.xml", general_xml)

    files_16c = collect_input_files(tmp_path, 16, document_type=None)
    assert len(files_16c) == 1
    assert files_16c[0].name == "general.xml"

    files_15c = collect_input_files(tmp_path, 15, document_type=None)
    assert len(files_15c) == 1
    assert files_15c[0].name == "mixed.xml"

    only_letters = collect_input_files(tmp_path, 15, document_type="letter")
    assert len(only_letters) == 1
    assert only_letters[0].name == "mixed.xml"

    only_non_letters = collect_input_files(tmp_path, 16, document_type="non-letter")
    assert len(only_non_letters) == 1
    assert only_non_letters[0].name == "general.xml"


# 12. <letter n="..."> is captured as letter_n, so distinct letters in the
# same file (identical year/sender/receiver) remain distinguishable.
def test_letter_n_attribute_captured(tmp_path: Path) -> None:
    xml = """<TEI>
  <letter n="001" sender="A" receiver="B" year="1452">
    <sent page="1a" n="1" lang="kor">hana</sent>
  </letter>
  <letter n="002" sender="A" receiver="B" year="1452">
    <sent page="2a" n="1" lang="kor">tul</sent>
  </letter>
</TEI>"""
    root = ET.fromstring(xml)
    infos = get_info_from_letters(root)
    assert [info.letter_n for info in infos] == ["001", "002"]


def test_letter_n_attribute_missing_defaults_to_empty(tmp_path: Path) -> None:
    xml = """<TEI>
  <letter sender="A" receiver="B" year="1452">
    <sent page="1a" n="1" lang="kor">hana</sent>
  </letter>
</TEI>"""
    root = ET.fromstring(xml)
    info = get_info_from_letters(root)[0]
    assert info.letter_n == ""


def test_run_corpus_list_includes_letter_number(tmp_path: Path, monkeypatch) -> None:
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    xml = """<TEI>
  <letter n="001" sender="A" receiver="B" year="1452">
    <sent page="1a" n="1" lang="kor">hana</sent>
  </letter>
  <letter n="002" sender="A" receiver="B" year="1452">
    <sent page="2a" n="1" lang="kor">tul</sent>
  </letter>
</TEI>"""
    _write(corpus_dir / "sample.xml", xml)
    monkeypatch.chdir(tmp_path)

    args = CLIArgs(
        path=corpus_dir,
        period=None,
        model_parameter=None,
        pattern=None,
        purpose=None,
        sort=None,
        corpus_list=True,
        document_type=None,
    )
    run_corpus_list(args)

    lines = (tmp_path / "corpus_list.txt").read_text(encoding="utf-8").splitlines()
    header, *rows = lines
    letter_col = header.split("\t").index("Letter #")
    letter_numbers = sorted(row.split("\t")[letter_col] for row in rows)
    assert letter_numbers == ["001", "002"]


# 13. "adressee" (missing a "d") is a real misspelling found in NIKL source
# XML and must resolve to the receiver just like the correctly-spelled tag.
def test_letter_adressee_typo_inner_element(tmp_path: Path) -> None:
    xml = """<TEI>
  <letter>
    <writer>E</writer>
    <adressee>F</adressee>
    <year>1620</year>
    <sent page="1a" n="1" lang="kor">tasus</sent>
  </letter>
</TEI>"""
    root = ET.fromstring(xml)
    info = get_info_from_letters(root)[0]
    assert info.receiver == "F"


def test_letter_adressee_typo_sibling_element(tmp_path: Path) -> None:
    xml = """<TEI>
  <text>
    <writer>I</writer>
    <adressee>J</adressee>
    <year>1810</year>
    <letter>
      <sent page="1a" n="1" lang="kor">ahob</sent>
    </letter>
  </text>
</TEI>"""
    root = ET.fromstring(xml)
    info = get_info_from_letters(root)[0]
    assert info.receiver == "J"


def test_trimming_date_and_convert_to_century_moved_to_parser() -> None:
    # Sanity check that the relocated helpers keep their prior behavior.
    assert trimming_date("1452") == 1452
    assert trimming_date("17c") == "1600s"
    assert convert_to_century(1452) == 15
    assert convert_to_century("") is None
