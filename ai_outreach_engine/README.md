# 🚀 Hyper-Nova AI Outreach Engine

> An autonomous AI-powered B2B lead generation and multi-channel outreach system. It finds real estate agencies, scrapes contact intelligence, generates hyper-personalized emails with AI, and deploys them — or initiates live AI voice calls — all from a slick dashboard.

---

## 📸 Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                     HYPER-NOVA ENGINE                            │
│                                                                  │
│   [React Frontend (Vite)]  ←──REST API──→  [FastAPI Backend]    │
│          |                                       |               │
│    AI Radar Tab                          ┌───────┴────────┐      │
│    Command Center Tab                    │   Scraper      │      │
│                                          │   AI Engine    │      │
│                                          │   Email Sender │      │
│                                          │   Voice (Vapi) │      │
│                                          └────────────────┘      │
└──────────────────────────────────────────────────────────────────┘
```

---

## ✨ What It Does

Hyper-Nova is a full-stack autonomous outreach machine. Here's the end-to-end workflow:

1. **🎯 Target** — You type a search query (e.g. *"Top real estate agencies"*) and a city (e.g. *"Miami"*)
2. **🕷️ Scan** — The backend fires a multi-query web scraper across Yahoo Search, harvesting up to 45 real estate agency candidates with domain deduplication and blacklisting
3. **🔍 Deep Intel** — Each candidate's website is crawled using 9-strategy address extraction, phone number detection, LinkedIn discovery, and founder/CEO identification
4. **🤖 AI Draft** — Gemini 2.0 Flash (or Ollama/heuristic fallback) writes a personalized 3-sentence cold email per lead based on scraped context
5. **✉️ Send Email** — You review + optionally edit the draft, then deploy it via SMTP with a PDF brochure automatically attached
6. **📞 Voice Call** — One click triggers an outbound AI phone call to the lead via Vapi (if a phone number was found)
7. **📊 Command Center** — A real-time log table tracks every email sent, delivery status, and server responses

---

## 🏗️ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend** | React 19 + Vite | SPA dashboard with real-time polling |
| **UI Icons** | Lucide React | Icon library |
| **Backend** | FastAPI (Python) | REST API server |
| **AI (Primary)** | Google Gemini 2.0 Flash | Personalized email generation |
| **AI (Fallback)** | Ollama (local LLM) | Offline/private fallback |
| **AI (Last resort)** | Heuristic template | Always-succeeds fallback |
| **Scraping** | BeautifulSoup + Requests | Web scraping & HTML parsing |
| **Concurrency** | ThreadPoolExecutor | Parallel website crawling (8 workers) |
| **Email** | Python smtplib / SMTP | Email delivery via Gmail |
| **PDF** | ReportLab | Auto-generated services brochure |
| **Voice** | Vapi.ai API | Outbound AI phone calls |
| **Config** | python-dotenv | Environment variable management |

---

## 📁 Project Structure

```
ai_outreach_engine/
├── backend/
│   ├── main.py              # FastAPI app — all REST endpoints
│   ├── scraper.py           # Yahoo search scraper + intel extractor
│   ├── ai_engine.py         # Gemini / Ollama / heuristic draft generator
│   ├── email_sender.py      # SMTP sender with PDF attachment
│   ├── generate_brochure.py # ReportLab PDF brochure generator
│   ├── services_brochure.pdf# Auto-generated PDF (attached to every email)
│   └── .env                 # API keys & credentials (NOT committed)
└── frontend/
    ├── src/
    │   ├── App.jsx          # Main React app component
    │   ├── index.css        # Global styles & dark theme
    │   └── main.jsx         # React entry point
    ├── index.html
    ├── vite.config.js
    └── package.json
```

---

## ✉️ How Email Works

```
User clicks "Deploy Email"
        │
        ▼
 POST /api/send/{lead_id}
        │
        ▼
 email_sender.py::send_email_to_lead()
        │
        ├── Load SMTP credentials from .env
        │       SMTP_SERVER=smtp.gmail.com
        │       SMTP_PORT=587 (STARTTLS)
        │       SMTP_USER=your@gmail.com
        │       SMTP_PASSWORD=app_password
        │
        ├── Build MIMEMultipart message
        │       From / To / Subject headers
        │       Plain-text body (AI-drafted + optionally edited)
        │
        ├── Attach PDF brochure
        │       services_brochure.pdf  (auto-generated on first run)
        │       Added as: "Hyper-Nova AI — Services Brochure.pdf"
        │
        ├── Connect via smtplib.SMTP → EHLO → STARTTLS → LOGIN
        │
        ├── send_message() → server.quit()
        │
        └── Log result to db["logs"]
                status: SUCCESS / FAILED
                response: "SMTP 250 OK" or error message
