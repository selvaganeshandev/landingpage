/**
 * Audit Engine — shapes returned by /audits/ (backend/audits/serializers.py)
 * and the report body written by engine/core/audit_scoring.py.
 */

export type AuditStatus = 'INIT' | 'PROC' | 'DONE' | 'FAIL';
export type AuditStage = '' | 'profile' | 'crawl' | 'prompts' | 'engines' | 'serp' | 'score' | 'publish';
export type AuditSource = 'manual' | 'landing' | 'api';
export type GeoStage = '' | 'absent' | 'present' | 'preferred' | 'default';
export type EngineOutcome = 'cited' | 'mentioned' | 'absent' | 'failed';

export interface AuditCompetitor {
  name: string;
  host: string;
}

export interface AuditConfig {
  enabled: boolean;
  engines: string[];
  prompt_count: number;
  seo_enabled: boolean;
  keyword_count: number;
  public_ttl_days: number;
  can_manage: boolean;
  can_list: boolean;
}

export interface AuditCreateResponse {
  id: number;
  host: string;
  status: AuditStatus;
  reused: boolean;
  status_url: string;
  public_token: string;
  error?: string;
}

/** Progress fields shared by every serializer. */
interface AuditProgress {
  status: AuditStatus;
  stage: AuditStage;
  stage_index: number;
  stage_total: number;
  stage_label: string;
  progress: number;
  error: string;
  is_claimed: boolean;
  is_expired: boolean;
}

export interface AuditListRow extends AuditProgress {
  id: number;
  public_token: string;
  host: string;
  website: string;
  country: string;
  source: AuditSource;
  brand_name: string;
  industry: string;
  competitors: AuditCompetitor[];
  geo_score: number | null;
  geo_stage: GeoStage;
  seo_visibility: string | null;
  engines_preferred: number;
  engines_total: number;
  opens: number;
  last_opened_at: string | null;
  expires_at: string | null;
  claimed_at: string | null;
  claimed_domain: number | null;
  claimed_domain_name: string;
  requested_by: number | null;
  requested_by_email: string;
  requester_email: string;
  created_at: string;
  completed_at: string | null;
}

export interface AuditPromptResult {
  id: number;
  prompt_index: number;
  prompt_text: string;
  topic: string;
  funnel_stage: string;
  platform: string;
  run_index: number;
  status: 'ok' | 'failed' | 'rate_limited' | 'skipped';
  is_mention: boolean;
  is_cited: boolean;
  position: string | null;
  sentiment: string;
  competitors_mentioned: string[];
  rival_positions?: Record<string, number>;
  cited_domains: string[];
  response_text: string;
  latency_ms: number | null;
  error: string;
  created_at: string;
}

export interface AuditKeywordResult {
  id: number;
  keyword: string;
  search_volume: number | null;
  position: number | null;
  ranking_url: string;
  outranked_by: string[];
  serp_features: string[];
  geo_engines_mentioning: number | null;
  created_at: string;
}

// ---- report body (audit_scoring.score_audit) ----

export interface ReportEngine {
  platform: string;
  asked: number;
  answered: number;
  mentioned: number;
  cited: number;
  mention_rate: number;
  avg_position: number | null;
  top_rival: string | null;
  top_rival_mentions: number;
  preferred: boolean;
}

export type GapType = 'won' | 'position_gap' | 'visibility_gap' | 'educational' | 'no_data';

export interface ReportEvidence {
  prompt_index: number;
  prompt_text: string;
  funnel_stage: string;
  engines: Record<string, EngineOutcome>;
  runs?: number;
  best_position?: number | null;
  top_competitor?: string | null;
  cited_instead: string[];
  gap_type?: GapType;
}

export interface ReportFunnelCell { asked: number; mentioned: number; cited: number; rate: number | null }
export interface ReportFunnel {
  stages: string[];
  labels: Record<string, string>;
  platforms: string[];
  cells: Record<string, Record<string, ReportFunnelCell>>;
  by_stage: Record<string, { label: string; prompts: number; asked: number; mentioned: number; rate: number | null }>;
}

