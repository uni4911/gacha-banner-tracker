import React, { useState, useEffect } from 'react';
import type { Banner, Reward, ServerRegion } from '../types/banner';
import { Sparkles, Calendar, Clock, Image as ImageIcon, User, Shield, AlertCircle } from 'lucide-react';

interface BannerCardProps {
  banner: Banner;
  index: number;
  selectedRegion?: ServerRegion;
}

const REGION_TIMEZONES: Record<ServerRegion, string | undefined> = {
  ALL: undefined,
  ASIA: 'Asia/Shanghai',
  EUROPE: 'Europe/Paris',
  AMERICA: 'America/New_York',
};

// Parse exact timestamp from ISO string, with standard fallback if time was saved as midnight
function getBannerTimestamp(
  isoString: string | null | undefined,
  _region: ServerRegion,
  phase: number,
  isEnd: boolean
): number {
  if (!isoString) return 0;
  const d = new Date(isoString);
  const rawH = d.getUTCHours();
  const rawMin = d.getUTCMinutes();
  const rawS = d.getUTCSeconds();

  // If backend provided an exact time (not 00:00:00 midnight), return exact timestamp
  if (rawH !== 0 || rawMin !== 0 || rawS !== 0) {
    return d.getTime();
  }

  // Fallback for dates saved as midnight (date-only)
  const y = d.getUTCFullYear();
  const m = d.getUTCMonth();
  const day = d.getUTCDate();

  if (isEnd) {
    // Phase 1 ends at 17:59:59, Phase 2 ends at 14:59:59
    const endH = phase === 2 ? 14 : 17;
    return Date.UTC(y, m, day, endH, 59, 59);
  } else {
    // Phase 1 starts at 06:00:00, Phase 2 starts at 18:00:00
    const startH = phase === 2 ? 18 : 6;
    return Date.UTC(y, m, day, startH, 0, 0);
  }
}

