import { useState, useEffect, useRef } from "react";
import { Send, Sparkles, TrendingUp, Lightbulb, Users, Search, BarChart3, MessageSquare, Bell, ExternalLink, MessageSquareText, Plus, ChevronDown, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel,
  DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { useAuth } from "@/contexts/AuthContext";
import { useDomainStore } from "@/stores/domainStore";
import { useNavigationStore } from "@/stores/navigationStore";
import { api } from "@/services/api";
import { useSearchParams, useNavigate } from "react-router-dom";
import { getFaviconUrl, handleFaviconError } from "@/utils/faviconHelper";
import { cn } from "@/lib/utils";
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
  const navigate = useNavigate();
  // Rendered by the conversations rail beside the chat. Also pushed to the
  // navigation store below, which currently has no reader.
  const [conversations, setConversations] = useState<any[]>([]);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historySearch, setHistorySearch] = useState("");
  const [deletingId, setDeletingId] = useState<number | null>(null);
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
        setConversations(sorted.slice(0, 20));
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

  const openConversation = (id: number) => {
    loadConversation(id);
    navigate(`/chat?conversation=${id}`, { replace: true });
    setHistoryOpen(false);
  };

  const handleDeleteConversation = async (id: number) => {
    setDeletingId(id);
    try {
      await api.deleteChatConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      // Deleting the open conversation would otherwise leave its messages on
      // screen with no record behind them.
      if (conversationId === id) startNewChat();
    } catch (error) {
      console.error("Failed to delete conversation:", error);
    } finally {
      setDeletingId(null);
    }
  };

  const activeTitle =
    conversations.find((c: any) => c.id === conversationId)?.title ||
    (conversationId ? `Chat ${conversationId}` : "New chat");

  const filteredConversations = conversations.filter((c: any) =>
    !historySearch ||
    (c.title || `Chat ${c.id}`).toLowerCase().includes(historySearch.toLowerCase())
  );

  const startNewChat = () => {
    setMessages([]);
    setConversationId(null);
    setInput("");
    navigate("/chat", { replace: true });
  };

  return (
    <div className="flex flex-col h-screen bg-background animate-fade-in">
      {/* Chat header — conversation switcher on the left, new chat on the
          right. Replaces the fixed rail: the list is only needed on demand, and
          a 240px column of titles was permanently spending horizontal space the
          conversation itself wants. */}
      <header className="relative z-20 flex items-center justify-between gap-3 px-4 h-12 border-b border-border flex-shrink-0 bg-background">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm" className="gap-2 max-w-[60%] px-2">
              <MessageSquareText className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
              <span className="truncate text-sm font-medium">{activeTitle}</span>
              <ChevronDown className="h-3.5 w-3.5 flex-shrink-0 opacity-60" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-[280px]">
            <DropdownMenuLabel className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              Recent chats
            </DropdownMenuLabel>
            {conversations.length === 0 ? (
              <p className="px-2 py-2 text-xs text-muted-foreground">No conversations yet</p>
            ) : (
              conversations.slice(0, 8).map((c: any) => (
                <DropdownMenuItem
                  key={c.id}
                  onClick={() => openConversation(c.id)}
                  className={cn("cursor-pointer gap-2", conversationId === c.id && "text-primary font-medium")}
                >
                  <MessageSquareText className="h-3.5 w-3.5 flex-shrink-0 opacity-60" />
                  <span className="truncate">{c.title || `Chat ${c.id}`}</span>
                </DropdownMenuItem>
              ))
            )}
            {conversations.length > 0 && (
              <>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => setHistoryOpen(true)} className="cursor-pointer gap-2 text-primary">
                  <Search className="h-3.5 w-3.5" />
                  See all chats
                </DropdownMenuItem>
              </>
            )}
          </DropdownMenuContent>
        </DropdownMenu>

        <Button variant="outline" size="sm" onClick={startNewChat} className="gap-1.5 flex-shrink-0">
          <Plus className="h-4 w-4" />
          New chat
        </Button>
      </header>

      <div className="flex-1 flex flex-col min-w-0">
      {messages.length === 0 ? (
        /* Initial Mode - Centered input with quick actions */
        <div className="flex-1 flex flex-col justify-center items-center w-full px-4 pb-[100px]">
          <div className="w-full max-w-3xl text-center">
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
              <div className="w-full max-w-3xl px-4">
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
            <div className="w-full max-w-3xl px-4">
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

      {/* Full history — search and delete. The dropdown above shows only the
          eight most recent, which is enough to switch between what you are
          actively working on; this is for finding something older. */}
      <Dialog open={historyOpen} onOpenChange={setHistoryOpen}>
        <DialogContent className="sm:max-w-[560px]">
          <DialogHeader>
            <DialogTitle>All chats</DialogTitle>
          </DialogHeader>

          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              value={historySearch}
              onChange={(e) => setHistorySearch(e.target.value)}
              placeholder="Search chats…"
              className="pl-9"
              autoFocus
            />
          </div>

          <div className="max-h-[50vh] overflow-y-auto -mx-1 px-1 space-y-0.5">
            {filteredConversations.length === 0 ? (
              <p className="py-8 text-center text-sm text-muted-foreground">
                {conversations.length === 0 ? "No conversations yet" : "No chats match that search"}
              </p>
            ) : (
              filteredConversations.map((c: any) => (
                <div
                  key={c.id}
                  className={cn(
                    "group flex items-center gap-2 rounded-md px-2.5 py-2 transition-colors",
                    conversationId === c.id ? "bg-accent" : "hover:bg-accent/60"
                  )}
                >
                  <button
                    onClick={() => openConversation(c.id)}
                    className="flex flex-1 items-center gap-2 min-w-0 text-left"
                    title={c.title || `Chat ${c.id}`}
                  >
                    <MessageSquareText className="h-3.5 w-3.5 flex-shrink-0 text-muted-foreground" />
                    <span className="truncate text-sm">{c.title || `Chat ${c.id}`}</span>
                  </button>
                  {c.updated_at && (
                    <span className="text-[11px] text-muted-foreground flex-shrink-0">
                      {new Date(c.updated_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                    </span>
                  )}
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 flex-shrink-0 text-muted-foreground hover:text-destructive"
                    disabled={deletingId === c.id}
                    onClick={() => handleDeleteConversation(c.id)}
                    aria-label="Delete chat"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              ))
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};
