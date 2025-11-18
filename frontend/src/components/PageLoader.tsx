import { memo } from "react";
import { useSidebar } from "@/contexts/SidebarContext";

interface PageLoaderProps {
  sidebarOpen?: boolean;
}

export const PageLoader = memo(({ sidebarOpen }: PageLoaderProps) => {
  // Use SidebarContext to get real-time sidebar state if not provided as prop
  const { isOpen } = useSidebar();
  const isSidebarOpen = sidebarOpen !== undefined ? sidebarOpen : isOpen;

  return (
    <div
      className="fixed top-0 bottom-0 right-0 z-50 flex items-center justify-center bg-background transition-all duration-150"
      style={{ left: isSidebarOpen ? '256px' : '64px' }}
    >
      <div className="flex flex-col items-center gap-4">
        <div className="relative w-16 h-16">
          {/* Outer ring */}
          <div className="absolute inset-0 rounded-full border-4 border-primary/20"></div>
          {/* Spinning ring */}
          <div className="absolute inset-0 rounded-full border-4 border-transparent border-t-primary animate-spin"></div>
        </div>
        <p className="text-sm text-muted-foreground font-medium">Loading...</p>
      </div>
    </div>
  );
});
