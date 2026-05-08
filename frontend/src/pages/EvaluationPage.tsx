import { useEffect, useState } from 'react';
import { apiGet, apiPost } from '../api/client';
import { PageHeader } from '../app/layout/PageHeader';

type AccuracyBucket = {
  total?: number;
  correct?: number;
  accuracy?: number;
};

type SectorSummary = {
  t1?: AccuracyBucket;
  t3?: AccuracyBucket;
  t5?: AccuracyBucket;
};

type RecommendationBucket = {
  evaluated_count?: number;
  hit_count?: number;
  hit_rate?: number;
  avg_return?: number;
  avg_excess_return?: number;
};

type RecommendationSummary = {
  total_recommendations?: number;
  t1?: RecommendationBucket;
  t3?: RecommendationBucket;
  t5?: RecommendationBucket;
};

export function EvaluationPage(props: { refreshKey: number }) {
  const [summary, setSummary] = useState<SectorSummary | null>(null);
  const [recommendationSummary, setRecommendationSummary] = useState<RecommendationSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = () => {
    let alive = true;
    setLoading(true);
    setError(null);
    Promise.all([
      apiGet<{ summary: SectorSummary }>('/api/evaluation/summary'),
      apiGet<{ summary: RecommendationSummary }>('/api/evaluation/recommendations/summary'),
    ])
      .then(([sectorResp, recoResp]) => {
        if (!alive) return;
        setSummary(sectorResp.summary ?? null);
        setRecommendationSummary(recoResp.summary ?? null);
      })
      .catch(() => {
        if (!alive) return;
        setError('加载失败');
      })
      .finally(() => {
        if (!alive) return;
        setLoading(false);
      });
    return () => {
      alive = false;
    };
  };

  useEffect(() => {
    return loadData();
  }, [props.refreshKey]);

  const onRunRecommendationEvaluation = async () => {
    setRunning(true);
    setError(null);
    try {
      await apiPost<{ evaluated: number }>('/api/evaluation/recommendations/run?recent_days=30', {});
      const resp = await apiGet<{ summary: RecommendationSummary }>('/api/evaluation/recommendations/summary');
      setRecommendationSummary(resp.summary ?? null);
    } catch {
      setError('评估计算失败');
    } finally {
      setRunning(false);
    }
  };

  return (
    <div>
      <PageHeader title="评估报告" />
      {error ? <div className="ui-state ui-state--error">{error}</div> : null}
      {loading ? (
        <div className="ui-state ui-state--muted" style={{ marginTop: 12 }}>
          加载中…
        </div>
      ) : null}

      {summary ? (
        <div style={{ marginTop: 12 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 8 }}>板块方向准确率</div>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            <SummaryCard label="T+1" value={summary.t1?.accuracy} detail={`${summary.t1?.correct ?? 0}/${summary.t1?.total ?? 0}`} />
            <SummaryCard label="T+3" value={summary.t3?.accuracy} detail={`${summary.t3?.correct ?? 0}/${summary.t3?.total ?? 0}`} />
            <SummaryCard label="T+5" value={summary.t5?.accuracy} detail={`${summary.t5?.correct ?? 0}/${summary.t5?.total ?? 0}`} />
          </div>
        </div>
      ) : null}

      <div style={{ marginTop: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, marginBottom: 8 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-secondary)' }}>个股推荐表现（1D/3D/5D）</div>
          <button
            type="button"
            onClick={onRunRecommendationEvaluation}
            disabled={running}
            style={{
              border: '1px solid var(--border-color)',
              background: 'var(--bg-secondary)',
              borderRadius: 8,
              padding: '4px 10px',
              fontSize: 12,
              color: 'var(--text-secondary)',
              cursor: running ? 'not-allowed' : 'pointer',
              opacity: running ? 0.6 : 1,
            }}
          >
            {running ? '计算中…' : '刷新推荐评估'}
          </button>
        </div>

        {recommendationSummary && (recommendationSummary.total_recommendations ?? 0) > 0 ? (
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            <RecommendationCard
              label="T+1"
              hitRate={recommendationSummary.t1?.hit_rate}
              avgReturn={recommendationSummary.t1?.avg_return}
              avgExcess={recommendationSummary.t1?.avg_excess_return}
              detail={`${recommendationSummary.t1?.hit_count ?? 0}/${recommendationSummary.t1?.evaluated_count ?? 0}`}
            />
            <RecommendationCard
              label="T+3"
              hitRate={recommendationSummary.t3?.hit_rate}
              avgReturn={recommendationSummary.t3?.avg_return}
              avgExcess={recommendationSummary.t3?.avg_excess_return}
              detail={`${recommendationSummary.t3?.hit_count ?? 0}/${recommendationSummary.t3?.evaluated_count ?? 0}`}
            />
            <RecommendationCard
              label="T+5"
              hitRate={recommendationSummary.t5?.hit_rate}
              avgReturn={recommendationSummary.t5?.avg_return}
              avgExcess={recommendationSummary.t5?.avg_excess_return}
              detail={`${recommendationSummary.t5?.hit_count ?? 0}/${recommendationSummary.t5?.evaluated_count ?? 0}`}
            />
          </div>
        ) : (
          <div className="ui-state ui-state--muted" style={{ marginTop: 8 }}>
            暂无推荐评估数据，可点击“刷新推荐评估”计算最近 30 天结果。
          </div>
        )}
      </div>
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

function RecommendationCard(props: {
  label: string;
  hitRate: unknown;
  avgReturn: unknown;
  avgExcess: unknown;
  detail: string;
}) {
  const hitRate = typeof props.hitRate === 'number' ? `${props.hitRate.toFixed(1)}%` : '—';
  const avgReturn = typeof props.avgReturn === 'number' ? `${props.avgReturn > 0 ? '+' : ''}${props.avgReturn.toFixed(2)}%` : '—';
  const avgExcess = typeof props.avgExcess === 'number' ? `${props.avgExcess > 0 ? '+' : ''}${props.avgExcess.toFixed(2)}%` : '—';
  return (
    <div
      className="surface-card surface-card--raised"
      style={{
        minWidth: 220,
        borderRadius: 8,
        padding: '12px 16px',
      }}
    >
      <div style={{ color: 'var(--text-secondary)', fontSize: 11, fontWeight: 600, letterSpacing: 0.3, textTransform: 'uppercase' }}>
        {props.label} 推荐表现
      </div>
      <div style={{ marginTop: 6, fontFamily: '"JetBrains Mono", ui-monospace, monospace', fontWeight: 700, fontSize: 18 }}>
        命中率 {hitRate}
      </div>
      <div style={{ marginTop: 4, fontSize: 12, color: 'var(--text-secondary)' }}>平均收益 {avgReturn}</div>
      <div style={{ marginTop: 2, fontSize: 12, color: 'var(--text-secondary)' }}>平均超额 {avgExcess}</div>
      <div style={{ marginTop: 2, fontSize: 12, color: 'var(--text-secondary)' }}>{props.detail}</div>
    </div>
  );
}

