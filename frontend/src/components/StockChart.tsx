import { useEffect, useRef, useState } from 'react';
import { apiGet } from '../api/client';
import type { KlineItem, KlineResponse } from '../api/types';

const cache = new Map<string, KlineItem[]>();

export function StockChart({ stockCode }: { stockCode: string }) {
  const [data, setData] = useState<KlineItem[]>([]);
  const [loading, setLoading] = useState(true);
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    let alive = true;
    setLoading(true);

    if (cache.has(stockCode)) {
      setData(cache.get(stockCode)!);
      setLoading(false);
      return;
    }

    apiGet<KlineResponse>(`/api/signals/stock/${stockCode}/kline?days=30`)
      .then((d) => {
        if (!alive) return;
        const items = d.data || [];
        cache.set(stockCode, items);
        setData(items);
        setLoading(false);
      })
      .catch(() => {
        if (!alive) return;
        setLoading(false);
      });
    return () => { alive = false; };
  }, [stockCode]);

  if (loading) return <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-muted)' }}>加载走势...</div>;
  if (!data.length) return <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-muted)' }}>暂无数据</div>;

  const width = 600;
  const height = 200;
  const padding = { top: 10, right: 10, bottom: 30, left: 50 };
  const chartW = width - padding.left - padding.right;
  const chartH = height - padding.top - padding.bottom;

  const prices = data.flatMap((d) => [d.high, d.low]);
  const minPrice = Math.min(...prices);
  const maxPrice = Math.max(...prices);
  const priceRange = maxPrice - minPrice || 1;

  const xScale = (i: number) => padding.left + (i / (data.length - 1)) * chartW;
  const yScale = (p: number) => padding.top + chartH - ((p - minPrice) / priceRange) * chartH;

  // 收盘价折线
  const linePath = data
    .map((d, i) => `${i === 0 ? 'M' : 'L'} ${xScale(i)} ${yScale(d.close)}`)
    .join(' ');

  // 均线
  const ma20 = data.map((_, i) => {
    if (i < 19) return null;
    const sum = data.slice(i - 19, i + 1).reduce((s, d) => s + d.close, 0);
    return sum / 20;
  });
  const maPath = ma20
    .map((v, i) => (v !== null ? `${i === 0 || ma20[i - 1] === null ? 'M' : 'L'} ${xScale(i)} ${yScale(v)}` : ''))
    .filter(Boolean)
    .join(' ');

  return (
    <div style={{ marginTop: 12 }}>
      <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 8 }}>近30日走势</div>
      <svg ref={svgRef} width={width} height={height} style={{ maxWidth: '100%' }}>
        {/* 网格线 */}
        {[0, 1, 2, 3, 4].map((i) => {
          const y = padding.top + (i / 4) * chartH;
          const price = maxPrice - (i / 4) * priceRange;
          return (
            <g key={i}>
              <line x1={padding.left} y1={y} x2={width - padding.right} y2={y} stroke="var(--border-color)" strokeWidth={0.5} />
              <text x={padding.left - 5} y={y + 3} textAnchor="end" fontSize={10} fill="var(--text-muted)">
                {price.toFixed(0)}
              </text>
            </g>
          );
        })}

        {/* 价格线 */}
        <path d={linePath} fill="none" stroke="#2563eb" strokeWidth={1.5} />

        {/* 均线 */}
        {maPath && <path d={maPath} fill="none" stroke="#f59e0b" strokeWidth={1} strokeDasharray="4,2" />}

        {/* X轴日期 */}
        {[0, Math.floor(data.length / 2), data.length - 1].map((i) => (
          <text key={i} x={xScale(i)} y={height - 5} textAnchor="middle" fontSize={10} fill="var(--text-muted)">
            {data[i].date.slice(5, 10)}
          </text>
        ))}
      </svg>
      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4, display: 'flex', gap: 16 }}>
        <span><span style={{ display: 'inline-block', width: 12, height: 2, background: '#2563eb', marginRight: 4 }}></span>收盘价</span>
        <span><span style={{ display: 'inline-block', width: 12, height: 2, background: '#f59e0b', marginRight: 4 }}></span>MA20</span>
      </div>
    </div>
  );
}