import { useEffect, useState } from 'react';
import { ApiError, apiGet } from '../api/client';
import type { MarketLatestResponse } from '../api/types';
import { PageHeader } from '../app/layout/PageHeader';
import { EChart } from '../charts/EChart';
import { readTokens } from '../charts/tokens';

export function MarketPage(props: { refreshKey: number }) {
  const [data, setData] = useState<MarketLatestResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [themeKey, setThemeKey] = useState<string>(() => document.documentElement.getAttribute('data-theme') ?? 'light');
  const [newsSource, setNewsSource] = useState<string>('全部');
  const [newsQuery, setNewsQuery] = useState<string>('');

  useEffect(() => {
    const el = document.documentElement;
    const mo = new MutationObserver(() => {
      setThemeKey(document.documentElement.getAttribute('data-theme') ?? 'light');
    });
    mo.observe(el, { attributes: true, attributeFilter: ['data-theme'] });
    return () => mo.disconnect();
  }, []);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(null);
    setData(null);

    apiGet<MarketLatestResponse>('/api/market/latest')
      .then((d) => {
        if (!alive) return;
        setData(d);
      })
      .catch((e) => {
        if (!alive) return;
        if (e instanceof ApiError && e.status === 404) {
          setError('暂无市场数据，请先点击侧边栏「执行分析」生成数据。');
        } else {
          setError('加载失败，请稍后重试。');
        }
      })
      .finally(() => {
        if (!alive) return;
        setLoading(false);
      });

    return () => {
      alive = false;
    };
  }, [props.refreshKey]);

  return (
    <div>
      <PageHeader title="市场分析" subtitle={data ? `交易日：${data.trade_date}` : undefined} />

      {loading ? (
        <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>加载中...</div>
      ) : null}

      {error ? (
        <div
          style={{
            marginTop: 12,
            padding: '12px 16px',
            background: 'var(--bg-card)',
            border: '1px solid var(--border-color)',
            borderRadius: 8,
            fontSize: 13,
            color: 'var(--text-secondary)',
          }}
        >
          {error}
        </div>
      ) : null}

      {data ? (
        <div
          style={{
            marginTop: 12,
            padding: '12px 16px',
            background: 'var(--bg-card)',
            border: '1px solid var(--border-color)',
            borderRadius: 8,
          }}
        >
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
            <Metric label="指数条目" value={String(Array.isArray(data.indices) ? data.indices.length : 0)} />
            <Metric label="新闻条目" value={String(Array.isArray(data.news) ? data.news.length : 0)} />
            <Metric label="状态" value={data.status} />
          </div>
        </div>
      ) : null}

      {data ? (
        <div
          style={{
            marginTop: 12,
            padding: '12px 16px',
            background: 'var(--bg-card)',
            border: '1px solid var(--border-color)',
            borderRadius: 8,
          }}
        >
          <div style={{ fontWeight: 600, marginBottom: 8 }}>今日新闻</div>
          {Array.isArray(data.news) && data.news.length > 0 ? (
            <>
              <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 10, flexWrap: 'wrap' }}>
                <label style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                  来源
                  <select
                    value={newsSource}
                    onChange={(e) => setNewsSource(e.target.value)}
                    style={{
                      marginLeft: 6,
                      background: 'var(--bg-secondary)',
                      color: 'var(--text-primary)',
                      border: '1px solid var(--border-color)',
                      borderRadius: 6,
                      padding: '6px 8px',
                      fontSize: 12,
                    }}
                  >
                    {buildNewsSources(data.news).map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </label>
                <input
                  value={newsQuery}
                  onChange={(e) => setNewsQuery(e.target.value)}
                  placeholder="搜索标题/内容"
                  style={{
                    flex: '1 1 220px',
                    background: 'var(--bg-secondary)',
                    color: 'var(--text-primary)',
                    border: '1px solid var(--border-color)',
                    borderRadius: 6,
                    padding: '8px 10px',
                    fontSize: 12,
                    outline: 'none',
                  }}
                />
                <div style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--text-muted)' }}>
                  {filterNews(data.news, newsSource, newsQuery).length}/{data.news.length}
                </div>
              </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 12 }}>
              {filterNews(data.news, newsSource, newsQuery)
                .slice(0, 20)
                .map((n, idx) => (
                  <NewsCard key={idx} item={n} />
              ))}
            </div>
            </>
          ) : (
            <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>暂无新闻数据（可能是当天采集为空或未开启相关数据源）。</div>
          )}
        </div>
      ) : null}

      {data ? (
        <div
          style={{
            marginTop: 12,
            padding: '12px 16px',
            background: 'var(--bg-card)',
            border: '1px solid var(--border-color)',
            borderRadius: 8,
          }}
        >
          <div style={{ fontWeight: 600, marginBottom: 8 }}>指数涨跌（示意）</div>
          <EChart option={buildIndicesChangeOption(data.indices, readTokens(), themeKey)} />
          <div style={{ marginTop: 6, fontSize: 12, color: 'var(--text-secondary)' }}>
            若某些指数字段缺失，会自动跳过；后续可按你确认的字段结构做严谨映射。
          </div>
        </div>
      ) : null}
    </div>
  );
}

