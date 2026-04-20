export function PageHeader(props: { title: string; subtitle?: string }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ fontSize: 18, fontWeight: 600 }}>{props.title}</div>
      {props.subtitle ? (
        <div style={{ marginTop: 2, fontSize: 13, color: 'var(--text-secondary)' }}>{props.subtitle}</div>
      ) : null}
    </div>
  );
}

