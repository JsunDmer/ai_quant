import { useEffect, useRef, useState } from 'react';
import * as echarts from 'echarts';

import { readTokens } from './tokens';

export function EChart(props: { option: echarts.EChartsOption; style?: React.CSSProperties }) {
  const elRef = useRef<HTMLDivElement | null>(null);
  const [themeKey, setThemeKey] = useState<string>(() => document.documentElement.getAttribute('data-theme') ?? 'light');

  useEffect(() => {
    const el = document.documentElement;
    const mo = new MutationObserver(() => {
      setThemeKey(document.documentElement.getAttribute('data-theme') ?? 'light');
    });
    mo.observe(el, { attributes: true, attributeFilter: ['data-theme'] });
    return () => mo.disconnect();
  }, []);

  useEffect(() => {
    const el = elRef.current;
    if (!el) return;

    const tokens = readTokens();
    const chart = echarts.init(el, undefined, { renderer: 'canvas' });

    chart.setOption(
      {
        backgroundColor: 'transparent',
        textStyle: {
          color: tokens.textPrimary,
          fontFamily: '"Noto Sans SC", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
        },
        ...props.option,
      },
      { notMerge: true }
    );

    const ro = new ResizeObserver(() => chart.resize());
    ro.observe(el);

    return () => {
      ro.disconnect();
      chart.dispose();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.option, themeKey]);

  return (
    <div
      ref={elRef}
      style={{
        width: '100%',
        height: 280,
        ...props.style,
      }}
    />
  );
}

