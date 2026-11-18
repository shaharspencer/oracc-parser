"""
Build-time completeness check for the Zenodo dataset.

Every project in ``projects_metadata.csv`` that is in scope for the dataset
should produce a catalogue CSV, a word-CSV folder and a raw JSON ZIP. A project
that silently drops out of the build (as ``atae/saab0509`` did, because of a
trailing slash in its metadata row) is caught here.

In scope = not an umbrella project, ``Is_Text_Folder_Empty == "no"``, and
``Languages`` mentions Akkadian. Projects excluded on purpose can be listed in
``allow_missing``.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from oracc_parser.utils.paths import get_projects_metadata, project_slug


@dataclass
class CompletenessReport:
    expected: list[str] = field(default_factory=list)
    missing_catalogue: list[str] = field(default_factory=list)
    missing_word_csvs: list[str] = field(default_factory=list)
    missing_jsonzip: list[str] = field(default_factory=list)
    allowed_missing: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not (self.missing_catalogue or self.missing_word_csvs or self.missing_jsonzip)

    def summary(self) -> str:
        lines = [f"{len(self.expected)} project(s) expected in the dataset"]
        for label, items in [
            ("missing catalogue CSV", self.missing_catalogue),
            ("missing word-CSV folder", self.missing_word_csvs),
            ("missing JSON ZIP", self.missing_jsonzip),
            ("allowed to be missing", self.allowed_missing),
        ]:
            if items:
                lines.append(f"  {label} ({len(items)}): {', '.join(items)}")
        lines.append("OK" if self.ok else "INCOMPLETE")
        return "\n".join(lines)


def expected_projects(metadata: pd.DataFrame | None = None) -> list[str]:
    """Return the project paths that should be present in the dataset."""
    df = get_projects_metadata() if metadata is None else metadata
    df = df.fillna("")
    mask = (
        (df["Is_Text_Folder_Empty"].str.strip().str.lower() == "no")
        & (df["Is_Umbrella_Project"].str.strip().str.lower() != "yes")
        & df["Languages"].str.contains("Akkadian", case=False)
    )
    return sorted(df.loc[mask, "Project_Name"].str.strip().str.strip("/"))


def check_completeness(
    catalogue_slugs: set[str],
    word_csv_slugs: set[str],
    jsonzip_slugs: set[str],
    metadata: pd.DataFrame | None = None,
    allow_missing: set[str] | None = None,
) -> CompletenessReport:
    """Compare the dataset contents with the projects that should be in it.

    Args:
        catalogue_slugs: Slugs with a catalogue CSV (``atae-saab0509``).
        word_csv_slugs:  Slugs with a non-empty word-CSV folder.
        jsonzip_slugs:   Slugs with a raw JSON ZIP.
        metadata:        Projects metadata table (defaults to the bundled one).
        allow_missing:   Project paths or slugs excluded on purpose.
    """
    allow = {project_slug(p) for p in (allow_missing or set())}
    report = CompletenessReport()
    for project in expected_projects(metadata):
        slug = project_slug(project)
        report.expected.append(project)
        missing = [
            (slug not in catalogue_slugs, report.missing_catalogue),
            (slug not in word_csv_slugs, report.missing_word_csvs),
            (slug not in jsonzip_slugs, report.missing_jsonzip),
        ]
        if any(m for m, _ in missing) and slug in allow:
            report.allowed_missing.append(project)
            continue
        for is_missing, bucket in missing:
            if is_missing:
                bucket.append(project)
    return report
