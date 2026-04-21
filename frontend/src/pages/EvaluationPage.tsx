import { useEffect, useState } from 'react';
import { apiGet } from '../api/client';
import { PageHeader } from '../app/layout/PageHeader';

export function EvaluationPage(props: { refreshKey: number }) {
  const [summary, setSummary] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setError(null);
    apiGet<{ summary: any }>('/api/evaluation/summary')
      .then((d) => {
        if (!alive) return;
        setSummary(d.summary ?? null);
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
      <PageHeader title="评估报告" />
      {error ? <div className="ui-state ui-state--error">{error}</div> : null}
      {summary ? (
        <div style={{ marginTop: 12, display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <SummaryCard label="T+1" value={summary.t1?.accuracy} detail={`${summary.t1?.correct ?? 0}/${summary.t1?.total ?? 0}`} />
          <SummaryCard label="T+3" value={summary.t3?.accuracy} detail={`${summary.t3?.correct ?? 0}/${summary.t3?.total ?? 0}`} />
          <SummaryCard label="T+5" value={summary.t5?.accuracy} detail={`${summary.t5?.correct ?? 0}/${summary.t5?.total ?? 0}`} />
        </div>
      ) : (
        <div className="ui-state ui-state--muted" style={{ marginTop: 12 }}>
          加载中…
        </div>
      )}
    </div>
  );
}

function SummaryCard(props: { label: string; value: unknown; detail: string }) {
  const v = typeof props.value === 'number' ? `${props.value.toFixed(1)}%` : '—';
  return (
    <div
      className="surface-card surface-card--raised"
      style={{
        minWidth: 180,
        borderRadius: 8,
        padding: '12px 16px',
      }}
    >
      <div style={{ color: 'var(--text-secondary)', fontSize: 11, fontWeight: 600, letterSpacing: 0.3, textTransform: 'uppercase' }}>
        {props.label} 准确率
      </div>
      <div style={{ marginTop: 6, fontFamily: '"JetBrains Mono", ui-monospace, monospace', fontWeight: 700, fontSize: 18 }}>
        {v}
      </div>
      <div style={{ marginTop: 2, fontSize: 12, color: 'var(--text-secondary)' }}>{props.detail}</div>
    </div>
  );
}

