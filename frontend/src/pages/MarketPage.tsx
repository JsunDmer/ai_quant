import { useEffect, useMemo, useState } from 'react';
import type { EChartsOption } from 'echarts';
import { Activity, Clock, Globe, Newspaper, Search, TrendingUp, AlertCircle, Filter, TrendingDown, Minus, Tag } from 'lucide-react';
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
  const [newsCategory, setNewsCategory] = useState<string>('全部');
  const [newsSentiment, setNewsSentiment] = useState<string>('全部');
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

  const filteredNews = useMemo(() => {
    return data ? filterNews(data.news, newsCategory, newsSentiment, newsQuery) : [];
  }, [data, newsCategory, newsSentiment, newsQuery]);

  const newsCategoryOptions = useMemo(() => {
    return data ? buildNewsCategories(data.news) : ['全部'];
  }, [data]);

  const northFlow = useMemo(() => parseNorthFlow(data?.north_flow), [data?.north_flow]);
  const marketMovers = useMemo(() => parseMarketMovers(data?.market_movers), [data?.market_movers]);

  useEffect(() => {
    if (!newsCategoryOptions.includes(newsCategory)) {
      setNewsCategory('全部');
    }
  }, [newsCategory, newsCategoryOptions]);

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
          <Metric icon={<TrendingUp size={20} color="var(--accent-red)" />} label="北向资金" value={formatSignedNumber(northFlow.north)} />
          <Metric icon={<TrendingDown size={20} color="var(--accent-green)" />} label="南向资金" value={formatSignedNumber(northFlow.south)} />
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
            padding: '20px 24px',
            borderRadius: 'var(--radius-lg)',
            display: 'grid',
            gridTemplateColumns: 'minmax(260px, 1fr) minmax(320px, 1.4fr)',
            gap: 16,
          }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 600, fontSize: 15, color: 'var(--text-primary)' }}>
              <TrendingUp size={16} color="var(--accent-red)" />
              <span>港股通资金流向</span>
            </div>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
              <div>北向：<span style={{ color: northFlow.north >= 0 ? 'var(--accent-red)' : 'var(--accent-green)', fontWeight: 600 }}>{formatSignedNumber(northFlow.north)}</span></div>
              <div>南向：<span style={{ color: northFlow.south >= 0 ? 'var(--accent-red)' : 'var(--accent-green)', fontWeight: 600 }}>{formatSignedNumber(northFlow.south)}</span></div>
              <div style={{ marginTop: 6, fontSize: 12, color: 'var(--text-muted)' }}>
                交易日：{northFlow.tradeDate || data.trade_date || '—'} · 来源：{northFlow.source || 'snapshot'}
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 600, fontSize: 15, color: 'var(--text-primary)' }}>
                <Activity size={16} color="var(--accent-blue)" />
                <span>关注池实时异动</span>
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                {marketMovers.length}/{typeof data.watchlist_size === 'number' ? data.watchlist_size : marketMovers.length}
              </div>
            </div>
            {marketMovers.length > 0 ? (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 8 }}>
                {marketMovers.slice(0, 6).map((item, idx) => (
                  <div
                    key={`${item.tsCode}-${idx}`}
                    style={{
                      display: 'grid',
                      gridTemplateColumns: 'minmax(96px, 1.4fr) minmax(84px, 1fr) minmax(64px, 0.8fr)',
                      gap: 8,
                      alignItems: 'center',
                      padding: '8px 10px',
                      borderRadius: 8,
                      border: '1px solid var(--border-color)',
                      background: 'var(--bg-secondary)',
                    }}
                  >
                    <div style={{ display: 'flex', flexDirection: 'column', minWidth: 0 }}>
                      <span style={{ fontSize: 13, color: 'var(--text-primary)', fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {item.name || item.tsCode}
                      </span>
                      <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: '"JetBrains Mono", ui-monospace, monospace' }}>
                        {item.tsCode}
                      </span>
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)', fontFamily: '"JetBrains Mono", ui-monospace, monospace' }}>
                      {item.price > 0 ? item.price.toFixed(2) : '—'}
                    </div>
                    <div style={{ fontSize: 12, fontWeight: 600, color: item.pctChange > 0 ? 'var(--accent-red)' : item.pctChange < 0 ? 'var(--accent-green)' : 'var(--text-muted)', fontFamily: '"JetBrains Mono", ui-monospace, monospace', textAlign: 'right' }}>
                      {formatSignedPercent(item.pctChange)}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ padding: '18px 12px', borderRadius: 8, border: '1px dashed var(--border-color)', color: 'var(--text-muted)', fontSize: 12 }}>
                暂无实时异动数据（请确认已配置 `TUSHARE_TOKEN`，且关注池中存在股票）。
              </div>
            )}
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
                    value={newsCategory}
                    onChange={(e) => setNewsCategory(e.target.value)}
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
                    {newsCategoryOptions.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </div>
                <div style={{ position: 'relative' }}>
                  <div style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none' }}>
                    <TrendingUp size={14} color="var(--text-secondary)" />
                  </div>
                  <select
                    className="form-control"
                    value={newsSentiment}
                    onChange={(e) => setNewsSentiment(e.target.value)}
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
                    {buildNewsSentiments().map((s) => (
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
                    placeholder="搜索标题/内容/板块"
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
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 500, background: 'var(--bg-secondary)', padding: '6px 12px', borderRadius: '999px' }}>
                    {filteredNews.length}/{data.news.length}
                  </div>
                  {(newsCategory !== '全部' || newsSentiment !== '全部' || newsQuery.trim()) ? (
                    <button
                      type="button"
                      onClick={() => {
                        setNewsCategory('全部');
                        setNewsSentiment('全部');
                        setNewsQuery('');
                      }}
                      style={{
                        border: '1px solid var(--border-color)',
                        background: 'var(--bg-secondary)',
                        color: 'var(--text-secondary)',
                        borderRadius: '999px',
                        padding: '6px 12px',
                        fontSize: 12,
                        fontWeight: 500,
                        cursor: 'pointer',
                      }}
                    >
                      清除筛选
                    </button>
                  ) : null}
                </div>
              </div>
            )}
          </div>

          {Array.isArray(data.news) && data.news.length > 0 ? (
            filteredNews.length > 0 ? (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: 16, alignItems: 'start' }}>
                {filteredNews
                  .slice(0, 20)
                  .map((n, idx) => (
                    <NewsCard key={buildNewsCardKey(n, idx)} item={n} />
                ))}
              </div>
            ) : (
              <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', border: '1px dashed var(--border-color)' }}>
                当前筛选条件下没有匹配新闻，可尝试清除筛选后重新查看。
              </div>
            )
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

