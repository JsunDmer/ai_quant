import { useEffect, useMemo, useRef, useState } from 'react';
import * as echarts from 'echarts';
import { apiGet } from '../api/client';
import type { KlineItem, KlineResponse } from '../api/types';

type CacheEntry = { ts: number; data: KlineItem[] };
type Preset = 'trend' | 'swing' | 'scalp';

const cache = new Map<string, CacheEntry>();
const inflight = new Map<string, Promise<KlineItem[]>>();
const CACHE_TTL_MS = 5 * 60 * 1000;

function getCacheKey(stockCode: string): string {
  return `${stockCode}:180`;
}

function readCache(key: string): KlineItem[] | null {
  const hit = cache.get(key);
  if (!hit) return null;
  if (Date.now() - hit.ts > CACHE_TTL_MS) {
    cache.delete(key);
    return null;
  }
  return hit.data;
}

async function fetchStockChartData(stockCode: string): Promise<KlineItem[]> {
  const key = getCacheKey(stockCode);
  const cached = readCache(key);
  if (cached) return cached;
  const running = inflight.get(key);
  if (running) return running;
  const req = apiGet<KlineResponse>(`/api/signals/stock/${stockCode}/kline?days=180`)
    .then((d) => {
      const items = d.data || [];
      cache.set(key, { ts: Date.now(), data: items });
      return items;
    })
    .finally(() => {
      inflight.delete(key);
    });
  inflight.set(key, req);
  return req;
}

export function prefetchStockChartData(stockCode: string): void {
  const code = (stockCode || '').trim();
  if (!code) return;
  void fetchStockChartData(code);
}

export function StockChart({
  stockCode,
  chartHeight = 480,
  compact = false,
}: {
  stockCode: string;
  chartHeight?: number | string;
  compact?: boolean;
}) {
  const [data, setData] = useState<KlineItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [preset, setPreset] = useState<Preset>('trend');
  const [chartError, setChartError] = useState<string | null>(null);
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInsRef = useRef<echarts.ECharts | null>(null);
  const windowResizeRef = useRef<(() => void) | null>(null);
  const resizeObserverRef = useRef<ResizeObserver | null>(null);

  useEffect(() => {
    let alive = true;
    setLoading(true);

    const cached = readCache(getCacheKey(stockCode));
    if (cached) {
      setData(cached);
      setLoading(false);
      return;
    }

    fetchStockChartData(stockCode)
      .then((d) => {
        if (!alive) return;
        setData(d);
        setLoading(false);
      })
      .catch(() => {
        if (!alive) return;
        setLoading(false);
      });
    return () => { alive = false; };
  }, [stockCode]);

  useEffect(() => {
    if (loading || !data.length) return;
    if (!chartRef.current) return;
    if (chartInsRef.current) return;

    try {
      const chart = echarts.init(chartRef.current);
      chartInsRef.current = chart;
      if (typeof ResizeObserver !== 'undefined') {
        const ro = new ResizeObserver(() => chart.resize());
        ro.observe(chartRef.current);
        resizeObserverRef.current = ro;
      } else {
        const onWindowResize = () => chart.resize();
        windowResizeRef.current = onWindowResize;
        window.addEventListener('resize', onWindowResize);
      }
      setChartError(null);
    } catch (e) {
      setChartError(`图表初始化失败: ${e instanceof Error ? e.message : 'unknown error'}`);
    }
  }, [loading, data.length]);

  useEffect(() => {
    return () => {
      if (resizeObserverRef.current) {
        resizeObserverRef.current.disconnect();
        resizeObserverRef.current = null;
      }
      if (windowResizeRef.current) {
        window.removeEventListener('resize', windowResizeRef.current);
        windowResizeRef.current = null;
      }
      if (chartInsRef.current) {
        try {
          chartInsRef.current.dispose();
        } catch {
          // noop: avoid dispose failure breaking UI
        }
        chartInsRef.current = null;
      }
    };
  }, []);

  const derived = useMemo(() => buildIndicators(data), [data]);

  useEffect(() => {
    const chart = chartInsRef.current;
    if (!chart || !derived) return;
    try {
      chart.setOption(buildOption(stockCode, derived, preset), true);
      setChartError(null);
    } catch (e) {
      setChartError(`图表渲染失败: ${e instanceof Error ? e.message : 'unknown error'}`);
    }
  }, [derived, stockCode, preset]);

  if (loading) return <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-muted)' }}>加载走势...</div>;
  if (!data.length) return <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-muted)' }}>暂无数据</div>;
  if (chartError) return <div style={{ padding: 20, textAlign: 'center', color: 'var(--accent-red)' }}>{chartError}</div>;

  return (
    <div style={{ marginTop: compact ? 6 : 12 }}>
      <div style={{ fontSize: compact ? 11 : 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 8 }}>
        近180日K线（可缩放/十字光标）
      </div>
      <div style={{ display: 'flex', gap: 8, marginBottom: compact ? 6 : 8, flexWrap: 'wrap' }}>
        <PresetButton label="趋势" active={preset === 'trend'} onClick={() => setPreset('trend')} />
        <PresetButton label="波段" active={preset === 'swing'} onClick={() => setPreset('swing')} />
        <PresetButton label="超短" active={preset === 'scalp'} onClick={() => setPreset('scalp')} />
      </div>
      <div ref={chartRef} style={{ width: '100%', height: chartHeight, minHeight: compact ? 320 : 420 }} />
      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: compact ? 4 : 6, display: 'flex', gap: 16, flexWrap: 'wrap' }}>
        <span>指标：MA / VOL / MACD / RSI / KDJ</span>
        {compact ? null : <span>提示：拖动下方滑块看历史区间</span>}
      </div>
    </div>
  );
}

