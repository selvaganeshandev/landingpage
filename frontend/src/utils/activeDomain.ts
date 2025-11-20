// utils/activeDomain.ts
// Active domain management with server sync

// Track the last update timestamp to prevent race conditions
const lastUpdateTimestamp: { [key: string]: number } = {};

export function getActiveDomainKey(userId: string | number): string {
  return `active_domain_id:${String(userId)}`;
}

function getLegacyKey(userId: string | number): string {
  return `selected_domain_user_${String(userId)}`;
}

function getTimestampKey(userId: string | number): string {
  return `active_domain_timestamp:${String(userId)}`;
}

/**
 * Load active domain from localStorage (cache)
 * This is a fast read for immediate use, but should be synced with server
 */
export function loadActiveDomain(userId: string | number): string | null {
  try {
    const current = localStorage.getItem(getActiveDomainKey(userId));
    if (current) return current;

    // Fallback to legacy key
    const legacy = localStorage.getItem(getLegacyKey(userId));
    if (legacy) {
      localStorage.setItem(getActiveDomainKey(userId), legacy);
      return legacy;
    }

    return null;
  } catch {
    return null;
  }
}

/**
 * Save active domain to localStorage (cache only)
 * Use syncActiveDomainToServer() to persist to database
 * NOTE: Only stores in active_domain_id key, legacy key is no longer written
 */
export function saveActiveDomain(userId: string | number, domainId: string | number | null, skipTimestamp = false): void {
  try {
    const userIdStr = String(userId);
    const activeKey = getActiveDomainKey(userIdStr);
    const timestampKey = getTimestampKey(userIdStr);

    if (domainId === null || domainId === undefined) {
      localStorage.removeItem(activeKey);
      localStorage.removeItem(timestampKey);
      // Also remove legacy key if it exists (cleanup)
      const legacyKey = getLegacyKey(userIdStr);
      localStorage.removeItem(legacyKey);
    } else {
      const idStr = String(domainId);
      localStorage.setItem(activeKey, idStr);
      if (!skipTimestamp) {
        const timestamp = Date.now();
        localStorage.setItem(timestampKey, String(timestamp));
        lastUpdateTimestamp[userIdStr] = timestamp;
      }
    }
  } catch (error) {
    // Silently ignore localStorage errors
  }
}

/**
 * Sync active domain to server (database)
 * This is the primary source of truth
 */
export async function syncActiveDomainToServer(domainId: number | null): Promise<boolean> {
  try {
    const { apiClient } = await import('@/services/api');
    await apiClient.updateActiveDomain(domainId);
    return true;
  } catch (error) {
    return false;
  }
}

/**
 * Load active domain from server and cache in localStorage
 * Returns the active domain ID from server, or null if not set
 * NOTE: This will NOT overwrite a recent local update (within 2 seconds)
 */
export async function loadActiveDomainFromServer(userId: string | number): Promise<string | null> {
  try {
    const userIdStr = String(userId);
    const timestampKey = getTimestampKey(userIdStr);

    // Check if there was a recent update (within 2 seconds)
    const lastTimestamp = localStorage.getItem(timestampKey);
    if (lastTimestamp) {
      const timeSinceUpdate = Date.now() - parseInt(lastTimestamp, 10);
      if (timeSinceUpdate < 2000) {
        return loadActiveDomain(userId);
      }
    }

    const { apiClient } = await import('@/services/api');
    const profile: any = await apiClient.getProfile();
    const activeDomainId = profile?.user?.active_domain_id;

    // Explicitly check for null, undefined, or falsy values
    if (activeDomainId !== null && activeDomainId !== undefined && activeDomainId !== '') {
      const idStr = String(activeDomainId);
      // Save but skip timestamp update (this is from server, not user action)
      saveActiveDomain(userId, idStr, true);
      return idStr;
    } else {
      // Clear cache if server has no active domain (null or undefined)
      saveActiveDomain(userId, null, true);
      return null;
    }
  } catch (error) {
    // Fallback to localStorage cache
    return loadActiveDomain(userId);
  }
}

/**
 * Update active domain (both server and localStorage)
 * This is the main function to use when changing domains
 * Also syncs with Zustand domain store
 */
export async function updateActiveDomain(
  userId: string | number,
  domainId: number | null,
  domain?: any // Optional domain object to sync with Zustand store
): Promise<boolean> {
  try {
    const userIdStr = String(userId);

    // Update localStorage immediately (optimistic update)
    saveActiveDomain(userIdStr, domainId);

    // Sync with Zustand domain store if domain object is provided
    if (domain) {
      try {
        const { useDomainStore } = await import('@/stores/domainStore');
        const store = useDomainStore.getState();
        store.setSelectedDomain(domain);
      } catch (storeError) {
        // Silently ignore store sync errors
      }
    }

    // Sync to server
    const success = await syncActiveDomainToServer(domainId);

    if (!success) {
      // If server sync fails, revert to server value
      await loadActiveDomainFromServer(userIdStr);
      return false;
    }

    return true;
  } catch (error) {
    return false;
  }
}

export function clearActiveDomain(userId: string | number): void {
  saveActiveDomain(userId, null);
}

/**
 * Clear all active domain related localStorage values for a user
 * This includes both the primary key and legacy key
 */
export function clearAllActiveDomainStorage(userId: string | number): void {
  try {
    const userIdStr = String(userId);
    const activeKey = getActiveDomainKey(userIdStr);
    const legacyKey = getLegacyKey(userIdStr);

    localStorage.removeItem(activeKey);
    localStorage.removeItem(legacyKey);
  } catch (error) {
    // Silently ignore errors
  }
}

/**
 * Get active domain ID for current user (unified helper for all components)
 * This function:
 * 1. Tries to get userId from AuthContext (preferred)
 * 2. Falls back to parsing JWT token
 * 3. Returns active domain ID from localStorage (fast read)
 * 
 * For server-synced value, use loadActiveDomainFromServer() instead
 */
export function getActiveDomainId(user: any = null): string | null {
  try {
    let userId: string | number | null = null;

    // Try to get from user object (from AuthContext)
    if (user?.id) {
      userId = user.id;
    } else {
      // Fallback: parse JWT token
      try {
        const token = localStorage.getItem('access_token') || '';
        if (token) {
          const payload = JSON.parse(atob(token.split('.')[1] || '""'));
          userId = payload?.user_id || payload?.id || null;
        }
      } catch {
        // ignore
      }
    }

    if (!userId) {
      return null;
    }

    return loadActiveDomain(userId);
  } catch (error) {
    return null;
  }
}

/**
 * Get active domain ID as number (for API calls)
 */
export function getActiveDomainIdNumber(user: any = null): number | null {
  const id = getActiveDomainId(user);
  if (!id) return null;
  const numId = parseInt(id, 10);
  return isNaN(numId) ? null : numId;
}
