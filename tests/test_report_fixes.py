"""Regression tests for the issues in the 2026-11 external bug report.

Numbers in the class names refer to the report's sections.
"""
import ast
from pathlib import Path
from unittest import mock

import pandas as pd
import pytest

from oracc_parser.utils.paths import (
    get_genre_classes,
    get_metadata_rules,
    get_period_mapping,
    get_projects_metadata,
    get_provenience,
    normalize_project,
    project_slug,
)


# ---------------------------------------------------------------------------
# §1  trailing slash in a project id / ORACC download URL
# ---------------------------------------------------------------------------


class TestProjectIds:
    @pytest.mark.parametrize("raw, path, slug", [
        ("atae/saab0509/", "atae/saab0509", "atae-saab0509"),
        ("/saao/saa01", "saao/saa01", "saao-saa01"),
        (" riao/ria1 ", "riao/ria1", "riao-ria1"),
        ("balt", "balt", "balt"),
        ("aemw/alalakh/idrimi", "aemw/alalakh/idrimi", "aemw-alalakh-idrimi"),
    ])
    def test_normalize_and_slug(self, raw, path, slug):
        assert normalize_project(raw) == path
        assert project_slug(raw) == slug

    def test_no_trailing_slash_in_projects_metadata(self):
        names = get_projects_metadata()["Project_Name"].dropna()
        bad = [n for n in names if n != n.strip().strip("/")]
        assert bad == []

    def test_download_zip_uses_slug_for_url_and_filename(self, tmp_path):
        from oracc_parser.download import oracc_download

        resp = mock.MagicMock()
        resp.headers = {"content-length": "3"}
        resp.iter_content.return_value = [b"zip"]
        with mock.patch.object(oracc_download.requests, "get", return_value=resp) as get:
            dest = oracc_download.download_zip("atae/saab0509/", output_dir=tmp_path)
        url = get.call_args.args[0]
        assert url.endswith("/json/atae-saab0509.zip")
        assert "//json" not in url
        assert dest == tmp_path / "atae-saab0509.zip"


# ---------------------------------------------------------------------------
# §2  one empty word CSV must not take down the whole project
# ---------------------------------------------------------------------------


class TestEmptyWordCsv:
    def test_empty_and_header_only_files_are_skipped(self, tmp_path):
        from oracc_parser.io.word_csv import load_word_csvs_from_dir

        d = tmp_path / "balt"
        d.mkdir()
        (d / "P000001.csv").write_text("text_id,project,word_index\nP000001,balt,0\n", encoding="utf-8")
        (d / "P365637.csv").write_bytes(b"\r\n")  # the 2-byte file from Zenodo
        (d / "P000002.csv").write_text("text_id,project,word_index\n", encoding="utf-8")

        result = load_word_csvs_from_dir(d)
        assert list(result) == ["P000001"]


# ---------------------------------------------------------------------------
# §3  city table rows + lenient lookup
# ---------------------------------------------------------------------------


class TestCityLookup:
    @pytest.fixture(autouse=True)
    def _load(self):
        from oracc_parser.metadata import populate
        populate._ensure_loaded()
        self.populate = populate

    @pytest.mark.parametrize("raw, city, pleiades", [
        ("Babylon (mod. Bābil)", "Babylon", "893951"),
        ("Kish (mod. Tell Ingharra)", "Kish", "894028"),
        ("Upi (mod. Opis)", "Opis", "894056"),
    ])
    def test_fixed_rows(self, raw, city, pleiades):
        c = self.populate._get_city(raw, "test", "P1")
        assert (c.city_name, c.city_plaides_id) == (city, pleiades)

    @pytest.mark.parametrize("raw, city", [
        ("babylon  (mod. babil)", "Babylon"),       # case + whitespace + diacritics
        ("Kish (mod. Some Other Tell)", "Kish"),    # unknown (mod. …) variant
        ("Nineveh (mod. Kuyunjik)", "Nineveh"),
    ])
    def test_lenient_variants(self, raw, city):
        assert self.populate._get_city(raw, "test", "P1").city_name == city

    def test_unknown_still_unmapped(self):
        assert self.populate._get_city("Atlantis", "test", "P1").city_name == "CITY NOT MAPPED YET"

    def test_ambiguous_keys_are_not_guessed(self):
        from oracc_parser.models.tablet import City
        fuzzy = self.populate._build_fuzzy_cities({
            "Ešnunna": City(city_name="A"),
            "Esnunna": City(city_name="B"),
        })
        assert fuzzy["esnunna"] is None