function PresetButton(props: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={props.onClick}
      style={{
        padding: '4px 10px',
        borderRadius: 999,
        border: '1px solid var(--border-color)',
        background: props.active ? 'var(--bg-primary)' : 'transparent',
        color: props.active ? 'var(--text-primary)' : 'var(--text-muted)',
        fontSize: 11,
        fontWeight: 600,
        cursor: 'pointer',
      }}
    >
      {props.label}
    </button>
  );
}

type ChartDerived = {
  dates: string[];
  kline: number[][];
  closes: number[];
  volumes: number[];
  upDownColor: string[];
  ma5: Array<number | null>;
  ma10: Array<number | null>;
  ma20: Array<number | null>;
  ma60: Array<number | null>;
  macd: Array<number | null>;
  dif: Array<number | null>;
  dea: Array<number | null>;
  rsi14: Array<number | null>;
  k: Array<number | null>;
  d: Array<number | null>;
  j: Array<number | null>;
};

function buildIndicators(items: KlineItem[]): ChartDerived | null {
  if (!items.length) return null;
  const dates = items.map((x) => x.date);
  const kline = items.map((x) => [x.open, x.close, x.low, x.high]);
  const closes = items.map((x) => x.close);
  const volumes = items.map((x) => x.volume);
  const upDownColor = items.map((x) => (x.close >= x.open ? '#ef4444' : '#22c55e'));

  const ma5 = calcMA(closes, 5);
  const ma10 = calcMA(closes, 10);
  const ma20 = calcMA(closes, 20);
  const ma60 = calcMA(closes, 60);
  const { dif, dea, macd } = calcMACD(closes);
  const rsi14 = calcRSI(closes, 14);
  const { k, d, j } = calcKDJ(items, 9);

  return {
    dates,
    kline,
    closes,
    volumes,
    upDownColor,
    ma5,
    ma10,
    ma20,
    ma60,
    macd,
    dif,
    dea,
    rsi14,
    k,
    d,
    j,
  };
}

