import { useState, useEffect, Suspense } from "react";
import { Sidebar } from "./Sidebar";
import { PageLoader } from "./PageLoader";
import { RouteFallback } from "./RouteFallback";
import { ProcessingBanner } from "./ProcessingBanner";
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

  // Determine whether to show the processing banner for the current page.
  //
  // The competitor and misinformation branches used to read
  // `processing_status !== 'COMP'`, which was tolerable when this gated a
  // blocking card but is wrong for a banner: a FAILED domain is not "still
  // being analysed", it is finished and broken, and saying otherwise would
  // leave someone waiting for a run that will never complete. Each branch now
  // asks whether something is genuinely in flight.
  const shouldShowProcessingState = () => {
    if (!selectedDomain) return false;
    if (selectedDomain.processing_status === 'FAIL') return false;

    const currentPath = location.pathname;

    if (competitorPages.some(page => currentPath.startsWith(page))) {
      return isCompetitorProcessing(selectedDomain) || isDomainProcessing(selectedDomain);
    }

    if (misinformationPages.some(page => currentPath.startsWith(page))) {
      return isMisinformationProcessing(selectedDomain) || isDomainProcessing(selectedDomain);
    }

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
          {/* The processing state is a banner above the page, not a substitute
              for it. Analysis lands progressively, so replacing the content
              hid data that had already arrived — and made the domain feel
              broken rather than busy. */}
          {shouldShowProcessingState() && selectedDomain && (
            <ProcessingBanner domain={selectedDomain} />
          )}
          <Outlet />
        </Suspense>
      </main>

      {/* The floating "New Chat" shortcut was removed: it sat fixed at
          bottom-right on every page at z-50, overlapping table rows, pagination
          and dialog corners. Chat is still reachable from the sidebar. */}
    </div>
  );
};
