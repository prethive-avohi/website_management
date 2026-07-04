# Paideia CMS — Claude Context

Template-driven headless CMS built on Frappe Framework. All AI runs in the separate
`aiAgents/paideia-agents` FastAPI service — Frappe never calls AI providers directly.

## Standing Rules
- **Always update ARCHITECTURE.md** whenever the system flow, file structure, API endpoints, or roles change.
- All Python code must live inside `paideia_cms/` — never at repo root.
- Frappe Cloud is the deployment target — `bench build` is not available. JS cache clears only via Frappe Desk "Clear Cache".
- No AI calls inside Frappe — all generation goes through the agent service.

---

## Two Roles

| Role | What they do |
|---|---|
| Template Administrator | Creates CMS Templates: defines JSON schema, writes AI prompt, publishes |
| CMS User | Creates CMS Page / Blog / Course: selects template, uploads PDF/DOCX, triggers AI generation, previews, publishes |

---

## Full System Flow

```
ADMIN SIDE
1. CMS Settings → set agent_service_url + agent_service_secret (one-time)
2. CMS Template → New → name, type, Astro component ref
3. Paste JSON Schema → defines what AI must output
4. Customise AI prompt ({content} + {schema} placeholders)
5. Click "Publish Template" → status: Active → visible to CMS users

USER SIDE
6.  CMS Page / Blog / Course → New
7.  Enter title, select Active template, attach PDF or DOCX → Save
8.  Click "AI → Generate Content"
9.  Frappe extracts text from file, dispatches to agent service (POST /api/v1/generate)
10. Agent service runs AI in background → webhooks step/completed/failed back to Frappe
11. Yellow spinner banner + auto-poll every 4s — page auto-reloads on completion
12. Review content_json field → edit directly if needed → Save
13. Click "View → Preview" → rendered HTML opens in new tab
14. Workflow: Draft → Review → Approved → Published
15. Astro frontend fetches published content via REST API → renders page
```

---

## File Structure

```
paideia_cms/
  hooks.py                          — app config, scheduled jobs, doctype JS map
  install.py                        — creates roles + default settings on install
  logger.py                         — get_logger() helper
  utils/slugify.py                  — URL slug generator
  jobs/
    ai_generation.py                — extract text in Frappe → dispatch to agent service → wait for callback
    ai_job_cleanup.py               — daily purge of AI Job Logs older than 30 days
    cache_cleanup.py                — hourly Redis cache flush (safety net for stale keys)
    translation.py                  — background translation job handler
  ai/translators/
    base.py                         — abstract BaseTranslator + shared string-walk helpers
    factory.py                      — get_translator() dispatcher (reads CMS Settings)
    deepl.py                        — DeepL API v2 translator
    google_translate.py             — Google Cloud Translation API translator
    custom_api.py                   — generic pluggable translation API
  cms/
    permissions/page_permissions.py — role-based access for all CMS doctypes
    services/
      preview_engine.py             — renders template file with {{dot.path}} injection
      cache_service.py              — Redis-based API response caching (get/set/invalidate)
      deploy_trigger.py             — debounced POST to Vercel deploy hook on publish
      image_utils.py                — merges image_overrides into content_json before API response
  api/
    response.py                     — standard {success, data, meta, errors} envelope
    v1/
      pages.py                      — guest page endpoints
      blogs.py                      — guest blog endpoints
      courses.py                    — guest course endpoints
      registry.py                   — get_published_pages (slug discovery for Astro getStaticPaths)
      redirects.py                  — get_redirects (CMS Redirect rules for Astro prebuild)
      templates.py                  — template picker + publish endpoints
      admin.py                      — trigger_generation, trigger_translation, get_job_status
      preview.py                    — render_page/blog/course + render_template_test
      ingest.py                     — ingest_course, ingest_blog (external push API)
      agent_callback.py             — receives step/completed/failed from paideia-agents
  pdcms/doctype/
    cms_settings/   — global singleton: agent service URL/secret, cache TTL, translation provider
    cms_template/   — template: JSON schema, AI prompt, Astro component ref
    cms_prompt/     — advanced per-section AI prompts
    cms_page/       — landing pages
    cms_blog/       — blog posts
    cms_course/     — courses
    cms_media/      — media asset library
    cms_translation/ — multilingual translation records
    cms_redirect/   — URL redirect rules (fetched by Astro prebuild)
    ai_job_log/     — tracks generation/translation job state

public/js/
  cms_template.js  — Publish Template, Deprecate, Validate Schema, Test Preview (View menu)
  cms_page.js      — Generate Content (AI menu), Preview (View menu), Translate (AI menu)
  cms_blog.js      — Generate Content (AI menu), Preview (View menu)
  cms_course.js    — Generate Content (AI menu), Preview (View menu)
```

