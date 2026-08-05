"""
Craft helpers to map arbitrary source data into Epigraf RAM rows.

Mirrors craft.R from the R package.
"""

import pandas as pd

from epygraf import base, ram


def _merge_mapping(values, default):
    """Merge user mapping into defaults (user keys override defaults)."""
    merged = dict(default)
    merged.update(values or {})
    return merged


def _ensure_column(df: pd.DataFrame, colname: str, default_value):
    """Add a source column with a default value if it is missing."""
    if colname not in df.columns:
        df[colname] = default_value
    return df


def _select_and_rename(df: pd.DataFrame, cols: dict) -> pd.DataFrame:
    """Select source columns by mapping values and rename to mapping keys."""
    source_cols = list(cols.values())
    missing = [c for c in source_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing source columns in mapping: {missing}")
    rows = df[source_cols].copy()
    rows.columns = list(cols.keys())
    return rows


def _apply_fill(rows: pd.DataFrame, fill: dict) -> pd.DataFrame:
    if rows.empty or not fill:
        return rows
    rows = rows.copy()
    for name, value in fill.items():
        rows[name] = value
    return rows


def _set_fields(rows: pd.DataFrame, fields_cols) -> pd.DataFrame:
    rows = rows.copy()
    if not rows.empty:
        rows["_fields"] = ",".join(list(fields_cols) + ["type", "norm_iri"])
    return rows


def _ensure_required(df: pd.DataFrame, required_col: str, msg: str):
    if required_col not in df.columns:
        raise ValueError(msg)


def craft_properties(df: pd.DataFrame, cols=None, fill=None) -> pd.DataFrame:
    """
    Create RAM rows for property data.

    Mirrors craft_properties() from craft.R.
    """
    cols = _merge_mapping(cols or {}, {"fragment": "property.id", "type": "property.type"})
    fill = fill or {}

    out = df.copy()
    rows = out.copy()
    rows = _ensure_column(rows, cols["fragment"], "default")
    rows = _ensure_column(rows, cols["type"], "default")

    rows = _select_and_rename(rows, cols)
    rows = _apply_fill(rows, fill)

    rows["id"] = [base.create_iri("properties", t, f) for t, f in zip(rows["type"], rows["fragment"])]
    rows = rows.drop(columns=["type", "fragment"])

    fields_cols = list(rows.columns)
    out[".property"] = rows["id"]
    rows[".property"] = rows["id"]

    rows = rows.drop_duplicates()
    rows = _set_fields(rows, fields_cols)

    return ram.add(out, rows)


def craft_projects(df: pd.DataFrame, cols=None, fill=None) -> pd.DataFrame:
    """
    Create RAM rows for project data.

    Mirrors craft_projects() from craft.R.
    """
    cols = _merge_mapping(cols or {}, {"type": "project.type", "fragment": "project.fragment"})
    fill = fill or {}

    out = df.copy()
    rows = out.copy()
    rows = _ensure_column(rows, cols["fragment"], "default")
    rows = _ensure_column(rows, cols["type"], "default")

    rows = _select_and_rename(rows, cols)
    rows = _apply_fill(rows, fill)

    rows["id"] = [base.create_iri("projects", t, f) for t, f in zip(rows["type"], rows["fragment"])]
    rows = rows.drop(columns=["type", "fragment"])

    fields_cols = list(rows.columns)
    out[".project"] = rows["id"]
    rows[".project"] = rows["id"]

    rows = rows.drop_duplicates()
    rows = _set_fields(rows, fields_cols)

    return ram.add(out, rows)


def craft_articles(df: pd.DataFrame, cols=None, fill=None) -> pd.DataFrame:
    """
    Create RAM rows for article data.

    Mirrors craft_articles() from craft.R.
    """
    _ensure_required(df, ".project", "Please, craft a project first")

    cols = _merge_mapping(
        cols or {},
        {"fragment": "article.fragment", "type": "article.type", "projects_id": ".project"},
    )
    fill = fill or {}

    out = df.copy()
    rows = out.copy()
    rows = _ensure_column(rows, cols["fragment"], "default")
    rows = _ensure_column(rows, cols["type"], "default")

    rows = _select_and_rename(rows, cols)
    rows = _apply_fill(rows, fill)

    rows["id"] = [base.create_iri("articles", t, f) for t, f in zip(rows["type"], rows["fragment"])]
    rows = rows.drop(columns=["type", "fragment"])

    fields_cols = list(rows.columns)
    out[".article"] = rows["id"]
    rows[".article"] = rows["id"]
    rows[".project"] = out[".project"]

    rows = rows.drop_duplicates()
    rows = _set_fields(rows, fields_cols)

    return ram.add(out, rows)


def craft_sections(df: pd.DataFrame, cols=None, fill=None) -> pd.DataFrame:
    """
    Create RAM rows for section data.

    Mirrors craft_sections() from craft.R.
    """
    _ensure_required(df, ".project", "Please, craft a project first")
    _ensure_required(df, ".article", "Please, craft an article first")

    cols = _merge_mapping(
        cols or {},
        {
            "fragment": "section.fragment",
            "type": "section.type",
            "articles_id": ".article",
            "projects_id": ".project",
        },
    )
    fill = fill or {}

    out = df.copy()
    rows = out.copy()
    rows = _ensure_column(rows, cols["fragment"], "default")
    rows = _ensure_column(rows, cols["type"], "default")

    rows = _select_and_rename(rows, cols)
    rows = _apply_fill(rows, fill)

    parents = base.iri_parent(rows["articles_id"])  # list like ["foo~", ...]
    fragments = rows["fragment"].astype(str).tolist()
    iri_fragments = [p + f for p, f in zip(parents, fragments)]

    rows["id"] = [base.create_iri("sections", t, frag) for t, frag in zip(rows["type"], iri_fragments)]
    rows = rows.drop(columns=["type", "fragment"])

    fields_cols = list(rows.columns)
    out[".section"] = rows["id"]
    rows[".section"] = rows["id"]
    rows[".project"] = out[".project"]
    rows[".article"] = out[".article"]

    rows = rows.drop_duplicates()
    rows = _set_fields(rows, fields_cols)

    return ram.add(out, rows)


def craft_items(df: pd.DataFrame, cols=None, fill=None) -> pd.DataFrame:
    """
    Create RAM rows for item data.

    Mirrors craft_items() from craft.R.
    """
    _ensure_required(df, ".project", "Please, map a project first")
    _ensure_required(df, ".article", "Please, map an article first")
    _ensure_required(df, ".section", "Please, map a section first")

    cols = _merge_mapping(
        cols or {},
        {
            "fragment": "item.fragment",
            "type": "item.type",
            "sections_id": ".section",
            "articles_id": ".article",
            "projects_id": ".project",
        },
    )
    fill = fill or {}

    out = df.copy()
    rows = out.copy()
    rows = _ensure_column(rows, cols["fragment"], "default")
    rows = _ensure_column(rows, cols["type"], "default")

    rows = _select_and_rename(rows, cols)
    rows = _apply_fill(rows, fill)

    parents = base.iri_parent(rows["sections_id"])
    fragments = rows["fragment"].astype(str).tolist()
    iri_fragments = [p + f for p, f in zip(parents, fragments)]

    rows["id"] = [base.create_iri("items", t, frag) for t, frag in zip(rows["type"], iri_fragments)]
    rows = rows.drop(columns=["type", "fragment"])

    fields_cols = list(rows.columns)
    out[".item"] = rows["id"]
    rows[".item"] = rows["id"]
    rows[".project"] = out[".project"]
    rows[".article"] = out[".article"]
    rows[".section"] = out[".section"]

    rows = rows.drop_duplicates()
    rows = _set_fields(rows, fields_cols)

    return ram.add(out, rows)


def df_to_ram(
    df: pd.DataFrame,
    project_cols=None,
    project_fill=None,
    article_cols=None,
    article_fill=None,
    section_cols=None,
    section_fill=None,
    property_cols=None,
    property_fill=None,
    item_cols=None,
    item_fill=None,
    compile: bool = False,
):
    """
    Map a source DataFrame to RAM rows.

    Calls craft methods for projects, articles, sections, items and properties.
    Mirrors df_to_ram() from craft.R.
    """
    project_cols = project_cols or {}
    project_fill = project_fill or {}
    article_cols = article_cols or {}
    article_fill = article_fill or {}
    section_cols = section_cols or {}
    section_fill = section_fill or {}
    property_cols = property_cols or {}
    property_fill = property_fill or {}
    item_cols = item_cols or {}
    item_fill = item_fill or {}

    out = df.copy()

    if property_cols or property_fill:
        out = craft_properties(out, property_cols, property_fill)

    if project_cols or project_fill:
        out = craft_projects(out, project_cols, project_fill)

    if article_cols or article_fill:
        out = craft_articles(out, article_cols, article_fill)

    if section_cols or section_fill:
        out = craft_sections(out, section_cols, section_fill)

    if item_cols or item_fill:
        out = craft_items(out, item_cols, item_fill)

    if compile:
        return ram.compile(out)

    return out


# Short aliases without craft_/df_ prefixes
projects = craft_projects
articles = craft_articles
sections = craft_sections
items = craft_items
properties = craft_properties
to_ram = df_to_ram

