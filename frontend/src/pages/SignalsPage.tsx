import { useEffect, useState } from 'react';
import { apiGet } from '../api/client';
import { PageHeader } from '../app/layout/PageHeader';

export function SignalsPage() {
  const [items, setItems] = useState<any[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setError(null);
    apiGet<{ items: any[] }>('/api/signals/latest?limit=50')
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
  }, []);

  return (
    <div>
      <PageHeader title="个股分析" />
      {error ? <div style={{ fontSize: 13, color: 'var(--accent-red)' }}>{error}</div> : null}
      {items ? (
        <div
          style={{
            marginTop: 12,
            background: 'var(--bg-card)',
            border: '1px solid var(--border-color)',
            borderRadius: 8,
            overflow: 'hidden',
          }}
        >
          <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr 90px 90px', gap: 0, padding: '10px 12px', borderBottom: '1px solid var(--border-color)', fontSize: 12, color: 'var(--text-secondary)' }}>
            <div>股票</div>
            <div>板块</div>
            <div>信号</div>
            <div>置信度</div>
          </div>
          {items.map((it, idx) => (
            <div key={idx} style={{ display: 'grid', gridTemplateColumns: '120px 1fr 90px 90px', padding: '10px 12px', borderBottom: '1px solid var(--border-color)', fontSize: 13 }}>
              <div style={{ fontFamily: '"JetBrains Mono", ui-monospace, monospace' }}>{it.stock_code ?? '—'}</div>
              <div style={{ color: 'var(--text-secondary)' }}>{it.sector_name ?? '—'}</div>
              <div>{it.signal ?? '—'}</div>
              <div style={{ fontFamily: '"JetBrains Mono", ui-monospace, monospace' }}>
                {typeof it.confidence === 'number' ? (it.confidence * 100).toFixed(0) + '%' : String(it.confidence ?? '—')}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>加载中…</div>
      )}
    </div>
  );
}

