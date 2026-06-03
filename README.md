# PDCMS App

AI-powered template-driven headless CMS built on Frappe. Two distinct roles drive the system — a Template Administrator who builds reusable templates, and a CMS User who generates website content from those templates using AI.

---

## Two-Role Architecture

```
ROLE 1: Template Administrator          ROLE 2: CMS User
────────────────────────────            ────────────────────────────
Creates and manages templates           Creates website pages/blogs/courses
Defines JSON schema                     Selects a template
Writes AI prompt                        Uploads content document
Uploads Astro/HTML template file        Generates JSON via AI
Publishes template                      Reviews and edits content
                                        Previews rendered page
                                        Publishes live
```

---

## Full System Flow

```
ADMINISTRATOR SIDE
──────────────────
1. CMS Settings → set AI provider + API key (one-time)
2. CMS Template → New → name, type, Astro component reference
3. Upload HTML/Astro template file with {{dot.path}} placeholders
4. Paste JSON Schema → defines what AI must output
5. Customize AI prompt (default pre-filled, {content} + {schema} placeholders)
6. Click "Publish Template" → status: Active → visible to CMS users

CMS USER SIDE
─────────────
7.  CMS Page / Blog / Course → New
8.  Enter title, select Active template, attach PDF or DOCX → Save
9.  "Generate Content" appears as primary button → click it
10. Yellow spinner banner + auto-poll every 4s (no manual refresh needed)
11. Page auto-reloads on completion → green banner confirms success
12. Review content_json field → edit directly if needed → Save
13. Click "Preview" (primary button) → rendered HTML opens in new tab
     Template file + content_json injected via {{dot.path}} placeholders
14. Edit JSON → Save → Preview again — unlimited iterations
15. Workflow: Draft → Review → Approved → Published
16. Astro frontend fetches published content via REST API → renders page

BACKGROUND
──────────
17. AI Job Log tracks every generation — check for errors if generation fails
18. Deleting a Page/Blog/Course also deletes its linked AI Job Log (no warnings)
19. API Cache serves repeated Astro requests (TTL set in CMS Settings)
20. Hourly job evicts expired cache, daily job purges AI Job Logs older than 30 days
```

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
| All AI providers | Done | Groq, OpenAI, Claude, Ollama, HuggingFace |
| Preview engine | Done | `{{dot.path}}` injection into template files |
| Preview API | Done | Opens rendered HTML in browser tab |
| Template API | Done | Serves active templates for picker |
| Form JS buttons | Done | Preview, Generate, Translate on all content forms |
| CMS Template Admin UI | Done | Publish, Deprecate, Validate Schema, Test Preview |
| `cache_cleanup.py` | Partial | Hourly job exists, eviction logic needs improvement |
| `api_cache.py` | Stub | Persistence only — no read/write serving logic yet |
| Translation job | Partial | CMS Translation doctype exists, provider wiring incomplete |
| Astro frontend | Not built | Required to render published content |

---

## Roles

| Role | Can Do |
|---|---|
| CMS Admin | Full access — manages templates, settings, all content |
| Content Editor | Create and edit CMS Page / Blog / Course |
| CMS Reviewer | Review and approve content |
| CMS Publisher | Publish approved content, write on templates |

---

## Step-by-Step: Template Administrator

### Step 1 — CMS Settings *(one-time)*

`Frappe Desk → Search → CMS Settings`

| Field | What to do |
|---|---|
| AI Provider | Choose `Groq` (cloud) or `Ollama` (local) |
| Groq API Key | Paste your key |
| Groq Model | Default: `llama-3.3-70b-versatile` |
| OpenAI / Claude API Key | Paste if using those providers |
| API Cache TTL | Default `300` seconds |

> AI generation will not work until provider + key is saved here.

---

### Step 2 — CMS Template → New

`Frappe Desk → Search → CMS Template → New`

| Field | What to enter | Notes |
|---|---|---|
| Template Name | Unique name | e.g. `Prethive Landing Page` |
| Template Type | Landing Page / Blog / Course / Custom | |
| Astro Component Reference | Astro component name | e.g. `LandingPageA` |
| Status | Leave as `Draft` until ready | |
| Description | What this template is for | |
| Preview Image | Upload a thumbnail | Shown in template picker |

---

### Step 3 — Upload Template File

In the **Template File** section:

- Convert your Figma design to HTML externally (v0, Cursor, AI, manual)
- Add `{{dot.path}}` placeholders where content should appear
- Upload the `.html` or `.astro` file

