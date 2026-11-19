import pandas as pd
import pytest

from epygraf import distill


def test_articles(example_article):
    result = distill.articles(example_article, cols=["name"])

    # TODO: assert full expected output as in test_tree.py


def test_items(example_article):
    result = distill.items(example_article, cols=["content"], property_cols=["lemma"])

    # TODO: assert full expected output as in test_tree.py


def test_properties(example_article):
    result = distill.properties(example_article, type="topics")

    # TODO: assert full expected output as in test_tree.py

def test_properties_levelup1(example_properties):
    result = distill.properties(example_properties, type="topics", levelup=1)

    # TODO: assert full expected output as in test_tree.py

def test_properties_annos(example_properties):
    result = distill.properties(example_properties, type="topics", annos=True)

    # TODO: assert full expected output as in test_tree.py

# --- links ------------------------------------------------------------------

def test_links(example_article):
    result = distill.links(example_article, properties_type="topics")

    # TODO: assert full expected output as in test_tree.py

def test_links_level0(example_properties):
    result = distill.links(example_properties, properties_type="topics", level=0)

    # TODO: assert full expected output as in test_tree.py

def test_links_segment(example_properties):
    result = distill.links(example_properties, properties_type="topics", cols=["path", "segment"])

    # TODO: assert full expected output as in test_tree.py


# --- segment extraction -----------------------------------------------------

def test_segment():
    result = distill.extract_segment('<seg id="s1">Hello</seg> world', "s1")

    # TODO: assert full expected output

def test_untagged():
    result = distill.extract_untagged('<seg id="s1">Hello</seg> world')
    # TODO: assert full expected output


def test_segment_invalid():
    assert distill.extract_segment("not valid <xml", "s1") == ""


def test_segment_missing():
    assert distill.extract_segment('<seg id="s1">Hello</seg>', "") == ""
