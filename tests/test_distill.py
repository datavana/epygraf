from epygraf import distill


def test_articles_returns_expected_columns(synthetic_ram):
    data = distill.articles(synthetic_ram, cols=["name"])
    assert "name" in data.columns
    assert "id" in data.columns


def test_items_joins_property_columns(synthetic_ram):
    data = distill.items(synthetic_ram, cols=["content"], property_cols=["lemma"])
    assert "content" in data.columns
    assert "properties.lemma" in data.columns


def test_properties_builds_path(synthetic_ram):
    props = distill.properties(synthetic_ram, type="topics")
    assert "path" in props.columns
    assert len(props) == 1


def test_extract_segment_and_untagged():
    seg = distill.extract_segment('<seg id="s1">Hello</seg> world', "s1")
    untagged = distill.extract_untagged('<seg id="s1">Hello</seg> world')

    assert "Hello" in seg
    assert "world" in untagged


def test_links_returns_annotation_rows(synthetic_ram):
    links = distill.links(synthetic_ram, properties_type="topics")
    assert "to_id" in links.columns
    assert len(links) == 1

