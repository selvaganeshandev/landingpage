import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Slider } from "@/components/ui/slider";
import { ChipInput } from "@/components/ChipInput";
import { apiClient } from "@/services/api";
import { useDomainStore } from "@/stores/domainStore";
import {
  ArrowLeft,
  ArrowRight,
  Sparkles,
  Check,
  Loader2,
  CircleAlert,
  Globe,
  Wand2,
} from "lucide-react";

/**
 * Screen 2 of the Generate-with-AI flow — confirm the brand facts that drive
 * prompt generation, then choose scope.
 *
 * Everything here is pre-filled from the project where we already hold it. The
 * user's job is to correct and fill gaps, not to author from scratch, which is
 * why lists are chips rather than textareas and why every field carries a
 * provenance badge.
 *
 * UI only for now: nothing is generated and nothing is saved. `onGenerate`
 * hands the assembled config to the caller.
 */

/** Where a field's current value came from. There is deliberately no
 *  "from the site" state: nothing crawls the site to prefill this wizard.
 *  stage_ground does read the site, but only at generation time and only as
 *  LLM context — it never populates these inputs.
 *
 *  "none" is what the user's own typing gets: it needs no badge, because the
 *  thing they just entered is not news to them.
 *
 *  "inferred" means the Autofill button read it off the site. That badge is the
 *  one thing on this form the user did not write, so it is worth flagging for
 *  review — the model is told to omit rather than guess, but it can still be
 *  wrong. */
type Provenance = "saved" | "missing" | "none" | "inferred";

export interface WizardConfig {
  // Step 1
  brand_name: string;
  business_model: string;
  offering_categories: string[];
  short_description: string;
  niches: string[];
  country: string;
  regions_served: string[];
  price_positioning: string;
  // Step 2
  target_audience: string;
  use_cases: string[];
  buying_criteria: string[];
  common_objections: string[];
  topics_to_avoid: string[];
  // Step 3
  key_competitors: string[];
  differentiators: string[];
  seed_questions: string[];
  target_count: number;
  funnel_mix: string;
  branded_ratio: number;
}

interface PromptGenerationWizardProps {
  onBack: () => void;
  onGenerate: (config: WizardConfig) => void;
}

const BUSINESS_MODELS = [
  "B2C ecommerce",
  "D2C brand",
  "B2B SaaS",
  "Local services",
  "Marketplace",
  "Agency / services",
  "Other",
];

const PRICE_POSITIONS = ["Budget", "Mid-market", "Premium", "Mixed"];

/** The choice chips store their own label, but the extractor is constrained to
 *  stable slugs (a model asked for "B2B SaaS" free-hand returns "b2b saas",
 *  "SaaS (B2B)", …, none of which match a chip). Translate on the way in; an
 *  unmapped slug is dropped rather than shown as a selection that isn't there. */
const BUSINESS_MODEL_BY_SLUG: Record<string, string> = {
  b2c_ecommerce: "B2C ecommerce",
  d2c_brand: "D2C brand",
  b2b_saas: "B2B SaaS",
  local_services: "Local services",
  marketplace: "Marketplace",
  agency_services: "Agency / services",
  other: "Other",
};

/** The fields Autofill can write. Kept in one place so the "already stored"
 *  check and the fill loop cannot drift apart. Mirrors the backend's
 *  site_profile TEXT_FIELDS + LIST_FIELDS. */
const AUTOFILL_FIELDS = [
  "short_description", "target_audience", "business_model", "price_positioning",
  "niches", "offering_categories", "regions_served", "use_cases",
  "buying_criteria", "differentiators", "key_competitors",
] as const;

const PRICE_POSITION_BY_SLUG: Record<string, string> = {
  budget: "Budget",
  mid_market: "Mid-market",
  premium: "Premium",
  mixed: "Mixed",
};

const FOCUS_PRESETS = [
  { key: "balanced", label: "Balanced", hint: "Even spread across the funnel" },
  { key: "discovery", label: "Discovery-heavy", hint: "Category questions where you may be invisible" },
  { key: "comparison", label: "Comparison-heavy", hint: "Versus competitors and alternatives" },
  { key: "defence", label: "Brand defence", hint: "Reviews, trust and objections" },
];

const COUNT_OPTIONS = [5, 10, 20, 30];

