from fastapi import FastAPI, BackgroundTasks, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Any
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(override=True)

from scraper import trigger_scraping_job
from ai_engine import process_lead_with_ai
from email_sender import send_email_to_lead
import requests as http_requests

app = FastAPI(title="Hyper-Nova Outreach Engine")
print(" HYPER-NOVA BACKEND IS LIVE AND RELOADED")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock database (in a real app, use SQLAlchemy/SQLite)
db = {
    "leads": [],
    "logs": [],
    "is_hunting": False
}

@app.get("/api/logs")
def get_logs():
    return {"logs": db["logs"]}

class SearchRequest(BaseModel):
    query: str
    city: str

class LeadResponse(BaseModel):
    id: str
    company_name: str
    website: str
    email: Optional[str]
    context: Optional[str]
    drafted_email: Optional[str]
    status: str

class SendRequest(BaseModel):
    email_body: Optional[str] = None  # if provided, use this instead of stored draft

@app.get("/")
def root():
    return {"status": "Engine is running"}

@app.post("/api/target")
async def target_leads(request: SearchRequest, background_tasks: BackgroundTasks):
    job_id = f"job_{len(db['leads']) + 1}"
    db["is_hunting"] = True
    db["leads"] = [] # Clear old results on new hunt
    # Start the scraping in background
    background_tasks.add_task(trigger_scraping_job, request.query, request.city, db)
    return {"status": "hunting", "job_id": job_id, "message": f"Hunting for leads in {request.city}"}

@app.get("/api/status")
def get_status():
    return {"is_hunting": db["is_hunting"]}

@app.get("/api/leads")
def get_leads():
    return {"leads": db["leads"]}

@app.post("/api/generate-draft/{lead_id}")
async def generate_draft(lead_id: str, background_tasks: BackgroundTasks):
    # Trigger Ollama generation for this lead
    lead = next((l for l in db["leads"] if l["id"] == lead_id), None)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    lead["status"] = "Generating AI Draft..."
    background_tasks.add_task(process_lead_with_ai, lead_id, db)
    return {"status": "generating", "message": "Ollama is drafting the email"}

@app.post("/api/send/{lead_id}")
async def send_lead_email(lead_id: str, payload: Optional[dict] = Body(None)):
    lead = next((l for l in db["leads"] if l["id"] == lead_id), None)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Use edited body from frontend if provided, else fall back to stored draft
    email_body_override = (payload or {}).get("email_body") if payload else None
    body_to_send = email_body_override or lead.get("drafted_email")
    if not body_to_send:
        raise HTTPException(status_code=400, detail="No email body to send")
    
    # Persist edited version back
    lead["drafted_email"] = body_to_send
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    success = send_email_to_lead(lead["email"], "Scaling " + lead["company_name"], body_to_send)
    print(f"📧 SMTP send to {lead['email']} → {'SUCCESS' if success else 'FAILED'}")
    
    log_entry = {
        "id": str(len(db["logs"]) + 1),
        "company_name": lead["company_name"],
        "email": lead["email"],
        "status": "SUCCESS" if success else "FAILED",
        "response": "SMTP 250 OK (Server Accepted)" if success else "SMTP Error: Handshake Failure",
        "date": timestamp,
        "notes": f"Personalized outreach for {lead['city']} campaign."
    }
    db["logs"].append(log_entry)

    if success:
        lead["status"] = "SENT 🚀"
        return {"status": "sent", "log": log_entry}
    else:
        lead["status"] = "FAILED"
        raise HTTPException(status_code=500, detail="Failed to send email")


@app.post("/api/voice-call/{lead_id}")
def trigger_voice_call(lead_id: str):
    """Initiate an AI outbound voice call via Vapi."""
    lead = next((l for l in db["leads"] if l["id"] == lead_id), None)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    phone = lead.get("phone") or (lead.get("intel") or {}).get("phone")
    if not phone:
        raise HTTPException(status_code=400, detail="No phone number found for this lead")

    vapi_key = os.getenv("VAPI_API_KEY", "").strip()
    if not vapi_key or vapi_key == "your_vapi_api_key_here":
        raise HTTPException(status_code=400, detail="VAPI_API_KEY not configured in .env")

    phone_number_id = os.getenv("VAPI_PHONE_NUMBER_ID", "").strip()
    assistant_id    = os.getenv("VAPI_ASSISTANT_ID", "").strip()

    payload = {
        "phoneNumberId": phone_number_id,
        "assistantId":   assistant_id,
        "customer": {
            "number": phone,
            "name":   lead.get("company_name", "")
        }
    }

    try:
        resp = http_requests.post(
            "https://api.vapi.ai/call/phone",
            headers={
                "Authorization": f"Bearer {vapi_key}",
                "Content-Type":  "application/json"
            },
            json=payload,
            timeout=15
        )
        if resp.status_code in (200, 201):
            lead["status"] = "Call Initiated 📞"
            return {"status": "call_initiated", "phone": phone, "data": resp.json()}
        else:
            raise HTTPException(status_code=resp.status_code,
                                detail=f"Vapi error: {resp.text[:200]}")
    except http_requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Vapi unreachable: {str(e)}")
