"""
Function calling tools for the Agentic ChatBot
These tools allow the AI to interact with domain data and perform actions
"""

CHAT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_domain_analytics",
            "description": "Get comprehensive analytics data for the user's domain including mentions, sentiment, visibility score, and platform distribution. Use this when user asks about domain performance, metrics, or trends.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_range": {
                        "type": "string",
                        "enum": ["7d", "30d", "90d", "all"],
                        "description": "Time period for analytics (7 days, 30 days, 90 days, or all time)"
                    },
                    "include_trends": {
                        "type": "boolean",
                        "description": "Whether to include historical trend data"
                    }
                },
                "required": ["date_range"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_competitor_analysis",
            "description": "Analyze competitors and compare visibility, mentions, and sentiment with the user's domain. Use this when user asks about competitors or market position.",
            "parameters": {
                "type": "object",
                "properties": {
                    "competitor_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of competitor names to analyze (optional - if not provided, analyzes all tracked competitors)"
                    },
                    "metric": {
                        "type": "string",
                        "enum": ["visibility", "mentions", "sentiment", "all"],
                        "description": "Specific metric to compare"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_prompt_performance",
            "description": "Get performance metrics for tracked prompts including mention frequency, average position, and sentiment. Use this when user asks about prompts or which queries mention their domain.",
            "parameters": {
                "type": "object",
                "properties": {
                    "platform": {
                        "type": "string",
                        "enum": ["ChatGPT", "Gemini", "Perplexity", "all"],
                        "description": "Filter by AI platform"
                    },
                    "sort_by": {
                        "type": "string",
                        "enum": ["mentions", "position", "sentiment", "recent"],
                        "description": "How to sort the results"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of prompts to return (default: 10)"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_content_gaps",
            "description": "Identify content gaps and suggest topics where the domain could improve visibility. Use this when user asks for content ideas, topics to cover, or how to improve visibility.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of gap suggestions to return (default: 10)"
                    },
                    "focus_area": {
                        "type": "string",
                        "enum": ["low_visibility", "competitor_strength", "emerging_topics", "all"],
                        "description": "What type of gaps to focus on"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_sentiment_analysis",
            "description": "Get detailed sentiment analysis showing positive, neutral, and negative mentions breakdown. Use this when user asks about sentiment, perception, or how they're being portrayed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_range": {
                        "type": "string",
                        "enum": ["7d", "30d", "90d", "all"],
                        "description": "Time period for sentiment analysis"
                    },
                    "by_platform": {
                        "type": "boolean",
                        "description": "Break down sentiment by platform"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_mentions",
            "description": "Get the most recent or most relevant mentions of the domain. Use this when user wants to see specific examples of how they're being mentioned.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of mentions to return (default: 5)"
                    },
                    "sort_by": {
                        "type": "string",
                        "enum": ["recent", "highest_position", "lowest_position", "sentiment"],
                        "description": "How to sort mentions"
                    },
                    "platform": {
                        "type": "string",
                        "enum": ["ChatGPT", "Gemini", "Perplexity", "all"],
                        "description": "Filter by platform"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_monitoring_rule",
            "description": "Create a new monitoring rule/alert for the domain. Use this when user wants to set up automated alerts or monitoring.",
            "parameters": {
                "type": "object",
                "properties": {
                    "rule_name": {
                        "type": "string",
                        "description": "Name for the monitoring rule"
                    },
                    "condition": {
                        "type": "string",
                        "enum": ["position_drop", "mention_spike", "sentiment_negative", "new_competitor"],
                        "description": "What condition to monitor"
                    },
                    "threshold": {
                        "type": "number",
                        "description": "Threshold value for the alert"
                    },
                    "notification_channel": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["email", "in_app"]
                        },
                        "description": "How to send notifications"
                    }
                },
                "required": ["rule_name", "condition", "notification_channel"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_prompts",
            "description": "Suggest new prompts to track based on domain niche, competitors, and performance gaps. Use this when user asks what prompts they should track.",
            "parameters": {
                "type": "object",
                "properties": {
                    "count": {
                        "type": "integer",
                        "description": "Number of prompts to suggest (default: 5)"
                    },
                    "strategy": {
                        "type": "string",
                        "enum": ["competitor_based", "niche_based", "gap_based", "trending"],
                        "description": "Strategy for suggesting prompts"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_platform_breakdown",
            "description": "Get detailed breakdown of performance across different AI platforms (ChatGPT, Gemini, Perplexity). Use this when user asks about platform-specific performance.",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {
                        "type": "string",
                        "enum": ["mentions", "position", "sentiment", "all"],
                        "description": "Which metric to analyze"
                    },
                    "date_range": {
                        "type": "string",
                        "enum": ["7d", "30d", "90d", "all"],
                        "description": "Time period"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_insights_dashboard",
            "description": "Get comprehensive insights dashboard data including key metrics, trends, and highlights. Use this when user asks for overall insights, dashboard summary, or key performance indicators.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_range": {
                        "type": "string",
                        "enum": ["7d", "30d", "90d", "all"],
                        "description": "Time period for insights"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_mentions_list",
            "description": "Get a detailed list of mentions with filters. Use this when user wants to see specific mentions, search mentions, or filter by platform/sentiment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "platform": {
                        "type": "string",
                        "enum": ["ChatGPT", "Gemini", "Perplexity", "all"],
                        "description": "Filter by platform"
                    },
                    "sentiment": {
                        "type": "string",
                        "enum": ["positive", "neutral", "negative", "all"],
                        "description": "Filter by sentiment"
                    },
                    "search_query": {
                        "type": "string",
                        "description": "Search term to filter mentions"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of mentions to return (default: 10)"
                    },
                    "sort_by": {
                        "type": "string",
                        "enum": ["recent", "position", "sentiment"],
                        "description": "Sort order"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_citations_list",
            "description": "Get citations where the domain was mentioned with source URLs. Use this when user asks about citations, sources, or where they were mentioned.",
            "parameters": {
                "type": "object",
                "properties": {
                    "platform": {
                        "type": "string",
                        "enum": ["ChatGPT", "Gemini", "Perplexity", "all"],
                        "description": "Filter by platform"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["verified", "pending", "flagged", "all"],
                        "description": "Citation verification status"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of citations to return (default: 10)"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_alerts_list",
            "description": "Get active alerts and alert rules for the domain. Use this when user asks about alerts, notifications, or monitoring rules.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["active", "investigating", "resolved", "all"],
                        "description": "Filter alerts by status"
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["high", "medium", "low", "all"],
                        "description": "Filter by severity"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of alerts to return (default: 10)"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_topics_analysis",
            "description": "Analyze topics and themes in mentions. Use this when user asks about topics, themes, or what people are discussing about their domain.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_range": {
                        "type": "string",
                        "enum": ["7d", "30d", "90d", "all"],
                        "description": "Time period"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of top topics to return (default: 10)"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_share_of_voice",
            "description": "Get share of voice analysis showing domain's visibility compared to market/competitors. Use this when user asks about market share, visibility percentage, or competitive position.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_range": {
                        "type": "string",
                        "enum": ["7d", "30d", "90d", "all"],
                        "description": "Time period"
                    },
                    "include_competitors": {
                        "type": "boolean",
                        "description": "Include competitor breakdown"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_historical_trends",
            "description": "Get historical trends showing how metrics have changed over time. Use this when user asks about trends, growth, or how things have changed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {
                        "type": "string",
                        "enum": ["mentions", "visibility", "sentiment", "position", "all"],
                        "description": "Which metric to show trends for"
                    },
                    "period": {
                        "type": "string",
                        "enum": ["daily", "weekly", "monthly"],
                        "description": "Aggregation period"
                    },
                    "months": {
                        "type": "integer",
                        "description": "Number of months of history (default: 3)"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_prompt_groups",
            "description": "Get prompt groups (collections of related prompts). Use this when user asks about prompt categories, groups, or wants to see organized prompts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of groups to return (default: 10)"
                    },
                    "sort_by": {
                        "type": "string",
                        "enum": ["mentions", "recent", "performance"],
                        "description": "Sort order"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_misinformation_alerts",
            "description": "Get misinformation and accuracy alerts for the domain. Use this when user asks about misinformation, incorrect information, or accuracy issues.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["active", "resolved", "all"],
                        "description": "Filter by status"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of alerts to return (default: 10)"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_domain_summary",
            "description": "Get a comprehensive summary of the domain including all key metrics, status, and quick overview. Use this when user asks for a complete overview or summary.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }
]
