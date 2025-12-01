import { useState, useEffect } from "react";
import { Sidebar } from "./Sidebar";
import { PageLoader } from "./PageLoader";
import { ProcessingStateCard } from "./ProcessingStateCard";
import { Outlet, useLocation } from "react-router-dom";
import { useSidebar } from "@/contexts/SidebarContext";
import { useDomainStore } from "@/stores/domainStore";
import { isDomainProcessing, isCompetitorProcessing, isMisinformationProcessing } from "@/utils/processingStatus";

export const Layout = () => {
  const [isLoading, setIsLoading] = useState(false);
  const location = useLocation();
  const { isOpen: sidebarOpen } = useSidebar();
  const { selectedDomain, isDomainSwitching } = useDomainStore();

  // Pages that require completed prompt processing
  const promptDataPages = [
    '/insights',
    '/mentions',
    '/prompts',
    '/sentiment',
    '/topics',
    '/share-of-voice',
    '/trends',
    '/alerts',
    '/content-gaps',
    '/reports',
    '/traffic',
    '/multilingual',
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

  useEffect(() => {
    // Show loader when route changes
    setIsLoading(true);

    // Hide loader after a brief delay to allow page to render
    const timer = setTimeout(() => {
      setIsLoading(false);
    }, 300);

    return () => clearTimeout(timer);
  }, [location.pathname]);

  return (
    <div className="flex min-h-screen gradient-subtle">
      {(isLoading || shouldShowDomainSwitchingLoader) && <PageLoader sidebarOpen={sidebarOpen} />}
      <Sidebar />
      <main className="flex-1 overflow-auto">
        {shouldShowProcessingState() ? (
          <ProcessingStateCard domain={selectedDomain!} />
        ) : (
          <Outlet />
        )}
      </main>
    </div>
  );
};
