import type { ReactNode } from 'react';

export function AppLayout(props: { sidebar: ReactNode; children: ReactNode }) {
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: '300px 1fr',
        minHeight: '100vh',
      }}
    >
      <div
        style={{
          background: 'var(--bg-card)',
          borderRight: '1px solid var(--border-color)',
          padding: 12,
          boxSizing: 'border-box',
        }}
      >
        {props.sidebar}
      </div>
      <div
        style={{
          background: 'var(--bg-primary)',
          padding: 20,
          boxSizing: 'border-box',
        }}
      >
        {props.children}
      </div>
    </div>
  );
}

