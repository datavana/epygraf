"""
Distill functions for Epigraf RAM data frames.

Mirrors distill.R from the R package.
A "RAM data frame" is the long-format DataFrame produced by db.fetch() or
api.fetch(), containing rows for articles, sections, items, properties,
links and footnotes identified by the ``table`` column.
"""

import warnings
import xml.etree.ElementTree as ET

import pandas as pd

from epygraf import base, utils
from epygraf import tree as _tree


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _unescape_cols(df: pd.DataFrame, cols) -> pd.DataFrame:
    """Replace common HTML entities in selected string columns."""
    for col in cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace("&amp;", "&", regex=False)
            df[col] = df[col].str.replace("&x2f;", "&", regex=False)
    return df


def _str_as_nullable(series: pd.Series) -> pd.Series:
    """Convert a Series to str, turning 'nan'/'None' back to pd.NA."""
    series = series.astype(str)
    series[series.isin({"nan", "None", "<NA>"})] = pd.NA
    return series


# ---------------------------------------------------------------------------
# XML helpers  (mirrors distill.R)
# ---------------------------------------------------------------------------

def extract_segment(xml_str: str, tagid: str) -> str:
    """
    Extract text from XML elements that carry a given ``id`` attribute.

    Mirrors extract_segment() from distill.R.

    :param xml_str: XML string (item content)
    :param tagid: The id attribute value to search for
    :return: Semicolon-joined text content of matching elements
    """
    if not xml_str or not tagid:
        return ""
    try:
        root = ET.fromstring(f"<root>{xml_str}</root>")
        segments = root.findall(f'.//*[@id="{tagid}"]')
        texts = []
        for el in segments:
            texts.extend(t.strip() for t in el.itertext() if t.strip())
        return ";".join(texts)
    except ET.ParseError:
        return ""


def extract_untagged(xml_str: str) -> str:
    """
    Extract text that is not contained inside any child element.

    Mirrors extract_untagged() from distill.R.

    :param xml_str: XML string
    :return: Direct text of the root element only
    """
    if not xml_str:
        return ""
    try:
        safe = xml_str.replace("&", "&#038;")
        root = ET.fromstring(f"<root>{safe}</root>")
        parts = [root.text or ""]
        for child in root:
            parts.append(child.tail or "")
        return " ".join(p.strip() for p in parts if p.strip())
    except ET.ParseError:
        return ""


# ---------------------------------------------------------------------------
# Distill functions  (mirrors distill.R)
# ---------------------------------------------------------------------------

def articles(df: pd.DataFrame, cols=None, section_type=None,
             section_cols=None, item_type=None, item_cols=None,
             property_cols=None) -> pd.DataFrame:
    """
    Get articles with optionally joined section, item, and property data.

    Mirrors distill_articles() from distill.R.

    :param df: A RAM DataFrame (from db.fetch or api.fetch)
    :param cols: Article columns to include
    :param section_type: Section types to join. ``None`` means all sections.
    :param section_cols: Columns to join from sections (prefixed ``sections.<col>``)
    :param item_type: Item types to join
    :param item_cols: Columns to join from items (prefixed ``items.<col>``)
    :param property_cols: Columns to join from properties (prefixed ``properties.<col>``)
    :return: DataFrame with articles
    """
    if cols is None:
        cols = []
    if section_cols is None:
        section_cols = []
    if item_cols is None:
        item_cols = []
    if property_cols is None:
        property_cols = []

    base_cols = list(dict.fromkeys(["id", "type", "norm_iri"] + list(cols)))
    cases = df[df["table"] == "articles"].copy()
    cases = cases[[c for c in base_cols if c in cases.columns]]
    cases = cases.drop_duplicates()

    extract_cols = (
        [f"sections.{c}" for c in section_cols]
        + [f"items.{c}" for c in item_cols]
        + [f"properties.{c}" for c in property_cols]
    )

    if extract_cols:
        its = base.extract_long(df, "items", item_type)  # prefixed "items."

        if property_cols:
            props = base.extract_long(df, "properties")
            if not props.empty and not its.empty and "items.property" in its.columns:
                its = its.merge(
                    props, left_on="items.property", right_on="properties.id", how="left"
                )

        if section_cols:
            secs = base.extract_long(df, "sections", section_type)
            if (not secs.empty and not its.empty
                    and "sections.id" in secs.columns
                    and "items.sections_id" in its.columns):
                its = secs.merge(
                    its, left_on="sections.id", right_on="items.sections_id", how="inner"
                )

        keep = [c for c in ["items.articles_id"] + extract_cols if c in its.columns]
        its = its[keep].copy()
        its = _unescape_cols(its, extract_cols)

        cases = cases.merge(its, left_on="id", right_on="items.articles_id", how="outer")
        ordered = [c for c in list(cols) + extract_cols + ["id", "type", "norm_iri"]
                   if c in cases.columns]
        cases = cases[list(dict.fromkeys(ordered))]

    cases = utils.move_cols_to_end(cases, ["id", "type", "norm_iri"])
    return cases.reset_index(drop=True)


