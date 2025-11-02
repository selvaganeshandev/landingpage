import { Button } from "@/components/ui/button";
import { Sparkles } from "lucide-react";
import { useNavigate } from "react-router-dom";

export const FloatingAICopilot = () => {
  const navigate = useNavigate();

  return (
    <Button
      onClick={() => navigate('/copilot')}
      className="fixed bottom-6 right-6 rounded-full shadow-2xl gradient-primary hover:opacity-90 transition-all duration-300 z-50"
      size="icon"
      style={{ width: '56px', height: '56px', padding: 0 }}
    >
      <Sparkles style={{ width: '28px', height: '28px' }} className="text-white" strokeWidth={2} />
    </Button>
  );
};
