import type { UiTokens } from './tokens';

/** 与 tokens.css 中浅色 / 深色块一致，仅用于 ECharts，不随整页主题切换 */
const CHART_LIGHT: UiTokens = {
  bgCard: 'transparent',
  borderColor: '#e2e8f0',
  textPrimary: '#0f172a',
  textSecondary: '#475569',
  textMuted: '#94a3b8',
  accentBlue: '#2563eb',
  accentGreen: '#10b981',
  accentRed: '#ef4444',
};

const CHART_DARK: UiTokens = {
  bgCard: 'transparent',
  borderColor: 'rgba(30, 41, 59, 0.7)',
  textPrimary: '#f8fafc',
  textSecondary: '#94a3b8',
  textMuted: '#64748b',
  accentBlue: '#3b82f6',
  accentGreen: '#10b981',
  accentRed: '#ef4444',
};

export type ChartPalette = 'light' | 'dark';

export function getChartTokens(palette: ChartPalette): UiTokens {
  return palette === 'dark' ? CHART_DARK : CHART_LIGHT;
}
