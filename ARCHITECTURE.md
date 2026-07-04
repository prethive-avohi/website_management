# Paideia CMS — Architecture

AI-powered, template-driven headless CMS built on Frappe Framework, serving a statically-built Astro frontend on Vercel.

---

## Table of Contents

1. [What Is This System](#1-what-is-this-system)
2. [The Two Roles](#2-the-two-roles)
3. [How a Piece of Content Becomes a Live Page](#3-how-a-piece-of-content-becomes-a-live-page)
4. [System Architecture](#4-system-architecture)
5. [Frontend Architecture (Astro)](#5-frontend-architecture-astro)
6. [What the Frontend Needs to Be Fully CMS-Connected](#6-what-the-frontend-needs-to-be-fully-cms-connected)
7. [DocTypes Reference](#7-doctypes-reference)
8. [AI Generation Pipeline](#8-ai-generation-pipeline)
9. [API Reference](#9-api-reference)
10. [CMS File Structure](#10-cms-file-structure)
11. [Frontend File Structure (`fe/`)](#11-frontend-file-structure-fe)
12. [Background Jobs](#12-background-jobs)
13. [Roles and Permissions](#13-roles-and-permissions)
14. [Implementation Status](#14-implementation-status)
15. [Local Setup](#15-local-setup)
16. [Deploying to Vercel](#16-deploying-to-vercel)

---

## 1. What Is This System

Two independent parts that work together:

| Part | What it is | Where it runs |
|---|---|---|
| **Paideia CMS** | Frappe app — content creation, AI generation, editorial workflow, REST API | Frappe bench (EC2 or Frappe Cloud) |
| **Paideia Frontend** | Astro site — statically pre-built HTML, served from CDN | Vercel |

**The connection:** At build time, Astro calls Frappe's guest REST API to fetch all published content, pre-renders it to HTML files, and Vercel serves those files from its CDN. At runtime, there is no connection — the live site makes zero calls to Frappe.

---

## 2. The Two Roles

| Role | What they do |
|---|---|
| **Template Administrator** | Creates CMS Templates: defines the JSON schema AI must produce, writes the AI prompt, sets the `astro_component` name that maps to the frontend renderer, publishes |
| **Content Editor / Publisher** | Creates CMS Page / Blog / Course: selects a template, uploads a PDF/DOCX/XLSX/TXT source document, triggers AI generation, reviews content_json, moves through the editorial workflow (Draft → Review → Approved → Published) |

---

## 3. How a Piece of Content Becomes a Live Page

```
STEP 1 — Create content in Frappe Desk
  Editor: New CMS Course → set title, institution (uws/presidency),
          study_level (Undergraduate/Postgraduate/…), template, slug → Save

STEP 2 — AI generates the content
  Editor: AI menu → "Generate Content"
  Frappe: enqueues background job
  Job: extracts text from source PDF → sends to Agent Service → Agent calls AI
  Agent: webhooks back to Frappe → content_json saved → generation_status = Completed
  Frappe Desk: auto-reloads, green banner, content_json is now filled

STEP 3 — Editorial review
  Reviewer inspects content_json, may edit directly
  Workflow: Draft → Review → Approved → Published
  (If translation needed: AI menu → "Translate" → sets up CMS Translation records
   per language; those also go through their own Draft→Published workflow)

STEP 4 — Publish triggers a Vercel deploy
  on_update() detects workflow_state changed to "Published"
  cms/services/deploy_trigger.py → debounced POST to Vercel deploy hook URL
  (max 1 trigger per 60 seconds — batches rapid publishes into one build)

STEP 5 — Vercel builds the Astro site
  scripts/prebuild.mjs runs first:
    → fetches active CMS Redirects from get_redirects API
    → writes src/generated/cms-redirects.json

  astro build runs:
    getStaticPaths() in course/blog routes calls get_published_pages API
    → returns ALL currently Published content (courses + blogs + pages)
    → merged with local markdown files (CMS wins for same slug)
    → one HTML file pre-built per page

  If bench unreachable at build time → cms.ts returns null/[] → markdown
  content only → build still succeeds (graceful fallback, never crashes)

STEP 6 — Live on CDN in ~2 minutes
  Vercel deploys dist/ to edge CDN
  paideia.global/en/uws/postgraduate/new-course → serves pre-built HTML
  Zero calls to Frappe at runtime — pure CDN delivery
```

---

## 4. System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  FRAPPE DESK  (Admin / Content Editor / Reviewer)                   │
│  CMS Template · CMS Page · CMS Blog · CMS Course · CMS Translation  │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ frappe.enqueue("Generate Content")
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  FRAPPE BACKGROUND JOB  jobs/ai_generation.py                       │
│  Extract PDF/DOCX/XLSX/TXT → prepare prompt → POST to Agent Service │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ HTTP POST /api/v1/generate (X-Agent-Secret)
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  AGENT SERVICE  aiAgents/paideia-agents  (separate FastAPI process) │
│  Calls AI provider (Groq/OpenAI/Claude/Ollama/HuggingFace)         │
│  Sends step / completed / failed webhooks back to Frappe            │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ webhook POST → api/v1/agent_callback.py
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  FRAPPE  content_json saved · generation_status = Completed         │
│  Editor reviews → workflow_state = Published                        │
│  deploy_trigger.py → debounced POST to Vercel deploy hook URL       │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ POST (hook URL is the secret)
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  VERCEL  — triggers Astro build                                     │
│                                                                     │
│  1. node scripts/prebuild.mjs                                       │
│       → GET .../redirects.get_redirects                             │
│       → writes src/generated/cms-redirects.json                     │
│                                                                     │
│  2. astro build                                                     │
│       getStaticPaths() → GET .../registry.get_published_pages       │
│       + getCollection('courses') + getCollection('blog')            │
│       per slug → GET .../courses.get_course (or blog/page)         │
│       → renders content_json through matching Astro component       │
│       → writes dist/client/en/.../index.html per page               │
│                                                                     │
│  3. astro.config.mjs injects cms-redirects.json as Vercel           │
│     redirect rules → old slugs 301 to new slugs at CDN level        │
│                                                                     │
│  4. dist/ deployed to Vercel edge CDN — site is live                │
└─────────────────────────────────────────────────────────────────────┘

RUNTIME (no Frappe involved):
  User visits paideia.global → Vercel CDN → serves pre-built HTML
  Contact form → /api/contact (Vercel serverless) → proxies to Frappe
```

---

## 5. Frontend Architecture (Astro)

The frontend is a **hybrid static** Astro site (`output: 'static'`):

- All content pages (courses, blogs, landing pages) → **pre-built HTML** at deploy time
- API routes (contact form, callback form, health) → **server-rendered** on Vercel (kept dynamic via `export const prerender = false`)

### Build-time data flow

```
astro build
  │
  ├── getStaticPaths()  [course and blog dynamic routes]
  │     ├── getPublishedPages()     → Frappe: all Published CMS content
  │     └── getCollection(...)      → local markdown files
  │     → merged paths (CMS wins for same slug)
  │
  └── per path render
        ├── getCmsCourse() / getCmsBlog()   → Frappe: full content_json
        │   if null → getCollection() fallback → markdown data
        └── renders Astro components → static HTML
```

### Hybrid source logic (CMS + Markdown coexist)

Every dynamic route tries CMS first, markdown second:

```typescript
// src/lib/cms.ts — all functions return null on error, never throw
const cmsCourse = await getCmsCourse(institution, level, slug);
if (cmsCourse) {
  // use content_json from Frappe
} else {
  // fall back to local markdown file
}
```

This means:
- **Bench down at build time** → markdown-only build, no crash
- **Course only in markdown** → built from markdown
- **Course only in CMS** → built from CMS
- **Same slug in both** → CMS wins, one HTML page

### URL structure

| Content type | URL pattern | Source fields |
|---|---|---|
| Course | `/en/{institution}/{study_level}/{slug}` | `institution`, `study_level`, `slug` on CMS Course |
| Blog | `/en/blog/{slug}` | `slug` on CMS Blog |
| Page | `/en/{slug}` | `slug` on CMS Page |

### Redirects

When a Published page's slug changes in Frappe, a CMS Redirect record is auto-created.

At build time:
1. `scripts/prebuild.mjs` fetches all active CMS Redirects
2. Writes to `src/generated/cms-redirects.json`
3. `astro.config.mjs` reads this and sets Astro's `redirects` config
4. Vercel converts these to CDN-level 301/302 rules

Old URL → 301 → new URL. Works even after the old HTML page is gone.

### Adapter selection

Set `DEPLOY_TARGET` environment variable:

| Value | Adapter | Use case |
|---|---|---|
| *(unset)* | `@astrojs/node` | Local dev, EC2 |
| `vercel` | `@astrojs/vercel` | Vercel production |
| `amplify` | `astro-aws-amplify` | AWS Amplify |

---

## 6. What the Frontend Needs to Be Fully CMS-Connected

### Already done (in `fe/`)

| What | Where | Status |
|---|---|---|
| CMS API client (`getCmsCourse`, `getCmsBlog`, `getCmsBlogs`, `getPublishedPages`) | `src/lib/cms.ts` | Done |
| Hybrid course route (CMS first, markdown fallback) | `src/pages/en/[institution]/[level]/[slug].astro` | Done |
| Hybrid blog route (CMS first, markdown fallback) | `src/pages/en/blog/[slug].astro` | Done |
| Hybrid blog listing (CMS + markdown merged) | `src/pages/en/blog/index.astro` | Done |
| Redirect wiring (prebuild → astro.config → Vercel CDN rules) | `scripts/prebuild.mjs` + `astro.config.mjs` | Done |
| Static build with server API routes | `output: 'static'` + `prerender: false` on API routes | Done |
| Multi-adapter support | `DEPLOY_TARGET` env var selects node/vercel/amplify | Done |

### Still needed before production

| What | Why | How |
|---|---|---|
| **CMS Course Template schema** | The `content_json` the AI generates must match the shape the course components expect (`hero.courseName`, `about.intro`, `modules.courseModules`, etc.) | Create a CMS Template in Frappe Desk with type=Course and a JSON Schema that matches the component props |
| **CMS Blog Template schema** | Same — `content_json.meta.*` fields drive the blog card and detail view | Create a CMS Template with type=Blog; `meta.title`, `meta.description`, `meta.category`, `meta.author`, `meta.pubDate`, `meta.coverImage`, `content` (HTML string) |
| **Migrate existing markdown content to CMS** | Until content is in Frappe, the CMS path is always empty and markdown serves everything | Create CMS Course/Blog entries for each markdown file; upload brochure PDF → AI generates → review → publish |
| **`PUBLIC_FRAPPE_URL` on Vercel** | Without this, `getPublishedPages()` returns `[]` — only markdown builds | Vercel → Project Settings → Environment Variables → `PUBLIC_FRAPPE_URL=https://your-frappe.com` |
| **Vercel deploy hook wired in CMS Settings** | Without this, publishing in Frappe does not trigger a Vercel rebuild | Vercel → Project → Settings → Git → Deploy Hooks → create → copy URL → Frappe Desk → CMS Settings → Vercel Deploy Hook URL |
| **CMS Translation form JS** | Reviewers have no UI to move translations Draft→Published in Frappe Desk | Create `cms_translation.js` with workflow state buttons |
| **Blog index shows CMS blog counts/categories** | Currently counts only markdown posts visible at build time | Already handled in blog/index.astro — will include CMS once blogs are published |

---

## 7. DocTypes Reference

| DocType | Type | Purpose |
|---|---|---|
| CMS Settings | Single | Global config: AI provider, API keys, agent service URL/secret, cache TTL, Vercel deploy hook URL |
| CMS Template | Standard | Template: HTML file for preview, JSON schema, AI prompt, `astro_component` name (join key to frontend) |
| CMS Prompt | Standard | Advanced per-section AI prompts linked to a template |
| CMS Page | Standard | Landing pages. Fields: title, slug, template, source_file, content_json, workflow_state |
| CMS Blog | Standard | Blog posts. Same fields + blog-specific metadata |
| CMS Course | Standard | Courses. Same fields + `institution` (uws/presidency) + `study_level` (Undergraduate/Postgraduate/Professional/Short Course/Certificate). Both drive the URL: `/en/{institution}/{study_level}/{slug}` |
| CMS Redirect | Standard | Slug redirect records. Auto-created when a Published doc's slug changes. Fields: old_slug, new_slug, redirect_type (301/302), active. Fetched by prebuild script → Vercel CDN rules |
| CMS Media | Standard | Media asset library |
| CMS Translation | Standard | Multilingual content. `status` = AI pipeline (Pending→Completed). `workflow_state` = editorial (Draft→Review→Approved→Published). API only serves `workflow_state=Published` translations. Deploy fires on editorial publish, not AI completion. |
| AI Job Log | Standard | Background job state: Queued → Running → Completed/Failed |
| API Cache | Standard | Redis-backed API response cache records |

---

## 8. AI Generation Pipeline

### Full flow (`jobs/ai_generation.py`)

```
1. frappe.enqueue("Generate Content") → run_page_generation(doc_name)
2. Create AI Job Log (status: Queued)
3. generation_status = "Extracting"
4. _extract_text(source_file):
     PDF  → pdfplumber  (per-page text + tables)
     DOCX → python-docx (paragraphs + tables flattened to pipe rows)
     XLSX → openpyxl    (every sheet, every row)
     TXT  → plain read
5. Smart truncate at 50K chars (paragraph/sentence boundary)
6. Load JSON schema + prompt from CMS Template
7. POST /api/v1/generate to Agent Service:
     { extracted_text, json_schema, prompt, provider, model,
       webhook_url, context: { doctype, doc_name } }
8. Return 202 — Frappe waits for webhook
```

### Webhook callback (`api/v1/agent_callback.py`)

```
Frappe receives: POST /api/method/paideia_cms.api.v1.agent_callback.receive
Auth: X-Agent-Secret header

step      → generation_status = progress message (live updates in Desk)
completed → content_json saved, generation_status = "Completed"
failed    → generation_status = "Failed", ai_error_log set
```

### Why Frappe extracts text (not the agent)

Source files are private Frappe attachments requiring session auth. The agent service has no Frappe session. Frappe extracts locally (no network hop), then sends the much smaller extracted text (~30–40KB) in the request body.

### JSON Schema must be a real schema

`CMS Template.json_schema` must have `type`/`properties` at every level (a proper JSON Schema), not literal example values. A literal document silently disables strict structured-output mode on OpenAI — the AI returns a looser shape and `content_json` fields may be missing.

---

## 9. API Reference

Every endpoint returns: `{ success, data, meta, errors }` wrapped under Frappe's `message` key.

`data` is always `[]` for empty list results (never `{}` — a prior bug where `[] or {}` silently converted empty arrays to objects has been fixed).

### Guest endpoints — no auth required (Astro build-time)

```
# Primary: used in getStaticPaths() — one call returns everything
GET /api/method/paideia_cms.api.v1.registry.get_published_pages
    Returns all Published Pages + Blogs + Courses:
    [{ slug, title, content_type, astro_component, institution, study_level,
       available_languages, updated_at }]

# Redirects: used by prebuild.mjs before every build
GET /api/method/paideia_cms.api.v1.redirects.get_redirects
    Returns all active CMS Redirect records:
    [{ old_slug, new_slug, redirect_type, content_type }]

# Per-content fetch (called per slug during page render)
GET /api/method/paideia_cms.api.v1.pages.get_page?slug=<slug>&lang=en
GET /api/method/paideia_cms.api.v1.blogs.get_blog?slug=<slug>&lang=en
GET /api/method/paideia_cms.api.v1.courses.get_course?slug=<slug>&lang=en
    Returns: { title, slug, content_json, template, astro_component,
               institution, study_level, seo_title, seo_description,
               available_languages, image_overrides }

# List endpoints (used by blog index)
GET /api/method/paideia_cms.api.v1.blogs.get_blogs
GET /api/method/paideia_cms.api.v1.courses.get_courses
```

### Authenticated endpoints — requires Frappe login

```
GET  /api/method/paideia_cms.api.v1.templates.get_active_templates
GET  /api/method/paideia_cms.api.v1.templates.get_template?name=<name>
POST /api/method/paideia_cms.api.v1.templates.publish_template
POST /api/method/paideia_cms.api.v1.admin.trigger_generation
POST /api/method/paideia_cms.api.v1.admin.trigger_translation
GET  /api/method/paideia_cms.api.v1.admin.get_job_status
GET  /api/method/paideia_cms.api.v1.preview.render_page?name=PAGE-0001
GET  /api/method/paideia_cms.api.v1.preview.render_blog?name=BLOG-0001
GET  /api/method/paideia_cms.api.v1.preview.render_course?name=COURSE-0001
POST /api/method/paideia_cms.api.v1.preview.render_template_test
```

### External ingest — requires Frappe API key auth

Used by external systems (partner portals, scrapers, bulk import scripts) to push courses or blogs directly into the CMS without going through Frappe Desk.

```
POST /api/method/paideia_cms.api.v1.ingest.ingest_course
POST /api/method/paideia_cms.api.v1.ingest.ingest_blog
     Auth: Authorization: token <api_key>:<api_secret>

ingest_course payload:
  title           string   required
  institution     string   required  — 'uws' | 'presidency'
  study_level     string   required  — 'Undergraduate' | 'Postgraduate' | 'Professional' | 'Short Course' | 'Certificate'
  slug            string   optional  — auto-generated from title if omitted
  content_json    object   optional  — pre-built content; leave empty to fill via AI later in Frappe Desk
  template        string   optional  — CMS Template name
  seo_title       string   optional
  seo_description string   optional
  publish         boolean  optional  — true → workflow_state=Published → deploy hook fires → frontend updates in ~2 min

Response:
  { name, slug, action ('created'|'updated'), published, url }
```

Behaviour:
- **Upsert by slug** — if a course with that slug already exists, it is updated; otherwise created.
- If `publish: true` → `on_update()` detects the state transition → `deploy_trigger.py` fires the debounced Vercel webhook → Vercel rebuilds → new course is live on the frontend in ~2 minutes.
- Translation records link to the course by `name` (primary key) — the same course can be translated in any language via CMS Translation records without any extra wiring.
- The external system generates an API key once from Frappe Desk → User → API Access → Generate Keys.

### Internal — agent service only

```
POST /api/method/paideia_cms.api.v1.agent_callback.receive
     Auth: X-Agent-Secret header
```

---

## 10. CMS File Structure

```
paideia_cms/
│
├── hooks.py                          — app config, scheduled jobs, doctype JS map
├── install.py                        — creates roles + default settings on install
├── TEMPLATE_REGISTRY.json            — source-of-truth: astro_component → schema keys, image slots
│
├── jobs/
│   ├── ai_generation.py              — extract → dispatch to agent service
│   ├── ai_job_cleanup.py             — daily purge of AI Job Logs older than 30 days
│   ├── cache_cleanup.py              — hourly cache flush (invalidate_all)
│   └── translation.py               — background translation handler
│
├── ai/translators/
│   ├── base.py                       — BaseTranslator + extract_strings/rebuild helpers
│   ├── factory.py                    — get_translator() — reads CMS Settings.translation_provider
│   ├── deepl.py                      — DeepL API v2 (50 texts/batch)
│   ├── google_translate.py           — Google Cloud Translation v2 (128 texts/batch)
│   └── custom_api.py                 — POST to an external translation API
│
├── utils/
│   └── slugify.py                    — slug generation
│
├── api/
│   ├── response.py                   — success()/error()/not_found() envelope
│   └── v1/
│       ├── agent_callback.py         — receives webhooks from agent service
│       ├── registry.py               — get_published_pages (unified build-time list)
│       ├── pages.py                  — get_page, get_slugs
│       ├── blogs.py                  — get_blog, get_blogs
│       ├── courses.py                — get_course, get_courses
│       ├── redirects.py              — get_redirects (fetched by prebuild.mjs)
│       ├── ingest.py                 — ingest_course, ingest_blog (external push API, API key auth, upsert by slug)
│       ├── templates.py              — publish_template, get_active_templates
│       ├── admin.py                  — trigger_generation, trigger_translation, get_job_status
│       └── preview.py                — render_page/blog/course, render_template_test
│
├── cms/
│   ├── permissions/page_permissions.py
│   └── services/
│       ├── preview_engine.py         — Jinja2 SandboxedEnvironment, {{dot.path}} syntax
│       ├── cache_service.py          — Redis cache with named helpers per content type
│       ├── image_utils.py            — apply_image_overrides() — dot-path URL injection
│       ├── document_extractor.py     — PDF/DOCX/XLSX/TXT extraction
│       ├── translation_service.py    — translation job orchestration
│       └── deploy_trigger.py         — debounced Vercel webhook (1 per 60s)
│
└── pdcms/doctype/
    ├── cms_settings/                 — global singleton
    ├── cms_template/                 — HTML file, JSON schema, AI prompt, astro_component, image_slots
    ├── cms_prompt/                   — per-section AI prompts
    ├── cms_page/                     — landing pages (+ image_overrides field)
    ├── cms_blog/                     — blog posts (+ image_overrides field)
    ├── cms_course/                   — courses (+ institution, study_level, image_overrides)
    ├── cms_redirect/                 — auto-created on slug change for Published docs
    ├── cms_media/                    — media asset library
    ├── cms_translation/              — multilingual records (status + workflow_state)
    ├── ai_job_log/                   — job state tracking
    └── api_cache/                    — cached API response records
```

---

## 11. Frontend File Structure (`fe/`)

`fe/` is the Astro frontend. It is the **deployed production frontend** (not just a reference — it IS the site).

```
fe/
├── astro.config.mjs              — output: 'static', adapter selection (node/vercel/amplify),
│                                   CMS redirects injected from src/generated/cms-redirects.json
├── package.json                  — build: "node scripts/prebuild.mjs && astro build"
├── .env.local                    — local dev env vars (gitignored)
│
├── scripts/
│   ├── prebuild.mjs              — runs before every build:
│   │                               fetches CMS redirects → src/generated/cms-redirects.json
│   └── add-locale.mjs            — locale scaffolding helper
│
├── src/
│   ├── generated/                — gitignored, created by prebuild.mjs
│   │   └── cms-redirects.json    — active redirects from Frappe
│   │
│   ├── lib/
│   │   ├── cms.ts                — CMS API client (all guest endpoints, returns null on error)
│   │   │                           getCmsCourse(), getCmsBlog(), getCmsBlogs(),
│   │   │                           getPublishedPages(), normalizeCmsBlog()
│   │   ├── frappe.ts             — authenticated Frappe resource API client
│   │   └── env.ts                — env var validation (throws on missing required vars)
│   │
│   ├── content/                  — local markdown content (fallback source)
│   │   ├── courses/
│   │   │   ├── uws/postgraduate/*.md
│   │   │   ├── uws/undergraduate/*.md
│   │   │   └── presidency/…/*.md
│   │   └── blog/*.md
│   │
│   ├── content.config.ts         — Astro content collection schemas (Zod)
│   │
│   └── pages/
│       ├── en/
│       │   ├── [institution]/[level]/[slug].astro
│       │   │     getStaticPaths(): merges CMS courses + markdown
│       │   │     render: getCmsCourse() → content_json, else markdown → data
│       │   │
│       │   ├── blog/
│       │   │   ├── index.astro   — getCmsBlogs() + getCollection('blog') merged
│       │   │   └── [slug].astro  — getCmsBlog() first, markdown fallback
│       │   │
│       │   └── …                 — static pages (about, contact, etc.)
│       │
│       └── api/
│           ├── contact.ts        — prerender: false (server-rendered, proxies to Frappe)
│           ├── callback.ts       — prerender: false
│           └── health.ts         — prerender: false
```

### How `cms.ts` works

```typescript
// Every function returns null on any error — callers always have a fallback
async function cmsGet<T>(path: string): Promise<T | null> {
  if (!BASE_URL) return null;          // PUBLIC_FRAPPE_URL not set
  try {
    const res = await fetch(..., { signal: AbortSignal.timeout(5000) });
    if (!res.ok) return null;           // 4xx/5xx
    return json.message?.success ? json.message.data : null;
  } catch {
    return null;                        // network error, timeout
  }
}
```

If `PUBLIC_FRAPPE_URL` is not set (e.g., first local run with no `.env.local`), every CMS call returns null immediately and markdown content serves everything. The build never fails due to CMS unavailability.

---

## 12. Background Jobs

| Job | Trigger | File |
|---|---|---|
| `run_page_generation` | "Generate Content" button | `jobs/ai_generation.py` |
| `run_blog_generation` | "Generate Content" button | `jobs/ai_generation.py` |
| `run_course_generation` | "Generate Content" button | `jobs/ai_generation.py` |
| `run_translation` | "Translate" button | `jobs/translation.py` |
| `cleanup_ai_jobs` | Daily (scheduled) | `jobs/ai_job_cleanup.py` |
| `cleanup_cache` | Hourly (scheduled) | `jobs/cache_cleanup.py` |

---

## 13. Roles and Permissions

| Role | Access |
|---|---|
| CMS Admin | Full access — all doctypes, settings, templates |
| Content Editor | Create/edit CMS Page, Blog, Course |
| CMS Reviewer | Read + approve content, move workflow state |
| CMS Publisher | Publish approved content, write on templates |

---

## 14. Implementation Status

| Component | Status | Notes |
|---|---|---|
| All DocTypes (12) | Done | CMS Settings, Template, Prompt, Page, Blog, Course, Redirect, Media, Translation, AI Job Log, API Cache |
| install.py | Done | Auto-creates roles + default settings |
| Slugify utility | Done | URL slugs from titles |
| Role-based permissions | Done | All doctypes |
| AI generation pipeline | Done | Dispatches to agent service, receives webhooks |
| Agent callback handler | Done | step/completed/failed with context |
| AI Job Log cleanup | Done | Daily, 30-day retention |
| Preview engine | Done | Jinja2 `{{dot.path}}` injection |
| Preview API | Done | Opens rendered HTML in new tab |
| Form JS (Generate, Preview, Translate) | Done | All three content forms |
| CMS Template admin UI | Done | Publish, Deprecate, Validate Schema, Test Preview |
| Guest REST API | Done | pages, blogs, courses, registry, redirects |
| `get_published_pages` registry | Done | Unified build-time slug list for Astro `getStaticPaths()` |
| `get_redirects` API | Done | Fetched by prebuild.mjs, converted to Vercel CDN rules |
| CMS Course: institution + study_level | Done | Drives URL `/en/{institution}/{study_level}/{slug}` |
| CMS Redirect doctype | Done | Auto-created on slug change for Published docs |
| Image slots (template) + image_overrides (content) | Done | Dot-path URL injection via `apply_image_overrides()` |
| Translation: dual workflow | Done | `status` (AI pipeline) vs `workflow_state` (editorial), API serves only Published |
| DeepL + Google Translate providers | Done | Batch string extraction, translate, rebuild |
| Cache service (named helpers) | Done | `invalidate_page/blog/course/registry/all()` |
| Deploy trigger (debounced) | Done | Fires on publish + translation editorial publish |
| Vercel redirect wiring | Done | `scripts/prebuild.mjs` → `src/generated/cms-redirects.json` → `astro.config.mjs` → Vercel CDN rules |
| Astro hybrid mode (`output: 'static'`) | Done | All content pages pre-built; `/api/*` routes server-rendered |
| `getStaticPaths()` — CMS + markdown merge | Done | Course + blog routes; CMS wins for same slug; graceful fallback |
| Multi-adapter support | Done | `DEPLOY_TARGET=vercel/amplify/node` |
| External ingest API (`ingest_course`, `ingest_blog`) | Done | `api/v1/ingest.py` — upsert by slug, optional publish, deploy fires automatically |
| **CMS Course Template schema** | **Not done** | Must be created in Frappe Desk to match course component props |
| **CMS Blog Template schema** | **Not done** | Must be created; `content_json.meta.*` fields drive blog card + detail |
| **Content migration (markdown → CMS)** | **Not done** | ~33 courses + blogs need CMS entries |
| **Translation form JS** | **Not done** | No UI for editorial workflow on CMS Translation |
| **`PUBLIC_FRAPPE_URL` on Vercel** | **Not done** | Required for CMS content to appear in Vercel builds |
| **Vercel deploy hook in CMS Settings** | **Not done** | Required for auto-rebuild on publish |

---

## 15. Local Setup

### Frappe CMS (backend)

```bash
cd /path/to/bench
bench get-app paideia_cms
bench --site <site> install-app paideia_cms

# Python deps (in bench venv)
pip install pdfplumber python-docx openpyxl requests

bench start
```

Then in Frappe Desk:
1. **CMS Settings** → set AI provider, API key, Agent Service URL, Agent Service Secret
2. **CMS Template** → New → upload HTML, paste JSON schema, write prompt → Publish
3. **CMS Page / Blog / Course** → New → select template, upload PDF → Generate Content

Agent service must be running. See `aiAgents/paideia-agents/` for setup.

### Astro frontend (local dev)

```bash
cd apps/paideia_cms/fe

# Create .env.local (gitignored)
cat > .env.local << 'EOF'
PUBLIC_FRAPPE_URL=http://localhost:8000
FRAPPE_API_KEY=your_key_from_frappe_desk
FRAPPE_API_SECRET=your_secret_from_frappe_desk
CONTACT_ALLOWED_ORIGIN=http://localhost:4321
EOF

npm install
npm run dev        # → http://localhost:4321
npm run build      # full static build (runs prebuild.mjs first)
```

With bench running, CMS content appears automatically. Without bench, only markdown content shows.

---

## 16. Deploying to Vercel

1. **Push `fe/` to a GitHub repo** (or a subdirectory — use Vercel's root directory setting)

2. **Vercel Project → Settings → Environment Variables**:
   ```
   PUBLIC_FRAPPE_URL        = https://your-frappe.com   (public, build-time)
   FRAPPE_API_KEY           = <key>                      (sensitive)
   FRAPPE_API_SECRET        = <secret>                   (sensitive)
   CONTACT_ALLOWED_ORIGIN   = https://paideia.global
   DEPLOY_TARGET            = vercel
   ```

3. **Vercel Project → Settings → Build & Output**:
   - Build command: `node scripts/prebuild.mjs && astro build` *(already in package.json)*
   - Output directory: `dist/client`
   - Install command: `npm install`

4. **Wire the deploy hook**:
   - Vercel → Project → Settings → Git → Deploy Hooks → create → copy URL
   - Frappe Desk → CMS Settings → Frontend Deploy → paste URL into **Vercel Deploy Hook URL**

5. **Publish anything in Frappe** → deploy fires → Vercel builds → live in ~2 minutes.