export interface ReportCompetitorRow {
  name: string;
  is_you: boolean;
  prompts_ranked: number;
  prompts_total: number;
  share: number;
  mentions: number;
  avg_position: number | null;
  stages: Record<string, { ranked: number; of: number; share: number | null }>;
}
export interface ReportCompetitors {
  rows: ReportCompetitorRow[];
  callouts: { name: string; title: string; text: string }[];
}

export interface ReportShareOfVoice {
  name: string;
  mentions: number;
  share: number;
  is_you: boolean;
}

export interface ReportCitationControl {
  owned: number;
  competitor: number;
  third_party: number;
  total_citations: number;
  top_sources: { host: string; count: number }[];
}

export interface ReportMeasure {
  key: string;
  pillar: 'findable' | 'cited' | 'chosen';
  label: string;
  value: string | null;
  score: number | null;
  target: number;
  evidence: string;
  status: 'pass' | 'fail' | null;
}

export interface ReportQuickWin {
  title: string;
  why: string;
  projected_geo_lift: number;
  effort_hours: number;
}

export interface ReportPlanItem {
  key: string;
  title: string;
  why: string;
  projected_geo_lift: number;
  effort_hours: number;
  owner: 'content' | 'dev' | 'seo' | 'outreach' | string;
  source: string | null;
}
export interface ReportPlanBucket {
  key: 'now' | 'next' | 'later';
  label: string;
  subtitle: string;
  from: number;
  to: number;
  lift: number;
  hours: number;
  items: ReportPlanItem[];
}
export interface ReportPlan {
  today: number;
  projected: number;
  status_quo: number;
  status_quo_note: string;
  buckets: ReportPlanBucket[];
  unscheduled: number;
}

export interface ReportNarrative {
  available: boolean;
  reason?: string;
  dominant_framing?: string;
  framing_share?: number | null;
  consistency?: number | null;
  descriptors_present?: { descriptor: string; share: number }[];
  descriptors_missing?: string[];
  by_engine?: { platform: string; leads_with: string; tone: 'positive' | 'neutral' | 'cautionary' | 'negative'; matches_profile: 'yes' | 'partial' | 'no' }[];
  off_brand?: { platform: string; claim: string; why: string }[];
  narrative_gap?: string;
  answers_analysed?: number;
  engines_analysed?: string[];
}

export interface ReportSummary {
  headline: string;
  key_findings: string[];
  sections: { geo?: string; competitors?: string; narrative?: string; website?: string; plan?: string };
  source: 'llm' | 'rules';
  fingerprint?: string;
}

export interface ReportSeo {
  keywords_total: number;
  top10: number;
  striking_distance: number;
  visibility: number | null;
  top_keywords: {
    keyword: string;
    search_volume: number | null;
    position: number | null;
    ranking_url: string;
    outranked_by: string[];
    geo_engines_mentioning: number | null;
  }[];
}

/** Technical / on-page signals for one sampled page (Phase O; absent on older reports). */
export interface ReportCrawlPageDetails {
  title_length?: number;
  description_length?: number;
  h1_count?: number;
  noindex?: boolean;
  canonical_status?: "ok" | "missing" | "mismatch";
  viewport?: boolean;
  images?: number;
  images_missing_alt?: number;
  mixed_content?: number;
  hreflang?: number;
  og?: boolean;
  https?: boolean;
  internal_links?: number;
  generic_anchors?: number;
  internal_anchors?: number;
  schema_gaps?: string[];
  has_person_schema?: boolean;
  credential_mentions?: number;
  status_code?: number;
  redirects?: number;
  final_url?: string;
  depth?: number;
  // Phase Q
  title_issue?: "short" | "long" | null;
  description_issue?: "short" | "long" | null;
  title_equals_h1?: boolean;
  heading_issues?: string[];
  images_missing_dimensions?: number;
  og_missing?: string[];
  twitter_card?: boolean;
  json_ld_invalid?: number;
  rich_result_blockers?: string[];
  thin?: boolean;
  scripts?: number;
  stylesheets?: number;
  images_legacy?: number;
  images_srcset?: number;
  soft_404?: boolean;
  lang?: string;
  favicon?: boolean;
  meta_refresh?: boolean;
  html_bytes?: number;
  has_params?: boolean;
  param_links?: number;
  hreflang_invalid?: string[];
  x_robots?: string;
  fetch_error?: string;
  index?: { verdict: IndexVerdict; reason: string };
  redirect_chain?: { status: number; url: string }[];
}

