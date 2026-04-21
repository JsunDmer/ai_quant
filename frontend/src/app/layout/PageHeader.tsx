export function PageHeader(props: { title: string; subtitle?: string }) {
  return (
    <header
      style={{
        marginBottom: 20,
        paddingBottom: 14,
        borderBottom: '1px solid var(--border-color)',
      }}
    >
      <h1
        style={{
          margin: 0,
          fontSize: 22,
          fontWeight: 700,
          letterSpacing: '-0.02em',
          lineHeight: 1.25,
          color: 'var(--text-primary)',
        }}
      >
        {props.title}
      </h1>
      {props.subtitle ? (
        <p
          style={{
            margin: '6px 0 0',
            fontSize: 14,
            color: 'var(--text-secondary)',
            fontWeight: 500,
          }}
        >
          {props.subtitle}
        </p>
      ) : null}
    </header>
  );
}

