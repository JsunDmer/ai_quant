import { useEffect, useState } from 'react';
import { apiGet } from '../api/client';
import { PageHeader } from '../app/layout/PageHeader';

export function SignalsPage(props: { refreshKey: number }) {
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
  }, [props.refreshKey]);

  return (
    <div>
      <PageHeader title="个股分析" />
      {error ? <div className="ui-state ui-state--error">{error}</div> : null}
      {items ? (
        items.length > 0 ? (
        <div className="ui-table-scroll" style={{ marginTop: 12 }}>
          <div style={{ minWidth: 480 }}>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'minmax(88px, 1fr) minmax(120px, 2fr) minmax(72px, 1fr) minmax(72px, 1fr)',
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
              <div>置信度</div>
            </div>
            {items.map((it, idx) => (
              <div
                key={idx}
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'minmax(88px, 1fr) minmax(120px, 2fr) minmax(72px, 1fr) minmax(72px, 1fr)',
                  padding: '10px 12px',
                  borderBottom: '1px solid var(--border-color)',
                  fontSize: 13,
                  alignItems: 'center',
                }}
              >
                <div style={{ fontFamily: '"JetBrains Mono", ui-monospace, monospace' }}>{it.stock_code ?? '—'}</div>
                <div style={{ color: 'var(--text-secondary)' }}>{it.sector_name ?? '—'}</div>
                <div>{it.signal ?? '—'}</div>
                <div style={{ fontFamily: '"JetBrains Mono", ui-monospace, monospace' }}>
                  {typeof it.confidence === 'number' ? (it.confidence * 100).toFixed(0) + '%' : String(it.confidence ?? '—')}
                </div>
              </div>
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

