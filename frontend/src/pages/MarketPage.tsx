import { useEffect, useMemo, useState } from 'react';
import type { EChartsOption } from 'echarts';
import { Activity, Clock, Globe, Newspaper, Search, TrendingUp, ChevronDown, ChevronUp, AlertCircle, Filter } from 'lucide-react';
import { ApiError, apiGet } from '../api/client';
import type { MarketLatestResponse } from '../api/types';
import { PageHeader } from '../app/layout/PageHeader';
import { EChart } from '../charts/EChart';
import { getChartTokens, type ChartPalette } from '../charts/chartTokens';
import type { UiTokens } from '../charts/tokens';

function Spinner() {
  return (
    <div className="ui-state ui-state--muted" style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '16px 18px', background: 'var(--bg-card)', backdropFilter: 'var(--glass-blur)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-lg)' }}>
      <div
        style={{
          width: 20,
          height: 20,
          border: '2px solid var(--border-color)',
          borderTopColor: 'var(--accent-blue)',
          borderRadius: '50%',
          animation: 'spin 0.8s linear infinite',
        }}
      />
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
      <span style={{ fontSize: 14, color: 'var(--text-secondary)', fontWeight: 500 }}>正在加载市场数据...</span>
    </div>
  );
}

export function MarketPage(props: { refreshKey: number; chartPalette: ChartPalette }) {
  const [data, setData] = useState<MarketLatestResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [newsSource, setNewsSource] = useState<string>('全部');
  const [newsQuery, setNewsQuery] = useState<string>('');

  const { chartOption: indicesChartOption, chartIsPlaceholder } = useMemo(() => {
    const tokens = getChartTokens(props.chartPalette);
    if (data) {
      const opt = buildIndicesChangeOption(data.indices, tokens);
      const x = opt.xAxis as { data?: unknown[] };
      if (Array.isArray(x?.data) && x.data.length > 0) {
        return { chartOption: opt, chartIsPlaceholder: false };
      }
    }
    return { chartOption: buildChartThemePreviewOption(tokens), chartIsPlaceholder: true };
  }, [data, props.chartPalette]);

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
          setError('暂无市场快照数据。下方指数图仍可先预览图表配色；需要真实数据时在侧栏点击「执行分析」即可。');
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
    <div className="page-enter" style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <PageHeader title="市场分析" subtitle={data ? `交易日：${data.trade_date}` : undefined} />

      {loading ? <Spinner /> : null}

      {error ? (
        <div className="ui-state ui-state--error" style={{ display: 'flex', alignItems: 'center', gap: 8, borderRadius: 'var(--radius-lg)' }}>
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      ) : null}

      {data ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
          <Metric icon={<TrendingUp size={20} color="var(--accent-blue)" />} label="指数条目" value={String(Array.isArray(data.indices) ? data.indices.length : 0)} />
          <Metric icon={<Newspaper size={20} color="var(--accent-purple)" />} label="新闻条目" value={String(Array.isArray(data.news) ? data.news.length : 0)} />
          <Metric icon={<Activity size={20} color="var(--accent-green)" />} label="市场状态" value={data.status || 'Active'} />
        </div>
      ) : null}

      {!loading ? (
        <div
          className="surface-card"
          style={{
            padding: '20px 24px',
            borderRadius: 'var(--radius-lg)',
            display: 'flex',
            flexDirection: 'column',
            gap: 12
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 600, fontSize: 16, color: 'var(--text-primary)' }}>
            <Activity size={18} color="var(--accent-blue)" />
            <span>指数涨跌走势</span>
          </div>
          <EChart chartPalette={props.chartPalette} option={indicesChartOption} style={{ height: 320 }} />
          <div style={{ marginTop: 6, fontSize: 12, color: 'var(--text-secondary)' }}>
            {chartIsPlaceholder
              ? '当前为示意图，仅用于预览配色。有市场快照后将自动切换为真实指数。'
              : '展示今日各大指数涨跌幅，自动过滤缺失字段的数据。'}
          </div>
        </div>
      ) : null}

      {data ? (
        <div
          className="surface-card"
          style={{
            padding: '24px',
            borderRadius: 'var(--radius-lg)',
            display: 'flex',
            flexDirection: 'column',
            gap: 20
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 600, fontSize: 16, color: 'var(--text-primary)' }}>
              <Newspaper size={18} color="var(--accent-purple)" />
              <span>今日新闻洞察</span>
            </div>
            
            {Array.isArray(data.news) && data.news.length > 0 && (
              <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
                <div style={{ position: 'relative' }}>
                  <div style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none' }}>
                    <Filter size={14} color="var(--text-secondary)" />
                  </div>
                  <select
                    className="form-control"
                    value={newsSource}
                    onChange={(e) => setNewsSource(e.target.value)}
                    style={{
                      background: 'var(--bg-secondary)',
                      color: 'var(--text-primary)',
                      border: '1px solid var(--border-color)',
                      borderRadius: 'var(--radius-md)',
                      padding: '8px 32px',
                      fontSize: 13,
                      appearance: 'none',
                      cursor: 'pointer',
                      minWidth: '120px'
                    }}
                  >
                    {buildNewsSources(data.news).map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </div>
                <div style={{ position: 'relative' }}>
                  <div style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none' }}>
                    <Search size={14} color="var(--text-secondary)" />
                  </div>
                  <input
                    className="form-control"
                    value={newsQuery}
                    onChange={(e) => setNewsQuery(e.target.value)}
                    placeholder="搜索标题/内容"
                    style={{
                      background: 'var(--bg-secondary)',
                      color: 'var(--text-primary)',
                      border: '1px solid var(--border-color)',
                      borderRadius: 'var(--radius-md)',
                      padding: '8px 12px 8px 32px',
                      fontSize: 13,
                      outline: 'none',
                      width: '220px'
                    }}
                  />
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 500, background: 'var(--bg-secondary)', padding: '6px 12px', borderRadius: '999px' }}>
                  {filterNews(data.news, newsSource, newsQuery).length}/{data.news.length}
                </div>
              </div>
            )}
          </div>

          {Array.isArray(data.news) && data.news.length > 0 ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 16 }}>
              {filterNews(data.news, newsSource, newsQuery)
                .slice(0, 20)
                .map((n, idx) => (
                  <NewsCard key={idx} item={n} />
              ))}
            </div>
          ) : (
            <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', border: '1px dashed var(--border-color)' }}>
              暂无新闻数据（可能是当天采集为空或未开启相关数据源）。
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}