**Placeholder syntax:**
```html
<h1>{{hero.headline}}</h1>
<p>{{hero.subheadline}}</p>
<a href="{{hero.cta_url}}">{{hero.cta_text}}</a>

<!-- Array item -->
<h3>{{features.0.title}}</h3>
<p>{{features.0.description}}</p>
```

---

### Step 4 — Define JSON Schema

In the **JSON Schema** section, paste the schema that matches your template placeholders:

**Landing Page example:**
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
          "description": { "type": "string" }
        }
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

Click **Validate Schema** button to verify.

---

### Step 5 — Configure AI Prompt

In the **AI Prompt** section, a default prompt is pre-filled:

```
Analyze the uploaded document and generate structured content JSON.

Document text:
{content}

You must output JSON that exactly matches this schema:
{schema}

Rules:
- Return ONLY valid JSON. No explanation, no markdown, no code fences.
- Every field in the schema must be present in your output.
- Keep text concise and professional.
- For SEO fields: meta_title max 60 characters, meta_description max 160 characters.
- Do not generate HTML, CSS, or Astro code — only JSON content values.
```

Customise the prompt for your specific template if needed. `{content}` and `{schema}` are required placeholders.

---

### Step 6 — Test Preview

Click **Test Preview** button:
- A dialog opens with sample JSON auto-generated from your schema
- Edit the sample JSON if needed
- Click Preview → rendered page opens in a new tab
- Verify all placeholders render correctly

---

### Step 7 — Publish Template

Click **Publish Template** button.

- Validates template file and schema are present
- Sets status to `Active`
- Template is now visible to all CMS Users in the template picker

---

## Step-by-Step: CMS User

### Step 1 — Create Content

`Frappe Desk → Search → CMS Page → New` (or CMS Blog / CMS Course)

| Field | What to enter |
|---|---|
| Title | Page title |
| Slug | Auto-generated — editable |
| Template | Select an Active template |
| Source File | Upload PDF or DOCX |

Save the record.

---

### Step 2 — Generate Content

Click **AI → Generate Content** button.

```
generation_status updates:
  Queued → Extracting → Generating → Completed
                                    → Failed (check AI Job Log)
```

On `Completed`: `content_json` field is populated with structured JSON.

---

### Step 3 — Review and Edit

The `content_json` field shows the generated JSON.

- Read through it — check all sections make sense
- Edit directly in the field if anything needs changing
- Save the record

---

### Step 4 — Preview

Click **View → Preview** button.

- Opens a new tab with your template rendered with the generated JSON
- No AI call happens — instant render
- Edit `content_json` → Save → Preview again (unlimited iterations)

---

### Step 5 — Publish

Move workflow state:
```
Draft → Review → Approved → Published
```

- **Content Editor** creates in Draft
- **CMS Reviewer** moves to Approved
- **CMS Publisher** moves to Published — content is now live

Once Published, Astro frontend can fetch and render it.

---

## AI Prompt Priority (how prompt is resolved)

```
1. template.ai_prompt          (set on CMS Template — recommended)
     ↓ if not customised
2. Linked CMS Prompt records   (advanced — multiple prompts per section)
     ↓ if none exist
3. Hardcoded defaults          (built into ai_generation.py — always works)
```

---

## Hardcoded Defaults (built-in fallback)

If no CMS Template or prompt is configured, these defaults are used:

| Content Type | Schema sections | Prompt behaviour |
|---|---|---|
| Landing Page | hero, features, about, cta_section, seo | Extracts headline, features, CTA, SEO |
| Blog | intro, sections[], conclusion, tags[], seo | Structures into intro → sections → conclusion |
| Course | overview, objectives[], modules[], seo | Breaks into modules with lessons |

---

## Template Placeholder Syntax

```html
<!-- Simple string field -->
{{hero.headline}}

<!-- Nested object -->
{{hero.cta_url}}

<!-- Array item by index -->
{{features.0.title}}
{{features.1.description}}
{{steps.0.number}}
{{steps.0.title}}

<!-- SEO -->
{{seo.meta_title}}
{{seo.meta_description}}
```

Unmatched placeholders are left as-is (not replaced).

---

## REST API

