import pandas as pd
import pytest

from epygraf import distill


# --- articles ---------------------------------------------------------------

def test_articles_returns_expected_columns(example_article):
    data = distill.articles(example_article, cols=["name"])
    assert "name" in data.columns
    assert "id" in data.columns


# --- items ------------------------------------------------------------------

def test_items_joins_property_columns(example_article):
    data = distill.items(example_article, cols=["content"], property_cols=["lemma"])
    assert "content" in data.columns
    assert "properties.lemma" in data.columns


# --- properties -------------------------------------------------------------

def test_properties_builds_path(example_article):
    props = distill.properties(example_article, type="topics")
    assert "path" in props.columns
    assert len(props) == 1


def test_properties_builds_full_path(example_properties):
    props = distill.properties(example_properties, type="topics")
    paths = props.set_index("id")["path"]
    assert paths["properties-1"] == "Root"
    assert paths["properties-4"] == "Root / A / A1"


def test_properties_dedups_sparse_and_full_rows(example_properties):
    # append a sparse link-only duplicate of A1 (no lemma/norm_iri/modified)
    sparse = example_properties[example_properties["id"] == "properties-4"].iloc[[0]].copy()
    sparse["lemma"] = None
    sparse["norm_iri"] = None
    sparse["modified"] = None
    ram = pd.concat([example_properties, sparse], ignore_index=True)

    props = distill.properties(ram, type="topics")
    assert props["id"].tolist().count("properties-4") == 1
    assert len(props) == 5


def test_properties_levelup_adds_ancestor(example_properties):
    props = distill.properties(example_properties, type="topics", levelup=1)
    by_id = props.set_index("id")

    assert by_id.loc["properties-4", "ancestor_id"] == "properties-2"
    assert by_id.loc["properties-4", "ancestor_path"] == "Root / A"
    # the root has no level-1 ancestor and is dropped
    assert "properties-1" not in props["id"].tolist()


def test_properties_annos_one_row_per_annotation(example_properties):
    props = distill.properties(example_properties, type="topics", annos=True)

    # A1 is targeted by two links -> two annotation rows (no cartesian product)
    assert props["id"].tolist().count("properties-4") == 2
    # 4 un-annotated properties + 2 annotation rows
    assert len(props) == 6


# --- links ------------------------------------------------------------------

def test_links_returns_annotation_rows(example_article):
    links = distill.links(example_article, properties_type="topics")
    assert "to_id" in links.columns
    assert len(links) == 1


def test_links_returns_one_row_per_link(example_properties):
    links = distill.links(example_properties, properties_type="topics", cols=["segment"])
    # two links, not (depth+1)^2 = 9 rows per link
    assert len(links) == 2
    assert "to_id" in links.columns
    assert "segment" in links.columns


def test_links_respects_aggregation_level(example_properties):
    expected = {
        0: "Root",
        1: "Root / A",
        2: "Root / A / A1",
        None: "Root / A / A1",
    }
    for level, path in expected.items():
        out = distill.links(example_properties, properties_type="topics",
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
