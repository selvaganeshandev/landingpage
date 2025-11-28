import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { LogIn } from "lucide-react";

const SessionExpired = () => {
  const navigate = useNavigate();

  useEffect(() => {
    // Clear any remaining auth data
    localStorage.removeItem("token");
    localStorage.removeItem("refresh_token");
  }, []);

  const handleLoginRedirect = () => {
    navigate("/signin");
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 flex items-center justify-center p-6">
      <div className="max-w-lg w-full">
        {/* Main Content */}
        <div className="text-center space-y-6">
          {/* Title with gradient */}
          <div className="space-y-2">
            <h1 className="text-3xl font-bold bg-gradient-to-r from-primary via-purple-500 to-secondary bg-clip-text text-transparent animate-fade-in">
              Session Expired
            </h1>
            <p className="text-base text-muted-foreground">
              Your session has timed out for security reasons
            </p>
          </div>

          {/* Action Button */}
          <div className="flex justify-center pt-2">
            <Button
              onClick={handleLoginRedirect}
              size="default"
              className="gradient-primary shadow-lg shadow-primary/20 hover:shadow-xl hover:shadow-primary/30 transition-all duration-300 group"
            >
              <LogIn className="h-4 w-4 mr-2 group-hover:scale-110 transition-transform" />
              Log In Again
            </Button>
          </div>
        </div>

        {/* Decorative Elements */}
        <div className="absolute top-10 left-10 w-20 h-20 rounded-full bg-primary/5 blur-3xl"></div>
        <div className="absolute bottom-10 right-10 w-32 h-32 rounded-full bg-secondary/5 blur-3xl"></div>
        <div className="absolute top-1/2 left-1/4 w-16 h-16 rounded-full bg-purple-500/5 blur-2xl"></div>
      </div>
    </div>
  );
};

export default SessionExpired;
