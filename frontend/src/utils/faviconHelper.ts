/**
 * Utility functions for handling favicons with www/non-www fallback
 */

/**
 * Generate favicon URL for a domain, using the host exactly as stored.
 *
 * This used to prepend "www." to every host that lacked it, to help apex
 * domains that only serve a favicon from www. But it applied the rule blindly,
 * so a SUBDOMAIN became a host that does not exist: trucks.tatamotors.com was
 * requested as www.trucks.tatamotors.com, which resolves nowhere, and every
 * subdomain silently fell through to the placeholder icon.
 *
 * The host is now used as given. The www variant is still tried — it is what
 * getAlternativeFaviconUrl toggles to on error — so the apex-only case still
 * resolves, one request later.
 */
export const getFaviconUrl = (url: string, size: number = 32): string => {
  try {
    // Ensure URL has protocol
    const fullUrl = url.startsWith('http://') || url.startsWith('https://')
      ? url
      : `https://${url}`;

    const parsedUrl = new URL(fullUrl);

    // Pass the full URL with protocol to Google's favicon service
    return `https://www.google.com/s2/favicons?domain=${parsedUrl.protocol}//${parsedUrl.hostname}&sz=${size}`;
  } catch {
    // Parsing failed — send what we were given rather than inventing a host.
    return `https://www.google.com/s2/favicons?domain=${url}&sz=${size}`;
  }
};

/**
 * Second attempt: the www/non-www counterpart of getFaviconUrl.
 *
 * Adding "www." is only meaningful for a registrable domain — "www" in front of
 * a subdomain is a host nobody publishes — so it is offered only when the host
 * has no subdomain of its own. Multi-part suffixes (.co.uk, .com.au, .bank.in)
 * mean label-counting alone would misread example.co.uk as a subdomain, so
 * those are recognised explicitly.
 */
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
      alternative = hostname.substring(4);
    } else if (isRegistrableDomain(hostname)) {
      alternative = `www.${hostname}`;
    } else {
      // A subdomain that already failed — there is no www variant worth trying,
      // so fall straight through to the placeholder.
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
