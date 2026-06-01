# PDCMS App

AI-powered multilingual headless CMS built on Frappe. Content is created and managed in Frappe, AI generates structured JSON from uploaded documents, and Astro consumes the JSON via REST API to render the frontend.

---

## Architecture Overview

```
Content Editor (Frappe Desk)
        │
        ▼
Upload source file (PDF/DOCX) on CMS Page / Blog / Course
        │
        ▼
AI Job auto-queued (frappe.enqueue)
        │
        ▼
ai_generation.py runs in background:
  1. Extract text from PDF/DOCX
  2. Load schema from CMS Template (or use hardcoded default)
  3. Load prompt from CMS Prompt (or use hardcoded default)
  4. Call AI provider (Groq / OpenAI / Claude / Ollama)
  5. Parse JSON response
  6. Save content_json back to doc
        │
        ▼
generation_status → Completed (or Failed — check AI Job Log)
        │
        ▼
Content Editor moves workflow: Draft → Review → Approved → Published
        │
        ▼
Astro frontend fetches content_json via Frappe REST API
        │
        ▼
API Cache serves repeated requests (TTL from CMS Settings)
```

---

## Roles

| Role | Can Do |
|---|---|
| CMS Admin | Full access to everything |
| Content Editor | Create and edit content |
| CMS Reviewer | Review and approve content |
| CMS Publisher | Publish approved content |

---

## Implementation Status

| Component | Status | Notes |
|---|---|---|
| All 10 DocTypes | Done | Fields, validation, controllers all complete |
| `install.py` | Done | Auto-creates roles and default settings on install |
| `slugify` utility | Done | Auto-generates URL slugs from titles |
| `page_permissions.py` | Done | Role-based access on all CMS doctypes |
| `ai_generation.py` | Done | Full pipeline — extract, prompt, AI call, save |
| `ai_job_cleanup.py` | Done | Daily purge of AI Job Log records older than 30 days |
| `cache_cleanup.py` | Partial | Hourly job exists, eviction logic needs improvement |
| `api_cache.py` | Stub | Persistence only — no read/write serving logic yet |
| `public/js/` form files | Missing | 4 JS files referenced in hooks.py don't exist yet |
| Translation provider | Not built | CMS Translation doctype exists, AI job not wired |

---

## Step-by-Step Setup & Usage

### Step 1 — CMS Settings *(one-time, Admin only)*

`Frappe Desk → Search → CMS Settings`

| Field | What to do |
|---|---|
| AI Provider | Choose `Groq` (cloud) or `Ollama` (local) |
| Groq API Key | Paste your Groq API key |
| Groq Model | Default: `llama-3.3-70b-versatile` (leave as-is) |
| OpenAI API Key | Paste if using OpenAI |
| OpenAI Model | Default: `gpt-4o-mini` |
| Claude API Key | Paste if using Claude |
| Claude Model | Default: `claude-sonnet-4-6` |
| Translation Provider | Set to `None` unless multilingual is needed |
| API Cache TTL | Default `300` seconds |
| Rate Limit | Default `60` req/min per IP |

> AI generation will not work until provider + API key is saved here.

---

### Step 2 — CMS Template *(one-time per content type)*

`Frappe Desk → Search → CMS Template → New`

Defines the **structure** AI must output for each content type.
Every CMS Page, Blog, and Course must link to a template.

> **Skip this step to test quickly** — `ai_generation.py` has hardcoded default schemas
> and prompts for Landing Page, Blog, and Course. You can create content without a template first.

| Field | What to enter | Example |
|---|---|---|
| Template Name | Unique name | `Prethive Landing Page` |
| Template Type | Landing Page / Blog / Course / Custom | `Landing Page` |
| Astro Component Reference | Astro component name that renders this | `LandingPageA` |
| Version | Keep as `1.0.0` | `1.0.0` |
| Status | Set `Active` when ready | `Active` |
| Description | What this template is for | `Main landing page layout` |
| Expected JSON Schema | JSON Schema AI must match | *(see below)* |
| SEO Mapping | Maps content_json fields to meta tags | *(see below)* |
| API Slug Prefix | URL prefix Astro uses | `pages` |
| Supported Languages | Comma-separated ISO codes | `en,ta,hi` |

