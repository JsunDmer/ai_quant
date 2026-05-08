import { useEffect, useState } from 'react';
import { apiGet } from '../api/client';
import type { FinancialData } from '../api/types';

type CacheEntry = { ts: number; data: FinancialData };

const cache = new Map<string, CacheEntry>();
const inflight = new Map<string, Promise<FinancialData>>();
const CACHE_TTL_MS = 15 * 60 * 1000;

function readCache(stockCode: string): FinancialData | null {
  const hit = cache.get(stockCode);
  if (!hit) return null;
  if (Date.now() - hit.ts > CACHE_TTL_MS) {
    cache.delete(stockCode);
    return null;
  }
  return hit.data;
}

async function fetchStockFinancialData(stockCode: string): Promise<FinancialData> {
  const cached = readCache(stockCode);
  if (cached) return cached;
  const running = inflight.get(stockCode);
  if (running) return running;
  const req = apiGet<FinancialData>(`/api/signals/stock/${stockCode}/financial`)
    .then((d) => {
      cache.set(stockCode, { ts: Date.now(), data: d });
      return d;
    })
    .finally(() => {
      inflight.delete(stockCode);
    });
  inflight.set(stockCode, req);
  return req;
}

export function prefetchStockFinancialData(stockCode: string): void {
  const code = (stockCode || '').trim();
  if (!code) return;
  void fetchStockFinancialData(code);
}

export function StockFinancials({ stockCode, compact = false }: { stockCode: string; compact?: boolean }) {
  const [data, setData] = useState<FinancialData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    setLoading(true);

    const cached = readCache(stockCode);
    if (cached) {
      setData(cached);
      setLoading(false);
      return;
    }

    fetchStockFinancialData(stockCode)
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

  if (loading) return <div style={{ padding: compact ? 12 : 20, textAlign: 'center', color: 'var(--text-muted)' }}>加载财务数据...</div>;
  if (!data || !data.has_data) return <div style={{ padding: compact ? 12 : 20, textAlign: 'center', color: 'var(--text-muted)' }}>暂无财务数据</div>;

  return (
    <div style={{ marginTop: compact ? 10 : 16 }}>
      <div style={{ fontSize: compact ? 11 : 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: compact ? 8 : 10 }}>2026年一季度财务</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: compact ? 8 : 12 }}>
        <FinancialCard
          compact={compact}
          label="净利润"
          value={`${data.net_profit}亿`}
          sub={data.net_profit_yoy !== 0 ? `同比${data.net_profit_yoy > 0 ? '+' : ''}${data.net_profit_yoy.toFixed(1)}%` : '同比持平'}
          positive={data.net_profit_yoy >= 0}
        />
        <FinancialCard compact={compact} label="ROE" value={`${data.roe}%`} sub="净资产收益率" positive={data.roe >= 10} />
        <FinancialCard compact={compact} label="业绩评级" value={data.reason} sub="最新季度" positive={data.reason.includes('达标')} />
      </div>
    </div>
  );
}

function FinancialCard({
  label,
  value,
  sub,
  positive,
  compact = false,
}: {
  label: string;
  value: string;
  sub: string;
  positive: boolean;
  compact?: boolean;
}) {
  return (
    <div style={{
      padding: compact ? '9px 10px' : '12px 14px',
      borderRadius: 8,
      background: 'var(--bg-secondary)',
      border: '1px solid var(--border-color)',
    }}>
      <div style={{ fontSize: compact ? 10 : 11, color: 'var(--text-muted)', marginBottom: 4 }}>{label}</div>
      <div style={{
        fontSize: compact ? 15 : 18,
        fontWeight: 700,
        color: positive ? 'var(--accent-red)' : 'var(--accent-green)',
        fontFamily: '"JetBrains Mono", ui-monospace, monospace',
      }}>
        {value}
      </div>
      <div style={{ fontSize: compact ? 9 : 10, color: 'var(--text-muted)', marginTop: 2 }}>{sub}</div>
    </div>
  );
}