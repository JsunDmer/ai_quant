import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { apiGet } from '../api/client';
import type { SignalItem, SignalsLatestResponse } from '../api/types';
import { PageHeader } from '../app/layout/PageHeader';
import { prefetchStockChartData, StockChart } from '../components/StockChart';
import { prefetchStockFinancialData, StockFinancials } from '../components/StockFinancials';

export function SignalsPage(props: { refreshKey: number }) {
  const [items, setItems] = useState<SignalItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeItem, setActiveItem] = useState<SignalItem | null>(null);

  useEffect(() => {
    let alive = true;
    setError(null);
    apiGet<SignalsLatestResponse>('/api/signals/latest?limit=10&include_realtime=0&include_auction=0')
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
              <SignalRow key={idx} item={it} onOpen={setActiveItem} />
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
      <StockDetailModal item={activeItem} onClose={() => setActiveItem(null)} />
    </div>
  );
}

function SignalRow(props: { item: SignalItem; onOpen: (item: SignalItem) => void }) {
  const it = props.item ?? {};
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

  const plainCode = normalizeStockCode(it.stock_code);

  return (
    <div>
      <div
        onMouseEnter={() => {
          if (!plainCode) return;
          prefetchStockChartData(plainCode);
          prefetchStockFinancialData(plainCode);
        }}
        onClick={(e) => {
          e.stopPropagation();
          if (!plainCode) return;
          prefetchStockChartData(plainCode);
          prefetchStockFinancialData(plainCode);
          props.onOpen(it);
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
          background: 'transparent',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontWeight: 600 }}>{it.stock_name ?? it.stock_code ?? '—'}</span>
          <span style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'monospace' }}>{plainCode}</span>
          <span style={{
            fontSize: 10,
            color: 'var(--text-muted)',
          }}>详情</span>
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
    </div>
  );
}

function StockDetailModal(props: { item: SignalItem | null; onClose: () => void }) {
  if (!props.item) return null;
  if (typeof document === 'undefined') return null;
  const plainCode = normalizeStockCode(props.item.stock_code);
  const modal = (
    <div
      onClick={props.onClose}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(2, 6, 23, 0.45)',
        backdropFilter: 'blur(2px)',
        zIndex: 1100,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '10px 14px',
        overflow: 'hidden',
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: 'min(1560px, 98vw)',
          height: 'min(940px, calc(100vh - 20px))',
          borderRadius: 12,
          border: '1px solid var(--border-color)',
          background: 'var(--bg-card)',
          boxShadow: '0 20px 50px rgba(0, 0, 0, 0.25)',
          overflow: 'hidden',
          display: 'grid',
          gridTemplateRows: 'auto 1fr',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '12px 16px',
            borderBottom: '1px solid var(--border-color)',
            background: 'var(--bg-card)',
            zIndex: 1,
          }}
        >
          <div style={{ fontSize: 14, fontWeight: 700 }}>
            {props.item.stock_name ?? props.item.stock_code ?? '个股详情'}
            <span style={{ marginLeft: 8, fontSize: 12, color: 'var(--text-muted)', fontFamily: 'monospace' }}>{plainCode}</span>
          </div>
          <button
            type="button"
            onClick={props.onClose}
            style={{
              border: '1px solid var(--border-color)',
              background: 'var(--bg-primary)',
              borderRadius: 8,
              padding: '4px 10px',
              fontSize: 12,
              cursor: 'pointer',
              color: 'var(--text-secondary)',
            }}
          >
            关闭
          </button>
        </div>
        <div style={{ padding: '10px 12px 12px', overflow: 'hidden' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 2fr) minmax(360px, 1fr)', gap: 12, height: '100%' }}>
            <div
              style={{
                border: '1px solid var(--border-color)',
                borderRadius: 10,
                background: 'var(--bg-primary)',
                padding: '8px 10px',
                overflow: 'hidden',
              }}
            >
              {plainCode ? <StockChart stockCode={plainCode} chartHeight="min(50vh, 430px)" compact /> : null}
            </div>
            <div
              style={{
                border: '1px solid var(--border-color)',
                borderRadius: 10,
                background: 'var(--bg-primary)',
                padding: '10px 12px',
                display: 'grid',
                alignContent: 'start',
                gap: 8,
                overflow: 'hidden',
              }}
            >
              <StockOverview item={props.item} compact />
              {plainCode ? <StockFinancials stockCode={plainCode} compact /> : null}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
  return createPortal(modal, document.body);
}

