import React, { useState, useEffect } from 'react';
import type { Banner, Reward, ServerRegion } from '../types/banner';
import { getBannerCategory, formatBannerType } from '../types/banner';
import {
  Sparkles,
  Calendar,
  Clock,
  Image as ImageIcon,
  User,
  Shield,
  AlertCircle,
  Sword,
  Sparkle,
} from 'lucide-react';

interface BannerCardProps {
  banner: Banner;
  index: number;
  gameName?: string;
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
  gameName,
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

  const category = getBannerCategory(banner.banner_type);
  const isWeapon = category === 'WEAPON';
  const isCharacter = category === 'CHARACTER';

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

  // Calculate remaining or upcoming time
  const getBannerTimingStatus = () => {
    const start = getBannerTimestamp(banner.start_date, selectedRegion, banner.phase, false);

    // Case 1: Banner hasn't started yet (Upcoming)
    if (start > now) {
      const diffMs = start - now;
      const totalMinutes = Math.floor(diffMs / (1000 * 60));
      const days = Math.floor(totalMinutes / (60 * 24));
      const hours = Math.floor((totalMinutes % (60 * 24)) / 60);
      const minutes = totalMinutes % 60;

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

      return {
        isUpcoming: true,
        isPermanent: false,
        text,
        isUrgent: false,
        progress: 0,
        label: `Starts in ${text}`,
      };
    }

    // Case 2: Permanent Banner
    if (!banner.end_date) {
      return {
        isUpcoming: false,
        isPermanent: true,
        text: 'Permanent',
        isUrgent: false,
        progress: 0,
        label: 'Permanent Banner',
      };
    }

    // Case 3: Active Banner with End Date
    const end = getBannerTimestamp(banner.end_date, selectedRegion, banner.phase, true);
    const diffMs = end - now;

    if (diffMs <= 0) {
      return {
        isUpcoming: false,
        isPermanent: false,
        text: 'Ended',
        isUrgent: true,
        progress: 100,
        label: 'Banner Ended',
      };
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

    return {
      isUpcoming: false,
      isPermanent: false,
      text,
      isUrgent,
      progress,
      label: `Ends in ${text}`,
    };
  };

  const timing = getBannerTimingStatus();

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
    const firstReward = fiveStarRewards[0];
    const data = firstReward?.extra_data;
    const item = firstReward?.item;
    return (
      item?.local_wish ||
      item?.wish_url ||
      data?.local_wish ||
      data?.wish_url ||
      data?.local_icon ||
      data?.icon_url ||
      (data?.prydwen_art as string | undefined) ||
      (data?.prydwen_icon as string | undefined) ||
      null
    );
  };

  const getRewardIconUrl = (reward: Reward): string | null => {
    const data = reward.extra_data;
    const item = reward.item;
    return (
      item?.local_icon ||
      item?.icon_url ||
      data?.local_icon ||
      data?.icon_url ||
      item?.local_wish ||
      item?.wish_url ||
      data?.local_wish ||
      data?.wish_url ||
      (data?.prydwen_icon as string | undefined) ||
      (data?.prydwen_art as string | undefined) ||
      null
    );
  };

  const featuredWishUrl = getFeaturedWishUrl();
  const formattedType = formatBannerType(banner.banner_type, gameName);

