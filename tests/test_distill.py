import pandas as pd
import pytest

from epygraf import distill


@pytest.fixture
def property_tree_ram():
    """RAM with a 3-level 'topics' tree plus two links annotating a leaf.

    The properties deliberately carry no ``level`` column, so ``links()`` has
    to derive the tree depth itself.
    """
    rows = [
        {"table": "properties", "type": "topics", "id": "properties-1",
         "parent_id": None, "lemma": "Root", "norm_iri": "root",
         "lft": 1, "rght": 10, "modified": "2024-01-01"},
        {"table": "properties", "type": "topics", "id": "properties-2",
         "parent_id": "properties-1", "lemma": "A", "norm_iri": "a",
         "lft": 2, "rght": 7, "modified": "2024-01-01"},
        {"table": "properties", "type": "topics", "id": "properties-3",
         "parent_id": "properties-1", "lemma": "B", "norm_iri": "b",
         "lft": 8, "rght": 9, "modified": "2024-01-01"},
        {"table": "properties", "type": "topics", "id": "properties-4",
         "parent_id": "properties-2", "lemma": "A1", "norm_iri": "a1",
         "lft": 3, "rght": 4, "modified": "2024-01-01"},
        {"table": "properties", "type": "topics", "id": "properties-5",
         "parent_id": "properties-2", "lemma": "A2", "norm_iri": "a2",
         "lft": 5, "rght": 6, "modified": "2024-01-01"},
        {"table": "articles", "type": "default", "id": "articles-1",
         "norm_iri": "art1", "name": "Art"},
        {"table": "sections", "type": "text", "id": "sections-1",
         "articles_id": "articles-1"},
        {"table": "items", "type": "text", "id": "items-1",
         "articles_id": "articles-1", "sections_id": "sections-1",
         "property": "properties-999", "content": '<seg id="s1">Anna</seg>'},
        {"table": "items", "type": "text", "id": "items-2",
         "articles_id": "articles-1", "sections_id": "sections-1",
         "property": "properties-999", "content": '<seg id="s1">Bernd</seg>'},
        {"table": "links", "type": None, "id": "links-1",
         "root_tab": "articles", "root_id": "articles-1",
         "from_tab": "items", "from_id": "items-1", "from_tagid": "s1",
         "to_tab": "properties", "to_id": "properties-4"},
        {"table": "links", "type": None, "id": "links-2",
         "root_tab": "articles", "root_id": "articles-1",
         "from_tab": "items", "from_id": "items-2", "from_tagid": "s1",
         "to_tab": "properties", "to_id": "properties-4"},
    ]
    return pd.DataFrame(rows)


# --- articles ---------------------------------------------------------------

def test_articles_returns_expected_columns(synthetic_ram):
    data = distill.articles(synthetic_ram, cols=["name"])
    assert "name" in data.columns
    assert "id" in data.columns


# --- items ------------------------------------------------------------------

def test_items_joins_property_columns(synthetic_ram):
    data = distill.items(synthetic_ram, cols=["content"], property_cols=["lemma"])
    assert "content" in data.columns
    assert "properties.lemma" in data.columns


# --- properties -------------------------------------------------------------

def test_properties_builds_path(synthetic_ram):
    props = distill.properties(synthetic_ram, type="topics")
    assert "path" in props.columns
    assert len(props) == 1


def test_properties_builds_full_path(property_tree_ram):
    props = distill.properties(property_tree_ram, type="topics")
    paths = props.set_index("id")["path"]
    assert paths["properties-1"] == "Root"
    assert paths["properties-4"] == "Root / A / A1"


def test_properties_dedups_sparse_and_full_rows(property_tree_ram):
    # append a sparse link-only duplicate of A1 (no lemma/norm_iri/modified)
    sparse = property_tree_ram[property_tree_ram["id"] == "properties-4"].iloc[[0]].copy()
    sparse["lemma"] = None
    sparse["norm_iri"] = None
    sparse["modified"] = None
    ram = pd.concat([property_tree_ram, sparse], ignore_index=True)

    props = distill.properties(ram, type="topics")
    assert props["id"].tolist().count("properties-4") == 1
    assert len(props) == 5


def test_properties_levelup_adds_ancestor(property_tree_ram):
    props = distill.properties(property_tree_ram, type="topics", levelup=1)
    by_id = props.set_index("id")

    assert by_id.loc["properties-4", "ancestor_id"] == "properties-2"
    assert by_id.loc["properties-4", "ancestor_path"] == "Root / A"
    # the root has no level-1 ancestor and is dropped
    assert "properties-1" not in props["id"].tolist()


def test_properties_annos_one_row_per_annotation(property_tree_ram):
    props = distill.properties(property_tree_ram, type="topics", annos=True)

    # A1 is targeted by two links -> two annotation rows (no cartesian product)
    assert props["id"].tolist().count("properties-4") == 2
    # 4 un-annotated properties + 2 annotation rows
    assert len(props) == 6


# --- links ------------------------------------------------------------------

def test_links_returns_annotation_rows(synthetic_ram):
    links = distill.links(synthetic_ram, properties_type="topics")
    assert "to_id" in links.columns
    assert len(links) == 1


def test_links_returns_one_row_per_link(property_tree_ram):
    links = distill.links(property_tree_ram, properties_type="topics", cols=["segment"])
    # two links, not (depth+1)^2 = 9 rows per link
    assert len(links) == 2
    assert "to_id" in links.columns
    assert "segment" in links.columns


def test_links_respects_aggregation_level(property_tree_ram):
    expected = {
        0: "Root",
        1: "Root / A",
        2: "Root / A / A1",
        None: "Root / A / A1",
    }
    for level, path in expected.items():
        out = distill.links(property_tree_ram, properties_type="topics",
                            cols=["path"], level=level)
        assert len(out) == 2
        assert set(out["path"].tolist()) == {path}


# --- segment extraction -----------------------------------------------------

def test_extract_segment_and_untagged():
    seg = distill.extract_segment('<seg id="s1">Hello</seg> world', "s1")
    untagged = distill.extract_untagged('<seg id="s1">Hello</seg> world')

    assert "Hello" in seg
    assert "world" in untagged


def test_extract_segment_invalid_xml_returns_empty():
    assert distill.extract_segment("not valid <xml", "s1") == ""


def test_extract_segment_missing_tagid_returns_empty():
    assert distill.extract_segment('<seg id="s1">Hello</seg>', "") == ""
