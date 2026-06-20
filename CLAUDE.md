# PDCMS App — Claude Context

AI-powered template-driven headless CMS built on Frappe Framework.

## Standing Rules
- **Always update README.md** whenever the system flow, file structure, API endpoints, or roles change.
- All Python code must live inside `pdcms_app/` — never at repo root. Frappe resolves imports like `pdcms_app.api.v1.pages` only inside the package.
- Frappe Cloud is the deployment target — `bench build` is not available. JS cache clears only via Frappe Desk "Clear Cache".

---

## Two Roles

| Role | What they do |
|---|---|
| Template Administrator | Creates CMS Templates: uploads HTML/Astro file, defines JSON schema, writes AI prompt, publishes |
| CMS User | Creates CMS Page / Blog / Course: selects template, uploads PDF/DOCX, triggers AI generation, previews, publishes |

---

## Full System Flow

```
ADMIN SIDE
1. CMS Settings → set AI provider + API key (one-time)
2. CMS Template → New → name, type, Astro component ref
3. Upload HTML/Astro template file with {{dot.path}} placeholders
4. Paste JSON Schema → defines what AI must output
5. Customise AI prompt ({content} + {schema} placeholders)
6. Click "Publish Template" → status: Active → visible to CMS users

USER SIDE
7.  CMS Page / Blog / Course → New
8.  Enter title, select Active template, attach PDF or DOCX → Save
9.  Click "AI → Generate Content"
10. Yellow spinner banner + auto-poll every 4s (no manual refresh needed)
11. Page auto-reloads on completion → green banner confirms success
12. Review content_json field → edit directly if needed → Save
13. Click "View → Preview" → rendered HTML opens in new tab
14. Edit JSON → Save → Preview again — unlimited iterations
15. Workflow: Draft → Review → Approved → Published
16. Astro frontend fetches published content via REST API → renders page
```

---

## File Structure

```
pdcms_app/
  hooks.py                          — app config, scheduled jobs, doctype JS map
  install.py                        — creates roles + default settings on install
  utils/slugify.py                  — URL slug generator
  jobs/
    ai_generation.py                — FULL AI pipeline: extract → prompt → call AI → save JSON
    ai_job_cleanup.py               — daily purge of AI Job Logs older than 30 days
    cache_cleanup.py                — hourly cache eviction (partial)
    translation.py                  — background translation job handler
  ai/translators/
    base.py                         — abstract BaseTranslator
    factory.py                      — get_translator() dispatcher
    custom_api.py                   — POSTs to external translation API
  cms/
    permissions/page_permissions.py — role-based access for all CMS doctypes
    services/
      preview_engine.py             — renders template file with {{dot.path}} injection
      cache_service.py              — Redis-based API response caching
      document_extractor.py         — PDF/DOCX/TXT text extraction
      translation_service.py        — translation job orchestration
    workflows/publish.py            — publish/archive workflow handlers
  api/
    response.py                     — standard {success, data, meta, errors} envelope
    v1/
      pages.py                      — guest page endpoints
      blogs.py                      — guest blog endpoints
      courses.py                    — guest course endpoints
      templates.py                  — template picker + publish endpoints
      admin.py                      — trigger_generation, trigger_translation, get_job_status
      preview.py                    — render_page/blog/course + render_template_test
  pdcms/doctype/
    cms_settings/                   — global singleton: AI provider, keys, cache TTL
    cms_template/                   — template: file, schema, prompt, preview image
    cms_prompt/                     — advanced per-section AI prompts
    cms_page/                       — landing pages
    cms_blog/                       — blog posts
    cms_course/                     — courses
    cms_media/                      — media asset library
    cms_translation/                — multilingual translation records
    ai_job_log/                     — background job state tracking
    api_cache/                      — API response cache records

public/js/
  cms_template.js  — Publish Template, Deprecate, Validate Schema, Test Preview (View menu), View Prompts
  cms_page.js      — Generate Content (AI menu), Preview (View menu), Translate (AI menu)
  cms_blog.js      — Generate Content (AI menu), Preview (View menu)
  cms_course.js    — Generate Content (AI menu), Preview (View menu)
```

---

## Key Technical Decisions

### Template placeholder syntax
`{{hero.headline}}` → `content["hero"]["headline"]`
`{{features.0.title}}` → `content["features"][0]["title"]`
Arrays use numeric index. Unmatched placeholders left as-is.

