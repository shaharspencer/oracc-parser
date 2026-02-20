"""Tests for the export module (JSONL and CSV)."""

import json
import csv
import tempfile
from pathlib import Path

import pytest

from oracc_parser.export.to_jsonl import to_csv, to_jsonl


class TestJSONLExport:
    """JSONL export should produce valid JSON lines."""

    def test_export_creates_file(self, sample_record, tmp_path):
        output = tmp_path / "test.jsonl"
        result = to_jsonl([sample_record], output)
        assert result.exists()
        assert result.stat().st_size > 0

    def test_export_valid_json_lines(self, sample_record, tmp_path):
        output = tmp_path / "test.jsonl"
        to_jsonl([sample_record], output)
        with open(output, "r", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line)
                assert "id" in data
                assert "transliteration" in data

    def test_export_empty_records(self, tmp_path):
        output = tmp_path / "empty.jsonl"
        to_jsonl([], output)
        assert output.exists()
        assert output.stat().st_size == 0


class TestCSVExport:
    """CSV export should produce a valid CSV file."""

    def test_export_creates_file(self, sample_record, tmp_path):
        output = tmp_path / "test.csv"
        result = to_csv([sample_record], output)
        assert result.exists()
        assert result.stat().st_size > 0

    def test_export_has_header(self, sample_record, tmp_path):
        output = tmp_path / "test.csv"
        to_csv([sample_record], output)
        with open(output, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            assert "id" in fieldnames
            assert "transliteration" in fieldnames
            assert "provenance" in fieldnames

    def test_export_data_matches(self, sample_record, tmp_path):
        output = tmp_path / "test.csv"
        to_csv([sample_record], output)
        with open(output, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            assert rows[0]["id"] == "test_P000001"
