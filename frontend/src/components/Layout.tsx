import { useState, useEffect } from "react";
import { Sidebar } from "./Sidebar";
import { PageLoader } from "./PageLoader";
import { ProcessingStateCard } from "./ProcessingStateCard";
import { Outlet, useLocation } from "react-router-dom";
import { useSidebar } from "@/contexts/SidebarContext";
import { useDomainStore } from "@/stores/domainStore";
import { isDomainProcessing } from "@/utils/processingStatus";

export const Layout = () => {
  const [isLoading, setIsLoading] = useState(false);
  const location = useLocation();
  const { isOpen: sidebarOpen } = useSidebar();
  const { selectedDomain, isDomainSwitching } = useDomainStore();

  // List of pages that should show processing state when domain is processing
  const dataRequiredPages = [
    '/insights',
    '/mentions',
    '/prompts',
    '/sentiment',
    '/topics',
    '/share-of-voice',
    '/trends',
    '/alerts',
    '/competitors',
    '/content-gaps',
    '/reports',
    '/misinformation',
    '/traffic',
    '/multilingual',
  ];

  // Pages that don't require domain data (have their own loading states)
  const noDomainDataPages = [
    '/organization-settings',
    '/profile',
  ];

  const shouldShowProcessingState =
    selectedDomain &&
    isDomainProcessing(selectedDomain) &&
    dataRequiredPages.some(page => location.pathname.startsWith(page));

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
        {shouldShowProcessingState ? (
          <ProcessingStateCard domain={selectedDomain} />
        ) : (
          <Outlet />
        )}
      </main>
    </div>
  );
};
