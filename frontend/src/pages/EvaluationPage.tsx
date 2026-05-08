import { useEffect, useMemo, useState } from 'react';
import type { CSSProperties } from 'react';
import type { EChartsOption } from 'echarts';
import { apiGet, apiPost } from '../api/client';
import { PageHeader } from '../app/layout/PageHeader';
import { EChart } from '../charts/EChart';
import { getChartTokens, type ChartPalette } from '../charts/chartTokens';

type AccuracyBucket = {
  total?: number;
  correct?: number;
  accuracy?: number;
};

type SectorSummary = {
  t1?: AccuracyBucket;
  t3?: AccuracyBucket;
  t5?: AccuracyBucket;
};

type RecommendationBucket = {
  evaluated_count?: number;
  hit_count?: number;
  hit_rate?: number;
  avg_return?: number;
  avg_excess_return_sector?: number;
  avg_excess_return_hs300?: number;
  avg_excess_return_momentum?: number;
  avg_baseline_sector_return?: number;
  avg_baseline_hs300_return?: number;
  avg_baseline_momentum_return?: number;
};

type RecommendationSummary = {
  total_recommendations?: number;
  t1?: RecommendationBucket;
  t3?: RecommendationBucket;
  t5?: RecommendationBucket;
};

type RecommendationDetail = {
  recommendation_date: string;
  recommendation_type: string;
  source: string;
  stock_code: string;
  stock_name: string;
  sector_name: string;
  return_1d: number | null;
  return_3d: number | null;
  return_5d: number | null;
};

type RecommendationCompareItem = {
  recommendation_type: string;
  source: string;
  sample_count: number;
  hit_rate_1d: number;
  hit_rate_3d: number;
  hit_rate_5d: number;
  avg_return_1d: number;
  avg_return_3d: number;
  avg_return_5d: number;
  avg_excess_return_5d: number;
};

