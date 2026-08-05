from epygraf import tree


def test_add_path_builds_hierarchical_paths(simple_tree):
    result = tree.add_path(simple_tree, "id", "parent_id", "lemma")

    root_path = result.loc[result["id"] == "1", "tree_path"].iloc[0]
    child_path = result.loc[result["id"] == "2", "tree_path"].iloc[0]

    assert root_path == "Root"
    assert " / " in str(child_path)


def test_stack_ancestors_duplicates_rows_per_ancestor(simple_tree):
    ancestors = tree.stack_ancestors(simple_tree, "id", "parent_id", "anc_id")
    assert len(ancestors) >= 5


def test_add_level_sets_root_and_child_levels(simple_tree):
    leveled = tree.add_level(simple_tree, "id", "parent_id")
    assert set(leveled["tree_level"].tolist()) == {0, 1}

