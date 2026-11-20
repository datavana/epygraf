import numpy as np
import pandas as pd
import pytest

from epygraf import distill


def _plain(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise a frame so dtype/null-type differences between pandas
    versions don't break ``assert_frame_equal``.

    pandas 3.0 defaults to ``StringDtype`` (with ``pd.NA``) for string data,
    whereas earlier versions use ``object`` (with ``np.nan``).  Casting to
    ``object`` and collapsing every missing value to ``None`` makes the
    comparison independent of both.
    """
    return df.astype(object).where(df.notna(), None)


# --- articles ---------------------------------------------------------------

def test_articles(example_article):
    result = distill.articles(example_article, cols=["name"])

    expected = pd.DataFrame(
          [("Article One", "articles-1", "default", "art1")],
        columns=["name",        "id",          "type",   "norm_iri"],
    )

    pd.testing.assert_frame_equal(_plain(result), _plain(expected))


# --- items ------------------------------------------------------------------

def test_items(example_article):
    result = distill.items(example_article, cols=["content"], property_cols=["lemma"])

    expected = pd.DataFrame(
        [
              ('<seg id="s1">Hello</seg> world', "Greetings", "items-100", "text", None, "articles-1", "sections-10"),
        ],
        columns=["content", "properties.lemma", "id", "type", "norm_iri", "articles_id", "sections_id"],
    )

    pd.testing.assert_frame_equal(_plain(result), _plain(expected))


# --- properties -------------------------------------------------------------

def test_properties(example_article):
    result = distill.properties(example_article, type="topics")

    expected = pd.DataFrame(
          [("Greetings", "properties-5", "topics", "greet")],
        columns=["path", "id", "type", "norm_iri"],
    )

    pd.testing.assert_frame_equal(_plain(result), _plain(expected))


def test_properties_levelup1(example_properties):
    result = distill.properties(example_properties, type="topics", levelup=1)

    expected = pd.DataFrame(
        [
            ("Root / A", "properties-2", "properties-1", "topics", "a", "properties-2", "Root / A"),
            ("Root / B", "properties-3", "properties-1", "topics", "b", "properties-3", "Root / B"),
            ("Root / A / A1", "properties-4", "properties-2", "topics", "a1", "properties-2", "Root / A"),
            ("Root / A / A2", "properties-5", "properties-2", "topics", "a2", "properties-2", "Root / A"),
        ],
        columns=["path", "id", "parent_id", "type", "norm_iri", "ancestor_id", "ancestor_path"],
    )

    pd.testing.assert_frame_equal(_plain(result), _plain(expected))


def test_properties_annos(example_properties):
    result = distill.properties(example_properties, type="topics", annos=True)

    expected = pd.DataFrame(
        [
            ("Root", "properties-1", pd.NA, "topics", "root", np.nan, np.nan, np.nan, np.nan, np.nan, np.nan),
            ("Root / A", "properties-2", "properties-1", "topics", "a", np.nan, np.nan, np.nan, np.nan, np.nan, np.nan),
            ("Root / B", "properties-3", "properties-1", "topics", "b", np.nan, np.nan, np.nan, np.nan, np.nan, np.nan),
            ("Root / A / A2", "properties-5", "properties-2", "topics", "a2", np.nan, np.nan, np.nan, np.nan, np.nan, np.nan),
            ("Root / A / A1", "properties-4", "properties-2", "topics", "a1", "articles-1", "sections-1", "items-1", "s1", "Anna", "properties-4"),
            ("Root / A / A1", "properties-4", "properties-2", "topics", "a1", "articles-1", "sections-1", "items-2", "s1", "Bernd", "properties-4"),
        ],
        columns=["path", "id", "parent_id", "type", "norm_iri","articles_id", "sections_id", "items_id", "from_tagid","segment", "to_id"],
    )

    pd.testing.assert_frame_equal(_plain(result), _plain(expected))


# --- links ------------------------------------------------------------------

def test_links(example_article):
    result = distill.links(example_article, properties_type="topics")

    expected = pd.DataFrame(
        [
            ("articles-1", "sections-10", "items-100", "s1", "Greetings", "Hello", "properties-5"),
        ],
        columns=["articles_id", "sections_id", "items_id", "from_tagid", "path", "segment", "to_id"],
    )

    pd.testing.assert_frame_equal(_plain(result), _plain(expected))


def test_links_level0(example_properties):

    # The default cols are ["path", "segment"]
    result = distill.links(example_properties, properties_type="topics", level=0)

    # TODO: to_id returns only the original ones. Return the ancestor id instead, if levelup is used.
    expected = pd.DataFrame(
        [
            ("articles-1", "sections-1", "items-1", "s1", "Root", "Anna", "properties-4"),
            ("articles-1", "sections-1", "items-2", "s1", "Root", "Bernd", "properties-4"),
        ],
        columns=["articles_id", "sections_id", "items_id", "from_tagid", "path", "segment", "to_id"],
    )

    pd.testing.assert_frame_equal(_plain(result), _plain(expected))


def test_links_segment(example_properties):
    result = distill.links(example_properties, properties_type="topics", cols=["path", "segment"])

    expected = pd.DataFrame(
        [
            ("articles-1", "sections-1", "items-1", "s1", "Root", "Anna", "properties-4"),
            ("articles-1", "sections-1", "items-2", "s1", "Root", "Bernd", "properties-4"),
        ],
        columns=["articles_id", "sections_id", "items_id", "from_tagid", "path", "segment", "to_id"],
    )

    pd.testing.assert_frame_equal(_plain(result), _plain(expected))


# --- segment extraction -----------------------------------------------------

def test_segment():
    result = distill.extract_segment('<seg id="s1">Hello</seg> world', "s1")
    assert result == "Hello"


def test_untagged():
    result = distill.extract_untagged('<seg id="s1">Hello</seg> world')
    assert result == "world"


def test_segment_invalid():
    assert distill.extract_segment("not valid <xml", "s1") == ""


def test_segment_missing():
    assert distill.extract_segment('<seg id="s1">Hello</seg>', "") == ""
