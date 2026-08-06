import { useState, useEffect, Suspense } from "react";
import { Sidebar } from "./Sidebar";
import { PageLoader } from "./PageLoader";
import { RouteFallback } from "./RouteFallback";
import { ProcessingStateCard } from "./ProcessingStateCard";
import { OnboardingModal } from "./OnboardingModal";
import { Outlet, useLocation } from "react-router-dom";
import { useSidebar } from "@/contexts/SidebarContext";
import { useDomainStore } from "@/stores/domainStore";
import { useAuth } from "@/contexts/AuthContext";
import { isDomainProcessing, isCompetitorProcessing, isMisinformationProcessing } from "@/utils/processingStatus";

export const Layout = () => {
  const [showOnboarding, setShowOnboarding] = useState(false);
  const location = useLocation();
  const { isOpen: sidebarOpen } = useSidebar();
  const { domains, selectedDomain, isDomainSwitching, isLoading: domainsLoading, loadDomains, setSelectedDomain } = useDomainStore();
  const { user } = useAuth();

  // Show onboarding when domains are loaded but empty
  useEffect(() => {
    if (!domainsLoading && domains.length === 0) {
      setShowOnboarding(true);
    } else {
      setShowOnboarding(false);
    }
  }, [domains, domainsLoading]);

  // Handle onboarding complete
  const handleOnboardingComplete = async (newDomain: any) => {
    setShowOnboarding(false);
    // Reload domains and select the new one
    await loadDomains();
    setSelectedDomain(newDomain);
  };

  // Pages that require completed prompt processing
  const promptDataPages = [
    '/insights',
    '/mentions',
    '/prompts',
    '/citations',
    '/sentiment',
    '/topics',
    '/share-of-voice',
    '/trends',
    '/alerts',
    '/content-gaps',
    '/reports',
    '/traffic',
    '/multilingual',
    '/content-calendar',
  ];

  // Pages that specifically need competitor analysis
  const competitorPages = [
    '/competitors',
    '/content-gaps',
    '/share-of-voice',
  ];

  // Pages that specifically need misinformation scanning
  const misinformationPages = [
    '/misinformation',
  ];

  // Pages that don't require domain data (have their own loading states)
  const noDomainDataPages = [
    '/organization-settings',
    '/profile',
  ];

  // Determine if we should show processing state based on current page
  const shouldShowProcessingState = () => {
    if (!selectedDomain) return false;

    const currentPath = location.pathname;

    // Check if on a competitor-specific page and competitor analysis is processing
    if (competitorPages.some(page => currentPath.startsWith(page))) {
      return isCompetitorProcessing(selectedDomain) ||
             (selectedDomain.processing_status !== 'COMP');
    }

    // Check if on misinformation page and scan is processing
    if (misinformationPages.some(page => currentPath.startsWith(page))) {
      return isMisinformationProcessing(selectedDomain) ||
             (selectedDomain.processing_status !== 'COMP');
    }

    // For all other data pages, show processing if prompt processing is not complete
    if (promptDataPages.some(page => currentPath.startsWith(page))) {
      return isDomainProcessing(selectedDomain);
    }

    return false;
  };

  // Don't show domain switching loader on pages that don't require domain data
  const shouldShowDomainSwitchingLoader =
    isDomainSwitching &&
    !noDomainDataPages.some(page => location.pathname.startsWith(page));

  // There used to be a `setIsLoading(true)` here on every pathname change,
  // cleared 300ms later, which painted the full-screen PageLoader over the
  // whole content area on EVERY menu click — a guaranteed spinner flash even
  // for a page that had all its data cached and could have rendered instantly.
  // Navigation is client-side; pages own their loading states. Nothing needs a
  // blanket delay.

  // Show onboarding modal if no domains
  if (showOnboarding) {
    return <OnboardingModal onComplete={handleOnboardingComplete} user={user} />;
  }

  return (
    <div className="flex min-h-screen gradient-subtle">
      {shouldShowDomainSwitchingLoader && <PageLoader sidebarOpen={sidebarOpen} />}
      <Sidebar />
      <main className="flex-1 overflow-auto">
        {/* Suspense sits HERE, not around <Routes> in App: a boundary above the
            Layout unmounts the sidebar and shell too, so the first visit to a
            code-split page blanked the entire window. Scoped to the content
            area, the shell stays put and only the page swaps. */}
        <Suspense fallback={<RouteFallback />}>
          {shouldShowProcessingState() ? (
            <ProcessingStateCard domain={selectedDomain!} />
          ) : (
            <Outlet />
          )}
        </Suspense>
      </main>

      {/* The floating "New Chat" shortcut was removed: it sat fixed at
          bottom-right on every page at z-50, overlapping table rows, pagination
          and dialog corners. Chat is still reachable from the sidebar. */}
    </div>
  );
};
