import { useState, useEffect, useRef } from "react";
import { Send, Sparkles, TrendingUp, Lightbulb, Users, Search, BarChart3, MessageSquare, Bell, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useAuth } from "@/contexts/AuthContext";
import { useDomainStore } from "@/stores/domainStore";
import { useNavigationStore } from "@/stores/navigationStore";
import { api } from "@/services/api";
import { useSearchParams } from "react-router-dom";
import { getFaviconUrl, handleFaviconError } from "@/utils/faviconHelper";
import { formatMessage, FORMATTED_MESSAGE_CLASSES } from "@/utils/textFormatter";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

// Loading messages - 3 sets
const LOADING_MESSAGES = {
  set1: [
    "Let me process that for a moment…",
    "Looking into this carefully…",
    "Gathering the most relevant details…",
    "Thinking this through… almost done…",
    "Organizing the information for clarity…",
    "Just polishing the response…",
    "Preparing something helpful for you…",
    "Hold on… finalizing the best answer…"
  ],
  set2: [
    "Analyzing your request from all angles…",
    "Forming a clear explanation…",
    "Connecting the important points…",
    "Reasoning through the details…",
    "Evaluating the best way to respond…",
    "Fine-tuning the final output…",
    "Let me make this as accurate as possible…",
    "Almost ready — refining the insight…"
  ],
  set3: [
    "Give me a moment to think this over…",
    "Working out the best way to answer…",
    "Let me organize my thoughts…",
    "Thinking it through… nearly there…",
    "Making sure everything lines up…",
    "Just a second — improving the clarity…",
    "Preparing a meaningful response…",
    "Alright… wrapping up the final answer…"
  ]
};

// Helper function to get random loading message
const getRandomLoadingMessage = () => {
  const sets = ['set1', 'set2', 'set3'] as const;
  const randomSet = sets[Math.floor(Math.random() * sets.length)];
  const messages = LOADING_MESSAGES[randomSet];
  return messages[Math.floor(Math.random() * messages.length)];
};

