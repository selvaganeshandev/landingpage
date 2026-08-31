# Image Generation — Portable Feature Spec

Everything that happens from the moment a user clicks **Image prompt** to the
moment a rendered image is inserted into the article.

This document is written to be implemented in a **different application**. It
describes behaviour, prompts, request shapes, and the reasoning behind each
decision — not this repo's file layout. Where a real file is referenced it is
only as a worked example.

---

## 1. The core idea: two models, two stages

The single most important design decision is that **image generation is two
separate model calls, not one**:

```
   user selects text / opens featured image
                  │
                  ▼
   ┌──────────────────────────────┐
   │  STAGE 1 — PROMPT WRITING    │   a TEXT model (Claude / GPT / Gemini)
   │  article context + style     │   turns messy article prose into one
   │        ↓                     │   vivid, self-contained image prompt
   │  one 2-4 sentence prompt     │
   └──────────────────────────────┘
                  │  user can EDIT the prompt here
                  ▼
   ┌──────────────────────────────┐
   │  STAGE 2 — RENDERING         │   an IMAGE model (Gemini image / gpt-image)
   │  prompt → pixels             │
   └──────────────────────────────┘
                  │
                  ▼
   save bytes → public URL → insert into article
```

**Why two stages.** Image models are bad at reading a 2,000-word article and
deciding what matters. Text models are good at exactly that. Splitting them also
gives the user an editable prompt in the middle, which is where almost all of the
perceived quality comes from — people tweak one clause and re-render.

Do not collapse these into one call. The editable middle step is the feature.

---

## 2. The UI contract

One modal, two variants, driven by a single piece of state: `prompt` is either
`null` (not generated yet) or a string.

### Inputs shown to the user

| Field | Type | Required | Notes |
|---|---|---|---|
| **Selected text** | read-only display | yes (selection variant) | The passage the image should illustrate. Shown so the user knows what the image is *about*. |
| **Additional details** | free text, max ~500 chars | no | e.g. *"include our logo, set it at night, focus on the laptop screen"*. Treated as **required instructions**, not hints. |
| **Illustration style** | one of 6, single-select | yes, defaults to first | See table below. |
| **Use brand colors** | checkbox | no | Disabled entirely when the project has no palette. |

### The 6 illustration styles

The user picks a `value`; the label/hint are display only; the `description` is
what actually goes into the prompt. Keep all three separate — the description is
far too verbose for a button, and the label is far too thin for a model.

| value | Label | Hint (UI) | Description (sent to the model) |
|---|---|---|---|
| `realistic` | Realistic | Photorealistic, high detail | photorealistic rendering, natural lighting, fine detail, as if shot on a high-end camera |
| `real-world` | Real world | Candid photograph | a genuine candid photograph of a real scene or setting, documentary style, unposed |
| `cartoon` | Cartoonic | Bold, flat cartoon | flat cartoon illustration, bold clean outlines, vibrant simplified colors, playful and friendly |
| `animation` | 3D animation | Pixar-style render | Pixar-style 3D animated render, soft global illumination, rounded stylized forms |
| `watercolor` | Watercolor | Hand-drawn, painterly | artistic watercolor illustration, visible brush texture, soft color bleeds, hand-drawn feel |
| `flat-design` | Flat design | Minimal vector illustration | modern flat vector illustration, minimal geometric shapes, limited restrained color palette |

### Brand-colors default behaviour (worth copying)

A brand palette fights a photograph. So the checkbox **defaults itself based on
the chosen style**:

- Photographic styles (`realistic`, `real-world`) → default **off**
- Everything else → default **on** (if a palette exists)

It follows the style until the user touches the checkbox themselves; after that
their choice sticks. Implement with a "touched" flag:

```
onStyleChange(next):
    style = next
    if (!userTouchedTheCheckbox):
        useBrandColors = hasPalette && !isPhotographic(next)

onCheckboxChange(value):
    userTouchedTheCheckbox = true
    useBrandColors = value
```

### Button states

| Condition | Visible |
|---|---|
| `prompt === null` | **Generate prompt** only |
| `prompt !== null` | prompt textarea (editable) + **Generate image** + **Regenerate prompt** |
| `imageUrl !== null` | image preview + **Save image** (download) + **Insert into article** / **Save as featured image** |

