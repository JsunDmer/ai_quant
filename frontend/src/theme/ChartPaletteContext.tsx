import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';
import type { ChartPalette } from '../charts/chartTokens';

const STORAGE_KEY = 'ai_quant_chart_palette';

function readStoredPalette(): ChartPalette {
  if (typeof window === 'undefined') return 'light';
  const v = window.localStorage.getItem(STORAGE_KEY);
  if (v === 'light' || v === 'dark') return v;
  return 'light';
}

type Ctx = {
  chartPalette: ChartPalette;
  setChartPalette: (p: ChartPalette) => void;
};

const ChartPaletteContext = createContext<Ctx | null>(null);

export function ChartPaletteProvider(props: { children: ReactNode }) {
  const [chartPalette, setState] = useState<ChartPalette>(() => readStoredPalette());

  const setChartPalette = useCallback((p: ChartPalette) => {
    window.localStorage.setItem(STORAGE_KEY, p);
    setState(p);
  }, []);

  const value = useMemo(() => ({ chartPalette, setChartPalette }), [chartPalette, setChartPalette]);

  return <ChartPaletteContext.Provider value={value}>{props.children}</ChartPaletteContext.Provider>;
}

export function useChartPalette(): Ctx {
  const v = useContext(ChartPaletteContext);
  if (!v) throw new Error('useChartPalette must be used within ChartPaletteProvider');
  return v;
}
