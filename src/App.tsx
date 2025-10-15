import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Layout } from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Prompts from "./pages/Prompts";
import Mentions from "./pages/Mentions";
import Sentiment from "./pages/Sentiment";
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
            <Route path="/mentions" element={<Mentions />} />
            <Route path="/sentiment" element={<Sentiment />} />
            <Route 
              path="/share-of-voice" 
              element={
                <PlaceholderPage 
                  title="Share of Voice" 
                  description="Competitive benchmarking and market position analysis"
                  features={[
                    "Real-time share of voice tracking across platforms",
                    "Competitive positioning insights",
                    "Market opportunity identification",
                    "Brand dominance scoring"
                  ]}
                />
              } 
            />
            <Route 
              path="/content-gaps" 
              element={
                <PlaceholderPage 
                  title="Content Gap Detection" 
                  description="Discover untapped opportunities and content recommendations"
                  features={[
                    "AI-powered content gap identification",
                    "Question mining from AI platforms",
                    "Content optimization recommendations",
                    "Priority scoring for content creation"
                  ]}
                />
              } 
            />
            <Route 
              path="/traffic" 
              element={
                <PlaceholderPage 
                  title="Traffic Attribution" 
                  description="Track conversions from AI-powered searches"
                  features={[
                    "GA4 integration for traffic tracking",
                    "Attribution modeling for AI sources",
                    "Conversion funnel analysis",
                    "ROI calculation from AI visibility"
                  ]}
                />
              } 
            />
            <Route 
              path="/trends" 
              element={
                <PlaceholderPage 
                  title="Historical Trends" 
                  description="Long-term performance tracking and forecasting"
                  features={[
                    "Time-series analysis of visibility metrics",
                    "Predictive trend forecasting",
                    "Seasonal pattern identification",
                    "Performance milestone tracking"
                  ]}
                />
              } 
            />
            <Route 
              path="/crawler" 
              element={
                <PlaceholderPage 
                  title="AI Crawler Analysis" 
                  description="Technical SEO for AI discoverability"
                  features={[
                    "AI crawler log analysis",
                    "Technical SEO audit for AI platforms",
                    "Indexability recommendations",
                    "Structured data optimization"
                  ]}
                />
              } 
            />
            <Route 
              path="/topics" 
              element={
                <PlaceholderPage 
                  title="Topic-Based Tracking" 
                  description="Monitor performance across key topics and categories"
                  features={[
                    "Topic clustering and categorization",
                    "AI-generated prompt suggestions",
                    "Topic performance benchmarking",
                    "Content strategy recommendations"
                  ]}
                />
              } 
            />
            <Route 
              path="/multilingual" 
              element={
                <PlaceholderPage 
                  title="Multilingual Monitoring" 
                  description="Global brand tracking across languages"
                  features={[
                    "Multi-language prompt tracking",
                    "Regional visibility analysis",
                    "Cross-cultural sentiment analysis",
                    "International SEO recommendations"
                  ]}
                />
              } 
            />
            <Route 
              path="/alerts" 
              element={
                <PlaceholderPage 
                  title="Real-Time Alerts" 
                  description="Stay informed with instant notifications"
                  features={[
                    "Custom alert rules and thresholds",
                    "Multi-channel notifications (email, Slack, SMS)",
                    "Anomaly detection for visibility changes",
                    "Competitive movement alerts"
                  ]}
                />
              } 
            />
            <Route 
              path="/competitors" 
              element={
                <PlaceholderPage 
                  title="Competitor Tracking" 
                  description="Monitor and analyze competitor performance"
                  features={[
                    "Competitor mention tracking",
                    "Comparative performance dashboards",
                    "Competitive strategy insights",
                    "Market positioning analysis"
                  ]}
                />
              } 
            />
            <Route 
              path="/reports" 
              element={
                <PlaceholderPage 
                  title="Custom Reporting" 
                  description="Generate and automate branded reports"
                  features={[
                    "Customizable report templates",
                    "Automated report scheduling",
                    "White-label reporting options",
                    "API access for integrations"
                  ]}
                />
              } 
            />
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
