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

    expected = pd.DataFrame(
        [
            ("1", None, "A&x2f;B", "A&x2f;B"),
            ("2", "1",  "C", "A&x2f;B / C"),
        ],
        columns=["id", "parent_id", "lemma", "tree_path"]
    )

    pd.testing.assert_frame_equal(result, expected)



# --- add_level --------------------------------------------------------------

def test_add_level_2(example_tree2):
    leveled = tree.add_level(example_tree2, "id", "parent_id")

    expected = pd.DataFrame(
        [
            ("1", None, "Root", "1", 0, 0),
            ("2", "1", "Child A", "1", 1, 1),
            ("3", "1", "Child B", "1", 1, 2),
        ],
        columns=["id", "parent_id", "lemma", "tree_thread", "tree_level", "tree_order"],
    )

    pd.testing.assert_frame_equal(leveled, expected)


def test_add_level_3(example_tree3):
    leveled = tree.add_level(example_tree3, "id", "parent_id")

    expected = pd.DataFrame(
        [
            ("1", None, "A", "1", 0, 0),
            ("6", None, "B", "6", 0, 0),
            ("2", "1", "A1", "1", 1, 1),
            ("3", "1", "A2", "1", 1, 2),
            ("7", "6", "B1", "6", 1, 1),
            ("4", "2", "A1-1", "1", 2, 1),
            ("5", "2", "A1-2", "1", 2, 2),
            ("8", "7", "B1-1", "6", 2, 1),
        ],
        columns=["id", "parent_id", "lemma", "tree_thread", "tree_level", "tree_order"],
    )

    pd.testing.assert_frame_equal(leveled, expected)

# --- add_path ---------------------------------------------------------------

def test_add_path_2(example_tree2):
    result = tree.add_path(example_tree2, "id", "parent_id", "lemma")

    expected = pd.DataFrame(
        [
            ("1", None, "Root", "Root"),
            ("2", "1", "Child A", "Root / Child A"),
            ("3", "1", "Child B", "Root / Child B"),
        ],
        columns=["id", "parent_id", "lemma", "tree_path"],
    )

    pd.testing.assert_frame_equal(result, expected)


def test_add_path_3(example_tree3):
    result = tree.add_path(example_tree3, "id", "parent_id", "lemma")

    expected = pd.DataFrame(
        [
            ("1", None, "A", "A"),
            ("2", "1", "A1", "A / A1"),
            ("3", "1", "A2", "A / A2"),
            ("4", "2", "A1-1", "A / A1 / A1-1"),
            ("5", "2", "A1-2", "A / A1 / A1-2"),
            ("6", None, "B", "B"),
            ("7", "6", "B1", "B / B1"),
            ("8", "7", "B1-1", "B / B1 / B1-1"),
        ],
        columns=["id", "parent_id", "lemma", "tree_path"],
    )

    pd.testing.assert_frame_equal(result, expected)

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

    expected = pd.DataFrame(
        [
            ("1", None, "Root", "Root"),
            ("1", None, "Root", "Root"),
            ("2", "1", "Child", "Root / Child"),
            ("2", "1", "Child", "Root / Child"),
        ],
        columns=["id", "parent_id", "lemma", "tree_path"],
    )

    pd.testing.assert_frame_equal(result, expected)



# --- stack_ancestors --------------------------------------------------------

def test_stack_ancestors(example_tree3):
    ancestors = tree.stack_ancestors(example_tree3, "id", "parent_id", "anc_id")

    expected = pd.DataFrame(
        [
            ("1", "1"),
            ("2", "2"),
            ("3", "3"),
            ("4", "4"),
            ("5", "5"),
            ("6", "6"),
            ("7", "7"),
            ("8", "8"),
            ("2", "1"),
            ("3", "1"),
            ("4", "2"),
            ("5", "2"),
            ("7", "6"),
            ("8", "7"),
            ("4", "1"),
            ("5", "1"),
            ("8", "6"),
        ],
        columns=["id", "anc_id"],
    )

    pd.testing.assert_frame_equal(ancestors, expected)




# --- add_ancestor -----------------------------------------------------------

def test_add_ancestor_3(example_tree3):
    with_path = tree.add_path(example_tree3, "id", "parent_id", "lemma")
    with_path["extra"] = "keep-me"

    result = tree.add_ancestor(with_path, "id", "parent_id", "tree_path", level=1)

    expected = pd.DataFrame(
        [
            ("2", "1", "A1", "A / A1", "keep-me", "2", "A / A1"),
            ("3", "1", "A2", "A / A2", "keep-me", "3", "A / A2"),
            ("4", "2", "A1-1", "A / A1 / A1-1", "keep-me", "2", "A / A1"),
            ("5", "2", "A1-2", "A / A1 / A1-2", "keep-me", "2", "A / A1"),
            ("7", "6", "B1", "B / B1", "keep-me", "7", "B / B1"),
            ("8", "7", "B1-1", "B / B1 / B1-1", "keep-me", "7", "B / B1"),
        ],
        columns=["id", "parent_id", "lemma", "tree_path", "extra", "ancestor_id", "ancestor_path"],
    )

    pd.testing.assert_frame_equal(result, expected)