function toNumber(raw: unknown, fallback = 0): number {
  if (typeof raw === 'number' && Number.isFinite(raw)) return raw;
  if (typeof raw === 'string') {
    const n = Number(raw);
    if (Number.isFinite(n)) return n;
  }
  return fallback;
}

function formatSignedNumber(value: number): string {
  if (!Number.isFinite(value)) return '—';
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}`;
}

function formatSignedPercent(value: number): string {
  if (!Number.isFinite(value)) return '—';
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}

function parseNorthFlow(raw: unknown): { north: number; south: number; tradeDate: string; source: string } {
  const r = typeof raw === 'object' && raw ? (raw as Record<string, unknown>) : {};
  const north = toNumber(r.north_money ?? r.north, 0);
  const south = toNumber(r.south_money ?? r.south, 0);
  return {
    north,
    south,
    tradeDate: String(r.trade_date ?? ''),
    source: String(r.source ?? ''),
  };
}

function parseMarketMovers(raw: unknown): Array<{ tsCode: string; name: string; price: number; pctChange: number }> {
  if (!Array.isArray(raw)) return [];
  return raw
    .map((item) => {
      const r = typeof item === 'object' && item ? (item as Record<string, unknown>) : {};
      const tsCode = String(r.ts_code ?? r.tsCode ?? '').trim();
      if (!tsCode) return null;
      return {
        tsCode,
        name: String(r.name ?? '').trim(),
        price: toNumber(r.price, 0),
        pctChange: toNumber(r.pct_change ?? r.pctChange, 0),
      };
    })
    .filter(Boolean) as Array<{ tsCode: string; name: string; price: number; pctChange: number }>;
}

function formatRelativeTime(timeStr: string): string {
  if (!timeStr) return '';
  const date = new Date(timeStr);
  if (isNaN(date.getTime())) return timeStr;
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  if (diffMs < 0) return formatAbsoluteTime(date);
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  
  if (diffMins < 60) return `${Math.max(1, diffMins)}分钟前`;
  if (diffHours < 24) return `${diffHours}小时前`;
  return formatAbsoluteTime(date);
}

function formatAbsoluteTime(date: Date): string {
  return `${date.getMonth() + 1}-${date.getDate()} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
}

