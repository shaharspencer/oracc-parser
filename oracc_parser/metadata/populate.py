"""
Populate tablet metadata from ORACC catalogue entries.

Logic ported from src/metadata_processing/:
  - populate_table_metadata.py
  - get_tablet_copyright_information.py
  - map_tablet_to_city.py
  - map_tablet_to_state.py
  - get_tablet_chronological_information.py
"""

import re

from oracc_parser.models.tablet import (
    City,
    TabletChronologicalInformation,
    TabletGeographicalInformation,
    TabletMetadata,
    TabletPeriod,
)
from oracc_parser.utils.logger import get_logger
from oracc_parser.utils.paths import get_provenience, get_period_mapping

logger = get_logger()

# ---------------------------------------------------------------------------
# Lazy-loaded reference data
# ---------------------------------------------------------------------------

_provenience_df = None
_period_df = None
_normalized_cities: dict[str, City] | None = None


def _ensure_loaded():
    global _provenience_df, _period_df, _normalized_cities
    try:
        if _provenience_df is None:
            _provenience_df = get_provenience(pleiades_only=False)
        if _period_df is None:
            _period_df = get_period_mapping()
        if _normalized_cities is None:
            _normalized_cities = _build_normalized_cities(_provenience_df)
    except Exception as e:
        logger.error(f"error loading reference data: {e}")


def _build_normalized_cities(df) -> dict[str, City]:
    """Build raw_provenience → City dict from the bundled provenience CSV.

    Mirrors src/utils/path_utils.get_normalized_cities().
    """
    result = {}
    for _, row in df.iterrows():
        try:
            raw = row.get("raw_provenience", "")
            city_name = row.get("normalized_city", "")
            pleiades_id = str(row.get("pleiades_id", "")).strip()
            # Guard against NaN: bool(float('nan')) is True, so we must
            # explicitly check the type, not just truthiness.
            if not isinstance(raw, str) or not isinstance(city_name, str):
                continue
            if raw and city_name:
                result[raw] = City(
                    city_name=city_name,
                    city_plaides_id=pleiades_id if pleiades_id.isdigit() else "",
                )
        except Exception as e:
            logger.warning(f"skipping bad provenience row {dict(row)!r}: {e}")
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def populate_metadata(
    metadata_dict: dict | None,
    text_id: str,
    project: str,
) -> TabletMetadata:
    """Build TabletMetadata from a catalogue entry.

    Logic from src/metadata_processing/populate_table_metadata.py.
    """
    _ensure_loaded()

    md = TabletMetadata(
        identifier=f"{project}_{text_id}",
        project=project,
        id_text=text_id,
        metadata_raw_dict=metadata_dict or {},
    )

    if not metadata_dict:
        logger.error(f"no metadata found in catalogue for tablet {project}/{text_id}")
        return md

    try:
        md.copyright_information = _get_copyright(metadata_dict, project, text_id)
        md.geographical_information = _get_geography(metadata_dict, project, text_id)
        md.chronological_information = _get_chronology(metadata_dict, project, text_id)
        md.genre = metadata_dict.get("genre", "")
    except Exception as e:
        logger.error(f"error in populate_metadata for {project}/{text_id}: {e}")

    return md


# ---------------------------------------------------------------------------
# Copyright  (from src/metadata_processing/get_tablet_copyright_information.py)
# ---------------------------------------------------------------------------

_COPYRIGHT_KEYS = [
    "atae_attribution",
    "attribution",
    "author",
    "btto_attribution",
    "credits",
    "editor",
    "riao_attribution",
    "saa_attribution",
    "cite_as",
    "please_cite",
    "external_resources",
    "external_resources_key",
    "uri",
]


def _get_copyright(metadata_dict: dict, project: str, text_id: str) -> str:
    try:
        parts = []
        for key in _COPYRIGHT_KEYS:
            value = metadata_dict.get(key)
            if value:
                parts.append(f"{key}: {value}")
        
        copyright_information_string = ", ".join(parts)
        if not copyright_information_string:
            import json
            copyright_information_string = f"metedata for text was: {json.dumps(metadata_dict)}"
        return copyright_information_string
    except Exception as e:
        logger.error(f"error in get_copyright_information for {project} - {text_id}: {e}")
        return ""


# ---------------------------------------------------------------------------
# Geography  (from src/metadata_processing/map_tablet_to_city.py + map_tablet_to_state.py)
# ---------------------------------------------------------------------------

_PREFIX_TO_STATE: list[tuple[str, str]] = [
    ("atae",  "Neo-Assyrian Empire"),
    ("asbp",  "Neo-Assyrian Empire"),
    ("riao",  "Neo-Assyrian Empire"),
    ("rinap", "Neo-Assyrian Empire"),
    ("saao",  "Neo-Assyrian Empire"),
    ("tcma",  "Middle-Assyrian State"),
]

