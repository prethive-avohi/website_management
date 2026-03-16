# Paideia CMS — Content Generator Setup Guide

## What This Module Does

Upload a **PDF or Word document** → AI extracts the content → automatically generates a **structured web page** (landing page, blog post, or web page) → hosts it on your Frappe site with a proper URL route.

```
User uploads PDF/Word
        ↓
[Paideia Content Generator] extracts text (PyPDF2 / python-docx)
        ↓
[Paideia CMS Settings] routes to AI provider
        ↓
   ┌──────┬──────────────┬──────────┬──────────┐
   ↓      ↓              ↓          ↓          ↓
Ollama  HuggingFace    Groq     OpenAI     Claude
(local)  (free)       (free)    (paid)     (paid)
   └──────┴──────────────┴──────────┴──────────┘
        ↓
  Structured JSON → Paideia Web Page (Draft)
        ↓
  Publish → /api/method/paideia_cms.api.pages.get_page?slug=your-slug
        ↓
  Astro frontend renders the page
```

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Install the App](#2-install-the-app)
3. [Choose Your AI Provider](#3-choose-your-ai-provider)
4. [Provider Setup — Local (Ollama)](#4a-provider-setup--ollama-local)
5. [Provider Setup — Groq (Free Cloud)](#4b-provider-setup--groq-free-cloud)
6. [Provider Setup — HuggingFace (Free Cloud)](#4c-provider-setup--huggingface-free-cloud)
7. [Provider Setup — OpenAI ChatGPT (Paid)](#4d-provider-setup--openai-chatgpt-paid)
8. [Provider Setup — Claude Anthropic (Paid)](#4e-provider-setup--claude-anthropic-paid)
9. [How to Use the Content Generator](#5-how-to-use-the-content-generator)
10. [How Routing Works](#6-how-routing-works)
11. [API Reference](#7-api-reference)
12. [Frappe Cloud Deployment](#8-frappe-cloud-deployment)
13. [Troubleshooting](#9-troubleshooting)
14. [File Structure](#10-file-structure)

---

## 1. Prerequisites

- **Frappe Bench** installed and working (v14 or v15)
- A Frappe site created (`bench new-site your-site.localhost`)
- Python 3.10+
- For local AI: macOS/Linux with 8GB+ RAM (for Ollama)
- For cloud AI: Internet access + free or paid API key

---

## 2. Install the App

### On Local / Self-Hosted Bench

```bash
# Step 1: Navigate to your bench directory
cd ~/frappe-bench

# Step 2: Get the app (if from git)
bench get-app paideia_cms /path/to/paideia_cms
# OR if it's already in your apps folder, skip this step

# Step 3: Install on your site
bench --site your-site.localhost install-app paideia_cms
```

This automatically:
- Installs Python dependencies (`PyPDF2`, `python-docx`)
- Creates all DocTypes (`Paideia Content Generator`, `Paideia CMS Settings`, etc.)
- Detects your environment (local vs cloud) and pre-configures settings

```bash
# Step 4: Run migrate (creates database tables)
bench --site your-site.localhost migrate

# Step 5: Clear cache
bench --site your-site.localhost clear-cache

# Step 6: Restart bench
bench restart
# OR for development:
bench start
```

### Verify Installation

Open your browser and go to:
```
http://your-site.localhost:8000/app/paideia-cms-settings
```

You should see the **Paideia CMS Settings** page with AI provider options.

---

## 3. Choose Your AI Provider

| Provider | Cost | Speed | Quality | Works on Frappe Cloud? |
|----------|------|-------|---------|----------------------|
| **Ollama (Local)** | Free | 10-60s | Good | No |
| **Groq** | Free (14,400 req/day) | 2-5s | Good | Yes |
| **HuggingFace** | Free (1,000 req/day) | 15-60s | Good | Yes |
| **OpenAI (ChatGPT)** | ~$0.15-$2.50/1M tokens | 3-10s | Excellent | Yes |
| **Claude (Anthropic)** | ~$0.25-$15/1M tokens | 3-15s | Excellent | Yes |

### Recommendation

- **Self-hosted, no budget**: Ollama (free, unlimited, private)
- **Frappe Cloud, no budget**: Groq (free, fast)
- **Best quality, budget OK**: Claude (`claude-sonnet-4-6`) or OpenAI (`gpt-4o-mini`)

---

## 4a. Provider Setup — Ollama (Local)

Ollama runs AI models locally on your machine. Completely free, no API keys needed.

### Install Ollama

```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Windows — download from https://ollama.ai
```

### Pull a Model

```bash
# Recommended: Mistral 7B (~4.1 GB download)
ollama pull mistral

# Lighter alternatives:
ollama pull phi3          # 3.8 GB — Microsoft Phi-3
ollama pull gemma2:2b     # 1.6 GB — Google Gemma 2 (smallest)
ollama pull llama3.1:8b   # 4.7 GB — Meta Llama 3.1
```

### Start Ollama Server

```bash
ollama serve
```

Ollama runs on `http://localhost:11434` by default.

### Configure in Frappe

1. Go to **Paideia CMS Settings** (`/app/paideia-cms-settings`)
2. Set **AI Provider** = `Ollama (Local)`
3. **Ollama URL** = `http://localhost:11434` (default)
4. **Ollama Model** = `mistral` (or whichever you pulled)
5. Save

### Verify Ollama is Running

```bash
curl http://localhost:11434/api/tags
# Should return a list of available models
```

---

## 4b. Provider Setup — Groq (Free Cloud)

Groq provides extremely fast inference with a generous free tier. Best option for Frappe Cloud.

### Get API Key

1. Go to [console.groq.com](https://console.groq.com)
2. Sign up (free)
3. Navigate to **API Keys** → **Create API Key**
4. Copy the key

### Configure in Frappe

1. Go to **Paideia CMS Settings** (`/app/paideia-cms-settings`)
2. Set **AI Provider** = `Groq (Free API)`
3. Paste your **Groq API Key**
4. **Groq Model** = `llama-3.1-8b-instant` (default, fastest)
5. Save

### Available Groq Models

| Model | Speed | Quality |
|-------|-------|---------|
| `llama-3.1-8b-instant` | Fastest | Good |
| `llama-3.3-70b-versatile` | Fast | Better |
| `mixtral-8x7b-32768` | Fast | Good (longer context) |
| `gemma2-9b-it` | Fast | Good |

---

## 4c. Provider Setup — HuggingFace (Free Cloud)

HuggingFace Inference API gives you access to thousands of models for free.

### Get API Token

1. Go to [huggingface.co](https://huggingface.co)
2. Sign up (free)
3. Go to **Settings** → **Access Tokens** → **New token**
4. Create a token with `read` permission
5. Copy the token

### Configure in Frappe

1. Go to **Paideia CMS Settings** (`/app/paideia-cms-settings`)
2. Set **AI Provider** = `HuggingFace (Free API)`
3. Paste your **HuggingFace API Token**
4. **HuggingFace Model** = `mistralai/Mistral-7B-Instruct-v0.3` (default)
5. Save

### Notes

- First request may take 30-60s (model cold start)
- Subsequent requests are faster (~15-30s)
- ~1,000 requests/day on the free tier

---

## 4d. Provider Setup — OpenAI ChatGPT (Paid)

OpenAI provides the most reliable JSON structured output.

### Get API Key

1. Go to [platform.openai.com](https://platform.openai.com)
2. Sign up and add billing (pay-as-you-go)
3. Go to **API Keys** → **Create new secret key**
4. Copy the key

### Configure in Frappe

1. Go to **Paideia CMS Settings** (`/app/paideia-cms-settings`)
2. Set **AI Provider** = `OpenAI (ChatGPT)`
3. Paste your **OpenAI API Key**
4. **OpenAI Model** = `gpt-4o-mini` (default, cheapest good model)
5. Save

### Available OpenAI Models

| Model | Cost (per 1M tokens) | Quality |
|-------|----------------------|---------|
| `gpt-4.1-nano` | ~$0.10 input / $0.40 output | Basic |
| `gpt-4o-mini` | ~$0.15 input / $0.60 output | Good |
| `gpt-4.1-mini` | ~$0.40 input / $1.60 output | Better |
| `gpt-4o` | ~$2.50 input / $10 output | Best |

### Estimated Cost Per Page Generation

With `gpt-4o-mini`: approximately **$0.002 - $0.01** per page (very cheap).

---

## 4e. Provider Setup — Claude Anthropic (Paid)

Claude produces the highest quality content and follows structured JSON instructions very well.

### Get API Key

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Sign up and add billing
3. Go to **Settings** → **API Keys** → **Create Key**
4. Copy the key

### Configure in Frappe

1. Go to **Paideia CMS Settings** (`/app/paideia-cms-settings`)
2. Set **AI Provider** = `Claude (Anthropic)`
3. Paste your **Anthropic API Key**
4. **Claude Model** = `claude-sonnet-4-6` (default, balanced)
5. Save

### Available Claude Models

| Model | Cost (per 1M tokens) | Quality |
|-------|----------------------|---------|
| `claude-haiku-4-5-20251001` | ~$0.25 input / $1.25 output | Fast, cheap |
| `claude-sonnet-4-6` | ~$3 input / $15 output | Balanced |
| `claude-opus-4-6` | ~$15 input / $75 output | Best |

### Estimated Cost Per Page Generation

With `claude-sonnet-4-6`: approximately **$0.01 - $0.05** per page.
With `claude-haiku-4-5-20251001`: approximately **$0.001 - $0.005** per page.

---

## 5. How to Use the Content Generator

### Step 1: Create a New Content Generator

1. In Frappe Desk, go to the search bar
2. Type **Paideia Content Generator** → click **+ New**
3. Or navigate to: `/app/paideia-content-generator/new`

### Step 2: Fill in the Form

| Field | What to Enter |
|-------|--------------|
| **Title** | Name for your page (e.g. "UK Student Visa Guide 2024") |
| **Upload Document** | Click to upload a `.pdf` or `.docx` file |
| **Page Type** | Choose one: **Landing Page**, **Blog Post**, or **Web Page** |
| **Audience** | Choose: **All**, **Universities**, **Students**, or **Consultants** |
| **Slug** | Auto-generated from title. Override if needed (e.g. `students/visa-guide-2024`) |

### Step 3: Save the Form

Press `Ctrl+S` or click **Save**. The status will show **Pending**.

### Step 4: Generate the Page

1. Click the **Actions** dropdown → **Generate Page**
2. Confirm in the dialog
3. Wait for processing (depends on provider — 2s to 60s)
4. Status changes: `Pending` → `Extracting` → `Generating` → `Completed`

### Step 5: Review the Generated Page

1. Click **Actions** → **View Generated Page**
2. This opens the generated **Paideia Web Page** in Draft mode
3. Review/edit the:
   - Hero headline and subheadline
   - Meta title and description (SEO)
   - Page sections (content, ordering, backgrounds)
4. When satisfied, change **Status** to `Published`

### Step 6: Access the Published Page

The page is now available via the API:
```
GET /api/method/paideia_cms.api.pages.get_page?slug=your-slug
```

Your Astro frontend fetches this data and renders the page.

### What Each Page Type Generates

| Page Type | What AI Creates |
|-----------|----------------|
| **Landing Page** | Hero + 4-6 sections (Feature Cards, Process Steps, CTA Banner, Trust Strip, FAQ) |
| **Blog Post** | Hero + 3-5 Rich Text sections with proper HTML formatting |
| **Web Page** | Hero + 3-6 mixed sections (Rich Text + Feature Cards/FAQ as appropriate) |

---

## 6. How Routing Works

### The Flow

```
1. Content Generator creates a Paideia Web Page with slug: "students/visa-guide"
2. Page status set to "Draft" (review first)
3. Admin reviews and sets status to "Published"
4. Astro frontend calls API: get_page("students/visa-guide")
5. API returns full page data (hero, meta, sections with parsed items)
6. Astro renders the page at: https://yoursite.com/students/visa-guide
```

### URL Structure

The `slug` field determines the URL path:

| Slug | Resulting URL |
|------|--------------|
| `about-us` | yoursite.com/about-us |
| `students/visa-guide` | yoursite.com/students/visa-guide |
| `blog/study-in-uk-2024` | yoursite.com/blog/study-in-uk-2024 |

### Slug Auto-Generation

- If you leave the slug blank, it's auto-generated from the title
- "UK Student Visa Guide 2024" → `uk-student-visa-guide-2024`
- You can override it to create nested paths like `students/visa-guide`
- If a slug already exists, a random 4-character hash is appended

---

## 7. API Reference

All endpoints are public (`allow_guest=True`) for Astro frontend access.

### Get a Single Page

```
GET /api/method/paideia_cms.api.pages.get_page?slug=students/visa-guide
```

**Response:**
```json
{
  "message": {
    "name": "UK Student Visa Guide",
    "title": "UK Student Visa Guide",
    "slug": "students/visa-guide",
    "audience": "Students",
    "meta_title": "UK Student Visa Guide | Paideia",
    "meta_description": "Complete guide to UK student visas...",
    "hero_headline": "Your Complete UK Student Visa Guide",
    "hero_subheadline": "Everything you need to know...",
    "hero_cta_label": "Start Application",
    "hero_cta_url": "#contact",
    "sections": [
      {
        "section_type": "Rich Text",
        "heading": "Introduction",
        "body": "<p>The UK student visa...</p>",
        "background": "White",
        "order": 1,
        "items": []
      },
      {
        "section_type": "Process Steps",
        "heading": "Application Process",
        "items": [
          {"title": "Step 1", "description": "Gather documents..."},
          {"title": "Step 2", "description": "Apply online..."}
        ],
        "background": "Grey",
        "order": 2
      }
    ]
  }
}
```

### Get All Page Slugs (for Astro Static Paths)

```
GET /api/method/paideia_cms.api.pages.get_all_slugs
```

### Get Pages by Audience

```
GET /api/method/paideia_cms.api.pages.get_pages_by_audience?audience=Students
```

### Get Site Config

```
GET /api/method/paideia_cms.api.pages.get_site_config
```

### Get Testimonials

```
GET /api/method/paideia_cms.api.pages.get_testimonials?audience=Students
```

---

## 8. Frappe Cloud Deployment

### Key Limitation

Frappe Cloud does **NOT** allow:
- Running background services (Ollama)
- SSH access
- Docker containers
- Custom system packages

### What Works on Frappe Cloud

All cloud API providers work:
- **Groq** (recommended — free + fast)
- **HuggingFace** (free)
- **OpenAI** (paid)
- **Claude** (paid)

### Deployment Steps

1. **Push your app to GitHub** (private repo is fine)

2. **Add the app on Frappe Cloud:**
   - Go to your FC dashboard
   - Navigate to your bench → **Apps** → **Add App**
   - Enter your GitHub repo URL
   - FC will install the app and run migrations

3. **Install dependencies** (if not auto-installed):
   - FC Dashboard → your site → **Site Console**
   ```bash
   bench pip install PyPDF2 python-docx
   ```

4. **Configure AI provider:**
   - Go to `https://your-site.frappe.cloud/app/paideia-cms-settings`
   - Select provider (e.g. `Groq (Free API)`)
   - Paste your API key
   - Save

5. **Test:**
   - Create a new Paideia Content Generator
   - Upload a test document
   - Click Generate Page

### Environment Variables on Frappe Cloud

If you prefer not to store API keys in the database, you can also set them in `site_config.json` via FC dashboard:

```json
{
  "groq_api_key": "gsk_...",
  "openai_api_key": "sk-...",
  "claude_api_key": "sk-ant-..."
}
```

Then modify the content_generator.py to check `frappe.conf` first.

---

## 9. Troubleshooting

### "Cannot connect to Ollama"

```
Cannot connect to Ollama at http://localhost:11434
```

**Fix:**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start it
ollama serve

# If port is different, update in Paideia CMS Settings
```

### "Model not found" (Ollama)

```bash
# Pull the model first
ollama pull mistral

# List available models
ollama list
```

### "HuggingFace model is loading (cold start)"

This is normal on first request. Wait 30-60 seconds and try again. The model stays warm for ~15 minutes after each request.

### "Failed to parse LLM response as JSON"

The AI returned malformed JSON. Try:
1. **Switch to a better model** — Claude and GPT-4o are most reliable for JSON
2. **Try again** — LLM outputs are non-deterministic
3. Check the **Extracted Text** section to verify the document was read correctly
4. Check the **Error Log** section for the raw AI response

### "PyPDF2 not installed" / "python-docx not installed"

```bash
# In your bench directory:
bench pip install PyPDF2 python-docx

# On Frappe Cloud, use Site Console:
bench pip install PyPDF2 python-docx
```

### "Could not extract any text from the PDF"

The PDF might be scanned (image-based). PyPDF2 cannot extract text from images. Options:
- Use a Word (.docx) document instead
- Use a PDF with selectable text (not scanned)
- For scanned PDFs, first run OCR (Optical Character Recognition) before uploading

### Status Stuck on "Extracting" or "Generating"

The request may have timed out. Steps:
1. Manually set status back to `Pending` (edit the document)
2. Check your AI provider is working (API key valid, Ollama running)
3. Try with a smaller document
4. Check Frappe error logs: **Error Log** list in desk

### Rate Limit Errors

| Provider | Free Limit | Fix |
|----------|-----------|-----|
| Groq | 14,400 req/day | Wait or upgrade |
| HuggingFace | ~1,000 req/day | Wait or use Pro ($9/mo) |
| OpenAI | Depends on tier | Add billing |
| Claude | Depends on tier | Add billing |

---

## 10. File Structure

```
paideia_cms/
├── setup.py                          # Package installation config
├── requirements.txt                  # Python dependencies
│
└── paideia_cms/
    ├── __init__.py
    ├── hooks.py                      # Frappe hooks (JS registration, after_install)
    ├── modules.txt                   # Module name: "Paideia CMS"
    ├── install.py                    # Post-install: pip deps + default settings
    ├── seed_data.py                  # Sample data seeder
    │
    ├── api/
    │   └── pages.py                  # Public API endpoints (get_page, get_all_slugs, etc.)
    │
    ├── utils/
    │   ├── document_extractor.py     # PDF + Word text extraction
    │   └── content_generator.py      # AI provider router (5 providers)
    │
    ├── paideia_cms_settings/         # Settings singleton DocType
    │   └── paideia_cms_settings.json # AI provider config, API keys
    │
    ├── paideia_content_generator/    # Content Generator DocType
    │   ├── paideia_content_generator.json  # DocType definition
    │   ├── paideia_content_generator.py    # Server-side controller
    │   └── paideia_content_generator.js    # Client-side UI
    │
    ├── paideia_web_page/             # Web Page DocType (output)
    │   └── paideia_web_page.json
    │
    ├── paideia_page_section/         # Page Section child table
    │   └── paideia_page_section.json
    │
    ├── paideia_site_config/          # Site-wide config singleton
    │   └── paideia_site_config.json
    │
    └── paideia_testimonial/          # Testimonials DocType
        └── paideia_testimonial.json
```

---

## Quick Start Summary

### Local (3 commands)

```bash
bench --site mysite install-app paideia_cms
ollama pull mistral && ollama serve
# Open /app/paideia-cms-settings → Ollama is auto-configured
```

### Frappe Cloud (2 steps)

1. Install app from FC dashboard
2. Open `/app/paideia-cms-settings` → pick Groq/OpenAI/Claude → paste API key → Save

### Generate Your First Page

1. Go to `/app/paideia-content-generator/new`
2. Title: "Test Page" → Upload any PDF → Page Type: "Web Page" → Save
3. Actions → Generate Page → Wait → Done!
