import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useToast } from "@/hooks/use-toast";
import { AlertCircle, CheckCircle, Eye, EyeOff, Building2 } from "lucide-react";
import { apiClient } from "@/services/api";
import { useAuth } from "@/contexts/AuthContext";

interface InvitationDetails {
  id: string;
  email: string;
  organisation_name: string;
  invited_by_name: string;
  role: string;
  message: string;
  expires_at: string;
  can_be_accepted: boolean;
}

export default function AcceptInvitation() {
  const navigate = useNavigate();
  const { invitationId } = useParams<{ invitationId: string }>();
  const { toast } = useToast();
  const { isAuthenticated, user } = useAuth();
  
  const [invitation, setInvitation] = useState<InvitationDetails | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAccepting, setIsAccepting] = useState(false);
  const [isAccepted, setIsAccepted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  
  const [formData, setFormData] = useState({
    first_name: "",
    last_name: "",
    password: "",
  });

  useEffect(() => {
    const loadInvitation = async () => {
      if (!invitationId) {
        setError("Invalid invitation link");
        setIsLoading(false);
        return;
      }

      try {
        const invitationData = await apiClient.getInvitationDetails(invitationId);
        setInvitation(invitationData);
        
        if (!invitationData.can_be_accepted) {
          setError("This invitation has expired or is no longer valid");
        }
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : "Failed to load invitation";
        setError(errorMessage);
      } finally {
        setIsLoading(false);
      }
    };

    loadInvitation();
  }, [invitationId]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }));
    if (error) setError(null);
  };

  const handleAccept = async () => {
    if (!invitation || !invitationId) return;

    setError(null);

    if (!formData.first_name || !formData.last_name || !formData.password) {
      setError("Please fill in all fields");
      return;
    }

    if (formData.password.length < 8) {
      setError("Password must be at least 8 characters long");
      return;
    }

    setIsAccepting(true);
    try {
      await apiClient.acceptInvitation(invitationId, formData);
      setIsAccepted(true);
      toast({
        title: "Invitation Accepted",
        description: "Your account has been created successfully. You can now sign in.",
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to accept invitation";
      setError(errorMessage);
      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setIsAccepting(false);
    }
  };

  const handleDecline = () => {
    navigate("/signin");
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background to-muted p-4">
        <Card className="w-full max-w-md border border-border">
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent"></div>
              <p className="text-muted-foreground">Loading invitation...</p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error && !invitation) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background to-muted p-4">
        <Card className="w-full max-w-md border border-border">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10">
              <AlertCircle className="h-6 w-6 text-destructive" />
            </div>
            <CardTitle className="text-2xl font-bold">Invalid Invitation</CardTitle>
            <CardDescription>
              This invitation link is invalid or has expired.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
            <Button 
              onClick={() => navigate("/signin")}
              className="w-full"
            >
              Go to Sign In
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (isAccepted) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background to-muted p-4">
        <Card className="w-full max-w-md border border-border">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-green-100">
              <CheckCircle className="h-6 w-6 text-green-600" />
            </div>
            <CardTitle className="text-2xl font-bold">Welcome to the Team!</CardTitle>
            <CardDescription>
              Your account has been created successfully.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Alert>
              <CheckCircle className="h-4 w-4" />
              <AlertDescription>
                You can now sign in with your credentials to access the platform.
              </AlertDescription>
            </Alert>
            <Button 
              onClick={() => navigate("/signin")}
              className="w-full"
            >
              Continue to Sign In
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!invitation) return null;

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background to-muted p-4">
      <Card className="w-full max-w-md border border-border">
        <CardHeader className="text-center">
          {/* Logo */}
          <div className="mx-auto mb-4">
            <img
              src="/logo.png"
              alt="PromptMaxx"
              className="h-12 w-auto"
            />
          </div>

          {/* Invitation Text */}
          <CardTitle className="text-xl font-semibold">
            <span className="text-blue-600 font-bold">{invitation.invited_by_name}</span> invited you to collaborate
          </CardTitle>
          <CardDescription className="mt-2">
            Join <strong>{invitation.organisation_name}</strong> as a <strong>{invitation.role}</strong>
          </CardDescription>
        </CardHeader>
        
        <CardContent className="space-y-4">
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {invitation.message && (
            <Alert>
              <Building2 className="h-4 w-4" />
              <AlertDescription>{invitation.message}</AlertDescription>
            </Alert>
          )}

          <form className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="first_name">First Name</Label>
                <Input
                  id="first_name"
                  name="first_name"
                  placeholder="Enter first name"
                  value={formData.first_name}
                  onChange={handleInputChange}
                  required
                  disabled={isAccepting}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="last_name">Last Name</Label>
                <Input
                  id="last_name"
                  name="last_name"
                  placeholder="Enter last name"
                  value={formData.last_name}
                  onChange={handleInputChange}
                  required
                  disabled={isAccepting}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Input
                  id="password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="Create a password"
                  value={formData.password}
                  onChange={handleInputChange}
                  required
                  disabled={isAccepting}
                  minLength={8}
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3">
              <Button 
                onClick={handleAccept}
                disabled={isAccepting || !invitation.can_be_accepted}
                className="flex-1 bg-green-600 hover:bg-green-700"
              >
                {isAccepting ? "Accepting..." : "Accept Invitation"}
              </Button>
              <Button 
                variant="outline" 
                onClick={handleDecline}
                disabled={isAccepting}
                className="flex-1"
              >
                Decline
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
