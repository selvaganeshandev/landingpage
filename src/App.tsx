import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Layout } from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Prompts from "./pages/Prompts";
import PromptDetail from "./pages/PromptDetail";
import Mentions from "./pages/Mentions";
import MentionDetail from "./pages/MentionDetail";
import Sentiment from "./pages/Sentiment";
import ShareOfVoice from "./pages/ShareOfVoice";
import ContentGaps from "./pages/ContentGaps";
import HistoricalTrends from "./pages/HistoricalTrends";
import Topics from "./pages/Topics";
import Alerts from "./pages/Alerts";
import Competitors from "./pages/Competitors";
import CompetitorDetail from "./pages/CompetitorDetail";
import Reports from "./pages/Reports";
import Multilingual from "./pages/Multilingual";
import PlaceholderPage from "./pages/PlaceholderPage";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/prompts" element={<Prompts />} />
            <Route path="/prompts/:id" element={<PromptDetail />} />
            <Route path="/mentions" element={<Mentions />} />
            <Route path="/mentions/:id" element={<MentionDetail />} />
            <Route path="/sentiment" element={<Sentiment />} />
            <Route path="/share-of-voice" element={<ShareOfVoice />} />
            <Route path="/content-gaps" element={<ContentGaps />} />
            <Route path="/trends" element={<HistoricalTrends />} />
            <Route path="/topics" element={<Topics />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/competitors" element={<Competitors />} />
            <Route path="/competitors/:id" element={<CompetitorDetail />} />
            <Route path="/multilingual" element={<Multilingual />} />
            <Route path="/reports" element={<Reports />} />
            <Route 
              path="/copilot" 
              element={
                <PlaceholderPage 
                  title="AI Copilot" 
                  description="Strategic recommendations powered by AI"
                  features={[
                    "AI-powered strategic recommendations",
                    "Optimization opportunity identification",
                    "Content strategy suggestions",
                    "Competitive positioning advice"
                  ]}
                />
              } 
            />
            <Route 
              path="/prompt-insights" 
              element={
                <PlaceholderPage 
                  title="Prompt Volume Insights" 
                  description="Understand trending queries and search volumes"
                  features={[
                    "Prompt volume trends and forecasting",
                    "Emerging query identification",
                    "Search intent analysis",
                    "Demand opportunity scoring"
                  ]}
                />
              } 
            />
            <Route 
              path="/misinformation" 
              element={
                <PlaceholderPage 
                  title="Misinformation Alerts" 
                  description="Detect and flag AI hallucinations about your brand"
                  features={[
                    "Automated hallucination detection",
                    "Brand misinformation alerts",
                    "Fact-checking assistance",
                    "Correction tracking and verification"
                  ]}
                />
              } 
            />
            <Route 
              path="/agent-analytics" 
              element={
                <PlaceholderPage 
                  title="Agent Analytics" 
                  description="Deep intelligence on AI model behavior and source preferences"
                  features={[
                    "Model-specific performance tracking",
                    "Source citation analysis",
                    "Agent behavior patterns",
                    "Referral pathway optimization"
                  ]}
                />
              } 
            />
            <Route 
              path="/settings" 
              element={
                <PlaceholderPage 
                  title="Settings" 
                  description="Configure your tracking and preferences"
                />
              } 
            />
            {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
