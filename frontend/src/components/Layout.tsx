import { useState, useEffect } from "react";
import { Sidebar } from "./Sidebar";
import { PageLoader } from "./PageLoader";
import { ProcessingStateCard } from "./ProcessingStateCard";
import { OnboardingModal } from "./OnboardingModal";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { useSidebar } from "@/contexts/SidebarContext";
import { useDomainStore } from "@/stores/domainStore";
import { useAuth } from "@/contexts/AuthContext";
import { isDomainProcessing, isCompetitorProcessing, isMisinformationProcessing } from "@/utils/processingStatus";
import { Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

export const Layout = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
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

  useEffect(() => {
    // Show loader when route changes
    setIsLoading(true);

    // Hide loader after a brief delay to allow page to render
    const timer = setTimeout(() => {
      setIsLoading(false);
    }, 300);

    return () => clearTimeout(timer);
  }, [location.pathname]);

  // Show onboarding modal if no domains
  if (showOnboarding) {
    return <OnboardingModal onComplete={handleOnboardingComplete} user={user} />;
  }

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

      {/* Floating New Chat Button */}
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              onClick={() => navigate('/chat')}
              className="fixed bottom-6 right-6 h-14 w-14 rounded-full shadow-lg hover:shadow-xl transition-shadow z-50 p-0 flex items-center justify-center"
            >
              <Sparkles style={{ width: '28px', height: '28px' }} />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="left">
            <p>New Chat</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    </div>
  );
};
