"""
Archive cleaning and normalizing logic for ORACC metadata.

The mapping from raw → normalized archive names is stored in
``oracc_parser/enriched_data/raw_archive_values.csv`` and loaded lazily at
runtime.  Use ``update_archive_mapping()`` in ``oracc_parser.utils.paths`` to
scan the corpus for unmapped raw values.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Lazy-loaded archive mapping (from raw_archive_values.csv)
# ---------------------------------------------------------------------------

_archive_mapping_cache: dict[str, str] | None = None


def _get_archive_mapping() -> dict[str, str]:
    """Return {raw_value: normalized_name} loaded from raw_archive_values.csv.

    Keys are quote-normalized so they match what clean_archive() passes after
    calling _normalize_quotes().
    """
    global _archive_mapping_cache
    if _archive_mapping_cache is not None:
        return _archive_mapping_cache
    from oracc_parser.utils.paths import get_archives
    df = get_archives()
    mapping: dict[str, str] = {}
    for _, row in df.iterrows():
        raw = str(row.get("Raw Archive Value", "")).strip()
        norm = str(row.get("Normalized Archive Value", "")).strip()
        if raw and norm and norm.lower() != "nan":
            # Normalize quotes on keys so lookups match what clean_archive() passes
            mapping[_normalize_quotes(raw)] = norm
            mapping[_normalize_quotes(raw).lower()] = norm
    _archive_mapping_cache = mapping
    return mapping


# ---------------------------------------------------------------------------
# The values below were the old hardcoded mapping dict.
# They now live in raw_archive_values.csv and are loaded via _get_archive_mapping().
# This dict is kept as dead code so the git diff shows what moved.
# ---------------------------------------------------------------------------

_REMOVED = {
    # The Governor's Palace Archive (Nimrud/Kalhu)
    "01 (The Governor’s Palace Archive)": "Governor's Palace Archive",
    "The Governor’s Palace Archive": "Governor's Palace Archive",
    "012 - Governor’s Palace": "Governor's Palace Archive",
    "002 - Governor’s Palace": "Governor's Palace Archive",

    # Northwest Palace, Nimrud (Domestic Wing mostly)
    "01 (Archives from the Domestic Wing of the North-West Palace at Kalhu/Nimrud)": "North-West Palace (Domestic Wing) Archive",
    "Archives from the Domestic Wing of the North-West Palace at Kalhu/Nimrud": "North-West Palace (Domestic Wing) Archive",

    # Assur Privat Archives (N-Series and Named)
    "001 - Mannu-ki-Aššur Archive": "Mannu-ki-Aššur Archive",
    "001 -  Mannu-ki-Aššur Archive": "Mannu-ki-Aššur Archive",
    "052a - Duri-Aššur Archive": "Duri-Aššur Archive",
    "01 (Assur 52a: Das Archiv des Dūrī-Aššur)": "Duri-Aššur Archive",
    "Assur 52a: Das Archiv des Dūrī-Aššur": "Duri-Aššur Archive",
    "046 - N 31 Archive": "Archive N31",
    "048 - N 33 Archive": "Archive N33",
    "19 (Archive N31 (Egyptians))": "Egyptian Archive (Archive N31)",
    "Archive N31 (Egyptians)": "Egyptian Archive (Archive N31)",
    "017 - Šamaš-šarru-uṣur Archive": "Šamaš-šarru-uṣur Archive",
    "006 - Ninurta-šarru-uṣur Archive": "Ninurta-šarru-uṣur Archive",
    "053 - Aššur-matu-taqqin Archive": "Aššur-matu-taqqin Archive",
    "01 (The Archive of Aššur-mātu-taqqin found in the new town of Aššur and dated mainly by Post-Canonical Eponyms)": "Aššur-matu-taqqin Archive",
    "The Archive of Aššur-mātu-taqqin found in the new town of Aššur and dated mainly by Post-Canonical Eponyms": "Aššur-matu-taqqin Archive",
    "040 - N 25 Archive": "Archive N25",
    "14 (Archive N25)": "Archive N25",
    "Archive N25": "Archive N25",
    "014 - Nabû Temple": "Nabu Temple Archive",
    "01 (Tablets from the Nabû Temple)": "Nabu Temple Archive",
    "01 (Die Texte aus N 33)": "Archive N33",
    "035 - N 20 Archive": "Archive N20",
    "10 (Archive N20 (Šarru-iqbi))": "Archive N20",
    "Archive N20 (Šarru-iqbi)": "Archive N20",
    "043 - N 28 Archive": "Archive N28",
    "015 - N 01 Archive": "Archive N1",
    "019 - N 03 Archive": "Archive N3",
    "21 (Archive N33 (Goldsmiths))": "Archive N33",
    "Archive N33 (Goldsmiths)": "Archive N33",
    "018 - N 02 Archive": "Archive N2",
    "042 - N 27 Archive": "Archive N27",
    "020 - N 04 Archive": "Archive N4",
    "045 - N 30 Archive": "Archive N30",
    "18 (Archive N30)": "Archive N30",
    "Archive N30": "Archive N30",
    "001 -  Qurdi-Nergal Archive": "Qurdi-Nergal Archive",
    "001 - Qurdi-Nergal Archive": "Qurdi-Nergal Archive",
    "027 - N 12 Archive": "Archive N12",
    "07 (Archive N12 (Caravansary))": "Archive N12",
    "Archive N12 (Caravansary)": "Archive N12",
    "052b - Egyptian Archive": "Egyptian Archive (Assur 52b)",
    "02 (Assur 52b: Das Archiv einer Gruppe von Ägyptern)": "Egyptian Archive (Assur 52b)",
    "Assur 52b: Das Archiv einer Gruppe von Ägyptern": "Egyptian Archive (Assur 52b)",
    "025 - N 10 Archive": "Archive N10",
    "05 (Archive N10 (Aššur-eriba, hundurayu))": "Archive N10",
    "Archive N10 (Aššur-eriba, hundurayu)": "Archive N10",
    "12 (Texte aus N 31)": "Archive N31",
    "12 (Archive N23)": "Archive N23",
    "038 - N 23 Archive": "Archive N23",
    "Archive N23": "Archive N23",
    "044 - N 29 Archive": "Archive N29",
    "17 (Archive N29)": "Archive N29",
    "Archive N29": "Archive N29",
    "033 - N 18 Archive": "Archive N18",
    "09 (Archive N18 (Arameans))": "Archive N18",
    "Archive N18 (Arameans)": "Archive N18",
    "03 (Texte aus N 2)": "Archive N2",
    "09 (Texte aus N 27)": "Archive N27",
    "10 (Texte aus N 28)": "Archive N28",
    "16 (Archive N28)": "Archive N28",
    "Archive N28": "Archive N28",
    "02 (Archive N3 (Singers))": "Archive N3",
    "Archive N3 (Singers)": "Archive N3",
    "047 - N 32 Archive": "Archive N32",
    "20 (Archive N32 (Tanners))": "Archive N32",
    "Archive N32 (Tanners)": "Archive N32",
    "04 (Archive N9 (Mudammiq-Aššur, hundurayu))": "Archive N9",
    "Archive N9 (Mudammiq-Aššur, hundurayu)": "Archive N9",
    "024 - N 09 Archive": "Archive N9",
    "041 - N 26 Archive": "Archive N26",
    "15 (Archive N26)": "Archive N26",
    "Archive N26": "Archive N26",
    "016 - N 05 Archive": "Archive N5",
    "026 - N 11 Archive": "Archive N11",
    "06 (Archive N11 (Dadaya))": "Archive N11",
    "Archive N11 (Dadaya)": "Archive N11",
    "029 - N 14 Archive": "Archive N14",
    "08 (Archive N14 (Oilpressers))": "Archive N14",
    "Archive N14 (Oilpressers)": "Archive N14",
    "049 - N 34 Archive": "Archive N34",
    "050 - N 35 Archive": "Archive N35",
    "01 (Archive N1 (Aššur Temple))": "Archive N1",
    "Archive N1 (Aššur Temple)": "Archive N1",
    "039 - N 24 Archive": "Archive N24",
    "13 (Archive N24 (Architects))": "Archive N24",
    "Archive N24 (Architects)": "Archive N24",
    "021 - N 06 Archive": "Archive N6",
    "022 - N 07 Archive": "Archive N7",
    "Archive N4 (Exorcists)": "Archive N4",
    "03 (Archive N4 (Exorcists))": "Archive N4",
    "036 - N 21 Archive": "Archive N21",
    "11 (Archive N21 (Doorkeepers))": "Archive N21",
    "Archive N21 (Doorkeepers)": "Archive N21",
    "023 - N 08 Archive": "Archive N8",

    # Other specific named archives
    "003 - Red House": "Red House Archive",
    "001 - Area F, Private Archive": "Area F Private Archive",
    "02 (Tablets from the Town Wall Houses)": "Town Wall Houses Archive",
    "018 - Town Wall Palace": "Town Wall Houses Archive",
    "03 (Three Tablets from the Town Wall Palace)": "Town Wall Houses Archive",
    "001 - Fort Shalmaneser, NE 47-50": "Fort Shalmaneser Archive",
    "001 -  Fort Shalmaneser, NE 47-50": "Fort Shalmaneser Archive",
    "003 - Fort Shalmaneser, Palace Manager Archive (SE 1, SE 10)": "Fort Shalmaneser Archive",
    "004 - Fort Shalmaneser, SE 14-15": "Fort Shalmaneser Archive",
    "005 - Fort Shalmaneser, šakinutu Archive (S 10)": "Fort Shalmaneser Archive",
    "002 - Fort Shalmaneser, SW 6": "Fort Shalmaneser Archive",
    "06 (Administrative records )": "Fort Shalmaneser Archive",  # CTN3 admin records from Fort Shalmaneser
    "01 (Archive of the rab ekall)": "Rab ekalli Archive",
    "Archive of the rab ekall": "Rab ekalli Archive",
    "001 - Hanni Archive (House C1)": "Hanni Archive",
    "Ilia A": "Ilia Archive",
    "Ilia A?": "Ilia Archive",
    "Ilia D": "Ilia Archive",
    "Borsippa 7.2.3.11 (Ilia A)": "Ilia Archive",
    "001 - Mamu Temple, Room 8": "Mamu Temple Archive",
    "Ezida": "Nabu Temple Archive",  # Ezida = the Nabû temple at Kalhu (Nimrud) and Assur
    "002 - Šibaniba 2": "Šibaniba Archive",
    "013 - Burnt Palace": "Burnt Palace Archive",
    "002 - Building F, Room B": "Building F Archive",
    "002 - Il-manani Archive": "Il-manani Archive",
    "001 - Lower Town, Building II,  Rooms 9–10": "Lower Town Building II Archive",
    "M 02 Archive": "Archive M2",
    "m 04 archive": "Archive M4",
    "m 07 archive": "Archive M7",
    "Archive N 2": "Archive N2",
    "Archive N 2 (?)": "Archive N2",
    "Archive N 18": "Archive N18",
    "Ibnāya A": "Ibnāya Archive",
    "Ibnāya B": "Ibnāya Archive",
    "Ibnāya C": "Ibnāya Archive",
    "Ibnāya D": "Ibnāya Archive",
    "Probably Ibnāya A": "Ibnāya Archive",
    "Bēliya’u": "Bēliya’u Archive",
    "Probably periphery of the Bēliya’u archive": "Bēliya’u Archive",
    "Periphery of the Bēliya’u archive": "Bēliya’u Archive",
    "Šaddinnu/periphery of the Bēliya’u archive": "Bēliya’u Archive",
    "Šaddinnu/probably retro of the Bēliya’u archive": "Bēliya’u Archive",
    "Borsippa 7.2.3.4 (Belia’u)": "Bēliya’u Archive",
    "Ilšu-abūšu B": "Ilšu-abūšu Archive",
    "Ilšu-abūšu A /archive of the slave Balāṭu": "Ilšu-abūšu Archive",
    "Kudurrānu A": "Kudurrānu Archive",
    "Ahiya’ūtu": "Ahiya’ūtu Archive",
    "Lā-kuppuru": "Lā-kuppuru Archive",
    "Possibly Lā-kuppuru": "Lā-kuppuru Archive",
    "Mannu-gērûšu": "Mannu-gērûšu Archive",
    "ashipus’ house": "House of the Ashipu",

    # Babylonian specific archives/locations
    "Sippar 7.11.1.2 (later Ebabbar)": "Ebabbar Archive",
    "Sippar 7.11.1.1 (early Ebabbar)": "Ebabbar Archive",
    "Ebabbar, library (Room 355)": "Ebabbar Library",
    "Babylon 7.1.2.8 (Nappāhu)": "Nappāhu Archive",
    "Babylon 7.1.2.4 (Egibi)": "Egibi Archive",
    "Uruk 7.13.2.11 (Mušēzib-Marduk)": "Mušēzib-Marduk Archive",
    "Uruk 7.13.1.1 (Eanna)": "Eanna Archive",
    "Kutha 7.3.3 (Šangû-Ištar-Bābili)": "Šangû-Ištar-Bābili Archive",
    "Kutha 7.3.2 (Re’indu/Nergal-ušēzib)": "Re’indu/Nergal-ušēzib Archive",
    "Kutha 7.3.1 (Bēl-ikṣur)": "Bēl-ikṣur Archive",
    "Borsippa 7.2.2.1 (Ea-ilutu-bani)": "Ea-ilutu-bani Archive",
    "Borsippa 7.2.3.21 (Rē’i-alpi)": "Rē’i-alpi Archive",
    "Rē’i-alpi": "Rē’i-alpi Archive",
    "4. Oxherds": "Rē’i-alpi Archive",
    "1. Brewers": "Sīrāšû Archive",
    "2. Bakers": "Nuhatimmu Archive",
    "3. Butchers": "Ṭābihu Archive",
    "5. Miscellanea": "Ezida Temple Miscellaneous",
    "Nippur 7.10.2.4 (Murašû)": "Murašû Archive",
    "Babylon 7.1.2.2 (Ea-eppēš-ilī A)": "Ea-eppēš-ilī Archive",

    # Specific Libraries
    "Ashurbanipal’s Library": "Ashurbanipal Library",
    "ashurbanipal library": "Ashurbanipal Library",
    "ashurbanipal's library": "Ashurbanipal Library",
    "Ashurbanipal Library": "Ashurbanipal Library",
    "kuyunjik (nineveh)": "Ashurbanipal Library", # todo uncertain
    "kuyunjik": "Ashurbanipal Library",
    "nineveh (mod. kuyunjik)": "Ashurbanipal Library",
    "099 - miscellaneous": "Miscellaneous",
    "Library N 4": "Library N4",
    "Library N 4 (?)": "Library N4",
    "N4": "Library N4",
    "Library N 5": "Library N5",
    "Library N 6": "Library N6",
    "Library of Iqīša": "Library of Iqīša",
    "Iqiša": "Library of Iqīša",
    "Iqisa": "Library of Iqīša",
    "Colophon:  tablet of Iqisha": "Library of Iqīša",
    "Colophon: tablet of Iqisha": "Library of Iqīša",
    "Resh temple library": "Resh Temple Library",
    "bit res archive": "Resh Temple Library",
    "Bit Res archive; gift of slave to temple": "Resh Temple Library",
    "bit res archive; portion of storehouse in temple": "Resh Temple Library",
    "bit res archive; record of court hearing concerning slave": "Resh Temple Library",
    "bit res archive; woman is party to transaction": "Resh Temple Library",
    "U 18, Library of Šamaš-iddin": "Library of Šamaš-iddin",

    # Generic ORACC list classifications
    "01 (The Wine Lists)": "Wine Lists",
    "08 (Wine List fragments)": "Wine Lists",
    "07 (The Horse Lists)": "Horse Lists",

    # Things that should explicitly be UNCERTAIN (mostly SAA chapter descriptions or unassignables)
    "099 - Miscellaneous": "Uncertain",
    "Ch. 11 (Unassigned)": "Uncertain",
    "Ch. 9 (Varia and Unassigned)": "Uncertain",
    "Ch. 9 (Varia)": "Uncertain",
    "Ch. 6 (Varia)": "Uncertain",
    "Ch. 11 (Varia and Unassigned)": "Uncertain",
    "Ch. 22 (Babylonian reports - unassigned)": "Uncertain",
    "Ch. 13 (Private Archives)": "Private Archives (Unassigned)",
    "Private Archives": "Private Archives (Unassigned)",
    "Ch. 6 (Letters from Northern Babylonia)": "Uncertain",
    "Ch. 9 (Assyrian reports - unassigned)": "Uncertain",
    "Ch. 7 (Letters from Central and Southern Babylonia)": "Uncertain",
    "Ch. 8 (Deportees and Displaced Persons)": "Uncertain",
    "Ch. 6 (Letters from Babylonia)": "Uncertain",
    "Ch. 10 (Varia)": "Uncertain",
    "Ch. 12 (Queries - Unclassifiable (Reign of Esarhaddon))": "Uncertain",
    "Ch. 21 (Babylonian reports - varia)": "Uncertain",
    "Ch. 14 (Varia)": "Uncertain",
    "Ch. 3 (Letters from Babylon)": "Uncertain",
    "Ch. 12 (Letters of Unknown Authorship)": "Uncertain",
    "Ch. 7 (Miscellaneous Letters)": "Uncertain",
    "Ch. 7 (Letters from Gambulu)": "Uncertain",
    "Ch. 10 (Varia and Unassigned)": "Uncertain",
    "25 (Unassignable Texts  (Loans and Debt-Notes))": "Uncertain",
    "24 (Unassignable Texts  (Sales of People))": "Uncertain",
    "22 (Unassignable Texts  (Real Estate Sales))": "Uncertain",
    "23 (Unassignable Texts  (Divisions of Property and Donations))": "Uncertain",
    "26 (Unassignable Texts  (Judicial Documents))": "Uncertain",
    "27 (Unassignable Texts  (Letters))": "Uncertain",
    "28 (Unassignable Texts  (Miscellanea and Fragments))": "Uncertain",
    "Unknown": "Uncertain",
    "Sippar, unassigned": "Uncertain",
    "Kutha, unassigned": "Uncertain",
    "Babylon, unassigned": "Uncertain",

    # CTN3 sub-groups — tablets from Fort Shalmaneser classified by material/type
    "02 (The škintu group)": "Uncertain (SAA Chapter)",
    "03 (The encrusted group)": "Uncertain (SAA Chapter)",
    "04 (Miscellaneous texts)": "Uncertain (SAA Chapter)",
    "05 (Babylonian dockets)": "Uncertain (SAA Chapter)",

    # Eponym list / chronicle — not an archive per se
    "1 (Assyrian Eponym List)": "Uncertain",
    "2 (Assyrian Eponym Chronicle)": "Uncertain",

    # Temple of Nabû explicit reference (cmawro-sources)
    "Temple of Nabû": "Nabu Temple Archive",

    # Borsippa-based attribution by prosopography
    "Uruk based on prosopography": "Uncertain",

    # Scholarly library text title (not an archive)
    "Burning the Witches and Sending Them to the Netherworld: The Library Version": "Ashurbanipal Library",
}

def _normalize_quotes(s):
    """Normalize all Unicode apostrophe/quote variants to ASCII apostrophe.
    ORACC data uses multiple forms: U+2019 RIGHT SINGLE QUOTATION MARK,
    U+02BC MODIFIER LETTER APOSTROPHE, U+02BB MODIFIER LETTER TURNED COMMA,
    U+2018 LEFT SINGLE QUOTATION MARK.
    """
    return (
        s.replace('\u2019', "'")
        .replace('\u02bc', "'")
        .replace('\u02bb', "'")
        .replace('\u2018', "'")
    )


def clean_archive(raw):
    """Convert a raw ORACC archive string into a normalized archive name."""
    if not isinstance(raw, str):
        return ""

    # Normalize all Unicode apostrophe/quote variants to ASCII apostrophe
    # before doing any lookup. ORACC JSON values use several different forms.
    raw_s = _normalize_quotes(raw.strip())
    mapping = _get_archive_mapping()

    norm = mapping.get(raw_s)
    if norm:
        return norm

    raw_lower = raw_s.lower()
    norm = mapping.get(raw_lower)
    if norm:
        return norm

    # Catch all lengthy publication credits
    if len(raw_s) > 100:
        if 'Tempelgoldschmiede' in raw_s:
            return "Archive N33"
        if 'Wohnquartiere in der Weststadt' in raw_s:
            return "Weststadt Private Archives (Assur)"
        if 'Alltagstexte aus neuassyrischen Archiven' in raw_s:
            return "Assur (Unassigned)"
        return "Uncertain (Modern Collection)"

    # Colophons
    if 'ashurbanipal library colophon' in raw_lower:
        return "Ashurbanipal Library"

    # M/N string fallbacks
    if 'texte aus n ' in raw_lower or 'text aus n ' in raw_lower:
        parts = raw_lower.split('n ')
        if len(parts) > 1:
            num = parts[-1].rstrip(')')
            return f"Archive N{num}"

    # SAA chapters as uncertain
    if raw_s.startswith('Ch. '):
        return "Uncertain (SAA Chapter)"

    # Excavation seasons (e.g. "season 27") — not an archive
    import re as _re
    if _re.match(r'^season \d+$', raw_lower):
        return "Uncertain"

    # Excavation site location strings (Kasr, Kuyunjik, etc.) — not an archive
    if 'kasr' in raw_lower or 'kuyunjik' in raw_lower or 'homera' in raw_lower:
        return "Uncertain"

    # Modern provenance notes (acquired, purchased, registered, probably ...)
    if raw_lower.startswith(('acquired by', 'purchased', 'registered as', 'probably ', 'from miss')):
        return "Uncertain"

    # Specific collections
    if 'museum' in raw_lower or 'library, ' in raw_lower or 'collection' in raw_lower or 'institut de france' in raw_lower or 'bm ' in raw_lower or 'yale' in raw_lower:
        return "Uncertain (Modern Collection)"

    # Rooms in Northwest Palace without clear archive names
    if 'northwest palace, room' in raw_lower or 'northwest palace, zt' in raw_lower:
        return "Uncertain (North-West Palace Room)"

    # Unmatched but has something
    if raw_s:
        return ""
        
    return ""