export type IndexVerdict = "indexable" | "not_indexable" | "canonicalised" | "redirected" | "unknown";

export interface ReportCrawlPage {
  url: string;
  title: string;
  fetched: boolean;
  word_count: number;
  schema_types: string[];
  author: string;
  external_links: number;
  last_modified: string | null;
  question_headings: number;
  has_table: boolean;
  has_faq_schema: boolean;
  details?: ReportCrawlPageDetails;
}

export type HealthPriority = "on_track" | "important" | "critical" | "not_measured";
export type IssueSeverity = "critical" | "warning" | "info";

export interface ReportHealthCategory {
  key: string;
  label: string;
  weight: number;
  score: number | null;
  priority: HealthPriority;
  detail: string;
}

export interface ReportTechnicalIssue {
  key: string;
  label: string;
  severity: IssueSeverity;
  count: number;
  of: number;
  examples: string[];
  fix: string;
  action: string;
  urls?: string[];
  snippet?: string;
}

export interface ReportIssueDelta {
  fixed: { key: string; label: string; was: number }[];
  new: { key: string; label: string; count: number }[];
  changed: { key: string; label: string; from: number; to: number }[];
  previous_total: number;
  current_total: number;
  previous_completed_at?: string | null;
  previous_health?: number | null;
}

export interface ReportSitemapHealth {
  listed: number;
  checked: number;
  errors: { url: string; problem: string }[];
  not_in_sitemap: string[];
}

export interface ReportLinkOpportunity { from: string; to: string; topic: string }

export interface ReportCwvPage {
  url: string;
  lcp_ms: number | null;
  cls: number | null;
  inp_ms: number | null;
  lcp_ms_rating?: CwvRating | null;
  cls_rating?: CwvRating | null;
  inp_ms_rating?: CwvRating | null;
  score: number | null;
  performance_score: number | null;
  mobile_friendly?: boolean | null;
}

export interface ReportContentPattern {
  key: string;
  title: string;
  status: "present" | "partial" | "missing";
  evidence: string;
  advice: string;
}

/** DataForSEO backlink summary (Phase P; present only when AUDIT_BACKLINKS_ENABLED). */
export interface ReportBacklinks {
  source: "dataforseo";
  authority_score: number | null;
  referring_domains: number;
  referring_domains_nofollow: number;
  backlinks: number;
  backlinks_nofollow: number;
  dofollow_share: number | null;
  broken_backlinks: number;
  referring_ips: number;
  referring_pages: number;
  first_seen: string | null;
  target: string;
  score: number | null;
  cost_usd?: number;
}

export type CwvRating = "good" | "needs_improvement" | "poor";

export interface ReportCwv {
  source: "field" | "lab";
  lcp_ms: number | null;
  cls: number | null;
  inp_ms: number | null;
  lcp_ms_rating?: CwvRating | null;
  cls_rating?: CwvRating | null;
  inp_ms_rating?: CwvRating | null;
  performance_score: number | null;
  score: number | null;
  mobile_friendly?: boolean | null;
  pages?: ReportCwvPage[];
  site_score?: number | null;
}

