import type { ReactNode } from 'react';

export function AppLayout(props: {
  sidebar: ReactNode;
  children: ReactNode;
  collapsed: boolean;
}) {
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: props.collapsed ? '64px 1fr' : '280px 1fr',
        minHeight: '100vh',
        transition: 'grid-template-columns 0.3s ease',
      }}
    >
      <div
        style={{
          background: 'var(--bg-card)',
          borderRight: '1px solid var(--border-color)',
          padding: props.collapsed ? '12px 8px' : '12px',
          boxSizing: 'border-box',
          transition: 'all 0.3s ease',
          /* 不与主区等高拉伸：否则市场页很长时，侧栏底部按钮被顶到页面最下方 */
          alignSelf: 'start',
          position: 'sticky',
          top: 0,
          height: '100vh',
          maxHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          overflowY: 'auto',
        }}
      >
        {props.sidebar}
      </div>
      <div
        style={{
          background: 'var(--bg-primary)',
          padding: 24,
          boxSizing: 'border-box',
          maxWidth: '100%',
        }}
      >
        <div style={{ maxWidth: 1400, margin: '0 auto' }}>
          {props.children}
        </div>
      </div>
    </div>
  );
}

