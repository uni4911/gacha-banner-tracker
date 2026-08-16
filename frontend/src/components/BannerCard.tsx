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

// Standard server timezone offsets from UTC in hours (HoYoverse servers: Asia=UTC+8, Europe=UTC+1, America=UTC-5)
const SERVER_UTC_OFFSETS: Record<ServerRegion, number> = {
  ALL: 1, // Default Europe baseline
  ASIA: 8,
  EUROPE: 1,
  AMERICA: -5,
};

// Calculate exact UTC timestamp when a target wall-clock time occurs in the specified server timezone
function getBannerTimestamp(
  isoString: string | null | undefined,
  region: ServerRegion,
  phase: number,
  isEnd: boolean
): number {
  if (!isoString) return 0;
  const d = new Date(isoString);
  const y = d.getUTCFullYear();
  const m = d.getUTCMonth();
  const day = d.getUTCDate();

  // If the ISO string already contains specific hours/minutes and region is ALL, use direct timestamp
  const rawH = d.getUTCHours();
  const rawMin = d.getUTCMinutes();
  const rawS = d.getUTCSeconds();
  const isMidnight = rawH === 0 && rawMin === 0 && rawS === 0;

  if (!isMidnight && region === 'ALL') {
    return d.getTime();
  }

  // Calculate standard server wall-clock time
  let wallH: number;
  let wallMin: number;
  let wallSec: number;

  if (isEnd) {
    // Phase 1 ends at 17:59:59 server time
    // Phase 2 ends at 14:59:59 server time (before maintenance)
    wallH = phase === 2 ? 14 : 17;
    wallMin = 59;
    wallSec = 59;
  } else {
    if (phase === 2) {
      // Phase 2 starts at 18:00:00 server time
      wallH = 18;
      wallMin = 0;
      wallSec = 0;
    } else {
      // Phase 1 global launch starts at 06:00 UTC
      return Date.UTC(y, m, day, 6, 0, 0);
    }
  }

  const offsetHours = SERVER_UTC_OFFSETS[region] ?? 1;
  // Convert server wall-clock time to UTC: UTC = wallH - offsetHours
  return Date.UTC(y, m, day, wallH - offsetHours, wallMin, wallSec);
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

  return (
    <article
      className="banner-card animate-fade-in"
      style={{ animationDelay: `${index * 0.08}s` }}
    >
      {/* Graphic Placeholder Slot */}
      <div className="banner-graphic-placeholder">
        <div className="placeholder-pattern" />
        <div className="placeholder-content">
          <div className="placeholder-icon-pill">
            <ImageIcon size={18} className="placeholder-icon" />
            <span>Banner Graphic Area</span>
          </div>
          <span className="placeholder-subtext">Slot reserved for official banner art</span>
        </div>

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
              fiveStarRewards.map((reward, i) => (
                <div key={i} className="five-star-item">
                  <div className="reward-avatar-placeholder gold-glow">
                    <User size={20} className="avatar-icon" />
                    <span className="avatar-placeholder-label">5★ Art</span>
                  </div>
                  <div className="reward-details">
                    <h3 className="five-star-name">{reward.name}</h3>
                    <span className="reward-type-label">Featured Exclusive Rate-Up</span>
                  </div>
                </div>
              ))
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
              {fourStarRewards.map((reward, i) => (
                <div key={i} className="four-star-chip">
                  <div className="mini-avatar-placeholder">
                    <Shield size={12} />
                  </div>
                  <span className="four-star-name">{reward.name}</span>
                </div>
              ))}
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
