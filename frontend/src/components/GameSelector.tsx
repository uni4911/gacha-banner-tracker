import React from 'react';
import type { GameOption } from '../types/banner';
import { Swords, Compass, Zap, Wind, Sparkles, Shield, Gamepad2, Flame } from 'lucide-react';

interface GameSelectorProps {
  games: GameOption[];
  selectedGame: string;
  onSelectGame: (gameName: string) => void;
  activeCount?: number;
  isLoading: boolean;
}

export const GameSelector: React.FC<GameSelectorProps> = ({
  games,
  selectedGame,
  onSelectGame,
  activeCount,
  isLoading,
}) => {
  const getGameIcon = (iconName: string, id: string) => {
    switch (iconName || id) {
      case 'compass':
      case 'genshin-impact':
        return <Compass size={18} className="game-btn-icon" />;
      case 'swords':
      case 'honkai-star-rail':
        return <Swords size={18} className="game-btn-icon" />;
      case 'zap':
      case 'zenless-zone-zero':
        return <Zap size={18} className="game-btn-icon" />;
      case 'wind':
      case 'wuthering-waves':
        return <Wind size={18} className="game-btn-icon" />;
      case 'shield':
      case 'arknights':
        return <Shield size={18} className="game-btn-icon" />;
      case 'sparkles':
      case 'fate-grand-order':
        return <Sparkles size={18} className="game-btn-icon" />;
      case 'flame':
        return <Flame size={18} className="game-btn-icon" />;
      default:
        return <Gamepad2 size={18} className="game-btn-icon" />;
    }
  };

  return (
    <section className="game-selector-section" aria-label="Game selection">
      <div className="section-label-row">
        <span className="section-eyebrow">SELECT GAME</span>
        <span className="section-hint">Click a game to view its active banners</span>
      </div>

      <div className="game-buttons-grid">
        {games.map((game) => {
          const isSelected = selectedGame === game.name;
          return (
            <button
              key={game.id}
              id={`game-btn-${game.id}`}
              onClick={() => onSelectGame(game.name)}
              className={`game-card-btn ${isSelected ? 'active' : ''}`}
              aria-pressed={isSelected}
              style={{
                '--game-accent': game.themeColor,
              } as React.CSSProperties}
            >
              <div className="game-btn-inner">
                <div className="game-btn-left">
                  <div className="game-icon-box">
                    {getGameIcon(game.iconName, game.id)}
                  </div>
                  <div className="game-name-wrapper">
                    <span className="game-title">{game.name}</span>
                    <span className="game-badge-tag">{game.badge}</span>
                  </div>
                </div>

                <div className="game-btn-right">
                  {isSelected && (
                    <div className="active-indicator-badge">
                      <span className="pulse-dot" />
                      <span>{isLoading ? 'Updating...' : `${activeCount ?? 0} Active`}</span>
                    </div>
                  )}
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
};
