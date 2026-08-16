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

export type BannerCategory = 'CHARACTER' | 'WEAPON' | 'SPECIAL';
export type BannerStatusTab = 'active' | 'upcoming' | 'all';
export type BannerCategoryFilter = 'all' | 'character' | 'weapon';
export type BannerLayoutMode = 'categorized' | 'grid';

export function getBannerCategory(bannerType: BannerType | string): BannerCategory {
  const t = (bannerType || '').toUpperCase();
  if (t.includes('WEAPON') || t.includes('LIGHT_CONE')) {
    return 'WEAPON';
  }
  if (t.includes('CHARACTER')) {
    return 'CHARACTER';
  }
  return 'SPECIAL';
}

export function formatBannerType(type: string, gameName?: string): string {
  const g = (gameName || '').toLowerCase();
  const isStarRail = g.includes('star rail') || g.includes('hsr');
  const isWuWa = g.includes('wuthering') || g.includes('wuwa');
  const isGenshin = g.includes('genshin');

  switch (type) {
    case 'LIMITED_CHARACTER':
      if (isStarRail) return 'Character Event Warp';
      if (isWuWa) return 'Character Convene';
      if (isGenshin) return 'Character Event Wish';
      return 'Limited Character';
    case 'LIMITED_WEAPON':
      if (isStarRail) return 'Light Cone Event Warp';
      if (isWuWa) return 'Weapon Convene';
      if (isGenshin) return 'Weapon Event Wish (Epitome)';
      return 'Limited Weapon';
    case 'STANDARD_CHARACTER':
      return 'Standard Character';
    case 'STANDARD_WEAPON':
      return isStarRail ? 'Standard Light Cone' : 'Standard Weapon';
    case 'CHRONICLED':
      return 'Chronicled Wish';
    case 'STANDARD_WEAPON_AND_CHARACTER':
      return 'Standard Banner';
    default:
      return type.replace(/_/g, ' ');
  }
}