_PROJECT_TO_STATE: dict[str, str] = {
    "ribo-bab7scores156":                 "Neo Babylonian Empire",
    "ribo-babylon101":                    "Hellenistic",
    "ribo-babylon240":                    "Babylonia Transition Period 2nd to 1st mill",
    "ribo-babylon34":                     "Babylonia Transition Period 2nd to 1st mill",
    "ribo-babylon46":                     "Babylonia Transition Period 2nd to 1st mill",
    "ribo-babylon51":                     "Babylonia Transition Period 2nd to 1st mill",
    "ribo-babylon6127":                   "WE HAVE NOT YET MAPPED THIS PROJECT",
    "ribo-babylon7244":                   "Neo Babylonian Empire",
    "ribo-babylon83":                     "Achemenid",
    "ribo-scores111":                     "Neo Babylonian Empire",
    "ribo-sources400":                    "Neo Babylonian Empire",
    "rimanum378":                         "Babylonia",
    "suhu33":                             "Suhu",
    "urap148":                            "First Sealand Dynasty",
    "ario175":                            "Achemenid",
}


def _get_state(project: str) -> str:
    """Map project name to a state supergroup string.

    Mirrors src/metadata_processing/map_tablet_to_state.py.
    """
    try:
        for prefix, state in _PREFIX_TO_STATE:
            if project.startswith(prefix):
                return state
        return _PROJECT_TO_STATE.get(project, "WE HAVE NOT YET MAPPED THIS PROJECT")
    except Exception as e:
        logger.error(f"error in get_state for project {project!r}: {e}")
        return "WE HAVE NOT YET MAPPED THIS PROJECT"


def _get_city(raw_prov: str, project: str, text_id: str) -> City:
    """Map raw provenience string to a City object.

    Mirrors src/metadata_processing/map_tablet_to_city.py.
    """
    try:
        if raw_prov in _normalized_cities:
            return _normalized_cities[raw_prov]
        logger.error(f"tablet {project} - {text_id} does not have a normalized city")
        return City(city_name="CITY NOT MAPPED YET")
    except Exception as e:
        logger.error(f"error in get_city for {project} - {text_id}: {e}")
        return City(city_name="CITY NOT MAPPED YET")


def _get_geography(metadata_dict: dict, project: str, text_id: str) -> TabletGeographicalInformation:
    try:
        geo = TabletGeographicalInformation()
        geo.state_supergroup = _get_state(project)
        raw_prov = metadata_dict.get("provenience", "")
        if raw_prov:
            geo.city = _get_city(raw_prov, project, text_id)
        return geo
    except Exception as e:
        logger.error(f"error in get_geography for {project}/{text_id}: {e}")
        return TabletGeographicalInformation()


# ---------------------------------------------------------------------------
# Chronology  (from src/metadata_processing/get_tablet_chronological_information.py)
# ---------------------------------------------------------------------------


def _get_chronology(metadata_dict: dict, project: str, text_id: str) -> TabletChronologicalInformation:
    """Extract chronological information from an ORACC catalogue entry.

    Mirrors src/metadata_processing/get_tablet_chronological_information.py.
    Priority: date_bce → date → regnal_dates → period.
    """
    info = TabletChronologicalInformation()

    try:
        # 1. date_bce
        if date_bce := metadata_dict.get("date_bce"):
            start, end = _parse_date_bce(date_bce)
            if start and end:
                info.start_year, info.end_year = start, end
                info.years_source = "date_bce"

        # 2. date
        if (date := metadata_dict.get("date")) and not info.years_source:
            start, end = _parse_date(date)
            if start and end:
                info.start_year, info.end_year = start, end
                info.years_source = "date"

        # 3. regnal_dates
        if (regnal := metadata_dict.get("regnal_dates")) and not info.years_source:
            start, end = _parse_regnal(regnal)
            if start and end:
                info.start_year, info.end_year = start, end
                info.years_source = "regnal_dates"

        # 4. period (always populate tablet_period; use as year fallback)
        if period := metadata_dict.get("period"):
            period_info = _get_period(period)
            info.tablet_period = period_info
            if period_info.period_start_year and period_info.period_end_year and not info.years_source:
                info.start_year = period_info.period_start_year
                info.end_year = period_info.period_end_year
                info.years_source = "period"

        if not (info.start_year and info.end_year):
            logger.debug(f"could not resolve dates for {project}/{text_id}")

    except Exception as e:
        logger.warning(f"error in get_chronology for {project}/{text_id}: {e}")

    return info


