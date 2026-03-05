import requests
import json
import os
import google.generativeai as genai

def process_lead_with_ai(lead_id: str, db: dict):
    lead = next((l for l in db["leads"] if l["id"] == lead_id), None)
    if not lead:
        return

    company_name = lead.get('company_name', 'your company')
    city = lead.get('city', 'your area')

    # Clean up company name if it has long SEO spam in it
    if "|" in company_name:
        company_name = company_name.split("|")[0].strip()
    if "-" in company_name and len(company_name.split("-")[0].strip()) > 3:
        company_name = company_name.split("-")[0].strip()

    # Build context safely — leads may not have a 'context' field
    context = lead.get('context') or lead.get('intel', {}) or {}
    if isinstance(context, dict):
        addr = context.get('address', '')
        founder = context.get('founder', '')
        context_str = f"Address: {addr}. Key person: {founder}." if (addr or founder) else f"Real estate company based in {city}."
    else:
        context_str = str(context) if context else f"Real estate agency based in {city}."

    prompt = f"""You are a concise B2B salesperson for a real estate AI firm.
Write a highly personalized, short cold email (max 3 sentences) to this real estate company.

Company Name: {company_name}
City: {city}
Context: {context_str}

Rules:
- ZERO buzzwords like 'delve', 'leverage', or 'supercharge'.
- Sound human. Like it was written by an expert in 30 seconds on their iPhone.
- Start with just "Hey {company_name}," or "Hi {company_name} team,"
- Briefly reference something from the context to prove you looked at them.
- Pitch AI automation for real estate (e.g. auto-follow-ups, saving agent time).
- No subject line. Just the email body."""

    from dotenv import dotenv_values
    env_vars = dotenv_values(".env")
    gemini_key = env_vars.get("GEMINI_API_KEY", "").strip()

    if gemini_key and gemini_key not in ("your_gemini_api_key_here", ""):
        try:
            genai.configure(api_key=gemini_key)
            # Use gemini-2.0-flash (latest fast model)
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(prompt)
            draft = (response.text or "").strip()
            if draft:
                lead["drafted_email"] = draft
                lead["status"] = "AI Drafted 🤖"
                print(f"✅ Gemini drafted for: {company_name}")
                return
            else:
                print(f"⚠️ Gemini returned empty response for {company_name}. Falling back.")
        except Exception as e:
            print(f"❌ Gemini API failed for {company_name}: {e}. Falling back to Ollama.")

    # Fallback 1: Local Ollama
    ollama_url = env_vars.get("OLLAMA_API_URL", "http://localhost:11434/api/generate")
    ollama_model = env_vars.get("OLLAMA_MODEL", "llama3")

    try:
        response = requests.post(
            ollama_url,
            json={"model": ollama_model, "prompt": prompt, "stream": False},
            timeout=15
        )
        if response.status_code == 200:
            draft = response.json().get("response", "").strip()
            lead["drafted_email"] = draft
            lead["status"] = "AI Drafted 🤖"
            print(f"✅ Ollama drafted for: {company_name}")
            return
        else:
            raise Exception(f"Ollama returned {response.status_code}")
    except Exception as e:
        print(f"⚠️ Ollama unavailable ({e}). Using heuristic fallback.")

    # Fallback 2: Smart heuristic template (always succeeds)
    fallback_email = (
        f"Hey {company_name} team,\n\n"
        f"I came across your work in {city} and noticed you're managing a solid pipeline of listings. "
        f"We build AI assistants for real estate teams that auto-follow-up on every web lead the moment they come in — "
        f"most of our clients recover 3-4 hours per agent per day.\n\n"
        f"Would a quick 10-min call make sense this week?\n\nCheers,\nOutreach AI"
    )
    lead["drafted_email"] = fallback_email
    lead["status"] = "AI Drafted 🤖"
    print(f"✅ Heuristic draft used for: {company_name}")
