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
import PromptInsights from "./pages/PromptInsights";
import AgentAnalytics from "./pages/AgentAnalytics";
import AICrawler from "./pages/AICrawler";
import AICopilot from "./pages/AICopilot";
import ContentCalendar from "./pages/ContentCalendar";
import AutomationSettings from "./pages/AutomationSettings";
import TrafficAttribution from "./pages/TrafficAttribution";
import Auth from "./pages/Auth";
import OrganizationSettings from "./pages/OrganizationSettings";
import TeamMemberPermissions from "./pages/TeamMemberPermissions";
import MisinformationAlerts from "./pages/MisinformationAlerts";
import PlaceholderPage from "./pages/PlaceholderPage";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path="/auth" element={<Auth />} />
          <Route element={<Layout />}>
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
            <Route path="/prompt-insights" element={<PromptInsights />} />
            <Route path="/agent-analytics" element={<AgentAnalytics />} />
            <Route path="/crawler" element={<AICrawler />} />
            <Route path="/traffic" element={<TrafficAttribution />} />
            <Route path="/organization-settings" element={<OrganizationSettings />} />
            <Route path="/organization-settings/members/:memberId" element={<TeamMemberPermissions />} />
            <Route path="/copilot" element={<AICopilot />} />
            <Route path="/content-calendar" element={<ContentCalendar />} />
            <Route path="/automation" element={<AutomationSettings />} />
            <Route path="/misinformation" element={<MisinformationAlerts />} />
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
          </Route>
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