# ---------------------------------------------------------------------------
# §4  genre / period fallbacks and their source fields
# ---------------------------------------------------------------------------


def _md(row, project="test/proj", text_id="P1"):
    from oracc_parser.metadata.populate import populate_metadata
    return populate_metadata(row, text_id, project)


class TestGenreFallback:
    def test_primary_genre_wins(self):
        md = _md({"genre": "Letter", "genres": "Legal", "subgenre": "Loan"})
        assert (md.genre, md.genre_source) == ("Letter", "genre")

    def test_genres_then_subgenre(self):
        assert _md({"genre": "", "genres": "Legal"}).genre_source == "genres"
        md = _md({"genre": " ", "genres": "", "subgenre": "Loan of lead"})
        assert (md.genre, md.genre_source) == ("Loan of lead", "subgenre")

    def test_project_rule(self):
        md = _md({"designation": "x"}, project="asbp/ninmed")
        assert (md.genre, md.genre_source, md.genre_class) == ("Scholarly", "rule:project", "Scholarly")

    @pytest.mark.parametrize("designation, genre", [
        ("VS 3, 012", "Legal"),
        ("UCP 9/1, I, 047", "Administrative"),
        ("UCP 9/12, 003", ""),   # exact match, not prefix
        ("GCCI 2, 100", ""),
        ("TMH 02-3, 5", ""),
    ])
    def test_balt_designation_rule(self, designation, genre):
        md = _md({"designation": designation}, project="balt")
        assert md.genre == genre
        assert md.genre_source == ("rule:designation" if genre else "")

    def test_rules_do_not_leak_to_other_projects(self):
        assert _md({"designation": "VS 3, 012"}, project="saao/saa01").genre == ""


class TestPeriodFallback:
    def test_primary_period(self):
        ci = _md({"period": "Neo-Assyrian"}).chronological_information
        assert (ci.tablet_period.period_name, ci.period_source) == ("Neo-Assyrian", "period")

    def test_seventh_century_date(self):
        ci = _md({"date": "7th century BC"}, project="asbp/ninmed").chronological_information
        assert (ci.tablet_period.period_name, ci.period_source) == ("Neo-Assyrian", "rule:date")

    def test_goal_year(self):
        ci = _md({"goal_year": "SE 120"}, project="adsd/adart6").chronological_information
        assert (ci.tablet_period.period_name, ci.period_source) == ("Hellenistic", "rule:goal_year")
        assert (ci.start_year, ci.end_year, ci.years_source) == (-323, -63, "period")

    def test_no_period(self):
        ci = _md({"date": "1st year of Esarhaddon"}).chronological_information
        assert (ci.tablet_period.period_name, ci.period_source) == ("", "")


class TestRulesTable:
    def test_rules_are_well_formed(self):
        rules = get_metadata_rules()
        assert set(rules["target"]) <= {"genre", "period"}
        assert set(rules["match"]) <= {"any", "exact", "leading_token", "nonempty"}
        assert set(rules["kind"]) <= {"general", "editorial"}
        periods = set(get_period_mapping()["period_name"])
        assert set(rules.loc[rules["target"] == "period", "value"]) <= periods


# ---------------------------------------------------------------------------
# §5  period canonical names
# ---------------------------------------------------------------------------


class TestPeriodMapping:
    def test_no_case_duplicates_and_no_lowercase_names(self):
        names = get_period_mapping()["period_name"]
        assert names.str.lower().is_unique
        assert not names.str.match(r"^[a-z]").any()

    @pytest.mark.parametrize("raw, canonical", [
        ("achaemenid", "Achaemenid"), ("HELLENISTIC", "Hellenistic"), ("uncertain", "Uncertain"),
    ])
    def test_canonical_casing(self, raw, canonical):
        from oracc_parser.metadata import populate
        populate._ensure_loaded()
        assert populate._get_period(raw).period_name == canonical


# ---------------------------------------------------------------------------
# §6 / §7  genre normalization and classes
# ---------------------------------------------------------------------------