function NewsCard(props: { item: unknown }) {
  const r = typeof props.item === 'object' && props.item ? (props.item as Record<string, unknown>) : {};
  const title = String(r.title ?? r.标题 ?? r.headline ?? r.name ?? '—');
  const content = String(r.content ?? r.内容 ?? r.text ?? '');
  const summary = String(r.summary ?? r.摘要 ?? r.snippet ?? r.brief ?? content).trim();
  const time = String(r.time ?? r.时间 ?? r.published_at ?? r.publishedAt ?? r.date ?? '').trim();
  const source = String(r.source ?? r.来源 ?? r.site ?? '').trim();
  const category = String(r.category ?? '未分类');
  const url = (r.url ?? r.link ?? r.source_url ?? r.sourceUrl ?? r.href) as unknown;
  const href = typeof url === 'string' && url.startsWith('http') ? url : null;
  const host = href ? safeHostname(href) : '';
  const sentiment = normalizeSentiment(r.sentiment);
  
  const relatedSectors = parseStringArray(r.related_sectors ?? r.related_sectors_json);

  return (
    <div
      className="surface-card"
      style={{
        borderRadius: 'var(--radius-md)',
        padding: '20px',
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
        position: 'relative'
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <Chip icon={<Tag size={12} />}>{`分类：${category}`}</Chip>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 4,
              padding: '4px 8px',
              borderRadius: 6,
              fontSize: 11,
              fontWeight: 600,
              color: sentiment.color,
              background: sentiment.background,
              border: '1px solid var(--border-color)',
              whiteSpace: 'nowrap',
            }}
          >
            {sentiment.icon}
            <span>{`情绪：${sentiment.label}`}</span>
          </div>
          {time ? <Chip icon={<Clock size={12} />}>{formatRelativeTime(time)}</Chip> : null}
        </div>
      </div>

      <div style={{ fontWeight: 600, fontSize: 16, lineHeight: 1.45, color: 'var(--text-primary)' }}>
        {href ? (
          <a href={href} target="_blank" rel="noreferrer" style={{ textDecoration: 'none', color: 'inherit', transition: 'color 0.2s' }} onMouseOver={(e) => e.currentTarget.style.color = 'var(--accent-blue)'} onMouseOut={(e) => e.currentTarget.style.color = 'inherit'}>
            {title}
          </a>
        ) : (
          title
        )}
      </div>
      
      {summary ? (
        <div style={{ 
          fontSize: 13, 
          color: 'var(--text-secondary)', 
          lineHeight: 1.6,
          display: '-webkit-box',
          WebkitLineClamp: 3,
          WebkitBoxOrient: 'vertical',
          overflow: 'hidden',
          textOverflow: 'ellipsis'
        }}>
          {summary}
        </div>
      ) : null}

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 'auto', paddingTop: 8 }}>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {relatedSectors.slice(0, 3).map((sec, i) => (
            <span key={i} style={{ fontSize: 11, color: 'var(--accent-blue)', background: 'var(--accent-blue-dim)', padding: '2px 8px', borderRadius: 4, fontWeight: 500 }}>
              {sec}
            </span>
          ))}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--text-muted)' }}>
          {host ? <><Globe size={11} /> {host}</> : source ? <><Newspaper size={11} /> {source}</> : null}
        </div>
      </div>
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

