"""
Relu Consultancy - AI & Automation Developer Hiring Hackathon
Main Python Application & Web Server.
Serves a sleek, minimalistic dark-theme Web UI with vibrant cyan/sky-blue accents (#38bdf8 / #0284c7).
Features resilient Vercel Serverless POST dispatching based on request body payload inspection.
"""

import json
import os
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any

from config import get_config
from serper import resolve_domain, search_serper
from crawler import crawl_company_website
from ai_engine import generate_company_research
from pdf_generator import generate_pdf_report
from discord_bot import send_report_to_discord

PORT = 8000

class handler(BaseHTTPRequestHandler):
    """HTTP Request Handler providing REST API endpoints and Web UI serving."""
    
    def log_message(self, format, *args):
        print(f"[HTTP Server]: {self.address_string()} - {args[0]}")

    def send_json(self, data: dict[str, Any], status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def send_bytes(self, content: bytes, content_type: str, filename: str = ""):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(content)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self):
        clean_path = self.path.split('?')[0].rstrip('/')
        if not clean_path or clean_path in ["", "/", "/index.html", "/api/index", "/index"]:
            html_content = get_web_ui_html()
            self.send_bytes(html_content.encode("utf-8"), "text/html; charset=utf-8")
        elif clean_path == "/api/health":
            self.send_json({"status": "ok", "app": "Relu AI Research Assistant"})
        else:
            html_content = get_web_ui_html()
            self.send_bytes(html_content.encode("utf-8"), "text/html; charset=utf-8")

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else ""
        
        try:
            req_data: dict[str, Any] = json.loads(post_body) if post_body else {}
        except Exception:
            req_data = {}

        path_str = f"{self.path} {self.headers.get('x-matched-path', '')} {self.headers.get('x-forwarded-uri', '')} {req_data.get('endpoint', '')}".lower()

        if "discord" in path_str or "bot_token" in req_data:
            self.handle_discord_api(req_data)
        elif "download-pdf" in path_str or ("report" in req_data and "input" not in req_data):
            self.handle_pdf_download_api(req_data)
        elif "research" in path_str or "input" in req_data:
            self.handle_research_api(req_data)
        else:
            self.send_json({"error": "Endpoint not found"}, 404)

    def handle_research_api(self, req_data: dict[str, Any]):
        input_text = req_data.get("input", "").strip()
        openrouter_key = req_data.get("openrouter_key", "").strip()
        serper_key = req_data.get("serper_key", "").strip()
        selected_model = req_data.get("selected_model", "").strip()

        if not input_text:
            self.send_json({"error": "Please enter a company name, company name & city, or website URL in the chat box."}, 400)
            return

        cfg = get_config()
        active_openrouter = openrouter_key or cfg.get("OPENROUTER_API_KEY", "")
        active_serper = serper_key or cfg.get("SERPER_API_KEY", "")

        if not active_openrouter:
            self.send_json({
                "error": "No OpenRouter API key found! Please click the 'API' tab on the left sidebar and enter your OpenRouter API Key to run research."
            }, 400)
            return

        print(f"\n[Research Pipeline Started]: Input='{input_text}', Model='{selected_model or 'default'}'")

        domain_info: dict[str, Any] = resolve_domain(input_text, active_serper)
        official_url = domain_info.get("official_website", "")
        company_name = domain_info.get("company_name", input_text)
        
        serper_data: dict[str, Any] = domain_info.get("serper_context") or search_serper(f"{input_text} official website global offices locations", active_serper)
        
        print(f"[Web Crawler]: Crawling domain '{official_url}'...")
        crawl_data: dict[str, Any] = crawl_company_website(official_url, max_pages=3)

        print(f"[AI Engine]: Generating research summary & locations for '{company_name}'...")
        report_dict: dict[str, Any] = generate_company_research(
            company_name=company_name,
            website_url=official_url,
            crawl_data=crawl_data,
            serper_data=serper_data,
            selected_model=selected_model,
            custom_openrouter_key=active_openrouter
        )

        if "error" in report_dict:
            self.send_json({"error": report_dict["error"]}, 400)
            return

        response_payload: dict[str, Any] = {
            "status": "success",
            "domain_info": domain_info,
            "crawl_stats": {
                "total_pages": crawl_data.get("total_pages", 0),
                "pages_crawled": crawl_data.get("pages_crawled", [])
            },
            "report": report_dict
        }

        self.send_json(response_payload)

    def handle_pdf_download_api(self, req_data: dict[str, Any]):
        report = req_data.get("report", {})
        if not report:
            self.send_json({"error": "Missing report data"}, 400)
            return
            
        pdf_bytes = generate_pdf_report(report)
        company_name = report.get("company_name", "company").lower().replace(" ", "_")
        filename = f"{company_name}_research_report.pdf"
        
        self.send_bytes(pdf_bytes, "application/pdf", filename)

    def handle_discord_api(self, req_data: dict[str, Any]):
        bot_token = req_data.get("bot_token", "")
        channel_id = req_data.get("channel_id", "")
        applicant_name = req_data.get("applicant_name", "")
        applicant_email = req_data.get("applicant_email", "")
        report = req_data.get("report", {})

        if not report or not bot_token or not channel_id:
            self.send_json({"error": "Report data, Bot Token, and Channel ID are required."}, 400)
            return

        pdf_bytes = generate_pdf_report(report)
        res_dict = send_report_to_discord(
            bot_token=bot_token,
            channel_id=channel_id,
            applicant_name=applicant_name,
            applicant_email=applicant_email,
            report=report,
            pdf_bytes=pdf_bytes
        )

        if res_dict.get("success"):
            self.send_json(res_dict)
        else:
            self.send_json(res_dict, 500)

ReluRequestHandler = handler