> **Trap worth avoiding.** In the reference implementation the *Generate image*
> button is rendered only when `prompt !== null`. That means if the text model is
> unavailable, the user cannot reach the renderer **even with a working image
> key**. If you want the render step usable independently, show the prompt
> textarea and the Generate image button from the start, pre-filled empty.

### The two variants

| | `selection` | `featured` |
|---|---|---|
| Context sent | the exact selected passage | article summary (meta description, else the brief, else the title) |
| Final action | insert image at the selection point | save as the article's featured image |
| Prompt framing | "illustrate this passage" | "represent the whole piece" |

---

## 3. Configuration the feature needs

```jsonc
{
  // Stage 1 — text model
  "textProvider": "claude" | "openai" | "auto",
  "claudeApiKey":  "encrypted",
  "openAiApiKey":  "encrypted",

  // Stage 2 — image model
  "imageProvider": "gemini" | "openai",
  "geminiApiKey":  "encrypted",

  // Optional
  "brandColors": ["#065ff0", "#1b1b1b", "#f5a623"]  // primary, secondary, accents…
}
```

Store keys **encrypted at rest** (AES-256-GCM is what the reference uses:
random 12-byte IV, auth tag, `iv.tag.ciphertext` base64-joined). Keep a
`last4` alongside so the UI can show a mask without decrypting.

**Choose the image provider per project, not per image.** Because Stage 1 writes
a prompt *for a specific image model*, the choice must be known before the prompt
is written. A per-image toggle means the prompt was already written for the wrong
target.

---

## 4. API surface

Three endpoints. All scoped to a project + article and behind auth.

### 4.1 `POST /articles/:id/image-prompt` — Stage 1 (selection)

```jsonc
// request
{
  "selectedText": "how to style graphic tees",   // required, 1..~5000
  "style": "realistic",                          // required, one of the 6
  "additionalInstructions": "include our logo",  // optional, max 500
  "useBrandColors": true                         // optional, default false
}
// 200
{ "prompt": "A close-up, photorealistic shot of … -ar:16:9" }
```

### 4.2 `POST /articles/:id/featured-image-prompt` — Stage 1 (featured)

Same, minus `selectedText` — the server derives context from the article itself.

### 4.3 `POST /articles/:id/generate-image` — Stage 2

```jsonc
// request
{
  "prompt": "A close-up, photorealistic shot of …",  // the possibly-EDITED prompt
  "useBrandColors": true
}
// 200
{ "url": "/uploads/3b82e316-….png" }
```

**Error codes**

| Code | When |
|---|---|
| `400` | no API key for the selected provider — name which key to add |
| `404` | article not found / not owned by caller |
| `502` | upstream model error — pass the provider's own message through, it is usually actionable (quota, rejected prompt, bad key) |

---

## 5. Stage 1 — writing the prompt

This is the highest-value part of the feature. The template below is the whole
thing.

### 5.1 The template

```
You are a prompt engineer writing image-generation prompts for {TARGET_MODEL},
to illustrate a blog post titled "{ARTICLE_TITLE}"{ (target keyword: "{KEYWORD}")}.

{CONTEXT_INTRO}
"""
{CONTEXT_TEXT}
"""

Desired visual style: {STYLE_LABEL} — {STYLE_DESCRIPTION}

{PALETTE_BLOCK}
{ADDITIONAL_INSTRUCTIONS_BLOCK}

Write ONE detailed, vivid image-generation prompt (2-4 sentences) that:
- {CAPTURE_INSTRUCTION}
- Fully commits to the "{STYLE_LABEL}" style described above
- {INCORPORATE_INSTRUCTIONS_BULLET}
- Specifies composition, lighting, mood, and color palette{PALETTE_TAIL}
- {TEXT_RULE}
- Is written as a single, ready-to-paste prompt — no headings, no bullet points,
  no surrounding quotes, no explanation, no preamble

Output ONLY the prompt text.
```

Model params: `max_tokens: 500`, no system prompt, single user message.

### 5.2 The slots

