import { useEffect, useState } from 'react';
import { apiGet } from '../api/client';
import { PageHeader } from '../app/layout/PageHeader';

export function SectorsPage() {
  const [items, setItems] = useState<any[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setError(null);
    apiGet<{ items: any[] }>('/api/sectors/latest')
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
      <PageHeader title="板块分析" />
      {error ? <div style={{ fontSize: 13, color: 'var(--accent-red)' }}>{error}</div> : null}
      {items ? (
        <div style={{ marginTop: 12, display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 12 }}>
          {items.slice(0, 20).map((it, idx) => (
            <div
              key={idx}
              style={{
                background: 'var(--bg-card)',
                border: '1px solid var(--border-color)',
                borderRadius: 8,
                padding: '12px 16px',
              }}
            >
              <div style={{ fontWeight: 600 }}>{it.sector_name ?? it.name ?? '—'}</div>
              <div style={{ marginTop: 4, fontSize: 12, color: 'var(--text-secondary)' }}>
                direction: {String(it.direction ?? '—')} | confidence: {String(it.confidence ?? '—')} | score: {String(it.rec_score ?? '—')}
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

