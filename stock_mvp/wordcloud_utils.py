from __future__ import annotations

import math
import importlib
import re
from collections import Counter
from typing import Callable, Iterable, List, Sequence, Set, Tuple

import plotly.graph_objects as go


TokenizeFn = Callable[[str], Iterable[str]]


_DEFAULT_STOPWORDS: Set[str] = {
    "的",
    "是",
    "在",
    "了",
    "和",
    "与",
    "或",
    "等",
    "及",
    "对",
    "为",
    "有",
    "这",
    "那",
    "上",
    "下",
    "中",
    "而",
    "被",
    "将",
    "把",
}


def extract_keywords(
    texts: Sequence[str],
    *,
    tokenize: TokenizeFn | None = None,
    stopwords: Set[str] | None = None,
    min_len: int = 2,
    top_n: int = 40,
) -> List[Tuple[str, int]]:
    if stopwords is None:
        stopwords = set(_DEFAULT_STOPWORDS)
    else:
        stopwords = set(stopwords)

    if tokenize is None:
        tokenize = _default_tokenize

    counter: Counter[str] = Counter()
    for text in texts:
        if not text:
            continue
        for token in tokenize(text):
            tok = (token or "").strip()
            if not tok:
                continue
            if tok in stopwords:
                continue
            if len(tok) < min_len:
                continue
            counter[tok] += 1

    items = list(counter.items())
    items.sort(key=lambda kv: (-kv[1], kv[0]))
    return items[: max(0, int(top_n))]


def generate_spiral_positions(n: int, *, scale: float = 0.1) -> List[Tuple[float, float]]:
    """Generate positions using an Archimedean spiral with wider spacing."""
    n = max(0, int(n))
    golden_angle = math.pi * (3 - math.sqrt(5))
    out: List[Tuple[float, float]] = []
    for i in range(n):
        if i == 0:
            out.append((0.0, 0.0))
            continue
        theta = i * golden_angle
        r = math.sqrt(i) * float(scale)
        out.append((r * math.cos(theta), r * math.sin(theta)))
    return out


# 词云配色方案：按权重梯度分配颜色
_WORDCLOUD_COLORS = [
    "#1e40af",  # 深蓝 - 最高权重
    "#2563eb",  # 蓝
    "#3b82f6",  # 中蓝
    "#0891b2",  # 青
    "#0d9488",  # 蓝绿
    "#059669",  # 绿
    "#6366f1",  # 靛蓝
    "#7c3aed",  # 紫
    "#8b5cf6",  # 浅紫
    "#64748b",  # 灰蓝 - 最低权重
]


def build_plotly_wordcloud_figure(
    keywords: Sequence[Tuple[str, int]],
    *,
    height: int = 420,
    min_font: float = 14.0,
    max_font: float = 40.0,
    font_color: str = "#3b82f6",
) -> go.Figure:
    # 限制关键词数量，避免过于密集
    keywords = list(keywords)[:20]

    words = [w for w, _ in keywords]
    freqs = [int(f) for _, f in keywords]

    if not words:
        fig = go.Figure()
        fig.update_layout(height=200, margin={"l": 0, "r": 0, "t": 0, "b": 0})
        return fig

    # 使用网格布局代替螺旋，避免重叠
    n = len(words)
    cols = min(5, n)
    rows = math.ceil(n / cols)

    xs: List[float] = []
    ys: List[float] = []
    for i in range(n):
        row = i // cols
        col = i % cols
        # 奇数行微偏移，避免对齐过于死板
        x_offset = 0.15 if row % 2 == 1 else 0.0
        xs.append(col * 1.0 + x_offset)
        ys.append(-row * 1.0)  # 从上往下

    # 字体大小：按权重比例缩放，但压缩范围使所有词都可读
    max_freq = max(freqs) or 1
    min_freq = min(freqs) or 1
    span = max(0.0, float(max_font) - float(min_font))
    sizes: List[float] = []
    for f in freqs:
        if max_freq == min_freq:
            ratio = 0.5
        else:
            ratio = (float(f) - min_freq) / (max_freq - min_freq)
        sizes.append(float(min_font) + ratio * span)

    # 按权重梯度分配颜色
    colors: List[str] = []
    n_colors = len(_WORDCLOUD_COLORS)
    for i in range(n):
        color_idx = min(int(i / n * n_colors), n_colors - 1)
        colors.append(_WORDCLOUD_COLORS[color_idx])

    fig = go.Figure(
        data=[
            go.Scatter(
                x=xs,
                y=ys,
                mode="text",
                text=words,
                textposition="middle center",
                textfont={"size": sizes, "color": colors, "family": "Noto Sans SC, sans-serif"},
                customdata=freqs,
                hovertemplate="<b>%{text}</b><br>权重: %{customdata}<extra></extra>",
            )
        ]
    )

    # 动态计算高度
    actual_height = max(200, min(int(height), rows * 80 + 40))

    fig.update_layout(
        height=actual_height,
        margin={"l": 20, "r": 20, "t": 15, "b": 15},
        plot_bgcolor="white",
        paper_bgcolor="white",
        hovermode="closest",
        showlegend=False,
    )
    fig.update_xaxes(visible=False, range=[-0.5, cols - 0.3])
    fig.update_yaxes(visible=False, range=[-(rows - 0.3), 0.5])
    return fig


def _default_tokenize(text: str) -> Iterable[str]:
    try:
        jieba = importlib.import_module("jieba")
        return jieba.cut(text, cut_all=False)
    except Exception:
        return (t for t in re.split(r"[^0-9A-Za-z\u4e00-\u9fff]+", text) if t)


def extract_keywords_from_ai_news(ai_news_list: List[dict], top_n: int = 35) -> List[Tuple[str, int]]:
    """
    从AI生成的新闻中提取关键词
    
    使用AI生成的keywords字段，结合importance权重计算
    
    Args:
        ai_news_list: AI生成的新闻列表（dict列表）
        top_n: 返回关键词数量
    
    Returns:
        [(关键词, 权重), ...] 按权重降序
    """
    import json
    
    keyword_weights = {}
    
    for news in ai_news_list:
        # 获取重要性权重
        importance = news.get('importance', 5)
        
        # 从keywords_json字段提取关键词
        keywords_json = news.get('keywords_json', '[]')
        try:
            keywords = json.loads(keywords_json) if isinstance(keywords_json, str) else keywords_json
        except:
            keywords = []
        
        # 累加权重
        for kw in keywords:
            if kw and isinstance(kw, str):
                keyword_weights[kw] = keyword_weights.get(kw, 0) + importance
    
    # 按权重排序
    sorted_keywords = sorted(keyword_weights.items(), key=lambda x: x[1], reverse=True)
    return sorted_keywords[:top_n]