class TestGenreNormalization:
    @pytest.mark.parametrize("raw, normalized", [
        ("letter", "Letter"),
        ("Document  + envelope", "Document + envelope"),
        ("šulmānu", "Šulmānu"),
        ("  Royal   Inscription ", "Royal Inscription"),
        ("Something New", "Something New"),
        ("", ""),
    ])
    def test_normalize(self, raw, normalized):
        from oracc_parser.metadata.genre import normalize_genre
        assert normalize_genre(raw) == normalized

    def test_class_table_complete(self):
        df = get_genre_classes()
        assert len(df) == 251
        assert df["genre_class"].nunique() == 12  # 11 classes + Uncertain

    @pytest.mark.parametrize("raw, source, cls", [
        ("letter", "genre", "Letter"),
        ("Document  + envelope", "subgenre", "Administrative"),
        ("Astronomical Diary", "genre", "Astronomical"),
        ("Fragment", "subgenre", "Uncertain"),
        ("Scholarly", "rule:project", "Scholarly"),
        ("Not in the table", "genre", ""),
    ])
    def test_classify(self, raw, source, cls):
        from oracc_parser.metadata.genre import classify_genre
        assert classify_genre(raw, source) == cls

    def test_populated_on_metadata(self):
        md = _md({"genre": "administrative record"})
        assert (md.genre_normalized, md.genre_class) == ("Administrative Record", "Administrative")


# ---------------------------------------------------------------------------
# §8  to_mask flag
# ---------------------------------------------------------------------------


class TestToMask:
    def test_mask_flag_follows_yes_no_column(self):
        from oracc_parser.parsing.parse_words import _load_lookups, _pos_dict
        _load_lookups()
        assert _pos_dict["PN"].to_mask is True
        assert _pos_dict["N"].to_mask is False


# ---------------------------------------------------------------------------
# §9  no non-ASCII in print() calls of the download module
# ---------------------------------------------------------------------------


class TestAsciiPrints:
    def test_fetch_data_prints_are_ascii(self):
        import oracc_parser.download.fetch_data as fd
        tree = ast.parse(Path(fd.__file__).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "print":
                src = ast.unparse(node)
                assert src.isascii(), src


# ---------------------------------------------------------------------------
# §10  project_slug on records and output tables
# ---------------------------------------------------------------------------


class TestProjectSlugField:
    def test_on_metadata(self):
        md = _md({"genre": "Letter"}, project="riao/ria1")
        assert (md.project, md.project_slug) == ("riao/ria1", "riao-ria1")

    def test_in_metadata_table(self):
        from oracc_parser.models.tablet import TabletRecord
        from oracc_parser.pipeline import get_metadata_table
        rec = TabletRecord(metadata=_md({"genre": "letter", "period": "achaemenid"}, project="riao/ria1"))
        row = get_metadata_table([rec]).iloc[0]
        assert row["project_slug"] == "riao-ria1"
        assert (row["genre"], row["genre_source"], row["genre_normalized"], row["genre_class"]) == (
            "letter", "genre", "Letter", "Letter")
        assert (row["period"], row["period_source"]) == ("Achaemenid", "period")


# ---------------------------------------------------------------------------
# Build-time completeness check
# ---------------------------------------------------------------------------


class TestReleaseCheck:
    @pytest.fixture
    def metadata(self):
        return pd.DataFrame([
            # Project_Name, Languages, Is_Umbrella_Project, Is_Text_Folder_Empty
            ("atae", "Akkadian", "yes", "no"),
            ("atae/saab0509/", "Akkadian", "no", "no"),
            ("atae/ctn1", "Akkadian", "no", "no"),
            ("ckst", "Akkadian, Sumerian", "no", "no"),
            ("epsd2/royal", "Sumerian", "no", "no"),
            ("saao/saa20", "Akkadian", "no", "yes"),
        ], columns=["Project_Name", "Languages", "Is_Umbrella_Project", "Is_Text_Folder_Empty"])

    def test_expected_projects(self, metadata):
        from oracc_parser.download.release_check import expected_projects
        assert expected_projects(metadata) == ["atae/ctn1", "atae/saab0509", "ckst"]

    def test_detects_missing_and_allows_exclusions(self, metadata):
        from oracc_parser.download.release_check import check_completeness
        have = {"atae-ctn1"}
        report = check_completeness(have, have, have | {"ckst"}, metadata, allow_missing={"ckst"})
        assert not report.ok
        assert report.missing_catalogue == ["atae/saab0509"]
        assert report.missing_jsonzip == ["atae/saab0509"]
        assert report.allowed_missing == ["ckst"]

        everything = {"atae-ctn1", "atae-saab0509", "ckst"}
        assert check_completeness(everything, everything, everything, metadata).ok
