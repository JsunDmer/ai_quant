/** 整页固定浅色（图表配色单独由 ChartPaletteContext 控制） */
export function applyUIPaletteLight(): void {
  document.documentElement.setAttribute('data-theme', 'light');
  document.documentElement.style.colorScheme = 'light';
}