**Landing Page JSON Schema example:**
```json
{
  "type": "object",
  "properties": {
    "hero": {
      "type": "object",
      "properties": {
        "headline":    { "type": "string" },
        "subheadline": { "type": "string" },
        "cta_text":    { "type": "string" },
        "cta_url":     { "type": "string" }
      }
    },
    "features": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "title":       { "type": "string" },
          "description": { "type": "string" },
          "icon":        { "type": "string" }
        }
      }
    },
    "about": {
      "type": "object",
      "properties": {
        "heading": { "type": "string" },
        "body":    { "type": "string" }
      }
    },
    "cta_section": {
      "type": "object",
      "properties": {
        "heading":      { "type": "string" },
        "button_label": { "type": "string" },
        "button_url":   { "type": "string" }
      }
    },
    "seo": {
      "type": "object",
      "properties": {
        "meta_title":       { "type": "string" },
        "meta_description": { "type": "string" }
      }
    }
  }
}
```

**Blog JSON Schema example:**
```json
{
  "type": "object",
  "properties": {
    "intro":    { "type": "string" },
    "sections": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "heading": { "type": "string" },
          "body":    { "type": "string" }
        }
      }
    },
    "conclusion": { "type": "string" },
    "tags": { "type": "array", "items": { "type": "string" } },
    "seo": {
      "type": "object",
      "properties": {
        "meta_title":       { "type": "string" },
        "meta_description": { "type": "string" }
      }
    }
  }
}
```

**SEO Mapping example:**
```json
{
  "meta_title": "seo.meta_title",
  "meta_description": "seo.meta_description"
}
```

---

### Step 3 — CMS Prompt *(optional — hardcoded defaults exist)*

`Frappe Desk → Search → CMS Prompt → New`

Tells the AI **how to generate** content. If no CMS Prompt is configured for a template,
`ai_generation.py` uses built-in default prompts automatically.

| Field | What to enter | Example |
|---|---|---|
| Prompt Key | Unique identifier | `landing_page_generator` |
| Template | Link to CMS Template | `Prethive Landing Page` |
| Section Type | hero / sections / seo / faq / cta / custom | `hero` |
| Sort Order | Run order — lower runs first | `10` |
| Is Active | Must be checked to run | ✓ |
| Prompt Text | AI instruction with `{content}` and `{schema}` placeholders | *(see below)* |
| Temperature | 0.0 (focused) → 2.0 (creative) | `0.3` |
| Max Tokens | Max response length | `8192` |

**Prompt Text example:**
```
You are a professional web content strategist.

Read the following document and generate a complete landing page JSON.

Document:
{content}

Output JSON matching this schema exactly:
{schema}

Rules:
- hero.headline: punchy, max 10 words
- features: extract 3-5 key features from the document
- seo.meta_title: max 60 characters
- seo.meta_description: max 160 characters
- Return ONLY valid JSON, no explanation, no markdown.
```

---

### Step 4 — CMS Page / CMS Blog / CMS Course *(content creation)*

`Frappe Desk → Search → CMS Page → New`

| Field | What to enter |
|---|---|
| Title | Page/blog/course title |
| Slug | Auto-generated from title — editable |
| Template | Link to a CMS Template (optional — defaults apply if blank) |
| Workflow State | Starts as `Draft` |
| Source File | Upload PDF or DOCX — triggers AI generation on save |
| Content JSON | Auto-filled by AI — can also be manually written |
| Meta Title / Description | SEO fields |
| OG Image | Social share image |

**What happens after saving with a source file:**
```
Save → AI job queued → background worker runs → generation_status updates:
  Queued → Extracting → Generating → Completed
                                   → Failed (check AI Job Log)
```
- On `Completed`: `content_json` is populated, ready for review
- On `Failed`: check `ai_error_log` field on the doc, or open AI Job Log for full trace

**Workflow progression:**
```
Draft → Review → Approved → Published → Archived
```
- **Content Editor** creates in Draft, edits content
- **CMS Reviewer** reviews and moves to Approved
- **CMS Publisher** moves to Published — content is now live
- Astro can fetch once Published

---

### Step 5 — CMS Media *(optional)*

`Frappe Desk → Search → CMS Media → New`

| Field | What to enter |
|---|---|
| Title | Descriptive name |
| Media Type | Image / Document / Video / Other |
| File URL | Upload the file |
| CDN URL | Paste CDN URL if hosted externally — takes priority over File URL |
| Alt Text | Image accessibility description |
| Tags | Comma-separated search tags |

Reference the `cdn_url` or `file_url` inside `content_json` when Astro needs to render images.

---

