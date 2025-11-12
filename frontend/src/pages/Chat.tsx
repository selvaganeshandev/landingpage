import { useState } from "react";
import { Send, Sparkles, TrendingUp, Lightbulb, Users, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useAuth } from "@/contexts/AuthContext";
import { useDomainStore } from "@/stores/domainStore";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

export const Chat = () => {
  const { user } = useAuth();
  const { selectedDomain } = useDomainStore();
  const [messages, setMessages] = useState<Array<{ role: 'user' | 'assistant'; content: string }>>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [openPopover, setOpenPopover] = useState<string | null>(null);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage = input.trim();
    setInput("");
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);

    // TODO: Integrate with your AI backend
    // For now, just a placeholder response
    setTimeout(() => {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: "I'm your AI assistant. How can I help you today?"
      }]);
      setIsLoading(false);
    }, 1000);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 18) return "Good afternoon";
    return "Good evening";
  };

  const userName = user?.first_name || user?.email?.split('@')[0] || "there";

  // Get domain favicon URL
  const getDomainFavicon = () => {
    if (selectedDomain?.url) {
      try {
        const url = new URL(selectedDomain.url.startsWith('http') ? selectedDomain.url : `https://${selectedDomain.url}`);
        return `${url.protocol}//${url.hostname}/favicon.ico`;
      } catch {
        return null;
      }
    }
    return null;
  };

  // Fallback to initials if favicon fails
  const getUserInitials = () => {
    if (user?.first_name && user?.last_name) {
      return `${user.first_name.charAt(0)}${user.last_name.charAt(0)}`.toUpperCase();
    } else if (user?.first_name) {
      return user.first_name.charAt(0).toUpperCase();
    } else if (user?.email) {
      return user.email.charAt(0).toUpperCase();
    }
    return "U";
  };

  return (
    <div className="flex flex-col h-screen bg-background animate-fade-in">
      {messages.length === 0 ? (
        /* Initial Mode - Centered input with quick actions */
        <div className="flex-1 flex flex-col justify-center items-center w-full px-4 -mt-[100px]">
          <div className="w-[60%] text-center">
            {/* Greeting - above input */}
            <div className="mb-8 flex items-center justify-center gap-3">
              <div className="flex items-center justify-center w-12 h-12 rounded-full bg-gradient-to-r from-primary to-secondary flex-shrink-0">
                <Sparkles className="h-6 w-6 text-white" />
              </div>
              <h2 className="text-4xl font-bold">
                {getGreeting()}, {userName}
              </h2>
            </div>

            {/* Input Box */}
            <div className="relative mb-4">
              <Textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask me anything..."
                className="min-h-[120px] pr-12 resize-none text-base shadow-glow"
                disabled={isLoading}
              />
              <Button
                onClick={handleSend}
                disabled={!input.trim() || isLoading}
                size="icon"
                className="absolute right-2 bottom-2 rounded-full"
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>

              {/* Quick actions - below input */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-4" style={{ animation: 'none' }}>
                <Popover open={openPopover === 'performance'} onOpenChange={(open) => setOpenPopover(open ? 'performance' : null)}>
                  <PopoverTrigger asChild>
                    <button className="p-3 rounded-lg border border-border hover:bg-accent text-left">
                      <div className="flex items-center gap-2">
                        <TrendingUp className="h-4 w-4" />
                        <div className="text-sm font-medium">Analyze Performance</div>
                      </div>
                    </button>
                  </PopoverTrigger>
                  <PopoverContent className="w-80 p-0" align="start">
                    <div className="p-2">
                      <p className="text-xs font-semibold text-muted-foreground px-3 py-2">Performance Analysis</p>
                      <button
                        onClick={() => { setInput("Analyze my domain's mention trends over the past month"); setOpenPopover(null); }}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-accent rounded-md transition-colors"
                      >
                        Analyze mention trends
                      </button>
                      <button
                        onClick={() => { setInput("Review sentiment analysis across all AI platforms"); setOpenPopover(null); }}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-accent rounded-md transition-colors"
                      >
                        Review sentiment analysis
                      </button>
                      <button
                        onClick={() => { setInput("Compare my share of voice with competitors"); setOpenPopover(null); }}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-accent rounded-md transition-colors"
                      >
                        Compare share of voice
                      </button>
                      <button
                        onClick={() => { setInput("Identify top performing prompts"); setOpenPopover(null); }}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-accent rounded-md transition-colors"
                      >
                        Identify top prompts
                      </button>
                    </div>
                  </PopoverContent>
                </Popover>

                <Popover open={openPopover === 'content'} onOpenChange={(open) => setOpenPopover(open ? 'content' : null)}>
                  <PopoverTrigger asChild>
                    <button className="p-3 rounded-lg border border-border hover:bg-accent text-left">
                      <div className="flex items-center gap-2">
                        <Lightbulb className="h-4 w-4" />
                        <div className="text-sm font-medium">Content Ideas</div>
                      </div>
                    </button>
                  </PopoverTrigger>
                  <PopoverContent className="w-80 p-0" align="start">
                    <div className="p-2">
                      <p className="text-xs font-semibold text-muted-foreground px-3 py-2">Content Strategy</p>
                      <button
                        onClick={() => { setInput("Suggest content topics based on content gaps"); setOpenPopover(null); }}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-accent rounded-md transition-colors"
                      >
                        Suggest content topics
                      </button>
                      <button
                        onClick={() => { setInput("Generate blog article ideas to improve visibility"); setOpenPopover(null); }}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-accent rounded-md transition-colors"
                      >
                        Generate blog ideas
                      </button>
                      <button
                        onClick={() => { setInput("Create content calendar based on trending topics"); setOpenPopover(null); }}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-accent rounded-md transition-colors"
                      >
                        Create content calendar
                      </button>
                      <button
                        onClick={() => { setInput("Develop content templates for my domain"); setOpenPopover(null); }}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-accent rounded-md transition-colors"
                      >
                        Develop templates
                      </button>
                    </div>
                  </PopoverContent>
                </Popover>

                <Popover open={openPopover === 'competitors'} onOpenChange={(open) => setOpenPopover(open ? 'competitors' : null)}>
                  <PopoverTrigger asChild>
                    <button className="p-3 rounded-lg border border-border hover:bg-accent text-left">
                      <div className="flex items-center gap-2">
                        <Users className="h-4 w-4" />
                        <div className="text-sm font-medium">Competitor Analysis</div>
                      </div>
                    </button>
                  </PopoverTrigger>
                  <PopoverContent className="w-80 p-0" align="start">
                    <div className="p-2">
                      <p className="text-xs font-semibold text-muted-foreground px-3 py-2">Competitor Insights</p>
                      <button
                        onClick={() => { setInput("Compare my visibility with top competitors"); setOpenPopover(null); }}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-accent rounded-md transition-colors"
                      >
                        Compare visibility
                      </button>
                      <button
                        onClick={() => { setInput("Analyze competitor mention frequency"); setOpenPopover(null); }}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-accent rounded-md transition-colors"
                      >
                        Analyze mention frequency
                      </button>
                      <button
                        onClick={() => { setInput("Identify gaps in competitor coverage"); setOpenPopover(null); }}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-accent rounded-md transition-colors"
                      >
                        Identify coverage gaps
                      </button>
                      <button
                        onClick={() => { setInput("Review competitor sentiment trends"); setOpenPopover(null); }}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-accent rounded-md transition-colors"
                      >
                        Review sentiment trends
                      </button>
                    </div>
                  </PopoverContent>
                </Popover>

                <Popover open={openPopover === 'prompts'} onOpenChange={(open) => setOpenPopover(open ? 'prompts' : null)}>
                  <PopoverTrigger asChild>
                    <button className="p-3 rounded-lg border border-border hover:bg-accent text-left">
                      <div className="flex items-center gap-2">
                        <Search className="h-4 w-4" />
                        <div className="text-sm font-medium">Optimize Prompts</div>
                      </div>
                    </button>
                  </PopoverTrigger>
                  <PopoverContent className="w-80 p-0" align="start">
                    <div className="p-2">
                      <p className="text-xs font-semibold text-muted-foreground px-3 py-2">Prompt Optimization</p>
                      <button
                        onClick={() => { setInput("Suggest new prompts to track for my domain"); setOpenPopover(null); }}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-accent rounded-md transition-colors"
                      >
                        Suggest new prompts
                      </button>
                      <button
                        onClick={() => { setInput("Optimize existing prompts for better coverage"); setOpenPopover(null); }}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-accent rounded-md transition-colors"
                      >
                        Optimize existing prompts
                      </button>
                      <button
                        onClick={() => { setInput("Group prompts by topic clusters"); setOpenPopover(null); }}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-accent rounded-md transition-colors"
                      >
                        Group by topics
                      </button>
                      <button
                        onClick={() => { setInput("Identify underperforming prompt categories"); setOpenPopover(null); }}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-accent rounded-md transition-colors"
                      >
                        Identify underperforming prompts
                      </button>
                    </div>
                  </PopoverContent>
                </Popover>
              </div>

            {/* Disclaimer */}
            <p className="text-xs text-muted-foreground">
              AI can make mistakes. Check important info.
            </p>
          </div>
        </div>
      ) : (
        /* Conversation Mode - Messages with bottom input */
        <>
          <div className="flex-1 overflow-y-auto">
            <div className="w-full flex justify-center pt-16">
              <div className="w-[60%]">
              {messages.map((message, index) => (
                <div
                  key={index}
                  className="flex gap-4 items-start px-6 py-4 transition-colors rounded-2xl"
                  style={{
                    backgroundColor: message.role === 'user' ? 'hsl(240, 10%, 96%)' : 'transparent'
                  }}
                >
                  <div className="flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center">
                    {message.role === 'assistant' ? (
                      <div className="w-9 h-9 rounded-full bg-gradient-to-r from-primary to-secondary flex items-center justify-center">
                        <Sparkles className="h-4 w-4 text-white" />
                      </div>
                    ) : (
                      <>
                        {getDomainFavicon() ? (
                          <img
                            src={getDomainFavicon()!}
                            alt="Domain favicon"
                            className="w-9 h-9 rounded-full object-cover"
                            onError={(e) => {
                              // Fallback to initials on error
                              e.currentTarget.style.display = 'none';
                              const parent = e.currentTarget.parentElement;
                              if (parent) {
                                parent.innerHTML = `<div class="w-9 h-9 rounded-full bg-muted-foreground/70 flex items-center justify-center"><span class="text-sm font-semibold text-white">${getUserInitials()}</span></div>`;
                              }
                            }}
                          />
                        ) : (
                          <div className="w-9 h-9 rounded-full bg-muted-foreground/70 flex items-center justify-center">
                            <span className="text-sm font-semibold text-white">{getUserInitials()}</span>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                  <div className="flex-1 min-w-0 py-1">
                    <div className="text-[15px] leading-normal">
                      <p className="whitespace-pre-wrap">{message.content}</p>
                    </div>
                  </div>
                </div>
              ))}
              {isLoading && (
                <div
                  className="flex gap-4 items-start px-6 py-4 rounded-2xl"
                  style={{ backgroundColor: 'transparent' }}
                >
                  <div className="flex-shrink-0 w-9 h-9 rounded-full bg-gradient-to-r from-primary to-secondary flex items-center justify-center">
                    <Sparkles className="h-4 w-4 text-white" />
                  </div>
                  <div className="flex-1 min-w-0 py-1">
                    <div className="flex gap-1">
                      <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                      <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                      <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                    </div>
                  </div>
                </div>
              )}
              </div>
            </div>
          </div>

          {/* Input Area at bottom - only in conversation mode */}
          <div className="px-4 py-4 bg-background w-full flex justify-center">
            <div className="w-[60%]">
              <div className="relative">
                <Textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask me anything..."
                  className="min-h-[84px] pr-12 resize-none shadow-glow"
                  disabled={isLoading}
                />
                <Button
                  onClick={handleSend}
                  disabled={!input.trim() || isLoading}
                  size="icon"
                  className="absolute right-2 bottom-2 rounded-full"
                >
                  <Send className="h-4 w-4" />
                </Button>
              </div>
              <p className="text-xs text-muted-foreground mt-2 text-center">
                AI can make mistakes. Check important info.
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
