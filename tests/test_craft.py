import pandas as pd
import pytest

from epygraf import craft, ram


def test_df_to_ram_returns_ram_enhanced_dataframe(example_import):
    result = craft.df_to_ram(
        example_import,
        project_fill={"fragment": "Example"},
        article_cols={"fragment": "case", "signature": "case", "name": "title"},
        section_fill={"fragment": "text"},
        item_cols={"content": "text"},
        compile=False,
    )

    assert "epi" in result.attrs
    assert "rows" in result.attrs["epi"]
    rows = result.attrs["epi"]["rows"]
    assert not rows.empty
    assert "id" in rows.columns


def test_df_to_ram_compile_true_returns_compiled_rows(example_import):
    compiled = craft.df_to_ram(
        example_import,
        project_fill={"fragment": "Example"},
        article_cols={"fragment": "case", "signature": "case", "name": "title"},
        section_fill={"fragment": "text"},
        item_cols={"content": "text"},
        compile=True,
    )

    assert isinstance(compiled, pd.DataFrame)
    assert not compiled.empty
    assert "id" in compiled.columns


def test_craft_articles_requires_project(example_import):
    with pytest.raises(ValueError, match="Please, craft a project first"):
        craft.craft_articles(example_import)


def test_craft_sections_requires_article(example_import):
    with_project = craft.craft_projects(example_import)
    with pytest.raises(ValueError, match="Please, craft an article first"):
        craft.craft_sections(with_project)


def test_craft_items_requires_section(example_import):
    with_project = craft.craft_projects(example_import)
    with_article = craft.craft_articles(with_project)
    with pytest.raises(ValueError, match="Please, map a section first"):
        craft.craft_items(with_article)


def test_craft_properties_builds_property_ids(example_import):
    result = craft.craft_properties(
        example_import,
        cols={"fragment": "case", "type": "title"},
        fill={"name": "X"},
    )

    rows = ram.compile(result)
    assert not rows.empty
    assert rows["id"].str.startswith("properties/").all()