**`{TARGET_MODEL}`** — name the actual renderer:
- Gemini → `Google's "Nano Banana" (Gemini) image model`
- OpenAI → `OpenAI's "gpt-image-1" image model`

**`{CONTEXT_INTRO}`**
- selection → `Here is the exact passage from the article this image should illustrate:`
- featured → `This image will be used as the article's featured/cover image — it should represent the piece as a whole, not one specific detail. Here is a summary of the article:`

**`{CAPTURE_INSTRUCTION}`**
- featured → `Captures the overall theme and core idea of the article as a whole (the underlying idea, not literal wording)`
- selection →
  ```
  Captures the core scene, subject, or concept behind the passage above (the
  underlying idea, not the literal wording). If the passage is abstract or
  technical (e.g. software, infrastructure, business process) with nothing
  literally visual in it, depict its concrete real-world subject matter directly
  — e.g. servers, code on a screen, a dashboard, people at work — rather than
  inventing an unrelated metaphor or symbolic scene
  ```
  That last clause exists because abstract passages otherwise produce glowing
  orbs and floating cubes. It is the single highest-impact sentence in the
  template.

**`{PALETTE_BLOCK}`** — only when brand colors are on:
```
Brand color palette — the image must be built around these exact hex colors:
{#p} as the dominant color, {#s} as the supporting color, {#a1}, {#a2} as accents used sparingly.
Name them explicitly in the prompt and keep any other colors neutral so the image reads as on-brand.
```

**`{PALETTE_TAIL}`** — appended to the composition bullet when colors are on:
` — state the brand hex colors ({comma-joined}) directly in the prompt and describe where each one appears`

**`{ADDITIONAL_INSTRUCTIONS_BLOCK}`** — when the user typed something:
```
Additional instructions from the user — treat these as required, not optional: {TEXT}
```
Note *required, not optional*. Without that, models routinely ignore it.

### 5.3 `{TEXT_RULE}` — the fiddliest part

Rendered text in images is the most common quality complaint. Three cases:

**No additional instructions** (the default — keep text out):
```
Is safe and appropriate for a professional blog, and does not ask for any
text/words/letters to be rendered in the image
```

**User asked for something, renderer is OpenAI** (renders text reliably):
```
Is safe and appropriate for a professional blog. Do not ask for text, words, or
letters to be rendered in the image unless the additional instructions above call
for labels, captions, or dialogue — in that case choose the exact strings
yourself, write each one inside double quotes, keep it to at most four words per
string and four strings in total, and close the prompt with "No other text
anywhere in the image."
```

**User asked for something, renderer is Gemini** (garbles text without heavy hedging):
```
Is safe and appropriate for a professional blog. Do not ask for text, words, or
letters to be rendered in the image unless the additional instructions above call
for labels, captions, or dialogue — in that case choose the exact strings
yourself and write each one inside double quotes, at most four words per string
and at most four strings in total, say they must be spelled exactly as written
and rendered crisp and legible, never describe them as placeholder lines, label
bars, or squiggles, and close the prompt with "No other text anywhere in the
image."
```

The rule is *text off by default, but the user's explicit request outranks that*.
Asking for a label and getting placeholder squiggles reads as the request being
ignored.

### 5.4 Aspect ratio

Gemini takes the ratio from a **trailing marker appended to the prompt string**;
it does not reliably honour an in-prose instruction:

```
{generated prompt} -ar:16:9
```

OpenAI takes it as a **request parameter**, so the marker must NOT be appended —
it would be read as literal prompt text.

```
if (imageProvider === "openai") return prompt
else                            return prompt + " -ar:16:9"
```

If you accept prompts from elsewhere, strip any trailing marker before sending to
OpenAI: `prompt.replace(/\s*-ar:\S+\s*$/, "").trim()`

---

## 6. Stage 2 — rendering

The interface is tiny, which is what makes providers swappable:

```
renderImage(apiKey, prompt) -> { mimeType, base64Data }
```

### 6.1 Gemini

```http
POST https://generativelanguage.googleapis.com/v1beta/models/{IMAGE_MODEL}:generateContent?key={API_KEY}
Content-Type: application/json

{
  "contents": [{ "parts": [{ "text": "<prompt>" }] }],
  "generationConfig": {
    "responseModalities": ["IMAGE"],
    "imageConfig": { "aspectRatio": "16:9" }
  }
}
```
Response → `candidates[0].content.parts[].inlineData` → `{ mimeType, data }` (base64).
Output is true **16:9**.