  return (
    <article
      className={`banner-card banner-card--${category.toLowerCase()} ${
        timing.isUpcoming ? 'banner-card--upcoming' : 'banner-card--active'
      } animate-fade-in`}
      style={{ animationDelay: `${index * 0.06}s` }}
      data-category={category}
    >
      {/* Category Indicator Accent Header Bar */}
      <div className={`card-category-strip strip--${category.toLowerCase()}`} />

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
            <div className={`placeholder-pattern pattern--${category.toLowerCase()}`} />
            <div className="placeholder-content">
              <div className={`placeholder-icon-pill pill--${category.toLowerCase()}`}>
                {isWeapon ? (
                  <Shield size={16} className="placeholder-icon" />
                ) : isCharacter ? (
                  <User size={16} className="placeholder-icon" />
                ) : (
                  <ImageIcon size={16} className="placeholder-icon" />
                )}
                <span>
                  {isWeapon ? 'Weapon / Light Cone Art' : isCharacter ? 'Character Art' : 'Banner Graphic'}
                </span>
              </div>
              <span className="placeholder-subtext">Slot reserved for official event art</span>
            </div>
          </>
        )}

        {/* Overlay Badges Top */}
        <div className="graphic-overlay-top">
          <span className={`version-badge ${timing.isUpcoming ? 'version-badge--upcoming' : ''}`}>
            {timing.isUpcoming && <span className="upcoming-pulse-dot" title="Upcoming Banner" />}
            v{banner.version} {banner.phase > 0 ? `• Phase ${banner.phase}` : ''}
          </span>

          <span className={`banner-type-badge badge--${category.toLowerCase()}`}>
            {isWeapon ? (
              <Shield size={12} className="type-icon" />
            ) : isCharacter ? (
              <Sword size={12} className="type-icon" />
            ) : (
              <Sparkle size={12} className="type-icon" />
            )}
            <span>{formattedType}</span>
          </span>
        </div>

        {/* Countdown Pill Bottom */}
        <div className="graphic-overlay-bottom">
          <span
            className={`countdown-pill ${
              timing.isUpcoming ? 'upcoming' : timing.isUrgent ? 'urgent' : 'active'
            }`}
          >
            {timing.isUpcoming ? (
              <Clock size={13} className="countdown-icon" />
            ) : timing.isUrgent ? (
              <AlertCircle size={13} className="countdown-icon" />
            ) : (
              <Clock size={13} className="countdown-icon" />
            )}
            <span className="countdown-time-digits">{timing.label}</span>
          </span>
        </div>
      </div>

      {/* Progress Bar for Active Banner */}
      {!timing.isPermanent && !timing.isUpcoming && (
        <div
          className="banner-progress-track"
          title={`${timing.progress.toFixed(1)}% time elapsed`}
        >
          <div
            className={`banner-progress-bar bar--${category.toLowerCase()}`}
            style={{ width: `${timing.progress}%` }}
          />
        </div>
      )}

      {/* Card Body */}
      <div className="banner-card-body">
        {/* 5-Star Featured Section */}
        <div className={`featured-section featured--${category.toLowerCase()}`}>
          <div className="featured-header">
            <div className="stars-row five-star-stars">
              <Sparkles size={14} className="star-icon" />
              <span>
                ★★★★★ 5-STAR {isWeapon ? 'FEATURED WEAPON' : 'FEATURED CHARACTER'}
              </span>
            </div>
            <span className={`rate-boost-tag tag--${category.toLowerCase()}`}>Rate Up</span>
          </div>

          <div className="five-star-list">
            {fiveStarRewards.length > 0 ? (
              fiveStarRewards.map((reward, i) => {
                const iconUrl = getRewardIconUrl(reward);
                return (
                  <div key={i} className="five-star-item">
                    <div className={`reward-avatar-placeholder gold-glow avatar--${category.toLowerCase()}`}>
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
                          {isWeapon ? (
                            <Shield size={20} className="avatar-icon" />
                          ) : (
                            <User size={20} className="avatar-icon" />
                          )}
                          <span className="avatar-placeholder-label">5★</span>
                        </>
                      )}
                    </div>
                    <div className="reward-details">
                      <h3 className="five-star-name">{reward.name}</h3>
                      <span className="reward-type-label">
                        {isWeapon
                          ? 'Featured Exclusive Light Cone / Weapon'
                          : 'Featured Exclusive Character'}
                      </span>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="empty-reward-note">
                {isWeapon ? 'Featured 5★ Weapon' : 'Featured 5★ Character'}
              </div>
            )}
          </div>
        </div>

        {/* 4-Star Rate-Up Lineup */}
        {fourStarRewards.length > 0 && (
          <div className="four-star-section">
            <div className="four-star-header">
              <span className="four-star-title">
                ★★★★ 4-STAR RATE-UP {isWeapon ? 'EQUIPMENT' : 'CHARACTERS'}
              </span>
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
                        {isWeapon ? <Shield size={12} /> : <User size={12} />}
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
              {selectedRegion !== 'ALL' ? `${selectedRegion} Server:` : 'Event Period:'}
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
