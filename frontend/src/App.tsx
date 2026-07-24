import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, ProtectedRoute } from "@/contexts/AuthContext";
import { SidebarProvider } from "@/contexts/SidebarContext";
import { Layout } from "./components/Layout";
import { Chat } from "./pages/Chat";
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
import ReportBuilder from "./pages/ReportBuilder";
import Multilingual from "./pages/Multilingual";
// import PromptInsights from "./pages/PromptInsights";
// import AgentAnalytics from "./pages/AgentAnalytics";
// import AICrawler from "./pages/AICrawler";
import AICopilot from "./pages/AICopilot";
import ContentCalendar from "./pages/ContentCalendar";
import ContentEditor from "./pages/ContentEditor";
import BulkContentUpload from "./pages/BulkContentUpload";
import AutomationSettings from "./pages/AutomationSettings";
import TrafficAttribution from "./pages/TrafficAttribution";
import SeoRankings from "./pages/SeoRankings";
import SeoKeywordDetail from "./pages/SeoKeywordDetail";
import SeoCompetitors from "./pages/SeoCompetitors";
import SeoReports from "./pages/SeoReports";
import ConfigureSeoReport from "./pages/ConfigureSeoReport";
import AddSeoKeyword from "./pages/AddSeoKeyword";
import SignIn from "./pages/Auth";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";
import AcceptInvitation from "./pages/AcceptInvitation";
import OrganizationSettings from "./pages/OrganizationSettings";
import TeamMemberPermissions from "./pages/TeamMemberPermissions";
import Clients from "./pages/Clients";
import DomainSettings from "./pages/DomainSettings";
import MisinformationAlerts from "./pages/MisinformationAlerts";
import Citations from "./pages/Citations";
import Sources from "./pages/Sources";
import PlaceholderPage from "./pages/PlaceholderPage";
import NotFound from "./pages/NotFound";
import Profile from "./pages/Profile";
import SessionExpired from "./pages/SessionExpired";
import { MODULES } from "@/types/auth";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <AuthProvider>
      <SidebarProvider>
        <TooltipProvider>
          <Toaster />
          <Sonner />
          <BrowserRouter>
          <Routes>
            <Route path="/signin" element={<SignIn />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password/:tokenId" element={<ResetPassword />} />
            <Route path="/accept-invitation/:invitationId" element={<AcceptInvitation />} />
            <Route path="/session-expired" element={<SessionExpired />} />
            <Route element={<Layout />}>
              {/* Chat - Landing Page (accessible to all authenticated users) */}
              <Route path="/" element={
                <ProtectedRoute>
                  <Chat />
                </ProtectedRoute>
              } />
              <Route path="/chat" element={
                <ProtectedRoute>
                  <Chat />
                </ProtectedRoute>
              } />

              {/* Overview */}
              <Route path="/insights" element={
                <ProtectedRoute requiredPermission={MODULES.DASHBOARD}>
                  <Dashboard />
                </ProtectedRoute>
              } />
              
              {/* Tracking */}
              <Route path="/mentions" element={
                <ProtectedRoute requiredPermission={MODULES.MENTIONS}>
                  <Mentions />
                </ProtectedRoute>
              } />
              <Route path="/mentions/:id" element={
                <ProtectedRoute requiredPermission={MODULES.MENTIONS}>
                  <MentionDetail />
                </ProtectedRoute>
              } />
              <Route path="/prompts" element={
                <ProtectedRoute requiredPermission={MODULES.PROMPTS}>
                  <Prompts />
                </ProtectedRoute>
              } />
              <Route path="/prompts/:id" element={
                <ProtectedRoute requiredPermission={MODULES.PROMPTS}>
                  <PromptDetail />
                </ProtectedRoute>
              } />
              <Route path="/alerts" element={
                <ProtectedRoute requiredPermission={MODULES.ALERTS}>
                  <Alerts />
                </ProtectedRoute>
              } />
              <Route path="/citations" element={
                <ProtectedRoute requiredPermission={MODULES.CITATIONS}>
                  <Citations />
                </ProtectedRoute>
              } />
              <Route path="/sources" element={
                <ProtectedRoute requiredPermission={MODULES.CITATIONS}>
                  <Sources />
                </ProtectedRoute>
              } />

              {/* Analytics */}
              <Route path="/sentiment" element={
                <ProtectedRoute requiredPermission={MODULES.SENTIMENT_ANALYSIS}>
                  <Sentiment />
                </ProtectedRoute>
              } />
              <Route path="/topics" element={
                <ProtectedRoute requiredPermission={MODULES.TOPICS}>
                  <Topics />
                </ProtectedRoute>
              } />
              <Route path="/share-of-voice" element={
                <ProtectedRoute requiredPermission={MODULES.SHARE_OF_VOICE}>
                  <ShareOfVoice />
                </ProtectedRoute>
              } />
              <Route path="/trends" element={
                <ProtectedRoute requiredPermission={MODULES.HISTORICAL_TRENDS}>
                  <HistoricalTrends />
                </ProtectedRoute>
              } />
              
              {/* Strategy */}
              <Route path="/content-gaps" element={
                <ProtectedRoute requiredPermission={MODULES.CONTENT_GAPS}>
                  <ContentGaps />
                </ProtectedRoute>
              } />
              <Route path="/competitors" element={
                <ProtectedRoute requiredPermission={MODULES.COMPETITORS}>
                  <Competitors />
                </ProtectedRoute>
              } />
              <Route path="/competitors/:id" element={
                <ProtectedRoute requiredPermission={MODULES.COMPETITORS}>
                  <CompetitorDetail />
                </ProtectedRoute>
              } />
              
              {/* Advanced */}
              <Route path="/multilingual" element={
                <ProtectedRoute requiredPermission={MODULES.MULTILINGUAL}>
                  <Multilingual />
                </ProtectedRoute>
              } />
              <Route path="/copilot" element={
                <ProtectedRoute requiredPermission={MODULES.AI_COPILOT}>
                  <AICopilot />
                </ProtectedRoute>
              } />
              <Route path="/traffic" element={
                <ProtectedRoute requiredPermission={MODULES.TRAFFIC_ATTRIBUTION}>
                  <TrafficAttribution />
                </ProtectedRoute>
              } />
              <Route path="/misinformation" element={
                <ProtectedRoute requiredPermission={MODULES.MISINFORMATION_ALERTS}>
                  <MisinformationAlerts />
                </ProtectedRoute>
              } />
              
              {/* Reporting */}
              <Route path="/reports" element={
                <ProtectedRoute requiredPermission={MODULES.REPORTS}>
                  <Reports />
                </ProtectedRoute>
              } />
              <Route path="/reports/create-template" element={
                <ProtectedRoute requiredPermission={MODULES.REPORTS}>
                  <ReportBuilder />
                </ProtectedRoute>
              } />
              
              {/* Administration */}
              <Route path="/organization-settings" element={
                <ProtectedRoute requiredPermission={MODULES.ORGANIZATION_SETTINGS} requiredLevel="read">
                  <OrganizationSettings />
                </ProtectedRoute>
              } />
              <Route path="/organization-settings/members/:memberId" element={
                <ProtectedRoute requiredPermission={MODULES.TEAM_MANAGEMENT} requiredLevel="admin">
                  <TeamMemberPermissions />
                </ProtectedRoute>
              } />
              <Route path="/clients" element={
                <ProtectedRoute requiredPermission={MODULES.TEAM_MANAGEMENT} requiredLevel="admin">
                  <Clients />
                </ProtectedRoute>
              } />
              <Route path="/organization-settings/domains/:domainId" element={
                <ProtectedRoute requiredPermission={MODULES.ORGANIZATION_SETTINGS} requiredLevel="read">
                  <DomainSettings />
                </ProtectedRoute>
              } />
              
              {/* Profile */}
              <Route path="/profile" element={
                <ProtectedRoute>
                  <Profile />
                </ProtectedRoute>
              } />
              
              {/* SEO Monitoring */}
              <Route path="/seo-rankings" element={
                <ProtectedRoute requiredPermission={MODULES.KEYWORD_RANKINGS}>
                  <SeoRankings />
                </ProtectedRoute>
              } />
              <Route path="/seo-rankings/add-keyword" element={
                <ProtectedRoute requiredPermission={MODULES.KEYWORD_RANKINGS}>
                  <AddSeoKeyword />
                </ProtectedRoute>
              } />
              <Route path="/seo-rankings/:id" element={
                <ProtectedRoute requiredPermission={MODULES.KEYWORD_RANKINGS}>
                  <SeoKeywordDetail />
                </ProtectedRoute>
              } />
              <Route path="/seo-competitors" element={
                <ProtectedRoute requiredPermission={MODULES.SEO_COMPETITORS}>
                  <SeoCompetitors />
                </ProtectedRoute>
              } />
              <Route path="/seo-reports" element={
                <ProtectedRoute requiredPermission={MODULES.ORGANIC_REPORTS}>
                  <SeoReports />
                </ProtectedRoute>
              } />
              <Route path="/seo-reports/configure" element={
                <ProtectedRoute requiredPermission={MODULES.ORGANIC_REPORTS}>
                  <ConfigureSeoReport />
                </ProtectedRoute>
              } />

              {/* Other routes */}
              <Route path="/content-calendar" element={
                <ProtectedRoute requiredPermission={MODULES.CONTENT_PLANNER}>
                  <ContentCalendar />
                </ProtectedRoute>
              } />
              <Route path="/content-editor/:id" element={
                <ProtectedRoute requiredPermission={MODULES.CONTENT_PLANNER}>
                  <ContentEditor />
                </ProtectedRoute>
              } />
              <Route path="/bulk-upload" element={
                <ProtectedRoute requiredPermission={MODULES.CONTENT_PLANNER}>
                  <BulkContentUpload />
                </ProtectedRoute>
              } />
              <Route path="/automation" element={
                <ProtectedRoute requiredPermission={MODULES.DASHBOARD}>
                  <AutomationSettings />
                </ProtectedRoute>
              } />
              <Route 
                path="/settings" 
                element={
                  <PlaceholderPage 
                    title="Settings" 
                    description="Configure your tracking and preferences"
                  />
                } 
              />
              
              {/* Catch-all route */}
              <Route path="*" element={<NotFound />} />
            </Route>
          </Routes>
        </BrowserRouter>
        </TooltipProvider>
      </SidebarProvider>
    </AuthProvider>
  </QueryClientProvider>
);

export default App;