const STEPS = [
  { n: 1, title: "What you sell" },
  { n: 2, title: "Who buys, and why" },
  { n: 3, title: "Competition & scope" },
];

/** Splits a stored string field into chips — several arrive comma-separated. */
const toList = (v: any): string[] => {
  if (Array.isArray(v)) return v.filter(Boolean).map(String);
  if (typeof v === "string" && v.trim()) {
    return v.split(",").map((s) => s.trim()).filter(Boolean);
  }
  return [];
};

const Badge = ({ state }: { state: Provenance }) => {
  if (state === "none") return null;
  if (state === "inferred") {
    return (
      <span className="inline-flex items-center gap-1 text-[11px] font-medium text-primary">
        <Globe className="h-3 w-3" /> From your site
      </span>
    );
  }
  if (state === "saved") {
    return (
      <span className="inline-flex items-center gap-1 text-[11px] font-medium text-success">
        <Check className="h-3 w-3" /> Saved
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-[11px] font-medium text-warning">
      <CircleAlert className="h-3 w-3" /> Needs input
    </span>
  );
};

/** Label row with its provenance badge. Plain function, not a component, so
 *  React keeps input identity stable across re-renders. */
const field = (label: string, state: Provenance, hint?: string) => (
  <div className="flex items-center justify-between gap-3">
    <Label className="text-sm">{label}</Label>
    <div className="flex items-center gap-2">
      {hint && <span className="text-[11px] text-muted-foreground">{hint}</span>}
      <Badge state={state} />
    </div>
  </div>
);

export const PromptGenerationWizard = ({
  onBack,
  onGenerate,
}: PromptGenerationWizardProps) => {
  const { selectedDomain } = useDomainStore();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(true);
  const [customCount, setCustomCount] = useState("");
  const [cfg, setCfg] = useState<WizardConfig>({
    brand_name: "",
    business_model: "",
    offering_categories: [],
    short_description: "",
    niches: [],
    country: "",
    regions_served: [],
    price_positioning: "",
    target_audience: "",
    use_cases: [],
    buying_criteria: [],
    common_objections: [],
    topics_to_avoid: [],
    key_competitors: [],
    differentiators: [],
    seed_questions: ["", "", ""],
    target_count: 20,
    funnel_mix: "balanced",
    // 0 by default: visibility monitoring is about whether the brand surfaces
    // in the generic questions buyers actually ask. A question that names the
    // brand presupposes the user already knows it, which measures nothing about
    // discovery. Raise the slider deliberately to track brand-defence queries.
    branded_ratio: 0,
  });
  // Which fields arrived already populated from the project record — drives the
  // Saved badge. Anything the user types is unbadged.
  const [prefilled, setPrefilled] = useState<Record<string, boolean>>({});
  // Fields the Autofill button filled from the site, so they can be badged as
  // not-the-user's-words and given a second look.
  const [inferred, setInferred] = useState<Record<string, boolean>>({});
  const [autofilling, setAutofilling] = useState(false);
  const [autofillNote, setAutofillNote] = useState<string | null>(null);
  // Fields the user has edited by hand this session. Autofill treats these as
  // final; everything else (blank, or loaded from the project record) is fair
  // game to replace.
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const [confirmRefetch, setConfirmRefetch] = useState(false);

  useEffect(() => {
    (async () => {
      if (!selectedDomain?.id) {
        setLoading(false);
        return;
      }
      try {
        const d: any = await apiClient.getDomain(selectedDomain.id);
        // Load every field the project stores, not just the original seven.
        // Autofill writes its findings back to Domain, so reading them all back
        // is what stops the crawl being paid for on every visit.
        const next: Partial<WizardConfig> = {
          brand_name: d?.name || selectedDomain.name || "",
          short_description: d?.short_description || "",
          niches: toList(d?.niches),
          country: d?.country || "",
          target_audience: d?.target_audience || "",
          topics_to_avoid: toList(d?.topics_to_avoid),
          key_competitors: toList(d?.key_competitors),
          business_model: d?.business_model || "",
          price_positioning: d?.price_positioning || "",
          offering_categories: toList(d?.offering_categories),
          regions_served: toList(d?.regions_served),
          use_cases: toList(d?.use_cases),
          buying_criteria: toList(d?.buying_criteria),
          common_objections: toList(d?.common_objections),
          differentiators: toList(d?.differentiators),
        };
        setCfg((p) => ({ ...p, ...next }));
        const isSet = (v: any) => (Array.isArray(v) ? v.length > 0 : !!v);
        setPrefilled(
          Object.fromEntries(
            Object.entries(next).map(([k, v]) => [k, isSet(v)]),
          ) as Record<string, boolean>,
        );
      } catch {
        // Prefill is a convenience; the wizard still works fully without it.
      } finally {
        setLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDomain?.id]);

  const set = <K extends keyof WizardConfig>(k: K, v: WizardConfig[K]) => {
    setCfg((p) => ({ ...p, [k]: v }));
    // Editing a field makes it the user's own answer: it stops being badged as
    // read off the site, and Autofill must not overwrite it afterwards.
    setInferred((p) => (p[k as string] ? { ...p, [k as string]: false } : p));
    setTouched((p) => (p[k as string] ? p : { ...p, [k as string]: true }));
  };

  /** Read the project's website and fill the form in from it.
   *
   *  What it may replace:
   *    - empty fields
   *    - values loaded from the project record ("Saved"), which are often
   *      stale — DataBlue's stored niches were generic DevOps terms with
   *      nothing to do with what the site actually sells
   *
   *  What it never replaces: anything edited in this session. That is the line
   *  that keeps the button safe to press at any point — your own words always
   *  win over a guess, no matter how many times it runs.
   */
  /** Fields Autofill would replace that already hold a stored value. Used to
   *  decide whether pressing the button needs confirming first. */
  const storedFieldCount = () =>
    AUTOFILL_FIELDS.filter((k) => {
      if (touched[k]) return false;          // user's own — never replaced anyway
      const v = cfg[k as keyof WizardConfig];
      return Array.isArray(v) ? v.length > 0 : !!v;
    }).length;

  const autofillFromSite = async (force = false) => {
    if (!selectedDomain?.id || autofilling) return;

    // Details are saved back to the project after a fetch, so a second press is
    // usually a re-crawl of something already answered. Confirm rather than
    // silently spend a crawl and a model call and replace what is there.
    if (!force && storedFieldCount() > 0) {
      setConfirmRefetch(true);
      return;
    }
    setConfirmRefetch(false);
    setAutofilling(true);
    setAutofillNote(null);
    try {
      const res: any = await apiClient.prefillFromSite(selectedDomain.id);
      const fields: Record<string, any> = res?.fields || {};

      if (res?.error) {
        setAutofillNote(res.error);
        return;
      }

      const filled: Record<string, boolean> = {};
      setCfg((prev) => {
        const next: any = { ...prev };
        for (const [rawKey, rawValue] of Object.entries(fields)) {
          const key = rawKey as keyof WizardConfig;
          if (!(key in prev)) continue;

          let value: any = rawValue;
          if (key === "business_model") value = BUSINESS_MODEL_BY_SLUG[String(rawValue)];
          if (key === "price_positioning") value = PRICE_POSITION_BY_SLUG[String(rawValue)];
          if (!value) continue;

          const current = prev[key];
          const isEmpty = Array.isArray(current) ? current.length === 0 : !current;
          // Fill the blanks, and refresh stale project-record values — but stop
          // dead at anything the user has edited themselves.
          if (!isEmpty && touched[rawKey]) continue;

          next[key] = value;
          filled[rawKey] = true;
        }
        return next;
      });

      setInferred((p) => ({ ...p, ...filled }));
      const n = Object.keys(filled).length;
      setAutofillNote(
        n === 0
          ? "Nothing to change — everything here is already your own answer."
          : `Filled ${n} field${n === 1 ? "" : "s"} from your site. Worth a quick check.`,
      );
    } catch (e: any) {
      setAutofillNote(e?.message || "Could not read the site. Fill it in by hand.");
    } finally {
      setAutofilling(false);
    }
  };

  const stateOf = (k: keyof WizardConfig): Provenance => {
    const v = cfg[k];
    const empty = Array.isArray(v) ? v.length === 0 : !v;
    if (empty) return "missing";
    if (inferred[k as string]) return "inferred";
    return prefilled[k] ? "saved" : "none";
  };

  // Only two fields gate progress; everything else improves quality without
  // blocking someone who wants to get moving.
  const canContinue =
    step !== 1 || (!!cfg.business_model && cfg.offering_categories.length > 0);

  const estimate = useMemo(() => {
    const platforms = 3;
    return (cfg.target_count * platforms * 30).toLocaleString();
  }, [cfg.target_count]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
        <p className="text-sm text-muted-foreground mt-3">
          Reading your project…
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto">
      {/* ---------- Autofill ----------
          Most of what this form asks is already stated on the brand's own
          homepage, and typing it out is the slowest part of the flow. Kept as
          an explicit button rather than something that runs on open: it costs
          a crawl and a model call, and it should be the user's choice to
          spend that. Only blank fields are touched. */}
      <div className="mb-6 rounded-xl border border-border bg-muted/30 p-4">
        <div className="flex flex-wrap items-center gap-3">
          <Globe className="h-4 w-4 text-primary shrink-0" />
          <div className="flex-1 min-w-[12rem]">
            <p className="text-sm font-medium">Fill this in from your website</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              {autofillNote ??
                "Read these answers off your website. Saved to the project, so this only needs running once."}
            </p>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => autofillFromSite()}
            disabled={autofilling || !selectedDomain?.id}
            className="border-border shrink-0"
          >
            {autofilling ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Reading your site…
              </>
            ) : (
              <>
                <Wand2 className="h-4 w-4 mr-2" />
                Autofill from my site
              </>
            )}
          </Button>
        </div>

        {/* Inline rather than a modal: the question is about the fields visible
            directly below, and a dialog would cover them up. */}
        {confirmRefetch && (
          <div className="mt-3 rounded-lg border border-warning/30 bg-warning/5 p-3.5">
            <div className="flex gap-2.5">
              <CircleAlert className="h-4 w-4 text-warning shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm font-medium">
                  This project already has details saved
                </p>
                <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                  {storedFieldCount()} field{storedFieldCount() === 1 ? " is" : "s are"}{" "}
                  already filled in from an earlier read. Fetching again re-reads
                  your site and overwrites them. Anything you have edited here
                  yourself is kept either way.
                </p>
                <div className="flex gap-2 mt-3">
                  <Button
                    type="button"
                    size="sm"
                    className="gradient-primary"
                    onClick={() => autofillFromSite(true)}
                  >
                    Fetch again and overwrite
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    className="border-border"
                    onClick={() => setConfirmRefetch(false)}
                  >
                    Keep what I have
                  </Button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ---------- Stepper ---------- */}
      <div className="flex items-center justify-center gap-2 mb-8">
        {STEPS.map((s, i) => (
          <div key={s.n} className="flex items-center gap-2">
            <div className="flex items-center gap-2">
              <div
                className={`h-7 w-7 rounded-full flex items-center justify-center text-xs font-semibold transition-colors ${
                  step > s.n
                    ? "bg-success text-success-foreground"
                    : step === s.n
                    ? "gradient-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground"
                }`}
              >
                {step > s.n ? <Check className="h-3.5 w-3.5" /> : s.n}
              </div>
              <span
                className={`text-sm hidden sm:inline ${
                  step === s.n ? "font-semibold" : "text-muted-foreground"
                }`}
              >
                {s.title}
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <div className="w-8 h-px bg-border mx-1" />
            )}
          </div>
        ))}
      </div>

      {/* ---------- Step 1 ---------- */}
      {step === 1 && (
        <div className="space-y-5">
          <div>
            <h2 className="font-inter text-2xl font-bold tracking-tight">
              What you sell
            </h2>
            <p className="text-sm text-muted-foreground mt-1.5">
              This shapes the kind of questions we generate. Correct anything
              that looks wrong.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              {field("Brand name", stateOf("brand_name"))}
              <Input
                value={cfg.brand_name}
                onChange={(e) => set("brand_name", e.target.value)}
              />
            </div>
            <div className="space-y-2">
              {field("Country", stateOf("country"))}
              <Input
                value={cfg.country}
                onChange={(e) => set("country", e.target.value)}
                placeholder="e.g. India"
              />
            </div>
          </div>

          <div className="space-y-2">
            {field("Business model", stateOf("business_model"), "Required")}
            <div className="flex flex-wrap gap-2">
              {BUSINESS_MODELS.map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => set("business_model", m)}
                  className={`rounded-lg border px-3 py-1.5 text-sm font-medium transition-all ${
                    cfg.business_model === m
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-border hover:border-primary/50 text-muted-foreground"
                  }`}
                >
                  {m}
                </button>
              ))}
            </div>
            <p className="text-xs text-muted-foreground">
              The biggest single lever — it decides the whole shape of the
              questions people ask.
            </p>
          </div>

          <div className="space-y-2">
            {field("What you sell", stateOf("offering_categories"), "Required")}
            <ChipInput
              value={cfg.offering_categories}
              onChange={(v) => set("offering_categories", v)}
              placeholder="e.g. Flowers, Cakes, Personalised gifts"
            />
          </div>

          <div className="space-y-2">
            {field("One-line description", stateOf("short_description"))}
            <Textarea
              rows={3}
              value={cfg.short_description}
              onChange={(e) => set("short_description", e.target.value)}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              {field("Niches", stateOf("niches"))}
              <ChipInput
                value={cfg.niches}
                onChange={(v) => set("niches", v)}
              />
            </div>
            <div className="space-y-2">
              {field("Cities / regions served", stateOf("regions_served"))}
              <ChipInput
                value={cfg.regions_served}
                onChange={(v) => set("regions_served", v)}
                placeholder="e.g. Bangalore, Mumbai, Pune"
              />
            </div>
          </div>

          <div className="space-y-2">
            {field("Price positioning", stateOf("price_positioning"))}
            <div className="flex flex-wrap gap-2">
              {PRICE_POSITIONS.map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => set("price_positioning", p)}
                  className={`rounded-lg border px-3 py-1.5 text-sm font-medium transition-all ${
                    cfg.price_positioning === p
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-border hover:border-primary/50 text-muted-foreground"
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ---------- Step 2 ---------- */}
      {step === 2 && (
        <div className="space-y-5">
          <div>
            <h2 className="font-inter text-2xl font-bold tracking-tight">
              Who buys, and why
            </h2>
            <p className="text-sm text-muted-foreground mt-1.5">
              Occasions and buying criteria are where the most realistic
              questions come from.
            </p>
          </div>

          <div className="space-y-2">
            {field("Target audience", stateOf("target_audience"))}
            <Textarea
              rows={3}
              value={cfg.target_audience}
              onChange={(e) => set("target_audience", e.target.value)}
            />
          </div>

          <div className="space-y-2">
            {field("Use cases & occasions", stateOf("use_cases"))}
            <ChipInput
              value={cfg.use_cases}
              onChange={(v) => set("use_cases", v)}
              placeholder="e.g. Birthdays, Anniversaries, Rakhi, Housewarming"
            />
          </div>

          <div className="space-y-2">
            {field("Buying criteria", stateOf("buying_criteria"))}
            <ChipInput
              value={cfg.buying_criteria}
              onChange={(v) => set("buying_criteria", v)}
              placeholder="e.g. Same-day delivery, Price, Freshness guarantee"
            />
            <p className="text-xs text-muted-foreground">
              Produces questions like “best florist with same-day delivery”.
            </p>
          </div>

          <div className="space-y-2">
            {field("Common objections", stateOf("common_objections"))}
            <ChipInput
              value={cfg.common_objections}
              onChange={(v) => set("common_objections", v)}
              placeholder="e.g. Late delivery, Refund process, Product quality"
            />
          </div>

          <div className="space-y-2">
            {field("Topics to avoid", stateOf("topics_to_avoid"))}
            <ChipInput
              value={cfg.topics_to_avoid}
              onChange={(v) => set("topics_to_avoid", v)}
            />
            <p className="text-xs text-muted-foreground">
              Applied as a filter after generation, so these never appear.
            </p>
          </div>
        </div>
      )}

      {/* ---------- Step 3 ---------- */}
      {step === 3 && (
        <div className="space-y-5">
          <div>
            <h2 className="font-inter text-2xl font-bold tracking-tight">
              Competition &amp; scope
            </h2>
            <p className="text-sm text-muted-foreground mt-1.5">
              Who you're up against, and how many prompts to generate.
            </p>
          </div>

          <div className="space-y-2">
            {field("Direct competitors", stateOf("key_competitors"))}
            <ChipInput
              value={cfg.key_competitors}
              onChange={(v) => set("key_competitors", v)}
              placeholder="e.g. Ferns N Petals, IGP, MyFlowerTree"
            />
          </div>

          <div className="space-y-2">
            {field("What makes you different", stateOf("differentiators"))}
            <ChipInput
              value={cfg.differentiators}
              onChange={(v) => set("differentiators", v)}
            />
          </div>

          <div className="space-y-2">
            <Label className="text-sm">
              Questions you'd want to be recommended for{" "}
              <span className="text-muted-foreground font-normal">
                (optional, but the single best input)
              </span>
            </Label>
            {cfg.seed_questions.map((q, i) => (
              <Input
                key={i}
                value={q}
                onChange={(e) => {
                  const next = [...cfg.seed_questions];
                  next[i] = e.target.value;
                  set("seed_questions", next);
                }}
                placeholder={
                  i === 0
                    ? "e.g. Where can I order same-day flowers in Bangalore?"
                    : "Another example…"
                }
                className="font-mono text-sm"
              />
            ))}
          </div>

          <div className="space-y-2">
            <Label className="text-sm">How many prompts?</Label>
            <div className="flex flex-wrap items-center gap-2">
              {COUNT_OPTIONS.map((n) => (
                <button
                  key={n}
                  type="button"
                  onClick={() => {
                    set("target_count", n);
                    setCustomCount("");
                  }}
                  className={`rounded-lg border px-4 py-1.5 text-sm font-medium transition-all ${
                    cfg.target_count === n && !customCount
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-border hover:border-primary/50 text-muted-foreground"
                  }`}
                >
                  {n}
                </button>
              ))}
              <Input
                type="number"
                min={1}
                value={customCount}
                onChange={(e) => {
                  setCustomCount(e.target.value);
                  const n = parseInt(e.target.value, 10);
                  if (!Number.isNaN(n) && n > 0) set("target_count", n);
                }}
                placeholder="Custom"
                className="w-28 h-9"
              />
            </div>
            <p className="text-xs text-muted-foreground">
              About{" "}
              <span className="font-medium text-foreground">
                {estimate} calls/month
              </span>{" "}
              on your OpenRouter key at 3 platforms, tracked daily.
            </p>
          </div>

          <div className="space-y-2">
            <Label className="text-sm">Focus</Label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {FOCUS_PRESETS.map((p) => (
                <button
                  key={p.key}
                  type="button"
                  onClick={() => set("funnel_mix", p.key)}
                  className={`rounded-lg border px-3 py-2.5 text-left transition-all ${
                    cfg.funnel_mix === p.key
                      ? "border-primary bg-primary/5"
                      : "border-border hover:border-primary/50"
                  }`}
                >
                  <p className="text-sm font-medium">{p.label}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {p.hint}
                  </p>
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label className="text-sm">Branded vs unbranded</Label>
              <span className="text-xs text-muted-foreground">
                {cfg.branded_ratio}% branded · {100 - cfg.branded_ratio}%
                unbranded
              </span>
            </div>
            <Slider
              value={[cfg.branded_ratio]}
              onValueChange={([v]) => set("branded_ratio", v)}
              min={0}
              max={100}
              step={5}
            />
            <p className="text-xs text-muted-foreground">
              Unbranded questions are where you can be invisible without knowing
              it, so this starts at zero branded. Naming your brand in the
              question assumes the asker already knows you — raise this only to
              track what AI says when they do.
            </p>
          </div>
        </div>
      )}

      {/* ---------- Footer ---------- */}
      <div className="flex items-center gap-2 mt-8 pt-5 border-t border-border">
        <Button
          variant="outline"
          className="border-border"
          onClick={() => (step === 1 ? onBack() : setStep(step - 1))}
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back
        </Button>

        <div className="ml-auto flex items-center gap-2">
          {!canContinue && (
            <span className="text-xs text-muted-foreground">
              Pick a business model and add what you sell
            </span>
          )}
          {step < 3 ? (
            <Button
              onClick={() => setStep(step + 1)}
              disabled={!canContinue}
              className="gradient-primary shadow-md shadow-primary/20"
            >
              Continue
              <ArrowRight className="h-4 w-4 ml-2" />
            </Button>
          ) : (
            <Button
              onClick={() => onGenerate(cfg)}
              className="gradient-primary shadow-md shadow-primary/20"
            >
              <Sparkles className="h-4 w-4 mr-2" />
              Generate {cfg.target_count} prompts
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};