export const BannerCard: React.FC<BannerCardProps> = ({
  banner,
  index,
  selectedRegion = 'ALL',
}) => {
  // Update timestamp periodically
  const [now, setNow] = useState<number>(Date.now());

  useEffect(() => {
    setNow(Date.now());
    const interval = setInterval(() => {
      setNow(Date.now());
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  // Format Banner Type
  const formatBannerType = (type: string) => {
    switch (type) {
      case 'LIMITED_CHARACTER':
        return 'Limited Character';
      case 'LIMITED_WEAPON':
        return 'Limited Weapon';
      case 'STANDARD_CHARACTER':
        return 'Standard Character';
      case 'STANDARD_WEAPON':
        return 'Standard Weapon';
      case 'CHRONICLED':
        return 'Chronicled Wish';
      case 'STANDARD_WEAPON_AND_CHARACTER':
        return 'Standard Banner';
      default:
        return type.replace(/_/g, ' ');
    }
  };

  // Format Dates
  const formatDate = (isoString?: string | null, isEnd = false) => {
    if (!isoString) return 'Permanent';
    const timestamp = getBannerTimestamp(isoString, selectedRegion, banner.phase, isEnd);
    const date = new Date(timestamp);
    const tz = REGION_TIMEZONES[selectedRegion];

    return date.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: tz,
    });
  };

  // Calculate remaining time in only days, hours, and minutes
  const getRemainingTime = () => {
    if (!banner.end_date) {
      return { isPermanent: true, text: 'Permanent Banner', isUrgent: false, progress: 0 };
    }

    const end = getBannerTimestamp(banner.end_date, selectedRegion, banner.phase, true);
    const start = getBannerTimestamp(banner.start_date, selectedRegion, banner.phase, false);
    const diffMs = end - now;

    if (diffMs <= 0) {
      return { isPermanent: false, text: 'Banner Ended', isUrgent: true, progress: 100 };
    }

    const totalDuration = end - start;
    const elapsed = now - start;
    const progress = Math.min(100, Math.max(0, (elapsed / (totalDuration || 1)) * 100));

    const totalMinutes = Math.floor(diffMs / (1000 * 60));
    const days = Math.floor(totalMinutes / (60 * 24));
    const hours = Math.floor((totalMinutes % (60 * 24)) / 60);
    const minutes = totalMinutes % 60;

    const isUrgent = days === 0 && hours < 24;

    let text = '';
    if (days > 0) {
      text = `${days}d ${hours}h ${minutes}m`;
    } else if (hours > 0) {
      text = `${hours}h ${minutes}m`;
    } else if (minutes > 0) {
      text = `${minutes}m`;
    } else {
      text = '< 1m';
    }

    return { isPermanent: false, text, isUrgent, progress, days, hours, minutes };
  };

  const remaining = getRemainingTime();

  // Extract 5-star rewards (featured limited) and 4-star rate ups
  const fiveStarRewards: Reward[] =
    banner.limited_rewards && banner.limited_rewards.length > 0
      ? banner.limited_rewards
      : (banner.rewards || []).filter((r) => r.is_featured || r.rarity === 5);

  const fourStarRewards: Reward[] =
    banner.low_rate_rewards && banner.low_rate_rewards.length > 0
      ? banner.low_rate_rewards
      : (banner.rewards || []).filter((r) => !r.is_featured && r.rarity === 4);

  const getFeaturedWishUrl = (): string | null => {
    if (!fiveStarRewards.length) return null;
    const data = fiveStarRewards[0]?.extra_data;
    if (!data) return null;
    return data.local_wish || data.wish_url || null;
  };

  const getRewardIconUrl = (reward: Reward): string | null => {
    const data = reward.extra_data;
    if (!data) return null;
    return data.local_icon || data.icon_url || null;
  };

  const featuredWishUrl = getFeaturedWishUrl();

  return (
    <article
      className="banner-card animate-fade-in"
      style={{ animationDelay: `${index * 0.08}s` }}
    >
      {/* Banner Graphic Slot (Wish Art / Splash or Patterned Fallback) */}
      <div className="banner-graphic-placeholder">
        {featuredWishUrl ? (
          <>
            <img
              src={featuredWishUrl}
              alt={fiveStarRewards[0]?.name || 'Banner Art'}
              className="banner-art-img"
              loading="lazy"
              referrerPolicy="no-referrer"
              onError={(e) => {
                // If image fails to load, hide image element and show fallback
                e.currentTarget.style.display = 'none';
              }}
            />
            <div className="banner-art-gradient-overlay" />
          </>
        ) : (
          <>
            <div className="placeholder-pattern" />
            <div className="placeholder-content">
              <div className="placeholder-icon-pill">
                <ImageIcon size={18} className="placeholder-icon" />
                <span>Banner Graphic Area</span>
              </div>
              <span className="placeholder-subtext">Slot reserved for official banner art</span>
            </div>
          </>
        )}

        {/* Overlay Badges */}
        <div className="graphic-overlay-top">
          <span className="version-badge">
            v{banner.version} {banner.phase > 0 ? `• Phase ${banner.phase}` : ''}
          </span>
          <span className="banner-type-badge">
            {formatBannerType(banner.banner_type)}
          </span>
        </div>

        {/* Countdown Pill with only hours and minutes */}
        <div className="graphic-overlay-bottom">
          <span className={`countdown-pill ${remaining.isUrgent ? 'urgent' : ''}`}>
            {remaining.isUrgent ? <AlertCircle size={13} /> : <Clock size={13} />}
            <span className="countdown-time-digits">
              {remaining.isPermanent ? 'Permanent' : `Ends in ${remaining.text}`}
            </span>
          </span>
        </div>
      </div>

      {/* Progress Bar for Active Banner */}
      {!remaining.isPermanent && (
        <div className="banner-progress-track" title={`${remaining.progress.toFixed(1)}% elapsed`}>
          <div
            className="banner-progress-bar"
            style={{ width: `${remaining.progress}%` }}
          />
        </div>
      )}

      {/* Card Body */}
      <div className="banner-card-body">
        {/* 5-Star Featured Section */}
        <div className="featured-section">
          <div className="featured-header">
            <div className="stars-row five-star-stars">
              <Sparkles size={14} className="star-icon" />
              <span>★★★★★ 5-STAR FEATURED</span>
            </div>
            <span className="rate-boost-tag">Rate Up</span>
          </div>

          <div className="five-star-list">
            {fiveStarRewards.length > 0 ? (
              fiveStarRewards.map((reward, i) => {
                const iconUrl = getRewardIconUrl(reward);
                return (
                  <div key={i} className="five-star-item">
                    <div className="reward-avatar-placeholder gold-glow">
                      {iconUrl ? (
                        <img
                          src={iconUrl}
                          alt={reward.name}
                          className="reward-avatar-img"
                          loading="lazy"
                          referrerPolicy="no-referrer"
                          onError={(e) => {
                            e.currentTarget.style.display = 'none';
                          }}
                        />
                      ) : (
                        <>
                          <User size={20} className="avatar-icon" />
                          <span className="avatar-placeholder-label">5★ Art</span>
                        </>
                      )}
                    </div>
                    <div className="reward-details">
                      <h3 className="five-star-name">{reward.name}</h3>
                      <span className="reward-type-label">Featured Exclusive Rate-Up</span>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="empty-reward-note">Featured 5★ Character / Weapon</div>
            )}
          </div>
        </div>

        {/* 4-Star Rate-Up Lineup */}
        {fourStarRewards.length > 0 && (
          <div className="four-star-section">
            <div className="four-star-header">
              <span className="four-star-title">★★★★ 4-STAR RATE-UP CHARACTERS</span>
            </div>
            <div className="four-star-chips-grid">
              {fourStarRewards.map((reward, i) => {
                const iconUrl = getRewardIconUrl(reward);
                return (
                  <div key={i} className="four-star-chip">
                    {iconUrl ? (
                      <img
                        src={iconUrl}
                        alt={reward.name}
                        className="mini-avatar-img"
                        loading="lazy"
                        referrerPolicy="no-referrer"
                        onError={(e) => {
                          e.currentTarget.style.display = 'none';
                        }}
                      />
                    ) : (
                      <div className="mini-avatar-placeholder">
                        <Shield size={12} />
                      </div>
                    )}
                    <span className="four-star-name">{reward.name}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Schedule & Timing Info */}
        <div className="banner-schedule-footer">
          <div className="schedule-item">
            <Calendar size={14} className="footer-icon" />
            <span className="schedule-label">
              {selectedRegion !== 'ALL' ? `${selectedRegion} Server Time:` : 'Duration:'}
            </span>
            <span className="schedule-value">
              {formatDate(banner.start_date, false)} — {formatDate(banner.end_date, true)}
            </span>
          </div>
        </div>
      </div>
    </article>
  );
};