### 6.2 OpenAI

```http
POST https://api.openai.com/v1/images/generations
Authorization: Bearer {API_KEY}
Content-Type: application/json

{
  "model": "gpt-image-1",
  "prompt": "<prompt, -ar marker stripped>",
  "size": "1536x1024",
  "n": 1
}
```
Response → `data[0].b64_json`. **No mime type is returned** — it is always PNG,
so hardcode `image/png`. Output is **3:2**, not 16:9 (1536×1024 is the widest
landscape offered).

### 6.3 Provider differences that will bite you

| | Gemini | OpenAI |
|---|---|---|
| Aspect ratio | 16:9 via config | 3:2 via `size` |
| `-ar:16:9` marker | required | must be stripped |
| Mime type returned | yes | no — assume PNG |
| Text rendering | weak, needs hedging | strong |
| Speed | fast | ~40–55s per image |
| Cost | low | higher |
| Free tier | **image quota is often 0** — see below | pay-as-you-go |

> **Real-world gotcha.** A Google free-tier key returns `429` with
> `limit: 0, model: gemini-*-image`. The key is valid and text generation works
> fine — image generation simply has no free allowance and requires billing on
> the Cloud project. Surface the provider's message verbatim or users will think
> your app is broken.

### 6.4 Always set a timeout

Neither API streams. A stalled connection otherwise holds a request handler open
forever. **180 seconds** is a sane ceiling for both.

---

## 7. Applying brand colors at render time

Brand colors are applied **twice**, deliberately:

1. **Stage 1** — the prompt writer is told to name the hex codes in its output
2. **Stage 2** — a palette instruction is appended again to the final prompt

The second pass survives the user editing the prompt by hand.

```
appendBrandColors(prompt, colors):
    if colors is empty: return prompt

    parts = ["{primary} as the dominant color"]
    if secondary: parts += "{secondary} as the supporting color"
    if accents:   parts += "{accents joined} as accents used sparingly"

    instruction = "Use this brand color palette: " + join(parts, ", ")
                + ". Keep every other color neutral."

    // The -ar marker must stay LAST if present
    if prompt ends with an -ar marker:
        return prompt_without_marker + "\n\n" + instruction + marker
    return prompt + "\n\n" + instruction
```

Keeping the marker last matters — Gemini reads it positionally.

---

## 8. Storage and insertion

**Save.** Decode base64 → write to disk (or object storage) under a random UUID
filename with an extension derived from the mime type → return a **relative
public URL** (`/uploads/{uuid}.png`).

Map only known types; default to `.png` on anything unexpected:
`image/png→png, image/jpeg→jpg, image/webp→webp, image/gif→gif`

Return a relative URL, not absolute — it survives domain changes and works behind
a proxy.

**Insert (selection variant).** Place the image node at the **end** of the
original selection range, and derive `alt` text from the nearest heading above
the selection, falling back to the article title. Never leave `alt` empty — these
are blog images and it is an accessibility and SEO regression.

**Insert (featured variant).** Persist the URL to the article record.

**Persistence warning.** Generated images live outside your database. If you
publish elsewhere (a CMS), upload a copy at publish time — otherwise losing the
uploads volume 404s every image in every unpublished draft.

---

## 8.1 Saving the image to the user's computer

Once an image has rendered, the user must be able to **download it to their own
machine** — independently of whether they insert it into the article. People want
the asset for social posts, decks, and re-use elsewhere.

### Required behaviour

| | |
|---|---|
| **When it appears** | As soon as an image has rendered — alongside the preview |
| **Label** | `Save image`, with a download icon |
| **On click** | The browser's own download flow saves the file to the user's Downloads folder |
| **Independent of** | Insert / Save-as-featured. Downloading must not close the modal, clear the image, or count as "using" it — the user can download **and then** insert. |
| **Repeatable** | Clicking twice saves twice. No state to manage. |

### Implementation