function Metric(props: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div
      className="surface-card surface-card--raised"
      style={{
        borderRadius: 'var(--radius-lg)',
        padding: '20px 24px',
        display: 'flex',
        alignItems: 'center',
        gap: 16
      }}
    >
      <div style={{ padding: 12, background: 'var(--bg-secondary)', borderRadius: 12, border: '1px solid var(--border-color)' }}>
        {props.icon}
      </div>
      <div>
        <div style={{ color: 'var(--text-secondary)', fontSize: 12, fontWeight: 500, textTransform: 'uppercase', letterSpacing: 0.5 }}>
          {props.label}
        </div>
        <div style={{ marginTop: 4, color: 'var(--text-primary)', fontFamily: '"JetBrains Mono", ui-monospace, monospace', fontWeight: 600, fontSize: 24, lineHeight: 1.1 }}>
          {props.value}
        </div>
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
  const host = href ? safeHostname(href) : '';
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className="surface-card"
      style={{
        borderRadius: 'var(--radius-md)',
        padding: '20px',
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
        height: '100%'
      }}
    >
      <div style={{ fontWeight: 600, fontSize: 15, lineHeight: 1.5, color: 'var(--text-primary)' }}>
        {href ? (
          <a href={href} target="_blank" rel="noreferrer" style={{ textDecoration: 'none', color: 'inherit', transition: 'color 0.2s' }} onMouseOver={(e) => e.currentTarget.style.color = 'var(--accent-blue)'} onMouseOut={(e) => e.currentTarget.style.color = 'inherit'}>
            {title}
          </a>
        ) : (
          title
        )}
      </div>
      
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        {source ? <Chip icon={<Newspaper size={12} />}>{source}</Chip> : null}
        {time ? <Chip icon={<Clock size={12} />}>{time}</Chip> : null}
        {host ? <Chip icon={<Globe size={12} />}>{host}</Chip> : null}
      </div>
      
      {summary ? (
        <div style={{ 
          fontSize: 13, 
          color: 'var(--text-secondary)', 
          lineHeight: 1.6,
          flexGrow: 1,
          marginTop: 4,
          position: 'relative'
        }}>
          {expanded ? summary : summary.slice(0, 120) + (summary.length > 120 ? '...' : '')}
          
          {summary.length > 120 && (
            <button
              onClick={() => setExpanded((v) => !v)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 4,
                marginTop: 12,
                background: 'transparent',
                border: 'none',
                color: 'var(--accent-blue)',
                padding: '4px 0',
                fontSize: 13,
                fontWeight: 500,
                cursor: 'pointer',
                transition: 'color 0.2s'
              }}
              onMouseOver={(e) => e.currentTarget.style.color = 'var(--accent-cyan)'}
              onMouseOut={(e) => e.currentTarget.style.color = 'var(--accent-blue)'}
            >
              {expanded ? <><ChevronUp size={14} /> 收起全文</> : <><ChevronDown size={14} /> 展开阅读</>}
            </button>
          )}
        </div>
      ) : null}
    </div>
  );
}

