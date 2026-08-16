import React from 'react';

interface BannerSkeletonProps {
  count?: number;
}

export const BannerSkeleton: React.FC<BannerSkeletonProps> = ({ count = 4 }) => {
  const items = Array.from({ length: count }, (_, i) => i + 1);

  return (
    <div className="banner-skeleton-grid">
      {items.map((n) => (
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