function buildOption(stockCode: string, d: ChartDerived, preset: Preset): echarts.EChartsCoreOption {
  const selected = presetToSelected(preset);
  return {
    animation: false,
    color: ['#f97316', '#3b82f6', '#8b5cf6', '#06b6d4', '#f59e0b', '#14b8a6', '#ef4444'],
    legend: {
      top: 4,
      left: 8,
      textStyle: { color: '#64748b', fontSize: 11 },
      itemWidth: 10,
      itemHeight: 6,
      data: ['K线', 'MA5', 'MA10', 'MA20', 'MA60', 'VOL', 'MACD', 'DIF', 'DEA', 'RSI14', 'K', 'D', 'J'],
      selected,
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      borderWidth: 1,
      borderColor: '#cbd5e1',
      textStyle: { color: '#0f172a', fontSize: 11 },
    },
    axisPointer: {
      link: [{ xAxisIndex: [0, 1, 2, 3] }],
      label: { backgroundColor: '#475569' },
    },
    grid: [
      { left: 56, right: 20, top: 30, height: 190 },
      { left: 56, right: 20, top: 228, height: 70 },
      { left: 56, right: 20, top: 304, height: 70 },
      { left: 56, right: 20, top: 380, height: 70 },
    ],
    xAxis: [
      axisCategory(d.dates, 0),
      axisCategory(d.dates, 1),
      axisCategory(d.dates, 2),
      axisCategory(d.dates, 3),
    ],
    yAxis: [
      axisValue('价格', 0),
      axisValue('成交量', 1),
      axisValue('MACD', 2),
      axisValue('振荡', 3),
    ],
    dataZoom: [
      { type: 'inside', xAxisIndex: [0, 1, 2, 3], start: 55, end: 100, zoomOnMouseWheel: false, moveOnMouseWheel: false },
      { type: 'slider', xAxisIndex: [0, 1, 2, 3], bottom: 8, height: 16, start: 55, end: 100 },
    ],
    series: [
      {
        name: 'K线',
        type: 'candlestick',
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: d.kline,
        itemStyle: { color: '#ef4444', color0: '#22c55e', borderColor: '#ef4444', borderColor0: '#22c55e' },
      },
      seriesLine('MA5', d.ma5, 0, 0),
      seriesLine('MA10', d.ma10, 0, 0),
      seriesLine('MA20', d.ma20, 0, 0),
      seriesLine('MA60', d.ma60, 0, 0),
      {
        name: 'VOL',
        type: 'bar',
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: d.volumes.map((v, i) => ({
          value: v,
          itemStyle: { color: d.upDownColor[i] },
        })),
      },
      {
        name: 'MACD',
        type: 'bar',
        xAxisIndex: 2,
        yAxisIndex: 2,
        data: d.macd.map((x) => (x === null ? null : x * 2)),
        itemStyle: {
          color: (p: { dataIndex: number }) => (toNum(d.macd[p.dataIndex]) >= 0 ? '#ef4444' : '#22c55e'),
        },
      },
      seriesLine('DIF', d.dif, 2, 2),
      seriesLine('DEA', d.dea, 2, 2),
      seriesLine('RSI14', d.rsi14, 3, 3),
      seriesLine('K', d.k, 3, 3),
      seriesLine('D', d.d, 3, 3),
      seriesLine('J', d.j, 3, 3),
    ],
    title: {
      text: `${stockCode} 交互分析`,
      left: 'center',
      top: 2,
      textStyle: { fontSize: 11, color: '#64748b', fontWeight: 'normal' },
    },
  };
}

function presetToSelected(preset: Preset): Record<string, boolean> {
  if (preset === 'scalp') {
    return {
      K线: true, MA5: true, MA10: true, MA20: false, MA60: false,
      VOL: true, MACD: true, DIF: true, DEA: true, RSI14: false, K: true, D: true, J: true,
    };
  }
  if (preset === 'swing') {
    return {
      K线: true, MA5: true, MA10: true, MA20: true, MA60: false,
      VOL: true, MACD: true, DIF: true, DEA: true, RSI14: true, K: false, D: false, J: false,
    };
  }
  return {
    K线: true, MA5: true, MA10: true, MA20: true, MA60: true,
    VOL: true, MACD: true, DIF: true, DEA: true, RSI14: false, K: false, D: false, J: false,
  };
}

function axisCategory(dates: string[], idx: number): echarts.XAXisComponentOption {
  return {
    type: 'category',
    gridIndex: idx,
    data: dates,
    boundaryGap: false,
    axisLine: { lineStyle: { color: '#cbd5e1' } },
    axisLabel: idx === 3 ? { color: '#64748b', fontSize: 10 } : { show: false },
    splitLine: { show: false },
    axisTick: { show: false },
    min: 'dataMin',
    max: 'dataMax',
  };
}