function StockOverview({ item, compact = false }: { item: SignalItem; compact?: boolean }) {
  const realtime = item.realtime;
  const auction = item.auction;
  const price = toNumber(realtime?.price, 0);
  const preClose = toNumber(realtime?.pre_close, 0);
  const changeAmount = toNumber(realtime?.change_amount, 0);
  const changePercent = toNumber(realtime?.change_percent, 0);
  const confidence = typeof item.confidence === 'number' ? `${(item.confidence * 100).toFixed(0)}%` : '—';
  const factors = Array.isArray(item.factors) ? item.factors : [];
  const factorViews = factors.map((f, idx) => toFactorView(f, idx));
  const bullishFactors = factorViews.filter((f) => f.tone === 'bullish');
  const bearishFactors = factorViews.filter((f) => f.tone === 'bearish');
  const neutralFactors = factorViews.filter((f) => f.tone === 'neutral');

  return (
    <div style={{ marginBottom: compact ? 4 : 12 }}>
      <div style={{ fontSize: compact ? 11 : 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: compact ? 6 : 8 }}>个股关键信息</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: compact ? 8 : 10 }}>
        <OverviewCard compact={compact} label="最新价 / 昨收" value={price > 0 ? `${price.toFixed(2)} / ${preClose.toFixed(2)}` : '—'} positive={changePercent >= 0} />
        <OverviewCard compact={compact} label="盘中涨跌" value={`${changeAmount >= 0 ? '+' : ''}${changeAmount.toFixed(2)} (${formatSignedPercent(changePercent)})`} positive={changePercent >= 0} />
        <OverviewCard compact={compact} label="交易信号 / 置信度" value={`${item.signal ?? '—'} / ${confidence}`} positive={toNumber(item.confidence, 0) >= 0.7} />
        <OverviewCard
          compact={compact}
          label="竞价表现"
          value={`${auction?.tag ?? '无竞价数据'}${auction?.has_data ? ` (${toNumber(auction.pct_change, 0).toFixed(2)}%)` : ''}`}
          positive={!(auction?.tag ?? '').includes('偏弱')}
        />
      </div>
      <div style={{ marginTop: compact ? 8 : 10 }}>
        <div style={{ fontSize: compact ? 11 : 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 8 }}>信号因子解读</div>
        {factorViews.length > 0 ? (
          <div style={{ display: 'grid', gap: compact ? 8 : 10 }}>
            {bullishFactors.length > 0 ? <FactorGroup compact={compact} title={`看多因子 (${bullishFactors.length})`} tone="bullish" items={bullishFactors} /> : null}
            {bearishFactors.length > 0 ? <FactorGroup compact={compact} title={`看空因子 (${bearishFactors.length})`} tone="bearish" items={bearishFactors} /> : null}
            {neutralFactors.length > 0 ? <FactorGroup compact={compact} title={`中性因子 (${neutralFactors.length})`} tone="neutral" items={neutralFactors} /> : null}
          </div>
        ) : (
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>暂无触发因子说明</span>
        )}
      </div>
    </div>
  );
}

function FactorGroup(props: { title: string; tone: FactorTone; items: FactorView[]; compact?: boolean }) {
  return (
    <div>
      <div style={{ fontSize: props.compact ? 10 : 11, color: 'var(--text-muted)', marginBottom: 6 }}>{props.title}</div>
      <div style={{ display: 'grid', gridTemplateColumns: `repeat(auto-fit, minmax(${props.compact ? 180 : 220}px, 1fr))`, gap: props.compact ? 6 : 8 }}>
        {props.items.map((factor) => (
          <FactorCard key={factor.key} factor={factor} tone={props.tone} compact={props.compact} />
        ))}
      </div>
    </div>
  );
}

