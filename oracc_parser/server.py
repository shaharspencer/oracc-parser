"""
Local HTTP API for browsing parsed ORACC cuneiform text data.

Designed to guide newcomers through the data step by step:

  1.  GET /               → Welcome page with "what to do next"
  2.  GET /projects       → Browse all 221 ORACC projects
  3.  POST /projects/{id}/parse  → Parse a project (downloads if needed)
  4.  GET /projects/{id}/texts   → List all parsed tablets
  5.  GET /projects/{id}/texts/{text}  → View one tablet in detail
  6.  GET /reference/...  → Browse provenance, periods, signs

Run with:
    python scripts/start_server.py

Then open http://localhost:8000/docs for the interactive Swagger UI.

Requires: pip install oracc-parser[server]
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from oracc_parser.models.config import RunConfig
from oracc_parser.pipeline import (
    get_full_flat_table,
    get_metadata_table,
    get_transliterations,
    get_normalizations,
    get_lemmatizations,
    get_unicode_texts,
    get_translations,
    parse_project,
    reference_data,
)

app = FastAPI(
    title="oracc-parser",
    description=(
        "Local API for browsing ORACC cuneiform text data.\n\n"
        "**Getting started:**\n"
        "1. Browse available projects at `/projects`\n"
        "2. Parse one with `POST /projects/{id}/parse`\n"
        "3. Explore the texts at `/projects/{id}/texts`\n"
        "4. View a single tablet at `/projects/{id}/texts/{text_id}`\n\n"
        "No external account or API key needed — everything runs locally."
    ),
    version="0.1.0",
)

# In-memory store for parsed records (per project)
_store: dict[str, list] = {}


# ---------------------------------------------------------------------------
# Landing page
# ---------------------------------------------------------------------------


@app.get("/", tags=["Start here"], summary="Welcome — what to do next")
def landing():
    """
    Returns a getting-started guide and the current state of the server.
    """
    return {
        "message": "Welcome to oracc-parser! Here's how to get started:",
        "steps": [
            "1. GET /projects — see all 221+ ORACC projects",
            "2. POST /projects/saao/saa01/parse?limit=5 — parse a small project",
            "3. GET /projects/saao/saa01/texts — browse the parsed tablets",
            "4. GET /projects/saao/saa01/texts/P313511 — view one tablet",
        ],
        "tip": "Open /docs for the interactive Swagger UI where you can try each endpoint",
        "parsed_projects": list(_store.keys()),
        "total_tablets": sum(len(v) for v in _store.values()),
    }


# ---------------------------------------------------------------------------
# Projects — browse and parse
# ---------------------------------------------------------------------------


@app.get("/projects", tags=["Projects"], summary="Browse all ORACC projects")
def list_projects(
    search: str | None = Query(None, description="Filter by name (case-insensitive)"),
    language: str | None = Query(None, description="Filter by language, e.g. 'Akkadian'"),
):
    """
    Lists all 221+ ORACC projects with their metadata.
    Use `search` to filter by name, or `language` to filter by language.
    """
    df = reference_data.get_projects_metadata().fillna("")

    if search:
        mask = df.apply(
            lambda row: search.lower() in " ".join(row.astype(str)).lower(),
            axis=1,
        )
        df = df[mask]

    if language:
        lang_cols = [c for c in df.columns if "lang" in c.lower()]
        if lang_cols:
            mask = df[lang_cols[0]].str.contains(language, case=False, na=False)
            df = df[mask]

    projects = df.to_dict(orient="records")
    return {
        "count": len(projects),
        "projects": projects,
        "tip": "Pick a project and parse it: POST /projects/{project_path}/parse",
    }


@app.post(
    "/projects/{project_path:path}/parse",
    tags=["Projects"],
    summary="Parse a project",
)
def parse(
    project_path: str,
    limit: int | None = Query(None, description="Only parse first N texts (good for testing)"),
    drop_missing: bool = Query(False, description="Drop broken/missing signs"),
    drop_damaged: bool = Query(False, description="Drop damaged signs"),
):
    """
    Downloads (if needed) and parses a project. Results are stored in memory
    so you can browse them with the other endpoints.

    **Try it:** `POST /projects/saao/saa01/parse?limit=5`
    """
    config = RunConfig(
        drop_missing=drop_missing,
        drop_damaged=drop_damaged,
        limit=limit,
    )
    records = parse_project(project_path, config=config)
    if not records:
        raise HTTPException(404, f"No texts found for project '{project_path}'")

    _store[project_path] = records

    return {
        "project": project_path,
        "tablets_parsed": len(records),
        "next_steps": [
            f"GET /projects/{project_path}/texts — browse all tablets",
            f"GET /projects/{project_path}/metadata — see provenance, period, etc.",
            f"GET /projects/{project_path}/export — download as flat JSON",
        ],
    }


# ---------------------------------------------------------------------------
# Texts — browse parsed tablets
# ---------------------------------------------------------------------------


def _get_records(project: str):
    if project not in _store:
        raise HTTPException(
            400,
            detail={
                "error": f"Project '{project}' not parsed yet.",
                "fix": f"POST /projects/{project}/parse first.",
            },
        )
    return _store[project]


@app.get(
    "/projects/{project_path:path}/texts",
    tags=["Texts"],
    summary="List all parsed tablets in a project",
)
def list_texts(
    project_path: str,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Tablets per page"),
):
    """
    Returns a paginated list of tablets with a short preview of each one.
    """
    records = _get_records(project_path)

    start = (page - 1) * per_page
    end = start + per_page
    page_records = records[start:end]

    texts = []
    for r in page_records:
        texts.append({
            "id": r.metadata.identifier,
            "text_id": r.metadata.text_id,
            "provenance": r.metadata.geographical_information.city.city_name
            if r.metadata.geographical_information
            else "",
            "period": r.metadata.chronological_information.tablet_period.period_name
            if r.metadata.chronological_information
            and r.metadata.chronological_information.tablet_period
            else "",
            "transliteration_preview": (
                r.content.transliterated_str_representation.text[:80] + "..."
                if r.content.transliterated_str_representation
                and r.content.transliterated_str_representation.text
                else ""
            ),
            "detail_url": f"/projects/{project_path}/texts/{r.metadata.text_id}",
        })

    return {
        "project": project_path,
        "total": len(records),
        "page": page,
        "per_page": per_page,
        "texts": texts,
    }


@app.get(
    "/projects/{project_path:path}/texts/{text_id}",
    tags=["Texts"],
    summary="View a single tablet in detail",
)
def get_text(project_path: str, text_id: str):
    """
    Returns all available representations of a single tablet:
    transliteration, normalization, lemmatization, Unicode, and translation.
    """
    records = _get_records(project_path)

    # Find the matching record
    record = None
    for r in records:
        if r.metadata.text_id == text_id or r.metadata.identifier == text_id:
            record = r
            break

    if not record:
        raise HTTPException(404, f"Text '{text_id}' not found in project '{project_path}'")

    result = {
        "id": record.metadata.identifier,
        "text_id": record.metadata.text_id,
        "project": project_path,
    }

    # Metadata
    meta = record.metadata
    result["metadata"] = {
        "genre": meta.genre,
        "provenance": meta.geographical_information.city.city_name
        if meta.geographical_information
        else "",
        "pleiades_id": meta.geographical_information.city.city_plaides_id
        if meta.geographical_information
        else "",
    }

    if meta.chronological_information:
        chrono = meta.chronological_information
        result["metadata"]["period"] = (
            chrono.tablet_period.period_name if chrono.tablet_period else ""
        )
        result["metadata"]["start_year"] = chrono.start_year
        result["metadata"]["end_year"] = chrono.end_year

    # Text representations
    c = record.content
    result["transliteration"] = (
        c.transliterated_str_representation.text
        if c.transliterated_str_representation
        else ""
    )
    result["normalization"] = (
        c.normalized_str_representation.text
        if c.normalized_str_representation
        else ""
    )
    result["lemmatization"] = (
        c.lemmatized_str_representation.text
        if c.lemmatized_str_representation
        else ""
    )
    result["unicode"] = (
        c.unicode_str_representation.text
        if c.unicode_str_representation
        else ""
    )
    result["translation"] = c.english_translation or ""

    # Stats
    if c.transliterated_str_representation:
        result["stats"] = {
            "total_tokens": c.transliterated_str_representation.total_tokens,
            "tokens_without_broken": c.transliterated_str_representation.tokens_without_broken,
            "total_words": len(c.words),
        }

    return result


# ---------------------------------------------------------------------------
# Bulk data endpoints
# ---------------------------------------------------------------------------


@app.get(
    "/projects/{project_path:path}/metadata",
    tags=["Bulk data"],
    summary="Flat metadata table for all tablets",
)
def project_metadata(project_path: str):
    """All metadata (provenance, period, years) as a flat JSON array."""
    records = _get_records(project_path)
    df = get_metadata_table(records)
    return JSONResponse(df.to_dict(orient="records"))


@app.get(
    "/projects/{project_path:path}/transliterations",
    tags=["Bulk data"],
    summary="All transliterations",
)
def project_transliterations(project_path: str):
    records = _get_records(project_path)
    df = get_transliterations(records)
    return JSONResponse(df.to_dict(orient="records"))


@app.get(
    "/projects/{project_path:path}/normalizations",
    tags=["Bulk data"],
    summary="All normalizations",
)
def project_normalizations(project_path: str):
    records = _get_records(project_path)
    df = get_normalizations(records)
    return JSONResponse(df.to_dict(orient="records"))


@app.get(
    "/projects/{project_path:path}/lemmatizations",
    tags=["Bulk data"],
    summary="All lemmatizations",
)
def project_lemmatizations(project_path: str):
    records = _get_records(project_path)
    df = get_lemmatizations(records)
    return JSONResponse(df.to_dict(orient="records"))


@app.get(
    "/projects/{project_path:path}/unicode",
    tags=["Bulk data"],
    summary="All Unicode cuneiform",
)
def project_unicode(project_path: str):
    records = _get_records(project_path)
    df = get_unicode_texts(records)
    return JSONResponse(df.to_dict(orient="records"))


@app.get(
    "/projects/{project_path:path}/translations",
    tags=["Bulk data"],
    summary="All English translations",
)
def project_translations(project_path: str):
    records = _get_records(project_path)
    df = get_translations(records)
    return JSONResponse(df.to_dict(orient="records"))


@app.get(
    "/projects/{project_path:path}/export",
    tags=["Bulk data"],
    summary="Full flat dataset (all fields)",
)
def project_export(project_path: str):
    """Everything in one flat JSON array — ideal for downloading."""
    records = _get_records(project_path)
    df = get_full_flat_table(records)
    return JSONResponse(df.to_dict(orient="records"))


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------


@app.get(
    "/reference/provenance",
    tags=["Reference"],
    summary="Provenance lookup table",
)
def ref_provenance():
    """Bundled city provenance data with Pleiades IDs."""
    df = reference_data.get_provenance()
    return JSONResponse(df.fillna("").to_dict(orient="records"))


@app.get(
    "/reference/periods",
    tags=["Reference"],
    summary="Period → year mapping",
)
def ref_periods():
    """Historical periods mapped to approximate start/end years."""
    df = reference_data.get_period_mapping()
    return JSONResponse(df.fillna("").to_dict(orient="records"))


@app.get(
    "/reference/signs",
    tags=["Reference"],
    summary="Cuneiform sign readings",
)
def ref_signs(
    search: str | None = Query(None, description="Filter by sign name"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
):
    """Cuneiform sign readings table (8900+ entries)."""
    df = reference_data.get_sign_list()
    if search:
        mask = df.apply(
            lambda row: search.lower() in " ".join(row.astype(str)).lower(),
            axis=1,
        )
        df = df[mask]
    return JSONResponse(df.fillna("").head(limit).to_dict(orient="records"))


@app.get(
    "/reference/pos",
    tags=["Reference"],
    summary="Part-of-speech tags",
)
def ref_pos():
    """POS tag definitions used in ORACC data."""
    df = reference_data.get_pos_tags()
    return JSONResponse(df.fillna("").to_dict(orient="records"))


@app.get(
    "/reference/languages",
    tags=["Reference"],
    summary="Language codes",
)
def ref_languages():
    """Language codes and names used in ORACC."""
    df = reference_data.get_languages()
    return JSONResponse(df.fillna("").to_dict(orient="records"))


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------


def run_server(host: str = "127.0.0.1", port: int = 8000):
    """Start the local API server."""
    import uvicorn

    print()
    print("  ╔═══════════════════════════════════════════════════╗")
    print("  ║  oracc-parser API                                ║")
    print(f"  ║  Running at   http://{host}:{port}            ║")
    print(f"  ║  Swagger docs http://{host}:{port}/docs       ║")
    print("  ║                                                   ║")
    print("  ║  Try: GET /projects to browse available projects  ║")
    print("  ╚═══════════════════════════════════════════════════╝")
    print()
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