function parseStringArray(raw: unknown): string[] {
  if (Array.isArray(raw)) {
    return raw.map(String).map((v) => v.trim()).filter(Boolean);
  }
  if (typeof raw !== 'string' || !raw.trim()) return [];
  try {
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) {
      return parsed.map(String).map((v) => v.trim()).filter(Boolean);
    }
  } catch {
    return [raw.trim()];
  }
  return [];
}

function buildNewsCardKey(item: unknown, index: number): string {
  const r = typeof item === 'object' && item ? (item as Record<string, unknown>) : {};
  const url = String(r.url ?? r.link ?? r.source_url ?? r.sourceUrl ?? '').trim();
  const title = String(r.title ?? r.标题 ?? r.headline ?? r.name ?? '').trim();
  const time = String(r.time ?? r.时间 ?? r.published_at ?? r.publishedAt ?? r.date ?? '').trim();
  return url || `${title || 'news'}-${time || index}`;
}

function normalizeSentiment(raw: unknown): {
  label: string;
  bucket: string;
  color: string;
  background: string;
  icon: React.ReactNode;
} {
  const value = String(raw ?? 'neutral').trim().toLowerCase();
  const positiveHints = ['positive', 'bullish', '看多', '利多', '偏多', '多头', '多頭', '看涨', '看漲'];
  const negativeHints = ['negative', 'bearish', '看空', '利空', '偏空', '空头', '空頭', '看跌'];

  if (positiveHints.some((hint) => value === hint || value.includes(hint))) {
    return {
      label: '利多',
      bucket: '利多',
      color: 'var(--accent-red)',
      background: 'var(--accent-red-dim)',
      icon: <TrendingUp size={14} strokeWidth={2.5} />,
    };
  }

  if (negativeHints.some((hint) => value === hint || value.includes(hint))) {
    return {
      label: '利空',
      bucket: '利空',
      color: 'var(--accent-green)',
      background: 'var(--accent-green-dim)',
      icon: <TrendingDown size={14} strokeWidth={2.5} />,
    };
  }

  return {
    label: '中性',
    bucket: '中性',
    color: 'var(--text-muted)',
    background: 'var(--bg-secondary)',
    icon: <Minus size={14} strokeWidth={2.5} />,
  };
}

function Chip(props: { icon?: React.ReactNode; children: string }) {
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        padding: '4px 8px',
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

function buildNewsCategories(news: unknown[]): string[] {
  const categories = new Set<string>();
  for (const n of news) {
    const r = typeof n === 'object' && n ? (n as Record<string, unknown>) : {};
    const c = String(r.category ?? '未分类').trim();
    if (c) categories.add(c);
  }
  return ['全部', ...Array.from(categories).sort((a, b) => a.localeCompare(b))];
}

function buildNewsSentiments(): string[] {
  return ['全部', '利多', '利空', '中性'];
}

function filterNews(news: unknown[], category: string, sentiment: string, query: string): unknown[] {
  const q = query.trim().toLowerCase();
  return news
    .slice()
    .filter((n) => {
      const r = typeof n === 'object' && n ? (n as Record<string, unknown>) : {};
      const c = String(r.category ?? '未分类').trim();
      if (category !== '全部' && c !== category) return false;
      const s = normalizeSentiment(r.sentiment).bucket;
      if (sentiment !== '全部' && s !== sentiment) return false;
      if (!q) return true;
      const title = String(r.title ?? r.标题 ?? '').toLowerCase();
      const content = String(r.content ?? r.内容 ?? r.text ?? r.summary ?? r.摘要 ?? '').toLowerCase();
      const relSectors = Array.isArray(r.related_sectors) ? r.related_sectors.join(',').toLowerCase() : String(r.related_sectors ?? '').toLowerCase();
      return title.includes(q) || content.includes(q) || relSectors.includes(q);
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