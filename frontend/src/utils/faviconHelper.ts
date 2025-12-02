/**
 * Utility functions for handling favicons with www/non-www fallback
 */

/**
 * Generate favicon URL with protocol
 * Automatically adds www. if domain doesn't have it (improves success rate)
 */
export const getFaviconUrl = (url: string, size: number = 32): string => {
  try {
    // Ensure URL has protocol
    const fullUrl = url.startsWith('http://') || url.startsWith('https://')
      ? url
      : `https://${url}`;

    const parsedUrl = new URL(fullUrl);
    let hostname = parsedUrl.hostname;

    // If hostname doesn't start with www., try adding it
    // Many sites work with www but not without (e.g., www.edelweisslife.in works, edelweisslife.in doesn't)
    if (!hostname.startsWith('www.') && !hostname.match(/^[0-9.]+$/)) { // Don't add www to IP addresses
      hostname = `www.${hostname}`;
    }

    // Pass the full URL with protocol to Google's favicon service
    return `https://www.google.com/s2/favicons?domain=${parsedUrl.protocol}//${hostname}&sz=${size}`;
  } catch {
    // Fallback if URL parsing fails - add www if not present
    const normalizedUrl = url.startsWith('www.') ? url : `www.${url}`;
    return `https://www.google.com/s2/favicons?domain=${normalizedUrl}&sz=${size}`;
  }
};

/**
 * Generate alternative favicon URL (toggle www/non-www)
 * If URL has www, returns non-www version and vice versa
 */
export const getAlternativeFaviconUrl = (url: string, size: number = 32): string => {
  try {
    // Ensure URL has protocol
    const fullUrl = url.startsWith('http://') || url.startsWith('https://')
      ? url
      : `https://${url}`;

    const parsedUrl = new URL(fullUrl);
    let hostname = parsedUrl.hostname;

    // Since getFaviconUrl already tries www., this should try non-www
    // Remove www if present (toggle opposite of what getFaviconUrl does)
    if (hostname.startsWith('www.')) {
      hostname = hostname.substring(4);
    }
    // If www was already added by getFaviconUrl and failed, don't add it again
    // Just return empty to skip to fallback

    return hostname === parsedUrl.hostname ? '' : `https://www.google.com/s2/favicons?domain=${parsedUrl.protocol}//${hostname}&sz=${size}`;
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
