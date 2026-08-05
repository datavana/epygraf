from epygraf import base


def test_extract_long_prefixes_columns(synthetic_ram):
    arts = base.extract_long(synthetic_ram, "articles")
    assert "articles.id" in arts.columns


def test_iri_parent_single_and_vector():
    single = base.iri_parent("properties/topics/foo")
    many = base.iri_parent(["properties/topics/foo", "items/text/bar"], prefix="~")

    assert single == "foo~"
    assert many == ["foo~", "bar~"]