function safeHostname(href: string): string {
  try {
    return new URL(href).hostname;
  } catch {
    return '';
  }
}

function Chip(props: { icon?: React.ReactNode; children: string }) {
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        padding: '4px 10px',
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border-color)',
        borderRadius: 6,
        fontSize: 11,
        fontWeight: 500,
        color: 'var(--text-secondary)',
      }}
    >
      {props.icon}
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

function buildChartThemePreviewOption(tokens: UiTokens): EChartsOption {
  return {
    title: {
      text: '暂无指数快照 · 示意柱预览',
      left: 'center',
      top: 6,
      textStyle: { color: tokens.textMuted, fontSize: 13, fontWeight: 500 },
    },
    grid: { left: 48, right: 16, top: 40, bottom: 40 },
    xAxis: {
      type: 'category' as const,
      data: ['上证指数', '深证成指', '创业板指'],
      axisLabel: { color: tokens.textSecondary, margin: 12 },
      axisLine: { lineStyle: { color: tokens.borderColor } },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value' as const,
      min: -1.5,
      max: 1.5,
      axisLabel: { color: tokens.textSecondary },
      splitLine: { lineStyle: { color: tokens.borderColor, type: 'dashed' } },
    },
    tooltip: { 
      trigger: 'axis' as const,
      backgroundColor: tokens.bgCard,
      borderColor: tokens.borderColor,
      textStyle: { color: tokens.textPrimary },
      padding: [10, 14],
      borderRadius: 8
    },
    series: [
      {
        type: 'bar' as const,
        barWidth: '40%',
        itemStyle: { borderRadius: [4, 4, 0, 0] },
        data: [
          { value: 1.0, itemStyle: { color: tokens.accentRed } },
          { value: -0.6, itemStyle: { color: tokens.accentGreen } },
          { value: 0.2, itemStyle: { color: tokens.accentRed } },
        ],
      },
    ],
  };
}

function buildIndicesChangeOption(indices: unknown[], tokens: UiTokens): EChartsOption {
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
      axisLabel: { color: tokens.textSecondary, margin: 12, interval: 0, rotate: names.length > 5 ? 30 : 0 },
      axisLine: { lineStyle: { color: tokens.borderColor } },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value' as const,
      axisLabel: { color: tokens.textSecondary, formatter: '{value}%' },
      splitLine: { lineStyle: { color: tokens.borderColor, type: 'dashed' } },
    },
    tooltip: { 
      trigger: 'axis' as const,
      backgroundColor: tokens.bgCard,
      borderColor: tokens.borderColor,
      textStyle: { color: tokens.textPrimary },
      padding: [10, 14],
      borderRadius: 8,
      formatter: (params: any) => {
        const p = params[0];
        const val = p.value;
        const color = val > 0 ? tokens.accentRed : val < 0 ? tokens.accentGreen : tokens.textMuted;
        return `<div style="display:flex;align-items:center;gap:8px;">
          <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${color}"></span>
          <span style="font-weight:600">${p.name}</span>
          <span style="color:${color};font-weight:600;margin-left:8px">${val > 0 ? '+' : ''}${val}%</span>
        </div>`;
      }
    },
    series: [
      {
        type: 'bar' as const,
        barWidth: '40%',
        itemStyle: { borderRadius: [4, 4, 0, 0] },
        data: values.map((v) => ({
          value: v,
          itemStyle: {
            color: v > 0 ? tokens.accentRed : v < 0 ? tokens.accentGreen : tokens.textMuted,
          },
        })),
      },
    ],
  };
}