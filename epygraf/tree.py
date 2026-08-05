"""
Tree helper functions for hierarchical data.

Mirrors trees.R from the R package.
"""

import pandas as pd

from epygraf import utils


def add_path(data: pd.DataFrame, col_id: str, col_parent_id: str,
             col_lemma: str, delim: str = "/") -> pd.DataFrame:
    """
    Add a column holding the path of each node.

    The path is built by concatenating all col_lemma values up to the root.
    Existing delimiters inside lemmata are escaped as ``&x<hex>;``
    (e.g. ``/`` becomes ``&x2f;``).

    Mirrors tree_add_path() from trees.R.

    :param data: DataFrame with hierarchical data
    :param col_id: ID column name
    :param col_parent_id: Parent ID column name
    :param col_lemma: Column used for path labels
    :param delim: Path segment separator (default ``/``)
    :return: DataFrame with additional column ``tree_path``
    """
    data = data.copy()
    delim_entity = f"&x{format(ord(delim), 'x')};"  # e.g. "&x2f;"

    # Escape delimiter inside lemmata
    data[col_lemma] = data[col_lemma].astype(str).str.replace(delim, delim_entity, regex=False)
    data["tree_path"] = pd.NA

    # Root nodes have no parent
    root_mask = data[col_parent_id].isna()
    current = (
        data.loc[root_mask, [col_id, col_lemma]]
        .rename(columns={col_lemma: "tree_path"})
        .copy()
    )

    while not current.empty:
        path_map = current.set_index(col_id)["tree_path"]
        update_mask = data[col_id].isin(current[col_id])
        data.loc[update_mask, "tree_path"] = (
            data.loc[update_mask, col_id].map(path_map).values
        )

        children = data.merge(
            current.rename(columns={col_id: "_par_id", "tree_path": "_par_path"}),
            left_on=col_parent_id, right_on="_par_id", how="inner",
        )
        if children.empty:
            break
        children["tree_path"] = children["_par_path"] + f" {delim} " + children[col_lemma]
        current = children[[col_id, "tree_path"]].copy()

    return data


def stack_ancestors(data: pd.DataFrame, col_id: str, col_parent: str,
                    col_stack: str) -> pd.DataFrame:
    """
    For each node, add a separate row for every ancestor.

    The result contains each original row duplicated once per ancestor
    (including the node itself).  ``col_stack`` holds the ancestor ID.

    Mirrors tree_stack_ancestors() from trees.R.

    :param data: DataFrame with all nodes
    :param col_id: ID column name
    :param col_parent: Parent ID column name
    :param col_stack: Column name for the ancestor IDs
    :return: Expanded DataFrame
    """
    data = data.copy()
    data["_tree_id"] = data[col_id]
    data["_tree_parent"] = data[col_parent]

    data_stacked = data.copy()
    data_stacked["_tree_main"] = data_stacked["_tree_id"]

    data_parents = data[data["_tree_parent"].notna()].copy()
    data_parents["_tree_main"] = data_parents["_tree_parent"]

    parent_ref = data[["_tree_id", "_tree_parent"]].rename(
        columns={"_tree_id": "_ref_id", "_tree_parent": "_tree_main_new"}
    )

    while not data_parents.empty:
        data_stacked = pd.concat([data_stacked, data_parents], ignore_index=True)
        merged = data_parents.merge(
            parent_ref, left_on="_tree_main", right_on="_ref_id", how="inner"
        )
        merged = merged[merged["_tree_main_new"].notna()]
        if merged.empty:
            break
        merged = merged.copy()
        merged["_tree_main"] = merged["_tree_main_new"]
        data_parents = merged.drop(
            columns=[c for c in ["_tree_main_new", "_ref_id"] if c in merged.columns]
        )

    result = data_stacked.drop(columns=["_tree_id", "_tree_parent"])
    return result.rename(columns={"_tree_main": col_stack}).reset_index(drop=True)


def add_level(data: pd.DataFrame, col_id: str, col_parent: str,
              col_sort: str = None) -> pd.DataFrame:
    """
    Add level, thread, and order columns.

    Mirrors tree_add_level() from trees.R.

    :param data: DataFrame with hierarchical data
    :param col_id: ID column name
    :param col_parent: Parent ID column name
    :param col_sort: Column for ordering siblings (defaults to col_id)
    :return: DataFrame with additional columns ``tree_thread``, ``tree_level``, ``tree_order``
    """
    if col_sort is None:
        col_sort = col_id

    data = data.copy()
    data["_tree_id"] = data[col_id]
    data["_tree_parent"] = data[col_parent]

    all_ids = set(data["_tree_id"].dropna().tolist())
    is_root = ~data["_tree_parent"].isin(all_ids) | data["_tree_parent"].isna()

    roots = data[is_root].copy()
    roots["tree_thread"] = roots["_tree_id"]
    roots["tree_level"] = 0
    roots["tree_order"] = 0

    result = roots.copy()
    current_with_thread = roots[["_tree_id", "tree_thread"]].copy()
    assigned_ids: set = set(roots["_tree_id"].tolist())

    level = 1
    while True:
        candidates = data[~data["_tree_id"].isin(assigned_ids)]
        children = candidates.merge(
            current_with_thread.rename(columns={"_tree_id": "_par_id"}),
            left_on="_tree_parent", right_on="_par_id", how="inner",
        )
        if children.empty:
            break

        children = children.sort_values(col_sort)
        children["tree_order"] = children.groupby("_tree_parent").cumcount() + 1
        children["tree_level"] = level

        result = pd.concat([result, children], ignore_index=True)
        assigned_ids.update(children["_tree_id"].tolist())
        current_with_thread = children[["_tree_id", "tree_thread"]].copy()
        level += 1

    drop_cols = [c for c in ["_tree_id", "_tree_parent", "_par_id"] if c in result.columns]
    return result.drop(columns=drop_cols).reset_index(drop=True)


def add_ancestor(data: pd.DataFrame, col_id: str, col_parent_id: str,
                 col_path: str, level: int = 0) -> pd.DataFrame:
    """
    Add ancestor id and path from a specific level to all descendants.

    Mirrors tree_add_ancestor() from trees.R.

    :param data: DataFrame with hierarchical data
    :param col_id: ID column name
    :param col_parent_id: Parent ID column name
    :param col_path: Path column name
    :param level: The target ancestor level (default 0 = root)
    :return: DataFrame with ``ancestor_id`` and ``ancestor_path`` columns added
    """
    target_cols = [c for c in [col_id, col_parent_id, col_path] if c in data.columns]
    target = add_level(data[target_cols].drop_duplicates(), col_id, col_parent_id)

    level_nodes = target[target["tree_level"] == level][[col_id, col_path]].copy()
    level_nodes.columns = ["ancestor_id", "ancestor_path"]

    stacked = stack_ancestors(data.drop_duplicates(), col_id, col_parent_id, "ancestor_id")
    return stacked.merge(level_nodes, on="ancestor_id", how="inner")

