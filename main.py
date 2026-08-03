"""
Main Python Application & Web Server for CorpIntel AI.
Supports local execution (python main.py) and Vercel Serverless Function deployment.
Features Dribbble Soft Neumorphic UI, Light Theme Default, Exhaustive Multi-Country Branches, and PDF Export.
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

PORT = int(os.environ.get("PORT", 8000))

class ReluRequestHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler providing REST API endpoints and Web UI serving."""
    
    def log_message(self, format, *args):
        print(f"[CorpIntel AI Server]: {self.address_string()} - {args[0]}")

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
        if self.path in ["/", "/index.html"]:
            html_content = get_web_ui_html()
            self.send_bytes(html_content.encode("utf-8"), "text/html; charset=utf-8")
        elif self.path == "/api/health":
            self.send_json({"status": "ok", "app": "CorpIntel AI"})
        else:
            self.send_json({"error": "Not Found"}, 404)

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_length).decode("utf-8")
        
        try:
            req_data: dict[str, Any] = json.loads(post_body) if post_body else {}
        except Exception:
            req_data = {}

        if self.path == "/api/research":
            self.handle_research_api(req_data)
        elif self.path == "/api/download-pdf":
            self.handle_pdf_download_api(req_data)
        else:
            self.send_json({"error": "Endpoint not found"}, 404)

    def handle_research_api(self, req_data: dict[str, Any]):
        input_text = req_data.get("input", "").strip()

        if not input_text:
            self.send_json({"error": "Please provide a company name, company and city name, or company website."}, 400)
            return

        print(f"\n[CorpIntel AI Research Pipeline Started]: Input='{input_text}'")

        domain_info: dict[str, Any] = resolve_domain(input_text)
        official_url = domain_info.get("official_website", "")
        company_name = domain_info.get("company_name", input_text)
        
        serper_data: dict[str, Any] = domain_info.get("serper_context") or search_serper(f"{company_name} official website founded CEO headquarters interview questions culture")
        
        print(f"[Web Crawler]: Crawling domain '{official_url}'...")
        crawl_data: dict[str, Any] = crawl_company_website(official_url, max_pages=6)

        print(f"[CorpIntel AI Engine]: Generating company research & candidate interview preparation for '{company_name}'...")
        report_dict: dict[str, Any] = generate_company_research(
            company_name=company_name,
            website_url=official_url,
            crawl_data=crawl_data,
            serper_data=serper_data
        )

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


# VERCEL SERVERLESS WSGI ADAPTER
def app(environ, start_response):
    """WSGI adapter function for Vercel deployment."""
    path = environ.get("PATH_INFO", "/")
    method = environ.get("REQUEST_METHOD", "GET")
    
    if method == "OPTIONS":
        headers = [
            ("Content-Type", "application/json"),
            ("Access-Control-Allow-Origin", "*"),
            ("Access-Control-Allow-Headers", "Content-Type"),
            ("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        ]
        start_response("200 OK", headers)
        return [b""]

    if method == "GET":
        if path in ["/", "/index.html"]:
            html_content = get_web_ui_html().encode("utf-8")
            headers = [
                ("Content-Type", "text/html; charset=utf-8"),
                ("Content-Length", str(len(html_content))),
                ("Access-Control-Allow-Origin", "*")
            ]
            start_response("200 OK", headers)
            return [html_content]
        elif path == "/api/health":
            body = json.dumps({"status": "ok", "app": "CorpIntel AI"}).encode("utf-8")
            headers = [
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(body))),
                ("Access-Control-Allow-Origin", "*")
            ]
            start_response("200 OK", headers)
            return [body]

    if method == "POST":
        try:
            length = int(environ.get("CONTENT_LENGTH", 0))
            body_bytes = environ["wsgi.input"].read(length)
            req_data = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except Exception:
            req_data = {}

        if path == "/api/research":
            input_text = req_data.get("input", "").strip()
            if not input_text:
                resp = json.dumps({"error": "Invalid input"}).encode("utf-8")
                start_response("400 Bad Request", [("Content-Type", "application/json")])
                return [resp]

            domain_info = resolve_domain(input_text)
            official_url = domain_info.get("official_website", "")
            company_name = domain_info.get("company_name", input_text)
            serper_data = domain_info.get("serper_context") or search_serper(f"{company_name} official website founded CEO headquarters interview questions culture")
            crawl_data = crawl_company_website(official_url, max_pages=6)
            report_dict = generate_company_research(company_name, official_url, crawl_data, serper_data)

            payload = json.dumps({"status": "success", "domain_info": domain_info, "report": report_dict}).encode("utf-8")
            headers = [
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(payload))),
                ("Access-Control-Allow-Origin", "*")
            ]
            start_response("200 OK", headers)
            return [payload]

        elif path == "/api/download-pdf":
            report = req_data.get("report", {})
            pdf_bytes = generate_pdf_report(report)
            headers = [
                ("Content-Type", "application/pdf"),
                ("Content-Length", str(len(pdf_bytes))),
                ("Content-Disposition", 'attachment; filename="research_report.pdf"'),
                ("Access-Control-Allow-Origin", "*")
            ]
            start_response("200 OK", headers)
            return [pdf_bytes]

    start_response("404 Not Found", [("Content-Type", "application/json")])
    return [json.dumps({"error": "Not Found"}).encode("utf-8")]


handler = app


def get_web_ui_html() -> str:
    """Returns single-page Dribbble neumorphic UI HTML with Light Theme Default and Exhaustive Multi-Country Branch Resolver."""
    return '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CorpIntel AI - Corporate Intelligence Assistant</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          colors: {
            brandOrange: '#f97316',
            brandOrangeHover: '#ea580c',
            brandBlue: '#0ea5e9',
            lightBlueAccent: '#38bdf8',
          }
        }
      }
    }
  </script>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    body { font-family: 'Plus Jakarta Sans', sans-serif; transition: background-color 0.3s ease, color 0.3s ease; }
    .sidebar-transition { transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
    .glass-card { backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); }
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(156, 163, 175, 0.4); border-radius: 9999px; }
    .pulse-glow { animation: pulse 2s infinite; }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
  </style>
