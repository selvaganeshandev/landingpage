import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Avatar } from "@/components/ui/avatar";
import { Sparkles, Send, TrendingUp, AlertCircle, Lightbulb } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  suggestions?: string[];
}

const AICopilot = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      role: "assistant",
      content: "Hello! I'm your AI Copilot. I analyze your brand's performance across AI platforms and provide strategic recommendations. How can I help you today?",
      timestamp: new Date(Date.now() - 3600000),
      suggestions: [
        "Analyze my current visibility trends",
        "Suggest content improvements",
        "Compare with competitors"
      ]
    },
    {
      id: "2",
      role: "user",
      content: "What's my current brand performance?",
      timestamp: new Date(Date.now() - 3500000),
    },
    {
      id: "3",
      role: "assistant",
      content: "Based on my analysis of your recent data:\n\n📊 **Visibility Score: 78/100** (+5% vs last week)\n- Total Mentions: 247 across 8 AI platforms\n- Average Position: 1.8 (improved from 2.1)\n- Sentiment: 72% Positive, 23% Neutral, 5% Negative\n\n🎯 **Top Performing Topics:**\n1. Product features (89 mentions)\n2. Customer support (54 mentions)\n3. Pricing (38 mentions)\n\n⚠️ **Areas Needing Attention:**\n- Competitor XYZ is gaining ground in 'enterprise solutions' queries\n- Misinformation detected in 3 responses (already flagged)\n- Response quality dropped 12% on ChatGPT this week",
      timestamp: new Date(Date.now() - 3400000),
      suggestions: [
        "Show competitor comparison",
        "View misinformation details",
        "Suggest optimization strategies"
      ]
    }
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSend = () => {
    if (!input.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    // Simulate AI response
    setTimeout(() => {
      const responses = [
        "Let me analyze that for you...\n\nBased on the current data, I recommend focusing on content optimization for 'enterprise solutions' queries. Your competitors are ranking 2.3 positions higher on average.",
        "I've identified 3 key opportunities:\n\n1. **Content Gap**: You're not appearing in AI responses for 'integration capabilities'\n2. **Sentiment Improvement**: Customer support mentions need attention\n3. **New Platform**: Consider optimizing for Perplexity AI (42% CTR)",
        "Here's what I found:\n\n✅ Your visibility has improved 15% month-over-month\n⚠️ However, competitor mentions increased 28% in the same period\n💡 Recommendation: Update your knowledge base with recent case studies"
      ];

      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: responses[Math.floor(Math.random() * responses.length)],
        timestamp: new Date(),
        suggestions: [
          "Show detailed metrics",
          "Generate action plan",
          "Export this analysis"
        ]
      };

      setMessages(prev => [...prev, aiMessage]);
      setIsLoading(false);
    }, 1500);
  };

  const handleSuggestionClick = (suggestion: string) => {
    setInput(suggestion);
  };

  return (
    <div className="p-8 h-[calc(100vh-4rem)] flex flex-col">
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-12 h-12 rounded-2xl gradient-primary flex items-center justify-center shadow-glow">
            <Sparkles className="h-6 w-6 text-white" />
          </div>
          <div>
            <h1 className="text-4xl font-bold tracking-tight">AI Copilot</h1>
            <p className="text-muted-foreground">Your strategic AI assistant for brand optimization</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 flex-1 min-h-0">
        {/* Insights Panel */}
        <Card className="p-6 lg:col-span-1 overflow-hidden flex flex-col">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Lightbulb className="h-5 w-5 text-primary" />
            Quick Insights
          </h2>
          <ScrollArea className="flex-1">
            <div className="space-y-4">
              <div className="p-4 rounded-lg bg-success/10 border border-success/20">
                <div className="flex items-start gap-3">
                  <TrendingUp className="h-5 w-5 text-success mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-success mb-1">Strong Growth</p>
                    <p className="text-xs text-muted-foreground">Visibility up 15% this month</p>
                  </div>
                </div>
              </div>

              <div className="p-4 rounded-lg bg-destructive/10 border border-destructive/20">
                <div className="flex items-start gap-3">
                  <AlertCircle className="h-5 w-5 text-destructive mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-destructive mb-1">Competitor Alert</p>
                    <p className="text-xs text-muted-foreground">XYZ Corp gaining in 3 categories</p>
                  </div>
                </div>
              </div>

              <div className="p-4 rounded-lg bg-primary/10 border border-primary/20">
                <div className="flex items-start gap-3">
                  <Sparkles className="h-5 w-5 text-primary mt-0.5" />
                  <div>
                    <p className="text-sm font-medium mb-1">New Opportunity</p>
                    <p className="text-xs text-muted-foreground">Perplexity AI showing high CTR</p>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Top Topics</p>
                <div className="flex flex-wrap gap-2">
                  <Badge variant="secondary">Product Features</Badge>
                  <Badge variant="secondary">Support</Badge>
                  <Badge variant="secondary">Pricing</Badge>
                  <Badge variant="secondary">Integration</Badge>
                </div>
              </div>
            </div>
          </ScrollArea>
        </Card>

        {/* Chat Area */}
        <Card className="lg:col-span-3 flex flex-col overflow-hidden">
          <ScrollArea className="flex-1 p-6">
            <div className="space-y-6">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex gap-4 ${message.role === "user" ? "flex-row-reverse" : ""}`}
                >
                  <Avatar className={`w-10 h-10 ${message.role === "assistant" ? "gradient-primary" : "bg-muted"}`}>
                    {message.role === "assistant" ? (
                      <Sparkles className="h-5 w-5 text-white" />
                    ) : (
                      <div className="text-sm font-semibold">You</div>
                    )}
                  </Avatar>
                  <div className={`flex-1 space-y-3 ${message.role === "user" ? "flex flex-col items-end" : ""}`}>
                    <div
                      className={`rounded-2xl p-4 max-w-2xl ${
                        message.role === "user"
                          ? "bg-primary text-primary-foreground ml-auto"
                          : "bg-muted"
                      }`}
                    >
                      <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                    </div>
                    {message.suggestions && message.suggestions.length > 0 && (
                      <div className="flex flex-wrap gap-2">
                        {message.suggestions.map((suggestion, idx) => (
                          <Button
                            key={idx}
                            variant="outline"
                            size="sm"
                            onClick={() => handleSuggestionClick(suggestion)}
                            className="text-xs"
                          >
                            {suggestion}
                          </Button>
                        ))}
                      </div>
                    )}
                    <p className="text-xs text-muted-foreground">
                      {message.timestamp.toLocaleTimeString()}
                    </p>
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="flex gap-4">
                  <Avatar className="w-10 h-10 gradient-primary">
                    <Sparkles className="h-5 w-5 text-white" />
                  </Avatar>
                  <div className="flex-1">
                    <div className="rounded-2xl p-4 bg-muted max-w-2xl">
                      <div className="flex gap-1">
                        <div className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: "0ms" }} />
                        <div className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: "150ms" }} />
                        <div className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: "300ms" }} />
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </ScrollArea>

          <div className="p-6 border-t border-border">
            <div className="flex gap-3">
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={(e) => e.key === "Enter" && handleSend()}
                placeholder="Ask about your brand performance, get recommendations..."
                className="flex-1"
                disabled={isLoading}
              />
              <Button onClick={handleSend} disabled={isLoading || !input.trim()}>
                <Send className="h-4 w-4" />
              </Button>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              💡 Try: "Analyze my visibility trends" or "Compare with competitors"
            </p>
          </div>
        </Card>
      </div>
    </div>
  );
};

export default AICopilot;