export const Chat = () => {
  const { user } = useAuth();
  const { selectedDomain } = useDomainStore();
  const { updateRecentChats } = useNavigationStore();
  const [searchParams] = useSearchParams();
  const [messages, setMessages] = useState<Array<{ role: 'user' | 'assistant'; content: string }>>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState("");
  const [openPopover, setOpenPopover] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const previousDomainRef = useRef<number | null>(null);
  const [streamingText, setStreamingText] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const loadingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Cycle through loading messages
  useEffect(() => {
    if (isLoading) {
      // Pick a random set of messages
      const sets = ['set1', 'set2', 'set3'] as const;
      const randomSet = sets[Math.floor(Math.random() * sets.length)];
      const messages = LOADING_MESSAGES[randomSet];
      let currentIndex = 0;

      // Set initial message
      setLoadingMessage(messages[0]);

      // Rotate through messages every 2 seconds
      loadingIntervalRef.current = setInterval(() => {
        currentIndex = (currentIndex + 1) % messages.length;
        setLoadingMessage(messages[currentIndex]);
      }, 2000);
    } else {
      // Clear interval when not loading
      if (loadingIntervalRef.current) {
        clearInterval(loadingIntervalRef.current);
        loadingIntervalRef.current = null;
      }
      setLoadingMessage("");
    }

    return () => {
      if (loadingIntervalRef.current) {
        clearInterval(loadingIntervalRef.current);
      }
    };
  }, [isLoading]);

  // Clear chat when domain changes
  useEffect(() => {
    if (previousDomainRef.current !== null &&
        selectedDomain?.id !== previousDomainRef.current) {
      // Domain changed - clear messages and conversation
      setMessages([]);
      setConversationId(null);
    }
    previousDomainRef.current = selectedDomain?.id || null;
  }, [selectedDomain]);

  // Load recent conversations on mount
  useEffect(() => {
    loadRecentConversations();
  }, [selectedDomain]);

  // Load conversation from URL params
  useEffect(() => {
    const convId = searchParams.get('conversation');
    if (convId && selectedDomain) {
      loadConversation(parseInt(convId));
    }
  }, [searchParams, selectedDomain]);

  // Auto-scroll to bottom when messages or streaming text changes
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingText, isLoading]);

  const loadRecentConversations = async () => {
    if (!selectedDomain) return;

    try {
      const response = await api.getChatConversations({
        domain_id: selectedDomain.id
      });

      if (response.conversations) {
        // Sort by updated_at descending and take first 20
        const sorted = [...response.conversations].sort((a: any, b: any) =>
          new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
        );
        updateRecentChats(sorted.slice(0, 20));
      }
    } catch (error) {
      console.error('Failed to load recent conversations:', error);
    }
  };

  const loadConversation = async (convId: number) => {
    try {
      const response = await api.getChatConversationDetail(convId);

      if (response.messages) {
        setMessages(response.messages.map((m: any) => ({
          role: m.role,
          content: m.content
        })));
        setConversationId(convId);
      }
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  };

  // Typewriter effect for streaming text
  // Uses requestAnimationFrame instead of setInterval to prevent pausing
  // when the user switches tabs (Issue 14: chat pauses on tab switch)
  const typeWriterEffect = (text: string, speed: number = 15) => {
    return new Promise<void>((resolve) => {
      setIsStreaming(true);
      setStreamingText("");
      let currentIndex = 0;
      let lastTime = performance.now();

      const animate = (now: number) => {
        // Check if tab was hidden (large time gap) — catch up instantly
        const elapsed = now - lastTime;
        if (elapsed > 500) {
          // Tab was in background — show full text immediately
          setStreamingText(text);
          setIsStreaming(false);
          setStreamingText("");
          resolve();
          return;
        }

        if (now - lastTime >= speed) {
          lastTime = now;
          if (currentIndex <= text.length) {
            setStreamingText(text.slice(0, currentIndex));
            currentIndex++;
          } else {
            setIsStreaming(false);
            setStreamingText("");
            resolve();
            return;
          }
        }
        requestAnimationFrame(animate);
      };

      requestAnimationFrame(animate);
    });
  };

  const handleSend = async () => {
    if (!input.trim() || !selectedDomain) return;

    const userMessage = input.trim();
    setInput("");
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);

    try {
      // Call Agentic ChatBot API
      const response = await api.sendChatMessage({
        message: userMessage,
        domain_id: selectedDomain.id,
        conversation_id: conversationId || undefined
      });

      // Hide loading indicator
      setIsLoading(false);

      // Start typewriter effect
      await typeWriterEffect(response.message);

      // Add complete message to history
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: response.message
      }]);

      // Save conversation ID for subsequent messages
      if (response.conversation_id) {
        setConversationId(response.conversation_id);
        // Refresh recent conversations after first message
        loadRecentConversations();
      }
    } catch (error: any) {
      console.error('ChatBot error:', error);
      setIsLoading(false);

      // Provide helpful error messages based on status code (Issue 16)
      let errorMessage = "Sorry, I encountered an error. Please try again.";
      const status = error.response?.status;
      const serverError = error.response?.data?.error;

      if (status === 403 || (serverError && serverError.toLowerCase().includes('access denied'))) {
        errorMessage = "You don't have access to the chat feature for this domain. Please contact your organization administrator to enable chat access.";
      } else if (status === 503) {
        errorMessage = "Chat service is temporarily unavailable. Please try again in a few moments.";
      } else if (status === 401) {
        errorMessage = "Your session has expired. Please refresh the page and log in again.";
      } else if (serverError) {
        errorMessage = serverError;
      }

      await typeWriterEffect(errorMessage);

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: errorMessage
      }]);
    }
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

  // Fallback to user initials when no domain is selected
  const getUserInitials = () => {
    if (user?.first_name && user?.last_name) {
      return `${user.first_name.charAt(0)}${user.last_name.charAt(0)}`.toUpperCase();
    } else if (user?.first_name) {
      return user.first_name.substring(0, 2).toUpperCase();
    } else if (user?.email) {
      const emailName = user.email.split('@')[0];
      return emailName.substring(0, 2).toUpperCase();
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
              <div className="flex items-center justify-center w-12 h-12 rounded-full bg-gradient-to-r from-primary to-secondary flex-shrink-0 overflow-hidden">
                {selectedDomain ? (
                  <img
                    key={selectedDomain.id}
                    src={getFaviconUrl(selectedDomain.url, 48)}
                    alt="Project favicon"
                    className="w-full h-full object-cover"
                    onError={(e) => handleFaviconError(e, selectedDomain.url, selectedDomain.name, 48)}
                  />
                ) : (
                  <span className="text-xs font-semibold text-white">{getUserInitials()}</span>
                )}
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
                placeholder="What would you like to explore in your domain?"
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
                {/* Analytics & Insights */}
                <Popover open={openPopover === 'analytics'} onOpenChange={(open) => setOpenPopover(open ? 'analytics' : null)}>
                  <PopoverTrigger asChild>
                    <button className="p-3 rounded-lg border border-border hover:bg-accent text-left">
                      <div className="flex items-center gap-2">
                        <BarChart3 className="h-4 w-4" />
                        <div className="text-sm font-medium">Analytics & Insights</div>
                      </div>
                    </button>
                  </PopoverTrigger>
                  <PopoverContent className="w-80 p-0" align="start">
                    <div className="p-2">
                      <p className="text-xs font-semibold text-muted-foreground px-3 py-2">Analytics & Insights</p>
                      <button
                        onClick={() => { setInput("Give me a complete dashboard overview"); setOpenPopover(null); }}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-accent rounded-md transition-colors"
                      >
                        Dashboard overview
                      </button>
                      <button
                        onClick={() => { setInput("Show historical trends for the last 6 months"); setOpenPopover(null); }}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-accent rounded-md transition-colors"
                      >
                        Historical trends
                      </button>
                      <button
                        onClick={() => { setInput("Analyze sentiment breakdown by platform"); setOpenPopover(null); }}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-accent rounded-md transition-colors"
                      >
                        Sentiment analysis
                      </button>
                      <button
                        onClick={() => { setInput("What topics am I mentioned in?"); setOpenPopover(null); }}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-accent rounded-md transition-colors"
                      >
                        Topic analysis
                      </button>
                      <button
                        onClick={() => { setInput("Show platform breakdown for all metrics"); setOpenPopover(null); }}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-accent rounded-md transition-colors"
                      >
                        Platform breakdown
                      </button>
                    </div>
                  </PopoverContent>
                </Popover>

                {/* Mentions & Citations */}
                <Popover open={openPopover === 'mentions'} onOpenChange={(open) => setOpenPopover(open ? 'mentions' : null)}>
                  <PopoverTrigger asChild>
                    <button className="p-3 rounded-lg border border-border hover:bg-accent text-left">
                      <div className="flex items-center gap-2">
                        <MessageSquare className="h-4 w-4" />
                        <div className="text-sm font-medium">Mentions & Citations</div>
                      </div>
                    </button>
                  </PopoverTrigger>
                  <PopoverContent className="w-80 p-0" align="start">
                    <div className="p-2">
                      <p className="text-xs font-semibold text-muted-foreground px-3 py-2">Mentions & Citations</p>
                      <button
                        onClick={() => { setInput("Show me recent mentions from all platforms"); setOpenPopover(null); }}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-accent rounded-md transition-colors"
                      >
                        Recent mentions
                      </button>
                      <button
                        onClick={() => { setInput("List negative mentions from ChatGPT"); setOpenPopover(null); }}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-accent rounded-md transition-colors"
                      >
                        Negative mentions
                      </button>
                      <button
                        onClick={() => { setInput("What sources cite my domain?"); setOpenPopover(null); }}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-accent rounded-md transition-colors"
                      >
                        Citation sources
                      </button>
                      <button
                        onClick={() => { setInput("Show top mentions sorted by position"); setOpenPopover(null); }}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-accent rounded-md transition-colors"
                      >
                        Top mentions
                      </button>
                    </div>
                  </PopoverContent>
                </Popover>

                {/* Competitors & Strategy */}
                <Popover open={openPopover === 'competitors'} onOpenChange={(open) => setOpenPopover(open ? 'competitors' : null)}>
                  <PopoverTrigger asChild>
                    <button className="p-3 rounded-lg border border-border hover:bg-accent text-left">
                      <div className="flex items-center gap-2">
                        <Users className="h-4 w-4" />
                        <div className="text-sm font-medium">Competitors & Strategy</div>
                      </div>
                    </button>
                  </PopoverTrigger>
                  <PopoverContent className="w-80 p-0" align="start">
                    <div className="p-2">
                      <p className="text-xs font-semibold text-muted-foreground px-3 py-2">Competitors & Strategy</p>
                      <button
                        onClick={() => { setInput("Compare my performance with competitors"); setOpenPopover(null); }}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-accent rounded-md transition-colors"
                      >
                        Competitor analysis
                      </button>
                      <button
                        onClick={() => { setInput("What's my share of voice in the market?"); setOpenPopover(null); }}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-accent rounded-md transition-colors"
                      >
                        Share of voice
                      </button>
                      <button
                        onClick={() => { setInput("Identify content gaps and opportunities"); setOpenPopover(null); }}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-accent rounded-md transition-colors"
                      >
                        Content gaps
                      </button>
                      <button
                        onClick={() => { setInput("Suggest content topics to improve visibility"); setOpenPopover(null); }}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-accent rounded-md transition-colors"
                      >
                        Content strategy
                      </button>
                    </div>
                  </PopoverContent>
                </Popover>

                {/* Prompts & Alerts */}
                <Popover open={openPopover === 'prompts'} onOpenChange={(open) => setOpenPopover(open ? 'prompts' : null)}>
                  <PopoverTrigger asChild>
                    <button className="p-3 rounded-lg border border-border hover:bg-accent text-left">
                      <div className="flex items-center gap-2">
                        <Bell className="h-4 w-4" />
                        <div className="text-sm font-medium">Prompts & Alerts</div>
                      </div>
                    </button>
                  </PopoverTrigger>
                  <PopoverContent className="w-80 p-0" align="start">
                    <div className="p-2">
                      <p className="text-xs font-semibold text-muted-foreground px-3 py-2">Prompts & Alerts</p>
                      <button
                        onClick={() => { setInput("Show my prompt groups and their performance"); setOpenPopover(null); }}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-accent rounded-md transition-colors"
                      >
                        Prompt groups
                      </button>
                      <button
                        onClick={() => { setInput("Suggest new prompts to track"); setOpenPopover(null); }}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-accent rounded-md transition-colors"
                      >
                        Suggest prompts
                      </button>
                      <button
                        onClick={() => { setInput("What active alerts do I have?"); setOpenPopover(null); }}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-accent rounded-md transition-colors"
                      >
                        Active alerts
                      </button>
                      <button
                        onClick={() => { setInput("Any misinformation alerts for my domain?"); setOpenPopover(null); }}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-accent rounded-md transition-colors"
                      >
                        Misinformation alerts
                      </button>
                    </div>
                  </PopoverContent>
                </Popover>
              </div>

            {/* Disclaimer */}
            <p className="text-xs text-muted-foreground">
              AI can make mistakes. Double-check important details.
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
                  className={`flex items-start transition-colors animate-fade-in ${
                    message.role === 'user' ? 'py-3' : 'py-1.5'
                  }`}
                  style={{
                    animationDelay: `${index * 0.05}s`,
                  }}
                >
                  {message.role === 'user' ? (
                    <div className="flex-1 min-w-0">
                      <div className="bg-primary/5 rounded-2xl px-4 py-3 inline-flex items-start gap-3 max-w-full">
                        <div className="flex-shrink-0 w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center overflow-hidden">
                          {selectedDomain ? (
                            <img
                              key={selectedDomain.id}
                              src={getFaviconUrl(selectedDomain.url, 28)}
                              alt="Project favicon"
                              className="w-full h-full object-cover"
                              onError={(e) => handleFaviconError(e, selectedDomain.url, selectedDomain.name, 28)}
                            />
                          ) : (
                            <span className="text-xs font-semibold text-primary">{getUserInitials()}</span>
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-[15px] leading-normal whitespace-pre-wrap m-0">{message.content}</p>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="w-full">
                      <div className={FORMATTED_MESSAGE_CLASSES}>
                        <div dangerouslySetInnerHTML={{ __html: formatMessage(message.content) }} />
                      </div>
                    </div>
                  )}
                </div>
              ))}
              {isLoading && (
                <div className="flex items-center gap-2 py-1.5 animate-fade-in">
                  <Sparkles className="h-4 w-4 text-primary animate-bounce" />
                  {loadingMessage && (
                    <p className="text-[15px] text-muted-foreground">{loadingMessage}</p>
                  )}
                </div>
              )}
              {isStreaming && streamingText && (
                <div className="py-1.5 w-full">
                  <div className={FORMATTED_MESSAGE_CLASSES}>
                    <div dangerouslySetInnerHTML={{ __html: formatMessage(streamingText) }} />
                    <span className="inline-block w-1.5 h-4 bg-primary animate-pulse ml-0.5 align-middle"></span>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
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
                  placeholder="What would you like to explore in your domain?"
                  className="min-h-[84px] pr-12 resize-none shadow-glow"
                  disabled={isLoading || isStreaming}
                />
                <Button
                  onClick={handleSend}
                  disabled={!input.trim() || isLoading || isStreaming}
                  size="icon"
                  className="absolute right-2 bottom-2 rounded-full"
                >
                  <Send className="h-4 w-4" />
                </Button>
              </div>
              <p className="text-xs text-muted-foreground mt-2 text-center">
                AI can make mistakes. Double-check important details.
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