---

## Key Technical Decisions

### AI generation — Frappe side (ai_generation.py)
Frappe's only responsibility is text extraction (it has private file auth). Everything else is the agent service.

1. Create AI Job Log (status: Queued)
2. Extract text from PDF/DOCX/XLSX/TXT via pdfplumber / python-docx / openpyxl
3. Read schema + prompt from linked CMS Template
4. POST to `agent_service_url/api/v1/generate` with extracted text, schema, prompt, provider, model, callback URL
5. Agent returns 202 immediately → generation_status = "Generating — agent job {id}"
6. Agent webhooks step/completed/failed to `agent_callback.receive`
7. On callback: save content_json, set generation_status = Completed

### Template placeholder syntax
`{{hero.headline}}` → `content["hero"]["headline"]`
`{{features.0.title}}` → `content["features"][0]["title"]`
Arrays use numeric index. Unmatched placeholders left as-is.

### Caching
Redis only — `cache_service.py` wraps `frappe.cache()`. No database cache table.
Keys: `pdcms:{type}:{slug}:{lang}`, `pdcms:registry:*`
Invalidated on `on_update()` of each doctype, and hourly by `cache_cleanup.py`.

### JS buttons strategy (Frappe Cloud cache issue)
- Buttons always added to View/AI menu groups — survive JS caching
- `frm.page.set_primary_action()` also set as a fresh-cache convenience

---

## Agent Service (separate project)

Location: `aiAgents/paideia-agents/`

| Route | Purpose |
|---|---|
| `POST /api/v1/generate` | Receive text + schema + prompt → run AI → POST results to Frappe callback |
| `GET /health` | Liveness check |

Auth: `X-Agent-Secret` header (shared secret set in CMS Settings).

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
GET /api/method/paideia_cms.api.v1.pages.get_page?slug=<slug>&lang=en
GET /api/method/paideia_cms.api.v1.blogs.get_blog?slug=<slug>
GET /api/method/paideia_cms.api.v1.blogs.get_blogs
GET /api/method/paideia_cms.api.v1.courses.get_course?slug=<slug>
GET /api/method/paideia_cms.api.v1.courses.get_courses
GET /api/method/paideia_cms.api.v1.registry.get_published_pages
GET /api/method/paideia_cms.api.v1.redirects.get_redirects
```

### Requires API token
```
POST /api/method/paideia_cms.api.v1.ingest.ingest_course
POST /api/method/paideia_cms.api.v1.ingest.ingest_blog
POST /api/method/paideia_cms.api.v1.admin.trigger_generation
POST /api/method/paideia_cms.api.v1.admin.trigger_translation
GET  /api/method/paideia_cms.api.v1.admin.get_job_status
GET  /api/method/paideia_cms.api.v1.templates.get_active_templates
GET  /api/method/paideia_cms.api.v1.preview.render_course?name=COURSE-0001
```

### Internal (agent service → Frappe)
```
POST /api/method/paideia_cms.api.v1.agent_callback.receive
```

---

## Implementation Status

| Component | Status |
|---|---|
| All 9 DocTypes | Done |
| install.py + roles | Done |
| AI generation (dispatch to agent service) | Done |
| Agent callback receiver | Done |
| Preview engine | Done |
| Cache (Redis) | Done |
| Deploy trigger (Vercel hook on publish) | Done |
| Image overrides | Done |
| Ingest API (external course/blog push) | Done |
| Registry + Redirects API | Done |
| Translation (DeepL / Google / Custom) | Done |
| AI Job cleanup | Done |
| Astro frontend | Done (fe/) |
| Agent service (content generation) | Done (aiAgents/paideia-agents/) |
| Schema-driven form editor | Not built |

---

## Local Setup

```bash
cd ~/frappe-projects/paideia-bench
bench --site cms migrate
bench start
```

Then in CMS Settings → set:
- `Agent Service URL`: http://localhost:8001
- `Agent Service Secret`: same value as `AGENT_SERVICE_SECRET` in paideia-agents `.env`

Start agent service separately — see `aiAgents/paideia-agents/README.md`.
