import { PageHeader } from '../app/layout/PageHeader';

export function EvaluationPage() {
  return (
    <div>
      <PageHeader title="评估报告" />
      <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>即将接入 `/api/evaluation/*`。</div>
    </div>
  );
}

