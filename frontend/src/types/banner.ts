export interface RewardExtraData {
  icon_url?: string;
  wish_url?: string;
  local_icon?: string;
  local_wish?: string;
  [key: string]: unknown;
}

export interface Reward {
  id?: number | null;
  banner_id?: number | null;
  name: string;
  rarity: number;
  is_featured: boolean;
  extra_data?: RewardExtraData;
}

export type BannerType =
  | 'LIMITED_CHARACTER'
  | 'LIMITED_WEAPON'
  | 'STANDARD_CHARACTER'
  | 'STANDARD_WEAPON'
  | 'CHRONICLED'
  | 'STANDARD_WEAPON_AND_CHARACTER'
  | string;

export interface Banner {
  id?: number | null;
  game_id?: number | null;
  version: string;
  phase: number;
  banner_type: BannerType;
  start_date: string;
  end_date: string | null;
  rewards: Reward[];
  limited_rewards: Reward[];
  low_rate_rewards: Reward[];
}

export type ServerRegion = 'ALL' | 'ASIA' | 'EUROPE' | 'AMERICA';

export interface GameOption {
  id: string;
  name: string;
  shortName: string;
  themeColor: string;
  badge: string;
  iconName: string;
}

export const GAME_PRESETS: Record<string, Partial<GameOption>> = {
  'Genshin Impact': {
    id: 'genshin-impact',
    shortName: 'Genshin',
    themeColor: '#06b6d4',
    badge: 'Teyvat',
    iconName: 'compass',
  },
  'Honkai: Star Rail': {
    id: 'honkai-star-rail',
    shortName: 'Star Rail',
    themeColor: '#818cf8',
    badge: 'Astral Express',
    iconName: 'swords',
  },
  'Zenless Zone Zero': {
    id: 'zenless-zone-zero',
    shortName: 'ZZZ',
    themeColor: '#f59e0b',
    badge: 'New Eridu',
    iconName: 'zap',
  },
  'Wuthering Waves': {
    id: 'wuthering-waves',
    shortName: 'WuWa',
    themeColor: '#10b981',
    badge: 'Solaris-3',
    iconName: 'wind',
  },
  'Fate/Grand Order': {
    id: 'fate-grand-order',
    shortName: 'FGO',
    themeColor: '#ec4899',
    badge: 'Chaldea',
    iconName: 'sparkles',
  },
  'Arknights': {
    id: 'arknights',
    shortName: 'Arknights',
    themeColor: '#3b82f6',
    badge: 'Rhodes Island',
    iconName: 'shield',
  },
};

const DYNAMIC_PALETTES = [
  '#06b6d4',
  '#818cf8',
  '#f59e0b',
  '#10b981',
  '#ec4899',
  '#3b82f6',
  '#a855f7',
  '#14b8a6',
  '#f43f5e',
];

export function resolveGameOption(name: string): GameOption {
  const match = GAME_PRESETS[name];
  const slug = name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
  if (match) {
    return {
      id: match.id ?? slug,
      name,
      shortName: match.shortName ?? name,
      themeColor: match.themeColor ?? '#06b6d4',
      badge: match.badge ?? 'Gacha',
      iconName: match.iconName ?? 'gamepad',
    };
  }

  // Consistent dynamic color generator based on name
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  const colorIndex = Math.abs(hash) % DYNAMIC_PALETTES.length;

  return {
    id: slug || 'game',
    name,
    shortName: name,
    themeColor: DYNAMIC_PALETTES[colorIndex],
    badge: 'Gacha',
    iconName: 'gamepad',
  };
}