```

> **Gmail Setup**: You must use a [Google App Password](https://myaccount.google.com/apppasswords), not your regular password. Enable 2FA on your Google account first.

> **Simulation Mode**: If SMTP credentials are not configured in `.env`, the engine prints a simulation log to the console instead of actually sending — safe for development.

---

## 📞 How Voice Calls Work

```
User clicks 📞 (phone button on a lead card)
        │
        ▼
 POST /api/voice-call/{lead_id}
        │
        ▼
 main.py::trigger_voice_call()
        │
        ├── Look up lead's phone number
        │       Extracted by scraper from:
        │         - <a href="tel:..."> links
        │         - Indian mobile regex (+91 XXXXXXXXXX)
        │         - Landline patterns (STD codes)
        │
        ├── Load Vapi credentials from .env
        │       VAPI_API_KEY
        │       VAPI_PHONE_NUMBER_ID   ← your purchased Vapi number
        │       VAPI_ASSISTANT_ID      ← your pre-built AI assistant
        │
        ├── POST https://api.vapi.ai/call/phone
        │       {
        │         "phoneNumberId": "...",
        │         "assistantId": "...",
        │         "customer": {
        │           "number": "+91XXXXXXXXXX",
        │           "name": "Agency Name"
        │         }
        │       }
        │
        └── Vapi dials the lead and runs the AI assistant
                Lead status → "Call Initiated 📞"
```

> **Vapi Setup**: Create an account at [vapi.ai](https://vapi.ai), purchase a phone number, configure an AI assistant with your pitch script, and paste the IDs into `.env`.

---

## 🕷️ How the Scraper Works

The scraper uses a multi-phase approach to find and enrich leads:

### Phase 1 — Search Harvest
Fires 3 Yahoo Search queries per hunt across up to 3 pages (30 results each):
- `"<city>" real estate agencies`
- `top real estate companies in <city>`
- `"<city>" property consultants site contact`

Filters out blacklisted domains (MagicBricks, 99acres, Zillow, LinkedIn, etc.) and deduplicates by domain.

### Phase 2 — Listicle Extraction
If a search result looks like a "Top 10 agencies" blog post, it crawls into that page and extracts the real agency links from headings and anchors.

### Phase 3 — Deep Intel (Parallel, 8 workers)
For each candidate agency website, it runs 9 extraction strategies:

| Strategy | Method |
|---|---|
| 1 | Google Maps iframe `q=` parameter |
| 2 | JSON-LD `schema.org/PostalAddress` |
| 3 | HTML `<address>` tag |
| 4 | `itemprop="address"` microdata |
| 5 | CSS class/id patterns (`address`, `location`, etc.) |
| 6 | Label-sibling (`Address:` text → next sibling element) |
| 7 | Footer section → PIN code regex |
| 8 | Page-wide PIN code regex |
| 9 | Generic street-type regex |

Also crawls sub-pages: `/contact`, `/about`, `/team`, `/location` for richer data.

### Phase 4 — Scoring & Sorting
Leads are scored by completeness:
- `+2000` — verified email found
- `+1500` — address mentions the searched city
- `+1000` — phone number found
- `+600` — founder/CEO identified
- `+400` — LinkedIn profile found

---

## 🤖 How AI Email Drafting Works

```
User clicks "Draft Pitch"
        │
        ▼
 POST /api/generate-draft/{lead_id}   (runs in background)
        │
        ▼
 ai_engine.py::process_lead_with_ai()
        │
        ├── Build prompt:
        │       Company name (cleaned of SEO junk)
        │       City
        │       Context: address + founder from scraper intel
        │
        ├── Try Gemini 2.0 Flash (primary)
        │       genai.GenerativeModel('gemini-2.0-flash')
        │       → Returns 3-sentence cold email
        │
        ├── Fallback 1: Local Ollama
        │       POST http://localhost:11434/api/generate
        │       Model: llama3 (configurable)
        │
        └── Fallback 2: Smart heuristic template
                Always succeeds — city/company personalized
```

**Prompt rules enforced:**
- Zero buzzwords ("leverage", "supercharge", "delve")
- Sounds human — written in 30 seconds on an iPhone
- Starts with `Hey {company},` or `Hi {company} team,`
- References something specific from the scraped context
- Pitches AI automation for real estate

---

## ⚙️ Setup & Running

### Prerequisites
- Python 3.10+
- Node.js 18+
- A Gmail account with an [App Password](https://myaccount.google.com/apppasswords)
- A [Gemini API key](https://aistudio.google.com/app/apikey) (free)
- *(Optional)* A [Vapi.ai](https://vapi.ai) account for voice calls

### 1. Backend

```bash
cd ai_outreach_engine/backend

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install fastapi uvicorn python-dotenv requests beautifulsoup4 google-generativeai reportlab

# Configure your .env file
# (Edit GEMINI_API_KEY, SMTP_USER, SMTP_PASSWORD, and optionally VAPI_*)

# Start the server
uvicorn main:app --reload --port 8000
```

### 2. Frontend

```bash
cd ai_outreach_engine/frontend

npm install
npm run dev
# Opens at http://localhost:5173
```

### 3. Configure `.env`

```env
# AI
GEMINI_API_KEY=your_gemini_key_here

