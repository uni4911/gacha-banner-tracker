import React from 'react';
import { CalendarX, RefreshCw } from 'lucide-react';

interface EmptyStateProps {
  gameName: string;
  onRefresh: () => void;
  isLoading: boolean;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  gameName,
  onRefresh,
  isLoading,
}) => {
  return (
    <div className="empty-state-container animate-fade-in">
      <div className="empty-icon-wrapper">
        <CalendarX size={36} className="empty-icon" />
      </div>
      <h3 className="empty-title">No Active Banners Found</h3>
      <p className="empty-desc">
        There are currently no active banners recorded for <strong className="game-highlight">{gameName}</strong> with the selected server/date filter.
      </p>
      <button
        onClick={onRefresh}
        className="empty-action-btn"
        disabled={isLoading}
      >
        <RefreshCw size={15} className={isLoading ? 'spinning' : ''} />
        <span>Check Again</span>
      </button>
    </div>
  );
};
