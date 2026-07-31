/**
 * Favicon URLs, resolved by the backend rather than guessed here.
 *
 * This file used to pick between the www and non-www spelling of a host and
 * hope. It cannot be done in the browser: Google answers a host it has no icon
 * for with a generic globe at HTTP 200 — a valid, decodable 16x16 PNG — so
 * `<img>` fires `load` rather than `error` and no fallback chain runs. The
 * status is unreadable too (no access-control-allow-origin on either
 * google.com/s2 or t*.gstatic.com, so fetch() is opaque and canvas is
 * tainted), and size is not a signal because some real icons are also 16x16.
 *
 * Nor is there a fixed rule to apply, since domains need opposite answers:
 *
 *     menolabs.com   www -> placeholder   bare -> real
 *     racold.com     www -> real          bare -> placeholder
 *
 * /favicon/ does the comparison server-side, where the bytes are readable,
 * and caches the winner. See backend/core/favicon_proxy.py.
 */

import { API_BASE_URL } from "@/services/api";

/** Bare hostname from a URL or host string. */
const hostOf = (url: string): string => {
  if (!url) return "";
  try {
    const full = /^https?:\/\//i.test(url) ? url : `https://${url}`;
    return new URL(full).hostname;
  } catch {
    return String(url).replace(/^https?:\/\//i, "").split("/")[0];
  }
};

export const getFaviconUrl = (url: string, size: number = 32): string => {
  const host = hostOf(url);
  if (!host) return "";
  return `${API_BASE_URL}/favicon/?domain=${encodeURIComponent(host)}&size=${size}`;
};

/**
 * Kept for the existing call sites. There is no second URL to try any more —
 * the backend has already tried every candidate before answering — so this
 * returns nothing and the error handler goes straight to the placeholder.
 */
export const getAlternativeFaviconUrl = (_url: string, _size: number = 32): string => "";

/**
 * Get fallback placeholder icon URL
 */
export const getFallbackIconUrl = (name?: string): string => {
  if (name) {
    // Use UI Avatars as fallback with first letter of name
    const initial = name.charAt(0).toUpperCase();
    return `https://ui-avatars.com/api/?name=${encodeURIComponent(initial)}&background=3b82f6&color=fff&size=128`;
  }
  // Default fallback
  return '/favicon.ico';
};

/**
 * Handle favicon load error.
 *
 * Now only fires for a genuine failure — the backend answers 404 when no real
 * icon exists anywhere, which DOES trigger this, unlike Google's 200-with-a-
 * globe. One step to the initial-avatar, then give up.
 */
export const handleFaviconError = (
  event: React.SyntheticEvent<HTMLImageElement>,
  originalUrl: string,
  name?: string,
  size: number = 32
): void => {
  const img = event.currentTarget;
  const fallbackUrl = getFallbackIconUrl(name);

  if (img.dataset.faviconAttempt) {
    img.style.display = 'none';
    return;
  }

  img.dataset.faviconAttempt = '1';
  img.src = fallbackUrl;
};
