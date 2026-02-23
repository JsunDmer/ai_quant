import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


def test_extract_keywords_respects_stopwords_and_min_len():
    from wordcloud_utils import extract_keywords

    texts = ["AI 投资 的 AI", "新能源 AI"]

    def tokenize(s: str):
        return s.split()

    keywords = extract_keywords(
        texts,
        tokenize=tokenize,
        stopwords={"的"},
        min_len=2,
        top_n=10,
    )

    assert ("AI", 3) in keywords
    assert ("新能源", 1) in keywords
    assert all(word != "的" for word, _ in keywords)


def test_generate_spiral_positions_deterministic():
    from wordcloud_utils import generate_spiral_positions

    positions = generate_spiral_positions(5, scale=0.1)
    assert len(positions) == 5
    assert positions[0] == (0.0, 0.0)


def test_build_plotly_wordcloud_figure_populates_text_and_sizes():
    from wordcloud_utils import build_plotly_wordcloud_figure

    keywords = [("AI", 10), ("新能源", 5)]
    fig = build_plotly_wordcloud_figure(keywords)

    assert len(fig.data) == 1
    trace = fig.data[0]
    assert list(trace.text) == ["AI", "新能源"]
    assert len(trace.textfont.size) == 2
