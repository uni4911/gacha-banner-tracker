import React from 'react';
import type { GameOption } from '../types/banner';
import { GameIcon } from './GameIcons';

interface GameSelectorProps {
  games: GameOption[];
  selectedGame: string;
  onSelectGame: (gameName: string) => void;
  activeCount?: number;
  upcomingCount?: number;
  isLoading: boolean;
}

export const GameSelector: React.FC<GameSelectorProps> = ({
  games,
  selectedGame,
  onSelectGame,
  activeCount = 0,
  upcomingCount = 0,
  isLoading,
}) => {
  return (
    <section className="game-selector-section" aria-label="Game selection">
      <div className="section-label-row">
        <span className="section-eyebrow">SELECT GAME</span>
        <span className="section-hint">Select a game to view active and upcoming banner schedules</span>
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
                  <div className="game-icon-box" title={game.name}>
                    <GameIcon id={game.id} name={game.name} size={28} className="game-btn-icon" />
                  </div>
                  <div className="game-name-wrapper">
                    <span className="game-title">{game.name}</span>
                    <span className="game-badge-tag">{game.badge}</span>
                  </div>
                </div>

                <div className="game-btn-right">
                  {isSelected && (
                    <div className="game-status-counts-group">
                      <div className="active-indicator-badge" title="Active Banners">
                        <span className="pulse-dot" />
                        <span>
                          {isLoading ? '...' : `${activeCount} Active`}
                        </span>
                      </div>
                      {upcomingCount > 0 && (
                        <div className="upcoming-indicator-badge" title="Upcoming Banners">
                          <span>{upcomingCount} Upcoming</span>
                        </div>
                      )}
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