### AI generation pipeline (jobs/ai_generation.py)
1. Create AI Job Log (status: Queued)
2. `generation_status = Extracting` → extract PDF/DOCX text
3. `generation_status = Generating` → build prompt → call AI provider
4. Parse JSON response (strip markdown fences if present)
5. Save to `content_json` → `generation_status = Completed`
6. On error: `generation_status = Failed`, populate `ai_error_log`

### Prompt priority
1. `template.ai_prompt` (set on CMS Template — recommended)
2. Linked CMS Prompt records (advanced, per-section)
3. Hardcoded defaults in `ai_generation.py` (always works as fallback)

### AI providers
Groq, OpenAI, Claude (Anthropic), Ollama (local), HuggingFace.
Configured in CMS Settings singleton. API keys stored as password fields.

### JS buttons strategy (Frappe Cloud cache issue)
- All buttons on CMS Template form are unconditional — validation runs inside click handlers
- Preview always added to `View` menu group on content forms (when `content_json` exists)
- `frm.page.set_primary_action()` set as well (works when cache is fresh)
- View/AI menu groups are permanent fallbacks that survive JS caching

---

## Roles

| Role | Access |
|---|---|
| CMS Admin | Full access — all doctypes, settings, templates |
| Content Editor | Create/edit CMS Page, Blog, Course |
| CMS Reviewer | Review and approve content |
| CMS Publisher | Publish approved content, write on templates |

---

## REST API

### Guest (Astro frontend — no login required)
```
GET /api/method/pdcms_app.api.v1.pages.get_page?slug=<slug>&lang=en
GET /api/method/pdcms_app.api.v1.pages.get_slugs
GET /api/method/pdcms_app.api.v1.blogs.get_blog?slug=<slug>
GET /api/method/pdcms_app.api.v1.blogs.get_blogs
GET /api/method/pdcms_app.api.v1.courses.get_course?slug=<slug>
GET /api/method/pdcms_app.api.v1.courses.get_courses
```

### Requires login
```
GET  /api/method/pdcms_app.api.v1.templates.get_active_templates
GET  /api/method/pdcms_app.api.v1.templates.get_template?name=<name>
POST /api/method/pdcms_app.api.v1.templates.publish_template
POST /api/method/pdcms_app.api.v1.admin.trigger_generation
POST /api/method/pdcms_app.api.v1.admin.trigger_translation
GET  /api/method/pdcms_app.api.v1.admin.get_job_status
GET  /api/method/pdcms_app.api.v1.preview.render_page?name=PAGE-0001
GET  /api/method/pdcms_app.api.v1.preview.render_blog?name=BLOG-0001
GET  /api/method/pdcms_app.api.v1.preview.render_course?name=COURSE-0001
POST /api/method/pdcms_app.api.v1.preview.render_template_test
```

---

## Implementation Status

| Component | Status | Notes |
|---|---|---|
| All 10 DocTypes | Done | Fields, validation, controllers complete |
| install.py | Done | Auto-creates roles and default settings |
| slugify utility | Done | Auto-generates URL slugs from titles |
| Role-based permissions | Done | All CMS doctypes covered |
| AI generation pipeline | Done | Groq, OpenAI, Claude, Ollama, HuggingFace |
| AI Job Log cleanup | Done | Daily purge, records older than 30 days |
| Preview engine | Done | `{{dot.path}}` injection into template files |
| Preview API | Done | Opens rendered HTML in browser tab |
| Template API | Done | Serves active templates for picker |
| Form JS buttons | Done | Preview, Generate, Translate on all content forms |
| CMS Template Admin UI | Done | Publish, Deprecate, Validate Schema, Test Preview |
| cache_cleanup.py | Partial | Hourly job exists, eviction logic needs improvement |
| api_cache.py | Stub | Persistence only — no read/write serving logic yet |
| Translation job | Partial | CMS Translation doctype exists, provider wiring incomplete |
| **Astro frontend** | **Not built** | **Highest priority — nothing visible to end users** |
| Schema-driven form editor | Not built | Edit content fields individually instead of raw JSON |

---

## Local Bench Setup

```bash
# Copy app into bench
cp -r pdcms_app /path/to/bench/apps/

# Install on site
bench --site <site-name> install-app pdcms_app

# Install Python dependencies
pip install PyPDF2 python-docx requests

# Start bench
bench start
```

Then go to **CMS Settings** → set AI provider + API key before generating any content.
