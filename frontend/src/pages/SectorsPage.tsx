import { PageHeader } from '../app/layout/PageHeader';

export function SectorsPage() {
  return (
    <div>
      <PageHeader title="板块分析" />
      <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>即将接入 `/api/sectors/latest`。</div>
    </div>
  );
}

