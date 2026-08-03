# CorpIntel AI 🚀
## Enterprise Corporate Intelligence Platform & Student Interview Preparation

**CorpIntel AI** is a professional corporate intelligence application built in pure Python. Designed with a soft Dribbble neumorphic UI, it combines multi-page web crawling, live search parsing, and AI reasoning to extract:
- 📍 **Exhaustive Multi-Country Branch Hierarchies** (US, India, UK, Singapore, Canada, Germany)
- 🏢 **Executive Summaries & Product Catalogs**
- 🎓 **Candidate Interview Preparation** (Founding Year, CEO Leadership, Parent Group, Headcount, Work Culture, Technical Focus, and Top Questions)
- 📄 **Dual-Engine Styled PDF Exports**

---

## 🔒 Security Best Practices

To prevent API key leaks when pushing to GitHub (`https://github.com/meganathan-data/CorpIntel-AI`):
- All API keys are loaded safely via environment variables (`os.environ.get("GOOGLE_API_KEY")`).
- Never commit `.env` or raw key strings to Git.
- Use `.env.example` as a template.

---

## 🐙 1. Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit of CorpIntel AI"
git branch -M main
git remote add origin https://github.com/meganathan-data/CorpIntel-AI.git
git push -u origin main
```

---

## 📐 2. Deploy on Vercel

1. Go to [Vercel Dashboard](https://vercel.com/dashboard) and click **Add New Project**.
2. Import repository **`meganathan-data/CorpIntel-AI`**.
3. Under **Environment Variables**, add:
   - `GOOGLE_API_KEY` = `your_google_gemini_api_key`
   - `SERPER_API_KEY` = `your_serper_dev_api_key`
4. Click **Deploy**! Vercel will automatically build and deploy `main.py` using `vercel.json`.

---

## 🏃 Local Execution

```bash
# Set environment variables in your terminal or .env file
export GOOGLE_API_KEY="your_api_key_here"

# Run application
python main.py
```
Open `http://localhost:8000` in your web browser.