def items(df: pd.DataFrame, type=None, cols=None,
          property_cols=None, article_cols=None) -> pd.DataFrame:
    """
    Get items with optionally joined property and article data.

    Mirrors distill_items() from distill.R.

    :param df: A RAM DataFrame
    :param type: Item types to filter. ``None`` means all types.
    :param cols: Columns returned from items
    :param property_cols: Property columns to join (prefixed ``properties.<col>``)
    :param article_cols: Article columns to join (prefixed ``articles.<col>``)
    :return: DataFrame with items
    """
    if cols is None:
        cols = []
    if property_cols is None:
        property_cols = []
    if article_cols is None:
        article_cols = []

    its = base.extract_long(df, "items", type, prefix=False)
    if its.empty:
        return its
    if "id" in its.columns:
        its["id"] = its["id"].astype(str)

    extract_cols = list(cols)

    if property_cols and "property" in its.columns:
        props = base.extract_long(df, "properties")
        if not props.empty and "properties.id" in props.columns:
            its["property"] = its["property"].astype(str)
            props["properties.id"] = props["properties.id"].astype(str)
            its = its.merge(props, left_on="property", right_on="properties.id", how="left")
            extract_cols += [f"properties.{c}" for c in property_cols]

    if article_cols:
        arts = base.extract_long(df, "articles")
        if not arts.empty and "articles_id" in its.columns and "articles.id" in arts.columns:
            its["articles_id"] = its["articles_id"].astype(str)
            arts["articles.id"] = arts["articles.id"].astype(str)
            its = its.merge(arts, left_on="articles_id", right_on="articles.id", how="left")
            extract_cols += [f"articles.{c}" for c in article_cols]

    its = utils.add_missing_columns(its, "norm_iri")
    final_cols = list(dict.fromkeys(
        extract_cols + ["id", "type", "norm_iri", "articles_id", "sections_id"]
    ))
    final_cols = [c for c in final_cols if c in its.columns]
    its = its[final_cols].copy()
    its = _unescape_cols(its, extract_cols)
    return its.reset_index(drop=True)


