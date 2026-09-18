import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface Domain {
  id: number;
  name: string;
  url: string;
  short_description?: string | null;
  country?: string;
  tone_of_voice?: string | null;
  content_style?: string | null;
  key_messages?: string | null;
  topics_to_avoid?: string | null;
  target_audience?: string | null;
  brand_values?: string | null;
  key_competitors?: string | null;
  organisation: number;
  total_mentions: number;
  total_citations: number;
  visibility_score: string;
  average_position: string;
  active_alerts: number;
  sentiment: string;
  sentiment_score: string;
  processing_status?: 'INIT' | 'SCHD' | 'PROC' | 'COMP' | 'FAIL';
  competitor_analysis_status?: 'NOT_READY' | 'READY' | 'ANALYZING' | 'COMPLETED';
  misinformation_scan_status?: 'NOT_READY' | 'READY' | 'SCANNING' | 'SCANNED' | 'NO_ISSUES';
  track_message?: string | null;
  tracked_at?: string | null;
  /** Prompts tracked for this project. Competitors, Topics and Misinformation
   *  are all derived from prompt responses, so 0 means those pages can only be
   *  empty and should point the user at Prompts first. */
  prompt_count?: number;
  /** Prompt groups in this project - what a sweep actually walks. */
  group_count?: number;
  /** How often the full sweep re-runs this project's prompts. Set on the
   *  Schedules screen and saved through PUT /domains/<id>/; the engine reads
   *  the same column to decide which projects a sweep run covers. */
  sweep_cadence?: 'weekly' | 'biweekly' | 'monthly' | 'off';
  /** When the sweep last covered this project. Written by the engine, so it is
   *  read-only here; null means it has not run since the field existed. */
  last_swept_at?: string | null;
  created_at: string;
  modified_at: string;
}

/** Sweep context that applies to the whole organisation, delivered on the same
 *  /domains/ response rather than from a second request. */
export interface SweepContext {
  /** AI platforms the engine has actually queried, from the analytics rows. */
  platforms: string[];
  /** The engine's kill switch. While false a sweep is refused even when forced,
   *  so the Schedules screen must not promise a next run. */
  enabled: boolean;
  disabled_reason: string;
  last_started_at: string | null;
}

interface DomainState {
  domains: Domain[];
  sweep: SweepContext | null;
  selectedDomain: Domain | null;
  isLoading: boolean;
  isDomainSwitching: boolean;
  error: string | null;

  // Actions
  setDomains: (domains: Domain[]) => void;
  setSelectedDomain: (domain: Domain | null) => void;
  setLoading: (loading: boolean) => void;
  setDomainSwitching: (switching: boolean) => void;
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
      sweep: null,
      selectedDomain: null,
      isLoading: false,
      isDomainSwitching: false,
      error: null,

      setDomains: (domains) => set({ domains }),

      setSelectedDomain: (domain) => {
        // Switching project must drop every cached read, or the new project's
        // pages would render the previous one's numbers until the entries aged
        // out. Guarded on the id actually changing: this setter is also called
        // by the server-sync effect with the SAME domain on every load, and
        // clearing there would defeat the cache entirely.
        const previousId = get().selectedDomain?.id;
        if (previousId !== domain?.id) {
          void import('@/services/api').then(({ clearApiCache }) => clearApiCache());
        }
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
                  }
                } catch (e) {
                  // Ignore token parsing errors
                }
              }
            } catch (error) {
              // Silently ignore sync errors
            }
          })();
        }
      },
      
      setLoading: (loading) => set({ isLoading: loading }),

      setDomainSwitching: (switching) => set({ isDomainSwitching: switching }),

      setError: (error) => set({ error }),
      
      loadDomains: async () => {
        try {
          set({ isLoading: true, error: null });

          // Import apiClient dynamically to avoid circular dependencies
          const { apiClient } = await import('@/services/api');
          // apiRequest resolves to `unknown`; name the shape once here so every
          // read below is checked rather than each one reaching into an any.
          const response = (await apiClient.getDomains()) as {
            domains: Domain[];
            sweep?: SweepContext;
          };

          // Get user ID to restore active domain
          let activeDomainId: string | null = null;
          try {
            const token = localStorage.getItem('access_token') || '';
            if (token) {
              const payload = JSON.parse(atob(token.split('.')[1] || '""'));
              const userId = payload?.user_id || payload?.id;
              if (userId) {
                // Import activeDomain utilities
                const { loadActiveDomain } = await import('@/utils/activeDomain');
                activeDomainId = loadActiveDomain(userId);
              }
            }
          } catch (e) {
            // Ignore token parsing errors
          }

          // Find the selected domain from cache
          let selectedDomain = null;
          if (activeDomainId) {
            const domainId = parseInt(activeDomainId, 10);
            selectedDomain = response.domains.find((d: any) => d.id === domainId) || null;
          }

          // If no cached domain or cached domain doesn't exist, select first completed domain
          if (!selectedDomain && response.domains.length > 0) {
            selectedDomain = response.domains.find((d: any) =>
              !d.processing_status || d.processing_status === 'COMP'
            ) || response.domains[0];
          }

          set({
            domains: response.domains,
            // Absent on the `fields=minimal` variant, so keep whatever we had
            // rather than blanking the Schedules screen mid-session.
            sweep: response.sweep ?? get().sweep,
            selectedDomain: selectedDomain,
            isLoading: false
          });

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
          sweep: null,
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
