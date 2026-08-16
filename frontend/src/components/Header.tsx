import React from 'react';
import { Sparkles, RefreshCw, Globe, CheckCircle2, AlertCircle } from 'lucide-react';
import type { ServerRegion } from '../types/banner';

interface HeaderProps {
  apiOnline: boolean;
  selectedRegion: ServerRegion;
  onRegionChange: (region: ServerRegion) => void;
  onRefresh: () => void;
  isLoading: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  apiOnline,
  selectedRegion,
  onRegionChange,
  onRefresh,
  isLoading,
}) => {
  const regions: { value: ServerRegion; label: string }[] = [
    { value: 'ALL', label: 'All Regions' },
    { value: 'ASIA', label: 'Asia' },
    { value: 'EUROPE', label: 'Europe' },
    { value: 'AMERICA', label: 'America' },
  ];

  return (
    <header className="app-header">
      <div className="header-brand">
        <div className="logo-icon-wrapper">
          <Sparkles className="logo-sparkle" size={24} />
        </div>
        <div>
          <div className="title-row">
            <h1 className="app-title">Gacha Banner Tracker</h1>
            <span className={`status-pill ${apiOnline ? 'online' : 'offline'}`}>
              {apiOnline ? (
                <>
                  <CheckCircle2 size={12} />
                  <span>API Connected</span>
                </>
              ) : (
                <>
                  <AlertCircle size={12} />
                  <span>API Offline</span>
                </>
              )}
            </span>
          </div>
          <p className="app-subtitle">
            Real-time active banners, featured 5★ characters, and rate-up lineups
          </p>
        </div>
      </div>

      <div className="header-controls">
        <div className="region-selector">
          <Globe size={15} className="control-icon" />
          <select
            id="server-region-select"
            value={selectedRegion}
            onChange={(e) => onRegionChange(e.target.value as ServerRegion)}
            className="region-select-input"
            aria-label="Filter by server region"
          >
            {regions.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </select>
        </div>

        <button
          id="refresh-banners-btn"
          className="refresh-btn"
          onClick={onRefresh}
          disabled={isLoading}
          title="Refresh active banners"
          aria-label="Refresh banners"
        >
          <RefreshCw size={16} className={isLoading ? 'spinning' : ''} />
          <span>Refresh</span>
        </button>
      </div>
    </header>
  );
};