export function EvaluationPage(props: { refreshKey: number; chartPalette: ChartPalette }) {
  const [summary, setSummary] = useState<SectorSummary | null>(null);
  const [recommendationSummary, setRecommendationSummary] = useState<RecommendationSummary | null>(null);
  const [details, setDetails] = useState<RecommendationDetail[]>([]);
  const [compareItems, setCompareItems] = useState<RecommendationCompareItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [recommendationType, setRecommendationType] = useState('');
  const [source, setSource] = useState('');
  const [sectorName, setSectorName] = useState('');

  const buildRecommendationQuery = (filters: {
    startDate: string;
    endDate: string;
    recommendationType: string;
    source: string;
    sectorName: string;
  }) => {
    const params = new URLSearchParams();
    if (filters.startDate) params.set('start_date', filters.startDate);
    if (filters.endDate) params.set('end_date', filters.endDate);
    if (filters.recommendationType) params.set('recommendation_type', filters.recommendationType);
    if (filters.source) params.set('source', filters.source);
    if (filters.sectorName) params.set('sector_name', filters.sectorName);
    return params.toString();
  };

  const loadData = (filters?: {
    startDate: string;
    endDate: string;
    recommendationType: string;
    source: string;
    sectorName: string;
  }) => {
    let alive = true;
    setLoading(true);
    setError(null);
    const activeFilters = filters ?? {
      startDate,
      endDate,
      recommendationType,
      source,
      sectorName,
    };
    const query = buildRecommendationQuery(activeFilters);
    const querySuffix = query ? `?${query}` : '';
    const detailsSuffix = query ? `?${query}&limit=50` : '?limit=50';

    Promise.all([
      apiGet<{ summary: SectorSummary }>('/api/evaluation/summary'),
      apiGet<{ summary: RecommendationSummary }>(`/api/evaluation/recommendations/summary${querySuffix}`),
      apiGet<{ items: RecommendationDetail[] }>(`/api/evaluation/recommendations/details${detailsSuffix}`),
      apiGet<{ items: RecommendationCompareItem[] }>(`/api/evaluation/recommendations/compare${querySuffix}`),
    ])
      .then(([sectorResp, recoResp, detailResp, compareResp]) => {
        if (!alive) return;
        setSummary(sectorResp.summary ?? null);
        setRecommendationSummary(recoResp.summary ?? null);
        setDetails(detailResp.items ?? []);
        setCompareItems(compareResp.items ?? []);
      })
      .catch(() => {
        if (!alive) return;
        setError('加载失败');
      })
      .finally(() => {
        if (!alive) return;
        setLoading(false);
      });
    return () => {
      alive = false;
    };
  };

  useEffect(() => {
    return loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.refreshKey]);

  const onRunRecommendationEvaluation = async () => {
    setRunning(true);
    setError(null);
    try {
      await apiPost<{ evaluated: number }>('/api/evaluation/recommendations/run?recent_days=30', {});
      loadData();
    } catch {
      setError('评估计算失败');
    } finally {
      setRunning(false);
    }
  };

  const onSearch = () => {
    loadData();
  };

  const onReset = () => {
    const empty = {
      startDate: '',
      endDate: '',
      recommendationType: '',
      source: '',
      sectorName: '',
    };
    setStartDate('');
    setEndDate('');
    setRecommendationType('');
    setSource('');
    setSectorName('');
    loadData(empty);
  };

  const compareOption = useMemo<EChartsOption>(() => {
    const tokens = getChartTokens(props.chartPalette);
    const labels = compareItems.map((item) => `${item.recommendation_type}/${item.source}`);
    const hitRateValues = compareItems.map((item) => Number(item.hit_rate_5d ?? 0));
    const excessValues = compareItems.map((item) => Number(item.avg_excess_return_5d ?? 0));

    return {
      grid: { left: 48, right: 24, top: 38, bottom: 48 },
      legend: {
        top: 6,
        textStyle: { color: tokens.textSecondary },
      },
      tooltip: {
        trigger: 'axis',
        backgroundColor: tokens.bgCard,
        borderColor: tokens.borderColor,
        textStyle: { color: tokens.textPrimary },
      },
      xAxis: {
        type: 'category',
        data: labels,
        axisLabel: { color: tokens.textSecondary, interval: 0, rotate: labels.length > 4 ? 20 : 0 },
        axisLine: { lineStyle: { color: tokens.borderColor } },
      },
      yAxis: [
        {
          type: 'value',
          name: '5D命中率%',
          axisLabel: { color: tokens.textSecondary },
          splitLine: { lineStyle: { color: tokens.borderColor, type: 'dashed' } },
        },
        {
          type: 'value',
          name: '5D超额%',
          axisLabel: { color: tokens.textSecondary },
          splitLine: { show: false },
        },
      ],
      series: [
        {
          name: '5D命中率',
          type: 'bar',
          data: hitRateValues,
          itemStyle: { color: tokens.accentBlue, borderRadius: [4, 4, 0, 0] },
          barMaxWidth: 30,
        },
        {
          name: '5D超额收益',
          type: 'line',
          yAxisIndex: 1,
          data: excessValues,
          smooth: true,
          lineStyle: { color: tokens.accentRed, width: 2 },
          itemStyle: { color: tokens.accentRed },
        },
      ],
    };
  }, [compareItems, props.chartPalette]);

  return (
    <div>
      <PageHeader title="评估报告" />
      {error ? <div className="ui-state ui-state--error">{error}</div> : null}
      {loading ? (
        <div className="ui-state ui-state--muted" style={{ marginTop: 12 }}>
          加载中…
        </div>
      ) : null}

      {summary ? (
        <div style={{ marginTop: 12 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 8 }}>板块方向准确率</div>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            <SummaryCard label="T+1" value={summary.t1?.accuracy} detail={`${summary.t1?.correct ?? 0}/${summary.t1?.total ?? 0}`} />
            <SummaryCard label="T+3" value={summary.t3?.accuracy} detail={`${summary.t3?.correct ?? 0}/${summary.t3?.total ?? 0}`} />
            <SummaryCard label="T+5" value={summary.t5?.accuracy} detail={`${summary.t5?.correct ?? 0}/${summary.t5?.total ?? 0}`} />
          </div>
        </div>
      ) : null}

      <div style={{ marginTop: 16 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 8, marginBottom: 10 }}>
          <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} style={inputStyle} />
          <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} style={inputStyle} />
          <select value={recommendationType} onChange={(e) => setRecommendationType(e.target.value)} style={inputStyle}>
            <option value="">全部类型</option>
            <option value="stock_signal">技术信号</option>
            <option value="sector_candidate">板块候选</option>
          </select>
          <select value={source} onChange={(e) => setSource(e.target.value)} style={inputStyle}>
            <option value="">全部来源</option>
            <option value="signal">signal</option>
            <option value="sector_candidate">sector_candidate</option>
          </select>
          <input
            value={sectorName}
            onChange={(e) => setSectorName(e.target.value)}
            placeholder="板块名"
            style={inputStyle}
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, marginBottom: 8 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-secondary)' }}>个股推荐表现（1D/3D/5D）</div>
          <div style={{ display: 'flex', gap: 6 }}>
            <button type="button" onClick={onSearch} style={buttonStyle}>查询</button>
            <button type="button" onClick={onReset} style={buttonStyle}>重置</button>
            <button
              type="button"
              onClick={onRunRecommendationEvaluation}
              disabled={running}
              style={{ ...buttonStyle, cursor: running ? 'not-allowed' : 'pointer', opacity: running ? 0.6 : 1 }}
            >
              {running ? '计算中…' : '刷新推荐评估'}
            </button>
          </div>
        </div>

        {recommendationSummary && (recommendationSummary.total_recommendations ?? 0) > 0 ? (
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            <RecommendationCard
              label="T+1"
              hitRate={recommendationSummary.t1?.hit_rate}
              avgReturn={recommendationSummary.t1?.avg_return}
              avgExcessSector={recommendationSummary.t1?.avg_excess_return_sector}
              avgExcessHs300={recommendationSummary.t1?.avg_excess_return_hs300}
              avgExcessMomentum={recommendationSummary.t1?.avg_excess_return_momentum}
              detail={`${recommendationSummary.t1?.hit_count ?? 0}/${recommendationSummary.t1?.evaluated_count ?? 0}`}
            />
            <RecommendationCard
              label="T+3"
              hitRate={recommendationSummary.t3?.hit_rate}
              avgReturn={recommendationSummary.t3?.avg_return}
              avgExcessSector={recommendationSummary.t3?.avg_excess_return_sector}
              avgExcessHs300={recommendationSummary.t3?.avg_excess_return_hs300}
              avgExcessMomentum={recommendationSummary.t3?.avg_excess_return_momentum}
              detail={`${recommendationSummary.t3?.hit_count ?? 0}/${recommendationSummary.t3?.evaluated_count ?? 0}`}
            />
            <RecommendationCard
              label="T+5"
              hitRate={recommendationSummary.t5?.hit_rate}
              avgReturn={recommendationSummary.t5?.avg_return}
              avgExcessSector={recommendationSummary.t5?.avg_excess_return_sector}
              avgExcessHs300={recommendationSummary.t5?.avg_excess_return_hs300}
              avgExcessMomentum={recommendationSummary.t5?.avg_excess_return_momentum}
              detail={`${recommendationSummary.t5?.hit_count ?? 0}/${recommendationSummary.t5?.evaluated_count ?? 0}`}
            />
          </div>
        ) : (
          <div className="ui-state ui-state--muted" style={{ marginTop: 8 }}>
            暂无推荐评估数据，可点击“刷新推荐评估”计算最近 30 天结果。
          </div>
        )}
      </div>

      <div
        className="surface-card"
        style={{
          marginTop: 14,
          borderRadius: 8,
          padding: '12px 14px',
        }}
      >
        <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 8 }}>
          类型/来源对比图（5D）
        </div>
        {compareItems.length > 0 ? (
          <EChart option={compareOption} chartPalette={props.chartPalette} style={{ height: 300 }} />
        ) : (
          <div className="ui-state ui-state--muted">暂无可对比数据。</div>
        )}
      </div>

      <div style={{ marginTop: 14 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 8 }}>推荐评估明细（最近50条）</div>
        {details.length > 0 ? (
          <div className="ui-table-scroll">
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr>
                  <th style={thStyle}>日期</th>
                  <th style={thStyle}>股票</th>
                  <th style={thStyle}>板块</th>
                  <th style={thStyle}>类型</th>
                  <th style={thStyle}>来源</th>
                  <th style={thStyle}>1D</th>
                  <th style={thStyle}>3D</th>
                  <th style={thStyle}>5D</th>
                </tr>
              </thead>
              <tbody>
                {details.map((row) => (
                  <tr key={`${row.recommendation_date}-${row.recommendation_type}-${row.stock_code}-${row.source}`}>
                    <td style={tdStyle}>{row.recommendation_date}</td>
                    <td style={tdStyle}>{row.stock_name || row.stock_code}</td>
                    <td style={tdStyle}>{row.sector_name || '—'}</td>
                    <td style={tdStyle}>{row.recommendation_type}</td>
                    <td style={tdStyle}>{row.source}</td>
                    <td style={tdStyle}>{formatPct(row.return_1d)}</td>
                    <td style={tdStyle}>{formatPct(row.return_3d)}</td>
                    <td style={tdStyle}>{formatPct(row.return_5d)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="ui-state ui-state--muted">暂无明细数据。</div>
        )}
      </div>
    </div>
  );
}

function SummaryCard(props: { label: string; value: unknown; detail: string }) {
  const v = typeof props.value === 'number' ? `${props.value.toFixed(1)}%` : '—';
  return (
    <div
      className="surface-card surface-card--raised"
      style={{
        minWidth: 180,
        borderRadius: 8,
        padding: '12px 16px',
      }}
    >
      <div style={{ color: 'var(--text-secondary)', fontSize: 11, fontWeight: 600, letterSpacing: 0.3, textTransform: 'uppercase' }}>
        {props.label} 准确率
      </div>
      <div style={{ marginTop: 6, fontFamily: '"JetBrains Mono", ui-monospace, monospace', fontWeight: 700, fontSize: 18 }}>
        {v}
      </div>
      <div style={{ marginTop: 2, fontSize: 12, color: 'var(--text-secondary)' }}>{props.detail}</div>
    </div>
  );
}

function RecommendationCard(props: {
  label: string;
  hitRate: unknown;
  avgReturn: unknown;
  avgExcessSector: unknown;
  avgExcessHs300: unknown;
  avgExcessMomentum: unknown;
  detail: string;
}) {
  const hitRate = typeof props.hitRate === 'number' ? `${props.hitRate.toFixed(1)}%` : '—';
  const avgReturn = typeof props.avgReturn === 'number' ? `${props.avgReturn > 0 ? '+' : ''}${props.avgReturn.toFixed(2)}%` : '—';
  const avgExcessSector = typeof props.avgExcessSector === 'number' ? `${props.avgExcessSector > 0 ? '+' : ''}${props.avgExcessSector.toFixed(2)}%` : '—';
  const avgExcessHs300 = typeof props.avgExcessHs300 === 'number' ? `${props.avgExcessHs300 > 0 ? '+' : ''}${props.avgExcessHs300.toFixed(2)}%` : '—';
  const avgExcessMomentum = typeof props.avgExcessMomentum === 'number' ? `${props.avgExcessMomentum > 0 ? '+' : ''}${props.avgExcessMomentum.toFixed(2)}%` : '—';
  return (
    <div
      className="surface-card surface-card--raised"
      style={{
        minWidth: 220,
        borderRadius: 8,
        padding: '12px 16px',
      }}
    >
      <div style={{ color: 'var(--text-secondary)', fontSize: 11, fontWeight: 600, letterSpacing: 0.3, textTransform: 'uppercase' }}>
        {props.label} 推荐表现
      </div>
      <div style={{ marginTop: 6, fontFamily: '"JetBrains Mono", ui-monospace, monospace', fontWeight: 700, fontSize: 18 }}>
        命中率 {hitRate}
      </div>
      <div style={{ marginTop: 4, fontSize: 12, color: 'var(--text-secondary)' }}>平均收益 {avgReturn}</div>
      <div style={{ marginTop: 2, fontSize: 12, color: 'var(--text-secondary)' }}>超额(板块/沪深300/动量) {avgExcessSector} / {avgExcessHs300} / {avgExcessMomentum}</div>
      <div style={{ marginTop: 2, fontSize: 12, color: 'var(--text-secondary)' }}>{props.detail}</div>
    </div>
  );
}

function formatPct(value: number | null | undefined): string {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '—';
  return `${value > 0 ? '+' : ''}${value.toFixed(2)}%`;
}

const inputStyle: CSSProperties = {
  border: '1px solid var(--border-color)',
  borderRadius: 8,
  padding: '6px 8px',
  fontSize: 12,
  background: 'var(--bg-secondary)',
  color: 'var(--text-secondary)',
};

const buttonStyle: CSSProperties = {
  border: '1px solid var(--border-color)',
  background: 'var(--bg-secondary)',
  borderRadius: 8,
  padding: '4px 10px',
  fontSize: 12,
  color: 'var(--text-secondary)',
  cursor: 'pointer',
};

const thStyle: CSSProperties = {
  textAlign: 'left',
  padding: '8px',
  borderBottom: '1px solid var(--border-color)',
  color: 'var(--text-secondary)',
};

const tdStyle: CSSProperties = {
  padding: '8px',
  borderBottom: '1px solid var(--border-color)',
  color: 'var(--text-primary)',
};