def properties(df: pd.DataFrame, type=None, cols=None,
               annos: bool = False, levelup=None) -> pd.DataFrame:
    """
    Get the property tree, optionally with annotations.

    Mirrors distill_properties() from distill.R.

    :param df: A RAM DataFrame
    :param type: Property type to filter. ``None`` means all types.
    :param cols: Additional property columns to include
    :param annos: Whether to attach annotations (items and links)
    :param levelup: Simplify the tree by replacing paths with the ancestor
                    at the given level.
    :return: DataFrame with the property tree and a ``path`` column
    """
    if cols is None:
        cols = []

    props = base.extract_long(df, "properties", type, prefix=False)
    if props.empty:
        warnings.warn(f"No property data with type '{type}' found.", stacklevel=2)
        return props

    props = utils.add_missing_columns(props, ["parent_id", "articles_id"])
    if "id" in props.columns:
        props["id"] = _str_as_nullable(props["id"])
    if "parent_id" in props.columns:
        props["parent_id"] = _str_as_nullable(props["parent_id"])

    base_cols = ["lemma", "type", "norm_iri", "level", "lft", "rght", "id", "parent_id"]
    keep_cols = list(dict.fromkeys(base_cols + list(cols)))
    keep_cols = [c for c in keep_cols if c in props.columns]
    props = props[keep_cols].copy()

    if "lft" in props.columns:
        props = props.sort_values("lft")

    if {"id", "parent_id", "lemma"}.issubset(props.columns):
        props = _tree.add_path(props, "id", "parent_id", "lemma")

    props = utils.drop_empty_columns(props)

    select_cols = list(dict.fromkeys(
        ["tree_path", "id", "parent_id"] + list(cols) + ["type", "norm_iri"]
    ))
    select_cols = [c for c in select_cols if c in props.columns]
    props = props[select_cols]

    if not props.empty and props.columns[0] == "tree_path":
        props = props.rename(columns={"tree_path": "path"})

    if annos:
        # --- items ---
        anno_items = items(df, None, cols=["property"])
        if not anno_items.empty:
            anno_items["items_id"] = anno_items["id"]
            anno_cols = [c for c in ["property", "articles_id", "sections_id", "items_id"]
                         if c in anno_items.columns]
            anno_items = anno_items[anno_cols].dropna()
            if not anno_items.empty and "id" in props.columns:
                anno_items = props.merge(anno_items, left_on="id", right_on="property", how="inner")
                anno_items = utils.drop_empty_columns(anno_items)
                if not anno_items.empty:
                    props = props[~props["id"].isin(anno_items["id"])]

        # --- links ---
        anno_links = links(df, properties_type=type, cols=["segment"], level=None)
        if not anno_links.empty and "to_id" in anno_links.columns and "id" in props.columns:
            anno_links = props.merge(anno_links, left_on="id", right_on="to_id", how="inner")
            anno_links = utils.drop_empty_columns(anno_links)
            if not anno_links.empty:
                props = props[~props["id"].isin(anno_links["id"])]

        frames = [f for f in [props,
                               anno_links if not anno_links.empty else None,
                               anno_items if not anno_items.empty else None] if f is not None]
        props = pd.concat(frames, ignore_index=True)

    if levelup is not None:
        props = utils.add_missing_columns(props, ["parent_id", "path"])
        if {"id", "parent_id", "path"}.issubset(props.columns):
            props = _tree.add_ancestor(props, "id", "parent_id", "path", level=levelup)

    return props.reset_index(drop=True)


