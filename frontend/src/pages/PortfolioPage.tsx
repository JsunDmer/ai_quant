import { useEffect, useMemo, useState } from 'react';
import type { CSSProperties } from 'react';
import type { EChartsOption } from 'echarts';

import { apiGet, apiPost } from '../api/client';
import { PageHeader } from '../app/layout/PageHeader';
import { EChart } from '../charts/EChart';
import { getChartTokens, type ChartPalette } from '../charts/chartTokens';

type PortfolioItem = {
  stock_code: string;
  stock_name: string;
  sector_name: string;
  signal: string;
  confidence: number;
  weight: number;
  weight_pct: number;
};

type PortfolioSuggestion = {
  trade_date: string;
  summary: {
    selected_count: number;
    cash_weight: number;
    max_single_weight_actual: number;
    max_sector_weight_actual: number;
    avg_confidence: number;
  };
  items: PortfolioItem[];
  risk_hints: string[];
};

type SimulationSummary = {
  total_trades: number;
  closed_trades: number;
  open_trades: number;
  win_count: number;
  loss_count: number;
  win_rate: number;
  avg_return: number;
  total_return: number;
  avg_holding_days: number;
  profit_factor: number;
};

type DailyPnl = {
  date: string;
  daily_return: number;
  cumulative_return: number;
  trade_count: number;
};

type SimDetail = {
  trade_date: string;
  stock_code: string;
  stock_name: string;
  sector_name: string;
  signal: string;
  confidence: number;
  return_pct: number;
  status: string;
  holding_days: number;
};

type OptimizerResult = {
  status: string;
  sample_count?: number;
  best?: {
    name: string;
    hit_rate?: number;
    avg_return_5d?: number;
    avg_excess_return_5d?: number;
    objective?: number;
    params?: Record<string, number>;
  };
  baseline?: {
    hit_rate?: number;
    avg_return_5d?: number;
    avg_excess_return_5d?: number;
    objective?: number;
  };
  top_trials?: Array<{
    name: string;
    hit_rate?: number;
    avg_return_5d?: number;
    avg_excess_return_5d?: number;
    objective?: number;
  }>;
  message?: string;
};

