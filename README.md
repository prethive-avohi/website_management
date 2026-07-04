# paideia_cms — Frappe CMS App

Template-driven headless CMS built on the Frappe Framework. Editors manage all content here — pages, blogs, courses — and the system handles AI generation, translation, preview, and publishing automatically. The frontend (Astro) pulls everything from this app at build time.

---

## What this app does

### 1. Template-driven content
Every page type is backed by a **CMS Template** that defines:
- A Jinja2 HTML file — the visual design of the page
- A JSON Schema — the exact structure AI must output
- An AI prompt — instructions for content generation

Editors never write code. They pick a template, upload a PDF/DOCX, click Generate.

### 2. AI content generation
Upload a PDF or DOCX → Frappe extracts the text → dispatches to the `paideia-agents` FastAPI service → AI (OpenAI / Groq / Claude / Ollama) generates structured `content_json` matching the template's schema → result webhooks back and saves automatically.

The AI job runs in the background. Editors see live progress and the form auto-reloads when done.

### 3. Preview = production
Editors click **View → Preview** and see exactly what visitors will see. Frappe renders the Jinja2 template with `content_json` injected — the same endpoint the Astro frontend calls at build time. No surprises between preview and live.

### 4. Multilingual translation
Any published document can be translated. Frappe calls DeepL or Google Cloud Translate on every string in `content_json` and stores the result in a **CMS Translation** record. The editor reviews, publishes, and the next Astro build serves translated content at `/pt-br/<slug>`, `/fr/<slug>`, etc.

Adding a new language = one line in the frontend config + create translations in Frappe. No route code changes.

### 5. Workflow + publish → live
Documents go through: **Draft → Review → Approved → Published**. On Publish, Frappe fires a deploy hook to AWS Amplify, which rebuilds the Astro site automatically. Live within minutes.

### 6. Caching
All public API responses are cached in Redis with a configurable TTL. Cache invalidates automatically on document update or publish.

### 7. Ingest API
External systems can push course and blog content directly into Frappe via authenticated endpoints — useful for syncing from university portals.

---

## How the three apps align

```
┌─────────────────────────────────────────────────────────────┐
│                    paideia_cms (Frappe)                      │
│                                                             │
│  Editor creates CMS Page → attaches PDF                     │
│  → "AI → Generate Content"                                  │
│        ↓                                                    │
│  Frappe extracts text → POST /api/v1/generate ──────────────┼──► paideia-agents
│        ↓           ◄── webhooks step/completed/failed ──────┼──◄  (OpenAI/Groq/Claude)
│  content_json saved                                         │
│        ↓                                                    │
│  Editor previews → publishes                                │
│  → deploy hook ─────────────────────────────────────────────┼──► AWS Amplify rebuild
│                                                             │          ↓
│  Astro build calls Frappe API ◄─────────────────────────────┼──◄ paideia-cms-fe
│    /registry   → all published slugs                        │    getStaticPaths()
│    /pages      → SEO metadata per page                      │    getCmsPage()
│    /preview    → rendered HTML per page                     │    getCmsPageHtml()
│    /blogs      → blog content_json                          │    getCmsBlog()
│    /courses    → course content_json                        │    getCmsCourse()
└─────────────────────────────────────────────────────────────┘
```

**Key design decisions:**
- Landing page design lives in Frappe (HTML template file) — each page can look completely different, zero Astro changes needed
- Blog and course design lives in Astro (fixed components) — CMS supplies content only
- Frappe never calls AI providers directly — all AI runs in the agent service, no keys in Frappe
- Preview and production use the same render endpoint — what the editor sees is exactly what goes live

---

## Local setup

```bash
cd ~/frappe-projects/paideia-bench
bench --site cms install-app paideia_cms
bench --site cms migrate
bench start
```

Open Frappe Desk → CMS Settings and configure:

| Setting | Value |
|---|---|
| Agent Service URL | `http://localhost:8001` |
| Agent Service Secret | Any strong random string — must match `AGENT_SERVICE_SECRET` in agent `.env` |
| Translation Provider | `deepl` / `google` / `custom` |
| Translation API Key | Your DeepL or Google Cloud key |
| Deploy Hook URL | AWS Amplify webhook URL |

---

## Doctypes

| Doctype | Purpose |
|---|---|
| CMS Settings | Global singleton — agent URL/secret, translation, cache TTL, deploy hook |
| CMS Template | Jinja2 HTML file + JSON schema + AI prompt + Astro component ref |
| CMS Page | Landing pages — slug → rendered HTML via template |
| CMS Blog | Blog posts |
| CMS Course | Courses keyed by institution / level / slug |
| CMS Translation | Translated content per language per document |
| CMS Media | Media asset library |
| CMS Redirect | URL redirect rules fetched by Astro at build time |
| AI Job Log | AI generation job state: Queued → Running → Completed / Failed |

---

## Roles

| Role | Access |
|---|---|
| CMS Admin | Full — settings, templates, all content |
| Content Editor | Create/edit CMS Page, Blog, Course |
| CMS Reviewer | Review and approve content |
| CMS Publisher | Publish approved content |

---

## Template syntax

Jinja2 with dot-path notation:

```html
<h1>{{ hero.headline }}</h1>
<p>{{ hero.subheadline }}</p>

{% for step in journey.steps %}
  <div class="step">{{ step.title }}</div>
{% endfor %}

<li>{{ nav.links.0.label }}</li>  <!-- array by index -->
```

---

## REST API

Base: `https://<frappe-site>/api/method/paideia_cms.api.v1`

### Public — no auth (`allow_guest=True`)

Called by the Astro frontend at build time.

```
GET /registry.get_published_pages
    → [{ slug, content_type, title, institution?, study_level? }]

GET /pages.get_page?slug=home&lang=en
    → { title, slug, astro_component, content, seo: { meta_title, meta_description, og_image, canonical_url } }

GET /preview.render_page_content?slug=home&lang=en
    → text/html  (Jinja2-rendered template, falls back to English if no translation)

GET /blogs.get_blog?slug=visa-guide&lang=en
    → { name, title, slug, content_json, creation, seo_title, seo_description }

GET /blogs.get_blogs
    → [CmsBlog]

GET /courses.get_course?slug=uws/postgraduate/ai&lang=en
    → { name, title, slug, institution, study_level, content_json, seo_title, seo_description }

GET /redirects.get_redirects
    → [{ source, destination, permanent }]

GET /preview.render_blog_content?slug=visa-guide&lang=en
    → text/html
```

### Authenticated — `Authorization: token <api_key>:<api_secret>`

```
POST /admin.trigger_generation       { doctype, doc_name }
     → { job_id, status: "queued" }

GET  /admin.get_job_status?job_id=…
     → { status, message }

POST /admin.trigger_translation      { doctype, doc_name, language }
     → { translation_name }

POST /ingest.ingest_course           { institution, study_level, slug, title, content_json }
POST /ingest.ingest_blog             { slug, title, content_json }

GET  /preview.render_page?name=PAGE-0001
GET  /preview.render_blog?name=BLOG-0001
GET  /preview.render_course?name=COURSE-0001
GET  /preview.render_translation?name=CMS-TRANS-0001
     → text/html (requires CMS role)
```

### Internal — agent service only (`X-Agent-Secret` header)

```
POST /agent_callback.receive

  Step:      { job_id, status: "step",      message, context: { doctype, doc_name } }
  Completed: { job_id, status: "completed", content_json, metadata, context }
  Failed:    { job_id, status: "failed",    error, context }

  → { ok: true }
```
