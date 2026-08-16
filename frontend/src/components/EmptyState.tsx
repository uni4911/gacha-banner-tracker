import React from 'react';
import { CalendarX, RefreshCw, SearchX, Sparkles } from 'lucide-react';
import type { BannerStatusTab } from '../types/banner';

interface EmptyStateProps {
  gameName: string;
  statusTab: BannerStatusTab;
  searchQuery?: string;
  categoryFilter?: string;
  onClearFilters?: () => void;
  onRefresh: () => void;
  isLoading: boolean;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  gameName,
  statusTab,
  searchQuery,
  categoryFilter = 'all',
  onClearFilters,
  onRefresh,
  isLoading,
}) => {
  const isFiltered = Boolean(searchQuery || categoryFilter !== 'all');

  let title = 'No Banners Found';
  let description = `There are currently no banners recorded for ${gameName}.`;

  if (isFiltered) {
    title = 'No Matching Banners';
    description = searchQuery
      ? `No banners matching "${searchQuery}" in ${gameName}. Try clearing your search or filters.`
      : `No ${categoryFilter} banners found for ${gameName} with current filters.`;
  } else if (statusTab === 'active') {
    title = 'No Active Banners Found';
    description = `There are currently no active banners running for ${gameName} with the selected server filter. Check upcoming banners to see what's next!`;
  } else if (statusTab === 'upcoming') {
    title = 'No Upcoming Banners Scheduled';
    description = `No upcoming banners are scheduled yet for ${gameName}. Check back soon or refresh for updates.`;
  }

  return (
    <div className="empty-state-container animate-fade-in">
      <div className="empty-icon-wrapper">
        {isFiltered ? (
          <SearchX size={36} className="empty-icon" />
        ) : statusTab === 'upcoming' ? (
          <Sparkles size={36} className="empty-icon" />
        ) : (
          <CalendarX size={36} className="empty-icon" />
        )}
      </div>
      <h3 className="empty-title">{title}</h3>
      <p className="empty-desc">
        {description.includes(gameName) ? (
          <>
            {description.split(gameName)[0]}
            <strong className="game-highlight">{gameName}</strong>
            {description.split(gameName)[1]}
          </>
        ) : (
          description
        )}
      </p>
      <div className="empty-actions-row">
        {isFiltered && onClearFilters && (
          <button
            onClick={onClearFilters}
            className="empty-action-btn empty-clear-btn"
          >
            Clear Filters
          </button>
        )}
        <button
          onClick={onRefresh}
          className="empty-action-btn"
          disabled={isLoading}
        >
          <RefreshCw size={15} className={isLoading ? 'spinning' : ''} />
          <span>Refresh Data</span>
        </button>
      </div>
    </div>
  );
};
