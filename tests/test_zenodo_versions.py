"""The package follows the newest Zenodo dataset version unless one is pinned."""
import hashlib
import importlib
import io
import zipfile
from unittest import mock

import pytest
import requests

import oracc_parser.settings as settings
from oracc_parser.download import fetch_data as fd


@pytest.fixture(autouse=True)
def _fresh(monkeypatch, tmp_path):
    """Isolated data folders, no pinned version, empty record cache."""
    monkeypatch.setattr(settings, "ZENODO_RECORD_URL", None)
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    monkeypatch.setattr(settings, "CATALOGUE_DIR", tmp_path / "catalogues")
    monkeypatch.setattr(settings, "WORD_CSV_DIR", tmp_path / "oracc_csvs")
    monkeypatch.setattr(settings, "JSONZIP_DIR", tmp_path / "jsonzip")
    monkeypatch.setattr(settings, "TRANSLATIONS_DIR", tmp_path / "translations")
    fd._record_cache.clear()
    yield
    fd._record_cache.clear()


def _zip(files: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, text in files.items():
            z.writestr(name, text)
    return buf.getvalue()


def _record(record_id: str, blobs: dict[str, bytes]) -> dict:
    return {
        "id": int(record_id),
        "files": [
            {
                "key": name,
                "size": len(data),
                "checksum": "md5:" + hashlib.md5(data).hexdigest(),
                "links": {"self": f"https://zenodo.org/api/records/{record_id}/files/{name}/content"},
            }
            for name, data in blobs.items()
        ],
    }


class _FakeZenodo:
    """Serves one record for the concept id and lets tests publish new versions."""

    def __init__(self):
        self.records: dict[str, dict] = {}
        self.blobs: dict[str, bytes] = {}
        self.newest = None
        self.downloads: list[str] = []

    def publish(self, record_id: str, blobs: dict[str, bytes]):
        self.records[record_id] = _record(record_id, blobs)
        for name, data in blobs.items():
            self.blobs[f"{record_id}/{name}"] = data
        self.newest = record_id
        fd._record_cache.clear()  # a new session

    def get(self, url, timeout=None, **kw):
        rid = url.rstrip("/").split("/")[-1]
        rid = self.newest if rid == settings.ZENODO_CONCEPT_ID else rid
        resp = mock.Mock()
        resp.raise_for_status = mock.Mock()
        resp.json = mock.Mock(return_value=self.records[rid])
        return resp

    def download_file(self, url, dest, desc=""):
        rid, name = url.split("/records/")[1].split("/files/")
        name = name.removesuffix("/content")
        self.downloads.append(name)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(self.blobs[f"{rid}/{name}"])
        return dest


@pytest.fixture
def zenodo(monkeypatch):
    fake = _FakeZenodo()
    monkeypatch.setattr(fd.requests, "get", fake.get)
    monkeypatch.setattr(fd, "download_file", fake.download_file)
    return fake


class TestRecordUrl:
    @pytest.mark.parametrize("raw", [
        "https://zenodo.org/records/24336925",
        "https://zenodo.org/records/24336925/",
        "https://zenodo.org/api/records/24336925",
        "https://doi.org/10.5281/zenodo.24336925",
        "24336925",
    ])
    def test_record_id_from_url(self, raw):
        assert fd.record_id_from_url(raw) == "24336925"

    def test_rejects_non_record(self):
        with pytest.raises(ValueError):
            fd.record_id_from_url("https://zenodo.org/records/")

    def test_default_is_concept_record(self):
        assert settings.zenodo_url() == f"https://zenodo.org/records/{settings.ZENODO_CONCEPT_ID}"
        assert not settings.zenodo_is_pinned()
        assert settings.get_settings()["zenodo_version"] == "newest"

    def test_pin_in_settings(self, monkeypatch):
        monkeypatch.setattr(settings, "ZENODO_RECORD_URL", "https://zenodo.org/records/111")
        assert settings.zenodo_url() == "https://zenodo.org/records/111"
        assert settings.zenodo_is_pinned()

    def test_pin_with_environment_variable(self, monkeypatch):
        monkeypatch.setenv("ORACC_ZENODO_RECORD_URL", "https://zenodo.org/records/222")
        try:
            importlib.reload(settings)
            assert settings.zenodo_url() == "https://zenodo.org/records/222"
        finally:
            monkeypatch.delenv("ORACC_ZENODO_RECORD_URL")
            importlib.reload(settings)
        assert settings.ZENODO_RECORD_URL is None


class TestResolve:
    def test_concept_resolves_to_newest(self, zenodo):
        zenodo.publish("100", {"catalogues.zip": b"x"})
        zenodo.publish("200", {"catalogues.zip": b"y"})
        assert fd.resolve_record_id() == "200"

    def test_pinned_version_is_used(self, zenodo, monkeypatch):
        zenodo.publish("100", {"catalogues.zip": b"x"})
        zenodo.publish("200", {"catalogues.zip": b"y"})
        monkeypatch.setattr(settings, "ZENODO_RECORD_URL", "https://zenodo.org/records/100")
        assert fd.resolve_record_id() == "100"

    def test_falls_back_when_zenodo_unreachable(self, monkeypatch):
        def boom(*a, **k):
            raise requests.ConnectionError("offline")
        monkeypatch.setattr(fd.requests, "get", boom)
        assert fd.resolve_record() == (settings.ZENODO_FALLBACK_RECORD_ID, None)

    def test_pinned_version_never_falls_back(self, monkeypatch):
        def boom(*a, **k):
            raise requests.ConnectionError("offline")
        monkeypatch.setattr(fd.requests, "get", boom)
        monkeypatch.setattr(settings, "ZENODO_RECORD_URL", "https://zenodo.org/records/100")
        with pytest.raises(requests.ConnectionError):
            fd.resolve_record()


class TestFetchDataFollowsVersions:
    def test_new_version_refreshes_catalogues(self, zenodo):
        zenodo.publish("100", {"catalogues.zip": _zip({"saao-saa01.csv": "old"})})
        fd.fetch_data()
        cat = settings.CATALOGUE_DIR
        assert (cat / "saao-saa01.csv").read_text() == "old"

        # Same version again: nothing is downloaded.
        fd.fetch_data()
        assert zenodo.downloads == ["catalogues.zip"]

        # A new version that changes the file and adds a project.
        zenodo.publish("200", {"catalogues.zip": _zip({"saao-saa01.csv": "new", "ctij.csv": "c"})})
        fd.fetch_data()
        assert zenodo.downloads == ["catalogues.zip", "catalogues.zip"]
        assert (cat / "saao-saa01.csv").read_text() == "new"
        assert (cat / "ctij.csv").read_text() == "c"
        assert fd._load_state()["catalogues.zip"]["record_id"] == "200"

    def test_new_version_with_unchanged_file_skips_it(self, zenodo):
        blob = _zip({"a.csv": "a"})
        zenodo.publish("100", {"catalogues.zip": blob})
        fd.fetch_data()
        zenodo.publish("200", {"catalogues.zip": blob, "ctij.zip": b"z"})
        fd.fetch_data()
        assert zenodo.downloads == ["catalogues.zip"]

    def test_catalogues_without_state_are_refreshed(self, zenodo):
        """Data extracted by an older package version (no state file) is replaced."""
        settings.CATALOGUE_DIR.mkdir(parents=True)
        (settings.CATALOGUE_DIR / "a.csv").write_text("stale")
        zenodo.publish("100", {"catalogues.zip": _zip({"a.csv": "fresh"})})
        fd.fetch_data()
        assert (settings.CATALOGUE_DIR / "a.csv").read_text() == "fresh"

    def test_explicit_url_selects_version(self, zenodo):
        zenodo.publish("100", {"catalogues.zip": _zip({"a.csv": "v1"})})
        zenodo.publish("200", {"catalogues.zip": _zip({"a.csv": "v2"})})
        fd.fetch_data(url="https://zenodo.org/records/100")
        assert (settings.CATALOGUE_DIR / "a.csv").read_text() == "v1"

    def test_corrupt_download_is_rejected(self, zenodo, monkeypatch):
        zenodo.publish("100", {"catalogues.zip": _zip({"a.csv": "a"})})
        monkeypatch.setattr(
            fd, "download_file",
            lambda url, dest, desc="": dest.write_bytes(b"truncated") or dest,
        )
        with pytest.raises(SystemExit):
            fd.fetch_data()
        assert not (settings.DATA_DIR / "catalogues.zip").exists()


class TestLazyWordCsvs:
    def test_project_csvs_come_from_newest_version(self, zenodo):
        zenodo.publish("100", {"catalogues.zip": b"", "ctij.zip": _zip({"ctij/P1.csv": "old"})})
        zenodo.publish("200", {"catalogues.zip": b"", "ctij.zip": _zip({"ctij/P1.csv": "new"})})
        path = fd.extract_project_csvs("ctij")
        assert (path / "P1.csv").read_text() == "new"
        assert fd._load_state()["ctij.zip"]["record_id"] == "200"

    def test_fetch_data_reports_stale_word_csvs(self, zenodo, capsys):
        zenodo.publish("100", {"catalogues.zip": _zip({"a.csv": "a"}), "saao.zip": _zip({"saao-saa01/P1.csv": "1"})})
        fd.extract_project_csvs("saao/saa01")
        zenodo.publish("200", {"catalogues.zip": _zip({"a.csv": "a"}), "saao.zip": _zip({"saao-saa01/P1.csv": "2"})})
        fd.fetch_data()
        out = capsys.readouterr().out
        assert "changed the word CSVs of: saao" in out