/** The crawl stage's site-level summary (audit_crawl.summarise + the page sample). */
export interface ReportCrawl {
  pages_sampled: number;
  urls_discovered?: number;
  seconds?: number;
  robots_present: boolean;
  bots: { bot: string; engine: string; allowed: boolean }[];
  bots_allowed: number;
  bots_total: number;
  sitemap_present: boolean;
  llms_txt: boolean;
  schema_coverage: number | null;
  schema_types: string[];
  recommended_types_present: string[];
  author_share: number | null;
  avg_word_count: number | null;
  avg_external_links: number | null;
  question_heading_share: number | null;
  table_share: number | null;
  dated_pages: number;
  stale_pages: number;
  freshest: string | null;
  error?: string | null;
  pages: ReportCrawlPage[];
  // ---- technical layer (Phase O; every key optional for older reports) ----
  sitemap_children?: number;
  link_check?: { checked: number; broken: number; examples: { url: string; status: number }[] } | null;
  cwv?: ReportCwv | null;
  backlinks?: ReportBacklinks | null;
  avg_internal_links?: number;
  descriptive_anchor_share?: number | null;
  missing_title?: number;
  duplicate_titles?: number;
  missing_description?: number;
  duplicate_descriptions?: number;
  missing_h1?: number;
  multiple_h1?: number;
  noindex_pages?: number;
  canonical_missing?: number;
  canonical_mismatch?: number;
  missing_viewport?: number;
  images_total?: number;
  images_missing_alt?: number;
  images_missing_alt_share?: number | null;
  mixed_content_pages?: number;
  http_pages?: number;
  redirected_pages?: number;
  error_pages?: number;
  hreflang_pages?: number;
  og_share?: number | null;
  schema_gaps?: { gap: string; pages: number }[];
  person_schema_share?: number | null;
  credential_share?: number | null;
  orphan_pages?: number;
  orphan_examples?: string[];
  unreached_pages?: number;
  max_depth?: number | null;
  deep_pages?: number;
  technical_issues?: ReportTechnicalIssue[];
  health?: { score: number | null; categories: ReportHealthCategory[] };
  content_patterns?: ReportContentPattern[];
  // Phase Q
  site?: {
    hsts?: boolean; ssl_error?: boolean; http_redirects_to_https?: boolean | null;
    security_headers?: Record<string, boolean>;
    certificate?: { expires: string; days_left: number; issuer: string } | null;
  };
  soft_404_pages?: number;
  avg_html_kb?: number | null;
  avg_scripts?: number;
  lang_missing_pages?: number;
  images_legacy_share?: number | null;
  indexability?: Record<IndexVerdict, number>;
  sitemap_url_count?: number;
  sitemap_health?: ReportSitemapHealth;
  duplicate_groups?: string[][];
  thin_pages?: number;
  redirect_chains?: number;
  json_ld_invalid?: number;
  rich_result_blockers?: { blocker: string; pages: number }[];
  og_complete_share?: number | null;
  images_missing_dimensions_share?: number | null;
  images_lazy_share?: number | null;
  title_equals_h1?: number;
  heading_issue_pages?: number;
  param_link_pages?: number;
  hreflang_errors?: { url: string; problem: string }[];
  link_opportunities?: ReportLinkOpportunity[];
  issue_delta?: ReportIssueDelta | null;
}

export interface AuditPageResult extends ReportCrawlPage {
  id: number;
  error: string;
  created_at: string;
}

export interface AuditReport {
  version: number;
  generated_at?: string;
  geo: {
    score: number;
    stage: GeoStage;
    stage_label: string;
    breakdown: { placement: number; frequency: number; sourcing: number; framing: number };
    weights: { placement: number; frequency: number; sourcing: number; framing: number };
    engines: ReportEngine[];
    evidence: ReportEvidence[];
    funnel?: ReportFunnel;
    competitors?: ReportCompetitors;
    gap_counts?: Partial<Record<GapType, number>>;
    runs_per_prompt?: number;
    share_of_voice: ReportShareOfVoice[];
    citation_control: ReportCitationControl;
    runs_total: number;
    runs_answered: number;
  };
  seo: ReportSeo | null;
  crawl?: ReportCrawl | null;
  measures: ReportMeasure[];
  pillars: { findable: number | null; cited: number | null; chosen: number | null };
  quick_wins: ReportQuickWin[];
  plan?: ReportPlan;
  narrative?: ReportNarrative;
  summary?: ReportSummary;
  profile?: {
    brand_name: string;
    host: string;
    industry: string;
    country: string;
    competitors: AuditCompetitor[];
    tech_stack: string[];
    description: string;
  };
  config?: {
    prompt_count: number;
    engines: string[];
    runs_per_prompt: number;
    seo_enabled: boolean;
    keyword_count: number;
    crawl_enabled?: boolean;
    crawl_pages?: number;
  };
}

