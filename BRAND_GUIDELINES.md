# Promptmaxx — UI conventions

Extracted from the existing pages on 2026-08-07, by counting what the codebase
actually does rather than what any single page happens to do. Where pages
disagree, the majority pattern is recorded as the rule and the exception is
named, so a new page doesn't inherit an old mistake.

Source of truth for tokens: `frontend/src/index.css` and
`frontend/tailwind.config.ts`. Everything below is Tailwind + shadcn/ui.

---

## 1. Colour — always tokens, never raw Tailwind colours

Semantic tokens are defined for both light and dark in `index.css` and mapped in
`tailwind.config.ts`. Using them is what makes dark mode work for free.

| Token | Use for |
|---|---|
| `primary` | Brand purple `hsl(250 95% 63%)`. Active states, primary icons, key actions |
| `secondary` | Brand magenta `hsl(280 90% 68%)`. Secondary icons, the second series in a chart |
| `success` | Gains, improvements, "up" |
| `destructive` | Losses, declines, "down", danger |
| `warning` | Caution, needs attention |
| `muted` / `muted-foreground` | Neutral surfaces and secondary text |
| `card`, `border`, `background`, `foreground` | Surfaces, rules, page ground, body text |

**Rule:** write `text-success` / `text-destructive`, not `text-green-500` /
`text-red-500`, and never `emerald`, `rose`, `sky`, etc. Raw colours are
hard-coded for light mode and drift in dark mode.

> Adoption: `text-destructive` 32 files, `text-success` 17 files, versus
> `text-red-500` 10 and `text-green-500` 6. The raw-colour files are the older
> ones (`SeoRankings.tsx` among them) — match the tokens, not those pages.

Tinted surfaces use the token at low alpha: `bg-success/10 border-success/20`.

---

## 2. Stat cards

The canonical four-across summary row. Label and number on the left, an icon on
the right, one line of context underneath.

```tsx
<div className="grid grid-cols-1 md:grid-cols-4 gap-6">
  <Card className="p-6 border border-border">
    <div className="flex items-center justify-between">
      <div>
        <p className="text-sm text-muted-foreground">Total Citations</p>
        <p className="text-2xl font-bold mt-1">{value}</p>
      </div>
      <Link2 className="h-5 w-5 text-primary" />
    </div>
    <p className="text-xs text-muted-foreground mt-2">Distinct domains cited</p>
  </Card>
</div>
```

- Grid: `grid grid-cols-1 md:grid-cols-4 gap-6`
- Card: `p-6 border border-border` — **no** nested tinted box inside. A coloured
  panel within a card reads as a box-in-a-box and appears nowhere in the app.
- Label `text-sm text-muted-foreground`, value `text-2xl font-bold mt-1`
- Icon `h-5 w-5`, tinted with a semantic token (`text-primary`, `text-secondary`,
  `text-success`, `text-destructive`) to carry the meaning — this is where colour
  goes, not the card background.
- Optional sub-line `text-xs text-muted-foreground mt-2`

Reference: `pages/Citations.tsx:349`, `pages/ContentGaps.tsx:319`,
`pages/HistoricalTrends.tsx:345`, `pages/Alerts.tsx:433`.

### Metric explanations

Eight pages wrap a stat label in `<InfoHint><MetricHint title plain formula />`
to explain what a number means and how it is computed. Worth adding on any
metric whose definition isn't self-evident. See `pages/Citations.tsx:355`.

---

## 3. Tabs

One pattern, used by 15+ pages. The active tab carries the brand gradient.

```tsx
<TabsList className="bg-muted/50 p-1 border border-border">
  <TabsTrigger
    value="all"
    className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white"
  >
    All Platforms
  </TabsTrigger>
</TabsList>
```

- List: `bg-muted/50 p-1 border border-border` (add `mb-4`/`mb-6` when the content
  needs separation)
- Trigger: always the three `data-[state=active]:` classes above. A bare
  `<TabsTrigger>` renders a flat grey pill that doesn't read as branded.

Reference: `pages/Mentions.tsx:280`, `pages/Citations.tsx:615`,
`pages/Alerts.tsx:475`, `pages/SeoKeywordDetail.tsx:623`.

---

## 4. Page shell