### Step 6 — CMS Translation *(optional, multilingual)*

`Frappe Desk → Search → CMS Translation → New`

| Field | What to enter |
|---|---|
| Reference Doctype | CMS Page / CMS Blog / CMS Course |
| Reference Name | The specific content record to translate |
| Language | ISO 639-1 code — `ta`, `hi`, `fr`, `de` |
| Status | Starts as `Pending` — auto-updates |

On completion, `translated_json` holds the translated version of `content_json`.
Astro fetches it by passing `?lang=ta` on the API call.

> Translation job execution is not yet wired — `translated_json` must be filled manually for now.

---

### Step 7 — AI Job Log *(monitor background jobs)*

`Frappe Desk → Search → AI Job Log`

| Field | Meaning |
|---|---|
| Reference Doctype / Name | Which content triggered this job |
| Job Type | Generate / Translate / Bulk |
| Status | Queued → Running → Completed / Failed |
| AI Provider | Which AI provider was used |
| Duration Seconds | How long the job took |
| Prompt Snapshot | The exact prompt sent to AI |
| Raw Response | Full AI response |
| Error Trace | Full error if status is Failed |

**Debugging a failed job:**
1. Open AI Job Log → read `Error Trace`
2. Common causes: wrong API key, file not found, AI returned invalid JSON
3. Fix the issue → re-save the content doc → new job queued automatically

---

### Step 8 — API Cache *(automatic)*

`Frappe Desk → Search → API Cache`

Populated automatically. Cleared when content is updated or published.
TTL controlled by `api_cache_ttl` in CMS Settings (default 300 seconds).

Only interact with this to manually delete a stuck cache entry.

---

## Hardcoded Defaults in ai_generation.py

If no CMS Template schema or CMS Prompt is set, these defaults are used automatically:

| Content Type | Default schema sections | Default prompt behaviour |
|---|---|---|
| Landing Page | hero, features, about, cta_section, seo | Extracts headline, features list, CTA, SEO tags |
| Blog | intro, sections[], conclusion, tags[], seo | Structures into intro → body sections → conclusion |
| Course | overview, objectives[], modules[], seo | Breaks into modules with lesson lists |

---

## Astro Integration

Frappe exposes content via REST API:

```
GET https://<site>/api/resource/CMS Page/<name>
GET https://<site>/api/resource/CMS Blog/<name>
GET https://<site>/api/resource/CMS Course/<name>
```

`content_json` is the structured data Astro renders.
`template.astro_component` tells Astro which component to use.

```js
const res = await fetch(`${FRAPPE_URL}/api/resource/CMS Page/${slug}`)
const { data } = await res.json()
const contentJson = JSON.parse(data.content_json)
const Component = componentMap[data.astro_component]
// render Component with contentJson
```

---

## File Structure

```
pdcms_app/
  hooks.py                        — app config, scheduled jobs, permissions
  install.py                      — creates roles + default settings on install
  utils/
    slugify.py                    — URL slug generator (used by Page, Blog, Course)
  jobs/
    ai_generation.py              — full AI pipeline: extract → prompt → call AI → save JSON
    ai_job_cleanup.py             — daily purge of AI Job Log records older than 30 days
    cache_cleanup.py              — hourly cache eviction (partial — needs improvement)
  cms/
    permissions/
      page_permissions.py         — role-based access control for all CMS doctypes
  pdcms/                          — Frappe module
    doctype/
      cms_settings/               — global singleton: AI provider, keys, cache TTL
      cms_template/               — content structure + JSON schema + SEO mapping
      cms_prompt/                 — AI prompt templates per section
      cms_page/                   — landing pages
      cms_blog/                   — blog posts
      cms_course/                 — courses
      cms_media/                  — media asset library
      cms_translation/            — multilingual translation records
      ai_job_log/                 — background job state tracking
      api_cache/                  — API response cache records
```

---

## What's Left to Build

| Item | Priority | Impact |
|---|---|---|
| `public/js/cms_page.js` etc — 4 form JS files | Medium | Custom buttons on Frappe forms (e.g. manual re-trigger generation) |
| `cache_cleanup.py` — fix eviction by `expires_at` | Low | Old API Cache records not cleaned up properly |
| `api_cache.py` — read/write serving logic | Medium | Cache not actually serving Astro yet |
| Translation job execution | Medium | `translated_json` must be filled manually for now |
| Astro frontend | High | Nothing renders until Astro consumes the API |
