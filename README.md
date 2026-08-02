# AI-Powered Company Research Assistant
**Relu Consultancy - AI & Automation Developer Hiring Hackathon**

An AI-powered corporate intelligence application that automatically researches any company by name or website URL, crawls official subpages, aggregates Serper.dev search context, generates deep strategic AI insights with OpenRouter/Gemini, identifies competitors, exports professional downloadable PDF reports, and posts automated PDF reports to Discord.

![Application Interface](https://raw.githubusercontent.com/relu-consultancy/company-intelligence/main/screenshot.png)

---

## Key Features

- 🔍 **Dual Input Support**: Accepts Company Name (e.g. `Figma`, `Tesla`, `Stripe`) or direct Website URL (`https://stripe.com`).
- 🕷️ **Intelligent Web Crawler**: Discovers key subpages (`/about`, `/products`, `/services`, `/solutions`, `/contact`, `/pricing`), filters out duplicate & login pages, and extracts clean context.
- 🌐 **Serper.dev Search Resolver**: Resolves official domains, extracts Google Knowledge Graph contact details (phone, address), and gathers organic search snippets.
- 🧠 **AI Reasoning Engine**: Supports OpenRouter AI models (`google/gemini-2.5-flash`, `openai/gpt-4o-mini`, `anthropic/claude-3.5-haiku`, `meta-llama/llama-3.3-70b-instruct`) and direct Google Gemini API.
- 📄 **1-Click Downloadable PDF**: Generates professional PDF reports matching exact corporate layout specifications.
- 🤖 **Discord Bot Integration**: Automatically posts applicant details, research summary, and attaches the generated PDF report directly to configured Discord channels.
- 🎨 **ChatGPT-Style Dark UI**: Ultra-modern, responsive interface with progress step loaders, tag pills, competitor cards, and settings drawers.

---

## Technical Stack & Python Data Architecture

The application is written in **Python** and leverages **Python Dictionaries (`dict`)** for end-to-end data manipulation and API schemas:

```
[ User Input (Name or Website URL) ]
            │
            ▼
[ Python Web Server (`main.py`) ]
            │
            ▼
[ Research Engine ]
  ├── 1. `serper.py`: Serper.dev Search -> Returns dict {"official_website": str, "knowledge_graph": dict}
  ├── 2. `crawler.py`: Web Crawler -> Returns dict {"pages_crawled": list, "combined_text": str}
  ├── 3. `ai_engine.py`: OpenRouter / Gemini -> Returns dict {"company_name": str, "pain_points": list, ...}
  ├── 4. `pdf_generator.py`: PDF Builder -> Returns PDF bytes from research dict
  └── 5. `discord_bot.py`: Discord Web API -> Posts embed & attaches PDF report binary
```

---

## Setup & Running Locally

### 1. Requirements
- Python 3.9 or higher

### 2. Quick Run (Standard Python Library - Zero Dependencies Required!)
Run the server immediately with Python's built-in libraries:

```bash
python main.py
```

Open your browser and navigate to:
```
http://localhost:8000
```

### 3. Optional Enhanced Setup (with ReportLab / Requests)
```bash
pip install -r requirements.txt
python main.py
```

---

## Environment Variables (`.env.local`)

| Environment Variable | Service | Description |
| :--- | :--- | :--- |
| `OPENROUTER_API_KEY` | OpenRouter AI API Key | Entered directly in UI or set via env var |
| `SERPER_API_KEY` | Serper.dev Search API Key | Optional (Entered directly in UI or set via env var) |
| `GOOGLE_API_KEY` | Google Gemini API Key | Optional fallback |

---

## Discord Integration Setup

1. In the web interface, click the **DISCORD** tab on the left sidebar.
2. Enter your **Bot Token** and **Channel ID**.
3. Enter your **Applicant Full Name** and **Email Address**.
4. Click **Saved ✓**.
5. Once research completes, the report and PDF file attachment will be posted automatically to your Discord channel!

---

## Submission Checklist

- [x] Source Code (Python + Web UI)
- [x] Website Crawling Implementation
- [x] AI Company Research (Gemini / OpenRouter)
- [x] Competitor Analysis
- [x] PDF Report Generation
- [x] Discord Bot Integration & File Attachment
- [x] README & Environment Variable Documentation
