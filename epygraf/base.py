"""
Functions for Epigraf data handling.

"""

import re
import pandas as pd

__all__ = [
    "create_iri", "clean_irifragment", "is_iripath", "is_id", "is_prefixid",
    "is_irifragment", "iri_parent", "extract_long", "extract_wide",
    "wide_to_long", "drop_empty_columns",
]

TABLES = ("projects", "articles", "sections", "items", "properties",
          "links", "footnotes", "types", "users")

_TABLE_RE = "(" + "|".join(TABLES) + ")"
_TYPE_RE = "([a-z0-9_-]+)"
_FRAGMENT_RE = "([a-z0-9_~-]+)"
_NUMBER_RE = "([0-9]+)"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _as_str_series(value) -> tuple[pd.Series, bool]:
    """Coerce scalars / lists / arrays / Series to a string Series.

    :return: (series, was_scalar)
    """
    if isinstance(value, pd.Series):
        return value.astype("string"), False
    if isinstance(value, pd.Index):
        return pd.Series(value).astype("string"), False
    if value is None or isinstance(value, str) or not hasattr(value, "__iter__"):
        return pd.Series([value], dtype="string"), True
    return pd.Series(list(value), dtype="string"), False


def _detect(value, pattern: str):
    """stringr::str_detect() with a fully anchored pattern."""
    s, scalar = _as_str_series(value)
    res = s.str.fullmatch(pattern).fillna(False).astype(bool)
    return bool(res.iloc[0]) if scalar else res


def _dedup_columns(df: pd.DataFrame) -> pd.DataFrame:
    """bind_rows()/concat() need unique column labels."""
    return df.loc[:, ~df.columns.duplicated()]


def _bind_rows(frames) -> pd.DataFrame:
    """dplyr::bind_rows(): union of columns, order of first appearance."""
    frames = [f for f in frames
              if f is not None and f.shape[0] > 0 and f.shape[1] > 0]
    if not frames:
        return pd.DataFrame()
    cols = list(dict.fromkeys(c for f in frames for c in f.columns))
    frames = [_dedup_columns(f).reindex(columns=cols) for f in frames]
    return pd.concat(frames, ignore_index=True, sort=False)


