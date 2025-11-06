// utils/activeDomain.ts

export function getActiveDomainKey(userId: string | number): string {
  return `active_domain_id:${String(userId)}`;
}

function getLegacyKey(userId: string | number): string {
  return `selected_domain_user_${String(userId)}`;
}

function tryReadLegacy(userId: string | number): string | null {
  try {
    const legacy = localStorage.getItem(getLegacyKey(userId));
    return legacy || null;
  } catch {
    return null;
  }
}

export function loadActiveDomain(userId: string | number): string | null {
  try {
    // Prefer the new key
    const current = localStorage.getItem(getActiveDomainKey(userId));
    if (current) return current;

    // Fallback to legacy key and backfill to the new key if found
    const legacy = tryReadLegacy(userId);
    if (legacy) {
      localStorage.setItem(getActiveDomainKey(userId), legacy);
      return legacy;
    }

    // Optional: try domain-store (if present) to extract selectedDomain.id
    const domainStore = localStorage.getItem('domain-store');
    if (domainStore) {
      try {
        const parsed = JSON.parse(domainStore);
        const sel = parsed?.state?.selectedDomain?.id || parsed?.selectedDomain?.id;
        if (sel) {
          const idStr = String(sel);
          localStorage.setItem(getActiveDomainKey(userId), idStr);
          localStorage.setItem(getLegacyKey(userId), idStr);
          return idStr;
        }
      } catch {
        // ignore parsing error
      }
    }

    return null;
  } catch {
    return null;
  }
}

export function saveActiveDomain(userId: string | number, domainId: string | number): void {
  try {
    const idStr = String(domainId);
    // Write both new and legacy keys for compatibility
    localStorage.setItem(getActiveDomainKey(userId), idStr);
    localStorage.setItem(getLegacyKey(userId), idStr);
  } catch {
    // no-op
  }
}

export function clearActiveDomain(userId: string | number): void {
  try {
    localStorage.removeItem(getActiveDomainKey(userId));
    localStorage.removeItem(getLegacyKey(userId));
  } catch {
    // no-op
  }
}