# Email (Gmail)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASSWORD=your_app_password   # NOT your login password

# Voice (optional)
VAPI_API_KEY=your_vapi_key
VAPI_PHONE_NUMBER_ID=your_phone_id
VAPI_ASSISTANT_ID=your_assistant_id

# Local LLM (optional fallback)
OLLAMA_API_URL=http://localhost:11434/api/generate
OLLAMA_MODEL=llama3
```

---

## 🗺️ System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER BROWSER                                 │
│                   React + Vite (port 5173)                          │
│                                                                     │
│  ┌──────────────────┐        ┌──────────────────────────────────┐   │
│  │   AI Radar Tab   │        │       Command Center Tab         │   │
│  │                  │        │                                  │   │
│  │  [Search Query]  │        │  📊 Stats: Sent / Failed         │   │
│  │  [City Input]    │        │  📋 Real-time outreach log table │   │
│  │  [Deploy Radar]  │        │                                  │   │
│  │                  │        └──────────────────────────────────┘   │
│  │  Lead Cards:     │                                               │
│  │  ┌────────────┐  │                                               │
│  │  │ Company    │  │                                               │
│  │  │ Email/Ph   │  │                                               │
│  │  │ AI Draft   │  │                                               │
│  │  │ [Draft]    │  │                                               │
│  │  │ [Send] [📞]│  │                                               │
│  │  └────────────┘  │                                               │
│  └──────────────────┘                                               │
└──────────────────────┬──────────────────────────────────────────────┘
                       │ HTTP REST (polling every 2s)
                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (port 8000)                        │
│                                                                     │
│  POST /api/target          → triggers scraping job (background)     │
│  GET  /api/leads           → returns all discovered leads           │
│  GET  /api/status          → returns is_hunting flag                │
│  POST /api/generate-draft  → triggers AI email generation           │
│  POST /api/send/{id}       → sends email via SMTP                   │
│  POST /api/voice-call/{id} → initiates Vapi phone call             │
│  GET  /api/logs            → returns outreach history               │
└────┬──────────────┬──────────────┬────────────────┬─────────────────┘
     │              │              │                │
     ▼              ▼              ▼                ▼
┌─────────┐  ┌──────────┐  ┌───────────┐  ┌──────────────┐
│ scraper │  │ai_engine │  │email_send │  │  Vapi API    │
│         │  │          │  │           │  │              │
│ Yahoo   │  │ Gemini   │  │ smtplib   │  │ POST         │
│ search  │  │ 2.0 Flash│  │ STARTTLS  │  │ /call/phone  │
│         │  │    ↓     │  │           │  │              │
│ HTML    │  │ Ollama   │  │ PDF attach│  │ AI assistant │
│ parse   │  │    ↓     │  │ brochure  │  │ speaks to    │
│         │  │heuristic │  │           │  │ the lead     │
│9-strat  │  │template  │  │           │  │              │
│address  │  └──────────┘  └───────────┘  └──────────────┘
│extractor│
│phone/   │
│linkedin │
│founder  │
└─────────┘
```

---

## 🔑 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Health check |
| `POST` | `/api/target` | Start a new lead hunt `{query, city}` |
| `GET` | `/api/leads` | Get all discovered leads |
| `GET` | `/api/status` | Check if hunt is still running |
| `POST` | `/api/generate-draft/{id}` | Trigger AI email drafting for a lead |
| `POST` | `/api/send/{id}` | Send email (with optional `{email_body}` override) |
| `POST` | `/api/voice-call/{id}` | Initiate Vapi outbound call |
| `GET` | `/api/logs` | Get outreach history |

---

## 📎 PDF Brochure

Every email is automatically accompanied by a professionally formatted PDF brochure (`services_brochure.pdf`) generated using **ReportLab**. It is:
- Auto-generated on first run if not present
- Attached to every outgoing email as `"Hyper-Nova AI — Services Brochure.pdf"`
- Describes the AI automation services offered

---

## 🛡️ Important Notes

- **`.env` is sensitive** — never commit it to version control. It contains API keys and SMTP credentials.
- **In-memory database** — leads and logs are stored in a Python dict. They reset on server restart.
-  **Gmail App Password** — Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords). Generate a password specifically for this app.
- **Vapi Voice Calls** — Requires a paid Vapi account with a purchased phone number and a configured AI assistant.
- **Rate Limiting** — Yahoo Search may throttle aggressive scraping. The scraper uses human-like User-Agent headers.

---

## 🧑‍💻 Built With

- **FastAPI** — Modern, fast Python web framework
- **React 19** — Latest React with hooks
- **Vite 7** — Lightning-fast frontend build tool
- **Google Gemini** — State-of-the-art LLM for personalization
- **Vapi.ai** — Voice AI platform for outbound calls
- **BeautifulSoup4** — HTML parsing for web scraping
- **ReportLab** — PDF generation library

---

*Made with ⚡ by Hyper-Nova*
