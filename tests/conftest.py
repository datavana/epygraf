import pandas as pd
import pytest


@pytest.fixture
def synthetic_ram():
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
def simple_tree():
    return pd.DataFrame({
        "id": ["1", "2", "3"],
        "parent_id": [None, "1", "1"],
        "lemma": ["Root", "Child A", "Child B"],
    })