Do **not** use a plain `<a href={imageUrl} download>`. The `download` attribute is
ignored cross-origin, and the browser navigates to the image instead of saving
it. Fetch the bytes and hand the browser a blob:

```js
async function saveImageToDisk(imageUrl, filename) {
  const res = await fetch(imageUrl);
  if (!res.ok) throw new Error("Couldn't fetch the image to save it.");
  const blob = await res.blob();

  // Trust the blob's own mime type for the extension — the renderer decides
  // the format, not the caller.
  const extension = blob.type.split("/")[1] ?? "png";

  const blobUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = blobUrl;
  link.download = `${filename}.${extension}`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(blobUrl);  // always revoke, or the blob leaks for the page's lifetime
}
```

Four details that matter:

1. **`URL.revokeObjectURL`** — without it, every download leaks the full image
   into memory until the page is reloaded.
2. **`document.body.appendChild`** before `.click()` — some browsers ignore a
   click on a detached anchor.
3. **Extension from `blob.type`**, not from a constant. OpenAI returns PNG,
   Gemini may return something else; a wrong extension makes the user's OS open
   the file with the wrong app.
4. **Wrap in try/catch** and show a visible error. A failed fetch otherwise looks
   like a dead button.

### Filename — do better than the reference

The reference implementation hardcodes:

```js
link.download = `nano-banana-image.${extension}`;   // <- don't copy this
```

Two problems: it leaks the vendor's model codename into the user's Downloads
folder, and every image saves under the **same name**, so the OS appends
`(1)`, `(2)`, `(3)`... and the user cannot tell them apart.

Derive something meaningful instead:

```js
const slug = (articleTitle || "image")
  .toLowerCase()
  .replace(/[^a-z0-9]+/g, "-")
  .replace(/^-|-$/g, "")
  .slice(0, 60);

const filename = `${slug}-${Date.now()}`;  // how-to-style-graphic-tees-1735300000000
```

Article slug plus a timestamp keeps files sorted, self-describing, and
collision-free.

### Discoverability — also worth changing

In the reference, the Save button is **only visible on hover** over the image (an
overlay that fades in). It looks clean, and it is easy to miss entirely — users
do not know the option exists. Prefer a persistent button under the preview, next
to Insert:

```
+-----------------------------+
|          [ preview ]        |
+-----------------------------+
  [ Save image ]  [ Insert into article ]
```

Keep the hover overlay too if you like it, but do not let it be the only
affordance.

### One environment caveat

Sandboxed contexts — some embedded viewers, strict CSP frames, certain in-app
browsers — **block script-initiated downloads**, blob URLs included. If your app
can run inside one, also expose the image's plain URL so the user can
right-click and *Save image as...* as a fallback.

---

## 9. Minimum viable port

If you want the smallest thing that works, in order:

1. **Stage 2 only** — a prompt textarea, a render button, one provider.
   Genuinely useful on its own.
2. **Add Stage 1** with a fixed style. This is where the quality jump is.
3. **Add the 6 styles.** Cheap — it is a lookup table plus one template slot.
4. **Add additional instructions** + the text rules.
5. **Add brand colors.**
6. **Add the second provider.** Only worth it once one is working end to end.

Steps 1–2 are perhaps a day. Everything after is incremental.

## 10. Checklist of the non-obvious decisions

- [ ] Two model calls, with an **editable prompt** between them
- [ ] Prompt writer is told **which image model** it is writing for
- [ ] `-ar` marker appended for Gemini, stripped for OpenAI
- [ ] Text-in-image **off by default**, user request overrides, hedging tuned per renderer
- [ ] Abstract passages → depict **concrete subject matter**, not metaphor
- [ ] Brand colors default **off** for photographic styles, until the user chooses
- [ ] Brand colors applied at **both** stages
- [ ] Additional instructions framed as **required, not optional**
- [ ] Provider chosen **per project**, before the prompt is written
- [ ] 180s timeout on both renderers
- [ ] Upstream error messages passed through verbatim
- [ ] **Save image** button downloads via blob + revokes the object URL
- [ ] Download filename derived from the article slug, not a constant
- [ ] `alt` text derived from the nearest heading
- [ ] Image bytes copied to the CMS at publish time
