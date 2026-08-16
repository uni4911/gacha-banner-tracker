import { useState, useEffect, useCallback } from 'react';
import type { Banner, GameOption, ServerRegion } from './types/banner';
import { resolveGameOption } from './types/banner';
import { fetchActiveBanners, fetchGames, checkApiHealth } from './services/api';
import { Header } from './components/Header';
import { GameSelector } from './components/GameSelector';
import { BannerCard } from './components/BannerCard';
import { BannerSkeleton } from './components/BannerSkeleton';
import { EmptyState } from './components/EmptyState';
import { Sparkles, AlertTriangle, Layers, Terminal } from 'lucide-react';
import './App.css';

const DEFAULT_GAMES: GameOption[] = [
  resolveGameOption('Genshin Impact'),
  resolveGameOption('Honkai: Star Rail'),
];

export function App() {
  const [games, setGames] = useState<GameOption[]>(DEFAULT_GAMES);
  const [selectedGame, setSelectedGame] = useState<string>(DEFAULT_GAMES[0].name);
  const [selectedRegion, setSelectedRegion] = useState<ServerRegion>('ALL');
  const [banners, setBanners] = useState<Banner[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [apiOnline, setApiOnline] = useState<boolean>(true);

  // Load games from backend database
  const loadGames = useCallback(async () => {
    try {
      const apiGames = await fetchGames();
      if (apiGames && apiGames.length > 0) {
        const mapped = apiGames.map((g) => resolveGameOption(g.name));
        setGames(mapped);
        setSelectedGame((prev) => {
          if (mapped.some((g) => g.name === prev)) {
            return prev;
          }
          return mapped[0].name;
        });
      }
    } catch (err) {
      console.error('Error fetching games list:', err);
    }
  }, []);

  // Load banners function
  const loadBanners = useCallback(async (gameName: string, region: ServerRegion) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchActiveBanners(gameName, region);
      setBanners(data);
      setApiOnline(true);
    } catch (err: unknown) {
      console.error('Error fetching banners:', err);
      const isOnline = await checkApiHealth();
      setApiOnline(isOnline);
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to connect to the backend server. Please verify FastAPI is running.'
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Check initial API health & load games
  useEffect(() => {
    checkApiHealth().then((online) => setApiOnline(online));
    loadGames();
  }, [loadGames]);

  useEffect(() => {
    if (selectedGame) {
      loadBanners(selectedGame, selectedRegion);
    }
  }, [selectedGame, selectedRegion, loadBanners]);

  const handleGameSelect = (gameName: string) => {
    if (selectedGame !== gameName) {
      setSelectedGame(gameName);
    }
  };

  const handleRefresh = () => {
    loadGames();
    if (selectedGame) {
      loadBanners(selectedGame, selectedRegion);
    }
  };

  return (
    <div className="app-layout">
      {/* Top Header */}
      <Header
        apiOnline={apiOnline}
        selectedRegion={selectedRegion}
        onRegionChange={setSelectedRegion}
        onRefresh={handleRefresh}
        isLoading={isLoading}
      />

      <main className="main-content">
        {/* Game Selector Buttons */}
        <GameSelector
          games={games}
          selectedGame={selectedGame}
          onSelectGame={handleGameSelect}
          activeCount={banners.length}
          isLoading={isLoading}
        />

        {/* Banner Section Header */}
        <section className="active-banners-container" aria-label="Active Banners">
          <div className="banners-section-header">
            <div className="banners-title-group">
              <div className="section-icon-badge">
                <Layers size={18} />
              </div>
              <div>
                <h2 className="section-title">
                  Active Banners for <span className="game-highlight-text">{selectedGame}</span>
                </h2>
                <p className="section-subtitle">
                  Currently running limited & standard wish/warp events
                </p>
              </div>
            </div>

            <div className="banner-count-badge">
              <Sparkles size={14} className="count-sparkle" />
              <span>
                {isLoading
                  ? 'Loading...'
                  : `${banners.length} ${banners.length === 1 ? 'Banner' : 'Banners'} Active`}
              </span>
            </div>
          </div>

          {/* Error Message with Help Command */}
          {error && (
            <div className="error-banner animate-fade-in" role="alert">
              <div className="error-content">
                <AlertTriangle size={24} className="error-icon" />
                <div className="error-text-wrap">
                  <h4 className="error-title">Backend Connection Required</h4>
                  <p className="error-message">{error}</p>
                  {!apiOnline && (
                    <div className="error-hint-box">
                      <Terminal size={14} className="terminal-icon" />
                      <code>.\.venv\Scripts\uvicorn src.api.app:app --reload --port 8000</code>
                    </div>
                  )}
                </div>
              </div>
              <button onClick={handleRefresh} className="retry-btn">
                Retry Connection
              </button>
            </div>
          )}

          {/* Loading Skeleton */}
          {isLoading && <BannerSkeleton />}

          {/* Empty State */}
          {!isLoading && !error && banners.length === 0 && (
            <EmptyState
              gameName={selectedGame}
              onRefresh={handleRefresh}
              isLoading={isLoading}
            />
          )}

          {/* Active Banners Grid */}
          {!isLoading && !error && banners.length > 0 && (
            <div className="banners-grid">
              {banners.map((banner, index) => (
                <BannerCard
                  key={banner.id ?? `${banner.version}-${banner.phase}-${index}`}
                  banner={banner}
                  index={index}
                  selectedRegion={selectedRegion}
                />
              ))}
            </div>
          )}
        </section>
      </main>

      {/* Footer */}
      <footer className="app-footer">
        <p>Gacha Banner Tracker • Real-time database updates</p>
      </footer>
    </div>
  );
}

export default App;