function Metric(props: { label: string; value: string }) {
  return (
    <div
      style={{
        minWidth: 140,
        background: 'var(--bg-card)',
        border: '1px solid var(--border-color)',
        borderRadius: 8,
        padding: '12px 16px',
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      <div style={{ color: 'var(--text-secondary)', fontSize: 11, fontWeight: 500, letterSpacing: 0.3, textTransform: 'uppercase' }}>
        {props.label}
      </div>
      <div style={{ marginTop: 6, color: 'var(--text-primary)', fontFamily: '"JetBrains Mono", ui-monospace, monospace', fontWeight: 600, fontSize: 18 }}>
        {props.value}
      </div>
    </div>
  );
}

function NewsCard(props: { item: unknown }) {
  const r = typeof props.item === 'object' && props.item ? (props.item as Record<string, unknown>) : {};
  const title = String(r.title ?? r.标题 ?? r.headline ?? r.name ?? '—');
  const content = String(r.content ?? r.内容 ?? r.text ?? '');
  const summary = String(r.summary ?? r.摘要 ?? r.snippet ?? r.brief ?? content).trim();
  const time = String(r.time ?? r.时间 ?? r.published_at ?? r.publishedAt ?? r.date ?? '').trim();
  const source = String(r.source ?? r.来源 ?? r.site ?? '').trim();
  const url = (r.url ?? r.link ?? r.source_url ?? r.sourceUrl ?? r.href) as unknown;
  const href = typeof url === 'string' && url.startsWith('http') ? url : null;
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border-color)',
        borderRadius: 10,
        padding: '12px 14px',
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      <div style={{ fontWeight: 600, lineHeight: 1.35 }}>
        {href ? (
          <a href={href} target="_blank" rel="noreferrer">
            {title}
          </a>
        ) : (
          title
        )}
      </div>
      <div style={{ marginTop: 6, display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        {source ? <Chip>{source}</Chip> : null}
        {time ? <Chip>{time}</Chip> : null}
        {href ? <Chip>{new URL(href).hostname}</Chip> : null}
      </div>
      {summary ? (
        <div style={{ marginTop: 6, fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.45 }}>
          {expanded ? summary : summary.slice(0, 140) + (summary.length > 140 ? '…' : '')}
        </div>
      ) : null}
      {summary && summary.length > 140 ? (
        <button
          onClick={() => setExpanded((v) => !v)}
          style={{
            marginTop: 8,
            background: 'transparent',
            border: '1px solid var(--border-color)',
            color: 'var(--text-secondary)',
            borderRadius: 999,
            padding: '6px 10px',
            fontSize: 12,
            cursor: 'pointer',
          }}
        >
          {expanded ? '收起' : '展开'}
        </button>
      ) : null}
    </div>
  );
}

function Chip(props: { children: string }) {
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        padding: '3px 8px',
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border-color)',
        borderRadius: 999,
        fontSize: 12,
        color: 'var(--text-secondary)',
      }}
    >
      {props.children}
    </span>
  );
}

function buildNewsSources(news: unknown[]): string[] {
  const sources = new Set<string>();
  for (const n of news) {
    const r = typeof n === 'object' && n ? (n as Record<string, unknown>) : {};
    const s = String(r.source ?? r.来源 ?? r.site ?? '').trim();
    if (s) sources.add(s);
  }
  return ['全部', ...Array.from(sources).sort((a, b) => a.localeCompare(b))];
}

function filterNews(news: unknown[], source: string, query: string): unknown[] {
  const q = query.trim().toLowerCase();
  return news
    .slice()
    .filter((n) => {
      const r = typeof n === 'object' && n ? (n as Record<string, unknown>) : {};
      const s = String(r.source ?? r.来源 ?? r.site ?? '').trim();
      if (source !== '全部' && s !== source) return false;
      if (!q) return true;
      const title = String(r.title ?? r.标题 ?? '').toLowerCase();
      const content = String(r.content ?? r.内容 ?? r.text ?? r.summary ?? r.摘要 ?? '').toLowerCase();
      return title.includes(q) || content.includes(q);
    });
}

function buildIndicesChangeOption(
  indices: unknown[],
  tokens: ReturnType<typeof readTokens>,
  _themeKey: string
) {
  const rows = (Array.isArray(indices) ? indices : [])
    .map((x) => (typeof x === 'object' && x ? (x as Record<string, unknown>) : null))
    .filter(Boolean) as Record<string, unknown>[];

  const items = rows
    .map((r) => {
      const name = (r.name ?? r.指数 ?? r.index_name ?? r.symbol ?? '') as string;
      const raw = (r.change_pct ?? r.涨跌幅 ?? r.pct_change ?? r.changePercent ?? r.change ?? null) as unknown;
      const v = typeof raw === 'number' ? raw : typeof raw === 'string' ? Number(raw.replace('%', '')) : NaN;
      if (!name || !Number.isFinite(v)) return null;
      return { name, value: v };
    })
    .filter(Boolean) as { name: string; value: number }[];

  const names = items.map((i) => i.name);
  const values = items.map((i) => i.value);

  return {
    grid: { left: 48, right: 16, top: 20, bottom: 40 },
    xAxis: {
      type: 'category' as const,
      data: names,
      axisLabel: { color: tokens.textSecondary },
      axisLine: { lineStyle: { color: tokens.borderColor } },
    },
    yAxis: {
      type: 'value' as const,
      axisLabel: { color: tokens.textSecondary },
      splitLine: { lineStyle: { color: tokens.borderColor } },
    },
    tooltip: { trigger: 'axis' as const },
    series: [
      {
        type: 'bar' as const,
        data: values,
        itemStyle: {
          color: tokens.accentBlue,
        },
      },
    ],
  };
}

