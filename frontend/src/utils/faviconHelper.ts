/**
 * Utility functions for handling favicons with www/non-www fallback
 */

/**
 * Favicon URL for a domain: "www." for a registrable domain, the host as-is
 * for a subdomain.
 *
 * The split exists because the two cases genuinely want opposite things, and
 * because a 404 CANNOT be detected here so the first URL has to be the right
 * one. Google answers a missing favicon with HTTP 404 whose body is a valid
 * 16x16 PNG; browsers decode 404 image bodies and fire `load`, not `error`, so
 * the onError chain below never runs for it. Reading the status directly is
 * not an option either — the endpoint sends no CORS headers, so fetch() can
 * only get an opaque response. Size is no signal either: trucks.tatamotors.com
 * serves a real 16x16 icon, the same dimensions as the placeholder.
 *
 * Measured against the service:
 *   racold.com              404   www.racold.com              200
 *   trucks.tatamotors.com   200   www.trucks.tatamotors.com   404
 *
 * So: www helps a registrable domain and breaks a subdomain, which is exactly
 * the rule applied here. Prefixing everything (the original behaviour) broke
 * every subdomain; prefixing nothing broke apex domains like racold.
 */
export const getFaviconUrl = (url: string, size: number = 32): string => {
  try {
    // Ensure URL has protocol
    const fullUrl = url.startsWith('http://') || url.startsWith('https://')
      ? url
      : `https://${url}`;

    const parsedUrl = new URL(fullUrl);
    const hostname = parsedUrl.hostname;
    const preferred = isRegistrableDomain(hostname) ? `www.${hostname}` : hostname;

    // Pass the full URL with protocol to Google's favicon service
    return `https://www.google.com/s2/favicons?domain=${parsedUrl.protocol}//${preferred}&sz=${size}`;
  } catch {
    // Parsing failed — send what we were given rather than inventing a host.
    return `https://www.google.com/s2/favicons?domain=${url}&sz=${size}`;
  }
};

const MULTI_PART_SUFFIXES = [
  'co.uk', 'org.uk', 'ac.uk', 'gov.uk',
  'com.au', 'net.au', 'org.au',
  'co.in', 'net.in', 'org.in', 'bank.in', 'gov.in', 'ac.in',
  'co.nz', 'co.za', 'co.jp', 'com.br', 'com.sg', 'com.my',
];

const isRegistrableDomain = (hostname: string): boolean => {
  if (hostname.match(/^[0-9.]+$/)) return false; // IP address
  const suffix = MULTI_PART_SUFFIXES.find((s) => hostname.endsWith(`.${s}`));
  const labels = hostname.split('.').length;
  return suffix ? labels === 3 : labels === 2;
};

/**
 * Second attempt: the counterpart of whatever getFaviconUrl chose.
 *
 * Only reached when the browser DOES fire an error (a genuine network failure
 * or an undecodable body). Google's 404-with-a-valid-PNG does not get here —
 * see the note on getFaviconUrl — which is why the first URL has to be right.
 */
export const getAlternativeFaviconUrl = (url: string, size: number = 32): string => {
  try {
    // Ensure URL has protocol
    const fullUrl = url.startsWith('http://') || url.startsWith('https://')
      ? url
      : `https://${url}`;

    const parsedUrl = new URL(fullUrl);
    const hostname = parsedUrl.hostname;

    let alternative: string;
    if (hostname.startsWith('www.')) {
      // Stored WITH www, so that is what was tried — drop it.
      alternative = hostname.substring(4);
    } else if (isRegistrableDomain(hostname)) {
      // www was tried first; the bare host is the remaining option.
      alternative = hostname;
    } else {
      // A subdomain, already tried as-is. "www" in front of it is a host
      // nobody publishes, so go straight to the placeholder.
      return '';
    }

    return `https://www.google.com/s2/favicons?domain=${parsedUrl.protocol}//${alternative}&sz=${size}`;
  } catch {
    return '';
  }
};

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
 * Handle favicon load error with cascading fallbacks
 * Usage in img tag: onError={(e) => handleFaviconError(e, url, name, size)}
 */
export const handleFaviconError = (
  event: React.SyntheticEvent<HTMLImageElement>,
  originalUrl: string,
  name?: string,
  size: number = 32
): void => {
  const img = event.currentTarget;
  const currentSrc = img.src;
  const primaryUrl = getFaviconUrl(originalUrl, size);
  const alternativeUrl = getAlternativeFaviconUrl(originalUrl, size);
  const fallbackUrl = getFallbackIconUrl(name);

  // Prevent infinite loop
  if (img.dataset.faviconAttempt) {
    const attempts = parseInt(img.dataset.faviconAttempt);

    if (attempts === 1) {
      // Second attempt: try alternative (www/non-www toggle)
      img.dataset.faviconAttempt = '2';
      img.src = alternativeUrl;
      return;
    } else if (attempts === 2) {
      // Third attempt: use fallback
      img.dataset.faviconAttempt = '3';
      img.src = fallbackUrl;
      return;
    } else {
      // Final fallback: hide image
      img.style.display = 'none';
      return;
    }
  }

  // First attempt failed, try alternative
  img.dataset.faviconAttempt = '1';
  img.src = alternativeUrl;
};
