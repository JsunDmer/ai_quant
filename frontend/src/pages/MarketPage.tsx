import { useEffect, useState } from 'react';
import { ApiError, apiGet } from '../api/client';
import type { MarketLatestResponse } from '../api/types';
import { PageHeader } from '../app/layout/PageHeader';

export function MarketPage(props: { refreshKey: number }) {
  const [data, setData] = useState<MarketLatestResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(null);
    setData(null);

    apiGet<MarketLatestResponse>('/api/market/latest')
      .then((d) => {
        if (!alive) return;
        setData(d);
      })
      .catch((e) => {
        if (!alive) return;
        if (e instanceof ApiError && e.status === 404) {
          setError('暂无市场数据，请先点击侧边栏「执行分析」生成数据。');
        } else {
          setError('加载失败，请稍后重试。');
        }
      })
      .finally(() => {
        if (!alive) return;
        setLoading(false);
      });

    return () => {
      alive = false;
    };
  }, [props.refreshKey]);

  return (
    <div>
      <PageHeader title="市场分析" subtitle={data ? `交易日：${data.trade_date}` : undefined} />

      {loading ? (
        <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>加载中...</div>
      ) : null}

      {error ? (
        <div
          style={{
            marginTop: 12,
            padding: '12px 16px',
            background: 'var(--bg-card)',
            border: '1px solid var(--border-color)',
            borderRadius: 8,
            fontSize: 13,
            color: 'var(--text-secondary)',
          }}
        >
          {error}
        </div>
      ) : null}

      {data ? (
        <div
          style={{
            marginTop: 12,
            padding: '12px 16px',
            background: 'var(--bg-card)',
            border: '1px solid var(--border-color)',
            borderRadius: 8,
          }}
        >
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
            <Metric label="指数条目" value={String(Array.isArray(data.indices) ? data.indices.length : 0)} />
            <Metric label="新闻条目" value={String(Array.isArray(data.news) ? data.news.length : 0)} />
            <Metric label="状态" value={data.status} />
          </div>
        </div>
      ) : null}
    </div>
  );
}

function Metric(props: { label: string; value: string }) {
  return (
    <div
      style={{
        minWidth: 140,
        background: 'var(--bg-card)',
        border: '1px solid var(--border-color)',
        borderRadius: 8,
        padding: '12px 16px',
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      <div style={{ color: 'var(--text-secondary)', fontSize: 11, fontWeight: 500, letterSpacing: 0.3, textTransform: 'uppercase' }}>
        {props.label}
      </div>
      <div style={{ marginTop: 6, color: 'var(--text-primary)', fontFamily: '"JetBrains Mono", ui-monospace, monospace', fontWeight: 600, fontSize: 18 }}>
        {props.value}
      </div>
    </div>
  );
}

