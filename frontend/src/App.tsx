import { Suspense, lazy } from "react";
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, ProtectedRoute } from "@/contexts/AuthContext";
import { SidebarProvider } from "@/contexts/SidebarContext";
import { Layout } from "./components/Layout";
import { RouteFallback } from "./components/RouteFallback";
const Chat = lazy(() => import("./pages/Chat").then((m) => ({ default: m.Chat })));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Prompts = lazy(() => import("./pages/Prompts"));
const PromptDetail = lazy(() => import("./pages/PromptDetail"));
const Mentions = lazy(() => import("./pages/Mentions"));
const Runs = lazy(() => import("./pages/Runs"));
const MentionDetail = lazy(() => import("./pages/MentionDetail"));
const Sentiment = lazy(() => import("./pages/Sentiment"));
const ShareOfVoice = lazy(() => import("./pages/ShareOfVoice"));
const ContentGaps = lazy(() => import("./pages/ContentGaps"));
const HistoricalTrends = lazy(() => import("./pages/HistoricalTrends"));
const Topics = lazy(() => import("./pages/Topics"));
const Alerts = lazy(() => import("./pages/Alerts"));
const AuditEngine = lazy(() => import("./pages/AuditEngine"));
const AuditDetail = lazy(() => import("./pages/AuditDetail"));
const PublicAudit = lazy(() => import("./pages/PublicAudit"));
const Competitors = lazy(() => import("./pages/Competitors"));
const CompetitorDetail = lazy(() => import("./pages/CompetitorDetail"));
const Reports = lazy(() => import("./pages/Reports"));
const ReportBuilder = lazy(() => import("./pages/ReportBuilder"));
const Multilingual = lazy(() => import("./pages/Multilingual"));
// import PromptInsights from "./pages/PromptInsights";
// import AgentAnalytics from "./pages/AgentAnalytics";
// import AICrawler from "./pages/AICrawler";
const AICopilot = lazy(() => import("./pages/AICopilot"));
const ContentCalendar = lazy(() => import("./pages/ContentCalendar"));
const ContentEditor = lazy(() => import("./pages/ContentEditor"));
const BulkContentUpload = lazy(() => import("./pages/BulkContentUpload"));
const AutomationSettings = lazy(() => import("./pages/AutomationSettings"));
const TrafficAttribution = lazy(() => import("./pages/TrafficAttribution"));
const SeoRankings = lazy(() => import("./pages/SeoRankings"));
const SeoKeywordDetail = lazy(() => import("./pages/SeoKeywordDetail"));
const SeoOpportunities = lazy(() => import("./pages/SeoOpportunities"));
const SeoOpportunityDetail = lazy(() => import("./pages/SeoOpportunityDetail"));
const SeoShareOfVoice = lazy(() => import("./pages/SeoShareOfVoice"));
const SeoBacklinks = lazy(() => import("./pages/SeoBacklinks"));
const SeoCompetitors = lazy(() => import("./pages/SeoCompetitors"));
const SeoContentGaps = lazy(() => import("./pages/SeoContentGaps"));
const SeoContentGapDetail = lazy(() => import("./pages/SeoContentGapDetail"));
const SeoReports = lazy(() => import("./pages/SeoReports"));
const ConfigureSeoReport = lazy(() => import("./pages/ConfigureSeoReport"));
const AddSeoKeyword = lazy(() => import("./pages/AddSeoKeyword"));
const SignIn = lazy(() => import("./pages/Auth"));
const ForgotPassword = lazy(() => import("./pages/ForgotPassword"));
const ResetPassword = lazy(() => import("./pages/ResetPassword"));
const AcceptInvitation = lazy(() => import("./pages/AcceptInvitation"));
const OrganizationSettings = lazy(() => import("./pages/OrganizationSettings"));
const TeamMemberPermissions = lazy(() => import("./pages/TeamMemberPermissions"));
const Clients = lazy(() => import("./pages/Clients"));
const Billing = lazy(() => import("./pages/Billing"));
const DomainSettings = lazy(() => import("./pages/DomainSettings"));
const MisinformationAlerts = lazy(() => import("./pages/MisinformationAlerts"));
const Citations = lazy(() => import("./pages/Citations"));
const Sources = lazy(() => import("./pages/Sources"));
const PlaceholderPage = lazy(() => import("./pages/PlaceholderPage"));
const NotFound = lazy(() => import("./pages/NotFound"));
const Profile = lazy(() => import("./pages/Profile"));
const SessionExpired = lazy(() => import("./pages/SessionExpired"));
import { MODULES } from "@/types/auth";

