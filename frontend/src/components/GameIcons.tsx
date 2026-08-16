import React, { useState } from 'react';

interface GameIconProps {
  id: string;
  name?: string;
  size?: number;
  className?: string;
}

const OFFICIAL_APP_ICONS: Record<string, string> = {
  'genshin-impact': '/game-icons/genshin-impact.jpg',
  'honkai-star-rail': '/game-icons/honkai-star-rail.jpg',
  'wuthering-waves': '/game-icons/wuthering-waves.jpg',
  'zenless-zone-zero': '/game-icons/zenless-zone-zero.jpg',
  'fate-grand-order': '/game-icons/fate-grand-order.jpg',
  'arknights': '/game-icons/arknights.jpg',
};

export const GameIcon: React.FC<GameIconProps> = ({ id, name = '', size = 36, className = '' }) => {
  const [imgError, setImgError] = useState<boolean>(false);
  const normalizedId = (id || name).toLowerCase().replace(/[^a-z0-9]/g, '-');

  // Match official app icon path
  const matchedKey = Object.keys(OFFICIAL_APP_ICONS).find(
    (key) => normalizedId.includes(key) || key.includes(normalizedId)
  );
  const appIconSrc = matchedKey ? OFFICIAL_APP_ICONS[matchedKey] : null;

  if (appIconSrc && !imgError) {
    return (
      <img
        src={appIconSrc}
        alt={name || id}
        width={size}
        height={size}
        className={`game-official-app-icon ${className}`}
        loading="lazy"
        onError={() => setImgError(true)}
      />
    );
  }

  // Fallback authentic vector SVG logos

  // Genshin Impact - Primogem & Ethereal Star Icon
  if (normalizedId.includes('genshin')) {
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 48 48"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={className}
        aria-label="Genshin Impact Logo"
      >
        <defs>
          <linearGradient id="genshinGrad" x1="0" y1="0" x2="48" y2="48" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#38bdf8" />
            <stop offset="50%" stopColor="#06b6d4" />
            <stop offset="100%" stopColor="#f59e0b" />
          </linearGradient>
          <linearGradient id="genshinInner" x1="24" y1="6" x2="24" y2="42" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#ffffff" />
            <stop offset="60%" stopColor="#bae6fd" />
            <stop offset="100%" stopColor="#0284c7" />
          </linearGradient>
        </defs>
        <path
          d="M24 4 L29 17 L42 24 L29 31 L24 44 L19 31 L6 24 L19 17 Z"
          fill="url(#genshinGrad)"
        />
        <polygon points="24,10 27,20 37,24 27,28 24,38 21,28 11,24 21,20" fill="url(#genshinInner)" />
        <polygon points="24,14 26,22 34,24 26,26 24,34 22,26 14,24 22,22" fill="#ffffff" />
        <circle cx="24" cy="24" r="2.5" fill="#fef08a" />
      </svg>
    );
  }

  // Honkai: Star Rail - Astral Express Stellar Warp Star
  if (normalizedId.includes('star-rail') || normalizedId.includes('hsr') || normalizedId.includes('honkai')) {
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 48 48"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={className}
        aria-label="Honkai: Star Rail Logo"
      >
        <defs>
          <linearGradient id="hsrGrad" x1="6" y1="6" x2="42" y2="42" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#c084fc" />
            <stop offset="50%" stopColor="#818cf8" />
            <stop offset="100%" stopColor="#f59e0b" />
          </linearGradient>
          <linearGradient id="hsrGold" x1="12" y1="12" x2="36" y2="36" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#fef08a" />
            <stop offset="100%" stopColor="#d97706" />
          </linearGradient>
        </defs>
        <ellipse cx="24" cy="24" rx="20" ry="8" transform="rotate(-30 24 24)" stroke="url(#hsrGrad)" strokeWidth="2.2" strokeDasharray="3 1" fill="none" opacity="0.8" />
        <path
          d="M24 3 C25 15, 33 23, 45 24 C33 25, 25 33, 24 45 C23 33, 15 25, 3 24 C15 23, 23 15, 24 3 Z"
          fill="url(#hsrGrad)"
        />
        <path
          d="M24 10 C25 18, 30 23, 38 24 C30 25, 25 30, 24 38 C23 30, 18 25, 10 24 C18 23, 23 18, 24 10 Z"
          fill="url(#hsrGold)"
        />
        <circle cx="24" cy="24" r="3" fill="#ffffff" />
      </svg>
    );
  }

  // Wuthering Waves - Solaris Resonance & Tacet Wave Mark
  if (normalizedId.includes('wuthering') || normalizedId.includes('wuwa')) {
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 48 48"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={className}
        aria-label="Wuthering Waves Logo"
      >
        <defs>
          <linearGradient id="wuwaGrad" x1="4" y1="4" x2="44" y2="44" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#34d399" />
            <stop offset="50%" stopColor="#10b981" />
            <stop offset="100%" stopColor="#06b6d4" />
          </linearGradient>
          <linearGradient id="wuwaCore" x1="14" y1="14" x2="34" y2="34" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#a7f3d0" />
            <stop offset="100%" stopColor="#059669" />
          </linearGradient>
        </defs>
        <circle cx="24" cy="24" r="19" stroke="url(#wuwaGrad)" strokeWidth="2.5" fill="none" opacity="0.6" strokeDasharray="16 4 8 4" />
        <path
          d="M14 24 C14 16, 20 11, 24 7 C28 11, 34 16, 34 24 C34 32, 28 37, 24 41 C20 37, 14 32, 14 24 Z"
          fill="url(#wuwaGrad)"
        />
        <path
          d="M18 24 C18 20, 21 16, 24 13 C27 16, 30 20, 30 24 C30 28, 27 32, 24 35 C21 32, 18 28, 18 24 Z"
          fill="url(#wuwaCore)"
        />
        <circle cx="24" cy="24" r="2.8" fill="#ffffff" />
      </svg>
    );
  }

  // Zenless Zone Zero - Bangboo / Stylized ZZZ Glitch Emblem
  if (normalizedId.includes('zenless') || normalizedId.includes('zzz')) {
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 48 48"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={className}
        aria-label="Zenless Zone Zero Logo"
      >
        <defs>
          <linearGradient id="zzzGrad" x1="0" y1="0" x2="48" y2="48" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#fbbf24" />
            <stop offset="100%" stopColor="#f59e0b" />
          </linearGradient>
        </defs>
        <rect x="6" y="6" width="36" height="36" rx="10" fill="#18181b" stroke="url(#zzzGrad)" strokeWidth="2.5" />
        <path
          d="M14 15 H34 L22 25 H34 M14 25 H26 L14 34 H34"
          stroke="url(#zzzGrad)"
          strokeWidth="3.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <circle cx="34" cy="15" r="2" fill="#ffffff" />
        <circle cx="14" cy="34" r="2" fill="#ffffff" />
      </svg>
    );
  }

  // Fate/Grand Order - Chaldea Command Seal
  if (normalizedId.includes('fate') || normalizedId.includes('fgo') || normalizedId.includes('grand-order')) {
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 48 48"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={className}
        aria-label="Fate/Grand Order Logo"
      >
        <defs>
          <linearGradient id="fgoGrad" x1="0" y1="0" x2="48" y2="48" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#f43f5e" />
            <stop offset="100%" stopColor="#be123c" />
          </linearGradient>
        </defs>
        <path
          d="M24 6 C27 14, 33 19, 36 21 C29 23, 25 18, 24 6 Z"
          fill="url(#fgoGrad)"
        />
        <path
          d="M24 6 C21 14, 15 19, 12 21 C19 23, 23 18, 24 6 Z"
          fill="url(#fgoGrad)"
        />
        <path
          d="M12 25 C20 25, 23 33, 24 42 C21 34, 15 32, 12 25 Z"
          fill="url(#fgoGrad)"
        />
        <path
          d="M36 25 C28 25, 25 33, 24 42 C27 34, 33 32, 36 25 Z"
          fill="url(#fgoGrad)"
        />
        <circle cx="24" cy="24" r="3.5" fill="#fbbf24" stroke="#ffffff" strokeWidth="1" />
      </svg>
    );
  }

  // Arknights - Rhodes Island Chemical Polygon / Rook Crest
  if (normalizedId.includes('arknights')) {
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 48 48"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={className}
        aria-label="Arknights Logo"
      >
        <defs>
          <linearGradient id="arkGrad" x1="0" y1="0" x2="48" y2="48" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#38bdf8" />
            <stop offset="100%" stopColor="#1d4ed8" />
          </linearGradient>
        </defs>
        <polygon points="24,6 40,15 40,33 24,42 8,33 8,15" stroke="url(#arkGrad)" strokeWidth="2.5" fill="#0f172a" />
        <path
          d="M24 14 L32 20 L32 28 L24 34 L16 28 L16 20 Z"
          fill="url(#arkGrad)"
        />
        <polygon points="24,19 28,24 24,29 20,24" fill="#ffffff" />
      </svg>
    );
  }

  // Default Fallback Gamepad / Gacha Crest
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <defs>
        <linearGradient id="defaultGameGrad" x1="0" y1="0" x2="48" y2="48" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#06b6d4" />
          <stop offset="100%" stopColor="#818cf8" />
        </linearGradient>
      </defs>
      <rect x="8" y="8" width="32" height="32" rx="8" stroke="url(#defaultGameGrad)" strokeWidth="2" fill="#182030" />
      <polygon points="24,14 27,21 34,24 27,27 24,34 21,27 14,24 21,21" fill="url(#defaultGameGrad)" />
      <circle cx="24" cy="24" r="2.5" fill="#ffffff" />
    </svg>
  );
};