def get_web_ui_html() -> str:
    """Returns the single-page ChatGPT minimalist dark mode web UI with Cyan/Sky-Blue styling and OpenRouter AI Model Selector."""
    return '''<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Relu Consultancy - AI Company Research Assistant</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          colors: {
            brandBlue: '#38bdf8',
            brandBlueDark: '#0284c7',
            brandBlueHover: '#0369a1',
            darkBg: '#090d16',
            sidebarBg: '#0f172a',
            cardBg: '#1e293b',
            inputBg: '#0f172a',
            borderDark: '#334155'
          }
        }
      }
    }
  </script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <style>
    body { font-family: 'Inter', sans-serif; background-color: #090d16; color: #f8fafc; }
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #0f172a; }
    ::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
    .pulse-glow { animation: pulse 2s infinite; }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
  </style>
</head>
<body class="h-screen flex overflow-hidden bg-[#090d16]">

  <!-- LEFT SIDEBAR -->
  <aside class="w-80 bg-[#0f172a] border-r border-[#334155] flex flex-col justify-between p-4 z-20">
    <div>
      <div class="flex items-center space-x-3 mb-6 pb-4 border-b border-[#334155]">
        <div class="w-9 h-9 rounded-xl bg-gradient-to-tr from-sky-500 to-blue-600 flex items-center justify-center font-bold text-white text-xl shadow-lg shadow-sky-500/20">
          R
        </div>
        <div>
          <h1 class="font-bold text-white tracking-wide text-base">Relu Consultancy</h1>
          <p class="text-xs text-sky-400 uppercase tracking-widest font-semibold">COMPANY INTELLIGENCE</p>
        </div>
      </div>

      <button onclick="startNewResearch()" class="w-full py-2.5 px-4 mb-5 rounded-xl border border-[#334155] hover:border-sky-400 text-slate-200 hover:text-sky-400 transition font-medium flex items-center justify-center space-x-2 text-sm bg-[#1e293b]">
        <svg class="w-4 h-4 text-sky-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
        <span>New Research</span>
      </button>

      <div class="grid grid-cols-2 gap-1 bg-[#1e293b] p-1 rounded-xl mb-5 border border-[#334155]">
        <button id="tab-api-btn" onclick="switchTab('api')" class="py-1.5 text-xs font-semibold rounded-lg bg-sky-500 text-slate-950 font-bold transition shadow-md">API</button>
        <button id="tab-discord-btn" onclick="switchTab('discord')" class="py-1.5 text-xs font-semibold rounded-lg text-slate-400 hover:text-white transition">DISCORD</button>
      </div>

      <!-- API KEYS & MODEL SELECTOR PANEL -->
      <div id="api-panel" class="space-y-3">
        <div class="p-3 rounded-xl bg-[#1e293b] border border-[#334155] text-xs text-sky-300 leading-relaxed">
          <span class="font-bold text-white block mb-1">🤖 AI Model & API Settings</span>
          Choose any OpenRouter-supported AI model or enter custom model slugs.
        </div>
        
        <div>
          <label class="block text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">SELECT AI MODEL</label>
          <select id="model-select" onchange="handleModelChange()" class="w-full bg-[#0f172a] border border-[#334155] rounded-lg px-3 py-2 text-xs text-sky-300 focus:outline-none focus:border-sky-400 font-semibold cursor-pointer">
            <option value="google/gemini-2.0-flash-001">⚡ Gemini 2.0 Flash (Recommended)</option>
            <option value="google/gemini-flash-1.5">🚀 Gemini 1.5 Flash</option>
            <option value="meta-llama/llama-3.3-70b-instruct">🦙 Llama 3.3 70B Instruct</option>
            <option value="openai/gpt-4o-mini">🧠 OpenAI GPT-4o Mini</option>
            <option value="deepseek/deepseek-chat">🌊 DeepSeek V3 Chat</option>
            <option value="anthropic/claude-3.5-haiku">🎨 Anthropic Claude 3.5 Haiku</option>
            <option value="mistralai/mistral-large">✏️ Mistral Large</option>
            <option value="custom">⚙️ Enter Custom OpenRouter Model Slug...</option>
          </select>
        </div>

        <div id="custom-model-box" class="hidden">
          <label class="block text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">CUSTOM OPENROUTER MODEL SLUG</label>
          <input type="text" id="custom-model-input" placeholder="e.g. qwen/qwen-2.5-72b-instruct" class="w-full bg-[#0f172a] border border-[#334155] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-sky-400 font-mono">
        </div>

        <div>
          <label class="block text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">OPENROUTER API KEY *</label>
          <input type="text" id="openrouter-key" placeholder="Open OPENROUTER API KEY" class="w-full bg-[#0f172a] border border-[#334155] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-sky-400 font-mono">
        </div>

        <div>
          <label class="block text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">SERPER API KEY (Search)</label>
          <input type="text" id="serper-key" placeholder="Enter Serper API Key (Optional)" class="w-full bg-[#0f172a] border border-[#334155] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-sky-400 font-mono">
        </div>

        <button onclick="saveAPISettings()" id="save-api-btn" class="w-full mt-2 py-2.5 bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-400 hover:to-blue-500 text-white font-bold text-xs rounded-xl shadow-lg shadow-sky-500/20 transition flex items-center justify-center space-x-1">
          <span>Save Model & Keys ✓</span>
        </button>
      </div>

      <!-- DISCORD SETTINGS PANEL -->
      <div id="discord-panel" class="space-y-3 hidden">
        <div class="p-3 rounded-xl bg-[#1e293b] border border-[#334155] text-xs text-sky-300 leading-relaxed">
          <span class="font-bold text-white block mb-1">Discord Bot Integration</span>
          After research completes, the report auto-sends to your configured channel.
        </div>

        <div>
          <label class="block text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">BOT TOKEN</label>
          <input type="text" id="discord-token" placeholder="Paste Discord Bot Token" class="w-full bg-[#0f172a] border border-[#334155] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-sky-400 font-mono">
        </div>

        <div>
          <label class="block text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">CHANNEL ID</label>
          <input type="text" id="discord-channel" placeholder="Paste 18-digit Channel ID" class="w-full bg-[#0f172a] border border-[#334155] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-sky-400 font-mono">
        </div>

        <div class="pt-2 border-t border-[#334155]">
          <span class="block text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-2">APPLICANT DETAILS</span>
          <div class="space-y-2">
            <input type="text" id="applicant-name" placeholder="Full Name" class="w-full bg-[#0f172a] border border-[#334155] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-sky-400">
            <input type="email" id="applicant-email" placeholder="Email Address" class="w-full bg-[#0f172a] border border-[#334155] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-sky-400">
          </div>
        </div>

        <button onclick="saveDiscordSettings()" id="save-discord-btn" class="w-full mt-3 py-2.5 bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-400 hover:to-blue-500 text-white font-bold text-xs rounded-xl shadow-lg shadow-sky-500/20 transition flex items-center justify-center space-x-1">
          <span>Save Discord Config ✓</span>
        </button>
      </div>

      <!-- HOW IT WORKS -->
      <div class="mt-6 pt-4 border-t border-[#334155]">
        <h4 class="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-3">HOW IT WORKS</h4>
        <ol class="space-y-2 text-xs text-slate-300">
          <li class="flex items-start space-x-2">
            <span class="w-4 h-4 rounded-full bg-sky-950 text-sky-400 border border-sky-800/80 text-[10px] font-bold flex items-center justify-center mt-0.5">1</span>
            <span>Select AI Model & Enter API Keys</span>
          </li>
          <li class="flex items-start space-x-2">
            <span class="w-4 h-4 rounded-full bg-sky-950 text-sky-400 border border-sky-800/80 text-[10px] font-bold flex items-center justify-center mt-0.5">2</span>
            <span>Enter Company Name, City, or URL</span>
          </li>
          <li class="flex items-start space-x-2">
            <span class="w-4 h-4 rounded-full bg-sky-950 text-sky-400 border border-sky-800/80 text-[10px] font-bold flex items-center justify-center mt-0.5">3</span>
            <span>AI generates research summary</span>
          </li>
          <li class="flex items-start space-x-2">
            <span class="w-4 h-4 rounded-full bg-sky-950 text-sky-400 border border-sky-800/80 text-[10px] font-bold flex items-center justify-center mt-0.5">4</span>
            <span>Download a professional PDF report</span>
          </li>
        </ol>
      </div>
    </div>

    <div class="pt-4 border-t border-[#334155] text-[10px] text-slate-500 uppercase tracking-widest font-mono text-center">
      OPENROUTER · SERPER · JSPDF
    </div>
  </aside>

  <!-- MAIN AREA -->
  <main class="flex-1 flex flex-col h-full bg-[#090d16] relative">

    <header class="h-14 border-b border-[#334155] px-6 flex items-center justify-between bg-[#0f172a]/70 backdrop-blur">
      <div class="flex items-center space-x-3">
        <h2 class="font-bold text-white text-base">Company Research</h2>
        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950/80 text-emerald-400 border border-emerald-800/60">
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 mr-1.5 pulse-glow"></span> LIVE
        </span>
      </div>
    </header>

    <div id="content-container" class="flex-1 overflow-y-auto p-6 md:p-10 space-y-6">

      <!-- WELCOME VIEW -->
      <div id="welcome-view" class="max-w-3xl mx-auto mt-12 text-center space-y-6">
        <div class="w-16 h-16 rounded-2xl bg-sky-500/10 border border-sky-500/30 flex items-center justify-center mx-auto shadow-lg shadow-sky-500/10">
          <svg class="w-8 h-8 text-sky-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/></svg>
        </div>
        <h3 class="text-2xl font-bold text-white">AI-Powered Corporate Intelligence</h3>
        <p class="text-slate-400 text-sm max-w-lg mx-auto leading-relaxed">
          Select your preferred OpenRouter AI model, then research any Company Name, City, or Website URL to explore branch location hierarchies, summaries, and PDF exports.
        </p>

        <div class="grid grid-cols-2 md:grid-cols-4 gap-3 max-w-xl mx-auto pt-4">
          <button onclick="quickInput('TCS Chennai')" class="p-3 bg-[#1e293b] hover:bg-[#283548] border border-[#334155] hover:border-sky-500/50 rounded-xl text-left transition group">
            <span class="block text-xs font-bold text-white group-hover:text-sky-400">TCS</span>
            <span class="text-[10px] text-slate-500">Chennai Siruseri</span>
          </button>
          <button onclick="quickInput('Tesla Austin')" class="p-3 bg-[#1e293b] hover:bg-[#283548] border border-[#334155] hover:border-sky-500/50 rounded-xl text-left transition group">
            <span class="block text-xs font-bold text-white group-hover:text-sky-400">Tesla</span>
            <span class="text-[10px] text-slate-500">Austin Giga</span>
          </button>
          <button onclick="quickInput('https://stripe.com')" class="p-3 bg-[#1e293b] hover:bg-[#283548] border border-[#334155] hover:border-sky-500/50 rounded-xl text-left transition group">
            <span class="block text-xs font-bold text-white group-hover:text-sky-400">Stripe</span>
            <span class="text-[10px] text-slate-500">stripe.com</span>
          </button>
          <button onclick="quickInput('Figma San Francisco')" class="p-3 bg-[#1e293b] hover:bg-[#283548] border border-[#334155] hover:border-sky-500/50 rounded-xl text-left transition group">
            <span class="block text-xs font-bold text-white group-hover:text-sky-400">Figma</span>
            <span class="text-[10px] text-slate-500">San Francisco</span>
          </button>
        </div>
      </div>

      <!-- LOADER -->
      <div id="progress-loader" class="hidden max-w-2xl mx-auto bg-[#1e293b] border border-[#334155] rounded-2xl p-6 shadow-2xl space-y-4">
        <div class="flex items-center justify-between border-b border-[#334155] pb-4">
          <div class="flex items-center space-x-3">
            <div class="w-8 h-8 rounded-lg bg-sky-500/20 flex items-center justify-center text-sky-400 animate-spin">
              ⚙️
            </div>
            <div>
              <h4 id="progress-title" class="font-bold text-white text-sm">Research Pipeline Active</h4>
              <p id="progress-subtitle" class="text-xs text-slate-400">Executing crawler and 3-tier location engine...</p>
            </div>
          </div>
          <span id="progress-step-badge" class="text-xs font-bold px-2.5 py-1 bg-sky-500/10 text-sky-400 rounded-full border border-sky-500/30">Step 1/4</span>
        </div>

        <div class="space-y-2 text-xs text-slate-300">
          <div id="step-1" class="flex items-center space-x-2 text-sky-400 font-semibold">
            <span>🔍 1. Serper.dev Search & Global Branch Resolver</span>
          </div>
          <div id="step-2" class="flex items-center space-x-2 text-slate-500">
            <span>🕷️ 2. Web Crawler - Page Link Discovery</span>
          </div>
          <div id="step-3" class="flex items-center space-x-2 text-slate-500">
            <span>🧠 3. AI Summary & Product Collection</span>
          </div>
          <div id="step-4" class="flex items-center space-x-2 text-slate-500">
            <span>🎯 4. Competitor Analysis & PDF Compilation</span>
          </div>
        </div>
      </div>

      <!-- RESULT CARD DISPLAY -->
      <div id="result-card" class="hidden max-w-4xl mx-auto bg-[#1e293b] border border-[#334155] rounded-2xl p-6 shadow-2xl space-y-6">

        <!-- HEADER -->
        <div class="flex flex-wrap items-start justify-between gap-4 border-b border-[#334155] pb-5">
          <div>
            <h3 id="res-company-name" onclick="toggleCountryContainer()" class="text-2xl font-bold text-white cursor-pointer hover:text-sky-400 transition flex items-center space-x-2">
              <span id="res-company-name-text">Company Name</span>
              <span class="text-xs text-sky-400 font-normal bg-sky-500/10 px-2 py-0.5 rounded-lg border border-sky-500/30">Click to View Countries ▾</span>
            </h3>
            <a id="res-website-link" href="#" target="_blank" class="text-xs font-mono text-sky-400 hover:underline block mt-1">https://officialwebsite.com</a>
          </div>
          <span class="px-3 py-1 bg-emerald-950/80 text-emerald-400 text-xs font-bold rounded-lg border border-emerald-800/60 tracking-wider">
            RESEARCH COMPLETE
          </span>
        </div>

        <!-- CONDITIONAL PHONE CONTAINER -->
        <div id="phone-container" class="hidden bg-[#0f172a] p-4 rounded-xl border border-[#334155]">
          <span class="block text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">PHONE</span>
          <p id="res-phone" class="text-xs font-semibold text-white"></p>
        </div>

        <!-- 3-TIER LOCATION DRILL-DOWN CONTAINER -->
        <div class="bg-[#0f172a] p-5 rounded-xl border border-[#334155] space-y-4">
          <div class="flex items-center justify-between cursor-pointer" onclick="toggleCountryContainer()">
            <div>
              <span class="block text-[10px] font-bold uppercase tracking-wider text-sky-400 mb-1">3-TIER LOCATION HIERARCHY</span>
              <p class="text-xs text-slate-300 font-medium">
                Click Country → Select City → Reveal Address
              </p>
            </div>
            <button class="text-xs text-sky-400 hover:underline font-bold px-3 py-1.5 bg-sky-500/10 rounded-lg border border-sky-500/30">
              Expand Countries & Branch Locations ▾
            </button>
          </div>

          <div id="country-container" class="hidden pt-3 border-t border-[#334155] space-y-3">
            <!-- Dynamically populated Country cards -->
          </div>
        </div>

        <!-- PRODUCTS & SERVICES PILLS -->
        <div>
          <span class="block text-[10px] font-bold uppercase tracking-wider text-sky-400 mb-2">PRODUCTS & SERVICES</span>
          <div id="res-products-list" class="flex flex-wrap gap-2">
            <!-- Dynamically populated tags -->
          </div>
        </div>

        <!-- DETAILED SUMMARY SECTION -->
        <div>
          <span class="block text-[10px] font-bold uppercase tracking-wider text-sky-400 mb-2">SUMMARY</span>
          <div id="res-summary-list" class="space-y-3 text-xs text-slate-300 leading-relaxed bg-[#0f172a] p-5 rounded-xl border border-[#334155]">
            <!-- Dynamically populated summary paragraphs -->
          </div>
        </div>

        <!-- COMPETITORS GRID -->
        <div>
          <span class="block text-[10px] font-bold uppercase tracking-wider text-sky-400 mb-3">COMPETITORS</span>
          <div id="res-competitors-grid" class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            <!-- Dynamically populated competitor cards -->
          </div>
        </div>

        <!-- ACTION BUTTONS -->
        <div class="flex flex-wrap items-center gap-3 pt-4 border-t border-[#334155]">
          <button onclick="downloadPDF()" class="py-2.5 px-5 bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-400 hover:to-blue-500 text-white font-bold text-xs rounded-xl shadow-lg shadow-sky-500/20 transition flex items-center space-x-2">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
            <span>Download Premium PDF Report</span>
          </button>

          <button id="discord-send-btn" onclick="sendToDiscordManual()" class="py-2.5 px-4 bg-[#0f172a] hover:bg-[#1e293b] border border-[#334155] text-emerald-400 font-semibold text-xs rounded-xl transition flex items-center space-x-2">
            <svg class="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
            <span id="discord-btn-text">Send to Discord</span>
          </button>
        </div>

      </div>

    </div>

    <!-- RESTRICTED CHAT INPUT BAR -->
    <div class="p-4 border-t border-[#334155] bg-[#0f172a]">
      <div class="max-w-4xl mx-auto space-y-2">
        <div class="relative">
          <input type="text" id="company-input" placeholder="" 
                 onkeydown="if(event.key==='Enter') executeResearch()"
                 class="w-full bg-[#1e293b] border border-[#334155] text-white text-xs rounded-xl px-4 py-3 focus:outline-none focus:border-sky-400 pr-28">
          <button onclick="executeResearch()" id="research-submit-btn" class="absolute right-1.5 top-1.5 bottom-1.5 px-4 bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-400 hover:to-blue-500 text-white font-bold text-xs rounded-lg shadow-md transition flex items-center space-x-1">
            <span>Research</span>
            <span>→</span>
          </button>
        </div>

        <p class="text-[10px] text-sky-400 font-medium uppercase tracking-widest text-center">
          ENTER COMPANY NAME, COMPANY NAME & CITY, OR WEBSITE URL ONLY
        </p>
      </div>
    </div>

  </main>

  <!-- HIDDEN PRINTABLE TEMPLATE -->
  <div id="pdf-printable-template" class="hidden font-sans text-gray-900 bg-white p-8 max-w-4xl">
    <div style="background-color: #0f172a; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
      <p style="color: #38bdf8; font-size: 11px; font-weight: bold; margin: 0; text-transform: uppercase; tracking-wide: 1px;">RELU CONSULTANCY · COMPANY RESEARCH REPORT</p>
      <h1 id="pdf-company-title" style="color: white; font-size: 26px; font-weight: bold; margin: 8px 0 0 0;">Company Name</h1>
    </div>

    <div style="margin-bottom: 20px;">
      <h3 style="color: #0284c7; font-size: 14px; font-weight: bold; border-bottom: 2px solid #0284c7; padding-bottom: 4px; margin-bottom: 12px;">COMPANY INFORMATION</h3>
      <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
        <tr style="background-color: #f8fafc; border: 1px solid #cbd5e1;">
          <td style="padding: 8px; font-weight: bold; width: 140px;">Website</td>
          <td id="pdf-website" style="padding: 8px; color: #0284c7;">https://officialwebsite.com</td>
        </tr>
        <tr id="pdf-phone-row" style="background-color: #f8fafc; border: 1px solid #cbd5e1;">
          <td style="padding: 8px; font-weight: bold;">Phone</td>
          <td id="pdf-phone" style="padding: 8px;">-</td>
        </tr>
        <tr style="background-color: #f8fafc; border: 1px solid #cbd5e1;">
          <td style="padding: 8px; font-weight: bold; vertical-align: top;">Branch Locations</td>
          <td id="pdf-locations" style="padding: 8px; line-height: 1.6;">-</td>
        </tr>
      </table>
    </div>

    <div style="margin-bottom: 20px;">
      <h3 style="color: #0284c7; font-size: 14px; font-weight: bold; border-bottom: 2px solid #0284c7; padding-bottom: 4px; margin-bottom: 12px;">PRODUCTS & SERVICES</h3>
      <ul id="pdf-products" style="margin: 0; padding-left: 20px; font-size: 12px; line-height: 1.8;">
      </ul>
    </div>

    <div style="margin-bottom: 20px;">
      <h3 style="color: #0284c7; font-size: 14px; font-weight: bold; border-bottom: 2px solid #0284c7; padding-bottom: 4px; margin-bottom: 12px;">SUMMARY</h3>
      <div id="pdf-summary" style="font-size: 12px; line-height: 1.6; space-y: 10px;">
      </div>
    </div>

    <div style="margin-bottom: 20px;">
      <h3 style="color: #0284c7; font-size: 14px; font-weight: bold; border-bottom: 2px solid #0284c7; padding-bottom: 4px; margin-bottom: 12px;">COMPETITORS</h3>
      <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
        <tbody id="pdf-competitors">
        </tbody>
      </table>
    </div>
  </div>

  <script>
    let currentReportData = null;

    window.addEventListener('DOMContentLoaded', () => {
      document.getElementById('discord-token').value = localStorage.getItem('discord_token') || '';
      document.getElementById('discord-channel').value = localStorage.getItem('discord_channel') || '';
      document.getElementById('applicant-name').value = localStorage.getItem('applicant_name') || '';
      document.getElementById('applicant-email').value = localStorage.getItem('applicant_email') || '';
      document.getElementById('serper-key').value = localStorage.getItem('serper_key') || '';
      document.getElementById('openrouter-key').value = localStorage.getItem('openrouter_key') || '';

      const savedModel = localStorage.getItem('selected_model') || 'google/gemini-2.0-flash-001';
      const modelSelect = document.getElementById('model-select');
      const customBox = document.getElementById('custom-model-box');
      const customInput = document.getElementById('custom-model-input');

      let found = false;
      for (let i = 0; i < modelSelect.options.length; i++) {
        if (modelSelect.options[i].value === savedModel) {
          modelSelect.selectedIndex = i;
          found = true;
          break;
        }
      }
      if (!found && savedModel) {
        modelSelect.value = 'custom';
        customBox.classList.remove('hidden');
        customInput.value = savedModel;
      }
    });

    function handleModelChange() {
      const val = document.getElementById('model-select').value;
      const customBox = document.getElementById('custom-model-box');
      if (val === 'custom') {
        customBox.classList.remove('hidden');
      } else {
        customBox.classList.add('hidden');
      }
    }

    function switchTab(tab) {
      const apiBtn = document.getElementById('tab-api-btn');
      const discordBtn = document.getElementById('tab-discord-btn');
      const apiPanel = document.getElementById('api-panel');
      const discordPanel = document.getElementById('discord-panel');

      if (tab === 'discord') {
        discordBtn.className = 'py-1.5 text-xs font-semibold rounded-lg bg-sky-500 text-slate-950 font-bold transition shadow-md';
        apiBtn.className = 'py-1.5 text-xs font-semibold rounded-lg text-slate-400 hover:text-white transition';
        discordPanel.classList.remove('hidden');
        apiPanel.classList.add('hidden');
      } else {
        apiBtn.className = 'py-1.5 text-xs font-semibold rounded-lg bg-sky-500 text-slate-950 font-bold transition shadow-md';
        discordBtn.className = 'py-1.5 text-xs font-semibold rounded-lg text-slate-400 hover:text-white transition';
        apiPanel.classList.remove('hidden');
        discordPanel.classList.add('hidden');
      }
    }

    function saveAPISettings() {
      const orKey = document.getElementById('openrouter-key').value.trim();
      const serpKey = document.getElementById('serper-key').value.trim();
      
      const modelChoice = document.getElementById('model-select').value;
      let finalModel = modelChoice;
      if (modelChoice === 'custom') {
        finalModel = document.getElementById('custom-model-input').value.trim() || 'google/gemini-2.0-flash-001';
      }

      localStorage.setItem('openrouter_key', orKey);
      localStorage.setItem('serper_key', serpKey);
      localStorage.setItem('selected_model', finalModel);

      const btn = document.getElementById('save-api-btn');
      btn.innerHTML = 'Saved ✓';
      btn.className = 'w-full mt-2 py-2.5 bg-emerald-600 text-white font-semibold text-xs rounded-xl transition';
      setTimeout(() => {
        btn.className = 'w-full mt-2 py-2.5 bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-400 hover:to-blue-500 text-white font-bold text-xs rounded-xl shadow-lg shadow-sky-500/20 transition';
      }, 2000);
    }

    function saveDiscordSettings() {
      const dToken = document.getElementById('discord-token').value.trim();
      const dChannel = document.getElementById('discord-channel').value.trim();
      const aName = document.getElementById('applicant-name').value.trim();
      const aEmail = document.getElementById('applicant-email').value.trim();

      localStorage.setItem('discord_token', dToken);
      localStorage.setItem('discord_channel', dChannel);
      localStorage.setItem('applicant_name', aName);
      localStorage.setItem('applicant_email', aEmail);

      const btn = document.getElementById('save-discord-btn');
      btn.innerHTML = 'Saved ✓';
      btn.className = 'w-full mt-3 py-2.5 bg-emerald-600 text-white font-semibold text-xs rounded-xl transition';
      setTimeout(() => {
        btn.className = 'w-full mt-3 py-2.5 bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-400 hover:to-blue-500 text-white font-bold text-xs rounded-xl shadow-lg shadow-sky-500/20 transition';
      }, 2000);
    }

    function quickInput(val) {
      document.getElementById('company-input').value = val;
      executeResearch();
    }

    function startNewResearch() {
      document.getElementById('company-input').value = '';
      document.getElementById('welcome-view').classList.remove('hidden');
      document.getElementById('progress-loader').classList.add('hidden');
      document.getElementById('result-card').classList.add('hidden');
      currentReportData = null;
    }

    function isValidCompanyInput(inputStr) {
      const trimmed = inputStr.trim();
      if (!trimmed || trimmed.length < 2) return false;
      if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) return true;
      if (/^[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(\/.*)?$/i.test(trimmed)) return true;

      const noisePatterns = [
        /^hi$/i, /^hello$/i, /^hey$/i, /^who are you/i, /^how are you/i,
        /^what is/i, /^tell me/i, /^code me/i, /^joke/i, /^weather/i, /^help$/i
      ];

      for (let pat of noisePatterns) {
        if (pat.test(trimmed)) return false;
      }
      return true;
    }

    async function executeResearch() {
      const rawInput = document.getElementById('company-input').value;
      const openrouterKey = (document.getElementById('openrouter-key').value || localStorage.getItem('openrouter_key') || '').trim();

      if (!openrouterKey) {
        switchTab('api');
        alert("⚠️ Please enter your OpenRouter API Key in the API tab on the left sidebar and click 'Save Model & Keys ✓' before running research.");
        return;
      }

      if (!isValidCompanyInput(rawInput)) {
        alert("Please enter a valid Company Name, Company Name with City, or Company Website URL (e.g. TCS, TCS Chennai, or https://www.tcs.com).");
        return;
      }

      const inputVal = rawInput.trim();

      const modelSelectVal = document.getElementById('model-select').value;
      let modelToUse = modelSelectVal;
      if (modelSelectVal === 'custom') {
        modelToUse = (document.getElementById('custom-model-input').value || localStorage.getItem('selected_model') || '').trim();
      } else {
        modelToUse = modelSelectVal || localStorage.getItem('selected_model') || 'google/gemini-2.0-flash-001';
      }

      document.getElementById('welcome-view').classList.add('hidden');
      document.getElementById('result-card').classList.add('hidden');
      document.getElementById('progress-loader').classList.remove('hidden');

      updateProgressStep(1, "🔍 1. Serper.dev Search & Global Branch Resolver");

      try {
        setTimeout(() => updateProgressStep(2, "🕷️ 2. Web Crawler - Page Link Discovery"), 350);
        setTimeout(() => updateProgressStep(3, "🧠 3. AI Summary & Product Collection"), 700);
        setTimeout(() => updateProgressStep(4, "🎯 4. Competitor Analysis & PDF Compilation"), 1050);

        const response = await fetch('/api/research', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            endpoint: 'research',
            input: inputVal,
            serper_key: (document.getElementById('serper-key').value || localStorage.getItem('serper_key') || '').trim(),
            openrouter_key: openrouterKey,
            selected_model: modelToUse
          })
        });

        const data = await response.json();

        if (data.error) {
          alert('API / Research Error: ' + data.error);
          document.getElementById('progress-loader').classList.add('hidden');
          document.getElementById('welcome-view').classList.remove('hidden');
          return;
        }

        currentReportData = data.report;
        renderReportResult(data.report);
        autoSendToDiscord(data.report);

      } catch (err) {
        alert('Server Error: ' + err.message);
        document.getElementById('progress-loader').classList.add('hidden');
        document.getElementById('welcome-view').classList.remove('hidden');
      }
    }

    function updateProgressStep(stepNum, text) {
      document.getElementById('progress-step-badge').innerText = `Step ${stepNum}/4`;
      for (let i = 1; i <= 4; i++) {
        const el = document.getElementById(`step-${i}`);
        if (i === stepNum) {
          el.className = "flex items-center space-x-2 text-sky-400 font-semibold pulse-glow";
        } else if (i < stepNum) {
          el.className = "flex items-center space-x-2 text-emerald-400 font-semibold";
        } else {
          el.className = "flex items-center space-x-2 text-slate-500";
        }
      }
    }

    function toggleCountryContainer() {
      const container = document.getElementById('country-container');
      container.classList.toggle('hidden');
    }

    function toggleCountryCities(countryIdx) {
      const citiesBox = document.getElementById(`country-cities-${countryIdx}`);
      if (citiesBox) citiesBox.classList.toggle('hidden');
    }

    function toggleCityAddress(cityId) {
      const addrBox = document.getElementById(`city-addr-${cityId}`);
      if (addrBox) addrBox.classList.toggle('hidden');
    }

    function renderReportResult(report) {
      document.getElementById('progress-loader').classList.add('hidden');
      document.getElementById('result-card').classList.remove('hidden');

      document.getElementById('res-company-name-text').innerText = report.company_name;
      const websiteLink = document.getElementById('res-website-link');
      websiteLink.innerText = report.website;
      websiteLink.href = report.website.startsWith('http') ? report.website : `https://${report.website}`;

      const phoneContainer = document.getElementById('phone-container');
      const phoneVal = (report.phone || '').trim();
      if (phoneVal && !phoneVal.toLowerCase().includes('not')) {
        phoneContainer.classList.remove('hidden');
        document.getElementById('res-phone').innerText = phoneVal;
      } else {
        phoneContainer.classList.add('hidden');
      }

      const countryContainer = document.getElementById('country-container');
      countryContainer.innerHTML = '';
      countryContainer.classList.add('hidden');

      const locs = report.locations || [];
      if (Array.isArray(locs) && locs.length > 0) {
        locs.forEach((countryObj, cIdx) => {
          const countryCard = document.createElement('div');
          countryCard.className = 'bg-[#1e293b] p-4 rounded-xl border border-[#334155] space-y-3';

          const cities = countryObj.cities || [];
          let citiesHtml = '';

          cities.forEach((cityObj, ctIdx) => {
            const uniqueCityId = `${cIdx}-${ctIdx}`;
            const addrs = cityObj.addresses || [];
            const addrsHtml = addrs.map(addr => `
              <div class="p-2.5 bg-[#0f172a] rounded-lg border border-[#334155] text-xs text-slate-300 flex items-start space-x-2 leading-relaxed">
                <span class="text-sky-400 mt-0.5">🏢</span>
                <span>${addr}</span>
              </div>
            `).join('');

            citiesHtml += `
              <div class="bg-[#0f172a] p-3 rounded-lg border border-[#334155] space-y-2">
                <div class="flex items-center justify-between cursor-pointer" onclick="toggleCityAddress('${uniqueCityId}')">
                  <div class="flex items-center space-x-2">
                    <span class="text-sm">🏙️</span>
                    <span class="font-bold text-xs text-white hover:text-sky-400">City: ${cityObj.city_name}</span>
                    <span class="text-[10px] text-slate-400 font-normal">(${addrs.length} Address)</span>
                  </div>
                  <span class="text-xs text-sky-400 font-bold">Click City to view address ▾</span>
                </div>
                <div id="city-addr-${uniqueCityId}" class="hidden space-y-1.5 pt-2 border-t border-[#334155]">
                  ${addrsHtml}
                </div>
              </div>
            `;
          });

          countryCard.innerHTML = `
            <div class="flex items-center justify-between cursor-pointer" onclick="toggleCountryCities(${cIdx})">
              <div class="flex items-center space-x-2">
                <span class="text-base">🌍</span>
                <span class="font-bold text-sm text-white hover:text-sky-400">Country: ${countryObj.country_name}</span>
                <span class="text-xs text-sky-400 font-semibold">(${cities.length} Cities)</span>
              </div>
              <span class="text-xs text-sky-400 font-bold px-2.5 py-1 bg-sky-500/10 rounded-lg border border-sky-500/30">
                Click Country to Expand Cities ▾
              </span>
            </div>
            <div id="country-cities-${cIdx}" class="hidden pt-3 border-t border-[#334155] space-y-2">
              ${citiesHtml}
            </div>
          `;

          countryContainer.appendChild(countryCard);
        });
      } else {
        countryContainer.innerHTML = `<p class="text-xs text-slate-400 italic p-3">No country location hierarchy available.</p>`;
      }

      const prodList = document.getElementById('res-products-list');
      prodList.innerHTML = '';
      (report.products_and_services || []).forEach(p => {
        const pill = document.createElement('span');
        pill.className = 'px-3 py-1.5 bg-sky-950/60 text-sky-200 text-xs font-medium rounded-xl border border-sky-800/60 shadow-sm';
        pill.innerText = p;
        prodList.appendChild(pill);
      });

      const summaryList = document.getElementById('res-summary-list');
      summaryList.innerHTML = '';
      const summaryItems = report.summary || report.pain_points || [];
      summaryItems.forEach((pt, i) => {
        const itemBox = document.createElement('div');
        itemBox.className = 'flex items-start space-x-3 p-3.5 rounded-xl bg-[#1e293b] border border-[#334155] shadow-sm';
        itemBox.innerHTML = `
          <span class="w-5 h-5 rounded-full bg-sky-500/20 text-sky-400 text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">${i+1}</span>
          <p class="text-xs text-slate-200 leading-relaxed font-normal">${pt}</p>
        `;
        summaryList.appendChild(itemBox);
      });

      const compGrid = document.getElementById('res-competitors-grid');
      compGrid.innerHTML = '';
      (report.competitors || []).forEach(c => {
        const card = document.createElement('a');
        card.href = c.website.startsWith('http') ? c.website : `https://${c.website}`;
        card.target = '_blank';
        card.className = 'p-3 bg-[#0f172a] border border-[#334155] hover:border-sky-400 rounded-xl transition block group shadow-sm';
        card.innerHTML = `
          <span class="block text-xs font-bold text-white group-hover:text-sky-400">${c.name}</span>
          <span class="text-[10px] text-slate-500 truncate block mt-0.5">${c.website}</span>
        `;
        compGrid.appendChild(card);
      });

      document.getElementById('pdf-company-title').innerText = report.company_name;
      document.getElementById('pdf-website').innerText = report.website;

      const pdfPhoneRow = document.getElementById('pdf-phone-row');
      if (phoneVal && !phoneVal.toLowerCase().includes('not')) {
        pdfPhoneRow.style.display = 'table-row';
        document.getElementById('pdf-phone').innerText = phoneVal;
      } else {
        pdfPhoneRow.style.display = 'none';
      }

      let pdfLocHtml = '';
      if (Array.isArray(report.locations)) {
        report.locations.forEach(c => {
          pdfLocHtml += `<strong>🌍 ${c.country_name}</strong><br/>`;
          (c.cities || []).forEach(city => {
            pdfLocHtml += `&nbsp;&nbsp;&nbsp;&nbsp;• <strong>${city.city_name}:</strong> ${(city.addresses || []).join(', ')}<br/>`;
          });
        });
      }
      document.getElementById('pdf-locations').innerHTML = pdfLocHtml || '-';

      let pdfProdHtml = '';
      (report.products_and_services || []).forEach(p => {
        pdfProdHtml += `<li><strong>${p}</strong></li>`;
      });
      document.getElementById('pdf-products').innerHTML = pdfProdHtml;

      let pdfSummaryHtml = '';
      (report.summary || report.pain_points || []).forEach((pt, idx) => {
        pdfSummaryHtml += `<p style="margin-bottom: 8px;"><strong>${idx+1}.</strong> ${pt}</p>`;
      });
      document.getElementById('pdf-summary').innerHTML = pdfSummaryHtml;

      let pdfCompHtml = '';
      (report.competitors || []).forEach(c => {
        pdfCompHtml += `<tr style="background-color: #f8fafc; border: 1px solid #cbd5e1;"><td style="padding: 6px; font-weight: bold;">${c.name}</td><td style="padding: 6px; color: #0284c7;">${c.website}</td></tr>`;
      });
      document.getElementById('pdf-competitors').innerHTML = pdfCompHtml;
    }

    async function downloadPDF() {
      if (!currentReportData) return;
      
      const element = document.getElementById('pdf-printable-template');
      element.classList.remove('hidden');

      const opt = {
        margin:       [0.4, 0.4, 0.4, 0.4],
        filename:     `${currentReportData.company_name.toLowerCase().replace(/ /g, '_')}_research_report.pdf`,
        image:        { type: 'jpeg', quality: 0.98 },
        html2canvas:  { scale: 2, useCORS: true, logging: false },
        jsPDF:        { unit: 'in', format: 'letter', orientation: 'portrait' }
      };

      try {
        await html2pdf().set(opt).from(element).save();
      } catch (e) {
        const res = await fetch('/api/download-pdf', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ endpoint: 'download-pdf', report: currentReportData })
        });
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${currentReportData.company_name.toLowerCase().replace(/ /g, '_')}_research_report.pdf`;
        document.body.appendChild(a);
        a.click();
        a.remove();
      } finally {
        element.classList.add('hidden');
      }
    }

    async function autoSendToDiscord(report) {
      const token = (document.getElementById('discord-token').value || localStorage.getItem('discord_token') || '').trim();
      const channel = (document.getElementById('discord-channel').value || localStorage.getItem('discord_channel') || '').trim();
      const name = (document.getElementById('applicant-name').value || localStorage.getItem('applicant_name') || '').trim();
      const email = (document.getElementById('applicant-email').value || localStorage.getItem('applicant_email') || '').trim();
      const btnText = document.getElementById('discord-btn-text');

      if (!token || !channel) {
        btnText.innerText = "Send to Discord";
        return;
      }

      btnText.innerText = "Sending to Discord...";

      try {
        const res = await fetch('/api/discord', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            endpoint: 'discord',
            bot_token: token,
            channel_id: channel,
            applicant_name: name,
            applicant_email: email,
            report: report
          })
        });
        const data = await res.json();
        if (data.success) {
          btnText.innerText = "✓ Sent to Discord";
        } else {
          btnText.innerText = "Discord Error (Click to retry)";
          alert('Discord Error: ' + (data.error || 'Failed to post message'));
        }
      } catch (e) {
        btnText.innerText = "Send to Discord";
        alert('Discord Error: ' + e.message);
      }
    }

    function sendToDiscordManual() {
      if (currentReportData) autoSendToDiscord(currentReportData);
    }
  </script>
</body>
</html>'''

if __name__ == "__main__":
    print(f"============================================================")
    print(f"Relu Consultancy - AI Company Research Assistant")
    print(f"Starting server on http://localhost:{PORT}...")
    print(f"============================================================")
    
    server = HTTPServer(("0.0.0.0", PORT), handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server gracefully...")
        server.server_close()
