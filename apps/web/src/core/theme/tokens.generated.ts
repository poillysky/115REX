// 由 tools/generate_tokens.py 从 packages/design-tokens/tokens.json 生成，不要手改。

export const colorLight = {
  background: '#F3F4F6',
  surface: '#FFFFFF',
  surfaceSecondary: '#F6F7F9',
  primary: '#176BFF',
  primarySubtle: '#E0F2FE',
  brandViolet: '#8B5CF6',
  onPrimary: '#FFFFFF',
  textPrimary: '#171A22',
  textSecondary: '#6B7280',
  textTertiary: '#6E757F',
  separator: '#E5E8EE',
  success: '#16845B',
  warning: '#B96B08',
  danger: '#D83B45',
} as const;

export const colorDark: Record<keyof typeof colorLight, string> = {
  background: '#000000',
  surface: '#1C1C1E',
  surfaceSecondary: '#2C2C2E',
  primary: '#3D8BFF',
  primarySubtle: '#0E1B2E',
  brandViolet: '#A57BFF',
  onPrimary: '#FFFFFF',
  textPrimary: '#F5F5F7',
  textSecondary: '#98989D',
  textTertiary: '#8E8E93',
  separator: '#38383A',
  success: '#2FBF85',
  warning: '#E8A030',
  danger: '#FF5F63',
};

export type ColorRole = keyof typeof colorLight;

/** 主题变体：只覆盖品牌三色，其余角色沿用深浅基准。 */
export const themeAccents = {
  default: {
    label: '经典蓝',
    light: {"primary": "#176BFF", "primarySubtle": "#E0F2FE", "onPrimary": "#FFFFFF"},
    dark: {"primary": "#3D8BFF", "primarySubtle": "#0E1B2E", "onPrimary": "#FFFFFF"},
  },
  graphite: {
    label: '石墨',
    light: {"primary": "#3A3F4A", "primarySubtle": "#EDEFF2", "onPrimary": "#FFFFFF"},
    dark: {"primary": "#C9CDD4", "primarySubtle": "#2A2D33", "onPrimary": "#171A22"},
  },
  teal: {
    label: '青碧',
    light: {"primary": "#0E7A6E", "primarySubtle": "#DDF3EF", "onPrimary": "#FFFFFF"},
    dark: {"primary": "#3FC9B4", "primarySubtle": "#0C2420", "onPrimary": "#08120F"},
  },
  violet: {
    label: '罗兰',
    light: {"primary": "#6A46D6", "primarySubtle": "#EDE7FC", "onPrimary": "#FFFFFF"},
    dark: {"primary": "#A78BFA", "primarySubtle": "#1D1633", "onPrimary": "#11101C"},
  },
  amber: {
    label: '琥珀',
    light: {"primary": "#A05A05", "primarySubtle": "#FBECDA", "onPrimary": "#FFFFFF"},
    dark: {"primary": "#F0B457", "primarySubtle": "#2A1D08", "onPrimary": "#191207"},
  },
  rose: {
    label: '绯红',
    light: {"primary": "#B62D5A", "primarySubtle": "#FBE4EC", "onPrimary": "#FFFFFF"},
    dark: {"primary": "#F27198", "primarySubtle": "#2B0F1A", "onPrimary": "#1A0A10"},
  },
} as const;

export type ThemeAccent = keyof typeof themeAccents;

export type ThemeMode = 'light' | 'dark';

export const space = {
  space1: 4,
  space2: 8,
  space3: 12,
  space4: 16,
  space5: 20,
  space6: 24,
  space8: 32,
  space10: 40,
} as const;

export const radius = {
  radiusSm: 8,
  radiusMd: 12,
  radiusLg: 16,
  radiusXl: 22,
  radius2xl: 28,
  radiusFull: 999,
} as const;

export const duration = {
  micro: 120,
  page: 300,
} as const;

export const fontSize = {
  display: 32,
  heading1: 30,
  heading2: 22,
  heading3: 18,
  body: 16,
  label: 15,
  caption: 13,
} as const;

export const fontWeight = {
  display: 600,
  heading1: 700,
  heading2: 600,
  heading3: 500,
  body: 400,
  label: 500,
  caption: 400,
} as const;

export const letterSpacing = {
  display: -0.7,
  heading1: -0.6,
  heading2: -0.45,
  heading3: -0.35,
  body: 0,
  label: 0,
  caption: 0,
} as const;

export const tokens = { colorLight, colorDark, themeAccents, space, radius, duration, fontSize, fontWeight, letterSpacing } as const;