def drop_empty_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Remove columns that contain only missing values."""
    if df.empty:
        return df
    return df.loc[:, df.notna().any()]


# ---------------------------------------------------------------------------
# IRI creation
# ---------------------------------------------------------------------------

def create_iri(table, type=None, fragment=None, split=False):
    """
    Create a clean IRI.

    Mirrors epi_create_iri().

    :param table: The table name
    :param type: If None/NA, the type will be omitted.
    :param fragment: The IRI fragment that will be cleaned
    :param split: Not implemented (as in R, the split branch is disabled)
    :return: Series of IRIs (or a single string for scalar input)
    """
    tab, s1 = _as_str_series(table)
    typ, s2 = _as_str_series(type)
    frg, s3 = _as_str_series(fragment)

    if len(tab) == 0 or len(typ) == 0 or len(frg) == 0:
        return pd.Series([], dtype="string")

    n = max(len(tab), len(typ), len(frg))
    tab = tab.repeat(n).reset_index(drop=True) if len(tab) == 1 else tab.reset_index(drop=True)
    typ = typ.repeat(n).reset_index(drop=True) if len(typ) == 1 else typ.reset_index(drop=True)
    frg = frg.repeat(n).reset_index(drop=True) if len(frg) == 1 else frg.reset_index(drop=True)

    tab = tab.fillna("") + "/"
    typ = typ.where(typ.isna(), typ + "/").fillna("")
    frg = clean_irifragment(frg)

    out = (tab + typ + frg.fillna("")).astype("string")
    return out.iloc[0] if (s1 and s2 and s3) else out


def clean_irifragment(fragment):
    """
    Create a clean IRI fragment.

    Replaces all non alphanumeric characters by hyphens and lowercases.

    Mirrors epi_clean_irifragment().
    """
    replacements = {
        "\u00E4": "ae", "\u00F6": "oe", "\u00FC": "ue", "\u00DF": "ss",
        "\u00E5": "aa", "\u00E6": "ae", "\u00F8": "oe",
    }

    s, scalar = _as_str_series(fragment)
    s = s.str.lower()
    for old, new in replacements.items():
        s = s.str.replace(old, new, regex=False)
    s = (s.str.replace(r"[^a-z0-9_~-]", "-", regex=True)
          .str.replace(r"-+", "-", regex=True)
          .str.replace(r"^-", "", regex=True, n=1)
          .str.replace(r"-$", "", regex=True, n=1))
    return s.iloc[0] if scalar else s


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

def is_iripath(iripath, table=None, type=None):
    """
    Check whether the provided values are valid IRI paths, e.g. 'items/xyz/abc'.

    Mirrors epi_is_iripath().

    :param iripath: Values to check (scalar, list or Series)
    :param table: Restrict to that table. None allows all tables.
    :param type: Restrict to that type. None allows all types.
    :return: bool Series (bool for scalar input)
    """
    table = _TABLE_RE if table is None else table
    type = _TYPE_RE if type is None else type
    return _detect(iripath, f"{table}/{type}/{_FRAGMENT_RE}")


def is_id(ids, table=None):
    """
    Check for valid IDs prefixed with table names, e.g. 'articles-123'.

    Mirrors epi_is_id().
    """
    table = _TABLE_RE if table is None else table
    return _detect(ids, f"{table}-{_NUMBER_RE}")


def is_prefixid(ids, table=None, prefix=None):
    """
    Check for valid IDs with temporary prefixes, e.g. 'articles-tmp123'.

    Mirrors epi_is_prefixid().
    """
    table = _TABLE_RE if table is None else table
    prefix = "[a-z]+" if prefix is None else prefix
    return _detect(ids, f"{table}-{prefix}{_NUMBER_RE}")


def is_irifragment(value):
    """
    Check whether the values are valid IRI fragments.

    Mirrors epi_is_irifragment().
    """
    return _detect(value, "[a-z0-9_~-]+")


def iri_parent(id=None, prefix="~"):
    """
    Get the IRI fragment of an IRI path, suffixed with *prefix*.

    Mirrors epi_iri_parent().
    """
    if id is None:
        return ""
    s, scalar = _as_str_series(id)
    out = s.str.rsplit("/", n=1).str[-1] + prefix
    return out.iloc[0] if scalar else out


# ---------------------------------------------------------------------------
# Long format
# ---------------------------------------------------------------------------

def extract_long(df: pd.DataFrame, table: str, type=None,
                 prefix: bool = True) -> pd.DataFrame:
    """
    Get RAM rows by table name.

    Mirrors epi_extract_long().

    :param df: A RAM DataFrame
    :param table: The table name
    :param type: Filter by type: a single value or a list of values
    :param prefix: Whether to prefix the columns with the table name
    :return: DataFrame with the filtered rows, columns prefixed
    """
    if df is None or df.empty or "table" not in df.columns:
        return pd.DataFrame()

    out = df[df["table"] == table]

    if type is not None:
        types = [type] if isinstance(type, str) else list(type)
        if "type" in out.columns:
            out = out[out["type"].isin(types)]

    out = drop_empty_columns(out.copy())
    out = out.drop_duplicates()

    if prefix:
        out.columns = [f"{table}.{c}" for c in out.columns]

    return out.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Wide format
# ---------------------------------------------------------------------------

def extract_wide(data: pd.DataFrame, cols_prefix: str,
                 cols_keep=None) -> pd.DataFrame:
    """
    Select nested data from prefixed columns.

    Mirrors epi_extract_wide().

    :param data: A DataFrame
    :param cols_prefix: All columns with that prefix are selected,
                        the prefix is removed from the column name.
    :param cols_keep: Convert the provided column names to underscored columns
    :return: DataFrame with all prefixed columns, prefix stripped
    """
    cols_keep = list(cols_keep) if cols_keep else []

    if cols_keep:
        alts = [rf"{k}\.id" for k in cols_keep] + [rf"{k}_id" for k in cols_keep]
        regex_keep = re.compile("^(?:" + "|".join(alts) + ")$")
    else:
        regex_keep = re.compile("^$")

    # select(starts_with("prefix."), matches(regex_keep))
    sel = [c for c in data.columns if str(c).startswith(cols_prefix + ".")]
    sel += [c for c in data.columns
            if regex_keep.search(str(c)) and c not in sel]
    if not sel:
        return pd.DataFrame()

    out = data[sel].copy()

    # rename_all: strip the prefix, then first remaining dot -> underscore
    def _rename(col):
        col = re.sub(re.escape(cols_prefix) + r"\.", "", str(col), count=1)
        return re.sub(r"\.", "_", col, count=1)

    out.columns = [_rename(c) for c in out.columns]
    out = _dedup_columns(out)

    out = out.drop_duplicates()                     # distinct()
    out = drop_empty_columns(out)                   # where(~!all(is.na(.x)))
    if out.shape[1] == 0:
        return pd.DataFrame()
    out = out[out.notna().any(axis=1)]              # if_any(everything(), ~!is.na(.))

    # Remove data that only contains ID columns
    id_only = {"id"} | {f"{k}_id" for k in cols_keep}
    if not (set(out.columns) - id_only):
        return pd.DataFrame()

    return out.reset_index(drop=True)


def wide_to_long(data: pd.DataFrame) -> pd.DataFrame:
    """
    Convert wide to long format.

    Mirrors epi_wide_to_long().

    :param data: A DataFrame with the column id containing a valid IRI path.
                 Columns prefixed with "properties", "items", "sections",
                 "articles" or "projects" followed by a dot (e.g.
                 "properties.id", "properties.lemma") are extracted and stacked.
    :return: DataFrame with all input rows and the nested entities stacked
    """
    # Extract nested rows
    rows = _bind_rows([
        extract_wide(data, "properties"),
        extract_wide(data, "projects"),
        extract_wide(data, "articles", ["projects"]),
        extract_wide(data, "sections", ["articles"]),
        extract_wide(data, "items", ["articles", "sections"]),
    ])

    # All other rows
    _OTHER_COLS_RE = re.compile(r"^[_a-z]+$")
    _OTHER_IDS_RE = re.compile(
        r"^projects\.id|articles\.id|sections\.id|items\.id|properties\.id$"
    )
    sel = [c for c in data.columns if _OTHER_COLS_RE.search(str(c))]
    sel += [c for c in data.columns
            if _OTHER_IDS_RE.search(str(c)) and c not in sel]

    extracted = data[sel].copy() if sel else pd.DataFrame()
    if not extracted.empty:
        extracted.columns = [re.sub(r"\.", "_", str(c), count=1)
                             for c in extracted.columns]
        extracted = _dedup_columns(extracted)

    if rows.shape[0] == 0:
        rows = extracted
    elif extracted.shape[0] > 0 and extracted.shape[1] > 0:
        rows = _bind_rows([rows, extracted])

    if rows.shape[0] == 0 or rows.shape[1] == 0:
        return pd.DataFrame()

    if "id" not in rows.columns:
        raise ValueError("No id column found")

    # stopifnot(epi_is_iripath(rows$id) | epi_is_id(rows$id))
    ids = rows["id"]
    valid = is_iripath(ids) | is_id(ids)
    if not valid.all():
        bad = rows.loc[~valid.to_numpy(), "id"].drop_duplicates().head().tolist()
        raise ValueError(f"Invalid ids, e.g. {bad}")

    # Create table column
    rows = rows[rows.notna().any(axis=1)].copy()

    ids = rows["id"].astype("string")
    mask_id = is_id(ids)
    mask_iri = is_iripath(ids) & ~mask_id

    table = pd.Series(pd.NA, index=rows.index, dtype="string")
    table[mask_id] = ids[mask_id].str.extract(r"^([^-]+)", expand=False)
    table[mask_iri] = ids[mask_iri].str.extract(r"^([^/]+)", expand=False)
    rows["table"] = table

    front = ["table", "id"]
    rows = rows[front + [c for c in rows.columns if c not in front]]

    # stopifnot(!is.na(rows$table))
    if rows["table"].isna().any():
        raise ValueError("Could not derive table from id")

    return rows.reset_index(drop=True)