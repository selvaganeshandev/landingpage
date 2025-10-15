import { useNavigate } from "react-router-dom";
import { useToast } from "@/hooks/use-toast";

export interface ContentGenerationParams {
  keywords?: string[];
  topic?: string;
  source?: string;
  priority?: "high" | "medium" | "low";
  articleType?: string;
}

export const useContentGeneration = () => {
  const navigate = useNavigate();
  const { toast } = useToast();

  const navigateToContentGeneration = (params?: ContentGenerationParams) => {
    // Store params in sessionStorage to pass to content generation
    if (params) {
      sessionStorage.setItem('contentGenerationParams', JSON.stringify(params));
    }
    
    toast({
      title: "Opening Content Generator",
      description: params?.topic 
        ? `Creating content for: ${params.topic}`
        : "Starting content generation workflow",
    });
    
    navigate('/content-calendar');
    
    // Trigger opening the generate dialog after navigation
    setTimeout(() => {
      window.dispatchEvent(new CustomEvent('openContentGeneration', { detail: params }));
    }, 100);
  };

  return { navigateToContentGeneration };
};