def links(df: pd.DataFrame, items_type=None, properties_type=None,
          cols=None, article_cols=None, level=0) -> pd.DataFrame:
    """
    Get article annotations via links.

    Mirrors distill_links() from distill.R.

    :param df: A RAM DataFrame
    :param items_type: Item type of annotating items (``None`` means all)
    :param properties_type: Keep only links targeting this property type
    :param cols: Result columns, e.g. ``["path", "segment"]``
    :param article_cols: Article columns to join
    :param level: Aggregation level (0-based). ``None`` means the deepest level.
    :return: DataFrame with annotations
    """
    if cols is None:
        cols = ["path", "segment"]
    if article_cols is None:
        article_cols = []

    codes = properties(df, properties_type, cols=["parent_id", "level", "norm_iri"])
    if codes.empty:
        return pd.DataFrame()

    cases = articles(df, cols=list(article_cols))
    if "id" in cases.columns:
        cases["id"] = cases["id"].astype(str)
    cases = cases.drop(columns=[c for c in ["type", "norm_iri"] if c in cases.columns])

    codes = utils.add_missing_columns(codes, "parent_id")
    if "id" in codes.columns:
        codes["id"] = codes["id"].astype(str)

    ancestors = _tree.stack_ancestors(
        codes[["id", "parent_id"]].drop_duplicates(), "id", "parent_id", "anc_id"
    ).drop_duplicates()

    if level is None:
        codes_level = codes.copy()
        effective_level = int(codes["level"].max()) if "level" in codes.columns else 0
    else:
        effective_level = level
        codes_level = (codes[codes["level"] == level].copy()
                       if "level" in codes.columns else codes.copy())

    lnks = base.extract_long(df, "links", prefix=False)
    if lnks.empty:
        return pd.DataFrame()

    if "root_tab" in lnks.columns:
        lnks = lnks[lnks["root_tab"] == "articles"]
    if "from_tab" in lnks.columns:
        lnks = lnks[lnks["from_tab"] == "items"]
    if "to_tab" in lnks.columns:
        lnks = lnks[lnks["to_tab"] == "properties"]
    if lnks.empty:
        return pd.DataFrame()

    id_cols = ["root_id", "from_id", "from_tagid", "to_id"]
    for col in id_cols:
        if col in lnks.columns:
            lnks[col] = lnks[col].astype(str)

    link_cols = [c for c in id_cols if c in lnks.columns]
    codings = lnks[link_cols].drop_duplicates()
    codings = codings.merge(ancestors, left_on="to_id", right_on="id", how="left")

    path_col = "path" if "path" in codes_level.columns else None
    if path_col is None:
        return pd.DataFrame()

    codings = (
        codings
        .merge(
            codes_level[["id", path_col]].rename(columns={"id": "_cid"}),
            left_on="anc_id", right_on="_cid", how="inner",
        )
        .drop(columns=["_cid"])
    )
    codings = codings[link_cols + [path_col]].drop_duplicates()
    codings = codings.merge(cases, left_on="root_id", right_on="id", how="left")
    codings = codings.drop(columns=[c for c in ["id"] if c in codings.columns])

    # Split path into level_0, level_1, … columns
    if path_col in codings.columns:
        split = codings[path_col].str.split(r" / ", n=effective_level, expand=True)
        level_col_names = [f"level_{i}" for i in range(split.shape[1])]
        split.columns = level_col_names
        for col in level_col_names:
            split[col] = split[col].str.replace("&#47;", "/", regex=False)
            split[col] = split[col].str.replace("&x2f;", "&", regex=False)
        codings = pd.concat([codings.reset_index(drop=True), split], axis=1)

    # Extract text segments from items
    segments_src = base.extract_long(df, "items", items_type, prefix=False)
    if not segments_src.empty:
        segments_src["items_id"] = segments_src["id"]
        seg_cols = [c for c in ["items_id", "sections_id", "articles_id", "content", "norm_iri"]
                    if c in segments_src.columns]
        segs = segments_src[seg_cols].copy()
        for col in segs.columns:
            segs[col] = segs[col].astype(str)

        if "from_id" in codings.columns and "items_id" in segs.columns:
            segs = segs.merge(codings, left_on="items_id", right_on="from_id", how="inner")
            if {"from_tagid", "content"}.issubset(segs.columns):
                segs["item_iri"] = segs.get("norm_iri", pd.NA)
                segs["segment"] = segs.apply(
                    lambda row: extract_segment(
                        row.get("content", "") or "",
                        row.get("from_tagid", "") or "",
                    ),
                    axis=1,
                )
                seg_keep = [c for c in
                            ["items_id", "sections_id", "articles_id",
                             "from_tagid", "content", "item_iri", "segment"]
                            if c in segs.columns]
                segs = segs[seg_keep]

                join_on = [c for c in ["from_id", "from_tagid"] if c in codings.columns]
                if join_on:
                    codings = codings.merge(
                        segs,
                        left_on=join_on,
                        right_on=["items_id"] + join_on[1:],
                        how="left",
                    )
                    if "from_id" in codings.columns:
                        codings["items_id"] = codings["from_id"]

    final_cols = list(dict.fromkeys(
        list(article_cols) + ["articles_id", "sections_id", "items_id",
                               "from_tagid"] + list(cols) + ["to_id"]
    ))
    codings = utils.add_missing_columns(codings, "to_id")
    final_cols = [c for c in final_cols if c in codings.columns]
    return codings[final_cols].reset_index(drop=True)

