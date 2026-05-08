import { useEffect, useState } from 'react';
import { apiGet } from '../api/client';
import type { SignalItem, SignalsLatestResponse } from '../api/types';
import { PageHeader } from '../app/layout/PageHeader';
import { StockChart } from '../components/StockChart';
import { StockFinancials } from '../components/StockFinancials';

export function SignalsPage(props: { refreshKey: number }) {
  const [items, setItems] = useState<SignalItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setError(null);
    apiGet<SignalsLatestResponse>('/api/signals/latest?limit=50')
      .then((d) => {
        if (!alive) return;
        setItems(d.items ?? []);
      })
      .catch(() => {
        if (!alive) return;
        setError('加载失败');
      });
    return () => {
      alive = false;
    };
  }, [props.refreshKey]);

  return (
    <div>
      <PageHeader title="个股分析" />
      {error ? <div className="ui-state ui-state--error">{error}</div> : null}
      {items ? (
        items.length > 0 ? (
        <div className="ui-table-scroll" style={{ marginTop: 12 }}>
          <div style={{ minWidth: 820 }}>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'minmax(100px, 1.5fr) minmax(100px, 1.5fr) minmax(72px, 1fr) minmax(80px, 1fr) minmax(96px, 1fr) minmax(120px, 1.4fr) minmax(72px, 1fr)',
                gap: 0,
                padding: '10px 12px',
                borderBottom: '1px solid var(--border-color)',
                fontSize: 12,
                color: 'var(--text-secondary)',
                fontWeight: 600,
              }}
            >
              <div>股票</div>
              <div>板块</div>
              <div>信号</div>
              <div>最新价</div>
              <div>盘中涨跌</div>
              <div>竞价标签</div>
              <div>置信度</div>
            </div>
            {items.map((it, idx) => (
              <SignalRow key={idx} item={it} />
            ))}
          </div>
        </div>
        ) : (
          <div className="ui-state ui-state--muted" style={{ marginTop: 12 }}>
            暂无个股买入信号（本次分析未筛出满足条件的个股）。
          </div>
        )
      ) : (
        <div className="ui-state ui-state--muted" style={{ marginTop: 12 }}>
          加载中…
        </div>
      )}
    </div>
  );
}

function SignalRow(props: { item: SignalItem }) {
  const it = props.item ?? {};
  const [expanded, setExpanded] = useState(false);
  const realtime = it.realtime;
  const auction = it.auction;
  const changePercent = toNumber(realtime?.change_percent, 0);
  const price = toNumber(realtime?.price, 0);
  const auctionTag = String(auction?.tag ?? '无竞价数据');
  const auctionColor = auctionTag.includes('偏弱')
    ? 'var(--accent-green)'
    : auctionTag.includes('偏强') || auctionTag.includes('偏多')
      ? 'var(--accent-red)'
      : 'var(--text-muted)';

  const plainCode = String(it.stock_code ?? '').replace(/^(sh|sz)\./, '');

  return (
    <div>
      <div
        onClick={(e) => {
          e.stopPropagation();
          setExpanded(!expanded);
        }}
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(100px, 1.5fr) minmax(100px, 1.5fr) minmax(72px, 1fr) minmax(80px, 1fr) minmax(96px, 1fr) minmax(120px, 1.4fr) minmax(72px, 1fr)',
          padding: '10px 12px',
          borderBottom: '1px solid var(--border-color)',
          fontSize: 13,
          alignItems: 'center',
          gap: 0,
          cursor: 'pointer',
          background: expanded ? 'var(--bg-secondary)' : 'transparent',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontWeight: 600 }}>{it.stock_name ?? it.stock_code ?? '—'}</span>
          <span style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'monospace' }}>{plainCode}</span>
          <span style={{
            fontSize: 10,
            color: 'var(--text-muted)',
            transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
            transition: 'transform 0.2s',
          }}>▼</span>
        </div>
        <div style={{ color: 'var(--text-secondary)' }}>{it.sector_name ?? '—'}</div>
        <div>{it.signal ?? '—'}</div>
        <div style={{ fontFamily: '"JetBrains Mono", ui-monospace, monospace' }}>
          {price > 0 ? price.toFixed(2) : '—'}
        </div>
        <div style={{ color: changePercent > 0 ? 'var(--accent-red)' : changePercent < 0 ? 'var(--accent-green)' : 'var(--text-muted)', fontFamily: '"JetBrains Mono", ui-monospace, monospace', fontWeight: 600 }}>
          {formatSignedPercent(changePercent)}
        </div>
        <div>
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              padding: '2px 8px',
              borderRadius: 999,
              border: '1px solid var(--border-color)',
              color: auctionColor,
              background: 'var(--bg-secondary)',
              fontSize: 11,
              fontWeight: 600,
            }}
          >
            {auctionTag}
          </span>
        </div>
        <div style={{ fontFamily: '"JetBrains Mono", ui-monospace, monospace' }}>
          {typeof it.confidence === 'number' ? (it.confidence * 100).toFixed(0) + '%' : String(it.confidence ?? '—')}
        </div>
      </div>
      {expanded && plainCode && (
        <div style={{
          padding: '16px 20px',
          borderBottom: '1px solid var(--border-color)',
          background: 'var(--bg-secondary)',
        }}
        >
          <StockChart stockCode={plainCode} />
          <StockFinancials stockCode={plainCode} />
        </div>
      )}
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

function formatSignedPercent(v: number): string {
  if (!Number.isFinite(v)) return '—';
  const sign = v > 0 ? '+' : '';
  return `${sign}${v.toFixed(2)}%`;
}