```tsx
<div className="p-8 space-y-8 bg-background animate-fade-in">
  <div className="flex items-center justify-between">
    <div>
      <h1 className="text-4xl font-bold tracking-tight">Page Title</h1>
      <p className="text-muted-foreground mt-2">One line on what this page answers</p>
    </div>
    {/* optional primary action */}
    <Button className="gradient-primary shadow-md shadow-primary/20">
      <Plus className="h-4 w-4 mr-2" /> Add Thing
    </Button>
  </div>
  ...
</div>
```

- Root: `p-8 space-y-8 bg-background animate-fade-in`
- Title `text-4xl font-bold tracking-tight`, subtitle `text-muted-foreground mt-2`
- No icon beside the page title — the sidebar already carries it.

### Detail pages have a different header

A page reached *from* a list does not repeat the index-page header. The back
control is an **icon-only outline button inline to the left of the title**, and
the row carries a rule beneath it:

```tsx
<div className="flex items-center justify-between pb-4 border-b border-border/50">
  <div className="flex items-center gap-4">
    <Button variant="outline" size="icon" className="border-border/50"
            onClick={() => navigate("/seo-rankings")}>
      <ArrowLeft className="h-4 w-4" />
    </Button>
    <div>
      <h1 className="text-2xl font-bold tracking-tight font-inter">{title}</h1>
      <p className="text-muted-foreground mt-0.5">{context}</p>
    </div>
  </div>
  {/* row actions, if any */}
</div>
```

- `text-2xl`, not the `text-4xl` used on index pages
- Never a full-width "← Back to X" text button stacked above the title
- Reference: `pages/SeoKeywordDetail.tsx:588`, `pages/CompetitorDetail.tsx:770`

### Button hierarchy

Only one button on a page gets the gradient. Everything else is secondary.

| Kind | Style | Examples |
|---|---|---|
| Primary action — creates something | `gradient-primary shadow-md shadow-primary/20` | Add Keyword, Create Report |
| Secondary action — exports, filters, settings | `variant="outline"` | Export, Configure, Refresh |

Export buttons are always `variant="outline"` with a `Download` icon
(`h-4 w-4 mr-2`), swapped for a spinning `Loader2` while in flight.
Reference: `pages/SeoReports.tsx:262`, `pages/Citations.tsx:314`.

---

## 5. Typography

- `font-inter` is applied globally on `body` and headings (`index.css:151,158`).
  Only add the class where a specific element would otherwise inherit something
  else. **Never `font-mono`** — nothing in the app uses it.
- Numbers that sit in a column: add `tabular-nums` so digits align.
- Utility classes live in `index.css`: `gradient-primary`, `gradient-secondary`,
  `gradient-subtle`, `shadow-glow`, `animate-fade-in`, `animate-shimmer`.

---

## 6. Tables

```tsx
<div className="rounded-md border border-border">
  <Table>
    <TableHeader>…</TableHeader>
    <TableBody>
      <TableRow className="cursor-pointer transition-colors hover:bg-muted/50">
```

Row hover `hover:bg-muted/50`; add `cursor-pointer` only when the row navigates.

---

## 7. Loading and empty states

```tsx
{/* loading */}
<div className="flex flex-col items-center justify-center py-32">
  <Loader2 className="h-10 w-10 animate-spin text-primary mb-4" />
  <span className="text-muted-foreground text-sm">Loading …</span>
</div>

{/* empty */}
<div className="py-16 text-center text-muted-foreground text-sm">
  Nothing here yet.
</div>
```

---

## Checklist for a new page

- [ ] Root is `p-8 space-y-8 bg-background animate-fade-in`
- [ ] Stat cards are `p-6 border border-border` with a token-tinted icon, no inner panel
- [ ] Stat grid is `grid-cols-1 md:grid-cols-4 gap-6`
- [ ] `TabsList` has `bg-muted/50 p-1 border border-border`, triggers have all three `data-[state=active]:` classes
- [ ] Colour comes from `success` / `destructive` / `primary` / `secondary`, never raw Tailwind colours
- [ ] No `font-mono`; column numbers use `tabular-nums`
- [ ] Loading, empty and error states all present
- [ ] Checked in both light and dark mode