/** The anonymous, token-addressed view. */
export interface PublicAudit extends AuditProgress {
  public_token: string;
  host: string;
  website: string;
  country: string;
  brand_name: string;
  industry: string;
  competitors: AuditCompetitor[];
  tech_stack: string[];
  stage_detail: Record<string, Record<string, unknown>>;
  geo_score: number | null;
  geo_stage: GeoStage;
  appearances: number;
  cited_runs: number;
  total_runs: number;
  engines_preferred: number;
  engines_total: number;
  share_of_voice: string | null;
  seo_visibility: string | null;
  keywords_top10: number;
  keywords_total: number;
  report: AuditReport | null;
  opens: number;
  expires_at: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface AuditDetail extends AuditListRow {
  tech_stack: string[];
  config: Record<string, unknown>;
  stage_detail: Record<string, Record<string, unknown>>;
  grounding: Record<string, unknown>;
  report: AuditReport | Record<string, never>;
  appearances: number;
  cited_runs: number;
  total_runs: number;
  share_of_voice: string | null;
  keywords_top10: number;
  keywords_total: number;
  requester_ip: string | null;
  prompt_results: AuditPromptResult[];
  keyword_results: AuditKeywordResult[];
  page_results: AuditPageResult[];
  status_url: string;
}

export interface AuditListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: AuditListRow[];
}

export interface AuditListParams {
  page?: number;
  page_size?: number;
  source?: AuditSource | '';
  status?: AuditStatus | '';
  geo_stage?: GeoStage;
  claimed?: 'true' | 'false' | '';
  search?: string;
  ordering?: string;
}

export interface AuditClaimResponse {
  success: boolean;
  message: string;
  audit: AuditListRow;
  domain: { id: number; name: string; url: string; country: string; processing_status: string };
}

export const AUDIT_STAGES: { key: Exclude<AuditStage, ''>; label: string; short: string }[] = [
  { key: 'profile', label: 'Reading the site', short: 'Profile' },
  { key: 'crawl', label: 'Checking your pages', short: 'Pages' },
  { key: 'prompts', label: 'Writing buyer prompts', short: 'Prompts' },
  { key: 'engines', label: 'Asking the AI engines', short: 'AI answers' },
  { key: 'serp', label: 'Checking Google rankings', short: 'SERP + crawl' },
  { key: 'score', label: 'Scoring', short: 'Score' },
  { key: 'publish', label: 'Publishing the report', short: 'Publish' },
];

export const GAP_LABELS: Record<GapType, { label: string; tone: string; hint: string }> = {
  won: { label: 'Won', tone: 'text-emerald-600', hint: 'Named in the top positions on at least one engine.' },
  position_gap: { label: 'Position gap', tone: 'text-amber-600', hint: 'Named, but never inside the top 3 options the engines list.' },
  visibility_gap: { label: 'Visibility gap', tone: 'text-destructive', hint: 'Never named while the engines name rivals.' },
  educational: { label: 'Educational', tone: 'text-muted-foreground', hint: 'A definitional answer where no vendor is named — not a real gap.' },
  no_data: { label: 'No answer', tone: 'text-muted-foreground', hint: 'No engine answered this prompt.' },
};

export const GEO_STAGE_LABELS: Record<Exclude<GeoStage, ''>, { label: string; range: string; tone: string }> = {
  absent: { label: 'Absent', range: '0–25', tone: 'text-destructive' },
  present: { label: 'Present', range: '26–50', tone: 'text-amber-600' },
  preferred: { label: 'Preferred', range: '51–75', tone: 'text-primary' },
  default: { label: 'Default', range: '76–100', tone: 'text-emerald-600' },
};

export const AUDIT_COUNTRIES: { code: string; name: string }[] = [
  { code: 'in', name: 'India' },
  { code: 'ae', name: 'UAE' },
  { code: 'us', name: 'United States' },
  { code: 'gb', name: 'United Kingdom' },
  { code: 'sg', name: 'Singapore' },
  { code: 'au', name: 'Australia' },
  { code: 'ca', name: 'Canada' },
  { code: 'de', name: 'Germany' },
];
