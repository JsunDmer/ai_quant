import { useEffect, useRef } from 'react';
import * as echarts from 'echarts';

import { getChartTokens, type ChartPalette } from './chartTokens';

export function EChart(props: {
  option: echarts.EChartsOption;
  style?: React.CSSProperties;
  chartPalette: ChartPalette;
}) {
  const elRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    const el = elRef.current;
    if (!el) return;

    let chart = chartRef.current;
    if (!chart || chart.isDisposed?.()) {
      chart = echarts.init(el, undefined, { renderer: 'canvas' });
      chartRef.current = chart;
    }

    const tokens = getChartTokens(props.chartPalette);
    chart.setOption(
      {
        backgroundColor: tokens.bgCard,
        textStyle: {
          color: tokens.textPrimary,
          fontFamily: '"Noto Sans SC", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
        },
        ...props.option,
      },
      { notMerge: true, lazyUpdate: false }
    );
    chart.resize();

    const ro = new ResizeObserver(() => {
      const c = chartRef.current;
      if (c && !c.isDisposed?.()) c.resize();
    });
    ro.observe(el);

    return () => {
      ro.disconnect();
    };
  }, [props.option, props.chartPalette]);

  useEffect(() => {
    return () => {
      const c = chartRef.current;
      if (c && !c.isDisposed?.()) {
        c.dispose();
      }
      chartRef.current = null;
    };
  }, []);

  return (
    <div
      ref={elRef}
      style={{
        width: '100%',
        height: 280,
        borderRadius: 8,
        overflow: 'hidden',
        ...props.style,
      }}
    />
  );
}