function axisValue(name: string, gridIndex: number): echarts.YAXisComponentOption {
  return {
    gridIndex,
    scale: true,
    name,
    nameTextStyle: { color: '#94a3b8', fontSize: 10, padding: [0, 0, 0, 6] },
    axisLabel: { color: '#64748b', fontSize: 10 },
    axisLine: { show: false },
    axisTick: { show: false },
    splitLine: { lineStyle: { color: '#e2e8f0', type: 'dashed', width: 0.8 } },
  };
}

function seriesLine(
  name: string,
  data: Array<number | null>,
  xAxisIndex: number,
  yAxisIndex: number,
): echarts.LineSeriesOption {
  return {
    name,
    type: 'line',
    xAxisIndex,
    yAxisIndex,
    data,
    showSymbol: false,
    smooth: true,
    lineStyle: { width: 1.2 },
  };
}

function calcMA(values: number[], period: number): Array<number | null> {
  const out: Array<number | null> = new Array(values.length).fill(null);
  let sum = 0;
  for (let i = 0; i < values.length; i += 1) {
    sum += values[i];
    if (i >= period) sum -= values[i - period];
    if (i >= period - 1) out[i] = sum / period;
  }
  return out;
}

function calcEMA(values: number[], period: number): Array<number | null> {
  const out: Array<number | null> = new Array(values.length).fill(null);
  if (!values.length) return out;
  const alpha = 2 / (period + 1);
  let prev = values[0];
  out[0] = prev;
  for (let i = 1; i < values.length; i += 1) {
    prev = alpha * values[i] + (1 - alpha) * prev;
    out[i] = prev;
  }
  return out;
}

function calcMACD(values: number[]) {
  const ema12 = calcEMA(values, 12);
  const ema26 = calcEMA(values, 26);
  const dif: Array<number | null> = values.map((_, i) => {
    const a = ema12[i];
    const b = ema26[i];
    if (a === null || b === null) return null;
    return a - b;
  });
  const dea = calcEMA(dif.map((x) => toNum(x)), 9);
  const macd: Array<number | null> = dif.map((x, i) => {
    if (x === null || dea[i] === null) return null;
    return x - dea[i]!;
  });
  return { dif, dea, macd };
}

function calcRSI(values: number[], period: number): Array<number | null> {
  const out: Array<number | null> = new Array(values.length).fill(null);
  if (values.length <= period) return out;
  let gainSum = 0;
  let lossSum = 0;

  for (let i = 1; i <= period; i += 1) {
    const delta = values[i] - values[i - 1];
    if (delta > 0) gainSum += delta;
    if (delta < 0) lossSum += -delta;
  }
  let avgGain = gainSum / period;
  let avgLoss = lossSum / period;
  out[period] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);

  for (let i = period + 1; i < values.length; i += 1) {
    const delta = values[i] - values[i - 1];
    const gain = delta > 0 ? delta : 0;
    const loss = delta < 0 ? -delta : 0;
    avgGain = (avgGain * (period - 1) + gain) / period;
    avgLoss = (avgLoss * (period - 1) + loss) / period;
    out[i] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);
  }
  return out;
}

function calcKDJ(items: KlineItem[], period = 9) {
  const k: Array<number | null> = new Array(items.length).fill(null);
  const d: Array<number | null> = new Array(items.length).fill(null);
  const j: Array<number | null> = new Array(items.length).fill(null);

  let prevK = 50;
  let prevD = 50;
  for (let i = 0; i < items.length; i += 1) {
    const start = Math.max(0, i - period + 1);
    let highest = -Infinity;
    let lowest = Infinity;
    for (let p = start; p <= i; p += 1) {
      highest = Math.max(highest, items[p].high);
      lowest = Math.min(lowest, items[p].low);
    }
    const close = items[i].close;
    const rsv = highest === lowest ? 50 : ((close - lowest) / (highest - lowest)) * 100;
    const currK = (2 * prevK + rsv) / 3;
    const currD = (2 * prevD + currK) / 3;
    const currJ = 3 * currK - 2 * currD;
    prevK = currK;
    prevD = currD;
    k[i] = currK;
    d[i] = currD;
    j[i] = currJ;
  }
  return { k, d, j };
}

function toNum(v: number | null | undefined): number {
  return typeof v === 'number' && Number.isFinite(v) ? v : 0;
}