def _parse_date_bce(date_bce_string: str) -> tuple[int | None, int | None]:
    """Parse BCE fraction strings like ``262/1`` → ``(-262, -261)``."""
    try:
        start_s, end_s = date_bce_string.split("/")
        start = -int(start_s)
        end = start + int(end_s)
        return start, end
    except Exception as e:
        logger.error(f"error in parse_date_bce for {date_bce_string!r}: {e}")
        return None, None


def _parse_date(date_string: str) -> tuple[int | None, int | None]:
    """Parse diverse ORACC date strings (centuries, ranges, single years, qualifiers)."""
    try:
        if not date_string or not isinstance(date_string, str):
            return None, None

        s = date_string.strip().lower()

        # ---- CENTURIES ----
        m_cent = re.search(r"(\d+)(?:st|nd|rd|th)?\s*century", s)
        if m_cent:
            c = int(m_cent.group(1))
            return -(c * 100), -(c * 100 - 99)

        # ---- REJECT completely unknown entries ----
        if re.fullmatch(r"\[+\.+\]+", s):
            return None, None

        # ---- CLEANUP ----
        s = re.sub(r"[\?\*\(\)\[\]₀₁₂₃₄₅₆₇₈₉]", "", s)
        s = re.sub(r"\bor\b", "/", s)
        s = re.sub(r"\b(ca\.?|circa|about)\b", "", s)
        s = re.sub(r"\s+", " ", s).strip()

        # ---- QUALIFIERS ----
        s = re.sub(r"\b(after|post|before|prior to|pre)\b", "", s).strip()

        # ---- YEAR RANGES ----
        m_range = re.search(r"\b(\d{3,4})(?:\s*[-/]\s*(\d{3,4}))+", s)
        if m_range:
            nums = [int(x) for x in re.findall(r"\d{3,4}", m_range.group(0))]
            if len(nums) >= 2:
                return -max(nums), -min(nums)
            return -nums[0], -nums[0]

        # ---- SINGLE YEAR ----
        m_year = re.search(r"\b(\d{3,4})\b", s)
        if m_year:
            y = int(m_year.group(1))
            return -y, -y

        # ---- QUALIFIED single-year fallback ----
        m_qual = re.search(r"\b(\d{3,4})\b", date_string)
        if m_qual:
            y = int(m_qual.group(1))
            return -y, -y

    except Exception as e:
        logger.error(f"error in parse_date for {date_string!r}: {e}")

    return None, None


def _parse_regnal(regnal_string: str) -> tuple[int | None, int | None]:
    """Parse regnal date ranges like ``680–669 BC``."""
    try:
        if not isinstance(regnal_string, str) or not regnal_string.strip():
            return None, None

        s = regnal_string.strip()
        s = s.replace("–", "-").replace("—", "-").replace("−", "-")
        s = re.sub(r"\s+", " ", s)
        s = re.sub(r"\bca\.?\s*", "", s, flags=re.IGNORECASE)

        # Range: 680-669 BC
        match = re.match(
            r"(?i)^(?P<start>\d{2,4})\s*-\s*(?P<end>\d{2,4})\s*(?P<era>BC|AD)?$",
            s,
        )
        if not match:
            match = re.match(
                r"(?i)^(?P<start>\d{2,4})\s*-\s*(?P<end>\d{2,4})\s*BC$",
                s,
            )

        if match:
            start = int(match.group("start"))
            end = int(match.group("end"))
            era = match.group("era") or "BC"
            if era.upper() == "BC":
                start, end = -start, -end
            if start > end:
                start, end = end, start
            return start, end

        # Single year: 668 BC
        match = re.match(r"(?i)(\d{2,4})\s*(BC|AD)?", s)
        if match:
            year = int(match.group(1))
            era = match.group(2) or "BC"
            if era.upper() == "BC":
                year = -year
            return year, year

    except Exception as e:
        logger.error(f"error in parse_regnal for {regnal_string!r}: {e}")

    return None, None


def _get_period(period_string: str) -> TabletPeriod:
    """Map a period name to start/end years via the bundled period mapping CSV."""
    period = TabletPeriod()
    try:
        if period_string == "Neo Assyrian":
            period_string = "Neo-Assyrian"

        rows = _period_df.loc[
            _period_df["period_name"].str.lower() == period_string.lower()
        ]
        if not rows.empty:
            row = rows.iloc[0]
            # Use the canonical name from the CSV (preserves correct casing like
            # "Neo-Assyrian") rather than always lowercasing the raw input.
            period.period_name = row["period_name"]
            period.period_start_year = int(row["start_year"])
            period.period_end_year = int(row["end_year"])
        else:
            # Unknown period — store the raw value title-cased as best effort
            period.period_name = period_string.title()
            logger.error(f"period {period_string!r} not found in period_mapping.csv")

    except Exception as e:
        logger.error(f"error in get_period for {period_string!r}: {e}")

    return period
