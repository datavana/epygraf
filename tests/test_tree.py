import pandas as pd
import pytest

from epygraf import tree


# --- escape delimiter --------------------------------------------------------------

def test_escape_delimiter():

    data = pd.DataFrame(
        [
            ("1", None, "A/B"),
            ("2", "1",  "C"),
        ],
        columns=["id", "parent_id", "lemma"]
    )

    result = tree.add_path(data, "id", "parent_id", "lemma")

    assert result.set_index("id")["tree_path"]["1"] == "A&x2f;B"

    # TODO: Compare to full expected output


# --- add_level --------------------------------------------------------------

def test_add_level_2(example_tree2):
    leveled = tree.add_level(example_tree2, "id", "parent_id")
    assert set(leveled["tree_level"].tolist()) == {0, 1}

    # TODO: Compare to full expected output


def test_add_level_3(example_tree3):
    leveled = tree.add_level(example_tree3, "id", "parent_id")
    levels = leveled.set_index("id")["tree_level"]
    assert levels["r"] == 0
    assert levels["a"] == 1
    assert levels["a1"] == 2

# --- add_path ---------------------------------------------------------------

def test_add_path_2(example_tree2):
    result = tree.add_path(example_tree2, "id", "parent_id", "lemma")

    root_path = result.loc[result["id"] == "1", "tree_path"].iloc[0]
    child_path = result.loc[result["id"] == "2", "tree_path"].iloc[0]

    assert root_path == "Root"
    assert " / " in str(child_path)

    # TODO: Compare to full expected output


def test_add_path_3(example_tree3):
    result = tree.add_path(example_tree3, "id", "parent_id", "lemma")

    paths = result.set_index("id")["tree_path"]
    assert paths["1"] == "A"
    assert paths["2"] == "A / A1"
    assert paths["4"] == "A / A1 / A1-1"

    # TODO: Compare to full expected output

def test_add_path_duplicates():
    data = pd.DataFrame(
        [
            ("1", None, "Root"),
            ("1", None, "Root"),
            ("2", "1", "Child"),
            ("2", "1", "Child"),
        ],
        columns=["id", "parent_id", "lemma"]
    )

    result = tree.add_path(data, "id", "parent_id", "lemma")

    # one output row per input row, not a cartesian product
    assert len(result) == len(data)

    # TODO: Compare to full expected output
    assert set(result["tree_path"].tolist()) == {"Root", "Root / Child"}


# --- stack_ancestors --------------------------------------------------------

def test_stack_ancestors(example_tree3):
    ancestors = tree.stack_ancestors(example_tree3, "id", "parent_id", "anc_id")


    assert len(ancestors) == 11

    assert list(ancestors.columns) == ["id", "anc_id"]

    pairs = set(zip(ancestors["id"], ancestors["anc_id"]))

    # a1 descends from itself, a and r
    assert ("a1", "a1") in pairs
    assert ("a1", "a") in pairs
    assert ("a1", "r") in pairs
    # a root only has itself as ancestor
    assert ("r", "r") in pairs

    # TODO: Compare to full expected output




# --- add_ancestor -----------------------------------------------------------

def test_add_ancestor_3(example_tree3):
    with_path = tree.add_path(example_tree3, "id", "parent_id", "lemma")
    with_path["extra"] = "keep-me"

    result = tree.add_ancestor(with_path, "id", "parent_id", "tree_path", level=1)

    by_id = result.set_index("id")
    assert by_id.loc["a1", "ancestor_id"] == "a"
    assert by_id.loc["a1", "ancestor_path"] == "Root / A"
    # the root has no level-1 ancestor and is dropped
    assert "r" not in result["id"].tolist()


    assert "extra" in result.columns
    assert "tree_path" in result.columns
    assert set(result["extra"].tolist()) == {"keep-me"}

    # TODO: Compare to full expected output