export function PortfolioPage(props: { refreshKey: number; chartPalette: ChartPalette }) {
  const [topN, setTopN] = useState(8);
  const [maxSingle, setMaxSingle] = useState(0.2);
  const [maxSector, setMaxSector] = useState(0.35);

  const [portfolio, setPortfolio] = useState<PortfolioSuggestion | null>(null);
  const [summary, setSummary] = useState<SimulationSummary | null>(null);
  const [dailyPnl, setDailyPnl] = useState<DailyPnl[]>([]);
  const [details, setDetails] = useState<SimDetail[]>([]);
  const [optimizerResult, setOptimizerResult] = useState<OptimizerResult | null>(null);

  const [loading, setLoading] = useState(false);
  const [runningSimulation, setRunningSimulation] = useState(false);
  const [runningOptimizer, setRunningOptimizer] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadPortfolio = async (opts?: { topN?: number; maxSingle?: number; maxSector?: number }) => {
    const activeTopN = opts?.topN ?? topN;
    const activeMaxSingle = opts?.maxSingle ?? maxSingle;
    const activeMaxSector = opts?.maxSector ?? maxSector;
    const query = new URLSearchParams({
      top_n: String(activeTopN),
      max_single_weight: String(activeMaxSingle),
      max_sector_weight: String(activeMaxSector),
    });
    const resp = await apiGet<PortfolioSuggestion>(`/api/evaluation/portfolio/suggest?${query.toString()}`);
    setPortfolio(resp);
  };

  const loadSimulation = async () => {
    const [summaryResp, pnlResp, detailResp] = await Promise.all([
      apiGet<{ summary: SimulationSummary }>('/api/evaluation/simulation/summary'),
      apiGet<{ items: DailyPnl[] }>('/api/evaluation/simulation/daily-pnl?days=120'),
      apiGet<{ items: SimDetail[] }>('/api/evaluation/simulation/details?limit=40'),
    ]);
    setSummary(summaryResp.summary ?? null);
    setDailyPnl(pnlResp.items ?? []);
    setDetails(detailResp.items ?? []);
  };

  const loadAll = async () => {
    setLoading(true);
    setError(null);
    try {
      await Promise.all([loadPortfolio(), loadSimulation()]);
    } catch {
      setError('组合与模拟数据加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.refreshKey]);

  const onRefreshPortfolio = async () => {
    setError(null);
    try {
      await loadPortfolio();
    } catch {
      setError('组合建议刷新失败');
    }
  };

  const onRunSimulation = async () => {
    setRunningSimulation(true);
    setError(null);
    try {
      await apiPost('/api/evaluation/simulation/run', {});
      await loadSimulation();
      await loadPortfolio();
    } catch {
      setError('模拟执行失败');
    } finally {
      setRunningSimulation(false);
    }
  };

  const onRunOptimizer = async () => {
    setRunningOptimizer(true);
    setError(null);
    try {
      const result = await apiPost<OptimizerResult>('/api/evaluation/optimizer/run?trials=40&min_samples=20', {});
      setOptimizerResult(result);
    } catch {
      setError('参数优化执行失败');
    } finally {
      setRunningOptimizer(false);
    }
  };

  const weightOption = useMemo<EChartsOption>(() => {
    const tokens = getChartTokens(props.chartPalette);
    const labels = (portfolio?.items ?? []).map((item) => item.stock_name || item.stock_code);
    const values = (portfolio?.items ?? []).map((item) => item.weight_pct ?? 0);
    return {
      grid: { left: 42, right: 18, top: 24, bottom: 42 },
      xAxis: {
        type: 'category',
        data: labels,
        axisLabel: { color: tokens.textSecondary, interval: 0, rotate: labels.length > 5 ? 25 : 0 },
        axisLine: { lineStyle: { color: tokens.borderColor } },
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: tokens.textSecondary, formatter: '{value}%' },
        splitLine: { lineStyle: { color: tokens.borderColor, type: 'dashed' } },
      },
      tooltip: { trigger: 'axis' },
      series: [
        {
          type: 'bar',
          data: values,
          itemStyle: { color: tokens.accentBlue, borderRadius: [4, 4, 0, 0] },
          barMaxWidth: 28,
        },
      ],
    };
  }, [portfolio?.items, props.chartPalette]);

  const pnlOption = useMemo<EChartsOption>(() => {
    const tokens = getChartTokens(props.chartPalette);
    const labels = dailyPnl.map((item) => item.date);
    const cumulative = dailyPnl.map((item) => item.cumulative_return ?? 0);
    const daily = dailyPnl.map((item) => item.daily_return ?? 0);
    return {
      grid: { left: 48, right: 24, top: 26, bottom: 42 },
      legend: { top: 2, textStyle: { color: tokens.textSecondary } },
      xAxis: {
        type: 'category',
        data: labels,
        axisLabel: { color: tokens.textSecondary, interval: Math.max(0, Math.floor(labels.length / 8)) },
        axisLine: { lineStyle: { color: tokens.borderColor } },
      },
      yAxis: [
        {
          type: 'value',
          axisLabel: { color: tokens.textSecondary, formatter: '{value}%' },
          splitLine: { lineStyle: { color: tokens.borderColor, type: 'dashed' } },
        },
        {
          type: 'value',
          axisLabel: { color: tokens.textSecondary, formatter: '{value}%' },
          splitLine: { show: false },
        },
      ],
      tooltip: { trigger: 'axis' },
      series: [
        {
          name: '日收益',
          type: 'bar',
          data: daily,
          itemStyle: { color: tokens.accentBlue },
          barMaxWidth: 20,
        },
        {
          name: '累计收益',
          type: 'line',
          yAxisIndex: 1,
          data: cumulative,
          smooth: true,
          lineStyle: { color: tokens.accentRed, width: 2 },
          itemStyle: { color: tokens.accentRed },
        },
      ],
    };
  }, [dailyPnl, props.chartPalette]);

  return (
    <div>
      <PageHeader title="组合与模拟" subtitle={portfolio?.trade_date ? `推荐日：${portfolio.trade_date}` : undefined} />
      {error ? <div className="ui-state ui-state--error">{error}</div> : null}
      {loading ? <div className="ui-state ui-state--muted">加载中…</div> : null}

      <div className="surface-card" style={{ marginTop: 12, borderRadius: 8, padding: '12px 14px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 8 }}>
          <label style={labelStyle}>
            TopN
            <input type="number" min={1} max={20} value={topN} onChange={(e) => setTopN(Number(e.target.value || 8))} style={inputStyle} />
          </label>
          <label style={labelStyle}>
            单票上限
            <input type="number" step={0.01} min={0.05} max={0.6} value={maxSingle} onChange={(e) => setMaxSingle(Number(e.target.value || 0.2))} style={inputStyle} />
          </label>
          <label style={labelStyle}>
            板块上限
            <input type="number" step={0.01} min={0.1} max={0.8} value={maxSector} onChange={(e) => setMaxSector(Number(e.target.value || 0.35))} style={inputStyle} />
          </label>
        </div>
        <div style={{ marginTop: 10, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button
            type="button"
            style={buttonStyle}
            onClick={() => loadPortfolio({ topN, maxSingle, maxSector })}
          >
            刷新建议
          </button>
          <button
            type="button"
            style={{ ...buttonStyle, opacity: runningSimulation ? 0.6 : 1 }}
            onClick={onRunSimulation}
            disabled={runningSimulation}
          >
            {runningSimulation ? '模拟中…' : '执行模拟'}
          </button>
          <button
            type="button"
            style={{ ...buttonStyle, opacity: runningOptimizer ? 0.6 : 1 }}
            onClick={onRunOptimizer}
            disabled={runningOptimizer}
          >
            {runningOptimizer ? '优化中…' : '运行参数优化'}
          </button>
          <button type="button" style={buttonStyle} onClick={onRefreshPortfolio}>
            仅刷新组合
          </button>
        </div>
      </div>

      <div className="surface-card" style={{ marginTop: 12, borderRadius: 8, padding: '12px 14px' }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 8 }}>组合建议与风险提示</div>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <Stat label="入选数量" value={String(portfolio?.summary.selected_count ?? 0)} />
          <Stat label="现金仓位" value={formatPct((portfolio?.summary.cash_weight ?? 0) * 100)} />
          <Stat label="最大单票" value={formatPct((portfolio?.summary.max_single_weight_actual ?? 0) * 100)} />
          <Stat label="最大板块" value={formatPct((portfolio?.summary.max_sector_weight_actual ?? 0) * 100)} />
        </div>
        {(portfolio?.risk_hints ?? []).length > 0 ? (
          <div style={{ marginTop: 10, display: 'grid', gap: 6 }}>
            {(portfolio?.risk_hints ?? []).map((hint, idx) => (
              <div key={`${hint}-${idx}`} style={{ fontSize: 12, color: 'var(--text-secondary)', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 6, padding: '6px 8px' }}>
                {hint}
              </div>
            ))}
          </div>
        ) : null}

        {(portfolio?.items ?? []).length > 0 ? (
          <>
            <div style={{ marginTop: 10 }}>
              <EChart option={weightOption} chartPalette={props.chartPalette} style={{ height: 280 }} />
            </div>
            <div className="ui-table-scroll" style={{ marginTop: 10 }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                <thead>
                  <tr>
                    <th style={thStyle}>股票</th>
                    <th style={thStyle}>板块</th>
                    <th style={thStyle}>信号</th>
                    <th style={thStyle}>置信度</th>
                    <th style={thStyle}>建议权重</th>
                  </tr>
                </thead>
                <tbody>
                  {(portfolio?.items ?? []).map((row) => (
                    <tr key={row.stock_code}>
                      <td style={tdStyle}>{row.stock_name || row.stock_code}</td>
                      <td style={tdStyle}>{row.sector_name}</td>
                      <td style={tdStyle}>{row.signal}</td>
                      <td style={tdStyle}>{formatPct((row.confidence ?? 0) * 100)}</td>
                      <td style={tdStyle}>{formatPct(row.weight_pct)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <div className="ui-state ui-state--muted" style={{ marginTop: 8 }}>暂无组合建议数据。</div>
        )}
      </div>

      <div className="surface-card" style={{ marginTop: 12, borderRadius: 8, padding: '12px 14px' }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 8 }}>模拟交易表现</div>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <Stat label="总交易" value={String(summary?.total_trades ?? 0)} />
          <Stat label="已平仓" value={String(summary?.closed_trades ?? 0)} />
          <Stat label="胜率" value={formatPct(summary?.win_rate)} />
          <Stat label="平均收益" value={formatPct(summary?.avg_return)} />
          <Stat label="累计收益" value={formatPct(summary?.total_return)} />
        </div>
        {dailyPnl.length > 0 ? (
          <div style={{ marginTop: 10 }}>
            <EChart option={pnlOption} chartPalette={props.chartPalette} style={{ height: 300 }} />
          </div>
        ) : (
          <div className="ui-state ui-state--muted" style={{ marginTop: 8 }}>暂无模拟收益曲线。</div>
        )}

        {details.length > 0 ? (
          <div className="ui-table-scroll" style={{ marginTop: 10 }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr>
                  <th style={thStyle}>日期</th>
                  <th style={thStyle}>股票</th>
                  <th style={thStyle}>板块</th>
                  <th style={thStyle}>状态</th>
                  <th style={thStyle}>收益</th>
                  <th style={thStyle}>持仓天数</th>
                </tr>
              </thead>
              <tbody>
                {details.map((row) => (
                  <tr key={`${row.trade_date}-${row.stock_code}`}>
                    <td style={tdStyle}>{row.trade_date}</td>
                    <td style={tdStyle}>{row.stock_name || row.stock_code}</td>
                    <td style={tdStyle}>{row.sector_name || '—'}</td>
                    <td style={tdStyle}>{row.status}</td>
                    <td style={tdStyle}>{formatPct(row.return_pct)}</td>
                    <td style={tdStyle}>{row.holding_days ?? 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>

      <div className="surface-card" style={{ marginTop: 12, borderRadius: 8, padding: '12px 14px' }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 8 }}>参数优化结果</div>
        {optimizerResult ? (
          optimizerResult.status === 'ok' ? (
            <>
              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                <Stat label="样本量" value={String(optimizerResult.sample_count ?? 0)} />
                <Stat label="Baseline目标值" value={String(optimizerResult.baseline?.objective ?? 0)} />
                <Stat label="Best目标值" value={String(optimizerResult.best?.objective ?? 0)} />
                <Stat label="Best 5D超额" value={formatPct(optimizerResult.best?.avg_excess_return_5d)} />
              </div>
              {(optimizerResult.top_trials ?? []).length > 0 ? (
                <div className="ui-table-scroll" style={{ marginTop: 10 }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                    <thead>
                      <tr>
                        <th style={thStyle}>方案</th>
                        <th style={thStyle}>目标值</th>
                        <th style={thStyle}>命中率</th>
                        <th style={thStyle}>5D收益</th>
                        <th style={thStyle}>5D超额</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(optimizerResult.top_trials ?? []).map((row) => (
                        <tr key={row.name}>
                          <td style={tdStyle}>{row.name}</td>
                          <td style={tdStyle}>{row.objective ?? 0}</td>
                          <td style={tdStyle}>{formatPct(row.hit_rate)}</td>
                          <td style={tdStyle}>{formatPct(row.avg_return_5d)}</td>
                          <td style={tdStyle}>{formatPct(row.avg_excess_return_5d)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : null}
            </>
          ) : (
            <div className="ui-state ui-state--muted">{optimizerResult.message ?? '样本不足，暂无法优化参数。'}</div>
          )
        ) : (
          <div className="ui-state ui-state--muted">点击“运行参数优化”生成结果。</div>
        )}
      </div>
    </div>
  );
}

function Stat(props: { label: string; value: string }) {
  return (
    <div className="surface-card surface-card--raised" style={{ minWidth: 140, borderRadius: 8, padding: '10px 12px' }}>
      <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{props.label}</div>
      <div style={{ fontSize: 16, fontWeight: 700, marginTop: 4 }}>{props.value}</div>
    </div>
  );
}

function formatPct(value: number | undefined | null): string {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '—';
  return `${value > 0 ? '+' : ''}${value.toFixed(2)}%`;
}

const labelStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 4,
  fontSize: 12,
  color: 'var(--text-secondary)',
};

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
  borderRadius: 8,
  padding: '6px 10px',
  fontSize: 12,
  color: 'var(--text-secondary)',
  background: 'var(--bg-secondary)',
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

