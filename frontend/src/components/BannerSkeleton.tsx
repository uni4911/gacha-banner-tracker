import React from 'react';

export const BannerSkeleton: React.FC = () => {
  return (
    <div className="banner-skeleton-grid">
      {[1, 2].map((n) => (
        <div key={n} className="banner-card-skeleton">
          <div className="skeleton-graphic-area shimmer-effect" />
          <div className="skeleton-body">
            <div className="skeleton-line-sm shimmer-effect" />
            <div className="skeleton-featured-box shimmer-effect" />
            <div className="skeleton-chips-row">
              <div className="skeleton-chip shimmer-effect" />
              <div className="skeleton-chip shimmer-effect" />
              <div className="skeleton-chip shimmer-effect" />
            </div>
            <div className="skeleton-line-xs shimmer-effect" />
          </div>
        </div>
      ))}
    </div>
  );
};
