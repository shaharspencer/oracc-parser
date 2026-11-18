"""
Build ``enriched_data/genre_normalization.csv`` from the project catalogues.

Raw ``genre`` / ``genres`` / ``subgenre`` strings are passed through verbatim
by ORACC, so the same label shows up in several spellings across projects
(``Letter`` / ``letter``, ``Document + envelope`` / ``Document  + envelope``).

This script counts every spelling across all catalogue CSVs, groups spellings
that are identical after case-folding and whitespace collapsing, and picks a
canonical spelling per group: a spelling with a capitalised first letter if the
group has one (matching ORACC's usual style), the most frequent among those, then
alphabetical order. Only spellings that differ from their canonical form are
written out.

Usage:
    python scripts/build_genre_normalization.py [CATALOGUE_DIR]
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

from oracc_parser.metadata.genre import GENRE_FIELDS, collapse_ws, fold_genre
from oracc_parser.settings import catalogue_dir
from oracc_parser.utils.paths import _data_file


def main(cat_dir: Path) -> None:
    counts: Counter[str] = Counter()
    for f in sorted(cat_dir.glob("*.csv")):
        df = pd.read_csv(f, dtype=str, keep_default_na=False)
        for col in GENRE_FIELDS:
            if col in df.columns:
                counts.update(v for v in df[col] if v.strip())

    groups: dict[str, Counter[str]] = defaultdict(Counter)
    for raw, n in counts.items():
        groups[fold_genre(raw)][raw] += n

    rows = []
    for spellings in groups.values():
        # Canonical spelling: capitalised first, then most frequent.
        collapsed: Counter[str] = Counter()
        for raw, n in spellings.items():
            collapsed[collapse_ws(raw)] += n
        canonical = sorted(
            collapsed.items(),
            key=lambda kv: (not kv[0][:1].isupper(), -kv[1], kv[0]),
        )[0][0]
        for raw, n in spellings.items():
            if raw != canonical:
                rows.append({"variant": raw, "canonical": canonical, "n_texts": n})

    out = pd.DataFrame(rows, columns=["variant", "canonical", "n_texts"])
    out = out.sort_values(["canonical", "variant"]).reset_index(drop=True)
    path = Path(_data_file("genre_normalization.csv"))
    out.to_csv(path, index=False, encoding="utf-8", lineterminator="\n")
    print(f"{len(counts)} distinct raw spellings, {len(groups)} groups, "
          f"{len(out)} non-canonical variants -> {path}")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else catalogue_dir())
