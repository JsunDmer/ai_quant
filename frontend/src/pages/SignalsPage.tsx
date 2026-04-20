import { PageHeader } from '../app/layout/PageHeader';

export function SignalsPage() {
  return (
    <div>
      <PageHeader title="个股分析" />
      <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>即将接入 `/api/signals/latest`。</div>
    </div>
  );
}

