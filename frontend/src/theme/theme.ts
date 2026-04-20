export type ThemeMode = 'light' | 'dark' | 'system';

const STORAGE_KEY = 'stock_mvp_theme_mode';

function getSystemTheme(): 'light' | 'dark' {
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

export function getStoredThemeMode(): ThemeMode {
  const v = window.localStorage.getItem(STORAGE_KEY);
  if (v === 'light' || v === 'dark' || v === 'system') return v;
  return 'system';
}

export function applyThemeMode(mode: ThemeMode): void {
  const actual = mode === 'system' ? getSystemTheme() : mode;
  document.documentElement.setAttribute('data-theme', actual);
  document.documentElement.style.colorScheme = actual;
}

export function setThemeMode(mode: ThemeMode): void {
  window.localStorage.setItem(STORAGE_KEY, mode);
  applyThemeMode(mode);
}

export function watchSystemTheme(onChange: (actual: 'light' | 'dark') => void): () => void {
  const mql = window.matchMedia?.('(prefers-color-scheme: dark)');
  if (!mql) return () => {};
  const handler = () => onChange(getSystemTheme());
  // Safari compatibility: addListener/removeListener fallback
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const anyMql: any = mql;
  if (typeof mql.addEventListener === 'function') {
    mql.addEventListener('change', handler);
    return () => mql.removeEventListener('change', handler);
  }
  anyMql.addListener(handler);
  return () => anyMql.removeListener(handler);
}

