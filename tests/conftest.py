import pandas as pd
import pytest


@pytest.fixture
def example_article():
    """Minimal synthetic RAM-like DataFrame used across distill/base/tree tests."""
    return pd.DataFrame([
        {
            "table": "articles",
            "type": "default",
            "id": "articles-1",
            "norm_iri": "art1",
            "name": "Article One",
        },
        {
            "table": "sections",
            "type": "text",
            "id": "sections-10",
            "articles_id": "articles-1",
        },
        {
            "table": "items",
            "type": "text",
            "id": "items-100",
            "sections_id": "sections-10",
            "articles_id": "articles-1",
            "content": '<seg id="s1">Hello</seg> world',
            "property": "properties-5",
        },
        {
            "table": "properties",
            "type": "topics",
            "id": "properties-5",
            "lemma": "Greetings",
            "parent_id": None,
            "lft": 1,
            "rght": 2,
            "norm_iri": "greet",
        },
        {
            "table": "links",
            "type": None,
            "id": "links-1",
            "root_tab": "articles",
            "root_id": "articles-1",
            "from_tab": "items",
            "from_id": "items-100",
            "from_tagid": "s1",
            "to_tab": "properties",
            "to_id": "properties-5",
        },
    ])


@pytest.fixture
def example_tree2():
    """Two-level tree: root -> child1, child2."""
    return pd.DataFrame({
        "id": ["1", "2", "3"],
        "parent_id": [None, "1", "1"],
        "lemma": ["Root", "Child A", "Child B"],
    })


@pytest.fixture
def example_tree3():
    """Three-level tree: root -> a,b -> a1,a2."""
    columns = ["id", "parent_id", "lemma"]

    rows = [
        ("1", None, "A"),
        ("2", "1", "A1"),
        ("3", "1", "A2"),
        ("4", "2", "A1-1"),
        ("5", "2", "A1-2"),
        ("6", None, "B"),
        ("7", "6", "B1"),
        ("8", "7", "B1-1"),
    ]

    return pd.DataFrame(rows, columns=columns)


@pytest.fixture
def example_properties():
    """RAM with a 3-level 'topics' tree plus two links annotating a leaf.

    """
    # ---------- properties ----------
    properties_cols = ["table", "type", "id", "parent_id", "lemma", "norm_iri", "lft", "rght", "modified"]
    properties_rows = [
        ("properties", "topics", "properties-1", None,           "Root", "root", 1, 10, "2024-01-01"),
        ("properties", "topics", "properties-2", "properties-1", "A",    "a",    2, 7, "2024-01-01"),
        ("properties", "topics", "properties-3", "properties-1", "B",    "b",    8, 9, "2024-01-01"),
        ("properties", "topics", "properties-4", "properties-2", "A1",   "a1",   3, 4, "2024-01-01"),
        ("properties", "topics", "properties-5", "properties-2", "A2",   "a2",   5, 6, "2024-01-01"),
    ]

    # ---------- articles ----------
    articles_cols = ["table", "type", "id", "norm_iri", "name"]
    articles_rows = [
        ("articles", "default", "articles-1", "art1", "Art"),
    ]

    # ---------- sections ----------
    sections_cols = ["table", "type", "id", "articles_id"]
    sections_rows = [
        ("sections", "text", "sections-1", "articles-1"),
    ]

    # ---------- items ----------
    items_cols = ["table", "type", "id", "articles_id", "sections_id", "property", "content"]
    items_rows = [
        ("items", "text", "items-1", "articles-1", "sections-1", "properties-999", 'Hello <seg id="s1">Anna</seg>.'),
        ("items", "text", "items-2", "articles-1", "sections-1", "properties-999", 'Hello <seg id="s1">Bernd</seg>.'),
    ]

    # ---------- links ----------
    links_cols = ["table", "type", "id", "root_tab", "root_id", "from_tab", "from_id", "from_tagid", "to_tab", "to_id"]
    links_rows = [
        ("links", None, "links-1", "articles", "articles-1", "items", "items-1", "s1", "properties", "properties-4"),
        ("links", None, "links-2", "articles", "articles-1", "items", "items-2", "s1", "properties", "properties-4"),
    ]

    # ---------- row bind ----------
    df = pd.concat([
        pd.DataFrame(properties_rows, columns=properties_cols),
        pd.DataFrame(articles_rows, columns=articles_cols),
        pd.DataFrame(sections_rows, columns=sections_cols),
        pd.DataFrame(items_rows, columns=items_cols),
        pd.DataFrame(links_rows, columns=links_cols),
    ], ignore_index=True)


@pytest.fixture
def example_import():
    return pd.DataFrame(
        {
            "case": [1, 2],
            "title": ["Case 01", "Case 02"],
            "text": ["Happy New Year!", "Happy Easter!"],
        }
    )

