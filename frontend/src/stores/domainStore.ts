import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface Domain {
  id: number;
  name: string;
  url: string;
  organisation: number;
  total_mentions: number;
  total_citations: number;
  visibility_score: string;
  average_position: string;
  active_alerts: number;
  sentiment: string;
  sentiment_score: string;
  created_at: string;
  modified_at: string;
}

interface DomainState {
  domains: Domain[];
  selectedDomain: Domain | null;
  isLoading: boolean;
  error: string | null;
  
  // Actions
  setDomains: (domains: Domain[]) => void;
  setSelectedDomain: (domain: Domain | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  loadDomains: () => Promise<void>;
  selectDomainById: (id: number) => void;
  selectDefaultDomain: () => void;
  clearDomainStore: () => void;
}

export const useDomainStore = create<DomainState>()(
  persist(
    (set, get) => ({
      domains: [],
      selectedDomain: null,
      isLoading: false,
      error: null,

      setDomains: (domains) => set({ domains }),
      
      setSelectedDomain: (domain) => {
        set({ selectedDomain: domain });
        // Sync with active_domain_id localStorage when domain is set
        // NOTE: This only updates active_domain_id key, not the legacy key
        if (domain) {
          // Use async IIFE to handle dynamic import
          (async () => {
            try {
              // Try to get userId from localStorage token
              const token = localStorage.getItem('access_token') || '';
              if (token) {
                try {
                  const payload = JSON.parse(atob(token.split('.')[1] || '""'));
                  const userId = payload?.user_id || payload?.id;
                  if (userId) {
                    const { saveActiveDomain } = await import('@/utils/activeDomain');
                    saveActiveDomain(userId, domain.id);
                    console.log(`[domainStore] Synced active_domain_id:${userId} with domain ${domain.id}`);
                  }
                } catch (e) {
                  // Ignore token parsing errors
                }
              }
            } catch (error) {
              console.warn('[domainStore] Failed to sync with active_domain_id:', error);
            }
          })();
        }
      },
      
      setLoading: (loading) => set({ isLoading: loading }),
      
      setError: (error) => set({ error }),
      
      loadDomains: async () => {
        try {
          set({ isLoading: true, error: null });
          
          // Import apiClient dynamically to avoid circular dependencies
          const { apiClient } = await import('@/services/api');
          const response = await apiClient.getDomains();
          
          set({ 
            domains: response.domains,
            selectedDomain: null, // Clear selected domain when loading fresh data
            isLoading: false 
          });
          
          // If no domain is selected and we have domains, select the first one
          const { selectedDomain } = get();
          if (!selectedDomain && response.domains.length > 0) {
            set({ selectedDomain: response.domains[0] });
          }
          
        } catch (error: any) {
          set({ 
            error: error.message || 'Failed to load domains',
            isLoading: false 
          });
        }
      },
      
      selectDomainById: (id) => {
        const { domains } = get();
        const domain = domains.find(d => d.id === id);
        if (domain) {
          set({ selectedDomain: domain });
        }
      },
      
      selectDefaultDomain: () => {
        const { domains } = get();
        if (domains.length > 0) {
          set({ selectedDomain: domains[0] });
        }
      },
      
      clearDomainStore: () => {
        set({ 
          domains: [], 
          selectedDomain: null, 
          error: null 
        });
      },
    }),
    {
      name: 'domain-store',
      partialize: (state) => ({
        selectedDomain: state.selectedDomain,
        domains: state.domains,
      }),
    }
  )
);
