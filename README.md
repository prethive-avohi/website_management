# paideia_cms — Frappe CMS App

Template-driven headless CMS built on the Frappe Framework. Manages all content (pages, blogs, courses), orchestrates AI content generation through the agent service, handles multilingual translation, and serves a REST API consumed by the Astro frontend.

## Related repos

| Repo | Purpose |
|---|---|
| `paideia_cms` (this) | Frappe backend — doctypes, API, AI orchestration |
| [paideia-agents](../../../paideia-agents) | FastAPI AI agent service — content generation |
| [paideia-cms-fe](../../../paideia-cms-fe) | Astro frontend — static site served to visitors |

---

## Local setup

```bash
cd ~/frappe-projects/paideia-bench
bench --site cms install-app paideia_cms
bench --site cms migrate
bench start
```

Then open Frappe Desk → CMS Settings and configure:

| Setting | Value |
|---|---|
| Agent Service URL | `http://localhost:8001` (local) or deployed agent URL |
| Agent Service Secret | Any strong random string — must match `AGENT_SERVICE_SECRET` in agent `.env` |
| Translation Provider | `deepl` / `google` / `custom` |
| Translation API Key | Your DeepL or Google Cloud key |
| Deploy Hook URL | AWS Amplify webhook URL (triggers Astro rebuild on publish) |

---

## Doctypes

| Doctype | Purpose |
|---|---|
| CMS Settings | Global singleton — agent URL/secret, translation, cache TTL, deploy hook |
| CMS Template | Template: Jinja2 HTML file, JSON schema, AI prompt, Astro component ref |
| CMS Page | Landing pages (slug → rendered HTML via template) |
| CMS Blog | Blog posts |
| CMS Course | Courses keyed by institution / level / slug |
| CMS Translation | Translated content per language per document |
| CMS Media | Media asset library |
| CMS Redirect | URL redirect rules fetched by Astro at build time |
| AI Job Log | Tracks AI generation job state (Queued → Running → Completed / Failed) |

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

HTML templates use Jinja2 with dot-path notation:

```html
<h1>{{ hero.headline }}</h1>
<p>{{ hero.subheadline }}</p>

{% for step in journey.steps %}
<div class="step">{{ step.title }}</div>
{% endfor %}

<!-- Array index -->
<li>{{ nav.links.0.label }}</li>
```

---

## Content workflow

```
New document → attach PDF/DOCX → "AI → Generate Content"
  → Frappe extracts text → dispatches to agent service
  → Agent runs AI → webhooks step/completed/failed back
  → Review content_json → "View → Preview"
  → Workflow: Draft → Review → Approved → Published
  → Deploy hook fires → Astro rebuild → live
```

## Translation workflow

```
Published CMS Page → "AI → Translate" → select language
  → Frappe enqueues translation job
  → DeepL/Google translates content_json string values
  → Creates CMS Translation record (workflow_state = Draft)
  → Editor reviews → "Publish"
  → Next Astro build picks up translated content via ?lang=pt-br
```

---

## REST API

Base: `https://<frappe-site>/api/method/paideia_cms.api.v1`

### Public endpoints — no auth (`allow_guest=True`)

Called by Astro frontend at build time.

#### Published page registry

```
GET /registry.get_published_pages
```

Response:
```json
{
  "message": {
    "success": true,
    "data": [
      { "title": "Home", "slug": "home", "content_type": "CMS Page" },
      { "title": "Visa Guide", "slug": "uk-student-visa-guide", "content_type": "CMS Blog" },
      { "title": "MSc AI", "slug": "uws/postgraduate/ai", "content_type": "CMS Course", "institution": "uws", "study_level": "postgraduate" }
    ]
  }
}
```

#### Get a CMS Page (JSON for SEO head)

```
GET /pages.get_page?slug=home&lang=en
```

Response:
```json
{
  "message": {
    "success": true,
    "data": {
      "title": "Home",
      "slug": "home",
      "template": "TMPL-0001",
      "astro_component": "LandingPage",
      "content": { "hero": { "headline": "Study in the UK" } },
      "seo": {
        "meta_title": "Paideia — Study Abroad",
        "meta_description": "...",
        "og_title": "...",
        "og_description": "...",
        "og_image": "https://...",
        "canonical_url": "https://paideia.global/en/home"
      },
      "published_at": "2025-06-01 10:00:00"
    }
  }
}
```

