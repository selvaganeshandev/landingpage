interface PageLoaderProps {
  sidebarOpen?: boolean;
}

export const PageLoader = ({ sidebarOpen = true }: PageLoaderProps) => {
  return (
    <div
      className="fixed top-0 bottom-0 right-0 z-50 flex items-center justify-center bg-background"
      style={{ left: sidebarOpen ? '256px' : '64px' }}
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
};