</head>
<body class="h-screen p-3 md:p-6 bg-[#e0e2e5] dark:bg-[#121316] text-gray-900 dark:text-gray-100 flex overflow-hidden">

  <!-- OUTER FLOATING CONTAINER MATCHING DRIBBBLE DESIGN -->
  <div class="w-full h-full flex gap-4 md:gap-6 overflow-hidden max-w-[1700px] mx-auto">

    <!-- FLOATING LEFT SIDEBAR -->
    <aside id="sidebar-panel" class="sidebar-transition w-72 bg-[#2a2b2e] text-white rounded-3xl p-4 flex flex-col justify-between shadow-2xl shrink-0 relative overflow-hidden z-20">
      
      <div class="space-y-4">
        
        <!-- TOP STACK: + NEW RESEARCH BUTTON -->
        <button onclick="startNewResearch()" id="new-research-btn" title="New Research" class="w-full py-3 px-3 rounded-2xl bg-[#37383c] hover:bg-[#45464b] border border-gray-700/50 transition font-semibold flex items-center justify-center space-x-2 text-xs text-white shadow-md">
          <span class="text-base text-brandOrange font-bold">+</span>
          <span class="sidebar-label text-xs tracking-wide">New Research</span>
        </button>

        <!-- STACKED DIRECTLY BELOW + NEW RESEARCH: SHRINK SIDEBAR TOGGLE BUTTON -->
        <button onclick="toggleSidebarShrink()" id="shrink-toggle-btn" title="Toggle Sidebar" class="w-full py-2.5 px-3 rounded-2xl bg-[#37383c] hover:bg-[#45464b] border border-gray-700/50 flex items-center justify-center space-x-2 text-gray-300 hover:text-white transition shadow-sm">
          <span id="shrink-icon" class="text-xs font-bold">◄</span>
          <span class="sidebar-label text-xs font-semibold">Collapse</span>
        </button>

        <!-- NAVIGATION / HISTORY SECTION -->
        <div class="space-y-3 pt-2">
          
          <!-- UNSHRINKED HEADER -->
          <div class="sidebar-label flex items-center justify-between px-1">
            <h4 class="text-[10px] font-bold uppercase tracking-widest text-gray-400">RECENT HISTORY</h4>
            <button onclick="clearSearchHistory()" class="text-[10px] text-gray-500 hover:text-red-400 transition font-mono">Clear</button>
          </div>
          
          <!-- SHRINKED RECENT BUTTON (SINGLE BUTTON WHEN SHRINKED) -->
          <button id="shrinked-recents-btn" onclick="toggleSidebarShrink()" title="Recent History" class="hidden w-full p-3 rounded-2xl bg-[#37383c] hover:bg-[#45464b] border border-gray-700/50 flex items-center justify-center text-brandOrange transition">
            <span class="text-sm font-bold">🕒</span>
          </button>

          <!-- FULL RECENT HISTORY LIST -->
          <div id="history-list" class="space-y-2 max-h-[50vh] overflow-y-auto pr-1">
            <!-- Dynamically populated search history -->
          </div>
        </div>

      </div>

      <!-- BOTTOM PROFILE / HOW IT WORKS CARD MATCHING DRIBBBLE UI -->
      <div id="sidebar-footer-card" class="bg-[#1f2023] p-4 rounded-2xl border border-gray-800 space-y-2">
        <div class="flex items-center space-x-2">
          <div class="w-6 h-6 rounded-full bg-brandOrange/20 text-brandOrange flex items-center justify-center font-bold text-xs">
            ⚡
          </div>
          <span class="sidebar-label text-xs font-bold text-gray-200">Research Features</span>
        </div>
        <p class="sidebar-label text-[11px] text-gray-400 leading-relaxed">
          Search company name or website to explore branches, interview prep, and PDF reports.
        </p>
      </div>

    </aside>

    <!-- FLOATING MAIN CONTENT PANEL MATCHING DRIBBBLE UI -->
    <main class="flex-1 bg-[#f5f6f8] dark:bg-[#1a1b1f] rounded-3xl border border-white/60 dark:border-gray-800/80 shadow-2xl flex flex-col h-full overflow-hidden relative">

      <!-- TOP HEADER BAR -->
      <header class="h-16 border-b border-gray-200/80 dark:border-gray-800 px-6 md:px-8 flex items-center justify-between bg-white/70 dark:bg-[#1a1b1f]/70 backdrop-blur shrink-0">
        <div class="flex items-center space-x-3">
          <h2 class="font-extrabold text-gray-900 dark:text-white text-lg md:text-xl tracking-tight">CorpIntel AI</h2>
          <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-brandOrange/10 text-brandOrange border border-brandOrange/20">
            <span class="w-1.5 h-1.5 rounded-full bg-brandOrange mr-1.5 pulse-glow"></span> Enterprise AI
          </span>
        </div>

        <!-- RIGHT HEADER ACTIONS: THEME TOGGLE -->
        <div class="flex items-center space-x-3">
          
          <!-- LIGHT / DARK MODE TOGGLE BUTTON (DEFAULT LIGHT THEME) -->
          <button onclick="toggleThemeMode()" id="theme-toggle-btn" class="p-2.5 rounded-2xl bg-gray-100 dark:bg-[#25272c] border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-200 hover:scale-105 transition shadow-sm flex items-center space-x-2 text-xs font-semibold">
            <span id="theme-icon">☀️</span>
            <span id="theme-text" class="hidden sm:inline">Light</span>
          </button>

        </div>
      </header>

      <!-- SCROLLABLE BODY CONTENT -->
      <div id="content-container" class="flex-1 overflow-y-auto p-6 md:p-10 space-y-6">

        <!-- WELCOME HERO VIEW MATCHING DRIBBBLE SCREENSHOT LAYOUT -->
        <div id="welcome-view" class="max-w-4xl mx-auto space-y-8 py-6">

          <div class="flex flex-col md:flex-row items-center justify-between gap-6 bg-white dark:bg-[#23252a] p-8 rounded-3xl border border-gray-100 dark:border-gray-800 shadow-xl">
            <div class="space-y-3 text-center md:text-left flex-1">
              <h1 class="text-3xl md:text-4xl font-extrabold text-gray-900 dark:text-white tracking-tight leading-tight">
                Let's start <br/><span class="text-brandOrange">smart corporate research!</span>
              </h1>
              <p class="text-xs md:text-sm text-gray-500 dark:text-gray-400 leading-relaxed max-w-lg">
                Enter any company name, company with city name, or official website to generate location branch hierarchies, executive summaries, products, and authentic candidate interview preparation.
              </p>
            </div>

            <!-- DRIBBBLE STYLE HERO CARD DECORATION -->
            <div class="w-full md:w-72 bg-gradient-to-br from-brandOrange/10 to-brandBlue/10 p-5 rounded-2xl border border-brandOrange/20 space-y-3">
              <div class="flex items-center justify-between">
                <span class="text-xs font-bold text-gray-700 dark:text-gray-300">Target Coverage</span>
                <span class="text-xs font-extrabold text-brandOrange">Global HQ & Branches</span>
              </div>
              <div class="w-full bg-gray-200 dark:bg-gray-700 h-2 rounded-full overflow-hidden">
                <div class="bg-brandOrange h-full w-4/5 rounded-full"></div>
              </div>
              <p class="text-[11px] text-gray-500 dark:text-gray-400">Multi-country branch addresses & interview preparation facts.</p>
            </div>
          </div>

          <!-- QUICK SUGGESTIONS CARDS -->
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <button onclick="quickInput('TCS Chennai')" class="p-4 bg-white dark:bg-[#23252a] hover:border-brandOrange border border-gray-100 dark:border-gray-800 rounded-2xl text-left transition shadow-md group">
              <span class="block text-xs font-bold text-gray-900 dark:text-white group-hover:text-brandOrange">TCS</span>
              <span class="text-[11px] text-gray-400">Chennai Hub</span>
            </button>
            <button onclick="quickInput('https://www.tcs.com/')" class="p-4 bg-white dark:bg-[#23252a] hover:border-brandOrange border border-gray-100 dark:border-gray-800 rounded-2xl text-left transition shadow-md group">
              <span class="block text-xs font-bold text-gray-900 dark:text-white group-hover:text-brandOrange">TCS Global</span>
              <span class="text-[11px] text-gray-400">tcs.com</span>
            </button>
            <button onclick="quickInput('Tesla Austin')" class="p-4 bg-white dark:bg-[#23252a] hover:border-brandOrange border border-gray-100 dark:border-gray-800 rounded-2xl text-left transition shadow-md group">
              <span class="block text-xs font-bold text-gray-900 dark:text-white group-hover:text-brandOrange">Tesla</span>
              <span class="text-[11px] text-gray-400">Austin Gigafactory</span>
            </button>
            <button onclick="quickInput('Figma San Francisco')" class="p-4 bg-white dark:bg-[#23252a] hover:border-brandOrange border border-gray-100 dark:border-gray-800 rounded-2xl text-left transition shadow-md group">
              <span class="block text-xs font-bold text-gray-900 dark:text-white group-hover:text-brandOrange">Figma</span>
              <span class="text-[11px] text-gray-400">San Francisco HQ</span>
            </button>
          </div>

        </div>

        <!-- PROGRESS LOADER -->
        <div id="progress-loader" class="hidden max-w-2xl mx-auto bg-white dark:bg-[#23252a] border border-gray-100 dark:border-gray-800 rounded-3xl p-6 md:p-8 shadow-2xl space-y-5">
          <div class="flex items-center justify-between border-b border-gray-100 dark:border-gray-800 pb-4">
            <div class="flex items-center space-x-3">
              <div class="w-10 h-10 rounded-2xl bg-brandOrange/10 flex items-center justify-center text-brandOrange font-bold animate-spin text-lg">
                ⚙️
              </div>
              <div>
                <h4 id="progress-title" class="font-bold text-gray-900 dark:text-white text-sm">CorpIntel Research Active</h4>
                <p id="progress-subtitle" class="text-xs text-gray-400">Executing web crawler & AI engine...</p>
              </div>
            </div>
            <span id="progress-step-badge" class="text-xs font-bold px-3 py-1 bg-brandOrange/10 text-brandOrange rounded-full border border-brandOrange/20">Step 1/4</span>
          </div>

          <div class="space-y-3 text-xs text-gray-600 dark:text-gray-300">
            <div id="step-1" class="flex items-center space-x-2 text-brandOrange font-semibold">
              <span>🔍 1. Search & Multi-Country Office Resolver</span>
            </div>
            <div id="step-2" class="flex items-center space-x-2 text-gray-400">
              <span>🕷️ 2. Web Crawler - Page Link Discovery</span>
            </div>
            <div id="step-3" class="flex items-center space-x-2 text-gray-400">
              <span>🧠 3. AI Executive Summary & Branch Processing</span>
            </div>
            <div id="step-4" class="flex items-center space-x-2 text-gray-400">
              <span>🎯 4. Interview Preparation Essentials & PDF Compilation</span>
            </div>
          </div>
        </div>

        <!-- RESULT CARD DISPLAY MATCHING DRIBBBLE SOFT NEUMORPHIC CARDS -->
        <div id="result-card" class="hidden max-w-4xl mx-auto space-y-6">

          <!-- MAIN HEADER CARD -->
          <div class="bg-white dark:bg-[#23252a] p-6 md:p-8 rounded-3xl border border-gray-100 dark:border-gray-800 shadow-xl flex flex-wrap items-start justify-between gap-4">
            <div>
              <h3 id="res-company-name" onclick="toggleCountryList()" class="text-2xl md:text-3xl font-extrabold text-gray-900 dark:text-white cursor-pointer hover:text-brandOrange transition flex items-center space-x-2">
                <span id="res-company-name-text">Tata Consultancy Services (TCS)</span>
                <span class="text-xs text-brandOrange font-normal bg-brandOrange/10 px-2.5 py-1 rounded-full border border-brandOrange/20">Click to View Countries ▾</span>
              </h3>
              <a id="res-website-link" href="#" target="_blank" class="text-xs font-mono text-brandOrange hover:underline block mt-2">https://www.tcs.com</a>
            </div>
            <span class="px-4 py-1.5 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-xs font-bold rounded-full border border-emerald-500/20 tracking-wider">
              RESEARCH COMPLETE
            </span>
          </div>

          <!-- CONDITIONAL PHONE CONTAINER -->
          <div id="phone-container" class="hidden bg-white dark:bg-[#23252a] p-5 rounded-2xl border border-gray-100 dark:border-gray-800 shadow-md">
            <span class="block text-[10px] font-bold uppercase tracking-wider text-gray-400 mb-1">PHONE</span>
            <p id="res-phone" class="text-xs font-semibold text-gray-900 dark:text-white"></p>
          </div>

          <!-- 3-TIER INTERACTIVE LOCATION DRILL-DOWN CONTAINER -->
          <div class="bg-white dark:bg-[#23252a] p-6 rounded-3xl border border-gray-100 dark:border-gray-800 shadow-xl space-y-4">
            <div class="flex items-center justify-between cursor-pointer" onclick="toggleCountryList()">
              <div>
                <span class="block text-xs font-bold uppercase tracking-wider text-brandOrange mb-1">LOCATION & BRANCH HIERARCHY</span>
                <p class="text-xs text-gray-500 dark:text-gray-400 font-medium">Click any Country to expand Cities, then click any City to view Street Address & Branch Focus.</p>
              </div>
              <button class="text-xs text-brandOrange hover:underline font-bold px-3 py-1.5 bg-brandOrange/10 rounded-full border border-brandOrange/20">
                Show Countries ▾
              </button>
            </div>

            <div id="countries-container" class="hidden pt-3 border-t border-gray-100 dark:border-gray-800 space-y-3">
              <!-- Dynamically populated countries list -->
            </div>
          </div>

          <!-- EXHAUSTIVE PRODUCTS & SERVICES PILLS -->
          <div class="bg-white dark:bg-[#23252a] p-6 rounded-3xl border border-gray-100 dark:border-gray-800 shadow-xl space-y-3">
            <span class="block text-xs font-bold uppercase tracking-wider text-brandOrange">ALL PRODUCTS & SERVICES</span>
            <div id="res-products-list" class="flex flex-wrap gap-2">
              <!-- Dynamically populated tags -->
            </div>
          </div>

          <!-- DETAILED SUMMARY SECTION (5-10 POINTS WITH UNIFORM STYLING) -->
          <div class="bg-white dark:bg-[#23252a] p-6 rounded-3xl border border-gray-100 dark:border-gray-800 shadow-xl space-y-3">
            <span class="block text-xs font-bold uppercase tracking-wider text-brandOrange">SUMMARY & BRANCH OPERATIONS</span>
            <div id="res-summary-list" class="space-y-3 text-xs leading-relaxed">
              <!-- Dynamically populated 5-10 uniform summary cards -->
            </div>
          </div>

          <!-- INTERVIEW PREPARATION & COMPANY ESSENTIALS -->
          <div class="bg-white dark:bg-[#23252a] p-6 md:p-8 rounded-3xl border border-gray-100 dark:border-gray-800 shadow-xl space-y-5">
            <div class="border-b border-gray-100 dark:border-gray-800 pb-3">
              <span class="block text-xs font-bold uppercase tracking-wider text-brandOrange">🎓 INTERVIEW PREPARATION & COMPANY ESSENTIALS</span>
              <p class="text-[11px] text-gray-400 mt-0.5">Authentic company facts, work culture, technical focus areas, and top questions for candidate interviews.</p>
            </div>

            <!-- KEY FACTS GRID -->
            <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div class="p-3.5 bg-gray-50 dark:bg-[#1a1b1f] rounded-2xl border border-gray-100 dark:border-gray-800">
                <span class="block text-[10px] font-bold text-gray-400 uppercase">FOUNDED</span>
                <span id="ip-founded" class="text-xs font-bold text-gray-900 dark:text-white block mt-1">1968</span>
              </div>
              <div class="p-3.5 bg-gray-50 dark:bg-[#1a1b1f] rounded-2xl border border-gray-100 dark:border-gray-800">
                <span class="block text-[10px] font-bold text-gray-400 uppercase">PARENT GROUP</span>
                <span id="ip-parent" class="text-xs font-bold text-gray-900 dark:text-white block mt-1">Tata Group</span>
              </div>
              <div class="p-3.5 bg-gray-50 dark:bg-[#1a1b1f] rounded-2xl border border-gray-100 dark:border-gray-800">
                <span class="block text-[10px] font-bold text-gray-400 uppercase">LEADERSHIP</span>
                <span id="ip-leadership" class="text-xs font-bold text-gray-900 dark:text-white block mt-1">K. Krithivasan (CEO)</span>
              </div>
              <div class="p-3.5 bg-gray-50 dark:bg-[#1a1b1f] rounded-2xl border border-gray-100 dark:border-gray-800">
                <span class="block text-[10px] font-bold text-gray-400 uppercase">GLOBAL HEADCOUNT</span>
                <span id="ip-headcount" class="text-xs font-bold text-gray-900 dark:text-white block mt-1">601,000+ Employees</span>
              </div>
            </div>

            <!-- CULTURE & VALUES -->
            <div>
              <span class="block text-[10px] font-bold text-brandOrange uppercase mb-1">WORK CULTURE & VALUES</span>
              <p id="ip-culture" class="text-xs text-gray-700 dark:text-gray-300 leading-relaxed bg-gray-50 dark:bg-[#1a1b1f] p-4 rounded-2xl border border-gray-100 dark:border-gray-800"></p>
            </div>

            <!-- TECHNICAL INTERVIEW FOCUS -->
            <div>
              <span class="block text-[10px] font-bold text-brandOrange uppercase mb-2">TECHNICAL INTERVIEW FOCUS AREAS</span>
              <div id="ip-tech-focus" class="flex flex-wrap gap-2">
                <!-- Dynamically populated pills -->
              </div>
            </div>

            <!-- TOP QUESTIONS -->
            <div>
              <span class="block text-[10px] font-bold text-brandOrange uppercase mb-2">FREQUENTLY ASKED INTERVIEW QUESTIONS</span>
              <div id="ip-questions-list" class="space-y-2">
                <!-- Dynamically populated questions -->
              </div>
            </div>
          </div>

          <!-- ACTION BUTTONS -->
          <div class="flex items-center justify-end pt-2">
            <button onclick="downloadPDF()" class="py-3 px-8 bg-brandOrange hover:bg-brandOrangeHover text-white font-bold text-xs rounded-full transition shadow-lg shadow-brandOrange/30 flex items-center space-x-2">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
              <span>Download PDF Report</span>
            </button>
          </div>

        </div>

      </div>

      <!-- CHAT INPUT BAR MATCHING DRIBBBLE NEUMORPHIC FLOATING PILL -->
      <div class="p-4 md:p-6 bg-white/70 dark:bg-[#1a1b1f]/70 backdrop-blur border-t border-gray-100 dark:border-gray-800 shrink-0">
        <div class="max-w-3xl mx-auto relative">
          <input type="text" id="company-input" placeholder="Enter company name, company and city name, or company website..." 
                 onkeydown="if(event.key==='Enter') executeResearch()"
                 class="w-full bg-gray-100 dark:bg-[#25272c] border border-gray-200 dark:border-gray-700/80 text-gray-900 dark:text-white text-xs rounded-full px-6 py-4 focus:outline-none focus:border-brandOrange pr-32 shadow-inner">
          <button onclick="executeResearch()" id="research-submit-btn" class="absolute right-2 top-2 bottom-2 px-6 bg-brandOrange hover:bg-brandOrangeHover text-white font-bold text-xs rounded-full transition flex items-center space-x-1 shadow-md shadow-brandOrange/30">
            <span>Research</span>
            <span>→</span>
          </button>
        </div>
      </div>

    </main>

  </div>

  <script>
    let currentReportData = null;
    let isSidebarShrunk = false;

    window.addEventListener('DOMContentLoaded', () => {
      // Light theme default
      const savedTheme = localStorage.getItem('theme_preference') || 'light';
      if (savedTheme === 'dark') {
        document.documentElement.classList.add('dark');
        document.getElementById('theme-icon').innerText = '🌙';
        document.getElementById('theme-text').innerText = 'Dark';
      } else {
        document.documentElement.classList.remove('dark');
        document.getElementById('theme-icon').innerText = '☀️';
        document.getElementById('theme-text').innerText = 'Light';
      }

      loadSearchHistory();
    });

    // LIGHT / DARK MODE TOGGLE FUNCTION
    function toggleThemeMode() {
      const htmlEl = document.documentElement;
      const themeIcon = document.getElementById('theme-icon');
      const themeText = document.getElementById('theme-text');

      if (htmlEl.classList.contains('dark')) {
        htmlEl.classList.remove('dark');
        themeIcon.innerText = '☀️';
        themeText.innerText = 'Light';
        localStorage.setItem('theme_preference', 'light');
      } else {
        htmlEl.classList.add('dark');
        themeIcon.innerText = '🌙';
        themeText.innerText = 'Dark';
        localStorage.setItem('theme_preference', 'dark');
      }
    }

    // SHRINK SIDEBAR TOGGLE FUNCTION
    function toggleSidebarShrink() {
      const sidebar = document.getElementById('sidebar-panel');
      const shrinkIcon = document.getElementById('shrink-icon');
      const labels = document.querySelectorAll('.sidebar-label');
      const footerCard = document.getElementById('sidebar-footer-card');
      const historyList = document.getElementById('history-list');
      const shrinkedRecentsBtn = document.getElementById('shrinked-recents-btn');

      isSidebarShrunk = !isSidebarShrunk;

      if (isSidebarShrunk) {
        sidebar.classList.remove('w-72');
        sidebar.classList.add('w-20');
        shrinkIcon.innerText = '►';
        labels.forEach(el => el.classList.add('hidden'));
        if (footerCard) footerCard.classList.add('hidden');
        if (historyList) historyList.classList.add('hidden');
        if (shrinkedRecentsBtn) shrinkedRecentsBtn.classList.remove('hidden');
      } else {
        sidebar.classList.remove('w-20');
        sidebar.classList.add('w-72');
        shrinkIcon.innerText = '◄';
        labels.forEach(el => el.classList.remove('hidden'));
        if (footerCard) footerCard.classList.remove('hidden');
        if (historyList) historyList.classList.remove('hidden');
        if (shrinkedRecentsBtn) shrinkedRecentsBtn.classList.add('hidden');
      }
    }

    function loadSearchHistory() {
      const history = JSON.parse(localStorage.getItem('search_history') || '[]');
      const container = document.getElementById('history-list');
      container.innerHTML = '';

      if (history.length === 0) {
        container.innerHTML = `<p class="sidebar-label text-xs text-gray-500 italic p-1">No search history.</p>`;
        return;
      }

      history.forEach(item => {
        const btn = document.createElement('button');
        btn.className = 'w-full text-left p-3 rounded-2xl bg-[#37383c] hover:bg-[#45464b] border border-gray-700/50 transition flex items-center justify-between group';
        btn.onclick = () => quickInput(item);
        btn.innerHTML = `
          <span class="sidebar-label text-xs font-medium text-gray-200 group-hover:text-white truncate">${item}</span>
        `;
        container.appendChild(btn);
      });
    }

    function saveToHistory(queryStr) {
      let history = JSON.parse(localStorage.getItem('search_history') || '[]');
      history = history.filter(q => q.toLowerCase() !== queryStr.toLowerCase());
      history.unshift(queryStr);
      if (history.length > 10) history = history.slice(0, 10);
      localStorage.setItem('search_history', JSON.stringify(history));
      loadSearchHistory();
    }

    function clearSearchHistory() {
      localStorage.removeItem('search_history');
      loadSearchHistory();
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
      
      if (!isValidCompanyInput(rawInput)) {
        alert("Please enter a valid company name, company and city name, or company website.");
        return;
      }

      const inputVal = rawInput.trim();
      saveToHistory(inputVal);

      document.getElementById('welcome-view').classList.add('hidden');
      document.getElementById('result-card').classList.add('hidden');
      document.getElementById('progress-loader').classList.remove('hidden');

      updateProgressStep(1, "🔍 1. Search & Multi-Country Office Resolver");

      try {
        setTimeout(() => updateProgressStep(2, "🕷️ 2. Web Crawler - Page Link Discovery"), 1200);
        setTimeout(() => updateProgressStep(3, "🧠 3. AI Executive Summary & Branch Processing"), 2500);
        setTimeout(() => updateProgressStep(4, "🎯 4. Interview Preparation Essentials & PDF Compilation"), 3800);

        const response = await fetch('/api/research', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ input: inputVal })
        });

        const data = await response.json();

        if (data.error) {
          alert('Research Error: ' + data.error);
          document.getElementById('progress-loader').classList.add('hidden');
          document.getElementById('welcome-view').classList.remove('hidden');
          return;
        }

        currentReportData = data.report;
        renderReportResult(data.report);

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
          el.className = "flex items-center space-x-2 text-brandOrange font-semibold pulse-glow";
        } else if (i < stepNum) {
          el.className = "flex items-center space-x-2 text-emerald-500 font-semibold";
        } else {
          el.className = "flex items-center space-x-2 text-gray-400";
        }
      }
    }

    function toggleCountryList() {
      const box = document.getElementById('countries-container');
      box.classList.toggle('hidden');
    }

    function toggleCountryCities(countryIdx) {
      const box = document.getElementById(`country-cities-${countryIdx}`);
      if (box) box.classList.toggle('hidden');
    }

    function toggleCityAddress(countryIdx, cityIdx) {
      const box = document.getElementById(`city-addr-${countryIdx}-${cityIdx}`);
      if (box) box.classList.toggle('hidden');
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

      // EXHAUSTIVE MULTI-COUNTRY LOCATION DRILL-DOWN (NO PIN EMOJI TO LEFT OF COUNTRY NAMES)
      const locs = report.locations || {};
      const countriesList = locs.countries || [];
      const countriesContainer = document.getElementById('countries-container');
      countriesContainer.innerHTML = '';
      countriesContainer.classList.add('hidden');

      if (countriesList.length === 0) {
        countriesContainer.innerHTML = `<p class="text-xs text-gray-400 italic p-3">No country location data available.</p>`;
      } else {
        countriesList.forEach((cItem, cIdx) => {
          const countryCard = document.createElement('div');
          countryCard.className = 'bg-gray-50 dark:bg-[#1a1b1f] p-4 rounded-2xl border border-gray-100 dark:border-gray-800 space-y-3';

          const citiesList = cItem.cities || [];
          let citiesHtml = '';

          citiesList.forEach((cityObj, cityIdx) => {
            const addrsHtml = (cityObj.addresses || []).map(addr => `
              <div class="p-3 bg-white dark:bg-[#23252a] rounded-xl border border-gray-100 dark:border-gray-800 text-xs text-gray-800 dark:text-gray-200 flex items-start space-x-2">
                <span class="text-brandOrange mt-0.5">🏢</span>
                <div>
                  <p class="font-semibold">${addr}</p>
                  ${cityObj.branch_focus ? `<p class="text-[10px] text-brandOrange font-mono mt-1">Focus: ${cityObj.branch_focus}</p>` : ''}
                </div>
              </div>
            `).join('');

            citiesHtml += `
              <div class="bg-white dark:bg-[#23252a] p-3.5 rounded-xl border border-gray-100 dark:border-gray-800 space-y-2">
                <div class="flex items-center justify-between cursor-pointer" onclick="toggleCityAddress(${cIdx}, ${cityIdx})">
                  <div class="flex items-center space-x-2 font-bold text-xs hover:text-brandOrange">
                    <span>🏙️ City: ${cityObj.city_name}</span>
                    <span class="text-[10px] text-gray-400 font-normal">(${(cityObj.addresses || []).length} Address)</span>
                  </div>
                  <span class="text-xs text-brandOrange font-bold">Click to view address ▾</span>
                </div>
                <div id="city-addr-${cIdx}-${cityIdx}" class="hidden space-y-2 pt-2 border-t border-gray-100 dark:border-gray-800">
                  ${addrsHtml}
                </div>
              </div>
            `;
          });

          countryCard.innerHTML = `
            <div class="flex items-center justify-between cursor-pointer" onclick="toggleCountryCities(${cIdx})">
              <div class="flex items-center space-x-2 font-bold text-sm hover:text-brandOrange">
                <span>Country: ${cItem.country_name}</span>
                <span class="text-xs text-brandOrange font-normal bg-brandOrange/10 px-2.5 py-0.5 rounded-full border border-brandOrange/20">${citiesList.length} Cities</span>
              </div>
              <span class="text-xs text-brandOrange font-bold">Click to view cities ▾</span>
            </div>
            <div id="country-cities-${cIdx}" class="hidden space-y-2.5 pt-3 border-t border-gray-100 dark:border-gray-800">
              ${citiesHtml}
            </div>
          `;
          countriesContainer.appendChild(countryCard);
        });
      }

      // EXHAUSTIVE PRODUCTS LIST
      const prodList = document.getElementById('res-products-list');
      prodList.innerHTML = '';
      (report.products_and_services || []).forEach(p => {
        const pill = document.createElement('span');
        pill.className = 'px-3.5 py-1.5 bg-gray-50 dark:bg-[#1a1b1f] text-gray-800 dark:text-gray-200 text-xs font-semibold rounded-full border border-gray-100 dark:border-gray-800';
        pill.innerText = p;
        prodList.appendChild(pill);
      });

      // 100% UNIFORM SUMMARY & BRANCH OPERATIONS (5 TO 10 POINTS)
      const summaryList = document.getElementById('res-summary-list');
      summaryList.innerHTML = '';
      const summaryItems = report.summary || report.pain_points || [];
      summaryItems.forEach((pt, i) => {
        const itemBox = document.createElement('div');
        itemBox.className = 'flex items-start space-x-3 p-4 rounded-2xl bg-gray-50 dark:bg-[#1a1b1f] border border-gray-100 dark:border-gray-800 text-gray-700 dark:text-gray-300';
        
        itemBox.innerHTML = `
          <span class="w-5 h-5 rounded-full bg-brandOrange/20 text-brandOrange text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">${i+1}</span>
          <p class="text-xs leading-relaxed">${pt}</p>
        `;
        summaryList.appendChild(itemBox);
      });

      // INTERVIEW PREPARATION SECTION RENDER
      const ip = report.interview_prep || {};
      const kf = ip.key_facts || {};

      document.getElementById('ip-founded').innerText = kf.founded || 'N/A';
      document.getElementById('ip-parent').innerText = kf.parent_organization || 'N/A';
      document.getElementById('ip-leadership').innerText = kf.leadership || 'N/A';
      document.getElementById('ip-headcount').innerText = kf.global_headcount || 'N/A';

      document.getElementById('ip-culture').innerText = ip.work_culture_and_values || 'Structured learning, ethics, and career growth.';

      // Tech focus pills
      const techBox = document.getElementById('ip-tech-focus');
      techBox.innerHTML = '';
      (ip.technical_interview_focus || []).forEach(t => {
        const tag = document.createElement('span');
        tag.className = 'px-3 py-1 bg-gray-50 dark:bg-[#1a1b1f] text-brandOrange font-semibold text-xs rounded-full border border-gray-100 dark:border-gray-800';
        tag.innerText = t;
        techBox.appendChild(tag);
      });

      // Questions list
      const qBox = document.getElementById('ip-questions-list');
      qBox.innerHTML = '';
      (ip.top_interview_questions || []).forEach((q, idx) => {
        const qItem = document.createElement('div');
        qItem.className = 'p-3.5 bg-gray-50 dark:bg-[#1a1b1f] rounded-2xl border border-gray-100 dark:border-gray-800 text-xs text-gray-800 dark:text-gray-200 flex items-start space-x-2.5';
        qItem.innerHTML = `
          <span class="px-2.5 py-0.5 bg-brandOrange/20 text-brandOrange font-bold text-[10px] rounded-full shrink-0 mt-0.5">Q${idx+1}</span>
          <p class="font-medium">${q}</p>
        `;
        qBox.appendChild(qItem);
      });
    }

    function downloadPDF() {
      if (!currentReportData) return;
      const compNameClean = currentReportData.company_name.toLowerCase().replace(/[^a-z0-9]/g, '_');
      generateClientSidePDF(currentReportData, compNameClean);
    }

    function generateClientSidePDF(report, filenameClean) {
      if (!window.jspdf) {
        alert("Generating PDF report...");
        return;
      }
      const { jsPDF } = window.jspdf;
      const doc = new jsPDF({ unit: 'pt', format: 'letter' });

      const compName = report.company_name || 'Company Report';
      const targetCity = report.target_city || '';
      const displayTitle = (targetCity && !compName.toLowerCase().includes(targetCity.toLowerCase())) 
        ? `${compName} ${targetCity}` 
        : compName;

      // 1. Dribbble Dark Charcoal Banner (#1f2023)
      doc.setFillColor(31, 32, 35);
      doc.rect(36, 36, 540, 60, 'F');

      doc.setTextColor(249, 115, 22); // Warm Coral Orange (#f97316)
      doc.setFontSize(8);
      doc.setFont('helvetica', 'bold');
      doc.text('CORPINTEL AI · COMPANY RESEARCH & INTELLIGENCE REPORT', 52, 56);

      doc.setTextColor(255, 255, 255);
      doc.setFontSize(18);
      doc.text(displayTitle, 52, 78);

      let y = 120;

      // 2. Section: COMPANY INFORMATION
      doc.setTextColor(249, 115, 22);
      doc.setFontSize(10);
      doc.setFont('helvetica', 'bold');
      doc.text('COMPANY INFORMATION', 36, y);
      y += 4;
      doc.setDrawColor(249, 115, 22);
      doc.setLineWidth(1);
      doc.line(36, y, 576, y);
      y += 12;

      const boxStartY = y;
      doc.setFillColor(248, 250, 252);
      doc.rect(36, boxStartY, 540, 140, 'F');
      doc.setDrawColor(226, 232, 240);
      doc.setLineWidth(0.5);
      doc.rect(36, boxStartY, 540, 140, 'S');
      doc.line(146, boxStartY, 146, boxStartY + 140, 'S');
      doc.line(36, boxStartY + 26, 576, boxStartY + 26, 'S');

      doc.setTextColor(30, 41, 59);
      doc.setFontSize(9);
      doc.setFont('helvetica', 'bold');
      doc.text('Website', 46, boxStartY + 16);

      doc.setFont('helvetica', 'normal');
      doc.setTextColor(249, 115, 22);
      doc.text(report.website || '', 156, boxStartY + 16);

      doc.setTextColor(30, 41, 59);
      doc.setFont('helvetica', 'bold');
      doc.text('Branch Locations', 46, boxStartY + 42);

      let locY = boxStartY + 42;
      const locs = report.locations || {};
      const countries = locs.countries || [];

      countries.forEach(c => {
        if (locY > boxStartY + 130) return;
        doc.setFont('helvetica', 'bold');
        doc.setTextColor(249, 115, 22);
        doc.text(c.country_name || '', 156, locY);
        locY += 12;

        (c.cities || []).forEach(city => {
          if (locY > boxStartY + 130) return;
          doc.setFont('helvetica', 'normal');
          doc.setTextColor(51, 65, 85);
          const addrs = (city.addresses || []).join(', ');
          const lineStr = `• ${city.city_name}: ${addrs}`;
          const splitLines = doc.splitTextToSize(lineStr, 400);
          doc.text(splitLines, 166, locY);
          locY += (splitLines.length * 11);
        });
      });

      y = boxStartY + 154;

      // 3. Section: PRODUCTS & SERVICES
      doc.setFont('helvetica', 'bold');
      doc.setTextColor(249, 115, 22);
      doc.setFontSize(10);
      doc.text('PRODUCTS & SERVICES', 36, y);
      y += 4;
      doc.line(36, y, 576, y);
      y += 16;

      doc.setFont('helvetica', 'bold');
      doc.setTextColor(30, 41, 59);
      doc.setFontSize(9);

      (report.products_and_services || []).forEach(p => {
        if (y > 740) { doc.addPage(); y = 40; }
        doc.text(`• ${p}`, 46, y);
        y += 14;
      });

      y += 10;

      // 4. Section: SUMMARY & BRANCH OPERATIONS
      if (y > 640) { doc.addPage(); y = 40; }
      doc.setFont('helvetica', 'bold');
      doc.setTextColor(249, 115, 22);
      doc.setFontSize(10);
      doc.text('SUMMARY & BRANCH OPERATIONS', 36, y);
      y += 4;
      doc.line(36, y, 576, y);
      y += 16;

      doc.setFont('helvetica', 'normal');
      doc.setTextColor(30, 41, 59);
      doc.setFontSize(9);

      (report.summary || report.pain_points || []).forEach((pt, idx) => {
        const splitPt = doc.splitTextToSize(`${idx + 1}. ${pt}`, 520);
        if (y + (splitPt.length * 13) > 740) { doc.addPage(); y = 40; }
        doc.text(splitPt, 46, y);
        y += (splitPt.length * 13) + 6;
      });

      y += 10;

      // 5. Section: INTERVIEW PREPARATION & COMPANY ESSENTIALS
      if (y > 600) { doc.addPage(); y = 40; }
      doc.setFont('helvetica', 'bold');
      doc.setTextColor(249, 115, 22);
      doc.setFontSize(10);
      doc.text('INTERVIEW PREPARATION & COMPANY ESSENTIALS', 36, y);
      y += 4;
      doc.line(36, y, 576, y);
      y += 14;

      const ip = report.interview_prep || {};
      const kf = ip.key_facts || {};

      doc.setFillColor(248, 250, 252);
      doc.rect(36, y, 540, 36, 'F');
      doc.setDrawColor(226, 232, 240);
      doc.rect(36, y, 540, 36, 'S');

      doc.setFont('helvetica', 'bold');
      doc.setFontSize(8.5);
      doc.setTextColor(30, 41, 59);
      doc.text(`Founded: ${kf.founded || 'N/A'}    |    Parent: ${kf.parent_organization || 'N/A'}    |    Leadership: ${kf.leadership || 'N/A'}`, 46, y + 14);
      doc.text(`Global Headcount: ${kf.global_headcount || 'N/A'}`, 46, y + 26);

      y += 46;

      const culture = ip.work_culture_and_values || '';
      if (culture) {
        doc.setFont('helvetica', 'bold');
        doc.text('Work Culture & Values:', 36, y);
        y += 12;
        doc.setFont('helvetica', 'normal');
        doc.setTextColor(51, 65, 85);
        const splitCul = doc.splitTextToSize(culture, 520);
        doc.text(splitCul, 36, y);
        y += (splitCul.length * 12) + 8;
      }

      const topQ = ip.top_interview_questions || [];
      if (topQ.length > 0) {
        doc.setFont('helvetica', 'bold');
        doc.setTextColor(249, 115, 22);
        doc.text('Frequently Asked Interview Questions:', 36, y);
        y += 12;

        topQ.forEach((q, idx) => {
          doc.setFont('helvetica', 'normal');
          doc.setTextColor(30, 41, 59);
          const splitQ = doc.splitTextToSize(`Q${idx+1}: ${q}`, 520);
          if (y + (splitQ.length * 12) > 740) { doc.addPage(); y = 40; }
          doc.text(splitQ, 36, y);
          y += (splitQ.length * 12) + 4;
        });
      }

      doc.save(`${filenameClean}_research_report.pdf`);
    }
  </script>
</body>
</html>'''

if __name__ == "__main__":
    print(f"============================================================")
    print(f"CorpIntel AI - Corporate Intelligence Platform")
    print(f"Starting server on http://localhost:{PORT}...")
    print(f"============================================================")
    
    server = HTTPServer(("0.0.0.0", PORT), ReluRequestHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server gracefully...")
        server.server_close()
