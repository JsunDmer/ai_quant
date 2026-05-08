import { useEffect, useState } from 'react';
import { apiGet } from '../api/client';
import type { FinancialData } from '../api/types';

const cache = new Map<string, FinancialData>();

export function StockFinancials({ stockCode }: { stockCode: string }) {
  const [data, setData] = useState<FinancialData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    setLoading(true);

    if (cache.has(stockCode)) {
      setData(cache.get(stockCode)!);
      setLoading(false);
      return;
    }

    apiGet<FinancialData>(`/api/signals/stock/${stockCode}/financial`)
      .then((d) => {
        if (!alive) return;
        cache.set(stockCode, d);
        setData(d);
        setLoading(false);
      })
      .catch(() => {
        if (!alive) return;
        setLoading(false);
      });
    return () => { alive = false; };
  }, [stockCode]);

  if (loading) return <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-muted)' }}>加载财务数据...</div>;
  if (!data || !data.has_data) return <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-muted)' }}>暂无财务数据</div>;

  return (
    <div style={{ marginTop: 16 }}>
      <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 10 }}>2026年一季度财务</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
        <FinancialCard label="净利润" value={`${data.net_profit}亿`} sub={data.net_profit_yoy !== 0 ? `同比${data.net_profit_yoy > 0 ? '+' : ''}${data.net_profit_yoy.toFixed(1)}%` : '同比持平'} positive={data.net_profit_yoy >= 0} />
        <FinancialCard label="ROE" value={`${data.roe}%`} sub="净资产收益率" positive={data.roe >= 10} />
        <FinancialCard label="业绩评级" value={data.reason} sub="最新季度" positive={data.reason.includes('达标')} />
      </div>
    </div>
  );
}

function FinancialCard({ label, value, sub, positive }: { label: string; value: string; sub: string; positive: boolean }) {
  return (
    <div style={{
      padding: '12px 14px',
      borderRadius: 8,
      background: 'var(--bg-secondary)',
      border: '1px solid var(--border-color)',
    }}>
      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>{label}</div>
      <div style={{
        fontSize: 18,
        fontWeight: 700,
        color: positive ? 'var(--accent-red)' : 'var(--accent-green)',
        fontFamily: '"JetBrains Mono", ui-monospace, monospace',
      }}>
        {value}
      </div>
      <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>{sub}</div>
    </div>
  );
}