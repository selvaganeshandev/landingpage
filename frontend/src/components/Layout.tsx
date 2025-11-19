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
  const { selectedDomain } = useDomainStore();

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

  const shouldShowProcessingState =
    selectedDomain &&
    isDomainProcessing(selectedDomain) &&
    dataRequiredPages.some(page => location.pathname.startsWith(page));

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
      {isLoading && <PageLoader sidebarOpen={sidebarOpen} />}
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