// Cached by default. With no options at all every query carried staleTime: 0,
// so any page using React Query refetched on every mount — leave a page, come
// back, and you get the full-page loader again as if the app had reloaded.
// A minute of freshness makes returning to a page instant while still picking
// up changes on any real navigation, and refetchOnWindowFocus stays off so
// alt-tabbing does not fire a burst of requests.
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      gcTime: 5 * 60_000,
      refetchOnWindowFocus: false,
    },
  },
});

/* RouteFallback moved to components/RouteFallback so Layout can mount its own
 * Suspense boundary around the content area. This outer boundary now only
 * catches the routes that render outside the app shell (sign-in and friends):
 * inside the shell, Layout's boundary is the nearer one and wins, which is what
 * keeps the sidebar on screen while a page chunk downloads. */

const App = () => (
  <QueryClientProvider client={queryClient}>
    <AuthProvider>
      <SidebarProvider>
        <TooltipProvider>
          <Toaster />
          <Sonner />
          <BrowserRouter>
          <Suspense fallback={<RouteFallback />}>
          <Routes>
            <Route path="/signin" element={<SignIn />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password/:tokenId" element={<ResetPassword />} />
            <Route path="/accept-invitation/:invitationId" element={<AcceptInvitation />} />
            <Route path="/session-expired" element={<SessionExpired />} />
            {/* Public audit report — outside the app shell and unauthenticated by
                design: it is opened from the landing page and from shared links. */}
            <Route path="/audit/:token" element={<PublicAudit />} />
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
              <Route path="/audits" element={
                <ProtectedRoute requiredPermission={MODULES.AUDIT_ENGINE}>
                  <AuditEngine />
                </ProtectedRoute>
              } />
              <Route path="/audits/:id" element={
                <ProtectedRoute requiredPermission={MODULES.AUDIT_ENGINE}>
                  <AuditDetail />
                </ProtectedRoute>
              } />
              <Route path="/insights" element={
                <ProtectedRoute requiredPermission={MODULES.DASHBOARD}>
                  <Dashboard />
                </ProtectedRoute>
              } />
              {/* Schedules sits under Overview beside the Dashboard, and rides
                  the same DASHBOARD permission: it is a read-only view of when
                  analysis runs, so anyone who can see the dashboard can see it. */}
              
              {/* Tracking */}
              <Route path="/runs" element={
                <ProtectedRoute requiredPermission={MODULES.PROMPTS}>
                  <Runs />
                </ProtectedRoute>
              } />
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
              {/* Billing — super admin only, gated here as well as in the
                  navigation so it is unreachable by URL for anyone else. */}
              <Route path="/billing" element={
                <ProtectedRoute requiredRoles={['super_admin']}>
                  <Billing />
                </ProtectedRoute>
              } />
              <Route path="/clients" element={
                <ProtectedRoute requiredPermission={MODULES.ORGANIZATION_SETTINGS} requiredLevel="read">
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
              <Route path="/seo-opportunities" element={
                <ProtectedRoute requiredPermission={MODULES.KEYWORD_RANKINGS}>
                  <SeoOpportunities />
                </ProtectedRoute>
              } />
              <Route path="/seo-opportunities/:id" element={
                <ProtectedRoute requiredPermission={MODULES.KEYWORD_RANKINGS}>
                  <SeoOpportunityDetail />
                </ProtectedRoute>
              } />
              <Route path="/seo-backlinks" element={
                <ProtectedRoute requiredPermission={MODULES.BACKLINKS}>
                  <SeoBacklinks />
                </ProtectedRoute>
              } />
              <Route path="/seo-share-of-voice" element={
                <ProtectedRoute requiredPermission={MODULES.SEO_COMPETITORS}>
                  <SeoShareOfVoice />
                </ProtectedRoute>
              } />
              <Route path="/seo-competitors" element={
                <ProtectedRoute requiredPermission={MODULES.SEO_COMPETITORS}>
                  <SeoCompetitors />
                </ProtectedRoute>
              } />
              <Route path="/seo-content-gaps" element={
                <ProtectedRoute requiredPermission={MODULES.KEYWORD_RANKINGS}>
                  <SeoContentGaps />
                </ProtectedRoute>
              } />
              <Route path="/seo-content-gaps/:id" element={
                <ProtectedRoute requiredPermission={MODULES.KEYWORD_RANKINGS}>
                  <SeoContentGapDetail />
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
          </Suspense>
        </BrowserRouter>
        </TooltipProvider>
      </SidebarProvider>
    </AuthProvider>
  </QueryClientProvider>
);

export default App;
