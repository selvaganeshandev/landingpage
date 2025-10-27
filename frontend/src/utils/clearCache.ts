// Utility function to clear domain store cache from localStorage
export const clearDomainStoreCache = () => {
  localStorage.removeItem('domain-store');
  console.log('Domain store cache cleared from localStorage');
};

// You can call this function in the browser console if needed:
// clearDomainStoreCache();