function FactorCard(props: { factor: FactorView; tone: FactorTone; compact?: boolean }) {
  const color = props.tone === 'bullish'
    ? 'var(--accent-red)'
    : props.tone === 'bearish'
      ? 'var(--accent-green)'
      : 'var(--text-secondary)';
  const label = props.factor.direction === 'up' ? '上行' : props.factor.direction === 'down' ? '下行' : '中性';
  return (
    <div
      style={{
        border: '1px solid var(--border-color)',
        borderRadius: 8,
        background: 'var(--bg-primary)',
        padding: props.compact ? '6px 8px' : '8px 10px',
        display: 'grid',
        gap: props.compact ? 3 : 4,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
        <span style={{ fontSize: props.compact ? 11 : 12, fontWeight: 600, color: 'var(--text-primary)' }}>{props.factor.name}</span>
        <span style={{
          fontSize: props.compact ? 9 : 10,
          color,
          border: '1px solid var(--border-color)',
          borderRadius: 999,
          padding: '1px 6px',
          background: 'var(--bg-secondary)',
          fontWeight: 600,
        }}
        >
          {label}
        </span>
      </div>
      <div style={{ fontSize: props.compact ? 11 : 12, color, fontFamily: '"JetBrains Mono", ui-monospace, monospace', fontWeight: 600 }}>
        {props.factor.value || '—'}
      </div>
    </div>
  );
}

function OverviewCard({
  label,
  value,
  positive,
  compact = false,
}: {
  label: string;
  value: string;
  positive: boolean;
  compact?: boolean;
}) {
  return (
    <div
      style={{
        padding: compact ? '8px 10px' : '10px 12px',
        borderRadius: 8,
        border: '1px solid var(--border-color)',
        background: 'var(--bg-primary)',
      }}
    >
      <div style={{ fontSize: compact ? 10 : 11, color: 'var(--text-muted)', marginBottom: 4 }}>{label}</div>
      <div style={{
        fontSize: compact ? 12 : 13,
        fontWeight: 700,
        fontFamily: '"JetBrains Mono", ui-monospace, monospace',
        color: positive ? 'var(--accent-red)' : 'var(--accent-green)',
      }}
      >
        {value}
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

function formatSignedPercent(v: number): string {
  if (!Number.isFinite(v)) return '—';
  const sign = v > 0 ? '+' : '';
  return `${sign}${v.toFixed(2)}%`;
}

type FactorTone = 'bullish' | 'bearish' | 'neutral';
type FactorDirection = 'up' | 'down' | 'flat';
type FactorView = {
  key: string;
  name: string;
  value: string;
  direction: FactorDirection;
  tone: FactorTone;
};

function toFactorView(raw: unknown, idx: number): FactorView {
  if (raw && typeof raw === 'object' && !Array.isArray(raw)) {
    const obj = raw as Record<string, unknown>;
    const name = String(obj.name ?? obj.factor_name ?? `因子${idx + 1}`);
    const value = String(obj.value ?? obj.detail ?? obj.desc ?? '').trim();
    const directionRaw = String(obj.direction ?? obj.trend ?? '').toLowerCase();
    const direction: FactorDirection = directionRaw === 'up' ? 'up' : directionRaw === 'down' ? 'down' : 'flat';
    return {
      key: `${name}-${idx}`,
      name,
      value,
      direction,
      tone: direction === 'up' ? 'bullish' : direction === 'down' ? 'bearish' : 'neutral',
    };
  }

  const text = String(raw ?? '').trim();
  return {
    key: `factor-${idx}`,
    name: text || `因子${idx + 1}`,
    value: '',
    direction: 'flat',
    tone: 'neutral',
  };
}

function normalizeStockCode(raw: unknown): string {
  const code = String(raw ?? '').trim();
  if (!code) return '';
  return code
    .replace(/^(sh|sz)\./i, '')
    .replace(/\.(sh|sz)$/i, '')
    .trim();
}