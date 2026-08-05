"""
RAM (Record Accumulation Model) helper functions.

Mirrors ram.R from the R package.
RAM rows are stored in ``df.attrs["epi"]["rows"]`` and can be compiled
into a patch-ready DataFrame with compile().
"""

import pandas as pd


def add(df: pd.DataFrame, rows: pd.DataFrame, skip: bool = False) -> pd.DataFrame:
    """
    Add rows to the RAM attribute of a DataFrame.

    Mirrors ram_add() from ram.R.

    :param df: An Epigraf DataFrame
    :param rows: DataFrame of crafted rows to accumulate
    :param skip: If True, mark rows with ``_action = "skip"`` so they are
                 used as reference only and not written back to the database
    :return: DataFrame with the new rows appended to its ``epi`` attribute
    """
    epi = dict(df.attrs.get("epi", {}))
    existing = epi.get("rows")
    if existing is None or (hasattr(existing, "empty") and existing.empty):
        epi["rows"] = pd.DataFrame()

    rows = rows.copy()
    # Cast all columns to str (mirrors R's mutate across as.character)
    for col in rows.columns:
        rows[col] = rows[col].astype(str)

    if skip:
        rows["_action"] = "skip"

    epi["rows"] = pd.concat([epi["rows"], rows], ignore_index=True)

    df = df.copy()
    df.attrs["epi"] = epi
    df.attrs["epi_type"] = "table"
    return df


def compile(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compile the accumulated RAM rows into a patch-ready DataFrame.

    Mirrors ram_compile() from ram.R.

    :param df: An Epigraf DataFrame with RAM rows in its ``epi`` attribute
    :return: DataFrame with the RAM rows in patch order
    """
    epi = df.attrs.get("epi", {})
    rows = epi.get("rows", pd.DataFrame())
    if rows is None or (hasattr(rows, "empty") and rows.empty):
        return pd.DataFrame()

    cols = list(rows.columns)
    cols_first = [c for c in ["table", "id"] if c in cols]
    cols_last = [c for c in ["properties_id", "sections_id", "articles_id",
                              "projects_id", "_fields"] if c in cols]
    dot_cols = [c for c in cols if c.startswith(".")]
    cols_mid = [c for c in cols
                if c not in cols_first and c not in cols_last and c not in dot_cols]

    ordered = list(dict.fromkeys(cols_first + cols_mid + cols_last))
    ordered = [c for c in ordered if c in cols]
    rows = rows[ordered]

    # Reverse row order (mirrors R's apply(rows, 2, rev))
    return rows.iloc[::-1].reset_index(drop=True)


def clear(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove all accumulated RAM rows from a DataFrame.

    Mirrors ram_clear() from ram.R.

    :param df: An Epigraf DataFrame with RAM rows in its ``epi`` attribute
    :return: DataFrame with an empty ``epi.rows`` attribute
    """
    epi = dict(df.attrs.get("epi", {}))
    epi["rows"] = pd.DataFrame()
    df = df.copy()
    df.attrs["epi"] = epi
    df.attrs["epi_type"] = "table"
    return df

