export type UiTokens = {
  bgCard: string;
  borderColor: string;
  textPrimary: string;
  textSecondary: string;
  accentBlue: string;
  accentGreen: string;
  accentRed: string;
};

export function readTokens(): UiTokens {
  const s = window.getComputedStyle(document.documentElement);
  const get = (name: string) => s.getPropertyValue(name).trim();
  return {
    bgCard: get('--bg-card'),
    borderColor: get('--border-color'),
    textPrimary: get('--text-primary'),
    textSecondary: get('--text-secondary'),
    accentBlue: get('--accent-blue'),
    accentGreen: get('--accent-green'),
    accentRed: get('--accent-red'),
  };
}

