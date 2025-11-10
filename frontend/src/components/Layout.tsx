import { useState, useEffect } from "react";
import { Sidebar } from "./Sidebar";
import { PageLoader } from "./PageLoader";
import { Outlet, useLocation } from "react-router-dom";
import { useSidebar } from "@/contexts/SidebarContext";

export const Layout = () => {
  const [isLoading, setIsLoading] = useState(false);
  const location = useLocation();
  const { isOpen: sidebarOpen } = useSidebar();

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
        <Outlet />
      </main>
    </div>
  );
};