#### Get rendered HTML for a CMS Page (landing page body)

```
GET /preview.render_page_content?slug=home&lang=en
```

Response: `text/html` — Jinja2-rendered template with content injected. Frappe checks for a Published CMS Translation for that lang and falls back to English if none exists.

#### Get a CMS Blog

```
GET /blogs.get_blog?slug=uk-student-visa-guide&lang=en
```

Response:
```json
{
  "message": {
    "success": true,
    "data": {
      "name": "BLOG-0001",
      "title": "UK Student Visa Guide",
      "slug": "uk-student-visa-guide",
      "content_json": { "meta": { "author": "Paideia Team" }, "body": "..." },
      "creation": "2025-05-15 08:30:00",
      "seo_title": "...",
      "seo_description": "..."
    }
  }
}
```

#### List all published blogs

```
GET /blogs.get_blogs
```

Response: `{ "message": { "success": true, "data": [ ... ] } }`

#### Get a CMS Course

```
GET /courses.get_course?slug=uws/postgraduate/artificial-intelligence&lang=en
```

Response:
```json
{
  "message": {
    "success": true,
    "data": {
      "name": "COURSE-0001",
      "title": "MSc Artificial Intelligence",
      "slug": "uws/postgraduate/artificial-intelligence",
      "institution": "uws",
      "study_level": "postgraduate",
      "content_json": { "hero": {...}, "about": {...}, "modules": [...], "fees": {...} },
      "seo_title": "...",
      "seo_description": "..."
    }
  }
}
```

#### URL redirects

```
GET /redirects.get_redirects
```

Response: `{ "message": { "success": true, "data": [ { "source": "/old-path", "destination": "/new-path", "permanent": true } ] } }`

#### Rendered HTML for CMS Blog

```
GET /preview.render_blog_content?slug=uk-student-visa-guide&lang=en
```

Response: `text/html`

---

### Authenticated — API token required

```
Authorization: token <api_key>:<api_secret>
```

#### Trigger AI content generation

```
POST /admin.trigger_generation
Content-Type: application/json

{ "doctype": "CMS Page", "doc_name": "PAGE-0001" }
```

Response: `{ "message": { "success": true, "data": { "job_id": "uuid-...", "status": "queued" } } }`

#### Check job status

```
GET /admin.get_job_status?job_id=uuid-...
```

Response: `{ "message": { "success": true, "data": { "status": "Completed", "message": "Content saved." } } }`

#### Trigger translation

```
POST /admin.trigger_translation
Content-Type: application/json

{ "doctype": "CMS Page", "doc_name": "PAGE-0001", "language": "pt-br" }
```

Response: `{ "message": { "success": true, "data": { "translation_name": "CMS-TRANS-0001" } } }`

#### Ingest a course (external push)

```
POST /ingest.ingest_course
Content-Type: application/json

{
  "institution": "uws",
  "study_level": "postgraduate",
  "slug": "artificial-intelligence",
  "title": "MSc Artificial Intelligence",
  "content_json": { ... }
}
```

Response: `{ "message": { "success": true, "data": { "name": "COURSE-0001" } } }`

#### Editor preview (CMS roles required)

```
GET /preview.render_page?name=PAGE-0001
GET /preview.render_blog?name=BLOG-0001
GET /preview.render_course?name=COURSE-0001
GET /preview.render_translation?name=CMS-TRANS-0001
```

All return `text/html`.

---

### Internal — agent service only

#### Agent job callback

```
POST /agent_callback.receive
X-Agent-Secret: <shared-secret>
Content-Type: application/json

// Step update:
{ "job_id": "uuid", "status": "step", "message": "Calling OpenAI...", "context": { "doctype": "CMS Page", "doc_name": "PAGE-0001" } }

// Completed:
{ "job_id": "uuid", "status": "completed", "content_json": {...}, "metadata": { "tokens_used": 1200, "model": "gpt-4o", "provider": "openai" }, "context": {...} }

// Failed:
{ "job_id": "uuid", "status": "failed", "error": "Rate limit exceeded.", "context": {...} }
```

Response: `{ "ok": true }`

---

## Standing rules

- All Python code lives inside `paideia_cms/` — never at repo root
- No AI logic or provider keys in Frappe — all AI runs in the agent service
- Always update `ARCHITECTURE.md` when system flow, API endpoints, or doctypes change
