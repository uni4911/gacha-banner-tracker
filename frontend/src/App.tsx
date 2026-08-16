import { useState, useEffect, useCallback, useMemo } from 'react';
import type {
  Banner,
  GameOption,
  ServerRegion,
  BannerStatusTab,
  BannerCategoryFilter,
  BannerLayoutMode,
} from './types/banner';
import { resolveGameOption, getBannerCategory } from './types/banner';
import {
  fetchActiveBanners,
  fetchUpcomingBanners,
  fetchGames,
  checkApiHealth,
} from './services/api';
import { Header } from './components/Header';
import { GameSelector } from './components/GameSelector';
import { BannerCard } from './components/BannerCard';
import { BannerSkeleton } from './components/BannerSkeleton';
import { EmptyState } from './components/EmptyState';
import {
  Sparkles,
  AlertTriangle,
  Layers,
  Terminal,
  Clock,
  Zap,
  Sword,
  Shield,
  Search,
  X,
  LayoutGrid,
  Columns,
  Sparkle,
} from 'lucide-react';
import './App.css';

const DEFAULT_GAMES: GameOption[] = [
  resolveGameOption('Honkai: Star Rail'),
  resolveGameOption('Genshin Impact'),
  resolveGameOption('Wuthering Waves'),
];

export function App() {
  const [games, setGames] = useState<GameOption[]>(DEFAULT_GAMES);
  const [selectedGame, setSelectedGame] = useState<string>(DEFAULT_GAMES[0].name);
  const [selectedRegion, setSelectedRegion] = useState<ServerRegion>('ALL');

  // Banner data state
  const [activeBanners, setActiveBanners] = useState<Banner[]>([]);
  const [upcomingBanners, setUpcomingBanners] = useState<Banner[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [apiOnline, setApiOnline] = useState<boolean>(true);

  // Filter & Layout state
  const [statusTab, setStatusTab] = useState<BannerStatusTab>('active');
  const [categoryFilter, setCategoryFilter] = useState<BannerCategoryFilter>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [layoutMode, setLayoutMode] = useState<BannerLayoutMode>('categorized');

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

  // Load banners (both active and upcoming)
  const loadBanners = useCallback(async (gameName: string, region: ServerRegion) => {
    setIsLoading(true);
    setError(null);
    try {
      const [activeData, upcomingData] = await Promise.all([
        fetchActiveBanners(gameName, region),
        fetchUpcomingBanners(gameName, region),
      ]);
      setActiveBanners(activeData);
      setUpcomingBanners(upcomingData);
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
      setSearchQuery('');
    }
  };

  const handleRefresh = () => {
    loadGames();
    if (selectedGame) {
      loadBanners(selectedGame, selectedRegion);
    }
  };

  // Base banner pool based on active/upcoming status tab
  const displayedBaseBanners = useMemo(() => {
    if (statusTab === 'active') return activeBanners;
    if (statusTab === 'upcoming') return upcomingBanners;
    return [...activeBanners, ...upcomingBanners];
  }, [statusTab, activeBanners, upcomingBanners]);

  // Filter banners by Category and Search Query
  const filteredBanners = useMemo(() => {
    return displayedBaseBanners.filter((banner) => {
      // 1. Category Filter
      if (categoryFilter !== 'all') {
        const cat = getBannerCategory(banner.banner_type);
        if (categoryFilter === 'character' && cat !== 'CHARACTER') return false;
        if (categoryFilter === 'weapon' && cat !== 'WEAPON') return false;
      }

      // 2. Search Query
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase().trim();
        const allRewardNames = [
          ...(banner.limited_rewards || []),
          ...(banner.low_rate_rewards || []),
          ...(banner.rewards || []),
        ].map((r) => r.name.toLowerCase());

        const matchesReward = allRewardNames.some((n) => n.includes(query));
        const matchesVersion = (banner.version || '').toLowerCase().includes(query);
        const matchesType = (banner.banner_type || '').toLowerCase().includes(query);

        return matchesReward || matchesVersion || matchesType;
      }

      return true;
    });
  }, [displayedBaseBanners, categoryFilter, searchQuery]);

  // Group filtered banners into Character vs Weapon vs Special
  const { characterBanners, weaponBanners, specialBanners } = useMemo(() => {
    const chars: Banner[] = [];
    const weaps: Banner[] = [];
    const specs: Banner[] = [];

    filteredBanners.forEach((banner) => {
      const cat = getBannerCategory(banner.banner_type);
      if (cat === 'CHARACTER') {
        chars.push(banner);
      } else if (cat === 'WEAPON') {
        weaps.push(banner);
      } else {
        specs.push(banner);
      }
    });

    return { characterBanners: chars, weaponBanners: weaps, specialBanners: specs };
  }, [filteredBanners]);

  // Sorted list for Grid mode: sorted so character and matching weapon banners appear paired/together
  const sortedGridBanners = useMemo(() => {
    return [...filteredBanners].sort((a, b) => {
      // 1. Sort by version desc
      if (a.version !== b.version) {
        return b.version.localeCompare(a.version, undefined, { numeric: true });
      }
      // 2. Sort by phase asc
      if (a.phase !== b.phase) {
        return a.phase - b.phase;
      }
      // 3. Put character banners before weapon banners
      const catA = getBannerCategory(a.banner_type);
      const catB = getBannerCategory(b.banner_type);
      if (catA !== catB) {
        if (catA === 'CHARACTER') return -1;
        if (catB === 'CHARACTER') return 1;
      }
      return 0;
    });
  }, [filteredBanners]);

  // Count statistics for the current game
  const counts = useMemo(() => {
    const activeChars = activeBanners.filter((b) => getBannerCategory(b.banner_type) === 'CHARACTER').length;
    const activeWeaps = activeBanners.filter((b) => getBannerCategory(b.banner_type) === 'WEAPON').length;
    const upcomingChars = upcomingBanners.filter((b) => getBannerCategory(b.banner_type) === 'CHARACTER').length;
    const upcomingWeaps = upcomingBanners.filter((b) => getBannerCategory(b.banner_type) === 'WEAPON').length;

    return {
      active: activeBanners.length,
      upcoming: upcomingBanners.length,
      all: activeBanners.length + upcomingBanners.length,
      activeChars,
      activeWeaps,
      upcomingChars,
      upcomingWeaps,
      currentChars: characterBanners.length,
      currentWeaps: weaponBanners.length,
    };
  }, [activeBanners, upcomingBanners, characterBanners, weaponBanners]);

  const hasCategorizedData = characterBanners.length > 0 && weaponBanners.length > 0;

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
        {/* Game Selector Section */}
        <GameSelector
          games={games}
          selectedGame={selectedGame}
          onSelectGame={handleGameSelect}
          activeCount={counts.active}
          upcomingCount={counts.upcoming}
          isLoading={isLoading}
        />

        {/* Banner Navigation Tabs & Controls Section */}
        <section className="banners-control-center" aria-label="Banner Controls">
          {/* Main Status Tabs (Active / Upcoming / All) */}
          <div className="status-tabs-container">
            <button
              id="tab-active-banners"
              onClick={() => setStatusTab('active')}
              className={`status-tab-btn ${statusTab === 'active' ? 'active' : ''}`}
            >
              <Zap size={16} className="tab-icon zap-icon" />
              <span>Active Banners</span>
              <span className="tab-counter-pill">{counts.active}</span>
            </button>

            <button
              id="tab-upcoming-banners"
              onClick={() => setStatusTab('upcoming')}
              className={`status-tab-btn ${statusTab === 'upcoming' ? 'active' : ''}`}
            >
              <Clock size={16} className="tab-icon clock-icon" />
              <span>Upcoming Banners</span>
              <span className="tab-counter-pill upcoming-pill">{counts.upcoming}</span>
            </button>

            <button
              id="tab-all-banners"
              onClick={() => setStatusTab('all')}
              className={`status-tab-btn ${statusTab === 'all' ? 'active' : ''}`}
            >
              <Layers size={16} className="tab-icon" />
              <span>All Banners</span>
              <span className="tab-counter-pill">{counts.all}</span>
            </button>
          </div>

          {/* Secondary Controls Bar: Type Filters, Search, and Layout Toggle */}
          <div className="banner-toolbar">
            {/* Category Filter Pills (All / Characters / Weapons) */}
            <div className="category-filter-group" role="group" aria-label="Filter by banner category">
              <button
                onClick={() => setCategoryFilter('all')}
                className={`filter-pill-btn ${categoryFilter === 'all' ? 'active' : ''}`}
              >
                <Sparkle size={13} />
                <span>All Types</span>
                <span className="pill-mini-count">{displayedBaseBanners.length}</span>
              </button>

              <button
                onClick={() => setCategoryFilter('character')}
                className={`filter-pill-btn character-pill ${categoryFilter === 'character' ? 'active' : ''}`}
              >
                <Sword size={13} />
                <span>Characters</span>
                <span className="pill-mini-count">
                  {statusTab === 'active'
                    ? counts.activeChars
                    : statusTab === 'upcoming'
                    ? counts.upcomingChars
                    : counts.activeChars + counts.upcomingChars}
                </span>
              </button>

              <button
                onClick={() => setCategoryFilter('weapon')}
                className={`filter-pill-btn weapon-pill ${categoryFilter === 'weapon' ? 'active' : ''}`}
              >
                <Shield size={13} />
                <span>Weapons & Light Cones</span>
                <span className="pill-mini-count">
                  {statusTab === 'active'
                    ? counts.activeWeaps
                    : statusTab === 'upcoming'
                    ? counts.upcomingWeaps
                    : counts.activeWeaps + counts.upcomingWeaps}
                </span>
              </button>
            </div>

            {/* Search and Layout Actions */}
            <div className="toolbar-actions-right">
              {/* Instant Search Bar */}
              <div className="search-input-wrapper">
                <Search size={15} className="search-icon" />
                <input
                  type="text"
                  placeholder="Search character, weapon, version..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="search-text-input"
                  aria-label="Search banners"
                />
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery('')}
                    className="search-clear-btn"
                    title="Clear search"
                  >
                    <X size={14} />
                  </button>
                )}
              </div>

              {/* View Layout Toggle */}
              <div className="layout-toggle-group" title="Switch layout view">
                <button
                  onClick={() => setLayoutMode('categorized')}
                  className={`layout-btn ${layoutMode === 'categorized' ? 'active' : ''}`}
                  title="Grouped by Category (Characters together, Weapons together)"
                  aria-label="Categorized view"
                >
                  <Columns size={15} />
                  <span className="layout-btn-label">Sections</span>
                </button>
                <button
                  onClick={() => setLayoutMode('grid')}
                  className={`layout-btn ${layoutMode === 'grid' ? 'active' : ''}`}
                  title="Unified Timeline Grid"
                  aria-label="Unified Grid view"
                >
                  <LayoutGrid size={15} />
                  <span className="layout-btn-label">Grid</span>
                </button>
              </div>
            </div>
          </div>
        </section>

        {/* Section Heading & Context Badge */}
        <section className="active-banners-container" aria-label="Banners Display">
          <div className="banners-section-header">
            <div className="banners-title-group">
              <div className={`section-icon-badge ${statusTab === 'upcoming' ? 'upcoming-badge-glow' : ''}`}>
                {statusTab === 'upcoming' ? <Clock size={18} /> : <Layers size={18} />}
              </div>
              <div>
                <h2 className="section-title">
                  {statusTab === 'active' && 'Active Banners'}
                  {statusTab === 'upcoming' && 'Upcoming Banners'}
                  {statusTab === 'all' && 'All Banners & Schedule'}{' '}
                  for <span className="game-highlight-text">{selectedGame}</span>
                </h2>
                <p className="section-subtitle">
                  {statusTab === 'active' && 'Currently running limited & standard wish/warp events'}
                  {statusTab === 'upcoming' && 'Confirmed future banner phases, rate-ups, and release schedules'}
                  {statusTab === 'all' && 'Complete active and upcoming gacha banner timeline'}
                </p>
              </div>
            </div>

            <div className="banner-count-badge">
              <Sparkles size={14} className="count-sparkle" />
              <span>
                {isLoading
                  ? 'Loading...'
                  : `${filteredBanners.length} ${
                      filteredBanners.length === 1 ? 'Banner' : 'Banners'
                    } Shown`}
              </span>
            </div>
          </div>

          {/* Backend Error Alert Banner */}
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
          {isLoading && <BannerSkeleton count={4} />}

          {/* Empty State */}
          {!isLoading && !error && filteredBanners.length === 0 && (
            <EmptyState
              gameName={selectedGame}
              statusTab={statusTab}
              searchQuery={searchQuery}
              categoryFilter={categoryFilter}
              onClearFilters={() => {
                setCategoryFilter('all');
                setSearchQuery('');
              }}
              onRefresh={handleRefresh}
              isLoading={isLoading}
            />
          )}

          {/* Categorized Sections View (All Character Banners next to each other, all Weapon Banners next to each other) */}
          {!isLoading && !error && filteredBanners.length > 0 && layoutMode === 'categorized' && (
            <div className="categorized-layout-container">
              {/* Character Banners Column / Section */}
              {characterBanners.length > 0 && (
                <div
                  className={`category-section character-category-section ${
                    !hasCategorizedData ? 'full-width-category' : ''
                  }`}
                >
                  <div className="category-section-header character-header">
                    <div className="category-title-wrap">
                      <div className="category-icon-box character-icon-box">
                        <Sword size={16} />
                      </div>
                      <div>
                        <h3 className="category-heading">Character Banners</h3>
                        <span className="category-subhead">
                          Featured 5★ characters & rate-up heroes
                        </span>
                      </div>
                    </div>
                    <span className="category-badge character-badge">
                      {characterBanners.length} {characterBanners.length === 1 ? 'Banner' : 'Banners'}
                    </span>
                  </div>

                  <div className="category-cards-grid">
                    {characterBanners.map((banner, index) => (
                      <BannerCard
                        key={banner.id ?? `char-${banner.version}-${banner.phase}-${index}`}
                        banner={banner}
                        index={index}
                        gameName={selectedGame}
                        selectedRegion={selectedRegion}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* Weapon & Light Cone Banners Column / Section */}
              {weaponBanners.length > 0 && (
                <div
                  className={`category-section weapon-category-section ${
                    !hasCategorizedData ? 'full-width-category' : ''
                  }`}
                >
                  <div className="category-section-header weapon-header">
                    <div className="category-title-wrap">
                      <div className="category-icon-box weapon-icon-box">
                        <Shield size={16} />
                      </div>
                      <div>
                        <h3 className="category-heading">Weapon & Light Cone Banners</h3>
                        <span className="category-subhead">
                          Featured 5★ signature weapons & equipment
                        </span>
                      </div>
                    </div>
                    <span className="category-badge weapon-badge">
                      {weaponBanners.length} {weaponBanners.length === 1 ? 'Banner' : 'Banners'}
                    </span>
                  </div>

                  <div className="category-cards-grid">
                    {weaponBanners.map((banner, index) => (
                      <BannerCard
                        key={banner.id ?? `weap-${banner.version}-${banner.phase}-${index}`}
                        banner={banner}
                        index={index}
                        gameName={selectedGame}
                        selectedRegion={selectedRegion}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* Special / Other Banners Section (e.g. Chronicled or Standard) */}
              {specialBanners.length > 0 && (
                <div className="category-section special-category-section full-width-category">
                  <div className="category-section-header special-header">
                    <div className="category-title-wrap">
                      <div className="category-icon-box special-icon-box">
                        <Sparkles size={16} />
                      </div>
                      <div>
                        <h3 className="category-heading">Special & Standard Banners</h3>
                        <span className="category-subhead">Chronicled wish and permanent lineups</span>
                      </div>
                    </div>
                    <span className="category-badge special-badge">
                      {specialBanners.length} {specialBanners.length === 1 ? 'Banner' : 'Banners'}
                    </span>
                  </div>

                  <div className="category-cards-grid">
                    {specialBanners.map((banner, index) => (
                      <BannerCard
                        key={banner.id ?? `spec-${banner.version}-${banner.phase}-${index}`}
                        banner={banner}
                        index={index}
                        gameName={selectedGame}
                        selectedRegion={selectedRegion}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Unified Grid View (Banners paired and sorted) */}
          {!isLoading && !error && filteredBanners.length > 0 && layoutMode === 'grid' && (
            <div className="banners-grid">
              {sortedGridBanners.map((banner, index) => (
                <BannerCard
                  key={banner.id ?? `${banner.version}-${banner.phase}-${banner.banner_type}-${index}`}
                  banner={banner}
                  index={index}
                  gameName={selectedGame}
                  selectedRegion={selectedRegion}
                />
              ))}
            </div>
          )}
        </section>
      </main>

      {/* Footer */}
      <footer className="app-footer">
        <p>Gacha Banner Tracker • Real-time database & banner schedules</p>
      </footer>
    </div>
  );
}

export default App;
