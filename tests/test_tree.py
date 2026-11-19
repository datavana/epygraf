import pandas as pd
import pytest

from epygraf import tree


@pytest.fixture
def multi_level_tree():
    """Three-level tree: root -> a,b -> a1,a2."""
    return pd.DataFrame({
        "id": ["r", "a", "b", "a1", "a2"],
        "parent_id": [None, "r", "r", "a", "a"],
        "lemma": ["Root", "A", "B", "A1", "A2"],
    })


# --- add_path ---------------------------------------------------------------

def test_add_path_builds_hierarchical_paths(simple_tree):
    result = tree.add_path(simple_tree, "id", "parent_id", "lemma")

    root_path = result.loc[result["id"] == "1", "tree_path"].iloc[0]
    child_path = result.loc[result["id"] == "2", "tree_path"].iloc[0]

    assert root_path == "Root"
    assert " / " in str(child_path)


def test_add_path_builds_deep_paths(multi_level_tree):
    result = tree.add_path(multi_level_tree, "id", "parent_id", "lemma")
    paths = result.set_index("id")["tree_path"]
    assert paths["r"] == "Root"
    assert paths["a"] == "Root / A"
    assert paths["a1"] == "Root / A / A1"


def test_add_path_escapes_delimiter_in_lemma():
    data = pd.DataFrame({
        "id": ["1", "2"],
        "parent_id": [None, "1"],
        "lemma": ["A/B", "C"],
    })
    result = tree.add_path(data, "id", "parent_id", "lemma")
    assert result.set_index("id")["tree_path"]["1"] == "A&x2f;B"


def test_add_path_does_not_explode_on_duplicate_ids():
    data = pd.DataFrame({
        "id": ["1", "1", "2", "2"],
        "parent_id": [None, None, "1", "1"],
        "lemma": ["Root", "Root", "Child", "Child"],
    })
    result = tree.add_path(data, "id", "parent_id", "lemma")
    # one output row per input row, not a cartesian product
    assert len(result) == len(data)
    assert set(result["tree_path"].tolist()) == {"Root", "Root / Child"}


# --- stack_ancestors --------------------------------------------------------

def test_stack_ancestors_returns_only_id_and_ancestor(multi_level_tree):
    ancestors = tree.stack_ancestors(multi_level_tree, "id", "parent_id", "anc_id")
    assert list(ancestors.columns) == ["id", "anc_id"]


def test_stack_ancestors_includes_self_and_all_ancestors(multi_level_tree):
    ancestors = tree.stack_ancestors(multi_level_tree, "id", "parent_id", "anc_id")
    pairs = set(zip(ancestors["id"], ancestors["anc_id"]))

    # a1 descends from itself, a and r
    assert ("a1", "a1") in pairs
    assert ("a1", "a") in pairs
    assert ("a1", "r") in pairs
    # a root only has itself as ancestor
    assert ("r", "r") in pairs


def test_stack_ancestors_row_count(multi_level_tree):
    ancestors = tree.stack_ancestors(multi_level_tree, "id", "parent_id", "anc_id")
    # r:1, a:2, b:2, a1:3, a2:3 -> 11 rows total
    assert len(ancestors) == 11


def test_stack_ancestors_duplicates_rows_per_ancestor(simple_tree):
    ancestors = tree.stack_ancestors(simple_tree, "id", "parent_id", "anc_id")
    assert len(ancestors) >= 5


# --- add_level --------------------------------------------------------------

def test_add_level_sets_root_and_child_levels(simple_tree):
    leveled = tree.add_level(simple_tree, "id", "parent_id")
    assert set(leveled["tree_level"].tolist()) == {0, 1}


def test_add_level_sets_deep_levels(multi_level_tree):
    leveled = tree.add_level(multi_level_tree, "id", "parent_id")
    levels = leveled.set_index("id")["tree_level"]
    assert levels["r"] == 0
    assert levels["a"] == 1
    assert levels["a1"] == 2


# --- add_ancestor -----------------------------------------------------------

def test_add_ancestor_maps_to_requested_level(multi_level_tree):
    with_path = tree.add_path(multi_level_tree, "id", "parent_id", "lemma")
    result = tree.add_ancestor(with_path, "id", "parent_id", "tree_path", level=1)

    by_id = result.set_index("id")
    assert by_id.loc["a1", "ancestor_id"] == "a"
    assert by_id.loc["a1", "ancestor_path"] == "Root / A"
    # the root has no level-1 ancestor and is dropped
    assert "r" not in result["id"].tolist()


def test_add_ancestor_preserves_other_columns(multi_level_tree):
    with_path = tree.add_path(multi_level_tree, "id", "parent_id", "lemma")
    with_path["extra"] = "keep-me"
    result = tree.add_ancestor(with_path, "id", "parent_id", "tree_path", level=0)

    assert "extra" in result.columns
    assert "tree_path" in result.columns
    assert set(result["extra"].tolist()) == {"keep-me"}