### Content endpoints (guest-accessible, for Astro)
```
GET /api/method/pdcms_app.api.v1.pages.get_page?slug=<slug>&lang=en
GET /api/method/pdcms_app.api.v1.pages.get_slugs
GET /api/method/pdcms_app.api.v1.blogs.get_blog?slug=<slug>
GET /api/method/pdcms_app.api.v1.blogs.get_blogs
GET /api/method/pdcms_app.api.v1.courses.get_course?slug=<slug>
GET /api/method/pdcms_app.api.v1.courses.get_courses
```

### Template endpoints (requires login)
```
GET /api/method/pdcms_app.api.v1.templates.get_active_templates
GET /api/method/pdcms_app.api.v1.templates.get_template?name=<name>
POST /api/method/pdcms_app.api.v1.templates.publish_template
```

### Admin endpoints (requires CMS role)
```
POST /api/method/pdcms_app.api.v1.admin.trigger_generation
POST /api/method/pdcms_app.api.v1.admin.trigger_translation
GET  /api/method/pdcms_app.api.v1.admin.get_job_status
```

### Preview endpoints (requires CMS role)
```
GET /api/method/pdcms_app.api.v1.preview.render_page?name=PAGE-0001
GET /api/method/pdcms_app.api.v1.preview.render_blog?name=BLOG-0001
GET /api/method/pdcms_app.api.v1.preview.render_course?name=COURSE-0001
POST /api/method/pdcms_app.api.v1.preview.render_template_test
```

---

## Astro Integration

```js
// Fetch published page by slug
const res = await fetch(`${FRAPPE_URL}/api/method/pdcms_app.api.v1.pages.get_page?slug=${slug}`)
const { data } = await res.json()

// data.content = parsed content_json
// data.template = CMS Template name
// data.seo = SEO fields

// Map template name to Astro component
const Component = componentMap[data.template]
// render Component with data.content
```

---

## File Structure

```
pdcms_app/
  hooks.py                        — app config, scheduled jobs, permissions
  install.py                      — creates roles + default settings on install
  utils/
    slugify.py                    — URL slug generator
  jobs/
    ai_generation.py              — full AI pipeline: extract → prompt → call AI → save JSON
    ai_job_cleanup.py             — daily purge of AI Job Log records older than 30 days
    cache_cleanup.py              — hourly cache eviction (partial)
  cms/
    permissions/
      page_permissions.py         — role-based access for all CMS doctypes
    services/
      preview_engine.py           — renders template file with {{dot.path}} injection
      cache_service.py            — Redis-based API response caching
      document_extractor.py       — PDF/DOCX text extraction
      translation_service.py      — translation job orchestration
    workflows/
      publish.py                  — publish/archive workflow handlers
  pdcms/                          — Frappe module
    doctype/
      cms_settings/               — global singleton: AI provider, keys, cache TTL
      cms_template/               — template: file, schema, prompt, preview image
      cms_prompt/                 — advanced per-section AI prompts
      cms_page/                   — landing pages
      cms_blog/                   — blog posts
      cms_course/                 — courses
      cms_media/                  — media asset library
      cms_translation/            — multilingual translation records
      ai_job_log/                 — background job state tracking
      api_cache/                  — API response cache records

ai/
  providers/                      — Groq, OpenAI, Claude, Ollama, HuggingFace
  generators/content_generator.py — template-driven multi-prompt generation
  validators/schema_validator.py  — JSON schema validation + LLM response parsing
  translators/                    — pluggable translation providers

api/
  v1/
    pages.py                      — guest page endpoints
    blogs.py                      — guest blog endpoints
    courses.py                    — guest course endpoints
    templates.py                  — template picker + publish endpoints
    admin.py                      — generation/translation trigger endpoints
    preview.py                    — preview render endpoints
  response.py                     — standard response envelope

public/js/
  cms_template.js                 — admin UI: publish, validate, test preview
  cms_page.js                     — user UI: generate, preview, translate
  cms_blog.js                     — user UI: generate, preview
  cms_course.js                   — user UI: generate, preview

utils/
  slugify.py                      — text-to-slug utility
  logger.py                       — frappe logger wrappers
```

---

## What's Left to Build

| Item | Priority | Impact |
|---|---|---|
| Astro frontend — consumes API and renders templates | High | Nothing visible to end users until this is built |
| Schema-driven form editor — edit content fields individually instead of raw JSON | Medium | Better CMS User experience |
| `api_cache.py` — read/write serving logic | Medium | API caching not serving Astro yet |
| `cache_cleanup.py` — fix TTL-based eviction | Low | Old records not cleaned up properly |
| Translation provider implementation (DeepL, Google) | Low | Multilingual not working end-to-end |
